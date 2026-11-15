"""Wind for the cells in alert on the live day of the next-day outlook, from Open-Meteo.

The model has no weather. This file is context for the map: where the wind blows from on the
predicted day, so that the interface can draw the downwind side of an active fire. It is a wind
forecast, not a spread forecast: nothing in this project checks that hotspots move downwind.

Input:   NASA_Data_Sources/processed/risk/cells_daily.parquet (the alerts of the newest day)
Output:  NASA_Data_Sources/processed/risk/wind_live.parquet
         burn_date, cell_lat, cell_lon, wind_from_deg (direction the wind comes from, 0 = north,
         90 = east), downwind_deg (where it blows to), wind_max_kmh, gust_max_kmh, rh_min_pct, tmax_c

Source: Open-Meteo forecast API (https://open-meteo.com), free for non-commercial use, no key,
licence CC BY 4.0: show "Weather data by Open-Meteo.com" where the values are shown. Days are local
civil days, not the 06:00 to 06:00 solar day of `burn_date`. Only cell centres are sent.

Run:  python scripts/daily_wind.py
"""

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RISK = ROOT / "NASA_Data_Sources" / "processed" / "risk"
API = "https://api.open-meteo.com/v1/forecast"
CELL_DEG = 0.25
BATCH = 25           # locations per request: each one counts against the limit of 600 calls a minute
DAILY = {            # Open-Meteo name -> our column
    "wind_direction_10m_dominant": "wind_from_deg",
    "wind_speed_10m_max": "wind_max_kmh",
    "wind_gusts_10m_max": "gust_max_kmh",
    "relative_humidity_2m_min": "rh_min_pct",
    "temperature_2m_max": "tmax_c",
}


def parse(payload, cells: pd.DataFrame) -> pd.DataFrame:
    """One row per cell from the API answer (a list, or one object when one location was asked)."""
    places = payload if isinstance(payload, list) else [payload]
    if len(places) != len(cells):
        raise ValueError(f"{len(places)} locations answered for {len(cells)} cells")
    out = cells.reset_index(drop=True).copy()
    for name, column in DAILY.items():
        out[column] = [(p["daily"].get(name) or [None])[0] for p in places]
    out["downwind_deg"] = (out["wind_from_deg"] + 180) % 360
    return out


def fetch(cells: pd.DataFrame, day) -> pd.DataFrame:
    query = urllib.parse.urlencode({
        "latitude": ",".join(f"{v + CELL_DEG / 2:.3f}" for v in cells["cell_lat"]),
        "longitude": ",".join(f"{v + CELL_DEG / 2:.3f}" for v in cells["cell_lon"]),
        "daily": ",".join(DAILY), "start_date": str(day), "end_date": str(day), "timezone": "auto",
    })
    for attempt in range(6):
        try:
            with urllib.request.urlopen(f"{API}?{query}", timeout=60) as answer:
                return parse(json.load(answer), cells)
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 5:      # 429: the free limit per minute; wait and try again
                raise
            time.sleep(65)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--risk", type=Path, default=RISK)
    args = ap.parse_args(argv)
    app = pd.read_parquet(args.risk / "cells_daily.parquet", columns=["burn_date", "cell_lat", "cell_lon", "alert"])
    day = app["burn_date"].max()
    cells = app[(app["burn_date"] == day) & (app["alert"] == 1)][["burn_date", "cell_lat", "cell_lon"]]
    parts = []
    for start in range(0, len(cells), BATCH):
        parts.append(fetch(cells.iloc[start:start + BATCH], day))
        time.sleep(3)                      # polite with a free service
    out = pd.concat(parts, ignore_index=True)
    columns = ["burn_date", "cell_lat", "cell_lon", "wind_from_deg", "downwind_deg", *list(DAILY.values())[1:]]
    out[columns].to_parquet(args.risk / "wind_live.parquet", index=False)
    print(f"{len(out):,} cells in alert on {day}; wind missing for {int(out['wind_from_deg'].isna().sum())}")
    print(f"Written: {args.risk / 'wind_live.parquet'}")


if __name__ == "__main__":
    main()
