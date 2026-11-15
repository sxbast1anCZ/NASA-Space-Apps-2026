"""Daily panel for the next-day outlook: one row per 0.25 degree cell and predicted day (card 1 of
docs/modeling-plan.md, section 0).

"Fire" on a day means at least one VIIRS hotspot of the target satellite in the cell on that
`burn_date`. It is a thermal detection, not an ignition and not burned area. The outlook says where
fire activity is most likely tomorrow; it does not predict where a fire will start.

Inputs (NASA_Data_Sources/processed/):
    harmonized/hotspots_kept.parquet    hotspots that pass the block 1 quality filter
    quality/outage_days.csv             outages per satellite (burn_date ranges)

Outputs (NASA_Data_Sources/processed/):
    risk/cells_daily.parquet    the file every lane meets at, written here with the baselines:
                                burn_date, cell_lat, cell_lon, probability (= p_hist until a model
                                replaces it), baseline_probability (= p_hist), alert (= p_near: the
                                cell or one of its 8 neighbours had fire the day before; 0 when that
                                day was not observed). Rows: predicted days 2023-2025 and the day
                                after the last complete day.
    daily/panel.parquet         predicted days 2014-2025, columns of section 4.1 of the plan:
                                burn_date, cell_lat, cell_lon, country, admin1, segment, season_label,
                                split, fire, new_cell, p_hist, p_persist, p_near, then the features
                                (prefixes lag_, nbr_, hist_, cal_, geo_).
    daily/live.parquet          the same columns for the day after the last complete day, with
                                split = "live" and no target (fire is null), for the live outlook.
    daily/panel_summary.json    row counts, the check against section 3 and the baseline scores.

Definitions:
    - Day D is the last day known when the prediction is made; the predicted day is D+1 (the row's
      `burn_date`). Every feature reads days up to D only (tests/test_daily_panel.py checks it).
    - Target satellite: Suomi-NPP from 2012-02-01 to 2026-10-31, NOAA-20 from 2026-11-01 (the
      periods of scripts/harmonize.py and scripts/risk_baseline.py). Never both on one day.
    - Cell: floor(coordinate / 0.25) * 0.25, the south-west corner. The country and `admin1` of a
      cell are those of most of its target hotspots.
    - Outage days of the target satellite are not observed: no row predicts them, and a single-day
      lag that falls on one is missing (NaN), not 0. Window counts (fire-days in 7 or 30 days) count
      the observed days only and are missing when no day of the window was observed.
    - Cells scored in year Y: cells with at least one observed target detection before Y.
    - Splits: train 2014-2020, tune 2021-2022, test 2023-2025. The first 7 predicted days of 2021
      and of 2023 are `gap` (section 5 of the plan: one fire must not sit in two splits). They are
      in the panel, so the app can show them, but no split reads them.
    - Segment: CL or AR, then PV (September to February) or OI (March to August), from the month of
      the predicted day. `season_label` names a PV season by the year it starts ("PV 2023/24").

Features (section 4.2 of the plan; weather and population are not added yet):
    lag_fire_d0 .. lag_fire_d6   fire in the cell on D, D-1 .. D-6 (NaN on an outage day)
    lag_fire_days_7, _30         fire-days of the cell in the 7 and 30 days ending on D
    lag_days_since_fire          days from the last fire of the cell to D, capped at 365
    lag_hotspots_d0              hotspots of the cell on D
    lag_frp_sum_d0, _max_d0      summed and maximum FRP (MW) of the cell on D
    lag_night_d0                 1 if a night pass detected fire in the cell on D
    nbr_fire_d0                  of the 8 neighbours, how many had fire on D
    nbr_hotspots_d0              hotspots of the 8 neighbours on D
    nbr_ring2_fire_d0            of the 16 cells of the next ring, how many had fire on D
    nbr_fire_days_7              fire-days of the 8 neighbours in the 7 days ending on D, summed
    hist_doy_rate                fire rate of the cell for that day of the year, 7 days on each side,
                                 every earlier year (never the year predicted), shrunk towards the
                                 cell's overall rate with 15 pseudo-days (one year of the window)
    hist_cell_rate               overall fire rate of the cell in earlier years
    cal_dow                      day of the week of the predicted day (0 = Monday)
    cal_month, cal_doy_sin, cal_doy_cos   calendar of the predicted day. The default model leaves
                                 them out; the comparison run of the plan uses them
    geo_lat, geo_lon             south-west corner of the cell

Baselines (section 4.3): p_hist = hist_doy_rate; p_persist = lag_fire_d0; p_near = 1 if the cell or
one of its 8 neighbours had fire on D. new_cell = 1 - p_near. All three are missing when D was not
observed.

Run:
    python scripts/daily_panel.py
    python scripts/daily_panel.py --baseline-only    # risk/cells_daily.parquet only (fast)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from risk_baseline import CELL_DEG, NOAA20_START, VIIRS_START, load_outages, target_outage_days
from risk_model import neighbour_ids

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "NASA_Data_Sources" / "processed"
KEPT = DATA / "harmonized" / "hotspots_kept.parquet"
QUALITY = DATA / "quality"

FIRST_YEAR, LAST_YEAR = 2014, 2025          # predicted days in the panel
TRAIN_UNTIL, TUNE_UNTIL = 2020, 2022
GAP_YEARS, GAP_DAYS = (2021, 2023), 7       # first predicted days of tune and test left out of the splits
APP_FROM = 2023                             # risk/cells_daily.parquet: predicted days from this year on
HIST_WINDOW, HIST_SHRINK = 7, 15.0
DAYS_SINCE_CAP = 365
COUNTRY_CODE = {"Chile": "CL", "Argentina": "AR"}

# Fire cell-days per segment in section 3 of the plan (Suomi-NPP, kept rows, burn_date 2013-2025).
SECTION3 = {"CL-PV": 29_930, "CL-OI": 33_563, "AR-PV": 265_854, "AR-OI": 268_590}

LAG_COLS = [f"lag_fire_d{k}" for k in range(7)] + [
    "lag_fire_days_7", "lag_fire_days_30", "lag_days_since_fire", "lag_hotspots_d0",
    "lag_frp_sum_d0", "lag_frp_max_d0", "lag_night_d0"]
NBR_COLS = ["nbr_fire_d0", "nbr_hotspots_d0", "nbr_ring2_fire_d0", "nbr_fire_days_7"]
HIST_COLS = ["hist_doy_rate", "hist_cell_rate"]
CAL_COLS = ["cal_dow", "cal_month", "cal_doy_sin", "cal_doy_cos"]
GEO_COLS = ["geo_lat", "geo_lon"]
FEATURES = LAG_COLS + NBR_COLS + HIST_COLS + CAL_COLS + GEO_COLS
ID_COLS = ["burn_date", "cell_lat", "cell_lon", "country", "admin1", "segment", "season_label", "split",
           "fire", "new_cell", "p_hist", "p_persist", "p_near"]
CONTRACT = ["burn_date", "cell_lat", "cell_lon", "probability", "baseline_probability", "alert"]


# ---------------------------------------------------------------- input

def load_cell_days(path: Path = KEPT) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Target hotspots per cell and burn_date, and the country and region of each cell.

    Target: Suomi-NPP from VIIRS_START to the day before NOAA20_START, NOAA-20 from NOAA20_START.
    """
    import duckdb

    if not path.exists():
        raise SystemExit(f"{path} not found. Build it with scripts/harmonize.py (docs/eda-runbook.md).")
    con = duckdb.connect()
    target = f"""
        SELECT burn_date, latitude, longitude, frp_mw, daynight, country, admin1,
               floor(latitude / {CELL_DEG}) * {CELL_DEG} AS cell_lat,
               floor(longitude / {CELL_DEG}) * {CELL_DEG} AS cell_lon
        FROM read_parquet('{path.as_posix()}')
        WHERE (satellite = 'Suomi-NPP' AND burn_date >= DATE '{VIIRS_START.date()}'
                                       AND burn_date <  DATE '{NOAA20_START.date()}')
           OR (satellite = 'NOAA-20'   AND burn_date >= DATE '{NOAA20_START.date()}')
    """
    days = con.execute(f"""
        SELECT burn_date, cell_lat, cell_lon, count(*)::INTEGER AS hotspots,
               coalesce(sum(frp_mw), 0)::FLOAT AS frp_sum, coalesce(max(frp_mw), 0)::FLOAT AS frp_max,
               bool_or(daynight = 'N') AS night
        FROM ({target}) GROUP BY ALL
    """).df()
    cells = con.execute(f"""
        WITH t AS ({target}),
        c AS (SELECT cell_lat, cell_lon, country, count(*) AS n FROM t GROUP BY ALL),
        a AS (SELECT cell_lat, cell_lon, country, admin1, count(*) AS n FROM t GROUP BY ALL)
        SELECT c.cell_lat, c.cell_lon, c.country,
               (SELECT arg_max(a.admin1, a.n) FROM a WHERE a.cell_lat = c.cell_lat
                  AND a.cell_lon = c.cell_lon AND a.country = c.country) AS admin1
        FROM c QUALIFY row_number() OVER (PARTITION BY c.cell_lat, c.cell_lon ORDER BY c.n DESC, c.country) = 1
        ORDER BY c.cell_lat, c.cell_lon
    """).df()
    days["burn_date"] = pd.to_datetime(days["burn_date"])
    return days, cells.reset_index(drop=True)


