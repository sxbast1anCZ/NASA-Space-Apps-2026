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
from typing import Annotated, Literal

import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("FIRE_DATA_DIR", ROOT / "NASA_Data_Sources" / "processed"))
CELL = 0.25                    # degrees, cell size of the harmonized dataset
VIIRS_START = date(2012, 2, 1)  # earlier months are MODIS scaled to VIIRS-equivalent counts
CSV_ROW_LIMIT = 200_000
# Anomalies (EDA block 4). The default reference starts in 2013, the first complete VIIRS year:
# before 2012 fire activity was 1.35 times higher, so an all-years median makes recent months look low.
REFERENCE_START = 2013
RELIABLE_MEDIAN = 10           # below this reference median the ratio is not shown as an anomaly
# Next-day outlook (docs/findings/09-daily-model.md). Share of the hotspots of a day that lie within
# each distance of a hotspot of the day before (Suomi-NPP, 2013-2025): where fire fell, not a forecast.
RINGS = [{"km": 5, "share": 0.38}, {"km": 10, "share": 0.50}, {"km": 25, "share": 0.69}]
RING_POINTS = 3000             # hotspots sent for the rings, after thinning them to about 2 km
NOAA20_FROM = date(2026, 11, 1)  # the satellite of the outlook: Suomi-NPP before, NOAA-20 from this day
EARTH_KM = 6371.0088           # mean radius, for the area of a cell on the sphere
ZONE_POINTS = 6000             # hotspots sent for the fire zones, largest fires first
# Area of a cell named by its south-west corner, in km2 (0.25 degree: about 700 km2 at 25 S, 450 at 54 S).
CELL_KM2 = (f"({EARTH_KM ** 2} * radians({CELL}) * "
            f"(sin(radians(cell_lat + {CELL})) - sin(radians(cell_lat))))")
# Optional files of the next-day outlook, with their columns so that the app starts without them.
DAILY_FILES = {
    "daily": ("cells_daily.parquet", "NULL::DATE AS burn_date, 0.0 AS cell_lat, 0.0 AS cell_lon, "
              "0.0 AS probability, 0.0 AS baseline_probability, 0 AS alert"),
    "daily_reasons": ("cells_daily_reasons.parquet", "NULL::DATE AS burn_date, 0.0 AS cell_lat, 0.0 AS cell_lon, "
                      "'' AS reason_1, '' AS reason_2, '' AS reason_3, 0.0 AS share_1, 0.0 AS share_2, 0.0 AS share_3"),
    "daily_wind": ("wind_live.parquet", "NULL::DATE AS burn_date, 0.0 AS cell_lat, 0.0 AS cell_lon, "
                   "0.0 AS wind_from_deg, 0.0 AS downwind_deg, 0.0 AS wind_max_kmh, 0.0 AS gust_max_kmh, "
                   "0.0 AS rh_min_pct, 0.0 AS tmax_c"),
    # Zones of likely activity around the fires of the day before (scripts/fire_zones.py).
    "zones": ("fire_zones.parquet", "NULL::DATE AS burn_date, NULL::DATE AS seen_date, 0 AS fire_id, 0.0 AS lat, "
              "0.0 AS lon, '' AS country, '' AS admin1, 0 AS hotspots, 0.0 AS frp_sum_mw, '' AS size_class, "
              "NULL::BOOLEAN AS active, 0.0 AS p_continue, 0.0 AS r50_km, 0.0 AS r80_km, 0.0 AS r90_km, "
              "0.0 AS area50_km2, 0.0 AS area80_km2, 0.0 AS area90_km2, NULL::BOOLEAN AS continued, "
              "0 AS next_hotspots, 0 AS next_in_r80"),
    "zone_points": ("fire_zone_points.parquet", "NULL::DATE AS burn_date, 0 AS fire_id, 0.0 AS lat, 0.0 AS lon"),
}

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
        # Risk layer (contract C3), optional: only the week in progress and the weeks ahead.
        risk = DATA / "risk" / "cells_weekly.parquet"
        source = f"read_parquet('{risk}')" if risk.exists() else "(SELECT NULL::DATE AS week_start, 0.0 AS cell_lat, 0.0 AS cell_lon, 0.0 AS probability, 0.0 AS baseline_probability LIMIT 0)"
        con.execute(f"""
            CREATE TABLE risk AS SELECT * FROM {source}
            WHERE week_start > (SELECT max(burn_date) - 8 FROM cells)
        """)
        # Next-day outlook: views, so that each request reads only its day from the files.
        for name, (file, empty) in DAILY_FILES.items():
            path = DATA / "risk" / file
            source = f"SELECT * REPLACE (burn_date::DATE AS burn_date) FROM read_parquet('{path}')" if path.exists() \
                else f"SELECT {empty} LIMIT 0"
            con.execute(f"CREATE VIEW {name} AS {source}")
        con.execute("CREATE TABLE daily_days AS SELECT DISTINCT burn_date FROM daily")
        # Region of each cell for the area summary: the one of most of its rows, ties by name.
        con.execute("""
            CREATE TABLE cell_region AS SELECT cell_lat, cell_lon, country, admin1 FROM (
                SELECT *, row_number() OVER (PARTITION BY cell_lat, cell_lon ORDER BY n DESC, country, admin1) AS k
                FROM (SELECT cell_lat, cell_lon, country, admin1, count(*) AS n FROM cells
                      WHERE admin1 IS NOT NULL GROUP BY cell_lat, cell_lon, country, admin1)) WHERE k = 1
        """)
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


