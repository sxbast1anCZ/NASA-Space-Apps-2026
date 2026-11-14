"""API of the harmonized burn calendar (module M4).

Run from the repo root:
    uvicorn backend.main:app --reload

Reads the outputs of scripts/build_hotspots.py and scripts/harmonize.py under
NASA_Data_Sources/processed/ (override with the FIRE_DATA_DIR environment variable).
Every date in the API is a `burn_date` (day from 06:00 to 06:00 local solar time), as YYYY-MM-DD.
"""

from __future__ import annotations

import calendar as cal
import csv
import io
import os
from datetime import date, timedelta
from pathlib import Path
from statistics import median
from typing import Annotated

import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("FIRE_DATA_DIR", ROOT / "NASA_Data_Sources" / "processed"))
CELL = 0.25                    # degrees, cell size of the harmonized dataset
VIIRS_START = date(2012, 2, 1)  # earlier months are MODIS scaled to VIIRS-equivalent counts
CSV_ROW_LIMIT = 200_000

app = FastAPI(title="Harmonized burn calendar")
_con: duckdb.DuckDBPyConnection | None = None


def db() -> duckdb.DuckDBPyConnection:
    global _con
    if _con is None:
        cells = DATA / "harmonized" / "cells_daily.parquet"
        if not cells.exists():
            raise HTTPException(503, f"Harmonized dataset not found at {cells}. Run scripts/harmonize.py.")
        con = duckdb.connect()
        con.execute("SET TimeZone='UTC'")
        con.execute(f"CREATE TABLE cells AS SELECT * FROM read_parquet('{cells}')")
        _con = con
    return _con.cursor()  # one cursor per request: endpoints run in a thread pool


def area_filter(west, south, east, north, country, admin1, *, lat="cell_lat", lon="cell_lon", size=CELL):
    """SQL conditions and parameters for a bounding box and/or a region.

    A cell is selected when it intersects the box, so a box smaller than a cell still returns data.
    """
    where, params = ["TRUE"], []
    box = [west, south, east, north]
    if any(v is not None for v in box):
        if any(v is None for v in box):
            raise HTTPException(422, "west, south, east and north must be given together")
        if west >= east or south >= north:
            raise HTTPException(422, "The box needs west < east and south < north")
        where.append(f"{lon} < ? AND {lon} + {size} > ? AND {lat} < ? AND {lat} + {size} > ?")
        params += [east, west, north, south]
    if country:
        where.append("country = ?")
        params.append(country)
    if admin1:
        where.append("admin1 = ?")
        params.append(admin1)
    return " AND ".join(where), params


def data_through(con) -> date:
    """Last complete burn_date: the newest day in the data is still arriving."""
    return con.execute("SELECT max(burn_date) FROM cells").fetchone()[0] - timedelta(days=1)


Lon = Annotated[float | None, Query(ge=-180, le=180)]
Lat = Annotated[float | None, Query(ge=-90, le=90)]


@app.get("/api/meta")
def meta():
    con = db()
    first = con.execute("SELECT min(burn_date) FROM cells").fetchone()[0]
    regions = con.execute(
        "SELECT DISTINCT country, admin1 FROM cells WHERE admin1 IS NOT NULL ORDER BY ALL"
    ).fetchall()
    return {
        "first_date": first,
        "data_through": data_through(con),
        "viirs_start": VIIRS_START,
        "cell_degrees": CELL,
        "regions": [{"country": c, "admin1": a} for c, a in regions],
    }


