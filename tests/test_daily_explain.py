"""scripts/daily_explain.py: reasons behind each alert (docs/findings/09-daily-model.md)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

pytest.importorskip("lightgbm")
import daily_explain as dx  # noqa: E402
import daily_train as dt  # noqa: E402
from test_daily_train import make_panel  # noqa: E402

FEATURES = ["lag_fire_d0", "lag_fire_days_7", "lag_days_since_fire", "lag_hotspots_d0", "lag_night_d0",
            "nbr_fire_d0", "nbr_ring2_fire_d0", "hist_doy_rate", "cal_dow", "geo_lat"]


def test_every_feature_of_the_panel_has_a_group():
    panel = ["lag_fire_d0", "lag_fire_d6", "lag_fire_days_7", "lag_fire_days_30", "lag_days_since_fire",
             "lag_hotspots_d0", "lag_frp_sum_d0", "lag_frp_max_d0", "lag_night_d0", "nbr_fire_d0",
             "nbr_hotspots_d0", "nbr_ring2_fire_d0", "nbr_fire_days_7", "hist_doy_rate", "hist_cell_rate",
             "cal_dow", "cal_month", "cal_doy_sin", "cal_doy_cos", "geo_lat", "geo_lon"]
    assert "other" not in {dx.group_of(f) for f in panel}
    assert dx.group_of("lag_hotspots_d0") == "intensity" and dx.group_of("lag_fire_days_30") == "recent"


def test_sentences_use_the_values_of_the_row():
    row = {"lag_fire_d0": 1, "lag_fire_days_7": 4, "lag_days_since_fire": 0, "lag_hotspots_d0": 12,
           "lag_night_d0": 1, "nbr_fire_d0": 3, "nbr_ring2_fire_d0": 5, "hist_doy_rate": 0.2}
    assert dx.sentence("recent", row) == "Fire was detected in this cell today, and on 4 of the last 7 days"
    assert dx.sentence("intensity", row) == "Today's fire here had 12 hotspots, and it was still burning at night"
    assert dx.sentence("nearby", row) == "3 of the 8 neighbouring cells had fire today"
    assert dx.sentence("history", row) == "In earlier years this cell had fire on 20% of the days at this time of the year"
    quiet = {"lag_fire_d0": 0, "lag_fire_days_30": 2, "lag_days_since_fire": 9, "nbr_fire_d0": 0, "nbr_ring2_fire_d0": 2}
    assert dx.sentence("recent", quiet) == "The last fire in this cell was 9 days ago, with 2 days of fire in the last 30"
    assert dx.sentence("nearby", quiet) == "2 cells within two cells of this one had fire today"


def test_a_day_the_satellite_did_not_see_gives_no_made_up_number():
    unknown = {"lag_fire_d0": np.nan, "lag_days_since_fire": np.nan, "hist_doy_rate": np.nan}
    for group in ("recent", "intensity", "nearby", "history"):
        assert not any(ch.isdigit() for ch in dx.sentence(group, unknown).replace("8 neighbouring", ""))


def test_reasons_rank_groups_and_only_list_what_pushes_up():
    values = pd.DataFrame([{"lag_fire_d0": 1, "lag_fire_days_7": 1, "lag_days_since_fire": 0, "lag_hotspots_d0": 2,
                            "lag_night_d0": 0, "nbr_fire_d0": 2, "nbr_ring2_fire_d0": 0, "hist_doy_rate": 0.1,
                            "cal_dow": 6, "geo_lat": -30.0}] * 2)
    #                 recent          intensity   nearby     history calendar place
    contrib = np.array([[0.5, 0.2, 0.3, 0.1, 0.0, 0.6, 0.0, -0.4, -0.1, 0.0],     # recent 1.0, nearby 0.6, intensity 0.1
                        [-0.2, 0.0, 0.0, 0.0, 0.0, -0.1, 0.0, 0.3, 0.0, -0.5]])   # only history pushes up
    out = dx.reasons(contrib, FEATURES, values)
    assert out.loc[0, "reason_1"].startswith("Fire was detected in this cell today")
    assert out.loc[0, "reason_2"] == "2 of the 8 neighbouring cells had fire today"
    assert out.loc[0, "reason_3"].startswith("Today's fire here had 2 hotspots")
    assert out.loc[0, ["share_1", "share_2", "share_3"]].tolist() == pytest.approx([1.0 / 1.7, 0.6 / 1.7, 0.1 / 1.7])
    assert out.loc[1, "reason_1"].startswith("In earlier years") and out.loc[1, "share_1"] == pytest.approx(1.0)
    assert out.loc[1, "reason_2"] == "" and out.loc[1, "reason_3"] == "" and out.loc[1, "share_2"] == 0


def test_alerts_get_reasons_and_the_rebuilt_model_matches_the_app_file(tmp_path):
    panel, live = make_panel()
    pd.concat([panel, live], ignore_index=True).to_parquet(tmp_path / "panel.parquet")
    args = ["--panel", str(tmp_path / "panel.parquet")]
    dt.main(args + ["--out-daily", str(tmp_path / "daily"), "--out-risk", str(tmp_path / "risk"), "--max-rounds", "60"])
    dx.main(args + ["--daily", str(tmp_path / "daily"), "--risk", str(tmp_path / "risk")])

    app = pd.read_parquet(tmp_path / "risk" / "cells_daily.parquet")
    why = pd.read_parquet(tmp_path / "risk" / "cells_daily_reasons.parquet")
    keys = ["burn_date", "cell_lat", "cell_lon"]
    assert len(why) == int(app["alert"].sum()) and not why.duplicated(keys).any()
    assert len(why.merge(app[app["alert"] == 1], on=keys)) == len(why)          # alerts, and only alerts
    assert (why["reason_1"] != "").all()                                         # an alert always has a reason
    assert why["burn_date"].max() == app["burn_date"].max()                      # the live day is explained too
    assert why["reason_1"].str.contains("Fire was detected in this cell today").any()   # the made-up fire follows it
    assert why[["share_1", "share_2", "share_3"]].sum(axis=1).between(0.5, 1.0001).all()

    # A different app file must stop the script, not get explanations of another model.
    app["probability"] = app["probability"] * 0.5
    app.to_parquet(tmp_path / "risk" / "cells_daily.parquet", index=False)
    with pytest.raises(SystemExit, match="does not match"):
        dx.main(args + ["--daily", str(tmp_path / "daily"), "--risk", str(tmp_path / "risk")])
