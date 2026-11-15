"""scripts/daily_train.py on a small made-up panel (docs/modeling-plan.md, card 3)."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

pytest.importorskip("lightgbm")
import daily_train as dt  # noqa: E402

CONTRACT = ["burn_date", "cell_lat", "cell_lon", "probability", "baseline_probability", "alert"]


def make_panel(signal: bool = True, flat_features: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(panel, live rows) as scripts/daily_panel.py writes them: two countries, 30 cells, 2019-2023.

    The first 7 days of 2021 and 2023 have split `gap`. The live day is 2024-01-01, in its own frame.

    With `signal`, fire follows the features. Without, it follows something only the baselines know.
    """
    rng = np.random.default_rng(7)
    days = pd.date_range("2019-01-01", "2023-12-31")
    frames, lives = [], []
    for country, lon in (("Chile", -71.0), ("Argentina", -60.0)):
        n = len(days) * 30
        df = pd.DataFrame({
            "burn_date": np.repeat(days.values, 30),
            "cell_lat": np.tile(-30.0 - np.arange(30) * 0.25, len(days)),
            "cell_lon": lon,
            "country": country,
        })
        lag = (rng.random(n) < 0.08).astype("float32")
        nbr = rng.integers(0, 4, n).astype("float32")
        hidden = rng.random(n) < 0.1
        rate = 0.02 + (0.5 * lag + 0.04 * nbr if signal else 0.6 * hidden)
        df["fire"] = (rng.random(n) < rate).astype("float64")
        df["lag_fire_d0"], df["nbr_fire_d0"] = lag, nbr
        df["hist_rate"] = rng.random(n).astype("float32") * 0.05
        df["geo_lat"] = df["cell_lat"].astype("float32")
        df["cal_dow"] = df["burn_date"].dt.day_of_week.astype("float32")
        df["cal_month"] = df["burn_date"].dt.month.astype("float32")
        df["cal_doy_sin"] = np.sin(df["burn_date"].dt.day_of_year / 365 * 2 * np.pi).astype("float32")
        df["cal_doy_cos"] = np.cos(df["burn_date"].dt.day_of_year / 365 * 2 * np.pi).astype("float32")
        df["p_hist"] = df["hist_rate"] if signal else (0.5 * hidden + df["hist_rate"]).astype("float32")
        df["p_persist"] = lag
        # With signal, a rule the model can beat; without, the rule sees what the features do not.
        df["p_near"] = (((lag > 0) | (rng.random(n) < 0.25)) if signal else hidden).astype("float32")
        year = df["burn_date"].dt.year
        df["split"] = np.select([year <= 2020, year <= 2022], ["train", "tune"], "test")
        df.loc[year.isin([2021, 2023]) & (df["burn_date"].dt.day_of_year <= 7), "split"] = "gap"
        if flat_features:                      # nothing to learn from: every score will be tied
            df[["lag_fire_d0", "nbr_fire_d0", "hist_rate", "geo_lat", "cal_dow"]] = 0.0
        live = df[df["burn_date"] == days[-1]].assign(burn_date=days[-1] + pd.Timedelta(days=1),
                                                      split="live", fire=np.nan)
        frames.append(df), lives.append(live)
    return pd.concat(frames, ignore_index=True), pd.concat(lives, ignore_index=True)


@pytest.fixture(scope="module")
def outputs(tmp_path_factory):
    root = tmp_path_factory.mktemp("daily")
    run(root, *make_panel())
    return root


def run(root: Path, panel: pd.DataFrame, live: pd.DataFrame | None, *extra: str) -> None:
    panel.to_parquet(root / "panel.parquet")
    if live is not None:
        live.to_parquet(root / "live.parquet")
    dt.main(["--panel", str(root / "panel.parquet"), "--live", str(root / "live.parquet"),
             "--out-daily", str(root / "daily"), "--out-risk", str(root / "risk"), "--max-rounds", "60", *extra])


def test_default_features_leave_out_calendar_target_and_baselines():
    columns = list(make_panel()[0].columns)
    default = dt.feature_columns(columns, calendar=False)
    assert set(default) == {"lag_fire_d0", "nbr_fire_d0", "hist_rate", "geo_lat", "cal_dow"}
    assert set(dt.feature_columns(columns, calendar=True)) - set(default) == set(dt.CALENDAR)


def test_app_file_follows_the_contract(outputs):
    app = pd.read_parquet(outputs / "risk" / "cells_daily.parquet")
    assert list(app.columns) == CONTRACT
    assert app["probability"].between(0, 1).all() and set(app["alert"]) <= {0, 1}
    assert not app.duplicated(["burn_date", "cell_lat", "cell_lon"]).any()
    years = set(pd.to_datetime(app["burn_date"]).dt.year)
    assert years == {2023, 2024}                      # the test year and the live day, never train or tune
    assert (pd.to_datetime(app["burn_date"]) == "2024-01-01").sum() == 60     # 30 cells, two countries


def test_predictions_cover_tune_and_test_for_both_runs(outputs):
    pred = pd.read_parquet(outputs / "daily" / "predictions.parquet")
    assert set(pred["model"]) == {"lgbm", "lgbm_calendar"}
    assert set(pd.to_datetime(pred["burn_date"]).dt.year) == {2021, 2022, 2023}
    assert pred.groupby("model").size().nunique() == 1