def anomaly(x: float | None, reference: list[float]) -> dict:
    """Median of the reference and the ratio (x + 1) / (median + 1). x is None for a partial month."""
    if not reference:
        return {"median": None, "ratio": None, "reliable": False}
    med = median(reference)
    return {
        "median": round(med, 1),
        "ratio": None if x is None else round((x + 1) / (med + 1), 3),
        "reliable": x is not None and med >= RELIABLE_MEDIAN,
    }


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
        # Weeks the risk layer covers, first the week in progress. Empty when there is no risk file.
        "risk_weeks": [w for (w,) in con.execute("SELECT DISTINCT week_start FROM risk ORDER BY 1").fetchall()],
        # Days the next-day outlook covers, newest first: the first one is the live day. Not every day
        # is there (satellite outages, and no days between the test years and the live day).
        "risk_days": [d for (d,) in con.execute("SELECT burn_date FROM daily_days ORDER BY 1 DESC").fetchall()],
    }


@app.get("/api/risk")
def risk(
    week: date,
    west: Lon = None, south: Lat = None, east: Lon = None, north: Lat = None,
    country: str | None = None, admin1: str | None = None,
):
    """Probability of fire activity per cell for one week: [cell_lat, cell_lon, probability, baseline]."""
    con = db()
    where, params = area_filter(west, south, east, north, country, admin1)
    rows = con.execute(f"""
        SELECT r.cell_lat, r.cell_lon, round(r.probability::DOUBLE, 3), round(r.baseline_probability::DOUBLE, 3)
        FROM risk r SEMI JOIN (SELECT DISTINCT cell_lat, cell_lon FROM cells WHERE {where}) c
             USING (cell_lat, cell_lon)
        WHERE r.week_start = ? ORDER BY 1, 2
    """, [*params, week]).fetchall()
    return {"week_start": week, "cells": rows}


Day = Annotated[date, Query(alias="date")]


