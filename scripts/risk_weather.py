"""Weekly weather features from NASA POWER for the risk model (block 8, module M5).

Weather comes from NASA POWER (MERRA-2 meteorology, IMERG-corrected precipitation), daily, Local
Solar Time. One point per 0.5 degree block that contains a fire cell, requested once and cached, so
a failed run resumes where it stopped.

Inputs:
    NASA_Data_Sources/processed/hotspots/    to find the 0.25 degree cells with fire (VIIRS)
    NASA POWER daily point API               https://power.larc.nasa.gov/docs/services/api/

Outputs (NASA_Data_Sources/processed/weather/):
    power_daily/<lat>_<lon>.csv    raw daily values per point (cache, one file per point)
    cell_to_point.parquet          0.25 degree fire cell -> weather point
    weekly.parquet                 one row per weather point and week (52 fixed bins, see
                                   scripts/risk_baseline.py)

Feature timing (no information leak):
    ante_*  use only the days BEFORE the week starts. They are known when the forecast is made.
    wk_*    describe the week itself. Useful to explain past weeks; for a real forecast they would
            need a weather forecast, so the first model does not use them.

Time alignment: POWER daily values run midnight to midnight local solar time, while `burn_date`
runs 06:00 to 06:00 local solar time (docs/eda-plan.md). The 6 hour offset is small for weekly and
monthly windows; it is a known limit of this layer.

Run:
    python scripts/risk_weather.py                 # all points, resumes from the cache
    python scripts/risk_weather.py --limit 5       # quick test with 5 points
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from risk_baseline import CELL_DEG, HOTSPOTS, N_WEEKS, QUALITY, load_detections, week_index, week_start

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "NASA_Data_Sources" / "processed" / "weather"
API = "https://power.larc.nasa.gov/api/temporal/daily/point"

POINT_DEG = 0.5  # MERRA-2 native grid is 0.5 x 0.625 degrees; finer requests repeat values
PARAMETERS = {   # POWER name -> our name (units of the AG community)
    "T2M_MAX": "tmax_c",
    "T2M": "tmean_c",
    "RH2M": "rh_pct",
    "WS10M": "wind_ms",
    "WS10M_MAX": "wind_max_ms",
    "PRECTOTCORR": "precip_mm",
    "GWETTOP": "soil_wet",
}
FIRST_DATE = pd.Timestamp("2011-09-01")  # 120 days of history before the first VIIRS week
RAIN_MM = 1.0                            # a day with at least this much rain counts as wet
SLEEP_S = 1.0                            # pause between requests, to be polite with the API


# ---------------------------------------------------------------- points

def fire_cells(hotspots: Path, quality: Path = QUALITY) -> pd.DataFrame:
    df = load_detections(hotspots, quality)
    cells = pd.DataFrame({
        "cell_lat": np.floor(df["latitude"] / CELL_DEG) * CELL_DEG,
        "cell_lon": np.floor(df["longitude"] / CELL_DEG) * CELL_DEG,
    }).drop_duplicates()
    # Weather point: centre of the 0.5 degree block that contains the cell.
    cells["point_lat"] = np.floor(cells["cell_lat"] / POINT_DEG) * POINT_DEG + POINT_DEG / 2
    cells["point_lon"] = np.floor(cells["cell_lon"] / POINT_DEG) * POINT_DEG + POINT_DEG / 2
    return cells.sort_values(["cell_lat", "cell_lon"]).reset_index(drop=True)


def cache_path(cache: Path, lat: float, lon: float) -> Path:
    return cache / f"{lat:+08.3f}_{lon:+09.3f}.csv"


# ---------------------------------------------------------------- download

def fetch_point(lat: float, lon: float, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Daily values for one point. Missing values (POWER fill value) become NaN."""
    query = urllib.parse.urlencode({
        "parameters": ",".join(PARAMETERS),
        "community": "AG",
        "latitude": f"{lat:.3f}",
        "longitude": f"{lon:.3f}",
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "time-standard": "LST",
        "format": "JSON",
    })
    last_error = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(f"{API}?{query}", timeout=180) as resp:
                payload = json.load(resp)
            return parse_power(payload)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"POWER request failed for {lat}, {lon}: {last_error}")


def parse_power(payload: dict) -> pd.DataFrame:
    values = payload["properties"]["parameter"]
    fill = payload.get("header", {}).get("fill_value", -999.0)
    missing = [p for p in PARAMETERS if p not in values]
    if missing:
        raise ValueError(f"POWER response has no {missing}")
    df = pd.DataFrame({PARAMETERS[p]: pd.Series(values[p], dtype="float64") for p in PARAMETERS})
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "date"
    return df.mask(df <= fill + 1e-6).sort_index()  # fill value is -999


def download(points: pd.DataFrame, cache: Path, end: pd.Timestamp, limit: int | None) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    todo = [(r.point_lat, r.point_lon) for r in points.itertuples()
            if not cache_path(cache, r.point_lat, r.point_lon).exists()]
    if limit is not None:
        todo = todo[:limit]
    print(f"Weather points: {len(points):,} | cached: {len(points) - len(todo):,} | to download: {len(todo):,}")
    for n, (lat, lon) in enumerate(todo, 1):
        df = fetch_point(lat, lon, FIRST_DATE, end)
        tmp = cache_path(cache, lat, lon).with_suffix(".part")
        df.to_csv(tmp)
        tmp.replace(cache_path(cache, lat, lon))
        if n % 25 == 0 or n == len(todo):
            print(f"  {n:,}/{len(todo):,} points downloaded")
        time.sleep(SLEEP_S)