# ---------------------------------------------------------------- arrays on (cell, day)

def build_grid(days_df: pd.DataFrame, cells: pd.DataFrame, days: pd.DatetimeIndex) -> dict[str, np.ndarray]:
    """Arrays [cell, day] of fire, hotspots, summed and maximum FRP and night detection."""
    index = {(round(a, 4), round(b, 4)): i for i, (a, b) in enumerate(zip(cells["cell_lat"], cells["cell_lon"]))}
    c = np.array([index.get((round(a, 4), round(b, 4)), -1)
                  for a, b in zip(days_df["cell_lat"], days_df["cell_lon"])], dtype=np.int64)
    t = days.get_indexer(days_df["burn_date"])
    ok = (c >= 0) & (t >= 0)
    c, t, d = c[ok], t[ok], days_df[ok]
    shape = (len(cells), len(days))
    grid = {"fire": np.zeros(shape, bool), "hotspots": np.zeros(shape, np.int32),
            "frp_sum": np.zeros(shape, np.float32), "frp_max": np.zeros(shape, np.float32),
            "night": np.zeros(shape, bool)}
    grid["fire"][c, t] = True
    grid["hotspots"][c, t] = d["hotspots"].to_numpy()
    grid["frp_sum"][c, t] = d["frp_sum"].to_numpy()
    grid["frp_max"][c, t] = d["frp_max"].to_numpy()
    grid["night"][c, t] = d["night"].fillna(False).to_numpy(bool)
    return grid