@app.get("/api/risk/daily")
def risk_daily(
    day: Day,
    west: Lon = None, south: Lat = None, east: Lon = None, north: Lat = None,
    country: str | None = None, admin1: str | None = None,
):
    """Next-day outlook for one predicted day.

    cells: [cell_lat, cell_lon, probability, historical rate, alert (0 or 1)].
    wind: [cell_lat, cell_lon, direction the wind blows to (degrees), maximum speed (km/h)], for the
    cells in alert, when the wind file has that day.
    """
    con = db()
    where, params = area_filter(west, south, east, north, country, admin1)
    area = f"SEMI JOIN (SELECT DISTINCT cell_lat, cell_lon FROM cells WHERE {where}) c USING (cell_lat, cell_lon)"
    cells = con.execute(f"""
        SELECT d.cell_lat, d.cell_lon, round(d.probability::DOUBLE, 3), round(d.baseline_probability::DOUBLE, 3),
               d.alert::INTEGER
        FROM daily d {area} WHERE d.burn_date = ? ORDER BY 1, 2
    """, [*params, day]).fetchall()
    wind = con.execute(f"""
        SELECT w.cell_lat, w.cell_lon, round(w.downwind_deg::DOUBLE), round(w.wind_max_kmh::DOUBLE, 1)
        FROM daily_wind w {area} WHERE w.burn_date = ? AND w.downwind_deg IS NOT NULL ORDER BY 1, 2
    """, [*params, day]).fetchall()
    return {"date": day, "cells": cells, "wind": wind, "area": daily_area(con, area, params, day)}


def daily_area(con, area: str, params: list, day: date) -> dict:
    """Area of the cells in alert and the expected area of cells with activity, in km2, with regions.

    `expected_km2` adds probability times cell area: the area of the cells where the satellite would
    see at least one hotspot, on average over days like this one. It is not burned area.
    """
    rows = con.execute(f"""
        SELECT r.country, r.admin1, count(*), sum(d.alert)::INTEGER,
               sum(d.km2), sum(d.km2 * d.alert), sum(d.km2 * d.probability)
        FROM (SELECT d.*, {CELL_KM2} AS km2 FROM daily d {area} WHERE d.burn_date = ?) d
        LEFT JOIN cell_region r USING (cell_lat, cell_lon)
        GROUP BY ALL ORDER BY 6 DESC, 7 DESC, 1, 2
    """, [*params, day]).fetchall()
    total = [sum(r[i] or 0 for r in rows) for i in range(2, 7)]
    return {
        "cells": total[0], "alert_cells": total[1], "cells_km2": round(total[2]),
        "alert_km2": round(total[3]), "expected_km2": round(total[4]),
        "regions": [{"country": c, "admin1": a, "cells": n, "alert_cells": k, "alert_km2": round(ak),
                     "expected_km2": round(ek)} for c, a, n, k, _, ak, ek in rows if k or ek >= 0.5],
    }


@app.get("/api/risk/daily/cell")
def risk_daily_cell(day: Day, cell_lat: float, cell_lon: float):
    """One cell of the next-day outlook: its numbers, the reasons of its alert and its wind."""
    con = db()
    key = [day, cell_lat, cell_lon]
    cell = con.execute("""
        SELECT probability::DOUBLE, baseline_probability::DOUBLE, alert::INTEGER FROM daily
        WHERE burn_date = ? AND cell_lat = ? AND cell_lon = ?
    """, key).fetchone()
    if cell is None:
        raise HTTPException(404, "No outlook for that cell and day")
    why = con.execute("""
        SELECT reason_1, share_1::DOUBLE, reason_2, share_2::DOUBLE, reason_3, share_3::DOUBLE FROM daily_reasons
        WHERE burn_date = ? AND cell_lat = ? AND cell_lon = ?
    """, key).fetchone() or ()
    wind = con.execute("""
        SELECT wind_from_deg::DOUBLE, downwind_deg::DOUBLE, wind_max_kmh::DOUBLE, gust_max_kmh::DOUBLE,
               rh_min_pct::DOUBLE, tmax_c::DOUBLE FROM daily_wind
        WHERE burn_date = ? AND cell_lat = ? AND cell_lon = ?
    """, key).fetchone()
    names = ["wind_from_deg", "downwind_deg", "wind_max_kmh", "gust_max_kmh", "rh_min_pct", "tmax_c"]
    return {
        "date": day, "cell_lat": cell_lat, "cell_lon": cell_lon,
        "probability": round(cell[0], 3), "baseline_probability": round(cell[1], 3), "alert": bool(cell[2]),
        "reasons": [{"text": text, "share": round(share, 2)} for text, share in zip(why[::2], why[1::2]) if text],
        "wind": dict(zip(names, wind)) if wind else None,
    }


