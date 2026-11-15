"""Next-day models: one LightGBM per country (docs/modeling-plan.md, section 0, card 3).

For each country, two runs on the same rows: the default without calendar features and a
comparison run with them. Each is fitted on `train` with early stopping on `tune`. The run that
needs fewer alerts to reach the required recall on `tune` is kept, and it is used in the app only
if it also beats the two baselines on `tune`. The `test` years are scored once, with the model
fitted on `train` and the threshold chosen on `tune`, and nothing is chosen on them.

Input:
    NASA_Data_Sources/processed/daily/panel.parquet   from scripts/daily_panel.py (section 4.1 of the
        plan). Rows with split `live` (no target) are the day after the last complete day.

Outputs:
    daily/predictions.parquet     tune and test rows of both runs: burn_date, cell_lat, cell_lon,
                                  model (`lgbm` or `lgbm_calendar`), probability
    daily/model_<country>.txt     the booster that scores the live day (refitted on every labelled year)
    risk/cells_daily.parquet      test years and the live day, for the web app: burn_date, cell_lat,
                                  cell_lon, probability, baseline_probability, alert
    risk/daily_model.json         per country: features, rounds, thresholds, which run was kept and why
    risk/daily_metrics.json, .md  from scripts/daily_eval.py

Run:  python scripts/daily_train.py [--min-recall 0.80]
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import daily_eval as de
from risk_model import PARAMS

DATA = de.DATA
KEYS = de.KEYS
PREFIXES = ("lag_", "nbr_", "hist_", "geo_", "wx_")           # wx_ only once the panel has weather
CALENDAR = ("cal_month", "cal_doy_sin", "cal_doy_cos")         # left out by default (plan, section 0)
RUNS = {"lgbm": False, "lgbm_calendar": True}                  # name -> with calendar features
MAX_ROUNDS = 2000


def feature_columns(columns, calendar: bool) -> list[str]:
    """Features by their prefix. The target, the baselines, the split and the year can never match."""
    feats = [c for c in columns if c.startswith(PREFIXES) or c == "cal_dow"]
    if calendar:
        feats += [c for c in CALENDAR if c in columns]
    if not feats:
        raise SystemExit("The panel has no feature columns (prefixes lag_, nbr_, hist_, geo_)")
    return feats


def fit(df: pd.DataFrame, features: list[str], valid: pd.DataFrame | None = None, rounds: int = MAX_ROUNDS):
    """With `valid`: early stopping by average precision. Without: exactly `rounds` rounds."""
    import lightgbm as lgb

    dtrain = lgb.Dataset(df[features], df["fire"].astype("int8"))
    if valid is None:
        return lgb.train(PARAMS, dtrain, num_boost_round=rounds)
    dvalid = lgb.Dataset(valid[features], valid["fire"].astype("int8"), reference=dtrain)
    return lgb.train({**PARAMS, "metric": "average_precision"}, dtrain, num_boost_round=rounds,
                     valid_sets=[dvalid], callbacks=[lgb.early_stopping(50, verbose=False)])


def flagged_share(p, threshold: float) -> float:
    return float((np.asarray(p) >= threshold).mean())


def train_country(g: pd.DataFrame, min_recall: float, max_rounds: int = MAX_ROUNDS):
    """Both runs for one country. Returns (predictions, app rows, booster for the live day, summary)."""
    parts = {s: g[g["split"] == s] for s in ("train", "tune", "test", "live")}
    train, tune, test, live = parts["train"], parts["tune"], parts["test"], parts["live"]
    if train.empty or tune.empty or not tune["fire"].any():
        raise SystemExit(f"{g['country'].iloc[0]}: the panel needs train rows and tune rows with fire")

    runs, preds = {}, []
    for name, calendar in RUNS.items():
        feats = feature_columns(g.columns, calendar)
        booster = fit(train, feats, tune, max_rounds)
        p_tune = booster.predict(tune[feats])
        threshold = de.pick_threshold(tune["fire"], p_tune, min_recall)
        runs[name] = {"features": feats, "booster": booster, "rounds": booster.best_iteration or max_rounds,
                      "threshold": threshold, "p_tune": p_tune,
                      "tune_flagged_share": flagged_share(p_tune, threshold)}
        for part, p in ((tune, p_tune), (test, booster.predict(test[feats]) if len(test) else [])):
            preds.append(part[KEYS].assign(model=name, probability=np.asarray(p, dtype="float32")))

    # Fewer alerts at the required recall wins; a tie keeps the run without calendar features.
    kept = min(RUNS, key=lambda n: runs[n]["tune_flagged_share"])
    run = runs[kept]

    # The model replaces the baselines only if it beats both on tune (plan, section 7).
    y = tune["fire"].to_numpy().astype(bool)
    near = tune["p_near"].to_numpy() >= 0.5
    at_near_budget = run["p_tune"] >= de.threshold_for_share(run["p_tune"], max(near.mean(), 1 / len(tune)))
    hist_share = flagged_share(tune["p_hist"], de.pick_threshold(y, tune["p_hist"], min_recall))
    checks = {
        "recall_at_alerts_of_p_near": float((at_near_budget & y).sum() / y.sum()),
        "recall_of_p_near": float((near & y).sum() / y.sum()),
        "flagged_share_at_recall": run["tune_flagged_share"],
        "flagged_share_of_p_hist_at_recall": hist_share,
    }
    use_model = (checks["recall_at_alerts_of_p_near"] > checks["recall_of_p_near"]
                 and run["tune_flagged_share"] < hist_share)

    # The live day is scored by the kept run, refitted on every year that has a target.
    feats = run["features"]
    final = fit(g[g["split"] != "live"], feats, rounds=run["rounds"])
    app = pd.concat([test, live])
    if use_model:
        p = np.concatenate([run["booster"].predict(test[feats]) if len(test) else [],
                            final.predict(live[feats]) if len(live) else []])
        alert = p >= run["threshold"]
    else:
        p, alert = app["p_hist"].to_numpy(), app["p_near"].to_numpy() >= 0.5
    app = app[KEYS].assign(probability=np.asarray(p, dtype="float32"),
                           baseline_probability=app["p_hist"].astype("float32").to_numpy(),
                           alert=alert.astype("int8"))

    gain = dict(zip(feats, final.feature_importance("gain")))
    total = sum(gain.values()) or 1.0
    summary = {
        "rows": {s: int(len(d)) for s, d in parts.items()},
        "kept_run": kept,
        "used_in_app": "model" if use_model else "baseline",
        "threshold": run["threshold"],
        "checks_on_tune": checks,
        "runs": {n: {k: r[k] for k in ("features", "rounds", "threshold", "tune_flagged_share")}
                 for n, r in runs.items()},
        "gain_share": {k: round(float(v / total), 4) for k, v in sorted(gain.items(), key=lambda kv: -kv[1])},
    }
    return pd.concat(preds), app, final, summary


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--panel", type=Path, default=DATA / "daily" / "panel.parquet")
    ap.add_argument("--out-daily", type=Path, default=DATA / "daily")
    ap.add_argument("--out-risk", type=Path, default=DATA / "risk")
    ap.add_argument("--min-recall", type=float, default=0.80)
    ap.add_argument("--max-rounds", type=int, default=MAX_ROUNDS)
    args = ap.parse_args(argv)
    if not args.panel.exists():
        raise SystemExit(f"{args.panel} not found. Build it with scripts/daily_panel.py")

    import pyarrow.parquet as pq

    names = pq.read_schema(args.panel).names
    needed = KEYS + ["country", "split", "fire", "p_hist", "p_near"]
    if missing := sorted(set(needed) - set(names)):
        raise SystemExit(f"{args.panel} lacks {missing} (docs/modeling-plan.md, section 4.1)")
    columns = needed + feature_columns(names, calendar=True)
    countries = pq.read_table(args.panel, columns=["country"])["country"].unique().to_pylist()

    args.out_daily.mkdir(parents=True, exist_ok=True)
    args.out_risk.mkdir(parents=True, exist_ok=True)
    preds, apps, report = [], [], {"min_recall": args.min_recall, "countries": {}}
    for country in sorted(countries):   # one country in memory at a time
        g = pd.read_parquet(args.panel, columns=columns, filters=[("country", "==", country)])
        g["burn_date"] = pd.to_datetime(g["burn_date"])
        pred, app, booster, summary = train_country(g, args.min_recall, args.max_rounds)
        booster.save_model(str(args.out_daily / f"model_{country.lower()}.txt"))
        preds.append(pred), apps.append(app)
        report["countries"][country] = summary
        print(f"{country}: kept {summary['kept_run']}, threshold {summary['threshold']:.4f}, "
              f"app shows the {summary['used_in_app']}")

    predictions = args.out_daily / "predictions.parquet"
    pd.concat(preds).to_parquet(predictions, index=False)
    pd.concat(apps).sort_values(KEYS).to_parquet(args.out_risk / "cells_daily.parquet", index=False)
    (args.out_risk / "daily_model.json").write_text(json.dumps(report, indent=2) + "\n")
    de.main(["--panel", str(args.panel), "--predictions", str(predictions), "--out", str(args.out_risk),
             "--min-recall", str(args.min_recall)])


if __name__ == "__main__":
    main()