def observed_days(days: pd.DatetimeIndex, first_day, last_day, outage_days: set) -> np.ndarray:
    """True for a day inside the covered period on which the target satellite was not out."""
    out = pd.DatetimeIndex(sorted(outage_days)) if outage_days else pd.DatetimeIndex([])
    return np.asarray((days >= first_day) & (days <= last_day) & ~days.isin(out))


def ring2_ids(cells: pd.DataFrame) -> np.ndarray:
    """ids[cell, 16] of the cells two steps away (the ring around the 8 neighbours), -1 if absent."""
    index = {(round(a, 4), round(b, 4)): i for i, (a, b) in enumerate(zip(cells["cell_lat"], cells["cell_lon"]))}
    steps = [(dy, dx) for dy in range(-2, 3) for dx in range(-2, 3) if max(abs(dy), abs(dx)) == 2]
    ids = np.full((len(cells), len(steps)), -1, dtype=np.int64)
    for i, (a, b) in enumerate(zip(cells["cell_lat"], cells["cell_lon"])):
        for k, (dy, dx) in enumerate(steps):
            ids[i, k] = index.get((round(a + dy * CELL_DEG, 4), round(b + dx * CELL_DEG, 4)), -1)
    return ids


def _sum_over(values: np.ndarray, ids: np.ndarray) -> np.ndarray:
    """values[cell, n] summed over the cells in ids[cell, k]; -1 counts as 0."""
    padded = np.vstack([values, np.zeros((1, values.shape[1]), values.dtype)])
    return padded[ids].sum(axis=1)