def test_model_with_signal_beats_the_baselines_and_is_used(outputs):
    report = json.loads((outputs / "risk" / "daily_model.json").read_text())
    for country in ("Chile", "Argentina"):
        s = report["countries"][country]
        assert s["used_in_app"] == "model"
        c = s["checks_on_tune"]
        assert c["flagged_share_at_recall"] < c["flagged_share_of_p_hist_at_recall"]
        assert next(iter(s["gain_share"])) == "lag_fire_d0"        # the feature that drives the fire
        assert "cal_month" not in s["runs"]["lgbm"]["features"]
    assert (outputs / "daily" / "model_chile.txt").exists()
    metrics = json.loads((outputs / "risk" / "daily_metrics.json").read_text())
    assert {"lgbm", "lgbm_calendar", "p_hist", "p_near"} <= {r["score"] for r in metrics["results"]}


def test_model_without_signal_leaves_the_baseline_in_the_app():
    g, source = (d[d["country"] == "Chile"] for d in make_panel(signal=False))
    _, app, _, summary = dt.train_country(g, source, 0.80, max_rounds=30)
    assert summary["used_in_app"] == "baseline"
    live = app[app["burn_date"] == "2024-01-01"]
    assert np.allclose(live["probability"], source["p_hist"]) and (live["alert"] == (source["p_near"] >= 0.5)).all()


# ---------------------------------------------------------------- audit of pull request 31

def test_live_day_and_gap_days_stay_in_the_app_file(outputs):
    dates = pd.to_datetime(pd.read_parquet(outputs / "risk" / "cells_daily.parquet")["burn_date"])
    assert dates.max() == pd.Timestamp("2024-01-01")                       # the live day
    per_day = dates.value_counts()
    for day in pd.date_range("2023-01-01", "2023-01-07"):                  # gap days of the test year
        assert per_day[day] == 60
    assert not (dates.dt.year == 2021).any()                               # gap days of tune are not shown


def test_gap_days_are_never_scored(outputs):
    pred = pd.to_datetime(pd.read_parquet(outputs / "daily" / "predictions.parquet")["burn_date"])
    assert not pred.between("2023-01-01", "2023-01-07").any() and not pred.between("2021-01-01", "2021-01-07").any()
    metrics = json.loads((outputs / "risk" / "daily_metrics.json").read_text())
    test_rows = {r["rows"] for r in metrics["results"] if r["split"] == "test" and r["group"] == "all"}
    assert test_rows == {(365 - 7) * 30}


def test_a_missing_live_file_stops_before_the_app_file_is_replaced(tmp_path):
    panel, live = make_panel()
    (tmp_path / "risk").mkdir()
    (tmp_path / "risk" / "cells_daily.parquet").write_text("the file of the data lane")
    with pytest.raises(SystemExit, match="live"):
        run(tmp_path, panel, None)
    with pytest.raises(SystemExit, match="Argentina"):
        run(tmp_path, panel, live[live["country"] == "Chile"])
    assert (tmp_path / "risk" / "cells_daily.parquet").read_text() == "the file of the data lane"


def test_no_live_has_to_be_asked_for(tmp_path):
    run(tmp_path, make_panel()[0], None, "--no-live")
    dates = pd.to_datetime(pd.read_parquet(tmp_path / "risk" / "cells_daily.parquet")["burn_date"])
    assert dates.max() == pd.Timestamp("2023-12-31")


def test_a_model_with_tied_scores_is_not_promoted_over_p_near():
    g, live = (d[d["country"] == "Chile"] for d in make_panel(flat_features=True))
    _, app, _, summary = dt.train_country(g, live, 0.80, max_rounds=30)
    c = summary["checks_on_tune"]
    assert c["alerts_of_model_at_that_budget"] <= c["alerts_of_p_near"]
    assert summary["used_in_app"] == "baseline"


def test_producer_then_consumer_keeps_every_date_of_the_app_file(tmp_path):
    """scripts/daily_panel.py followed by scripts/daily_train.py, on a tiny made-up hotspot table."""
    dp = pytest.importorskip("daily_panel")
    rng = np.random.default_rng(3)
    cells = [(-36.0 - 0.25 * i, -72.0 + 0.25 * j) for i in range(4) for j in range(4)]
    rows = [{"burn_date": d.date(), "latitude": lat + 0.1, "longitude": lon + 0.1,
             "frp_mw": float(rng.uniform(1, 40)), "daynight": rng.choice(["D", "N"]),
             "country": "Chile", "admin1": "Maule", "satellite": "Suomi-NPP"}
            for d in pd.date_range("2012-01-20", "2023-03-10") for lat, lon in cells if rng.random() < 0.06]
    pd.DataFrame(rows).to_parquet(tmp_path / "hotspots_kept.parquet", index=False)
    (tmp_path / "quality").mkdir()
    pd.DataFrame({"satellite": ["Suomi-NPP"], "start": ["2016-03-01"], "end": ["2016-03-04"],
                  "days": [4]}).to_csv(tmp_path / "quality" / "outage_days.csv", index=False)

    dp.main(["--kept", str(tmp_path / "hotspots_kept.parquet"), "--quality", str(tmp_path / "quality"),
             "--out", str(tmp_path)])
    app_file = tmp_path / "risk" / "cells_daily.parquet"
    before = pd.read_parquet(app_file)

    dt.main(["--panel", str(tmp_path / "daily" / "panel.parquet"), "--live", str(tmp_path / "daily" / "live.parquet"),
             "--out-daily", str(tmp_path / "daily"), "--out-risk", str(tmp_path / "risk"), "--max-rounds", "40"])
    after = pd.read_parquet(app_file)

    keys = ["burn_date", "cell_lat", "cell_lon"]
    assert list(after.columns) == CONTRACT
    pd.testing.assert_frame_equal(before[keys].sort_values(keys).reset_index(drop=True),
                                  after[keys].sort_values(keys).reset_index(drop=True))
    assert pd.to_datetime(after["burn_date"]).max() == pd.to_datetime(before["burn_date"]).max()   # the live day
