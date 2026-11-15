"""Hand-made and synthetic cases for scripts/fire_zones.py (docs/findings/10-fire-zones.md)."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import fire_zones as fz  # noqa: E402

LAT0, LON0 = -38.0, -71.0
KM_X = fz.KM_LON * np.cos(np.radians(LAT0))


def at(km_east, km_north):
    """Latitude and longitude of points given in km from (LAT0, LON0)."""
    e, n = np.atleast_1d(km_east).astype(float), np.atleast_1d(km_north).astype(float)
    return LAT0 + n / fz.KM_LAT, LON0 + e / KM_X


def xy(km_east, km_north):
    return fz.to_km(*at(km_east, km_north))


# ---------------------------------------------------------------- geometry

def test_groups_chain_links_and_a_gap_splits():
    # 0, 0.9, 1.8 km form one chain; 3.0 km is 1.2 km from the chain: a fire of its own
    lab = fz.group_fires(xy([0, 0.9, 1.8, 3.0], [0, 0, 0, 0]))
    assert lab[0] == lab[1] == lab[2] != lab[3]


def test_group_ids_go_largest_first_and_do_not_depend_on_order():
    e = [50, 0, 0.5, 1.0, 20, 20.5]
    lab = fz.group_fires(xy(e, [0] * 6))
    assert lab.tolist() == [2, 0, 0, 0, 1, 1]     # 3 points, then 2 (first point decides the tie), then 1


def test_size_classes_at_their_edges():
    assert fz.size_class([1, 2, 4, 5, 19, 20, 99, 100, 5000]).tolist() == \
        ["1", "2-4", "2-4", "5-19", "5-19", "20-99", "20-99", "100+", "100+"]


def test_zone_area_of_one_two_and_overlapping_points():
    r = 2.0
    one = fz.zone_area_km2(*at([0], [0]), r)
    assert one == pytest.approx(np.pi * r * r)
    apart = fz.zone_area_km2(*at([0, 10], [0, 0]), r)
    assert apart == pytest.approx(2 * np.pi * r * r, rel=0.01)
    same = fz.zone_area_km2(*at([0, 0], [0, 0]), r)
    assert same == pytest.approx(np.pi * r * r, rel=0.01)
    touching = fz.zone_area_km2(*at([0, 2], [0, 0]), r)
    assert np.pi * r * r < touching < 2 * np.pi * r * r


# ---------------------------------------------------------------- one day

def test_active_before_and_unknown_when_not_observed():
    today = xy([0, 0.5, 30], [0, 0, 0])
    lab = fz.group_fires(today)
    prev = xy([1.9], [0])                               # 1.4 km from the second hotspot of fire 0
    assert fz.active_before(today, lab, prev).tolist() == [True, False]
    assert fz.active_before(today, lab, xy([], [])).tolist() == [False, False]
    assert fz.active_before(today, lab, None).tolist() == [None, None]


def test_continuation_takes_the_whole_touching_group_with_its_distances():
    today = xy([0, 0.5], [0, 0])                        # one fire
    lab = fz.group_fires(today)
    # next day: a chain from 1.5 km to 3.3 km east (touches at 1.0 km from the 0.5 km hotspot),
    # and a lone hotspot 10 km north (no contact)
    nxt = xy([1.5, 2.4, 3.3, 0], [0, 0, 0, 10])
    owner, dist = fz.continuation(today, lab, nxt)
    assert owner.tolist() == [0, 0, 0, -1]
    np.testing.assert_allclose(dist[:3], [1.0, 1.9, 2.8], atol=0.01)
    assert np.isnan(dist[3])


def test_a_group_touching_two_fires_goes_to_the_closest():
    today = xy([0, 10], [0, 0])                         # two fires, 10 km apart
    lab = fz.group_fires(today)
    nxt = xy([1.8, 2.7, 3.6, 4.5, 5.4, 6.3, 7.2, 8.1, 9.0], [0] * 9)   # chain from 1.8 to 9.0 km
    owner, _ = fz.continuation(today, lab, nxt)
    assert set(owner.tolist()) == {lab[1]}              # touches fire at 10 km at 1.0 km, fire at 0 at 1.8 km


def test_day_fires_country_by_majority_and_size():
    lat, lon = at([0, 0.5, 1.0, 40], [0, 0, 0, 0])
    day = pd.DataFrame({"latitude": lat, "longitude": lon, "frp_mw": [1.0, 2.0, 3.0, 4.0],
                        "country": ["Chile", "Argentina", "Argentina", "Chile"],
                        "admin1": ["Araucanía", "Neuquén", "Neuquén", "Araucanía"]})
    lab, fires = fz.day_fires(day)
    big = fires[fires["fire_id"] == 0].iloc[0]
    assert (big["hotspots"], big["country"], big["admin1"], big["size_class"]) == (3, "Argentina", "Neuquén", "2-4")
    assert big["frp_sum_mw"] == pytest.approx(6.0)
    assert lab.tolist() == [0, 0, 0, 1]


# ---------------------------------------------------------------- table

def table_inputs():
    rows, spread = [], []
    for cls, n, p in (("1", 300, 0.1), ("2-4", 300, 0.3)):
        for act in (False, True):
            k = n if not act else 50                     # few active fires: they fall back
            cont = np.arange(k) < round(p * k + (0.2 * k if act else 0))
            rows.append(pd.DataFrame({"country": "Chile", "size_class": cls, "active": act, "continued": cont}))
            spread.append(pd.DataFrame({"country": "Chile", "size_class": cls, "active": act,
                                        "dist_km": np.linspace(0, 4, 400)}))
    rows.append(pd.DataFrame({"country": "Chile", "size_class": "1", "active": [None] * 10, "continued": True}))
    return pd.concat(rows, ignore_index=True), pd.concat(spread, ignore_index=True)


def test_calibrate_hides_small_groups_and_lookup_falls_back():
    fires, spread = table_inputs()
    table = fz.calibrate(fires, spread, min_n=200)
    lvl0 = table[(table["level"] == 0) & (table["size_class"] == "1")].set_index("active")
    assert lvl0.loc[False, "p_continue"] == pytest.approx(0.1)
    assert np.isnan(lvl0.loc[True, "p_continue"])               # 50 fires: too few
    assert lvl0.loc[True, "r80_km"] == pytest.approx(3.2, abs=0.02)   # 400 hotspots: enough

    ask = pd.DataFrame({"country": ["Chile", "Chile", "Chile"], "size_class": ["1", "1", "1"],
                        "active": [False, True, None]})
    got = fz.lookup(table, ask)
    assert got["p_level"].tolist() == [0, 2, 2]
    assert got.loc[0, "p_continue"] == pytest.approx(0.1)
    # size only: all 360 fires of class 1, including the 10 with an unknown day before
    assert got.loc[1, "p_continue"] == pytest.approx(fires[fires["size_class"] == "1"]["continued"].mean())
    assert got["r_level"].tolist() == [0, 0, 2]


def test_evaluate_counts_hotspots_inside_each_radius():
    fires = pd.DataFrame({"country": "Chile", "size_class": "1", "continued": [True, False, False, False],
                          "p_continue": 0.25, "base_rate": 0.5, "area80_km2": 3.0})
    spread = pd.DataFrame({"country": "Chile", "size_class": "1", "dist_km": [0.5, 1.5, 2.5, 3.5],
                           "r50_km": 1.0, "r80_km": 2.0, "r90_km": 3.0})
    ev = fz.evaluate(fires, spread)
    assert ev["brier_table"] == pytest.approx((0.75 ** 2 + 3 * 0.25 ** 2) / 4)
    assert ev["brier_one_rate"] == pytest.approx(0.25)
    assert (ev["inside_r50"], ev["inside_r80"], ev["inside_r90"]) == (0.25, 0.5, 0.75)
    assert ev["by_class"][0]["observed"] == 0.25


# ---------------------------------------------------------------- the whole run

def synthetic_hotspots(seed=3, start="2022-05-01", end="2023-01-05", shift_after=None):
    """Fires that start, grow and continue. `shift_after` moves every hotspot after that day far away."""
    rng = np.random.default_rng(seed)
    rows, alive = [], []
    for day in pd.date_range(start, end):
        alive = [(e + 0.8, n, k + 2) for e, n, k in alive if rng.random() < 0.6]   # continue and grow
        for _ in range(rng.integers(6, 10)):
            alive.append((rng.uniform(0, 3000), rng.uniform(0, 600), int(rng.choice([1, 1, 1, 3, 8, 30, 110]))))
        for e, n, k in alive:
            ee = e + 0.5 * np.arange(k) % 5.0             # rows of points 0.5 km apart: linked
            nn = n + 0.5 * (np.arange(k) // 10)
            lat, lon = at(ee, nn)
            rows.append(pd.DataFrame({"burn_date": day, "latitude": lat, "longitude": lon,
                                      "frp_mw": rng.uniform(1, 30, k)}))
    df = pd.concat(rows, ignore_index=True)
    df["country"] = np.where(df["longitude"] < LON0 + 1500 / KM_X, "Chile", "Argentina")
    df["admin1"] = "Somewhere"
    df["satellite"] = "Suomi-NPP"
    df["burn_date"] = pd.to_datetime(df["burn_date"]).dt.date
    if shift_after is not None:
        late = pd.to_datetime(df["burn_date"]) > pd.Timestamp(shift_after)
        df.loc[late, "latitude"] = df.loc[late, "latitude"] - 3.0 + rng.uniform(0, 0.1, late.sum())
    return df


def write_inputs(tmp_path, hot, outage=("2022-06-10", "2022-06-11")):
    kept = tmp_path / "kept.parquet"
    hot.to_parquet(kept)
    quality = tmp_path / "quality"
    quality.mkdir()
    pd.DataFrame({"satellite": ["Suomi-NPP"], "start": [outage[0]], "end": [outage[1]], "days": [2]}).to_csv(
        quality / "outage_days.csv", index=False)
    return kept, quality


@pytest.fixture
def small_groups(monkeypatch):
    monkeypatch.setattr(fz, "MIN_FIRES", 10)


def test_main_writes_zones_for_app_days_and_the_live_day(tmp_path, small_groups):
    hot = synthetic_hotspots()
    kept, quality = write_inputs(tmp_path, hot)
    out = tmp_path / "risk"
    fz.main(["--kept", str(kept), "--quality", str(quality), "--out", str(out)])
    zones = pd.read_parquet(out / "fire_zones.parquet")
    pts = pd.read_parquet(out / "fire_zone_points.parquet")
    model = json.loads((out / "fire_zones.json").read_text())

    live = pd.Timestamp("2023-01-05").date()
    assert zones["burn_date"].min() == pd.Timestamp("2023-01-01").date()
    assert zones["burn_date"].max() == live
    assert zones.loc[zones["burn_date"] == live, "continued"].isna().all()       # tomorrow is unknown
    assert zones.loc[zones["burn_date"] < live, "continued"].notna().all()
    assert zones[["p_continue", "r50_km", "r80_km", "r90_km", "area80_km2"]].notna().all().all()
    assert (zones["r50_km"] <= zones["r80_km"]).all() and (zones["r80_km"] <= zones["r90_km"]).all()
    assert (zones["area50_km2"] <= zones["area80_km2"] + 1e-9).all()
    # every fire has its points, and the number of fires matches the hotspots of its day
    assert set(map(tuple, pts[["burn_date", "fire_id"]].drop_duplicates().to_numpy())) == \
        set(map(tuple, zones[["burn_date", "fire_id"]].to_numpy()))
    seen = pd.Timestamp("2023-01-04").date()
    assert zones.loc[zones["burn_date"] == live, "seen_date"].eq(seen).all()
    assert zones.loc[zones["burn_date"] == live, "hotspots"].sum() == (hot["burn_date"] == seen).sum()
    # continuing hotspots inside the 80% zone never exceed the continuing hotspots
    done = zones[zones["continued"].fillna(False).astype(bool)]
    assert (done["next_in_r80"] <= done["next_hotspots"]).all()
    assert model["test"]["fires"] > 0 and 0 <= model["test"]["inside_r80"] <= 1
    assert (out / "fire_zones.md").read_text().startswith("# Zones of likely activity")


def test_the_table_never_reads_the_test_years(tmp_path, small_groups):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    for d, hot in ((a, synthetic_hotspots()), (b, synthetic_hotspots(shift_after="2022-12-31"))):
        kept, quality = write_inputs(d, hot)
        fz.main(["--kept", str(kept), "--quality", str(quality), "--out", str(d / "risk")])
    ta = json.loads((a / "risk" / "fire_zones.json").read_text())["table"]
    tb = json.loads((b / "risk" / "fire_zones.json").read_text())["table"]
    assert ta == tb


def test_no_fire_is_scored_against_an_outage_day(tmp_path, small_groups):
    hot = synthetic_hotspots()
    kept, quality = write_inputs(tmp_path, hot, outage=("2023-01-02", "2023-01-02"))
    out = tmp_path / "risk"
    fz.main(["--kept", str(kept), "--quality", str(quality), "--out", str(out)])
    zones = pd.read_parquet(out / "fire_zones.parquet")
    days = pd.to_datetime(zones["burn_date"])
    assert not (days == "2023-01-03").any()                        # D = 2 January was not observed
    assert zones.loc[days == "2023-01-02", "continued"].isna().all()   # its D+1 was not observed
    assert zones.loc[days == "2023-01-02", "p_continue"].notna().all()  # but it is still zoned