@app.get("/api/calendar")
def calendar(
    west: Lon = None, south: Lat = None, east: Lon = None, north: Lat = None,
    country: str | None = None, admin1: str | None = None,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
):
    """Harmonized hotspots per year and month for an area, with medians and the current period."""
    con = db()
    where, params = area_filter(west, south, east, north, country, admin1)
    through = data_through(con)
    first = con.execute("SELECT min(burn_date) FROM cells").fetchone()[0]
    start = max(start or first, first).replace(day=1)  # the calendar works on whole months
    end = min(end or through, through)
    if start > end:
        raise HTTPException(422, "'from' must be before 'to' and inside the data period")

    n_cells, w, s, e, n = con.execute(f"""
        SELECT count(DISTINCT (cell_lat, cell_lon)), min(cell_lon), min(cell_lat),
               max(cell_lon) + {CELL}, max(cell_lat) + {CELL}
        FROM cells WHERE {where}
    """, params).fetchone()

    found = {(y, m): rest for y, m, *rest in con.execute(f"""
        SELECT year(burn_date), month(burn_date), sum(hotspots_harmonized), sum(hotspots_raw),
               bool_or(provisional)
        FROM cells WHERE {where} AND burn_date BETWEEN ? AND ? GROUP BY 1, 2
    """, [*params, start, end]).fetchall()}

    # Every month of the range, including the ones without detections.
    last_month_partial = end.day < cal.monthrange(end.year, end.month)[1]
    months = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        hotspots, raw, provisional = found.get((y, m), (0.0, 0, False))
        months.append({
            "year": y, "month": m, "hotspots": round(hotspots, 1), "raw": raw,
            "estimated": date(y, m, 1) < VIIRS_START, "provisional": bool(provisional),
            "partial": (y, m) == (end.year, end.month) and last_month_partial,
        })
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)

    complete = [x for x in months if not x["partial"]]
    median_by_month = [
        round(median(v), 1) if (v := [x["hotspots"] for x in complete if x["month"] == mm]) else None
        for mm in range(1, 13)
    ]
    years = []
    for yr in range(start.year, end.year + 1):
        in_year = [x for x in months if x["year"] == yr]
        years.append({
            "year": yr, "hotspots": round(sum(x["hotspots"] for x in in_year), 1),
            "partial": len(in_year) < 12 or any(x["partial"] for x in in_year),
        })

    # Current period: never compare a partial month with complete ones. Take the same days
    # (1 to N) of the same month in every year of the range.
    same_days = dict(con.execute(f"""
        SELECT year(burn_date), sum(hotspots_harmonized) FROM cells
        WHERE {where} AND month(burn_date) = ? AND day(burn_date) <= ? AND burn_date BETWEEN ? AND ?
        GROUP BY 1
    """, [*params, end.month, end.day, start, end]).fetchall())
    earlier = [same_days.get(yr, 0.0) for yr in range(start.year, end.year)
               if date(yr, end.month, 1) >= start]
    now = same_days.get(end.year, 0.0)
    med = median(earlier) if earlier else None
    current = {
        "year": end.year, "month": end.month, "days": end.day, "hotspots": round(now, 1),
        "median": None if med is None else round(med, 1),
        "ratio": round(now / med, 2) if med else None,
        "years_compared": len(earlier),
        "rank": 1 + sum(v > now for v in earlier) if earlier else None,
    }

    return {
        "from": start, "to": end, "data_through": through,
        "cells": n_cells, "bounds": None if not n_cells else [w, s, e, n],
        "months": months, "median_by_month": median_by_month, "years": years, "current": current,
    }


CSV_COLUMNS = [
    "latitude", "longitude", "acq_date", "acq_time", "satellite", "instrument", "confidence_raw",
    "version", "bright_mir_k", "bright_tir_k", "frp_mw", "daynight", "fire_type", "processing",
    "burn_date", "local_wall_time", "tz_name", "country", "admin1",
]


@app.get("/api/hotspots.csv")
def hotspots_csv(
    west: Lon = None, south: Lat = None, east: Lon = None, north: Lat = None,
    country: str | None = None, admin1: str | None = None,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
):
    """The hotspots of a search: FIRMS' UTC columns untouched, plus the local ones. Not harmonized."""
    con = db()
    source = DATA / "hotspots"
    if not source.is_dir():
        raise HTTPException(503, f"Hotspot table not found at {source}. Run scripts/build_hotspots.py.")
    where, params = area_filter(west, south, east, north, country, admin1, lat="latitude", lon="longitude", size=0)
    # Same filter as the calendar: vegetation fires (NRT rows have no fire_type yet and are kept).
    where += " AND (fire_type = 0 OR fire_type IS NULL)"
    if start:
        where += " AND burn_date >= ?"
        params.append(start)
    if end:
        where += " AND burn_date <= ?"
        params.append(end)
    table = f"read_parquet('{source}/*/*.parquet', hive_partitioning=true)"

    n = con.execute(f"SELECT count(*) FROM {table} WHERE {where}", params).fetchone()[0]
    if n > CSV_ROW_LIMIT:
        raise HTTPException(413, f"{n:,} hotspots match; the limit is {CSV_ROW_LIMIT:,}. "
                                 "Choose a smaller area or a shorter period.")
    rows = con.execute(
        f"SELECT {', '.join(CSV_COLUMNS)} FROM {table} WHERE {where} ORDER BY acq_datetime", params
    )

    def stream():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(CSV_COLUMNS)
        while True:
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate()
            chunk = rows.fetchmany(20_000)
            if not chunk:
                return
            writer.writerows(chunk)

    return StreamingResponse(stream(), media_type="text/csv", headers={
        "Content-Disposition": 'attachment; filename="hotspots.csv"', "X-Hotspot-Count": str(n),
    })


# Serve the built web app when it exists, so one process runs everything in production.
if (ROOT / "frontend" / "dist").is_dir():
    app.mount("/", StaticFiles(directory=ROOT / "frontend" / "dist", html=True), name="web")