def day_features(grid: dict, avail: np.ndarray, nbr1: np.ndarray, nbr2: np.ndarray,
                 t_pred: np.ndarray) -> dict[str, np.ndarray]:
    """lag_ and nbr_ features [cell, n] for predicted day indices t_pred. Reads days < t_pred only."""
    t_pred = np.asarray(t_pred, dtype=np.int64)
    D = t_pred - 1
    lo = max(int(D.min()) - DAYS_SINCE_CAP - 1, 0)
    hi = int(D.max()) + 1
    if hi > len(avail) or D.min() < 0:
        raise ValueError("predicted days need a previous day inside the grid")
    sub = {k: v[:, lo:hi] for k, v in grid.items()}       # nothing after the last D is in reach
    av = avail[lo:hi]
    Dl = D - lo
    n_cells = sub["fire"].shape[0]

    def on(arr: np.ndarray, t: np.ndarray) -> np.ndarray:
        ok = (t >= 0) & av[np.clip(t, 0, None)]
        v = arr[:, np.clip(t, 0, None)].astype(np.float32)
        v[:, ~ok] = np.nan
        return v

    out = {f"lag_fire_d{k}": on(sub["fire"], Dl - k) for k in range(7)}

    cf = np.zeros((n_cells, hi - lo + 1), np.int32)
    np.cumsum(sub["fire"], axis=1, dtype=np.int32, out=cf[:, 1:])
    ca = np.concatenate([[0], np.cumsum(av, dtype=np.int32)])
    windows = {}
    for w in (7, 30):
        start = np.clip(Dl + 1 - w, 0, None)
        count = (cf[:, Dl + 1] - cf[:, start]).astype(np.float32)
        count[:, (ca[Dl + 1] - ca[start]) == 0] = np.nan
        windows[w] = count
        out[f"lag_fire_days_{w}"] = count

    seen = np.where(sub["fire"], np.arange(hi - lo), -1)
    last = np.maximum.accumulate(seen, axis=1)[:, Dl]
    since = np.where(last >= 0, Dl[None, :] - last, DAYS_SINCE_CAP)
    out["lag_days_since_fire"] = np.minimum(since, DAYS_SINCE_CAP).astype(np.float32)

    out["lag_hotspots_d0"] = on(sub["hotspots"], Dl)
    out["lag_frp_sum_d0"] = on(sub["frp_sum"], Dl)
    out["lag_frp_max_d0"] = on(sub["frp_max"], Dl)
    out["lag_night_d0"] = on(sub["night"], Dl)

    d_ok = av[Dl]
    for name, arr, ids in (("nbr_fire_d0", sub["fire"], nbr1), ("nbr_hotspots_d0", sub["hotspots"], nbr1),
                           ("nbr_ring2_fire_d0", sub["fire"], nbr2)):
        v = _sum_over(arr[:, Dl].astype(np.float32), ids)
        v[:, ~d_ok] = np.nan
        out[name] = v
    w7 = windows[7]
    v = _sum_over(np.nan_to_num(w7), nbr1)
    v[:, np.isnan(w7).all(axis=0)] = np.nan
    out["nbr_fire_days_7"] = v
    return out


def year_start_index(days: pd.DatetimeIndex, year: int) -> int:
    return int(days.searchsorted(pd.Timestamp(year=year, month=1, day=1)))


def hist_features(fire: np.ndarray, avail: np.ndarray, days: pd.DatetimeIndex, year: int, t_pred: np.ndarray,
                  window: int = HIST_WINDOW, shrink: float = HIST_SHRINK) -> tuple[np.ndarray, np.ndarray]:
    """Historical rate [cell, n] for predicted days of `year`, and the cell rate [cell], from earlier years.

    For each earlier year, the same calendar date (29 February as 28 February) and `window` days on
    each side. The window may cross into the next year, but never reaches 1 January of `year`.
    """
    start = year_start_index(days, year)
    S = np.zeros((fire.shape[0], start + 1), np.int32)
    np.cumsum(fire[:, :start] & avail[None, :start], axis=1, dtype=np.int32, out=S[:, 1:])
    A = np.concatenate([[0], np.cumsum(avail[:start], dtype=np.int32)])
    prior = S[:, start] / A[start] if A[start] else np.zeros(fire.shape[0])
    years = list(range(days[0].year, year))
    if not years or start == 0:
        nan = np.full((fire.shape[0], len(t_pred)), np.nan, np.float32)
        return nan, np.full(fire.shape[0], np.nan, np.float32)
    lo = np.zeros((len(t_pred), len(years)), np.int64)
    hi = np.zeros_like(lo)
    for i, t in enumerate(t_pred):
        d = days[t]
        for j, y in enumerate(years):
            same = pd.Timestamp(year=y, month=d.month, day=28 if (d.month, d.day) == (2, 29) else d.day)
            c = (same - days[0]).days
            lo[i, j], hi[i, j] = c - window, c + window
    lo = np.clip(lo, 0, start)
    hi = np.clip(hi, -1, start - 1)
    hi = np.where(hi < lo, lo - 1, hi)                    # empty window
    k = (S[:, hi + 1] - S[:, lo]).sum(axis=2)
    n = (A[hi + 1] - A[lo]).sum(axis=1)
    rate = (k + shrink * prior[:, None]) / (n[None, :] + shrink)
    return rate.astype(np.float32), prior.astype(np.float32)