@app.get("/api/risk/daily/hotspots")
def risk_daily_hotspots(
    day: Day,
    west: Lon = None, south: Lat = None, east: Lon = None, north: Lat = None,
    country: str | None = None, admin1: str | None = None,
):
    """Hotspots of the day before the predicted day, for the rings of the map: [latitude, longitude].

    Only the satellite of the outlook, and thinned to one point per 0.02 degrees (about 2 km): the
    smallest ring is 5 km. `truncated` says that the area has more points than are sent.
    """
    con = db()
    source = DATA / "harmonized" / "hotspots_kept.parquet"
    if not source.exists():
        raise HTTPException(503, f"{source} not found. Run scripts/harmonize.py.")
    seen = day - timedelta(days=1)
    satellite = "NOAA-20" if seen >= NOAA20_FROM else "Suomi-NPP"
    where, params = area_filter(west, south, east, north, country, admin1, lat="latitude", lon="longitude", size=0)
    points = con.execute(f"""
        SELECT DISTINCT round(round(latitude / 0.02) * 0.02, 2), round(round(longitude / 0.02) * 0.02, 2)
        FROM read_parquet('{source}') WHERE {where} AND burn_date = ? AND satellite = ?
        ORDER BY 1, 2 LIMIT {RING_POINTS + 1}
    """, [*params, seen, satellite]).fetchall()
    return {"date": seen, "satellite": satellite, "points": points[:RING_POINTS],
            "truncated": len(points) > RING_POINTS, "rings": RINGS}


@app.get("/api/risk/daily/zones")
def risk_daily_zones(
    day: Day,
    west: Lon = None, south: Lat = None, east: Lon = None, north: Lat = None,
    country: str | None = None, admin1: str | None = None,
):
    """Fires of the day before the predicted day, with the zones where their hotspots usually fall next.

    `fires`: [fire_id, lat, lon, hotspots, p_continue, r50_km, r80_km, r90_km, area50_km2, area80_km2,
    area90_km2, continued, next_hotspots, next_in_r80, admin1], largest first. `continued` is null for
    the live day. `points`: [fire_id, lat, lon] of the hotspots, about 200 m apart, for as many fires
    as fit in ZONE_POINTS; `truncated` says that some fires were left without points.
    """
    con = db()
    where, params = area_filter(west, south, east, north, country, admin1, lat="lat", lon="lon", size=0)
    fires = con.execute(f"""
        SELECT fire_id, round(lat, 4), round(lon, 4), hotspots::INTEGER, round(p_continue::DOUBLE, 3),
               round(r50_km::DOUBLE, 2), round(r80_km::DOUBLE, 2), round(r90_km::DOUBLE, 2),
               round(area50_km2::DOUBLE, 1), round(area80_km2::DOUBLE, 1), round(area90_km2::DOUBLE, 1),
               continued, next_hotspots::INTEGER, next_in_r80::INTEGER, admin1
        FROM zones WHERE burn_date = ? AND {where} ORDER BY hotspots DESC, fire_id
    """, [day, *params]).fetchall()
    seen = con.execute("SELECT max(seen_date) FROM zones WHERE burn_date = ?", [day]).fetchone()[0]
    sent, budget = [], ZONE_POINTS
    for f in fires:
        if f[3] > budget and sent:   # the largest fire always gets its points
            break
        sent.append(f[0])
        budget -= f[3]
    points = con.execute(
        "SELECT fire_id, lat, lon FROM zone_points WHERE burn_date = ? AND list_contains(?, fire_id) ORDER BY 1, 2, 3",
        [day, sent]).fetchall() if sent else []
    summary = {
        "fires": len(fires),
        "likely": sum(1 for f in fires if f[4] is not None and f[4] >= 0.5),
        "expected_continuing": round(sum(f[4] or 0 for f in fires), 1),
        "area80_km2": round(sum(f[9] or 0 for f in fires)),
    }
    return {"date": day, "seen_date": seen, "fires": fires, "points": points,
            "truncated": len(sent) < len(fires), "summary": summary}


