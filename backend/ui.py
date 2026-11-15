"""Extra endpoints for the full-screen map (frontend/src/studio).

Run from the repo root:
    uvicorn backend.ui:app --reload --port 8000

Adds, under /api/ui/, what the full-screen map needs on top of backend/main.py:
    hotspots    individual hotspots of a short period, columnar, for the WebGL layers
    days        harmonized hotspots per day for the timeline
    density     harmonized hotspots per cell for a period (history mode)
    regimes     fire regimes of block 5
    static      persistent static sources of block 1
    regions     per region: last 7 days against the same 7 days of 2013-2025, alerts for tomorrow
    boundaries  simplified region outlines (GeoJSON)
    series      yearly raw MODIS / VIIRS and harmonized totals for an area (science view)
"""

from __future__ import annotations

import json
import threading
from datetime import date, timedelta
from functools import lru_cache
from statistics import median
from typing import Annotated, Literal

from fastapi import HTTPException, Query

from backend import main
from backend.main import ROOT, Lat, Lon, app, area_filter, data_through, db

SAT_CODE = {"Terra": 0, "Aqua": 1, "Suomi-NPP": 2, "NOAA-20": 3, "NOAA-21": 4}
MAX_DAYS = 45
MAX_POINTS = 250_000
From = Annotated[date, Query(alias="from")]
To = Annotated[date, Query(alias="to")]


def kept() -> str:
    source = main.DATA / "harmonized" / "hotspots_kept.parquet"
    if not source.exists():
        raise HTTPException(503, f"{source} not found. Run scripts/harmonize.py.")
    return f"read_parquet('{source}')"


@app.get("/api/ui/hotspots")
def ui_hotspots(start: From, end: To, west: Lon = None, south: Lat = None, east: Lon = None, north: Lat = None):
    """Hotspots between two burn dates (both included), as columns.

    day is the number of days since `from`. sat: 0 Terra, 1 Aqua, 2 Suomi-NPP, 3 NOAA-20, 4 NOAA-21.
    """
    if end < start or (end - start).days > MAX_DAYS:
        raise HTTPException(422, f"Choose up to {MAX_DAYS} days")
    con = db()
    where, params = area_filter(west, south, east, north, None, None, lat="latitude", lon="longitude", size=0)
    rows = con.execute(f"""
        SELECT round(longitude, 4), round(latitude, 4), round(coalesce(frp_mw, 0), 1),
               satellite, daynight = 'N', date_diff('day', ?::DATE, burn_date),
               coalesce(confidence_level, 'nominal'), strftime(local_wall_time, '%H:%M'), admin1
        FROM {kept()} WHERE {where} AND burn_date BETWEEN ? AND ?
        ORDER BY frp_mw DESC NULLS LAST LIMIT {MAX_POINTS + 1}
    """, [start, *params, start, end]).fetchall()
    truncated = len(rows) > MAX_POINTS
    rows = rows[:MAX_POINTS]
    cols = list(zip(*rows)) if rows else [()] * 9
    return {
        "from": start, "to": end, "count": len(rows), "truncated": truncated,
        "lon": cols[0], "lat": cols[1], "frp": cols[2], "sat": [SAT_CODE.get(s, 9) for s in cols[3]],
        "night": [int(n) for n in cols[4]], "day": cols[5],
        "conf": [{"low": 0, "nominal": 1, "high": 2}.get(c, 1) for c in cols[6]],
        "time": cols[7], "region": cols[8],
    }


@app.get("/api/ui/days")
def ui_days(start: From, end: To, west: Lon = None, south: Lat = None, east: Lon = None, north: Lat = None,
            country: str | None = None, admin1: str | None = None):
    """Harmonized hotspots per burn date, with the median of the same calendar day in 2013-2025."""
    con = db()
    where, params = area_filter(west, south, east, north, country, admin1)
    found = dict(con.execute(f"""
        SELECT burn_date, sum(hotspots_harmonized) FROM cells
        WHERE {where} AND burn_date BETWEEN ? AND ? GROUP BY 1
    """, [*params, start, end]).fetchall())
    ref = con.execute(f"""
        SELECT month(burn_date), day(burn_date), list(s) FROM (
            SELECT burn_date, sum(hotspots_harmonized) s FROM cells
            WHERE {where} AND year(burn_date) BETWEEN 2013 AND 2025 GROUP BY 1) GROUP BY 1, 2
    """, params).fetchall()
    ref = {(m, d): v for m, d, v in ref}
    out, d = [], start
    while d <= end:
        vals = ref.get((d.month, d.day), [])
        vals = vals + [0.0] * (13 - len(vals))  # days without detections in a year count as zero
        out.append({"date": d, "hotspots": round(found.get(d, 0.0), 1), "median": round(median(vals), 1)})
        d += timedelta(days=1)
    return {"days": out, "data_through": data_through(con)}


