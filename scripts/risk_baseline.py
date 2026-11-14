"""Baseline risk layer: historical probability of fire activity per 0.25 degree cell and week.

This is the reference the risk model (block 8, module M5) has to beat. It also gives the web app a
real risk layer before the model exists.

Inputs:
    NASA_Data_Sources/processed/hotspots/                  unified table (scripts/build_hotspots.py)
    NASA_Data_Sources/processed/quality/quality_flags.parquet   block 1 filter (`keep`)
    NASA_Data_Sources/processed/quality/outage_days.csv         block 1 outages
    Both quality files come from notebooks/01_quality.ipynb.

Outputs (NASA_Data_Sources/processed/risk/):
    cells_weekly.parquet       contract C3: week_start, cell_lat, cell_lon, probability,
                               baseline_probability. Until the model exists, probability is the
                               baseline. Rows cover the evaluation years, the rest of the current
                               year and a few weeks ahead.
    baseline_eval.parquet      the same rows plus `observed` (1 fire, 0 no fire, null not observed
                               yet), for notebooks.
    baseline_metrics.json      Brier score, average precision and ROC AUC per test year.

Definitions (see docs/eda-plan.md):
    - Day key `burn_date`: day from 06:00 to 06:00 local solar time, read from the hotspot table
      (scripts/timefields.py). Rebuild the table with scripts/build_hotspots.py if it is missing.
    - Week: 52 fixed 7-day bins per year. 29 February is merged into 28 February and the last bin
      takes the remaining day (8 days). `week_start` is the first `burn_date` of the bin.
    - Cell: 0.25 degree, identified by its south-west corner.
    - Target: at least one VIIRS detection in the cell during the week. VIIRS only (2012 onward),
      so the target does not depend on the MODIS harmonisation.
    - Reference series (default): Suomi-NPP from 2012-02-01 to 2026-10-31, NOAA-20 from 2026-11-01,
      the same periods as scripts/harmonize.py. Counting every VIIRS
      satellite would make the target depend on how many satellites flew each year (1, 2, 3, then 2),
      so a model could learn the satellite count as if it were fire. Use --target all-viirs to compare.
    - Baseline for year Y, cell c and week w: mean weekly fire rate of c over weeks w-1, w and w+1
      of every earlier year (each observed cell-week counts once), shrunk towards the cell's average
      weekly rate. A cell that burns in one of the three weeks every year gets about 0.33. The window
      crosses the year boundary into the adjacent year (week 0 uses week 51 of the year before) and
      never reads year Y itself, so the baseline never sees the year it predicts.
    - Filters: the block 1 quality filter, the same one the harmonized dataset uses (`keep` in
      quality_flags.parquet: no low confidence, no static sources, no volcano or offshore rows, no
      Easter Island or Malvinas/Falklands). docs/findings/01-quality.md.
    - Outages: a week with an outage day of the target satellite (outage_days.csv) is not observed,
      so it is neither scored nor used as "no fire".
    - Cells scored in year Y: cells with at least one reference detection before Y. The universe
      does not look at Y or later, so cells that burn for the first time in Y are not in the panel.
    - `last_day`: last complete day of the target satellite (rule 7 in docs/eda-plan.md), not of
      every satellite.

Run:
    python scripts/risk_baseline.py
    python scripts/risk_baseline.py --target all-viirs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HOTSPOTS = ROOT / "NASA_Data_Sources" / "processed" / "hotspots"
OUT = ROOT / "NASA_Data_Sources" / "processed" / "risk"
QUALITY = ROOT / "NASA_Data_Sources" / "processed" / "quality"
KEY = "satellite, acq_datetime, latitude, longitude"  # unique per hotspot, shared with the flags

CELL_DEG = 0.25
N_WEEKS = 52
# Same periods as scripts/harmonize.py (contract C2), so the calendar and the risk layer agree.
VIIRS_START = pd.Timestamp("2012-02-01")   # Suomi-NPP complete from February 2012
NOAA20_START = pd.Timestamp("2026-11-01")  # Suomi-NPP stopped on 2026-11-02


# ---------------------------------------------------------------- time keys

def week_index(dates: pd.Series) -> np.ndarray:
    """52 fixed 7-day bins. 29 February counts as 28 February; the last bin has 8 days."""
    doy = dates.dt.dayofyear.to_numpy()
    leap = dates.dt.is_leap_year.to_numpy()
    doy = np.where(leap & (doy >= 60), doy - 1, doy)  # 29 Feb (60) -> 59, later days shift back
    return np.minimum((doy - 1) // 7, N_WEEKS - 1)


def week_start(year: int, week: int) -> pd.Timestamp:
    """First `burn_date` of a week bin."""
    doy = week * 7 + 1  # day of year in a 365-day year
    if pd.Timestamp(year=year, month=1, day=1).is_leap_year and doy >= 60:
        doy += 1
    return pd.Timestamp(year=year, month=1, day=1) + pd.Timedelta(days=doy - 1)


def week_end(year: int, week: int) -> pd.Timestamp:
    """Last `burn_date` of a week bin."""
    if week == N_WEEKS - 1:
        return pd.Timestamp(year=year, month=12, day=31)
    return week_start(year, week + 1) - pd.Timedelta(days=1)


# ---------------------------------------------------------------- input

def load_detections(path: Path, quality: Path = QUALITY) -> pd.DataFrame:
    """VIIRS detections that pass the block 1 quality filter (same rows as the harmonized dataset)."""
    import duckdb

    flags = quality / "quality_flags.parquet"
    if not flags.exists():
        raise SystemExit(f"{flags} not found. Run notebooks/01_quality.ipynb to create it.")
    con = duckdb.connect()
    con.execute("SET TimeZone='UTC'")
    table = f"read_parquet('{path.as_posix()}/*/*.parquet', hive_partitioning=true)"
    columns = con.execute(f"DESCRIBE SELECT * FROM {table}").df()["column_name"].tolist()
    if "burn_date" not in columns:
        raise SystemExit("The hotspot table has no burn_date: rebuild it with scripts/build_hotspots.py")
    unflagged = con.execute(f"""
        SELECT count(*) FROM {table} t ANTI JOIN read_parquet('{flags.as_posix()}') q USING ({KEY})
        WHERE t.instrument = 'VIIRS'
    """).fetchone()[0]
    if unflagged:
        raise SystemExit(f"{unflagged:,} VIIRS hotspots have no quality flag: the flags are older than "
                         "the table. Re-run notebooks/01_quality.ipynb.")
    n0, df = con.execute(f"""
        SELECT count(*) OVER () AS n0, t.burn_date, t.latitude, t.longitude, t.satellite, q.keep
        FROM {table} t JOIN read_parquet('{flags.as_posix()}') q USING ({KEY})
        WHERE t.instrument = 'VIIRS'
    """).df().pipe(lambda d: (int(d["n0"].iloc[0]) if len(d) else 0, d))
    df = df[df["keep"].fillna(False).to_numpy()].drop(columns=["n0", "keep"])
    print(f"VIIRS rows read: {n0:,} | kept by the block 1 filter: {len(df):,}")
    df["burn_date"] = pd.to_datetime(df["burn_date"])
    df["satellite"] = df["satellite"].astype("object")
    return df.reset_index(drop=True)


def load_outages(quality: Path = QUALITY) -> pd.DataFrame:
    """Outage runs (satellite, start, end) from block 1, as burn_date ranges. Empty if missing."""
    path = quality / "outage_days.csv"
    if not path.exists():
        print(f"No {path.name}: outages are not masked.")
        return pd.DataFrame(columns=["satellite", "start", "end"])
    out = pd.read_csv(path, parse_dates=["start", "end"])
    return out[["satellite", "start", "end"]]


def select_target_rows(df: pd.DataFrame, target: str):
    """Rows that define the target, first covered day, switch day and last complete day.

    `last_day` comes from the satellites of the target only (rule 7 in docs/eda-plan.md).
    """
    snpp = df[df["satellite"] == "Suomi-NPP"]
    if snpp.empty:
        raise SystemExit("No Suomi-NPP rows: the reference series cannot be built.")
    first_day = max(snpp["burn_date"].min(), VIIRS_START)
    switch = NOAA20_START
    df = df[df["burn_date"] >= first_day]
    if target == "all-viirs":
        ends = df.groupby("satellite")["burn_date"].max()
        active = ends[ends >= ends.max() - pd.Timedelta(days=30)]  # satellites still delivering
        return df, first_day, switch, active.min() - pd.Timedelta(days=1)
    keep = ((df["satellite"] == "Suomi-NPP") & (df["burn_date"] < switch)) | (
        (df["satellite"] == "NOAA-20") & (df["burn_date"] >= switch)
    )
    rows = df[keep.to_numpy()]
    return rows, first_day, switch, rows["burn_date"].max() - pd.Timedelta(days=1)


# ---------------------------------------------------------------- panel

def build_panel(rows: pd.DataFrame, years: np.ndarray, cells: pd.DataFrame) -> np.ndarray:
    """Boolean array fire[cell, year, week]."""
    fire = np.zeros((len(cells), len(years), N_WEEKS), dtype=bool)
    key = rows[["cell_lat", "cell_lon"]].merge(
        cells.reset_index(), on=["cell_lat", "cell_lon"], how="left"
    )["cell_id"].to_numpy(dtype="float64")
    y = rows["burn_date"].dt.year.to_numpy() - years[0]
    w = week_index(rows["burn_date"])
    ok = (y >= 0) & (y < len(years)) & ~np.isnan(key)  # rows outside the cell universe are ignored
    fire[key[ok].astype(np.int64), y[ok], w[ok]] = True
    return fire


def observed_weeks(years: np.ndarray, first_day: pd.Timestamp, last_day: pd.Timestamp,
                   outage_days: set | None = None) -> np.ndarray:
    """avail[year, week]: True when the whole week lies inside the covered period and has no
    outage day of the target satellite."""
    outage_days = outage_days or set()
    avail = np.zeros((len(years), N_WEEKS), dtype=bool)
    for i, yr in enumerate(years):
        for w in range(N_WEEKS):
            s, e = week_start(yr, w), week_end(yr, w)
            avail[i, w] = s >= first_day and e <= last_day and not any(
                d in outage_days for d in pd.date_range(s, e))
    return avail


def target_outage_days(outages: pd.DataFrame, target: str, switch: pd.Timestamp) -> set:
    """Days when the satellite that defines the target was out (reference series only)."""
    if target != "reference" or outages.empty:
        return set()
    days = set()
    for r in outages.itertuples():
        for d in pd.date_range(r.start, r.end):
            if (r.satellite == "Suomi-NPP" and d < switch) or (r.satellite == "NOAA-20" and d >= switch):
                days.add(d)
    return days


def baseline_for_year(fire: np.ndarray, avail: np.ndarray, i: int, window: int, shrink: float) -> np.ndarray:
    """Baseline probability[cell, week] for year index i, from years 0..i-1 only.

    Weeks are laid end to end (t = year * 52 + week), so the window of week 0 reaches week 51 of the
    year before. Source weeks at or after the start of year i are never read.
    """
    n_cells, T = fire.shape[0], i * N_WEEKS
    f = (fire[:, :i, :] & avail[None, :i, :]).reshape(n_cells, T).astype("float32")
    a = avail[:i, :].reshape(T).astype("float32")
    k = np.zeros((n_cells, N_WEEKS))
    n = np.zeros(N_WEEKS)
    for d in range(-window, window + 1):
        fs, as_ = np.zeros_like(f), np.zeros_like(a)
        if d >= 0:
            fs[:, :T - d], as_[:T - d] = f[:, d:], a[d:]
        else:
            fs[:, -d:], as_[-d:] = f[:, :T + d], a[:T + d]
        k += fs.reshape(n_cells, i, N_WEEKS).sum(axis=1)
        n += as_.reshape(i, N_WEEKS).sum(axis=0)
    total_obs = a.sum()
    prior = f.sum(axis=1) / total_obs if total_obs else np.zeros(n_cells)
    return (k + shrink * prior[:, None]) / (n[None, :] + shrink)


def eligible_cells(fire: np.ndarray, avail: np.ndarray, i: int) -> np.ndarray:
    """Cells with at least one observed reference detection before year index i."""
    return (fire[:, :i, :] & avail[None, :i, :]).any(axis=(1, 2))


# ---------------------------------------------------------------- metrics

def average_precision(y: np.ndarray, p: np.ndarray) -> float:
    if y.sum() == 0:
        return float("nan")
    order = np.argsort(-p, kind="mergesort")
    y_sorted = y[order]
    hits = np.cumsum(y_sorted)
    precision = hits / np.arange(1, len(y) + 1)
    return float((precision * y_sorted).sum() / y.sum())


def roc_auc(y: np.ndarray, p: np.ndarray) -> float:
    pos, neg = y.sum(), len(y) - y.sum()
    if pos == 0 or neg == 0:
        return float("nan")
    ranks = pd.Series(p).rank(method="average").to_numpy()
    return float((ranks[y == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))


def evaluate(y: np.ndarray, p: np.ndarray) -> dict:
    base_rate = y.mean()
    brier = float(((p - y) ** 2).mean())
    brier_ref = float(((base_rate - y) ** 2).mean())
    return {
        "rows": int(len(y)),
        "positive_rate": float(base_rate),
        "brier": brier,
        "brier_skill_vs_constant": float(1 - brier / brier_ref) if brier_ref else float("nan"),
        "average_precision": average_precision(y, p),
        "roc_auc": roc_auc(y, p),
    }


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hotspots", type=Path, default=HOTSPOTS)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--target", choices=["reference", "all-viirs"], default="reference")
    ap.add_argument("--quality", type=Path, default=QUALITY, help="folder with the block 1 quality files")
    ap.add_argument("--min-years", type=int, default=4, help="past years needed before a year is scored")
    ap.add_argument("--window", type=int, default=1, help="neighbouring weeks on each side")
    ap.add_argument("--shrink", type=float, default=3.0, help="pseudo-observations towards the cell rate")
    ap.add_argument("--horizon-weeks", type=int, default=8, help="weeks to forecast after the data end")
    args = ap.parse_args()

    df = load_detections(args.hotspots, args.quality)
    if df.empty:
        raise SystemExit("No VIIRS detections left after filters.")
    df["cell_lat"] = np.floor(df["latitude"] / CELL_DEG) * CELL_DEG
    df["cell_lon"] = np.floor(df["longitude"] / CELL_DEG) * CELL_DEG

    rows, first_day, switch, last_day = select_target_rows(df, args.target)
    print(f"Target: {args.target} | covered {first_day.date()} to {last_day.date()} | "
          f"S-NPP -> NOAA-20 switch on {switch.date()}")

    # The forecast horizon can reach into the next calendar year.
    future = [last_day + pd.Timedelta(days=7 * h) for h in range(1, args.horizon_weeks + 1)]
    years = np.arange(first_day.year, max(d.year for d in future) + 1)
    # Every VIIRS cell, so any satellite's rows map to a cell; scoring uses eligible_cells().
    cells = (df[["cell_lat", "cell_lon"]].drop_duplicates()
             .sort_values(["cell_lat", "cell_lon"]).reset_index(drop=True))
    cells.index.name = "cell_id"
    fire = build_panel(rows, years, cells)
    outage_days = target_outage_days(load_outages(args.quality), args.target, switch)
    avail = observed_weeks(years, first_day, last_day, outage_days)
    print(f"Outage days of the target satellite: {len(outage_days)} | weeks not observed because of them: "
          f"{sum(1 for i, y in enumerate(years) for w in range(N_WEEKS) if not avail[i, w] and week_start(y, w) >= first_day and week_end(y, w) <= last_day)}")
    print(f"Cells with any VIIRS detection: {len(cells):,} | years {years[0]}-{years[-1]}")
    obs = fire[:, avail]
    print(f"Observed cell-weeks: {obs.size:,} | with fire: {obs.mean():.2%} | without fire: {1 - obs.mean():.2%}")

    if args.target == "reference":
        # How different is NOAA-20 from Suomi-NPP where both flew? (diagnostic for the team)
        both = df[df["satellite"].isin(["Suomi-NPP", "NOAA-20"]) & (df["burn_date"] < switch)]
        overlap_start = both.loc[both["satellite"] == "NOAA-20", "burn_date"].min()
        if pd.notna(overlap_start):
            both = both[both["burn_date"] >= overlap_start]
            per_sat = {s: build_panel(both[both["satellite"] == s], years, cells)
                       for s in ["Suomi-NPP", "NOAA-20"]}
            win = avail & np.array([[week_start(y, w) >= overlap_start and week_end(y, w) < switch
                                     for w in range(N_WEEKS)] for y in years])
            a, b = per_sat["Suomi-NPP"][:, win], per_sat["NOAA-20"][:, win]
            print(f"Overlap {overlap_start.date()} to {switch.date()}: fire cell-weeks "
                  f"S-NPP {a.sum():,}, NOAA-20 {b.sum():,} (ratio {b.sum() / max(a.sum(), 1):.2f}); "
                  f"agreement {(a == b).mean():.2%}")

    # Score every year with enough history; also produce the current year and the horizon.
    out_rows, metrics = [], {}
    pooled_y, pooled_p = [], []
    for i, yr in enumerate(years):
        if i < args.min_years:
            continue
        prob = baseline_for_year(fire, avail, i, args.window, args.shrink)
        keep = eligible_cells(fire, avail, i)  # cells with history before this year only
        if not keep.any():
            continue
        # Observed weeks, plus the forecast: the current partial week and the next ones.
        weeks = [w for w in range(N_WEEKS)
                 if avail[i, w] or (week_end(yr, w) > last_day and week_start(yr, w) <= future[-1])]
        if not weeks:
            continue
        observed = np.where(avail[i, weeks][None, :], fire[keep][:, i, weeks], np.nan)
        starts = np.array([week_start(yr, w) for w in weeks], dtype="datetime64[D]")
        n_keep = int(keep.sum())
        out_rows.append(pd.DataFrame({
            "week_start": np.tile(starts, n_keep),
            "cell_lat": np.repeat(cells["cell_lat"].to_numpy()[keep], len(weeks)),
            "cell_lon": np.repeat(cells["cell_lon"].to_numpy()[keep], len(weeks)),
            "baseline_probability": prob[keep][:, weeks].astype("float32").ravel(),
            "observed": observed.ravel(),
        }))
        scored = avail[i, :]
        if scored.any():
            y_true = fire[keep][:, i, scored].ravel().astype(int)
            p_pred = prob[keep][:, scored].ravel()
            metrics[str(yr)] = evaluate(y_true, p_pred)
            pooled_y.append(y_true)
            pooled_p.append(p_pred)

    if not out_rows:
        raise SystemExit("Not enough years to score. Lower --min-years or add data.")
    result = pd.concat(out_rows, ignore_index=True)
    result["probability"] = result["baseline_probability"]
    result["observed"] = result["observed"].astype("Int8")
    result["week_start"] = pd.to_datetime(result["week_start"]).dt.date
    metrics["all_scored_years"] = evaluate(np.concatenate(pooled_y), np.concatenate(pooled_p))
    metrics["settings"] = {
        "target": args.target, "quality_filter": "block 1 keep", "min_years": args.min_years,
        "window": args.window, "shrink": args.shrink, "cell_deg": CELL_DEG,
        "first_day": str(first_day.date()), "last_day": str(last_day.date()),
        "switch_day": str(switch.date()),
    }

    args.out.mkdir(parents=True, exist_ok=True)
    c3 = ["week_start", "cell_lat", "cell_lon", "probability", "baseline_probability"]
    result[c3].to_parquet(args.out / "cells_weekly.parquet", index=False)
    result[c3 + ["observed"]].to_parquet(args.out / "baseline_eval.parquet", index=False)
    (args.out / "baseline_metrics.json").write_text(json.dumps(metrics, indent=2))

    print(f"Wrote {len(result):,} rows to {args.out / 'cells_weekly.parquet'}")
    table = pd.DataFrame({k: v for k, v in metrics.items() if k != "settings"}).T
    print(table[["positive_rate", "brier", "brier_skill_vs_constant", "average_precision", "roc_auc"]]
          .round(4).to_string())


if __name__ == "__main__":
    main()
