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


def make_panel(signal: bool = True) -> pd.DataFrame:
    """Two countries, 30 cells each, 2019-2023 plus one live day.

    With `signal`, fire follows the features. Without, it follows something only the baselines know.
    """
    rng = np.random.default_rng(7)
    days = pd.date_range("2019-01-01", "2023-12-31")
    frames = []
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
        live = df[df["burn_date"] == days[-1]].assign(burn_date=days[-1] + pd.Timedelta(days=1),
                                                      split="live", fire=np.nan)
        frames += [df, live]
    return pd.concat(frames, ignore_index=True)


@pytest.fixture(scope="module")
def outputs(tmp_path_factory):
    root = tmp_path_factory.mktemp("daily")
    make_panel().to_parquet(root / "panel.parquet")
    dt.main(["--panel", str(root / "panel.parquet"), "--out-daily", str(root / "daily"),
             "--out-risk", str(root / "risk"), "--max-rounds", "60"])
    return root


def test_default_features_leave_out_calendar_target_and_baselines():
    columns = list(make_panel().columns)
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
    g = make_panel(signal=False)
    g = g[g["country"] == "Chile"]
    _, app, _, summary = dt.train_country(g, 0.80, max_rounds=30)
    assert summary["used_in_app"] == "baseline"
    live = app[app["burn_date"] == "2024-01-01"]
    source = g[g["split"] == "live"]
    assert np.allclose(live["probability"], source["p_hist"]) and (live["alert"] == (source["p_near"] >= 0.5)).all()