@app.get("/api/ui/density")
def ui_density(start: From, end: To, sensor: Literal["harmonized", "modis", "viirs"] = "harmonized",
               min_conf: Annotated[int, Query(ge=0, le=2)] = 0, min_frp: Annotated[float, Query(ge=0)] = 0,
               time: Literal["all", "day", "night"] = "all"):
    """Hotspots per 0.25 degree cell for a period: [cell_lat, cell_lon, hotspots].

    harmonized: the VIIRS-equivalent series (sensor of each period, MODIS scaled before 2012).
    modis / viirs: raw detections of that instrument, where the confidence, power and day/night
    filters apply. Comparing the two raw maps over 2012-2026 shows why harmonization is needed.
    """
    con = db()
    if sensor == "harmonized":
        rows = con.execute("""
            SELECT cell_lat, cell_lon, round(sum(hotspots_harmonized), 1) FROM cells
            WHERE burn_date BETWEEN ? AND ? GROUP BY 1, 2 HAVING sum(hotspots_harmonized) > 0
        """, [start, end]).fetchall()
        return {"from": start, "to": end, "sensor": sensor, "cells": rows, "estimated": start < date(2012, 2, 1)}
    where = ["burn_date BETWEEN ? AND ?", "instrument = ?"]
    params: list = [start, end, sensor.upper()]
    if min_conf:
        where.append("confidence_level IN ('nominal', 'high')" if min_conf == 1 else "confidence_level = 'high'")
    if min_frp:
        where.append("frp_mw >= ?")
        params.append(min_frp)
    if time != "all":
        where.append("daynight = ?")
        params.append("D" if time == "day" else "N")
    rows = con.execute(f"""
        SELECT floor(latitude / 0.25) * 0.25, floor(longitude / 0.25) * 0.25, count(*)::DOUBLE FROM {kept()}
        WHERE {' AND '.join(where)} GROUP BY 1, 2
    """, params).fetchall()
    return {"from": start, "to": end, "sensor": sensor, "cells": rows, "estimated": False}


@app.get("/api/ui/yearly")
@lru_cache(maxsize=1)
def ui_yearly():
    """Per burn year: raw MODIS, raw VIIRS and harmonized hotspots, for the history timeline."""
    con = db()
    raw = con.execute(f"""
        SELECT burn_year, count(*) FILTER (WHERE instrument = 'MODIS'), count(*) FILTER (WHERE instrument = 'VIIRS')
        FROM {kept()} GROUP BY 1
    """).fetchall()
    harm = dict(con.execute("SELECT year(burn_date), sum(hotspots_harmonized) FROM cells GROUP BY 1").fetchall())
    return {"years": [{"year": y, "modis": m, "viirs": v, "harmonized": round(harm.get(y, 0.0), 1)}
                      for y, m, v in sorted(raw) if y >= 2001]}


@app.get("/api/ui/regimes")
@lru_cache(maxsize=1)
def ui_regimes():
    path = main.DATA / "spatial" / "cell_regimes.parquet"
    if not path.exists():
        return {"cells": [], "names": []}
    con = db()
    rows = con.execute(f"""
        SELECT cell_lat, cell_lon, regime, peak_month, round(hotspots_per_km2_year, 4)
        FROM read_parquet('{path}')
    """).fetchall()
    return {"cells": rows, "names": ["Winter-spring", "January pulse", "Late summer", "December pulse"]}


