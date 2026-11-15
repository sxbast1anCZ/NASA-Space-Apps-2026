"""Hand-made cases for scripts/daily_eval.py (docs/modeling-plan.md, card 2)."""

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import daily_eval as de  # noqa: E402


# ---------------------------------------------------------------- thresholds

def test_threshold_is_the_highest_that_reaches_the_recall():
    y = [1, 1, 1, 1, 0, 0]
    p = [0.9, 0.8, 0.7, 0.1, 0.6, 0.2]
    assert de.pick_threshold(y, p, 0.75) == 0.7     # 3 of 4 fires
    assert de.pick_threshold(y, p, 0.80) == 0.1     # 3 of 4 is not enough: the fourth is needed
    assert de.pick_threshold(y, p, 1.00) == 0.1


def test_threshold_does_not_ask_for_one_fire_too_many():
    # 0.8 * 15 is 12.000000000000002 in floating point: the answer is the 12th fire, not the 13th.
    p = np.arange(15, 0, -1) / 100
    assert de.pick_threshold(np.ones(15), p, 0.80) == pytest.approx(0.04)


def test_threshold_with_tied_scores_still_reaches_the_recall():
    y, p = [1, 1, 0, 1], [0.5, 0.5, 0.5, 0.2]
    t = de.pick_threshold(y, p, 0.5)
    assert t == 0.5
    assert de.scores(y, p, t)["recall"] == pytest.approx(2 / 3)   # the tie flags both, and one false alarm


def test_threshold_needs_fire_rows_and_a_valid_recall():
    with pytest.raises(ValueError):
        de.pick_threshold([0, 0], [0.1, 0.9], 0.8)
    with pytest.raises(ValueError):
        de.pick_threshold([1, 0], [0.1, 0.9], 0.0)


def test_budget_threshold_flags_exactly_the_budget_without_ties():
    p = np.arange(100) / 100
    assert (p >= de.threshold_within_budget(p, 10)).sum() == 10
    assert (p >= de.threshold_within_budget(p, 100)).sum() == 100
    assert (p >= de.threshold_within_budget(p, 500)).sum() == 100


def test_budget_threshold_never_goes_over_the_budget_with_ties():
    p = np.array([0.9, 0.5, 0.5, 0.5, 0.5, 0.1])
    assert (p >= de.threshold_within_budget(p, 1)).sum() == 1
    assert (p >= de.threshold_within_budget(p, 3)).sum() == 1      # the four tied rows do not fit in 3
    assert (p >= de.threshold_within_budget(p, 5)).sum() == 5
    everything_tied = np.full(6, 0.3)
    assert (everything_tied >= de.threshold_within_budget(everything_tied, 1)).sum() == 0


def test_a_budget_of_zero_alerts_flags_nothing():
    t = de.threshold_within_budget([0.9, 0.1], 0)
    assert math.isinf(t) and de.scores([1, 0], [0.9, 0.1], t)["tp"] == 0


# ---------------------------------------------------------------- scores

def test_scores_of_a_case_counted_by_hand():
    y = [1, 1, 0, 0, 0]
    p = [0.9, 0.2, 0.8, 0.1, 0.1]
    s = de.scores(y, p, 0.5, n_days=2)
    assert (s["tp"], s["fp"], s["fn"], s["tn"]) == (1, 1, 1, 2)
    assert s["recall"] == 0.5 and s["fn_rate"] == 0.5 and s["precision"] == 0.5
    assert s["f2"] == pytest.approx(5 / 10)             # 5 TP / (5 TP + 4 FN + FP)
    assert s["false_alarm_rate"] == pytest.approx(1 / 3)
    assert s["alerts_per_day"] == 1.0 and s["flagged_share"] == pytest.approx(0.4)
    assert s["rows"] == 5 and s["fire"] == 2


def test_recall_and_false_negative_rate_add_up():
    rng = np.random.default_rng(0)
    y, p = rng.random(500) < 0.1, rng.random(500)
    s = de.scores(y, p, 0.3)
    assert s["recall"] + s["fn_rate"] == pytest.approx(1)
    assert s["tp"] + s["fp"] + s["fn"] + s["tn"] == 500


def test_scores_without_fire_rows_are_nan_not_an_error():
    s = de.scores([0, 0, 0], [0.9, 0.1, 0.2], 0.5)
    assert math.isnan(s["recall"]) and math.isnan(s["pr_auc"]) and math.isnan(s["f2"])
    assert s["fp"] == 1 and s["false_alarm_rate"] == pytest.approx(1 / 3)


def test_a_missing_score_is_never_flagged():
    s = de.scores([1, 1], [np.nan, 0.9], 0.0)
    assert (s["tp"], s["fn"]) == (1, 1)


def test_flagging_everything_gives_full_recall_and_every_alert():
    s = de.scores([1, 0, 0, 0], [0.4, 0.3, 0.2, 0.1], 0.0, n_days=1)
    assert s["recall"] == 1.0 and s["alerts_per_day"] == 4 and s["false_alarm_rate"] == 1.0


# ---------------------------------------------------------------- breakdown and report