def eligible(fire: np.ndarray, avail: np.ndarray, days: pd.DatetimeIndex, year: int) -> np.ndarray:
    """Cells with at least one observed target detection before `year`."""
    start = year_start_index(days, year)
    return (fire[:, :start] & avail[None, :start]).any(axis=1)


# ---------------------------------------------------------------- rows

def split_of(dates: pd.Series) -> np.ndarray:
    y = dates.dt.year.to_numpy()
    split = np.where(y <= TRAIN_UNTIL, "train", np.where(y <= TUNE_UNTIL, "tune", "test")).astype(object)
    gap = np.isin(y, GAP_YEARS) & (dates.dt.dayofyear.to_numpy() <= GAP_DAYS)
    split[gap] = "gap"
    return split


def segment_of(country: pd.Series, month: pd.Series) -> pd.Series:
    season = np.where(month.isin([9, 10, 11, 12, 1, 2]), "PV", "OI")
    return country.map(COUNTRY_CODE).fillna("XX") + "-" + season


def season_label_of(dates: pd.Series) -> np.ndarray:
    y, m = dates.dt.year.to_numpy(), dates.dt.month.to_numpy()
    start = np.where(m <= 2, y - 1, y)
    names = {(s, oi): (f"OI {s}" if oi else f"PV {s}/{(s + 1) % 100:02d}")
             for s, oi in set(zip(start.tolist(), ((m >= 3) & (m <= 8)).tolist()))}
    return np.array([names[k] for k in zip(start.tolist(), ((m >= 3) & (m <= 8)).tolist())], dtype=object)


def frame_for_days(grid, avail, nbr1, nbr2, cells, days, year, t_pred, live: bool = False) -> pd.DataFrame:
    """Panel rows for the predicted day indices t_pred, all inside `year`, eligible cells only."""
    keep = eligible(grid["fire"], avail, days, year)
    ids = np.flatnonzero(keep)
    feats = day_features(grid, avail, nbr1, nbr2, t_pred)
    rate, prior = hist_features(grid["fire"], avail, days, year, t_pred)
    n, m = len(t_pred), len(ids)

    def flat(a: np.ndarray) -> np.ndarray:            # [cell, day] -> rows ordered by day, then cell
        return a[ids].T.ravel()

    dates = pd.Series(np.repeat(days[t_pred].to_numpy(), m))
    df = pd.DataFrame({
        "burn_date": dates.dt.date,
        "cell_lat": np.tile(cells["cell_lat"].to_numpy()[ids], n),
        "cell_lon": np.tile(cells["cell_lon"].to_numpy()[ids], n),
        "country": np.tile(cells["country"].to_numpy()[ids], n).astype(object),
        "admin1": np.tile(cells["admin1"].to_numpy()[ids], n).astype(object),
    })
    df["segment"] = segment_of(df["country"], dates.dt.month).to_numpy()
    df["season_label"] = season_label_of(dates)
    df["split"] = "live" if live else split_of(dates)
    df["fire"] = pd.array([pd.NA] * len(df), dtype="Int8") if live else flat(grid["fire"][:, t_pred]).astype(np.int8)
    persist = flat(feats["lag_fire_d0"])
    near = np.where(np.isnan(persist), np.nan, ((persist > 0) | (flat(feats["nbr_fire_d0"]) > 0)).astype(np.float32))
    df["new_cell"] = pd.array(np.where(np.isnan(near), np.nan, 1 - near), dtype="Float32").astype("Int8")
    df["p_hist"] = flat(rate)
    df["p_persist"] = persist
    df["p_near"] = near.astype(np.float32)
    for name in LAG_COLS + NBR_COLS:
        df[name] = flat(feats[name])
    df["hist_doy_rate"] = flat(rate)
    df["hist_cell_rate"] = np.tile(prior[ids], n)
    doy = dates.dt.dayofyear.to_numpy()
    df["cal_dow"] = dates.dt.dayofweek.to_numpy().astype(np.int8)
    df["cal_month"] = dates.dt.month.to_numpy().astype(np.int8)
    df["cal_doy_sin"] = np.sin(2 * np.pi * (doy - 1) / 365.25).astype(np.float32)
    df["cal_doy_cos"] = np.cos(2 * np.pi * (doy - 1) / 365.25).astype(np.float32)
    df["geo_lat"] = df["cell_lat"].astype(np.float32)
    df["geo_lon"] = df["cell_lon"].astype(np.float32)
    return df[ID_COLS + FEATURES]