# ---------------------------------------------------------------- weekly features

def days_since_rain(precip: pd.Series) -> pd.Series:
    """Days since the last day with at least RAIN_MM, counted at the end of each day."""
    wet = (precip >= RAIN_MM).to_numpy()
    out = np.empty(len(wet))
    count = 120.0  # unknown history counts as long dry
    for i, w in enumerate(wet):
        count = 0.0 if w else min(count + 1, 120.0)
        out[i] = count
    return pd.Series(out, index=precip.index)


def weekly_features(daily: pd.DataFrame, years: range) -> pd.DataFrame:
    d = daily.asfreq("D")
    es = 0.6108 * np.exp(17.27 * d["tmean_c"] / (d["tmean_c"] + 237.3))  # kPa
    d["vpd_kpa"] = es * (1 - d["rh_pct"] / 100)

    # Antecedent features: windows that END the day before the week starts (shift by one day).
    ante = pd.DataFrame(index=d.index)
    ante["ante_precip_30d_mm"] = d["precip_mm"].rolling(30, min_periods=25).sum().shift(1)
    ante["ante_precip_90d_mm"] = d["precip_mm"].rolling(90, min_periods=80).sum().shift(1)
    ante["ante_dry_days_30d"] = (d["precip_mm"] < RAIN_MM).astype(float).rolling(30, min_periods=25).sum().shift(1)
    ante["ante_days_since_rain"] = days_since_rain(d["precip_mm"].fillna(0)).shift(1)
    ante["ante_tmax_14d_c"] = d["tmax_c"].rolling(14, min_periods=10).mean().shift(1)
    ante["ante_rh_14d_pct"] = d["rh_pct"].rolling(14, min_periods=10).mean().shift(1)
    ante["ante_vpd_14d_kpa"] = d["vpd_kpa"].rolling(14, min_periods=10).mean().shift(1)
    ante["ante_wind_7d_ms"] = d["wind_ms"].rolling(7, min_periods=5).mean().shift(1)
    ante["ante_wind_max_7d_ms"] = d["wind_max_ms"].rolling(7, min_periods=5).max().shift(1)
    ante["ante_soil_wet"] = d["soil_wet"].shift(1)

    rows = []
    for yr in years:
        for w in range(N_WEEKS):
            s = week_start(yr, w)
            e = week_start(yr, w + 1) - pd.Timedelta(days=1) if w < N_WEEKS - 1 else pd.Timestamp(yr, 12, 31)
            if s not in ante.index:
                continue
            row = {"year": yr, "week": w, "week_start": s.date(), **ante.loc[s].to_dict()}
            wk = d.loc[s:e]
            if len(wk) == (e - s).days + 1 and wk["tmax_c"].notna().all():
                row.update({
                    "wk_tmax_mean_c": wk["tmax_c"].mean(), "wk_tmax_max_c": wk["tmax_c"].max(),
                    "wk_rh_mean_pct": wk["rh_pct"].mean(), "wk_wind_max_ms": wk["wind_max_ms"].max(),
                    "wk_precip_mm": wk["precip_mm"].sum(), "wk_vpd_mean_kpa": wk["vpd_kpa"].mean(),
                })
            rows.append(row)
    return pd.DataFrame(rows)


def build_weekly(points: pd.DataFrame, cache: Path, years: range) -> pd.DataFrame:
    frames = []
    for r in points.itertuples():
        path = cache_path(cache, r.point_lat, r.point_lon)
        if not path.exists():
            continue
        daily = pd.read_csv(path, index_col="date", parse_dates=["date"])
        wk = weekly_features(daily, years)
        wk.insert(0, "point_lon", r.point_lon)
        wk.insert(0, "point_lat", r.point_lat)
        frames.append(wk)
    if not frames:
        raise SystemExit("No cached weather points: run the download first.")
    out = pd.concat(frames, ignore_index=True)
    num = out.columns.difference(["point_lat", "point_lon", "year", "week", "week_start"])
    out[num] = out[num].astype("float32")
    return out


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hotspots", type=Path, default=HOTSPOTS)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--quality", type=Path, default=QUALITY, help="folder with the block 1 quality files")
    ap.add_argument("--limit", type=int, default=None, help="download at most N new points")
    ap.add_argument("--end", default=None, help="last date YYYY-MM-DD (default: 3 days ago, POWER latency)")
    args = ap.parse_args()

    end = pd.Timestamp(args.end) if args.end else pd.Timestamp.now(tz="UTC").tz_localize(None).normalize() - pd.Timedelta(days=3)
    cells = fire_cells(args.hotspots, args.quality)
    points = cells[["point_lat", "point_lon"]].drop_duplicates().reset_index(drop=True)
    print(f"Fire cells: {len(cells):,} -> weather points: {len(points):,} | days {FIRST_DATE.date()} to {end.date()}")

    cache = args.out / "power_daily"
    download(points, cache, end, args.limit)

    args.out.mkdir(parents=True, exist_ok=True)
    cells.to_parquet(args.out / "cell_to_point.parquet", index=False)
    weekly = build_weekly(points, cache, range(2012, end.year + 1))
    weekly.to_parquet(args.out / "weekly.parquet", index=False)
    print(f"Wrote {len(weekly):,} rows ({weekly[['point_lat', 'point_lon']].drop_duplicates().shape[0]:,} points) "
          f"to {args.out / 'weekly.parquet'}")


if __name__ == "__main__":
    main()