@app.get("/api/calendar")
def calendar(
    west: Lon = None, south: Lat = None, east: Lon = None, north: Lat = None,
    country: str | None = None, admin1: str | None = None,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
    reference: Literal["recent", "all"] = "recent",
):
    """Harmonized hotspots per year and month for an area, with anomalies and the current period.

    An anomaly compares a month with the median of the same calendar month in the reference years
    (2013 onward, or every complete year with reference=all), leaving out the year being judged.
    The reference does not depend on the period asked for.
    """
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

    # Reference years: complete calendar years only, so a partial month never enters a median.
    first_year = first.year + (first != date(first.year, 1, 1))
    last_year = through.year - (through != date(through.year, 12, 31))
    ref_years = range(max(first_year, REFERENCE_START) if reference == "recent" else first_year, last_year + 1)
    ref = {(y, m): v for y, m, v in con.execute(f"""
        SELECT year(burn_date), month(burn_date), sum(hotspots_harmonized)
        FROM cells WHERE {where} AND year(burn_date) BETWEEN ? AND ? GROUP BY 1, 2
    """, [*params, ref_years.start, last_year]).fetchall()}

    # Every month of the range, including the ones without detections.
    last_month_partial = end.day < cal.monthrange(end.year, end.month)[1]
    months = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        hotspots, raw, provisional = found.get((y, m), (0.0, 0, False))
        partial = (y, m) == (end.year, end.month) and last_month_partial
        months.append({
            "year": y, "month": m, "hotspots": round(hotspots, 1), "raw": raw,
            "estimated": date(y, m, 1) < VIIRS_START, "provisional": bool(provisional),
            "partial": partial,
            # A partial month gets no ratio: it cannot be compared with complete months.
            **anomaly(None if partial else hotspots, [ref.get((yr, m), 0.0) for yr in ref_years if yr != y]),
        })
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)

    # The typical year: every reference year, nothing left out.
    median_by_month = [
        round(median(ref.get((yr, mm), 0.0) for yr in ref_years), 1) if ref_years else None
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
    # (1 to N) of the same month in the reference years.
    same_days = dict(con.execute(f"""
        SELECT year(burn_date), sum(hotspots_harmonized) FROM cells
        WHERE {where} AND month(burn_date) = ? AND day(burn_date) <= ? AND burn_date <= ?
        GROUP BY 1
    """, [*params, end.month, end.day, through]).fetchall())
    others = [same_days.get(yr, 0.0) for yr in ref_years if yr != end.year]
    now = same_days.get(end.year, 0.0)
    current = {
        "year": end.year, "month": end.month, "days": end.day, "hotspots": round(now, 1),
        **anomaly(now, others),
        "years_compared": len(others),
        "rank": 1 + sum(v > now for v in others) if others else None,
    }

    return {
        "from": start, "to": end, "data_through": through,
        "reference": {
            "mode": reference,
            "from_year": ref_years.start if ref_years else None,
            "to_year": last_year if ref_years else None,
        },
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
    """The hotspots of a search: FIRMS' UTC columns untouched, plus the local ones. Not harmonized.

    Same rows as the calendar: only hotspots that pass the quality filter of block 1.
    """
    con = db()
    # Written by scripts/harmonize.py: the same rows the calendar counts, already checked and with
    # the region corrected, so this endpoint has nothing to filter or validate.
    source = DATA / "harmonized" / "hotspots_kept.parquet"
    if not source.exists():
        raise HTTPException(503, f"{source} not found. Run scripts/harmonize.py.")
    where, params = area_filter(west, south, east, north, country, admin1, lat="latitude", lon="longitude", size=0)
    if start:
        where += " AND burn_date >= ?"
        params.append(start)
    if end:
        where += " AND burn_date <= ?"
        params.append(end)
    table = f"read_parquet('{source}')"

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
