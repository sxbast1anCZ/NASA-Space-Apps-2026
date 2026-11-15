"""Zones of likely activity around each active fire, for the next day (docs/findings/10-fire-zones.md).

For every fire seen on day D (hotspots of the target satellite linked closer than 1 km), two numbers
about day D+1, both measured on earlier years and never on the day they describe:

1. **Chance that the fire is still detected tomorrow**: the share of the fires of the same size (and
   country, and whether the fire was already active the day before) that had a hotspot within 2 km of
   their hotspots on the next day. A table, not a fitted model.
2. **Where its hotspots fall if it is**: the 50, 80 and 90% radii of the distance from each hotspot
   of the continuing fire on D+1 to the nearest hotspot of the fire on D. The zone of a fire is the
   union of circles of that radius around its hotspots, and its area is given in km2.

What it is not: burned area, a perimeter, a direction of spread or a forecast of new fires. A hotspot is
a thermal detection in a pixel, and the zone only says where the next detections of an active fire
usually fall. New ignitions are the next-day outlook (scripts/daily_train.py).

Definitions:
    Fire on D:               hotspots of D linked closer than LINK_KM (connected groups).
    Active the day before:   a hotspot of D-1 within CONT_KM of a hotspot of the fire.
    Continues on D+1:        a group of D+1 has a hotspot within CONT_KM of a hotspot of the fire. All
                             the hotspots of that group are the fire on D+1 (it may have spread far).
    Target satellite:        Suomi-NPP before 2026-11-01, NOAA-20 from then on. Never both.
    Outage days:             not observed. No fire is scored for a D+1 that was not observed.

Years: the table is fitted on predicted days (D+1) of 2013-2022 and scored on 2023-2025, then used
unchanged for the app days (2023 to the live day, the day after the last complete day).

Inputs (NASA_Data_Sources/processed/):
    harmonized/hotspots_kept.parquet, quality/outage_days.csv

Outputs (NASA_Data_Sources/processed/risk/):
    fire_zones.parquet         one row per fire of D, keyed by the predicted day burn_date = D+1
    fire_zone_points.parquet   the hotspots of each fire, thinned to about 200 m, for the map
    fire_zones.json            the table, the test scores and the run settings
    fire_zones.md              the same, as tables to read

Run:  python scripts/fire_zones.py
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from risk_baseline import NOAA20_START, VIIRS_START, load_outages, target_outage_days

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "NASA_Data_Sources" / "processed"
KEPT = DATA / "harmonized" / "hotspots_kept.parquet"
QUALITY = DATA / "quality"

LINK_KM = 1.0               # hotspots closer than this on one day are one fire (task T8)
CONT_KM = 2.0               # a fire continues if the next day has a hotspot this close to it
QUANTILES = (0.5, 0.8, 0.9)
SIZE_EDGES = (1, 4, 19, 99)   # hotspots on D: 1, 2-4, 5-19, 20-99, 100+
SIZE_LABELS = ("1", "2-4", "5-19", "20-99", "100+")
CALIB_UNTIL = 2022           # predicted days up to this year fit the table
TEST_YEARS = (2023, 2025)
APP_FROM = pd.Timestamp("2023-01-01")
MIN_FIRES = 200              # fewer fires (or hotspots, for a radius) in a group: use the wider group
THIN_DEG = 0.002             # points of the map file, about 200 m
KM_LAT = 110.574
EARTH_KM = 6371.0088         # mean radius
KM_LON = 111.320
ONE = pd.Timedelta(days=1)
_T0 = time.perf_counter()


def log(msg: str) -> None:
    print(f"[{time.perf_counter() - _T0:6.0f} s] {msg}", flush=True)


# ---------------------------------------------------------------- geometry

def to_km(lat, lon) -> np.ndarray:
    """Points on a sphere of radius EARTH_KM, as x, y, z in km.

    The straight-line distance between two of them is the great-circle distance to within one part in
    a million at the 0-50 km of this script, so a KD-tree on these coordinates links and measures
    correctly anywhere. (A plane x = lon * cos(lat) does not: with longitudes near -70 degrees, a small
    change of latitude moved x by hundreds of metres.)
    """
    lat, lon = np.radians(np.asarray(lat, dtype="float64")), np.radians(np.asarray(lon, dtype="float64"))
    c = np.cos(lat)
    return EARTH_KM * np.c_[c * np.cos(lon), c * np.sin(lon), np.sin(lat)]


def group_fires(xy: np.ndarray, link_km: float = LINK_KM) -> np.ndarray:
    """Fire id of each point: connected groups of points closer than `link_km`.

    Ids run from 0, largest fire first; ties keep the order of the first point, so the ids do not
    depend on how the graph library numbers its components.
    """
    n = len(xy)
    if n == 0:
        return np.zeros(0, dtype=np.int64)
    pairs = cKDTree(xy).query_pairs(link_km, output_type="ndarray")
    graph = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n))
    _, comp = connected_components(graph, directed=False)
    size = np.bincount(comp)
    first = np.full(len(size), n)
    np.minimum.at(first, comp, np.arange(n))
    order = np.lexsort((first, -size))          # largest first, then first point
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))
    return rank[comp]


def size_class(hotspots) -> np.ndarray:
    idx = np.searchsorted(np.asarray(SIZE_EDGES), np.asarray(hotspots), side="left")
    return np.asarray(SIZE_LABELS, dtype=object)[idx]


AREA_STEPS = 8           # grid of the area: radius / 8
_g = np.arange(-AREA_STEPS, AREA_STEPS + 1)
_dx, _dy = np.meshgrid(_g, _g, indexing="ij")
_DISK = np.c_[_dx.ravel(), _dy.ravel()][(_dx ** 2 + _dy ** 2).ravel() <= AREA_STEPS ** 2].astype(np.int64)
_DISK_KEY = (_DISK[:, 0] << 21) + _DISK[:, 1]        # offsets in the packed key (x << 21 | y)
_CELL_SCALE = np.pi * AREA_STEPS ** 2 / len(_DISK)   # 197 cells stand for one circle: one point gives pi r2


def union_areas(x, y, group, r, n_groups: int, max_cells: int = 4_000_000) -> np.ndarray:
    """Area of the union of circles around the points of each group, in the units of x and y squared.

    `x`, `y`: point coordinates; `group`: group of each point (0 .. n_groups-1, sorted); `r`: radius of
    each group. Each point paints the cells of a grid of step r/AREA_STEPS that lie within r of it; the
    area is the number of distinct cells times the cell size, scaled so that one point gives pi r2 exactly.
    Overlaps are within a few percent. (GEOS buffers of thousands of points take minutes per fire.)
    """
    x, y, group = np.asarray(x, dtype="float64"), np.asarray(y, dtype="float64"), np.asarray(group, dtype=np.int64)
    r = np.asarray(r, dtype="float64")
    area = np.full(n_groups, np.nan)
    ok = np.isfinite(r[group]) & (r[group] > 0)
    x, y, group = x[ok], y[ok], group[ok]
    if not len(group):
        return area
    step = r[group] / AREA_STEPS
    gx = np.round(x / step).astype(np.int64) + (1 << 20)
    gy = np.round(y / step).astype(np.int64) + (1 << 20)
    cells = np.zeros(n_groups, dtype=np.int64)
    bounds = np.flatnonzero(np.r_[True, group[1:] != group[:-1], True])   # start of each group, and the end
    per_chunk = max(max_cells // len(_DISK), 1)
    i = 0
    while i < len(bounds) - 1:
        j = i + 1
        while j < len(bounds) - 1 and bounds[j + 1] - bounds[i] <= per_chunk:
            j += 1
        sl = slice(bounds[i], bounds[j])
        key = ((group[sl] << 42) | (gx[sl] << 21) | gy[sl])[:, None] + _DISK_KEY   # one array, no copies
        key = np.unique(key.ravel())
        cells += np.bincount(key >> 42, minlength=n_groups)
        i = j
    has = np.zeros(n_groups, dtype=bool)
    has[group] = True
    rr = r / AREA_STEPS
    area[has] = cells[has] * rr[has] ** 2 * _CELL_SCALE
    return area


def zone_area_km2(lat, lon, r_km: float) -> float:
    """Area of the union of circles of radius `r_km` around the points, in km2."""
    lat, lon = np.asarray(lat, dtype="float64"), np.asarray(lon, dtype="float64")
    if len(lat) == 0:
        return 0.0
    lat0, lon0 = lat.mean(), lon.mean()
    x = (lon - lon0) * KM_LON * np.cos(np.radians(lat0))
    y = (lat - lat0) * KM_LAT
    return float(union_areas(x, y, np.zeros(len(x), dtype=np.int64), [r_km], 1)[0])


# ---------------------------------------------------------------- one day

def majority(lab: np.ndarray, values, n_fires: int) -> np.ndarray:
    """Per fire, the most frequent value; ties go to the first by name, and a missing value loses."""
    codes, names = pd.factorize(pd.Series(values, dtype=object), sort=True)
    codes = np.where(codes < 0, len(names), codes)          # missing: after every name
    key, count = np.unique(lab.astype(np.int64) * (len(names) + 1) + codes, return_counts=True)
    fire, code = key // (len(names) + 1), key % (len(names) + 1)
    order = np.lexsort((code, -count, fire))
    first = order[np.r_[True, fire[order][1:] != fire[order][:-1]]]
    out = np.full(n_fires, None, dtype=object)
    lookup = np.append(np.asarray(names, dtype=object), None)
    out[fire[first]] = lookup[code[first]]
    return out


def day_fires(day: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
    """Fire id of each hotspot of one day, and one row per fire.

    `day` has latitude, longitude, frp_mw, country, admin1 (one day, one satellite).
    Country and region of a fire: those of most of its hotspots, ties broken by name.
    """
    lat, lon = day["latitude"].to_numpy(dtype="float64"), day["longitude"].to_numpy(dtype="float64")
    lab = group_fires(to_km(lat, lon))
    n = int(lab.max()) + 1 if len(lab) else 0
    hot = np.bincount(lab, minlength=n)
    frp = day["frp_mw"].to_numpy(dtype="float64")
    seen = np.bincount(lab, weights=np.isfinite(frp), minlength=n)
    frp_sum = np.bincount(lab, weights=np.nan_to_num(frp), minlength=n)
    fires = pd.DataFrame({
        "fire_id": np.arange(n),
        "hotspots": hot,
        "frp_sum_mw": np.where(seen > 0, frp_sum, np.nan),
        "lat": np.bincount(lab, weights=lat, minlength=n) / hot,
        "lon": np.bincount(lab, weights=lon, minlength=n) / hot,
        "country": majority(lab, day["country"].to_numpy(), n),
        "admin1": majority(lab, day["admin1"].to_numpy(), n),
        "size_class": size_class(hot),
    })
    return lab, fires


def active_before(xy: np.ndarray, lab: np.ndarray, xy_prev: np.ndarray | None,
                  cont_km: float = CONT_KM) -> np.ndarray:
    """Per fire: a hotspot of the day before within `cont_km`. None (unknown) when D-1 was not observed."""
    n_fires = int(lab.max()) + 1 if len(lab) else 0
    if xy_prev is None:
        return np.full(n_fires, None, dtype=object)
    if not len(xy_prev):
        return np.zeros(n_fires, dtype=bool)
    d, _ = cKDTree(xy_prev).query(xy, distance_upper_bound=cont_km)
    return np.bincount(lab, weights=np.isfinite(d), minlength=n_fires) > 0


def continuation(xy: np.ndarray, lab: np.ndarray, xy_next: np.ndarray,
                 cont_km: float = CONT_KM, link_km: float = LINK_KM) -> tuple[np.ndarray, np.ndarray]:
    """The fire of D that each hotspot of D+1 belongs to (-1 for none), and its distance to that fire.

    The hotspots of D+1 are grouped like those of D. A group belongs to the fire of D that its closest
    hotspot within `cont_km` touches; the whole group goes with it. Distance: from each hotspot of the
    group to the nearest hotspot of its fire on D.
    """
    owner = np.full(len(xy_next), -1, dtype=np.int64)
    dist = np.full(len(xy_next), np.nan)
    if not len(xy) or not len(xy_next):
        return owner, dist
    nlab = group_fires(xy_next, link_km)
    near, idx = cKDTree(xy).query(xy_next, distance_upper_bound=cont_km)
    touch = np.isfinite(near)
    if not touch.any():
        return owner, dist
    t = pd.DataFrame({"g": nlab[touch], "fire": lab[idx[touch]], "d": near[touch], "i": np.flatnonzero(touch)})
    t = t.sort_values(["g", "d", "i"]).drop_duplicates("g")
    group_fire = np.full(int(nlab.max()) + 1, -1, dtype=np.int64)
    group_fire[t["g"].to_numpy()] = t["fire"].to_numpy()
    owner = group_fire[nlab]
    # nearest hotspot of the same fire: each fire sits in its own layer, far apart on a third axis
    sel = owner >= 0
    layer = 1e6
    tree = cKDTree(np.c_[xy, lab * layer])
    dist[sel] = tree.query(np.c_[xy_next[sel], owner[sel] * layer])[0]
    return owner, dist


# ---------------------------------------------------------------- table

LEVELS = (("country", "size_class", "active"), ("size_class", "active"), ("size_class",))


def calibrate(fires: pd.DataFrame, spread: pd.DataFrame, min_n: int | None = None) -> pd.DataFrame:
    """Chance of continuing and radii, for each group of the three levels of `LEVELS`.

    `fires`: one row per scored fire (country, size_class, active, continued).
    `spread`: one row per hotspot of a continuing fire on D+1 (country, size_class, active, dist_km).
    A group with fewer than `min_n` fires has no chance; one with fewer than `min_n` hotspots has no radii.
    `active` is None when the day before was not observed: those fires count only at the last level.
    """
    min_n = MIN_FIRES if min_n is None else min_n
    rows = []
    for level, keys in enumerate(LEVELS):
        f = fires if "active" not in keys else fires[fires["active"].notna()]
        s = spread if "active" not in keys else spread[spread["active"].notna()]
        f = f.assign(active=f["active"].astype(object)) if "active" in keys else f
        s = s.assign(active=s["active"].astype(object)) if "active" in keys else s
        chance = f.groupby(list(keys), observed=True)["continued"].agg(fires="size", p_continue="mean")
        radii = s.groupby(list(keys), observed=True)["dist_km"].agg(
            next_hotspots="size", **{f"r{int(q * 100)}_km": (lambda v, q=q: float(np.quantile(v, q))) for q in QUANTILES})
        t = chance.join(radii, how="outer").reset_index()
        t.loc[t["fires"].fillna(0) < min_n, "p_continue"] = np.nan
        t.loc[t["next_hotspots"].fillna(0) < min_n, [f"r{int(q * 100)}_km" for q in QUANTILES]] = np.nan
        t["level"] = level
        rows.append(t)
    out = pd.concat(rows, ignore_index=True)
    for k in ("country", "active"):
        if k not in out:
            out[k] = None
    out["active"] = out["active"].astype(object).where(out["active"].notna(), None)
    out["country"] = out["country"].astype(object).where(out["country"].notna(), None)
    return out[["level", "country", "size_class", "active", "fires", "p_continue", "next_hotspots",
                *[f"r{int(q * 100)}_km" for q in QUANTILES]]]


def lookup(table: pd.DataFrame, fires: pd.DataFrame) -> pd.DataFrame:
    """For each fire, the chance and radii of the narrowest group that has them (`LEVELS` in order).

    Adds p_continue, r50_km, r80_km, r90_km, and p_level / r_level (0 narrowest, 2 size only).
    """
    radii = [f"r{int(q * 100)}_km" for q in QUANTILES]
    out = fires.copy()
    out["p_continue"], out["p_level"], out["r_level"] = np.nan, -1, -1
    for c in radii:
        out[c] = np.nan
    for level, keys in enumerate(LEVELS):
        cols = list(keys)
        t = table.loc[table["level"] == level, cols + ["p_continue", *radii]].astype({c: object for c in cols})
        left = out[cols].astype(object).assign(_row=np.arange(len(out)))
        if "active" in cols:   # unknown is never a key: those fires wait for the size-only level
            left = left[left["active"].notna()]
            t = t[t["active"].notna()]
        m = left.merge(t, on=cols, how="inner")
        rows = m["_row"].to_numpy()
        take_p = (out["p_level"].to_numpy()[rows] < 0) & m["p_continue"].notna().to_numpy()
        out.iloc[rows[take_p], out.columns.get_loc("p_continue")] = m["p_continue"].to_numpy(dtype="float64")[take_p]
        out.iloc[rows[take_p], out.columns.get_loc("p_level")] = level
        take_r = (out["r_level"].to_numpy()[rows] < 0) & m[radii[0]].notna().to_numpy()
        for c in radii:
            out.iloc[rows[take_r], out.columns.get_loc(c)] = m[c].to_numpy(dtype="float64")[take_r]
        out.iloc[rows[take_r], out.columns.get_loc("r_level")] = level
    return out


# ---------------------------------------------------------------- scores

def evaluate(fires: pd.DataFrame, spread: pd.DataFrame) -> dict:
    """Scores of the table on unseen fires (`fires` already through `lookup`, `spread` with its radii).

    Chance: Brier score of the table and of one rate for all fires (the rate of the fitting years),
    and predicted against observed per size class. Zones: the share of the hotspots of continuing
    fires that fall inside each radius, which should be close to 50, 80 and 90%.
    """
    y = fires["continued"].astype(float).to_numpy()
    p = fires["p_continue"].to_numpy(dtype="float64")
    base = fires["base_rate"].to_numpy(dtype="float64")
    out = {
        "fires": int(len(fires)), "continued": int(y.sum()),
        "brier_table": float(np.mean((p - y) ** 2)), "brier_one_rate": float(np.mean((base - y) ** 2)),
    }
    out["brier_skill"] = 1 - out["brier_table"] / out["brier_one_rate"] if out["brier_one_rate"] else None
    by = []
    for (country, cls), g in fires.groupby(["country", "size_class"], observed=True):
        s = spread[(spread["country"] == country) & (spread["size_class"] == cls)]
        row = {"country": country, "size_class": cls, "fires": int(len(g)),
               "predicted": float(g["p_continue"].mean()), "observed": float(g["continued"].mean()),
               "next_hotspots": int(len(s)),
               "area_r80_km2_median": float(g["area80_km2"].median())}
        for q in QUANTILES:
            c = f"r{int(q * 100)}_km"
            row[f"inside_r{int(q * 100)}"] = float((s["dist_km"] <= s[c]).mean()) if len(s) else None
        by.append(row)
    out["by_class"] = by
    for q in QUANTILES:
        c = f"r{int(q * 100)}_km"
        out[f"inside_r{int(q * 100)}"] = float((spread["dist_km"] <= spread[c]).mean()) if len(spread) else None
    return out


# ---------------------------------------------------------------- the run

def load_target(path: Path) -> pd.DataFrame:
    """Hotspots of the target satellite: Suomi-NPP before the switch, NOAA-20 from it."""
    switch = NOAA20_START.date()
    return duckdb.sql(f"""
        SELECT burn_date, latitude, longitude, frp_mw, country, admin1
        FROM read_parquet('{path}')
        WHERE burn_date >= DATE '{VIIRS_START.date()}'
          AND ((satellite = 'Suomi-NPP' AND burn_date < DATE '{switch}')
            OR (satellite = 'NOAA-20' AND burn_date >= DATE '{switch}'))
        ORDER BY burn_date, latitude, longitude
    """).df().assign(burn_date=lambda d: pd.to_datetime(d["burn_date"]))


def run_days(hot: pd.DataFrame, outage_days: set, app_from: pd.Timestamp = APP_FROM):
    """Fires of every observed day D, with what D+1 showed when it was observed.

    Returns (fires, spread, points): fires keyed by burn_date = D+1; spread has one row per hotspot
    of a continuing fire on D+1; points are the hotspots of the fires of app days, thinned.
    The last day of `hot` is the live predicted day: its D is the last complete day.
    """
    by_day = {d: g for d, g in hot.groupby("burn_date", sort=True)}
    first, live = min(by_day), max(by_day)
    last = live - ONE
    days = pd.date_range(first, last, freq="D")
    observed = {d for d in days if d not in outage_days}
    fire_rows, spread_rows, point_rows = [], [], []
    empty = hot.iloc[:0]
    for D in days:
        if D.month == 1 and D.day == 1:
            log(f"fires of {D.year}")
        if D not in observed:
            continue
        today = by_day.get(D, empty)
        if today.empty:
            continue
        nxt = D + ONE
        nxt_seen = nxt <= last and nxt in observed
        prev_seen = (D - ONE) in observed and D - ONE >= first
        xy = to_km(today["latitude"], today["longitude"])
        lab, fires = day_fires(today)
        prev = by_day.get(D - ONE, empty)
        fires["active"] = active_before(xy, lab, to_km(prev["latitude"], prev["longitude"]) if prev_seen else None)
        fires["burn_date"], fires["seen_date"] = nxt, D
        if nxt_seen:
            tomorrow = by_day.get(nxt, empty)
            owner, dist = continuation(xy, lab, to_km(tomorrow["latitude"], tomorrow["longitude"]))
            fires["continued"] = np.bincount(owner[owner >= 0], minlength=len(fires)) > 0
            fires["next_hotspots"] = np.bincount(owner[owner >= 0], minlength=len(fires))
            if (owner >= 0).any():
                s = pd.DataFrame({"fire_id": owner[owner >= 0], "dist_km": dist[owner >= 0]})
                s = s.merge(fires[["fire_id", "country", "size_class", "active"]], on="fire_id")
                s["burn_date"] = nxt
                spread_rows.append(s)
        else:
            fires["continued"], fires["next_hotspots"] = None, None
        fire_rows.append(fires)
        if nxt >= app_from:
            pts = pd.DataFrame({"fire_id": lab,
                                "lat": np.round(np.round(today["latitude"].to_numpy() / THIN_DEG) * THIN_DEG, 3),
                                "lon": np.round(np.round(today["longitude"].to_numpy() / THIN_DEG) * THIN_DEG, 3)})
            pts = pts.drop_duplicates()
            pts["burn_date"] = nxt
            point_rows.append(pts)
    fires = pd.concat(fire_rows, ignore_index=True)
    spread = pd.concat(spread_rows, ignore_index=True) if spread_rows else pd.DataFrame(
        columns=["fire_id", "dist_km", "country", "size_class", "active", "burn_date"])
    points = pd.concat(point_rows, ignore_index=True) if point_rows else pd.DataFrame(
        columns=["fire_id", "lat", "lon", "burn_date"])
    return fires, spread, points


def add_areas(fires: pd.DataFrame, points: pd.DataFrame) -> pd.DataFrame:
    """Zone areas (km2) of each fire: union of circles of its radii around its thinned points."""
    out = fires.reset_index(drop=True)
    pts = points.merge(out[["burn_date", "fire_id"]].assign(_fire=np.arange(len(out))), on=["burn_date", "fire_id"])
    pts = pts.sort_values("_fire", kind="stable")
    f = pts["_fire"].to_numpy()
    lat0 = out["lat"].to_numpy()[f]
    x = (pts["lon"].to_numpy() - out["lon"].to_numpy()[f]) * KM_LON * np.cos(np.radians(lat0))
    y = (pts["lat"].to_numpy() - lat0) * KM_LAT
    for q in QUANTILES:
        out[f"area{int(q * 100)}_km2"] = union_areas(x, y, f, out[f"r{int(q * 100)}_km"].to_numpy(), len(out))
    out.index = fires.index
    return out


def to_markdown(model: dict) -> str:
    def f(v, pct=False):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return ""
        return f"{100 * v:.1f}%" if pct else (f"{v:,.2f}" if isinstance(v, float) else f"{v:,}")

    ev = model["test"]
    out = ["# Zones of likely activity around active fires", "",
           f"Table fitted on predicted days up to {CALIB_UNTIL}, scored on {TEST_YEARS[0]}-{TEST_YEARS[1]}. "
           f"A fire continues if the next day has a hotspot within {CONT_KM:g} km of it.", "",
           "## Test, all fires", "",
           "| Fires | Continued | Brier, table | Brier, one rate | Skill | Inside r50 | Inside r80 | Inside r90 |",
           "|---|---|---|---|---|---|---|---|",
           f"| {f(ev['fires'])} | {f(ev['continued'])} | {ev['brier_table']:.4f} | {ev['brier_one_rate']:.4f} | "
           f"{f(ev['brier_skill'], True)} | {f(ev['inside_r50'], True)} | {f(ev['inside_r80'], True)} | "
           f"{f(ev['inside_r90'], True)} |", "",
           "## Test, by country and size (hotspots of the fire on D)", "",
           "| Country | Size | Fires | Chance given | Share that continued | Next-day hotspots | Inside r50 | "
           "Inside r80 | Inside r90 | Median zone r80 (km2) |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    order = {c: i for i, c in enumerate(SIZE_LABELS)}
    for r in sorted(ev["by_class"], key=lambda r: (r["country"], order[r["size_class"]])):
        out.append(f"| {r['country']} | {r['size_class']} | {f(r['fires'])} | {f(r['predicted'], True)} | "
                   f"{f(r['observed'], True)} | {f(r['next_hotspots'])} | {f(r['inside_r50'], True)} | "
                   f"{f(r['inside_r80'], True)} | {f(r['inside_r90'], True)} | {f(r['area_r80_km2_median'])} |")
    out += ["", "## The table (fitted years)", "",
            "| Level | Country | Size | Active the day before | Fires | Chance | Next-day hotspots | r50 km | r80 km | r90 km |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for r in model["table"]:
        out.append(f"| {r['level']} | {r['country'] or 'both'} | {r['size_class']} | "
                   f"{'' if r['active'] is None else ('yes' if r['active'] else 'no')} | {f(r['fires'])} | "
                   f"{f(r['p_continue'], True)} | {f(r['next_hotspots'])} | {f(r['r50_km'])} | {f(r['r80_km'])} | "
                   f"{f(r['r90_km'])} |")
    return "\n".join(out) + "\n"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kept", type=Path, default=KEPT)
    ap.add_argument("--quality", type=Path, default=QUALITY)
    ap.add_argument("--out", type=Path, default=DATA / "risk")
    ap.add_argument("--app-from", default=str(APP_FROM.date()), help="first predicted day written for the app")
    args = ap.parse_args(argv)
    if not args.kept.exists():
        raise SystemExit(f"{args.kept} not found (docs/eda-runbook.md, step 7)")

    hot = load_target(args.kept)
    log(f"{len(hot):,} hotspots of the target satellite")
    outage_days = target_outage_days(load_outages(args.quality), "reference", NOAA20_START)
    fires, spread, points = run_days(hot, outage_days, pd.Timestamp(args.app_from))
    year = fires["burn_date"].dt.year
    scored = fires["continued"].notna()
    calib = scored & (year <= CALIB_UNTIL)
    test = scored & year.between(*TEST_YEARS)
    log(f"{len(fires):,} fires and {len(spread):,} next-day hotspots of continuing fires")
    s_year = spread["burn_date"].dt.year
    table = calibrate(fires[calib], spread[s_year <= CALIB_UNTIL])
    if table.loc[table["level"] == len(LEVELS) - 1, ["p_continue", "r80_km"]].isna().any().any():
        raise SystemExit("Too few fitted fires for some size class: the table has gaps")

    app = fires["burn_date"] >= pd.Timestamp(args.app_from)
    keep = (app | test).to_numpy()
    zoned = lookup(table, fires[keep]).set_index(fires.index[keep])
    log(f"table fitted; zones for {len(zoned):,} fires")
    zoned = add_areas(zoned, points)
    log("areas done")
    zoned["base_rate"] = float(fires.loc[calib, "continued"].astype(float).mean())

    t_spread = spread[s_year.between(*TEST_YEARS)].merge(
        zoned.loc[zoned.index.isin(fires.index[test]), ["burn_date", "fire_id", "r50_km", "r80_km", "r90_km"]],
        on=["burn_date", "fire_id"])
    ev = evaluate(zoned.loc[zoned.index.isin(fires.index[test])], t_spread)
    log("test scored")

    # observed outcome of each app fire: hotspots of its continuation inside the 80% zone
    inside = (spread.merge(zoned[["burn_date", "fire_id", "r80_km"]], on=["burn_date", "fire_id"])
              .assign(inside=lambda d: d["dist_km"] <= d["r80_km"])
              .groupby(["burn_date", "fire_id"])["inside"].sum().rename("next_in_r80"))
    out = zoned[app[keep].to_numpy()].merge(inside, on=["burn_date", "fire_id"], how="left")
    out.loc[out["continued"].notna() & out["next_in_r80"].isna(), "next_in_r80"] = 0
    cols = ["burn_date", "seen_date", "fire_id", "lat", "lon", "country", "admin1", "hotspots", "frp_sum_mw",
            "size_class", "active", "p_continue", "r50_km", "r80_km", "r90_km",
            "area50_km2", "area80_km2", "area90_km2", "continued", "next_hotspots", "next_in_r80"]
    out = out[cols].copy()
    out["burn_date"] = out["burn_date"].dt.date
    out["seen_date"] = out["seen_date"].dt.date
    for c in ("active", "continued"):
        out[c] = out[c].astype("boolean")
    for c in ("next_hotspots", "next_in_r80"):
        out[c] = out[c].astype("Int64")
    pts = points[points["burn_date"] >= pd.Timestamp(args.app_from)].copy()
    pts["burn_date"] = pts["burn_date"].dt.date

    args.out.mkdir(parents=True, exist_ok=True)
    out.sort_values(["burn_date", "fire_id"]).to_parquet(args.out / "fire_zones.parquet", index=False)
    pts[["burn_date", "fire_id", "lat", "lon"]].sort_values(["burn_date", "fire_id"]).to_parquet(
        args.out / "fire_zone_points.parquet", index=False)
    model = {
        "settings": {"link_km": LINK_KM, "cont_km": CONT_KM, "quantiles": list(QUANTILES),
                     "size_classes": list(SIZE_LABELS), "fit_until": CALIB_UNTIL, "test_years": list(TEST_YEARS),
                     "min_group": MIN_FIRES, "app_from": args.app_from},
        "days": {"first": str(hot["burn_date"].min().date()), "live_predicted_day": str(hot["burn_date"].max().date())},
        "fitted": {"fires": int(calib.sum()), "continued": int(fires.loc[calib, "continued"].sum()),
                   "base_rate": float(fires.loc[calib, "continued"].astype(float).mean())},
        "table": json.loads(table.to_json(orient="records")),
        "test": ev,
    }
    (args.out / "fire_zones.json").write_text(json.dumps(model, indent=1))
    (args.out / "fire_zones.md").write_text(to_markdown(model))
    print(f"Fires fitted: {model['fitted']['fires']:,} | test: {ev['fires']:,} | "
          f"Brier skill {ev['brier_skill']:.1%} | inside r50/r80/r90: "
          f"{ev['inside_r50']:.1%} / {ev['inside_r80']:.1%} / {ev['inside_r90']:.1%}")
    print(f"App fires: {len(out):,} from {out['burn_date'].min()} to {out['burn_date'].max()}")
    print(f"Written: {args.out / 'fire_zones.parquet'}, fire_zone_points.parquet, fire_zones.json, fire_zones.md")


if __name__ == "__main__":
    main()
