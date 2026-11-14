"""Baseline risk layer: historical probability of fire activity per 0.25 degree cell and week.

This is the reference the risk model (block 8, module M5) has to beat. It also gives the web app a
real risk layer before the model exists.

Input:
    NASA_Data_Sources/processed/hotspots/    unified table from scripts/build_hotspots.py

Outputs (NASA_Data_Sources/processed/risk/):
    cells_weekly.parquet       contract C3: week_start, cell_lat, cell_lon, probability,
                               baseline_probability. Until the model exists, probability is the
                               baseline. Rows cover the evaluation years, the rest of the current
                               year and a few weeks ahead.
    baseline_eval.parquet      the same rows plus `observed` (1 fire, 0 no fire, null not observed
                               yet), for notebooks.
    baseline_metrics.json      Brier score, average precision and ROC AUC per test year.

Definitions (see docs/eda-plan.md):
    - Day key `burn_date`: day from 06:00 to 06:00 local solar time, date(UTC + longitude/15 h - 6 h).
      Taken from the table when the column exists, computed here otherwise (same formula).
    - Week: 52 fixed 7-day bins per year. 29 February is merged into 28 February and the last bin
      takes the remaining day (8 days). `week_start` is the first `burn_date` of the bin.
    - Cell: 0.25 degree, identified by its south-west corner.
    - Target: at least one VIIRS detection in the cell during the week. VIIRS only (2012 onward),
      so the target does not depend on the MODIS harmonisation.
    - Reference series (default): Suomi-NPP from 2012-02-01 to 2026-10-31, NOAA-20 from 2026-11-01,
      the same periods as scripts/harmonize.py. Counting every VIIRS
      satellite would make the target depend on how many satellites flew each year (1, 2, 3, then 2),
      so a model could learn the satellite count as if it were fire. Use --target all-viirs to compare.
    - Baseline for year Y, cell c and week w: share of earlier years (Y-1 back to the first year)
      with fire in c during weeks w-1, w or w+1, shrunk towards the cell's average weekly rate.
      Only years before Y are used, so the baseline never sees the year it predicts.

Run:
    python scripts/risk_baseline.py
    python scripts/risk_baseline.py --target all-viirs --drop-low
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

CELL_DEG = 0.25
N_WEEKS = 52
# Same periods as scripts/harmonize.py (contract C2), so the calendar and the risk layer agree.
VIIRS_START = pd.Timestamp("2012-02-01")   # Suomi-NPP complete from February 2012
NOAA20_START = pd.Timestamp("2026-11-01")  # Suomi-NPP stopped on 2026-11-02
COUNTRIES = ("Chile", "Argentina")
STATIC_FIRE_TYPES = (1, 2, 3)  # volcano, other static land source, offshore
READ_COLS = [
    "acq_datetime", "latitude", "longitude", "country", "instrument", "satellite",
    "confidence_level", "fire_type",
]


# ---------------------------------------------------------------- time keys

def add_burn_date(df: pd.DataFrame) -> pd.DataFrame:
    """Add `burn_date` (datetime64, midnight) when the table does not have it yet."""
    if "burn_date" in df:
        df["burn_date"] = pd.to_datetime(df["burn_date"])
        return df
    t = pd.to_datetime(df["acq_datetime"], utc=True)
    shift = pd.to_timedelta(df["longitude"].to_numpy() / 15.0 * 3600.0 - 6 * 3600.0, unit="s")
    df["burn_date"] = (t + shift).dt.tz_localize(None).dt.floor("D")
    return df


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

def load_detections(path: Path, drop_low: bool) -> pd.DataFrame:
    df = pd.read_parquet(path, columns=READ_COLS, filters=[("instrument", "==", "VIIRS")])
    n0 = len(df)
    df = df[df["country"].astype("object").isin(COUNTRIES)]
    fire_type = df["fire_type"].astype("Int8")
    df = df[~fire_type.isin(STATIC_FIRE_TYPES).fillna(False).to_numpy()]
    if drop_low:
        df = df[df["confidence_level"].astype("object") != "low"]
    # Outside the analysis (docs/eda-plan.md): Easter Island and Malvinas/Falklands.
    lon, lat = df["longitude"], df["latitude"]
    outside = (lon < -100) | ((lon > -62) & (lat < -50))
    df = df[~outside.to_numpy()].copy()
    print(f"VIIRS rows read: {n0:,} | kept after filters: {len(df):,}")
    df = add_burn_date(df)
    df["satellite"] = df["satellite"].astype("object")
    return df


def select_target_rows(df: pd.DataFrame, target: str) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    """Return the rows that define the target, the first covered day and the switch date."""
    snpp = df[df["satellite"] == "Suomi-NPP"]
    if snpp.empty:
        raise SystemExit("No Suomi-NPP rows: the reference series cannot be built.")
    first_day = max(snpp["burn_date"].min(), VIIRS_START)
    switch = NOAA20_START
    df = df[df["burn_date"] >= first_day]
    if target == "all-viirs":
        return df, first_day, switch
    keep = ((df["satellite"] == "Suomi-NPP") & (df["burn_date"] < switch)) | (
        (df["satellite"] == "NOAA-20") & (df["burn_date"] >= switch)
    )
    return df[keep.to_numpy()], first_day, switch


# ---------------------------------------------------------------- panel

def build_panel(rows: pd.DataFrame, years: np.ndarray, cells: pd.DataFrame) -> np.ndarray:
    """Boolean array fire[cell, year, week]."""
    fire = np.zeros((len(cells), len(years), N_WEEKS), dtype=bool)
    key = rows[["cell_lat", "cell_lon"]].merge(
        cells.reset_index(), on=["cell_lat", "cell_lon"], how="left"
    )["cell_id"].to_numpy()
    y = rows["burn_date"].dt.year.to_numpy() - years[0]
    w = week_index(rows["burn_date"])
    ok = (y >= 0) & (y < len(years))
    fire[key[ok], y[ok], w[ok]] = True
    return fire


def observed_weeks(years: np.ndarray, first_day: pd.Timestamp, last_day: pd.Timestamp) -> np.ndarray:
    """avail[year, week]: True when the whole week lies inside the covered period."""
    avail = np.zeros((len(years), N_WEEKS), dtype=bool)
    for i, yr in enumerate(years):
        for w in range(N_WEEKS):
            avail[i, w] = week_start(yr, w) >= first_day and week_end(yr, w) <= last_day
    return avail


def baseline_for_year(fire: np.ndarray, avail: np.ndarray, i: int, window: int, shrink: float) -> np.ndarray:
    """Baseline probability[cell, week] for year index i, from years 0..i-1 only."""
    past_fire = fire[:, :i, :] & avail[None, :i, :]
    past_avail = avail[:i, :]
    k = np.zeros((fire.shape[0], N_WEEKS))
    n = np.zeros(N_WEEKS)
    for d in range(-window, window + 1):  # neighbouring weeks, wrapping around the year
        k += np.roll(past_fire.sum(axis=1), -d, axis=1)
        n += np.roll(past_avail.sum(axis=0), -d)
    total_obs = past_avail.sum()
    prior = past_fire.sum(axis=(1, 2)) / total_obs if total_obs else np.zeros(fire.shape[0])
    return (k + shrink * prior[:, None]) / (n[None, :] + shrink)


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
    ap.add_argument("--drop-low", action="store_true", help="drop low-confidence detections")
    ap.add_argument("--min-years", type=int, default=4, help="past years needed before a year is scored")
    ap.add_argument("--window", type=int, default=1, help="neighbouring weeks on each side")
    ap.add_argument("--shrink", type=float, default=3.0, help="pseudo-observations towards the cell rate")
    ap.add_argument("--horizon-weeks", type=int, default=8, help="weeks to forecast after the data end")
    args = ap.parse_args()

    df = load_detections(args.hotspots, args.drop_low)
    if df.empty:
        raise SystemExit("No VIIRS detections left after filters.")
    df["cell_lat"] = np.floor(df["latitude"] / CELL_DEG) * CELL_DEG
    df["cell_lon"] = np.floor(df["longitude"] / CELL_DEG) * CELL_DEG

    rows, first_day, switch = select_target_rows(df, args.target)
    last_day = df["burn_date"].max() - pd.Timedelta(days=1)  # the newest day is partial
    print(f"Target: {args.target} | covered {first_day.date()} to {last_day.date()} | "
          f"S-NPP -> NOAA-20 switch on {switch.date()}")

    # The forecast horizon can reach into the next calendar year.
    future = [last_day + pd.Timedelta(days=7 * h) for h in range(1, args.horizon_weeks + 1)]
    years = np.arange(first_day.year, max(d.year for d in future) + 1)
    cells = (rows[["cell_lat", "cell_lon"]].drop_duplicates()
             .sort_values(["cell_lat", "cell_lon"]).reset_index(drop=True))
    cells.index.name = "cell_id"
    fire = build_panel(rows, years, cells)
    avail = observed_weeks(years, first_day, last_day)
    print(f"Cells with any detection: {len(cells):,} | years {years[0]}-{years[-1]}")
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
        # Observed weeks, plus the forecast: the current partial week and the next ones.
        weeks = [w for w in range(N_WEEKS)
                 if avail[i, w] or (week_end(yr, w) > last_day and week_start(yr, w) <= future[-1])]
        if not weeks:
            continue
        observed = np.where(avail[i, weeks][None, :], fire[:, i, weeks], np.nan)
        starts = np.array([week_start(yr, w) for w in weeks], dtype="datetime64[D]")
        out_rows.append(pd.DataFrame({
            "week_start": np.tile(starts, len(cells)),
            "cell_lat": np.repeat(cells["cell_lat"].to_numpy(), len(weeks)),
            "cell_lon": np.repeat(cells["cell_lon"].to_numpy(), len(weeks)),
            "baseline_probability": prob[:, weeks].astype("float32").ravel(),
            "observed": observed.ravel(),
        }))
        scored = avail[i, :]
        if scored.any():
            y_true = fire[:, i, scored].ravel().astype(int)
            p_pred = prob[:, scored].ravel()
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
        "target": args.target, "drop_low": args.drop_low, "min_years": args.min_years,
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
