"""Merge every FIRMS download into one hotspot table with a single schema.

Inputs (from scripts/download_firms.sh and scripts/download_firms_api.sh):
    NASA_Data_Sources/<SENSOR>/<Country>/*.csv   yearly country files (SP, clipped to the country)
    NASA_Data_Sources/<SENSOR>/API_bbox/*.csv    monthly API files (SP + NRT, Chile/Argentina bbox)

Output:
    NASA_Data_Sources/processed/hotspots/year=YYYY/*.parquet

What the merge does:
    - Maps MODIS and VIIRS columns to common names (bright_mir_k, bright_tir_k, ...).
    - Normalises satellite names, acquisition time (HHMM, UTC) and processing level (SP/NRT).
    - Maps confidence to a common low/nominal/high level, keeping the raw value.
    - Labels every point with country and first-level region (`admin1`) using the polygons in
      NASA_Data_Sources/boundaries/<Country>.geojson (see README), so yearly and API rows use the
      same borders. FIRMS' own label from the yearly files is kept as `country_firms`; yearly rows
      the polygons miss keep that label. API rows outside both countries are dropped, since they come
      from the bounding box. Without boundary files, API rows keep `country` empty.
    - Drops exact duplicates (same position, time and satellite).

This step does not harmonise MODIS against VIIRS: it only puts both records in one table
with the sensor kept as a column, which is the input for the harmonisation.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

import timefields

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "NASA_Data_Sources"
OUT = DATA / "processed" / "hotspots"
BOUNDARIES = DATA / "boundaries"

# Folder name -> (instrument, satellite as it will appear in the output)
SENSOR_FOLDERS = {
    "MODIS": "MODIS",
    "VIIRS_SNPP": "VIIRS",
    "VIIRS_NOAA20": "VIIRS",
    "VIIRS_NOAA21": "VIIRS",
}
SATELLITE_NAMES = {
    "Terra": "Terra", "T": "Terra",
    "Aqua": "Aqua", "A": "Aqua",
    "N": "Suomi-NPP", "1": "Suomi-NPP",
    "N20": "NOAA-20",
    "N21": "NOAA-21",
}
# MODIS confidence is 0-100; FIRMS groups it as low < 30 <= nominal < 80 <= high.
MODIS_CONF_BINS = [-1, 29, 79, 100]
VIIRS_CONF = {"l": "low", "n": "nominal", "h": "high"}
CONF_LEVELS = ["low", "nominal", "high"]

READ_DTYPES = {
    "latitude": "float64", "longitude": "float64",
    "brightness": "float32", "bright_t31": "float32",
    "bright_ti4": "float32", "bright_ti5": "float32",
    "scan": "float32", "track": "float32", "frp": "float32",
    "acq_date": "string", "acq_time": "string", "satellite": "string",
    "instrument": "string", "confidence": "string", "version": "string",
    "daynight": "string", "type": "Int8",
}


def list_inputs() -> list[tuple[Path, str, str, str]]:
    """Return (path, sensor folder, source kind, country from folder or '')."""
    files = []
    for folder in SENSOR_FOLDERS:
        base = DATA / folder
        if not base.is_dir():
            continue
        for sub in sorted(p for p in base.iterdir() if p.is_dir()):
            kind = "api_bbox" if sub.name == "API_bbox" else "country_yearly"
            country = "" if kind == "api_bbox" else sub.name
            files += [(f, folder, kind, country) for f in sorted(sub.glob("*.csv"))]
    return files


def read_one(path: Path, folder: str, kind: str, country: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=READ_DTYPES)
    instrument = SENSOR_FOLDERS[folder]
    if instrument == "MODIS":
        df = df.rename(columns={"brightness": "bright_mir_k", "bright_t31": "bright_tir_k"})
        conf_pct = pd.to_numeric(df["confidence"], errors="coerce").astype("Int16")
        df["confidence_pct"] = conf_pct
        df["confidence_level"] = pd.cut(conf_pct, MODIS_CONF_BINS, labels=CONF_LEVELS)
    else:
        df = df.rename(columns={"bright_ti4": "bright_mir_k", "bright_ti5": "bright_tir_k"})
        df["confidence_pct"] = pd.array([pd.NA] * len(df), dtype="Int16")
        df["confidence_level"] = df["confidence"].str.lower().map(VIIRS_CONF)
    if "type" not in df:
        df["type"] = pd.array([pd.NA] * len(df), dtype="Int8")
    df["instrument"] = instrument
    df["source"] = kind
    df["source_file"] = f"{folder}/{path.parent.name}/{path.name}"
    df["country"] = country or pd.NA
    return df


def normalise(df: pd.DataFrame, strict: bool = True) -> pd.DataFrame:
    hhmm = df["acq_time"].str.strip().str.zfill(4)
    df["acq_time"] = hhmm
    df["acq_datetime"] = pd.to_datetime(
        df["acq_date"] + " " + hhmm, format="%Y-%m-%d %H%M", utc=True
    )
    df["acq_date"] = df["acq_datetime"].dt.date
    df["year"] = df["acq_datetime"].dt.year.astype("int16")
    df["month"] = df["acq_datetime"].dt.month.astype("int8")
    # acq_date, year and month above are UTC (FIRMS-compatible). The day key is burn_date.
    df = timefields.add_solar_fields(df, strict=strict)

    unknown = set(df["satellite"].dropna().unique()) - set(SATELLITE_NAMES)
    if unknown:
        raise ValueError(f"Unknown satellite codes: {sorted(unknown)}")
    df["satellite"] = df["satellite"].map(SATELLITE_NAMES)
    df["processing"] = np.where(
        df["version"].str.contains("NRT", case=False, na=False), "NRT", "SP"
    )
    df["pixel_area_km2"] = (df["scan"] * df["track"]).astype("float32")
    df = df.rename(columns={
        "confidence": "confidence_raw", "frp": "frp_mw",
        "scan": "scan_km", "track": "track_km", "type": "fire_type",
    })
    for col in ["instrument", "satellite", "processing", "daynight", "source", "country"]:
        df[col] = df[col].astype("category")
    df["confidence_level"] = pd.Categorical(df["confidence_level"], categories=CONF_LEVELS, ordered=True)
    return df


# ---------------------------------------------------------------- country and region labels

SIMPLIFY_DEG = 0.001  # ~100 m, well below the 375 m VIIRS pixel
NAME_KEYS = ("shapeName", "nam", "name", "NAME_1")


def fix_mojibake(text: str) -> str:
    """Undo UTF-8 text that was decoded as Latin-1 (e.g. 'RegiÃ³n' -> 'Región')."""
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def load_regions() -> list[tuple[str, str, object]]:
    """Read BOUNDARIES/<Country>.geojson (one feature per first-level region).

    Returns (country, region, prepared shapely geometry) for every region.
    """
    import shapely

    regions = []
    for f in sorted(BOUNDARIES.glob("*.geojson")):
        gj = json.loads(f.read_text(encoding="utf-8"))
        for feat in gj["features"]:
            props = feat.get("properties") or {}
            name = next((props[k] for k in NAME_KEYS if props.get(k)), "")
            geom = shapely.make_valid(shapely.geometry.shape(feat["geometry"]))
            geom = shapely.simplify(geom, SIMPLIFY_DEG, preserve_topology=True)
            shapely.prepare(geom)
            regions.append((f.stem, fix_mojibake(name), geom))
    return regions


def label_regions(lon: np.ndarray, lat: np.ndarray, regions) -> tuple[np.ndarray, np.ndarray]:
    """Return (country, region) arrays for each point; None where no region contains it."""
    import shapely

    country = np.full(len(lon), None, dtype=object)
    region = np.full(len(lon), None, dtype=object)
    for c, r, geom in regions:
        xmin, ymin, xmax, ymax = geom.bounds
        cand = (lon >= xmin) & (lon <= xmax) & (lat >= ymin) & (lat <= ymax)
        cand &= region == None  # noqa: E711  first match wins where borders overlap
        idx = np.flatnonzero(cand)
        if idx.size:
            inside = shapely.contains_xy(geom, lon[idx], lat[idx])
            country[idx[inside]] = c
            region[idx[inside]] = r
    return country, region


def nearest_region(lon: np.ndarray, lat: np.ndarray, country: np.ndarray, regions) -> np.ndarray:
    """Closest region of the same country for each point (used for points the polygons miss)."""
    import shapely

    points = shapely.points(lon, lat)
    best = np.full(len(lon), np.inf)
    nearest = np.full(len(lon), None, dtype=object)
    for c, r, geom in regions:
        idx = np.flatnonzero(country == c)
        dist = shapely.distance(geom, points[idx])
        closer = dist < best[idx]
        best[idx[closer]] = dist[closer]
        nearest[idx[closer]] = r
    return nearest


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    inputs = list_inputs()
    if not inputs:
        raise SystemExit(f"No CSV files found under {DATA}. Run the download scripts first.")
    print(f"Reading {len(inputs)} files ...")
    df = pd.concat([read_one(*i) for i in inputs], ignore_index=True)
    df = normalise(df)
    n_read = len(df)

    key = ["latitude", "longitude", "acq_datetime", "satellite"]
    df = df.drop_duplicates(key)
    print(f"Rows read: {n_read:,} | exact duplicates dropped: {n_read - len(df):,}")

    # FIRMS' own country label (yearly files only) is kept for comparison.
    df["country_firms"] = df["country"]
    regions = load_regions() if BOUNDARIES.is_dir() else []
    if regions:
        print(f"Labelling {len(df):,} points with {len(regions)} regions ...")
        country, region = label_regions(df["longitude"].to_numpy(), df["latitude"].to_numpy(), regions)
        # Yearly rows the polygons miss (coast, simplified borders) keep FIRMS' country label.
        firms = df["country_firms"].astype("object").to_numpy()
        missed = (country == None) & pd.notna(firms)  # noqa: E711
        country[missed] = firms[missed]
        df["country"] = pd.Categorical(country)
        df["admin1"] = pd.Categorical(region)
        # API rows outside both countries come from the bounding box (neighbouring countries).
        outside = df["country"].isna().to_numpy()
        df = df[~outside]
        print(f"Yearly rows outside the polygons that keep FIRMS' label: {int(missed.sum()):,}")
        print(f"API rows dropped as outside Chile/Argentina: {int(outside.sum()):,}")

        # Civil time zone comes from the region; rows without one take the nearest region's zone.
        tz_region = df["admin1"].astype("object").to_numpy(copy=True)
        no_region = pd.isna(tz_region)
        tz_region[no_region] = nearest_region(
            df["longitude"].to_numpy()[no_region], df["latitude"].to_numpy()[no_region],
            df["country"].astype("object").to_numpy()[no_region], regions,
        )
        df["_tz_region"] = tz_region
        df = timefields.add_civil_fields(df, region_col="_tz_region")
    else:
        df["admin1"] = pd.Categorical([None] * len(df))
        print(f"No boundary files in {BOUNDARIES}: API rows keep country empty, no admin1.")

    cols = [
        "acq_datetime", "acq_date", "acq_time", "year", "month", "daynight",
        "solar_time_h", "pass_slot", "burn_date", "burn_year", "burn_month", "season_year",
        "tz_name", "utc_offset_min", "local_wall_time", "local_date",
        "latitude", "longitude", "country", "admin1", "country_firms",
        "instrument", "satellite", "processing", "version",
        "confidence_level", "confidence_pct", "confidence_raw",
        "bright_mir_k", "bright_tir_k", "frp_mw",
        "scan_km", "track_km", "pixel_area_km2", "fire_type",
        "source", "source_file",
    ]
    df = df[[c for c in cols if c in df]].sort_values(["acq_datetime", "satellite"]).reset_index(drop=True)

    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)
    df.to_parquet(args.out, partition_cols=["year"], index=False, compression="zstd")
    print(f"Wrote {len(df):,} rows to {args.out}")
    print(df.groupby(["instrument", "satellite", "processing"], observed=True).size().to_string())


if __name__ == "__main__":
    main()