@app.get("/api/ui/static")
@lru_cache(maxsize=1)
def ui_static():
    path = main.DATA / "quality" / "static_mask_cells.parquet"
    if not path.exists():
        return {"points": []}
    return {"points": db().execute(f"SELECT lat, lon, ndays FROM read_parquet('{path}')").fetchall()}


_lock = threading.Lock()
_ready: set[str] = set()


def _cell_region():
    with _lock:
        if "cell_region" in _ready:
            return True
        _make_cell_region()
        _ready.add("cell_region")
    return True


def _make_cell_region():
    con = db()
    con.execute("""
        CREATE OR REPLACE TABLE cell_region AS
        SELECT cell_lat, cell_lon, arg_max(country, n) country, arg_max(admin1, n) admin1 FROM (
            SELECT cell_lat, cell_lon, country, admin1, sum(hotspots_raw) n FROM cells
            WHERE admin1 IS NOT NULL GROUP BY ALL) GROUP BY 1, 2
    """)
    return True


@app.get("/api/ui/regions")
def ui_regions(day: Annotated[date | None, Query(alias="date")] = None):
    """Per region: hotspots in the 7 days to `date` (default: last complete day) against the median
    of the same 7 calendar days in 2013-2025, and the cells in alert in the newest outlook."""
    con = db()
    through = min(day or data_through(con), data_through(con))
    now = dict(((c, a), v) for c, a, v in con.execute("""
        SELECT country, admin1, sum(hotspots_harmonized) FROM cells
        WHERE admin1 IS NOT NULL AND burn_date BETWEEN ? AND ? GROUP BY 1, 2
    """, [through - timedelta(days=6), through]).fetchall())
    ref: dict = {}
    for yr in range(2013, 2026):
        if yr == through.year:
            continue
        try:
            end = through.replace(year=yr)
        except ValueError:  # 29 February
            end = through.replace(year=yr, day=28)
        for c, a, v in con.execute("""
            SELECT country, admin1, sum(hotspots_harmonized) FROM cells
            WHERE admin1 IS NOT NULL AND burn_date BETWEEN ? AND ? GROUP BY 1, 2
        """, [end - timedelta(days=6), end]).fetchall():
            ref.setdefault((c, a), {})[yr] = v
    live = con.execute("SELECT max(burn_date) FROM daily_days").fetchone()[0]
    alerts = dict(((c, a), (n, p)) for c, a, n, p in con.execute("""
        SELECT r.country, r.admin1, sum(d.alert)::INT, max(d.probability) FROM daily d
        JOIN (SELECT cell_lat, cell_lon, arg_max(country, n) country, arg_max(admin1, n) admin1 FROM (
            SELECT cell_lat, cell_lon, country, admin1, sum(hotspots_raw) n FROM cells
            WHERE admin1 IS NOT NULL GROUP BY ALL) GROUP BY 1, 2) r USING (cell_lat, cell_lon) WHERE d.burn_date = ? GROUP BY 1, 2
    """, [live]).fetchall()) if live else {}
    bounds = {(c, a): b for c, a, *b in con.execute(f"""
        SELECT country, admin1, min(cell_lon), min(cell_lat), max(cell_lon) + 0.25, max(cell_lat) + 0.25
        FROM (SELECT cell_lat, cell_lon, arg_max(country, n) country, arg_max(admin1, n) admin1 FROM (
            SELECT cell_lat, cell_lon, country, admin1, sum(hotspots_raw) n FROM cells
            WHERE admin1 IS NOT NULL GROUP BY ALL) GROUP BY 1, 2) GROUP BY 1, 2
    """).fetchall()}
    years = [y for y in range(2013, 2026) if y != through.year]
    out = []
    for key, b in bounds.items():
        vals = [ref.get(key, {}).get(y, 0.0) for y in years]
        med = median(vals)
        n = now.get(key, 0.0)
        n_alert, p_max = alerts.get(key, (0, None))
        out.append({
            "country": key[0], "admin1": key[1], "hotspots_7d": round(n, 1), "median_7d": round(med, 1),
            "ratio": round((n + 1) / (med + 1), 2), "reliable": med >= 10,
            "alerts": n_alert, "max_probability": None if p_max is None else round(p_max, 3), "bounds": b,
        })
    out.sort(key=lambda r: -r["hotspots_7d"])
    return {"through": through, "outlook_day": live, "regions": out}