def panel() -> pd.DataFrame:
    """Two countries, tune 2021 and test 2023, four cells a day. `p_model` ranks fires first on tune."""
    rows = []
    for split, year in (("tune", 2021), ("test", 2023)):
        for day in pd.date_range(f"{year}-01-01", periods=10):
            for country in ("Chile", "Argentina"):
                for cell in range(4):
                    fire = int(cell == 0 or (cell == 1 and day.day % 2 == 0))
                    rows.append({
                        "burn_date": day, "cell_lat": -30.0 - cell * 0.25,
                        "cell_lon": -71.0 if country == "Chile" else -60.0,
                        "country": country, "admin1": "A", "segment": country[:2].upper() + "-PV",
                        "split": split, "fire": fire, "new_cell": int(cell == 1),
                        "p_hist": 0.5 if cell == 0 else 0.1,
                        "p_persist": float(cell == 0), "p_near": float(cell <= 1),
                        "p_model": [0.9, 0.6, 0.2, 0.1][cell],
                    })
    return pd.DataFrame(rows)


def test_breakdown_has_one_row_per_group_and_counts_its_own_days():
    df = panel()
    df = df[(df["split"] == "test") & (df["country"] == "Chile")]
    out = de.breakdown(df, "p_model", 0.5, "new_cell")
    assert list(out["new_cell"]) == [0, 1]
    new = out[out["new_cell"] == 1].iloc[0]
    assert new["rows"] == 10 and new["fire"] == 5 and new["recall"] == 1.0
    assert new["alerts_per_day"] == 1.0          # 10 alerts on 10 days


def test_rules_keep_their_own_threshold_and_models_get_one_from_tune():
    res = de.evaluate(panel(), ["p_hist", "p_persist", "p_near", "p_model"], 0.80)
    rule = res[(res["score"] == "p_near") & (res["group"] == "all")]
    assert set(rule["operating_point"]) == {"rule"} and set(rule["threshold"]) == {0.5}
    model = res[(res["score"] == "p_model") & (res["group"] == "all") & (res["country"] == "Chile")]
    assert set(model["operating_point"]) == {"recall", "alerts of p_near"}
    at_recall = model[(model["operating_point"] == "recall") & (model["split"] == "test")].iloc[0]
    assert at_recall["threshold"] == 0.6 and at_recall["recall"] == 1.0 and at_recall["fn"] == 0


def test_the_threshold_does_not_look_at_test_rows():
    df = panel()
    changed = df.copy()
    changed.loc[changed["split"] == "test", "fire"] = 1 - changed.loc[changed["split"] == "test", "fire"]
    a = de.evaluate(df, ["p_model"], 0.80)
    b = de.evaluate(changed, ["p_model"], 0.80)
    assert list(a["threshold"]) == list(b["threshold"])


def test_command_writes_json_and_markdown(tmp_path):
    df = panel()
    df.drop(columns="p_model").to_parquet(tmp_path / "panel.parquet")
    pred = df[["burn_date", "cell_lat", "cell_lon"]].assign(model="lgbm", probability=df["p_model"])
    pred.to_parquet(tmp_path / "predictions.parquet")
    de.main(["--panel", str(tmp_path / "panel.parquet"), "--predictions", str(tmp_path / "predictions.parquet"),
             "--out", str(tmp_path / "risk")])
    data = json.loads((tmp_path / "risk" / "daily_metrics.json").read_text())   # strict JSON: no NaN
    assert data["min_recall"] == 0.8
    assert {r["score"] for r in data["results"]} == {"p_hist", "p_persist", "p_near", "lgbm"}
    assert {r["country"] for r in data["results"]} == {"Chile", "Argentina"}
    text = (tmp_path / "risk" / "daily_metrics.md").read_text()
    assert "## All rows" in text and "| Chile | lgbm | recall | test |" in text


def test_command_runs_with_baselines_only(tmp_path):
    panel().drop(columns="p_model").to_parquet(tmp_path / "panel.parquet")
    de.main(["--panel", str(tmp_path / "panel.parquet"), "--predictions", str(tmp_path / "none.parquet"),
             "--out", str(tmp_path)])
    assert (tmp_path / "daily_metrics.json").exists()


def test_a_model_never_gets_more_alerts_than_p_near_on_tune():
    df = panel()
    df["p_model"] = 0.5                                   # every score tied: nothing fits a smaller budget
    df.loc[df["cell_lat"] == -30.0, "p_model"] = 0.9      # one cell in four stands out; p_near flags two
    res = de.evaluate(df, ["p_near", "p_model"], 0.80)
    tune = res[(res["split"] == "tune") & (res["group"] == "all")]
    for country in ("Chile", "Argentina"):
        t = tune[tune["country"] == country].set_index(["score", "operating_point"])
        rule, model = t.loc[("p_near", "rule")], t.loc[("p_model", "alerts of p_near")]
        assert model["tp"] + model["fp"] <= rule["tp"] + rule["fp"]


def test_a_rule_without_alerts_leaves_the_model_without_alerts(tmp_path):
    df = panel()
    df["p_near"] = 0.0
    res = de.evaluate(df, ["p_near", "p_model"], 0.80)
    at_budget = res[(res["score"] == "p_model") & (res["operating_point"] == "alerts of p_near")]
    assert (at_budget["tp"] + at_budget["fp"] == 0).all()
    assert "none flagged" in de.to_markdown(res, 0.80)
    json.loads(res.to_json(orient="records"))             # infinity is written as null: strict JSON