def contract_rows(df: pd.DataFrame) -> pd.DataFrame:
    """The columns of risk/cells_daily.parquet, with the baselines in place of a model."""
    return pd.DataFrame({
        "burn_date": df["burn_date"], "cell_lat": df["cell_lat"], "cell_lon": df["cell_lon"],
        "probability": df["p_hist"].astype(np.float32), "baseline_probability": df["p_hist"].astype(np.float32),
        "alert": np.nan_to_num(df["p_near"].to_numpy()).astype(np.int8),
    })


# ---------------------------------------------------------------- checks

def section3_check(days_df: pd.DataFrame, cells: pd.DataFrame, outage_days: set) -> dict:
    """Fire cell-days per segment, Suomi-NPP 2013-2025, against section 3 of the plan."""
    d = days_df[(days_df["burn_date"].dt.year >= 2013) & (days_df["burn_date"].dt.year <= 2025)]
    d = d.merge(cells[["cell_lat", "cell_lon", "country"]], on=["cell_lat", "cell_lon"], how="left")
    d["segment"] = segment_of(d["country"], d["burn_date"].dt.month)
    all_days = d.groupby("segment").size()
    observed = d[~d["burn_date"].isin(pd.DatetimeIndex(sorted(outage_days)))].groupby("segment").size()
    return {s: {"plan": SECTION3[s], "all_days": int(all_days.get(s, 0)), "outage_days_removed": int(observed.get(s, 0))}
            for s in SECTION3}


class RuleTally:
    """Confusion counts of the yes/no baselines over every panel row, per split and in total."""

    def __init__(self):
        self.t: dict = {}

    def add(self, df: pd.DataFrame) -> None:
        y = df["fire"].to_numpy().astype(bool)
        for rule in ("p_persist", "p_near"):
            flag = np.nan_to_num(df[rule].to_numpy()) > 0.5
            for split in ("all", *df["split"].unique()):
                m = np.ones(len(df), bool) if split == "all" else (df["split"] == split).to_numpy()
                c = self.t.setdefault((rule, split), np.zeros(3, np.int64))
                c += [(flag & y & m).sum(), (flag & ~y & m).sum(), (~flag & y & m).sum()]

    def report(self) -> dict:
        out = {}
        for (rule, split), (tp, fp, fn) in sorted(self.t.items()):
            out.setdefault(rule, {})[split] = {
                "tp": int(tp), "fp": int(fp), "fn": int(fn),
                "recall": float(tp / (tp + fn)) if tp + fn else None,
                "precision": float(tp / (tp + fp)) if tp + fp else None}
        return out


# ---------------------------------------------------------------- main