@app.get("/api/ui/series")
def ui_series(west: Lon = None, south: Lat = None, east: Lon = None, north: Lat = None,
              country: str | None = None, admin1: str | None = None):
    """Per year: raw MODIS hotspots, raw VIIRS hotspots and the harmonized series."""
    con = db()
    where, params = area_filter(west, south, east, north, country, admin1)
    rows = con.execute(f"""
        SELECT year(burn_date) y, sensor, sum(hotspots_raw), sum(hotspots_harmonized) FROM cells
        WHERE {where} GROUP BY 1, 2 ORDER BY 1
    """, params).fetchall()
    out: dict = {}
    for y, sensor, raw, harm in rows:
        r = out.setdefault(y, {"year": y, "modis_raw": 0, "viirs_raw": 0, "harmonized": 0.0})
        r["modis_raw" if str(sensor).upper().startswith("MODIS") else "viirs_raw"] += raw
        r["harmonized"] += harm
    for r in out.values():
        r["harmonized"] = round(r["harmonized"], 1)
    sensors = [s for (s,) in con.execute("SELECT DISTINCT sensor FROM cells").fetchall()]
    return {"years": list(out.values()), "sensors": sensors}


@app.get("/api/ui/boundaries")
@lru_cache(maxsize=1)
def ui_boundaries():
    """Region outlines, simplified to about 2 km and clipped to the mainland box."""
    cache = main.DATA / "ui" / "boundaries.geojson"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    import shapely
    from shapely.geometry import box, mapping, shape

    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_hotspots import NAME_KEYS, fix_mojibake

    clip = box(-110, -56, -50, -17)
    features = []
    for f in sorted((ROOT / "NASA_Data_Sources" / "boundaries").glob("*.geojson")):
        gj = json.loads(f.read_text(encoding="utf-8"))
        for feat in gj["features"]:
            props = feat.get("properties") or {}
            name = fix_mojibake(next((props[k] for k in NAME_KEYS if props.get(k)), ""))
            geom = shapely.make_valid(shape(feat["geometry"])).intersection(clip)
            geom = shapely.simplify(geom, 0.02, preserve_topology=True)
            if geom.is_empty:
                continue
            geom = shapely.set_precision(geom, 0.001)
            features.append({"type": "Feature", "properties": {"country": f.stem, "admin1": name},
                             "geometry": mapping(geom)})
    # Everything outside Chile and Argentina, to dim the rest of the continent.
    land = shapely.unary_union([shape(f["geometry"]).buffer(0.02) for f in features]).buffer(-0.01)
    mask = shapely.simplify(box(-180, -85, 180, 85).difference(land), 0.02)
    features.append({"type": "Feature", "properties": {"mask": True}, "geometry": mapping(mask)})
    out = {"type": "FeatureCollection", "features": features}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out), encoding="utf-8")
    return out


# ---------------------------------------------------------------- towns and wind field

@app.get("/api/ui/towns")
@lru_cache(maxsize=1)
def ui_towns():
    """Towns of Chile and Argentina with at least 5,000 people (GeoNames cities5000, CC BY 4.0):
    [name, lat, lon, population, region]."""
    path = ROOT / "NASA_Data_Sources" / "geonames" / "cl_ar.tsv"
    if not path.exists():
        return {"towns": []}
    import shapely
    from shapely.geometry import shape

    regions = [(f["properties"]["admin1"], shape(f["geometry"])) for f in ui_boundaries()["features"]
               if not f["properties"].get("mask")]
    for _, g in regions:
        shapely.prepare(g)
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        c = line.split("\t")
        name, lat, lon, pop = c[1], float(c[4]), float(c[5]), int(c[14] or 0)
        if pop < 5000:
            continue
        region = next((r for r, g in regions if shapely.contains_xy(g, lon, lat)), None)
        out.append([name, round(lat, 4), round(lon, 4), pop, region])
    out.sort(key=lambda t: -t[3])
    return {"towns": out, "source": "GeoNames cities5000 (CC BY 4.0)"}


