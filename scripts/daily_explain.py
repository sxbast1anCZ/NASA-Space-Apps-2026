"""Reasons behind each alert of the next-day outlook, in plain words (SHAP values of the model).

For every row of the app file with `alert` = 1, the model's score is split into the contribution of
each feature (TreeSHAP, built into LightGBM: `pred_contrib`). Features are added up into six groups
a person can read, and the groups that push the score up become one sentence each.

What a reason is, and is not: it says which inputs moved the model's score for that cell and day. It
is not a cause of fire. The model knows fire history, neighbours, the calendar and the place; it has
no weather, vegetation or human activity, so no reason can mention them.

Inputs (NASA_Data_Sources/processed/):
    daily/panel.parquet         features of every row (scripts/daily_panel.py)
    daily/model_<country>.txt   the booster that scores the live day (scripts/daily_train.py)
    risk/daily_model.json       which run was kept, its features, rounds and threshold
    risk/cells_daily.parquet    the app file: which rows are alerts, and the probabilities to match

Output:
    risk/cells_daily_reasons.parquet   one row per alert: burn_date, cell_lat, cell_lon, then
        reason_1..3 (sentences, strongest first; empty when fewer groups push up) and share_1..3
        (that group's part of everything that pushes the score up).

The test years were scored by the model fitted on `train`, which is not saved: it is fitted again
here with the recorded number of rounds, and the script stops unless its probabilities equal the
ones in the app file. Countries whose app rows come from the baseline get no reasons.

Run:  python scripts/daily_explain.py
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import daily_eval as de
import daily_train as dt

DATA = de.DATA
KEYS = de.KEYS
TOP = 3
GROUPS = {          # group -> prefixes or names of its features
    "recent": ("lag_fire_d", "lag_fire_days_", "lag_days_since_fire"),
    "intensity": ("lag_hotspots_d0", "lag_frp_", "lag_night_d0"),
    "nearby": ("nbr_",),
    "history": ("hist_",),
    "calendar": ("cal_",),
    "place": ("geo_",),
}


def group_of(feature: str) -> str:
    for group, starts in GROUPS.items():
        if feature.startswith(starts):
            return group
    return "other"


def _num(row: dict, name: str) -> float:
    value = row.get(name)
    return float("nan") if value is None or pd.isna(value) else float(value)


def _count(n: float, noun: str) -> str:
    return f"{n:.0f} {noun}{'' if n == 1 else 's'}"


def sentence(group: str, row: dict) -> str:
    """One plain sentence for a group, with the values of that row. `row` maps feature name to value."""
    if group == "recent":
        today, week, month = _num(row, "lag_fire_d0"), _num(row, "lag_fire_days_7"), _num(row, "lag_fire_days_30")
        since = _num(row, "lag_days_since_fire")
        if today == 1:
            return ("Fire was detected in this cell today" +
                    (f", and on {week:.0f} of the last 7 days" if week > 1 else ""))
        if since < 365:
            return (f"The last fire in this cell was {_count(since, 'day')} ago" +
                    (f", with {_count(month, 'day')} of fire in the last 30" if month >= 1 else ""))
        return "Recent fire history of this cell"
    if group == "intensity":
        hotspots = _num(row, "lag_hotspots_d0")
        if hotspots >= 1:
            return (f"Today's fire here had {_count(hotspots, 'hotspot')}" +
                    (", and it was still burning at night" if _num(row, "lag_night_d0") == 1 else ""))
        return "Strength of today's fire in this cell"
    if group == "nearby":
        first, second, week = _num(row, "nbr_fire_d0"), _num(row, "nbr_ring2_fire_d0"), _num(row, "nbr_fire_days_7")
        if first >= 1:
            return f"{first:.0f} of the 8 neighbouring cells had fire today"
        if second >= 1:
            return f"{_count(second, 'cell')} within two cells of this one had fire today"
        if week >= 1:
            return "Neighbouring cells had fire during the last 7 days"
        return "Fire activity around this cell"
    if group == "history":
        rate = _num(row, "hist_doy_rate")
        if rate == rate:
            return f"In earlier years this cell had fire on {rate:.0%} of the days at this time of the year"
        return "Fire history of this cell in earlier years"
    if group == "calendar":
        return "The day of the week and the time of the year"
    if group == "place":
        return "This part of the country has more fire activity"
    return "Other inputs of the model"


def reasons(contrib: np.ndarray, features: list[str], values: pd.DataFrame, top: int = TOP) -> pd.DataFrame:
    """Top groups that push the score up, per row. `contrib` has one column per feature (no bias column)."""
    names = sorted(set(map(group_of, features)))
    of = np.array([names.index(group_of(f)) for f in features])
    grouped = np.stack([contrib[:, of == k].sum(axis=1) for k in range(len(names))], axis=1)
    up = np.clip(grouped, 0, None)
    total = up.sum(axis=1)
    order = np.argsort(-grouped, axis=1, kind="stable")[:, :top]
    rows = values[features].to_dict("records")
    out = {}
    for rank in range(top):
        k = order[:, rank] if rank < order.shape[1] else np.full(len(rows), -1)
        push = grouped[np.arange(len(rows)), k] if rank < order.shape[1] else np.zeros(len(rows))
        out[f"reason_{rank + 1}"] = [sentence(names[j], r) if p > 0 else "" for j, p, r in zip(k, push, rows)]
        out[f"share_{rank + 1}"] = np.where(push > 0, push / np.where(total > 0, total, 1), 0).astype("float32")
    return pd.DataFrame(out, index=values.index)


def explain(booster, rows: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    contrib = booster.predict(rows[features], pred_contrib=True)[:, :-1]      # the last column is the bias
    return pd.concat([rows[KEYS], reasons(contrib, features, rows)], axis=1)


def explain_country(g: pd.DataFrame, summary: dict, app: pd.DataFrame, final) -> pd.DataFrame:
    """Reasons for the alert rows of one country. `final` is the saved booster of the live day."""
    run = summary["runs"][summary["kept_run"]]
    features = run["features"]
    rows = g.merge(app[KEYS + ["probability", "alert"]], on=KEYS, how="inner")
    live = rows["split"] == "live"
    scored = dt.fit(g[g["split"] == "train"], features, rounds=run["rounds"])     # the model of the test years
    p = np.where(live, final.predict(rows[features]), scored.predict(rows[features]))
    worst = float(np.abs(p - rows["probability"]).max()) if len(rows) else 0.0
    if worst > 1e-5:
        raise SystemExit(f"The rebuilt model does not match the app file (largest difference {worst:.2g}). "
                         "Run scripts/daily_train.py again and then this script.")
    alerts = rows[rows["alert"] == 1]
    parts = [explain(scored, alerts[~live[alerts.index]], features), explain(final, alerts[live[alerts.index]], features)]
    return pd.concat([x for x in parts if len(x)]) if len(alerts) else pd.DataFrame()


def main(argv=None) -> None:
    import lightgbm as lgb

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--panel", type=Path, default=DATA / "daily" / "panel.parquet")
    ap.add_argument("--daily", type=Path, default=DATA / "daily", help="folder with model_<country>.txt")
    ap.add_argument("--risk", type=Path, default=DATA / "risk")
    args = ap.parse_args(argv)

    report = json.loads((args.risk / "daily_model.json").read_text())
    app = pd.read_parquet(args.risk / "cells_daily.parquet")
    app["burn_date"] = pd.to_datetime(app["burn_date"])
    out = []
    for country, summary in report["countries"].items():
        if summary["used_in_app"] != "model":
            print(f"{country}: the app shows the baseline, no reasons")
            continue
        features = summary["runs"][summary["kept_run"]]["features"]
        g = pd.read_parquet(args.panel, columns=KEYS + ["split", "fire"] + features,
                            filters=[("country", "==", country)])
        g["burn_date"] = pd.to_datetime(g["burn_date"])
        final = lgb.Booster(model_file=str(args.daily / f"model_{country.lower()}.txt"))
        part = explain_country(g, summary, app, final)
        out.append(part)
        print(f"{country}: {len(part):,} alerts explained")
    if not out:
        return
    res = pd.concat(out).sort_values(KEYS)
    res["burn_date"] = res["burn_date"].dt.date
    res.to_parquet(args.risk / "cells_daily_reasons.parquet", index=False)
    print(f"Written: {args.risk / 'cells_daily_reasons.parquet'} ({len(res):,} rows)")
    print(res["reason_1"].str.replace(r"\d+", "N", regex=True).value_counts().head(8).to_string())


if __name__ == "__main__":
    main()