def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kept", type=Path, default=KEPT)
    ap.add_argument("--quality", type=Path, default=QUALITY)
    ap.add_argument("--out", type=Path, default=DATA)
    ap.add_argument("--baseline-only", action="store_true", help="write risk/cells_daily.parquet only")
    args = ap.parse_args(argv)

    days_df, cells = load_cell_days(args.kept)
    first_day = max(days_df["burn_date"].min(), VIIRS_START)
    last_day = days_df["burn_date"].max() - pd.Timedelta(days=1)        # last complete day
    live_day = last_day + pd.Timedelta(days=1)
    days = pd.date_range(first_day, live_day, freq="D")
    outage_days = target_outage_days(load_outages(args.quality), "reference", NOAA20_START)
    avail = observed_days(days, first_day, last_day, outage_days)
    grid = build_grid(days_df, cells, days)
    nbr1, nbr2 = neighbour_ids(cells), ring2_ids(cells)
    print(f"Target cell-days: {len(days_df):,} | cells: {len(cells):,} | covered {first_day.date()} to "
          f"{last_day.date()} | outage days not observed: {int(((days <= last_day) & ~avail).sum())} | "
          f"live predicted day: {live_day.date()}")

    check = section3_check(days_df, cells, outage_days)
    print("Fire cell-days 2013-2025 against section 3 of the plan:")
    for s, v in check.items():
        flag = "ok" if v["all_days"] == v["plan"] else "DIFFERS"
        print(f"  {s}: plan {v['plan']:,} | here {v['all_days']:,} ({flag}) | without outage days "
              f"{v['outage_days_removed']:,}")

    daily_dir, risk_dir = args.out / "daily", args.out / "risk"
    daily_dir.mkdir(parents=True, exist_ok=True)
    risk_dir.mkdir(parents=True, exist_ok=True)

    live = frame_for_days(grid, avail, nbr1, nbr2, cells, days, live_day.year,
                          np.array([days.get_loc(live_day)]), live=True)
    years = range(APP_FROM if args.baseline_only else FIRST_YEAR, LAST_YEAR + 1)
    writer, app_parts, tally, counts = None, [], RuleTally(), {}
    for year in years:
        t_pred = np.flatnonzero(avail & (days.year == year))
        if not len(t_pred):
            continue
        df = frame_for_days(grid, avail, nbr1, nbr2, cells, days, year, t_pred)
        if year >= APP_FROM:
            app_parts.append(contract_rows(df))
        if args.baseline_only:
            continue
        tally.add(df)
        counts[str(year)] = {"rows": len(df), "fire": int(df["fire"].sum()), "cells": int(df[["cell_lat", "cell_lon"]].drop_duplicates().shape[0])}
        table = pa.Table.from_pandas(df, preserve_index=False)
        if writer is None:
            writer = pq.ParquetWriter(daily_dir / "panel.parquet", table.schema)
        writer.write_table(table.cast(writer.schema))
        print(f"  {year}: {len(df):,} rows, {counts[str(year)]['fire']:,} fire cell-days")
    if writer is not None:
        writer.close()

    app = pd.concat(app_parts + [contract_rows(live)], ignore_index=True)[CONTRACT]
    app.to_parquet(risk_dir / "cells_daily.parquet", index=False)
    print(f"Wrote {len(app):,} rows to {risk_dir / 'cells_daily.parquet'} (baselines; "
          f"{app['burn_date'].min()} to {app['burn_date'].max()})")
    if args.baseline_only:
        return

    live.to_parquet(daily_dir / "live.parquet", index=False)
    rules = tally.report()
    summary = {
        "first_day": str(first_day.date()), "last_complete_day": str(last_day.date()),
        "live_predicted_day": str(live_day.date()), "cells": len(cells), "live_rows": len(live),
        "section3_fire_cell_days": check, "per_year": counts, "baselines": rules,
        "settings": {"hist_window": HIST_WINDOW, "hist_shrink": HIST_SHRINK, "gap_days": GAP_DAYS,
                     "features": FEATURES},
    }
    (daily_dir / "panel_summary.json").write_text(json.dumps(summary, indent=2))
    total = sum(v["rows"] for v in counts.values())
    seg = pd.read_parquet(daily_dir / "panel.parquet", columns=["segment", "split", "fire"])
    print(f"Wrote {total:,} rows to {daily_dir / 'panel.parquet'} and {len(live):,} to live.parquet")
    print(seg.groupby(["segment", "split"])["fire"].agg(["size", "sum"]).unstack("split").to_string())
    for rule, by_split in rules.items():
        a = by_split["all"]
        print(f"{rule}: recall {a['recall']:.1%} | precision {a['precision']:.1%} (all panel rows)")


if __name__ == "__main__":
    main()