WIND_BOX = (-77.0, -56.0, -52.0, -17.0)  # west, south, east, north
WIND_STEP = 1.5
_wind_lock = threading.Lock()


@app.get("/api/ui/windfield")
def ui_windfield(day: Annotated[date, Query(alias="date")]):
    """Wind at 10 m on a 1.5 degree grid for one day, at 18 UTC (mid afternoon in both countries),
    from Open-Meteo (forecast API for recent days, ERA5 archive before). u and v in km/h,
    rows south to north, columns west to east."""
    import httpx

    cache = main.DATA / "ui" / f"wind_{day}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    w, s, e, n = WIND_BOX
    lats = [s + i * WIND_STEP for i in range(int((n - s) / WIND_STEP) + 1)]
    lons = [w + j * WIND_STEP for j in range(int((e - w) / WIND_STEP) + 1)]
    points = [(la, lo) for la in lats for lo in lons]
    recent = (date.today() - day).days < 80
    url = "https://api.open-meteo.com/v1/forecast" if recent else "https://archive-api.open-meteo.com/v1/archive"
    speed, direc = [], []
    with _wind_lock, httpx.Client(timeout=60) as client:
        for k in range(0, len(points), 100):
            chunk = points[k:k + 100]
            r = client.get(url, params={
                "latitude": ",".join(f"{p[0]:.2f}" for p in chunk), "longitude": ",".join(f"{p[1]:.2f}" for p in chunk),
                "hourly": "wind_speed_10m,wind_direction_10m", "start_date": str(day), "end_date": str(day),
                "timezone": "UTC", "wind_speed_unit": "kmh",
            })
            if r.status_code != 200:
                raise HTTPException(502, f"Open-Meteo: {r.text[:200]}")
            body = r.json()
            for loc in body if isinstance(body, list) else [body]:
                h = loc["hourly"]
                i = h["time"].index(f"{day}T18:00") if f"{day}T18:00" in h["time"] else len(h["time"]) // 2
                speed.append(h["wind_speed_10m"][i])
                direc.append(h["wind_direction_10m"][i])
    import math
    u, v = [], []
    for sp, d in zip(speed, direc):
        if sp is None or d is None:
            u.append(0.0); v.append(0.0)
            continue
        a = math.radians(d)  # direction the wind comes FROM
        u.append(round(-sp * math.sin(a), 2))
        v.append(round(-sp * math.cos(a), 2))
    out = {"date": day, "hour_utc": 18, "west": w, "south": s, "step": WIND_STEP, "nx": len(lons), "ny": len(lats),
           "u": u, "v": v, "max": round(max(speed or [0]) or 0, 1), "source": "Open-Meteo"}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, default=str))
    return out


_weather: dict = {}


@app.get("/api/ui/weather")
def ui_weather(lat: Annotated[float, Query(ge=-90, le=90)], lon: Annotated[float, Query(ge=-180, le=180)]):
    """Current weather at a point (Open-Meteo), with its IANA time zone. Cached 10 minutes."""
    import time

    import httpx

    key = (round(lat, 2), round(lon, 2))
    hit = _weather.get(key)
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    r = httpx.get("https://api.open-meteo.com/v1/forecast", timeout=20, params={
        "latitude": key[0], "longitude": key[1], "timezone": "auto", "wind_speed_unit": "kmh",
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,"
                   "wind_speed_10m,wind_direction_10m,wind_gusts_10m,is_day",
        "daily": "temperature_2m_max,temperature_2m_min,sunrise,sunset", "forecast_days": 1,
    })
    if r.status_code != 200:
        raise HTTPException(502, f"Open-Meteo: {r.text[:200]}")
    j = r.json()
    out = {"timezone": j.get("timezone"), "utc_offset_seconds": j.get("utc_offset_seconds"), "current": j.get("current"),
           "daily": {k: v[0] for k, v in (j.get("daily") or {}).items() if v}, "source": "Open-Meteo"}
    _weather[key] = (time.time(), out)
    return out


# backend/main.py mounts the built web app at "/" when frontend/dist exists. Routes added after a
# mount never match, so the mount goes back to the end of the list.
app.router.routes.sort(key=lambda route: type(route).__name__ == "Mount")
