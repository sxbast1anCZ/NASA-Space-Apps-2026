"""Hand-made and synthetic cases for scripts/daily_panel.py (docs/modeling-plan.md, card 1)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import daily_panel as dp  # noqa: E402


def grid_of(fire: np.ndarray, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    hot = np.where(fire, rng.integers(1, 20, fire.shape), 0).astype(np.int32)
    frp = np.where(fire, rng.uniform(1, 50, fire.shape), 0).astype(np.float32)
    return {"fire": fire.copy(), "hotspots": hot, "frp_sum": frp * 2, "frp_max": frp,
            "night": fire & (rng.random(fire.shape) < 0.5)}


def square(n: int = 5) -> pd.DataFrame:
    """n x n cells, 0.25 degree apart, in row-major order."""
    lat, lon = np.meshgrid(np.arange(n) * dp.CELL_DEG - 30, np.arange(n) * dp.CELL_DEG - 65, indexing="ij")
    return pd.DataFrame({"cell_lat": lat.ravel(), "cell_lon": lon.ravel(),
                         "country": "Argentina", "admin1": "Salta"})


def random_world(seed: int = 1, start="2012-02-01", end="2016-12-31"):
    days = pd.date_range(start, end)
    cells = square(5)
    rng = np.random.default_rng(seed)
    fire = rng.random((len(cells), len(days))) < 0.08
    avail = np.ones(len(days), bool)
    avail[rng.choice(len(days), 25, replace=False)] = False      # outage days
    fire[:, ~avail] = False                                     # nothing is seen on an outage day
    return days, cells, grid_of(fire, seed), avail


# ---------------------------------------------------------------- no feature reads the predicted day

@pytest.mark.parametrize("cut", ["2015-01-01", "2015-03-01", "2015-07-14", "2015-12-31"])
def test_no_feature_reads_the_predicted_day_or_later(cut):
    days, cells, grid, avail = random_world()
    nbr1, nbr2 = dp.neighbour_ids(cells), dp.ring2_ids(cells)
    t0 = days.get_loc(pd.Timestamp(cut))
    t_pred = np.arange(dp.year_start_index(days, 2015), t0 + 1)         # 2015 up to the cut day
    before = dp.frame_for_days(grid, avail, nbr1, nbr2, cells, days, 2015, t_pred)

    rng = np.random.default_rng(99)
    changed = {k: v.copy() for k, v in grid.items()}
    for k, v in changed.items():                                         # rewrite day t0 and later
        changed[k][:, t0:] = rng.permutation(v[:, t0:].ravel()).reshape(v[:, t0:].shape)
    changed["fire"][:, t0:] = rng.random(changed["fire"][:, t0:].shape) < 0.5
    avail2 = avail.copy()
    avail2[t0:] = rng.random(len(avail) - t0) < 0.5
    after = dp.frame_for_days(changed, avail2, nbr1, nbr2, cells, days, 2015, t_pred)

    features = [c for c in dp.FEATURES + ["p_hist", "p_persist", "p_near", "new_cell"]]
    pd.testing.assert_frame_equal(before[features], after[features])
    last = before["burn_date"] == pd.Timestamp(cut).date()               # the target does change
    assert last.any()


def test_history_never_reads_the_year_it_predicts():
    days, cells, grid, avail = random_world()
    t_pred = np.flatnonzero(days.year == 2015)
    rate, prior = dp.hist_features(grid["fire"], avail, days, 2015, t_pred)
    changed = grid["fire"].copy()
    changed[:, dp.year_start_index(days, 2015):] = True                  # the whole of 2015 on fire
    rate2, prior2 = dp.hist_features(changed, avail, days, 2015, t_pred)
    np.testing.assert_array_equal(rate, rate2)
    np.testing.assert_array_equal(prior, prior2)


def test_cells_are_eligible_only_with_fire_before_the_year():
    days = pd.date_range("2013-01-01", "2015-12-31")
    fire = np.zeros((3, len(days)), bool)
    fire[0, days.get_loc(pd.Timestamp("2013-06-01"))] = True
    fire[1, days.get_loc(pd.Timestamp("2014-01-01"))] = True             # first fire in 2014
    avail = np.ones(len(days), bool)
    avail[days.get_loc(pd.Timestamp("2013-06-01"))] = False              # cell 0's only fire was not observed
    assert dp.eligible(fire, avail, days, 2014).tolist() == [False, False, False]
    assert dp.eligible(fire, avail, days, 2015).tolist() == [False, True, False]


# ---------------------------------------------------------------- lag and neighbour features

def test_lags_windows_and_days_since_fire():
    days = pd.date_range("2020-01-01", "2020-03-31")
    cells = square(1)
    fire = np.zeros((1, len(days)), bool)
    fire[0, [10, 12, 13]] = True
    avail = np.ones(len(days), bool)
    avail[11] = False                                                    # outage day
    t = np.array([14, 12, 40, 50])                                       # D = 13, 11, 39, 49
    f = dp.day_features(grid_of(fire), avail, dp.neighbour_ids(cells), dp.ring2_ids(cells), t)

    assert f["lag_fire_d0"][0].tolist()[0] == 1
    assert np.isnan(f["lag_fire_d0"][0, 1])                              # D is the outage day
    assert np.isnan(f["lag_fire_d2"][0, 0])                              # D-2 = day 11, outage
    assert f["lag_fire_d3"][0, 0] == 1                                   # day 10
    assert f["lag_fire_days_7"][0, 0] == 3                               # days 7..13
    assert f["lag_fire_days_30"][0, 2] == 3                              # days 10..39
    assert f["lag_fire_days_7"][0, 2] == 0
    assert f["lag_days_since_fire"][0].tolist() == [0, 1, 26, 36]
    assert np.isnan(f["lag_hotspots_d0"][0, 1])


def test_days_since_fire_is_capped_when_no_fire_was_seen():
    days = pd.date_range("2019-01-01", "2020-12-31")
    fire = np.zeros((1, len(days)), bool)
    fire[0, 3] = True
    cells = square(1)
    f = dp.day_features(grid_of(fire), np.ones(len(days), bool), dp.neighbour_ids(cells),
                        dp.ring2_ids(cells), np.array([2, 300, 600]))
    assert f["lag_days_since_fire"][0].tolist() == [365, 296, 365]


def test_window_of_only_outage_days_is_missing():
    days = pd.date_range("2020-01-01", "2020-02-29")
    fire = np.zeros((1, len(days)), bool)
    avail = np.ones(len(days), bool)
    avail[20:27] = False                                                 # 7 days out
    cells = square(1)
    f = dp.day_features(grid_of(fire), avail, dp.neighbour_ids(cells), dp.ring2_ids(cells), np.array([27, 28]))
    assert np.isnan(f["lag_fire_days_7"][0, 0]) and f["lag_fire_days_7"][0, 1] == 0
    assert np.isnan(f["nbr_fire_days_7"][0, 0])
    assert f["lag_fire_days_30"][0, 0] == 0                              # the 30-day window saw other days


def test_neighbours_and_second_ring():
    days = pd.date_range("2020-01-01", "2020-01-10")
    cells = square(5)                                                    # centre cell is 12
    fire = np.zeros((25, len(days)), bool)
    fire[[6, 7, 8], 4] = True                                            # three of the 8 neighbours of 12
    fire[[0, 4, 24], 4] = True                                           # three corners of the ring of 16
    g = grid_of(fire)
    g["hotspots"][:, :] = np.where(fire, 2, 0)
    f = dp.day_features(g, np.ones(len(days), bool), dp.neighbour_ids(cells), dp.ring2_ids(cells), np.array([5]))
    assert f["nbr_fire_d0"][12, 0] == 3
    assert f["nbr_hotspots_d0"][12, 0] == 6
    assert f["nbr_ring2_fire_d0"][12, 0] == 3
    assert f["nbr_fire_days_7"][12, 0] == 3


def test_ring2_has_16_cells_and_minus_one_at_the_edge():
    ids = dp.ring2_ids(square(5))
    assert ids.shape == (25, 16)
    assert sorted(ids[12].tolist()) == [0, 1, 2, 3, 4, 5, 9, 10, 14, 15, 19, 20, 21, 22, 23, 24]
    assert (ids[0] == -1).sum() == 16 - 5                                # corner: 5 cells of the ring exist


# ---------------------------------------------------------------- history

def test_history_rate_with_shrinkage_by_hand():
    days = pd.date_range("2012-01-01", "2014-12-31")
    fire = np.zeros((1, len(days)), bool)
    fire[0, days.get_loc(pd.Timestamp("2012-07-03"))] = True             # inside the window of 1 July
    fire[0, days.get_loc(pd.Timestamp("2013-12-31"))] = True             # outside it
    avail = np.ones(len(days), bool)
    t = np.array([days.get_loc(pd.Timestamp("2014-07-01"))])
    rate, prior = dp.hist_features(fire, avail, days, 2014, t, window=7, shrink=15.0)
    n_before = (days < "2014-01-01").sum()
    assert prior[0] == pytest.approx(2 / n_before)
    assert rate[0, 0] == pytest.approx((1 + 15 * 2 / n_before) / (2 * 15 + 15))


def test_history_window_stops_before_the_year_predicted():
    days = pd.date_range("2012-01-01", "2014-12-31")
    fire = np.zeros((1, len(days)), bool)
    avail = np.ones(len(days), bool)
    t = np.array([days.get_loc(pd.Timestamp("2014-12-31"))])
    # For 2013 the window of 31 December is 24 to 31 December 2013: it must not reach 1-7 January 2014.
    start = dp.year_start_index(days, 2014)
    fire[0, start:start + 7] = True                                      # 1 to 7 January 2014
    rate, _ = dp.hist_features(fire, avail, days, 2014, t)
    assert rate[0, 0] == 0


def test_29_february_uses_28_february_of_other_years():
    days = pd.date_range("2013-01-01", "2016-12-31")
    fire = np.zeros((1, len(days)), bool)
    avail = np.ones(len(days), bool)
    t = np.array([days.get_loc(pd.Timestamp("2016-02-29"))])
    rate, _ = dp.hist_features(fire, avail, days, 2016, t)
    assert np.isfinite(rate).all()


# ---------------------------------------------------------------- labels

def test_splits_with_gap_days():
    d = pd.Series(pd.to_datetime(["2020-12-31", "2021-01-07", "2021-01-08", "2022-06-01", "2023-01-01",
                                  "2023-01-08", "2025-12-31", "2014-01-01"]))
    assert dp.split_of(d).tolist() == ["train", "gap", "tune", "tune", "gap", "test", "test", "train"]


def test_segments_and_season_labels():
    d = pd.Series(pd.to_datetime(["2023-02-28", "2023-03-01", "2023-08-31", "2023-09-01", "2024-01-15"]))
    seg = dp.segment_of(pd.Series(["Chile", "Chile", "Argentina", "Argentina", "Chile"]), d.dt.month)
    assert seg.tolist() == ["CL-PV", "CL-OI", "AR-OI", "AR-PV", "CL-PV"]
    assert dp.season_label_of(d).tolist() == ["PV 2022/23", "OI 2023", "OI 2023", "PV 2023/24", "PV 2023/24"]
    assert dp.season_label_of(pd.Series(pd.to_datetime(["1999-10-01"]))).tolist() == ["PV 1999/00"]


def test_baselines_and_new_cell_in_the_frame():
    days, cells, grid, avail = random_world()
    t = np.flatnonzero(avail & (days.year == 2016))
    df = dp.frame_for_days(grid, avail, dp.neighbour_ids(cells), dp.ring2_ids(cells), cells, days, 2016, t)
    assert list(df.columns) == dp.ID_COLS + dp.FEATURES
    ok = df["p_near"].notna()
    assert (df.loc[ok, "p_near"] >= df.loc[ok, "p_persist"]).all()
    assert (df.loc[ok, "new_cell"] == 1 - df.loc[ok, "p_near"]).all()
    assert (df["p_hist"] == df["hist_doy_rate"]).all()
    assert df["fire"].isin([0, 1]).all()
    assert df["burn_date"].map(lambda x: x.year).eq(2016).all()
    app = dp.contract_rows(df)
    assert list(app.columns) == dp.CONTRACT
    assert set(app["alert"].unique()) <= {0, 1}


# ---------------------------------------------------------------- end to end on a tiny made-up table

def tiny_inputs(tmp_path):
    """A made-up kept-hotspot table (Suomi-NPP, 2012 to March 2023) and an outage list."""
    rng = np.random.default_rng(3)
    days = pd.date_range("2012-01-20", "2023-03-10")
    cells = square(3)
    rows = []
    for d in days:
        sat = "Suomi-NPP"
        for c in cells.itertuples():
            if rng.random() < 0.06:
                rows.append({"burn_date": d.date(), "latitude": c.cell_lat + 0.1, "longitude": c.cell_lon + 0.1,
                             "frp_mw": float(rng.uniform(1, 40)), "daynight": rng.choice(["D", "N"]),
                             "country": "Chile", "admin1": "Maule", "satellite": sat})
    kept = tmp_path / "hotspots_kept.parquet"
    pd.DataFrame(rows).to_parquet(kept, index=False)
    quality = tmp_path / "quality"
    quality.mkdir()
    pd.DataFrame({"satellite": ["Suomi-NPP", "Terra"], "start": ["2016-03-01", "2016-05-01"],
                  "end": ["2016-03-04", "2016-05-02"], "days": [4, 2]}).to_csv(quality / "outage_days.csv", index=False)
    return kept, quality, pd.Timestamp(max(r["burn_date"] for r in rows))


def test_main_writes_the_contract_files(tmp_path):
    kept, quality, last = tiny_inputs(tmp_path)
    dp.main(["--kept", str(kept), "--quality", str(quality), "--out", str(tmp_path)])

    panel = pd.read_parquet(tmp_path / "daily" / "panel.parquet")
    assert list(panel.columns) == dp.ID_COLS + dp.FEATURES
    dates = pd.to_datetime(panel["burn_date"])
    assert dates.min() == pd.Timestamp("2014-01-01")
    assert not dates.between("2016-03-01", "2016-03-04").any()           # Suomi-NPP outage: not predicted
    assert dates.between("2016-05-01", "2016-05-02").any()               # Terra outage: irrelevant
    assert set(panel["split"]) == {"train", "tune", "test", "gap", "live"}
    assert set(panel["segment"]) == {"CL-PV", "CL-OI"}

    live = panel[panel["split"] == "live"]                               # in the panel, as daily_train.py reads it
    assert len(live) and (dates[live.index] == last).all()               # the day after the last complete day
    assert live["fire"].isna().all() and panel.loc[panel["split"] != "live", "fire"].notna().all()
    assert not (tmp_path / "daily" / "live.parquet").exists()            # one contract: no separate file
    labelled = pd.read_parquet(tmp_path / "daily" / "panel.parquet", filters=[("split", "in", ["tune", "test"])])
    assert labelled["fire"].isin([0, 1]).all()                           # what daily_eval.py reads has a target

    app = pd.read_parquet(tmp_path / "risk" / "cells_daily.parquet")
    assert list(app.columns) == dp.CONTRACT
    app_dates = pd.to_datetime(app["burn_date"])
    assert app_dates.min() == pd.Timestamp("2023-01-01") and app_dates.max() == pd.Timestamp(last)
    assert (app["probability"] == app["baseline_probability"]).all()
    assert (tmp_path / "daily" / "panel_summary.json").exists()


# ---------------------------------------------------------------- producer, then consumer

def test_training_keeps_every_app_date_of_the_panel(tmp_path):
    """daily_panel.py, then daily_train.py: the model's cells_daily.parquet must cover the same days
    as the baseline one, including the live day and the `gap` days of early January 2023."""
    dt = pytest.importorskip("daily_train", reason="needs scripts/daily_train.py (pull request 31)")
    pytest.importorskip("lightgbm")
    kept, quality, last = tiny_inputs(tmp_path)
    dp.main(["--kept", str(kept), "--quality", str(quality), "--out", str(tmp_path)])
    app_path = tmp_path / "risk" / "cells_daily.parquet"
    baseline = pd.read_parquet(app_path)

    dt.main(["--panel", str(tmp_path / "daily" / "panel.parquet"), "--out-daily", str(tmp_path / "daily"),
             "--out-risk", str(tmp_path / "risk"), "--max-rounds", "20"])

    model = pd.read_parquet(app_path)
    assert list(model.columns)[:len(dp.CONTRACT)] == dp.CONTRACT
    days = set(pd.to_datetime(model["burn_date"]))
    assert last in days                                                  # the live outlook survives
    assert set(pd.date_range("2023-01-01", "2023-01-07")) <= days        # the gap days stay in the app
    assert days == set(pd.to_datetime(baseline["burn_date"]))
    assert len(model) == len(baseline)
