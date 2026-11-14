"""Risk model: probability of fire activity per 0.25 degree cell and week (block 8, module M5).

A LightGBM classifier on top of the baseline (scripts/risk_baseline.py). It must beat the baseline
on later years it never saw; if it does not, the app keeps the baseline (docs/findings/08-risk-model.md).

Inputs:
    NASA_Data_Sources/processed/hotspots/                    target and fire history (VIIRS)
    NASA_Data_Sources/processed/quality/                      block 1 filter and outages
    NASA_Data_Sources/processed/weather/weekly.parquet        from scripts/risk_weather.py
    NASA_Data_Sources/processed/weather/cell_to_point.parquet

Outputs (NASA_Data_Sources/processed/risk/):
    cells_weekly.parquet    contract C3. `probability` comes from the model where it was tested
                            out of sample or can forecast, and from the baseline elsewhere:
                              - test years (default 2023-2025): model trained on earlier years only
                              - current year, observed weeks and the current partial week: model
                                refitted on every complete year
                              - weeks after the current one, and years before the test: baseline
    model_eval.parquet      the same rows plus `observed` and `source` (model or baseline)
    model_metrics.json      model against baseline on the test years, feature importance, settings

Every feature is known before the week starts:
    baseline_probability     history of the cell for that week, earlier years only

Cells in year Y: only those with a reference detection before Y (scripts/risk_baseline.py), so
the panel does not leak which cells burn later.
    fire_prev_1w / _4w       fire in the cell in the previous 1 and 4 weeks
    nbr_fire_prev_1w         neighbouring cells (8) with fire in the previous week
    week_sin, week_cos       season
    cell_lat, cell_lon       position
    ante_*                   weather of the days before the week (NASA POWER)

Run:
    python scripts/risk_model.py
    python scripts/risk_model.py --no-weather       # history only, to measure what weather adds
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from risk_baseline import (
    CELL_DEG, HOTSPOTS, N_WEEKS, OUT, QUALITY, baseline_for_year, build_panel, eligible_cells, evaluate,
    load_detections, load_outages, observed_weeks, select_target_rows, target_outage_days, week_end,
    week_start,
)

ROOT = Path(__file__).resolve().parents[1]
WEATHER = ROOT / "NASA_Data_Sources" / "processed" / "weather"

PARAMS = {
    "objective": "binary",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 200,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "lambda_l2": 1.0,
    "verbose": -1,
    "seed": 42,
}


# ---------------------------------------------------------------- features

def neighbour_ids(cells: pd.DataFrame) -> np.ndarray:
    """ids[cell, 8] of the surrounding cells, -1 where there is no fire cell."""
    index = {(round(a, 4), round(b, 4)): i for i, (a, b) in enumerate(zip(cells["cell_lat"], cells["cell_lon"]))}
    ids = np.full((len(cells), 8), -1, dtype=np.int64)
    steps = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)]
    for i, (a, b) in enumerate(zip(cells["cell_lat"], cells["cell_lon"])):
        for k, (dy, dx) in enumerate(steps):
            ids[i, k] = index.get((round(a + dy * CELL_DEG, 4), round(b + dx * CELL_DEG, 4)), -1)
    return ids


def history_features(fire: np.ndarray, avail: np.ndarray, nbr: np.ndarray) -> dict[str, np.ndarray]:
    """Lag features on the flattened week axis t = year * 52 + week. NaN when not observed."""
    n_cells = fire.shape[0]
    f = fire.reshape(n_cells, -1).astype("float32")
    a = avail.reshape(-1)
    f[:, ~a] = np.nan
    prev1 = np.full_like(f, np.nan)
    prev1[:, 1:] = f[:, :-1]
    prev4 = np.full_like(f, np.nan)
    for t in range(4, f.shape[1]):
        prev4[:, t] = f[:, t - 4:t].sum(axis=1) if a[t - 4:t].all() else np.nan
    padded = np.vstack([prev1, np.zeros((1, prev1.shape[1]), dtype="float32")])  # row -1 = no cell
    nbr_prev1 = padded[nbr].sum(axis=1)
    nbr_prev1[:, np.isnan(prev1).all(axis=0)] = np.nan
    shape = fire.shape
    return {"fire_prev_1w": prev1.reshape(shape), "fire_prev_4w": prev4.reshape(shape),
            "nbr_fire_prev_1w": nbr_prev1.reshape(shape)}


def weather_table(cells: pd.DataFrame, weather_dir: Path) -> pd.DataFrame | None:
    weekly_path, map_path = weather_dir / "weekly.parquet", weather_dir / "cell_to_point.parquet"
    if not weekly_path.exists() or not map_path.exists():
        return None
    weekly = pd.read_parquet(weekly_path)
    mapping = pd.read_parquet(map_path)[["cell_lat", "cell_lon", "point_lat", "point_lon"]]
    ante = [c for c in weekly if c.startswith("ante_")]
    w = cells.reset_index().merge(mapping, on=["cell_lat", "cell_lon"], how="left")
    w = w.merge(weekly[["point_lat", "point_lon", "year", "week"] + ante],
                on=["point_lat", "point_lon"], how="left")
    return w[["cell_id", "year", "week"] + ante]


def assemble(years, cells, fire, avail, hist, last_day, horizon_end, args) -> pd.DataFrame:
    """One row per cell and week to score: observed weeks and the forecast weeks."""
    frames = []
    for i, yr in enumerate(years):
        if i < args.min_years:
            continue
        base = baseline_for_year(fire, avail, i, args.window, args.shrink)
        keep = eligible_cells(fire, avail, i)  # cells with history before this year only
        ids = np.flatnonzero(keep)
        for w in range(N_WEEKS):
            s, e = week_start(yr, w), week_end(yr, w)
            is_obs = bool(avail[i, w])
            if not is_obs and not (e > last_day and s <= horizon_end):
                continue
            frames.append(pd.DataFrame({
                "cell_id": ids, "year": yr, "week": w,
                "week_start": s.date(),
                "observed": fire[ids, i, w].astype("float32") if is_obs else np.nan,
                "baseline_probability": base[ids, w].astype("float32"),
                "fire_prev_1w": hist["fire_prev_1w"][ids, i, w],
                "fire_prev_4w": hist["fire_prev_4w"][ids, i, w],
                "nbr_fire_prev_1w": hist["nbr_fire_prev_1w"][ids, i, w],
                # The model forecasts the week in progress only: later weeks have no weather yet.
                "model_ok": is_obs or (s <= last_day < e),
            }))
    df = pd.concat(frames, ignore_index=True)
    df["week_sin"] = np.sin(2 * np.pi * df["week"] / N_WEEKS).astype("float32")
    df["week_cos"] = np.cos(2 * np.pi * df["week"] / N_WEEKS).astype("float32")
    df = df.merge(cells.reset_index(), on="cell_id", how="left")
    return df


# ---------------------------------------------------------------- main

def main() -> None:
    import lightgbm as lgb

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hotspots", type=Path, default=HOTSPOTS)
    ap.add_argument("--weather", type=Path, default=WEATHER)
    ap.add_argument("--quality", type=Path, default=QUALITY, help="folder with the block 1 quality files")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--no-weather", action="store_true")
    ap.add_argument("--train-until", type=int, default=2020)
    ap.add_argument("--valid-until", type=int, default=2022)
    ap.add_argument("--test-until", type=int, default=2025)
    ap.add_argument("--min-years", type=int, default=4)
    ap.add_argument("--window", type=int, default=1)
    ap.add_argument("--shrink", type=float, default=3.0)
    ap.add_argument("--horizon-weeks", type=int, default=8)
    args = ap.parse_args()

    df = load_detections(args.hotspots, args.quality)
    df["cell_lat"] = np.floor(df["latitude"] / CELL_DEG) * CELL_DEG
    df["cell_lon"] = np.floor(df["longitude"] / CELL_DEG) * CELL_DEG
    rows, first_day, switch, last_day = select_target_rows(df, "reference")
    horizon_end = last_day + pd.Timedelta(days=7 * args.horizon_weeks)
    years = np.arange(first_day.year, horizon_end.year + 1)
    cells = (df[["cell_lat", "cell_lon"]].drop_duplicates()
             .sort_values(["cell_lat", "cell_lon"]).reset_index(drop=True))
    cells.index.name = "cell_id"
    fire = build_panel(rows, years, cells)
    avail = observed_weeks(years, first_day, last_day,
                           target_outage_days(load_outages(args.quality), "reference", switch))
    hist = history_features(fire, avail, neighbour_ids(cells))
    table = assemble(years, cells, fire, avail, hist, last_day, horizon_end, args)

    features = ["baseline_probability", "fire_prev_1w", "fire_prev_4w", "nbr_fire_prev_1w",
                "week_sin", "week_cos", "cell_lat", "cell_lon"]
    if not args.no_weather:
        weather = weather_table(cells, args.weather)
        if weather is None:
            raise SystemExit(f"No weather in {args.weather}. Run scripts/risk_weather.py or use --no-weather.")
        table = table.merge(weather, on=["cell_id", "year", "week"], how="left")
        ante = [c for c in weather if c.startswith("ante_")]
        features += ante
        print(f"Weather features: {len(ante)} | rows without weather: {table[ante[0]].isna().mean():.1%}")

    obs = table["observed"].notna()
    train = obs & (table["year"] <= args.train_until)
    valid = obs & (table["year"] > args.train_until) & (table["year"] <= args.valid_until)
    test = obs & (table["year"] > args.valid_until) & (table["year"] <= args.test_until)
    print(f"Rows: train {train.sum():,} | valid {valid.sum():,} | test {test.sum():,} | "
          f"fire rate in train {table.loc[train, 'observed'].mean():.2%}")
    if not (train.any() and valid.any() and test.any()):
        raise SystemExit("Not enough years for train / valid / test. Check --train-until and the data range.")

    def fit(mask, rounds=None, valid_mask=None):
        dtrain = lgb.Dataset(table.loc[mask, features], table.loc[mask, "observed"])
        if valid_mask is None:
            return lgb.train(PARAMS, dtrain, num_boost_round=rounds)
        dvalid = lgb.Dataset(table.loc[valid_mask, features], table.loc[valid_mask, "observed"], reference=dtrain)
        return lgb.train(PARAMS, dtrain, num_boost_round=2000, valid_sets=[dvalid],
                         callbacks=[lgb.early_stopping(50, verbose=False)])

    model = fit(train, valid_mask=valid)
    best = model.best_iteration or 200
    test_model = fit(train | valid, rounds=best)  # trained up to --valid-until, never sees test years

    y = table.loc[test, "observed"].to_numpy().astype(int)
    p_model = test_model.predict(table.loc[test, features])
    p_base = table.loc[test, "baseline_probability"].to_numpy()
    metrics = {"model": evaluate(y, p_model), "baseline": evaluate(y, p_base), "per_year": {}}
    for yr in sorted(table.loc[test, "year"].unique()):
        m = (table.loc[test, "year"] == yr).to_numpy()
        metrics["per_year"][str(yr)] = {"model": evaluate(y[m], p_model[m]), "baseline": evaluate(y[m], p_base[m])}
    beats = (metrics["model"]["average_precision"] > metrics["baseline"]["average_precision"]
             and metrics["model"]["brier"] < metrics["baseline"]["brier"])
    metrics["model_beats_baseline"] = bool(beats)

    # Probabilities for the output: model where it is out of sample or forecasting, baseline elsewhere.
    table["probability"] = table["baseline_probability"].astype("float64")
    table["source"] = "baseline"
    table.loc[test, "probability"] = p_model
    table.loc[test, "source"] = "model"
    current = table["model_ok"] & (table["year"] > args.test_until)
    if current.any():
        final = fit(obs & (table["year"] <= args.test_until), rounds=best)
        table.loc[current, "probability"] = final.predict(table.loc[current, features])
        table.loc[current, "source"] = "model"
    if not beats:
        print("Model does NOT beat the baseline: writing the baseline as `probability`.")
        table["probability"] = table["baseline_probability"].astype("float64")
        table["source"] = "baseline"

    importance = dict(zip(features, test_model.feature_importance("gain").round(1).tolist()))
    metrics["feature_importance_gain"] = dict(sorted(importance.items(), key=lambda kv: -kv[1]))
    metrics["settings"] = {**{k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
                           "best_iteration": int(best), "features": features,
                           "last_day": str(last_day.date())}

    args.out.mkdir(parents=True, exist_ok=True)
    table["probability"] = table["probability"].astype("float32")
    c3 = ["week_start", "cell_lat", "cell_lon", "probability", "baseline_probability"]
    table[c3].to_parquet(args.out / "cells_weekly.parquet", index=False)
    table[c3 + ["observed", "source"]].to_parquet(args.out / "model_eval.parquet", index=False)
    (args.out / "model_metrics.json").write_text(json.dumps(metrics, indent=2))

    cmp = pd.DataFrame({"model": metrics["model"], "baseline": metrics["baseline"]}).T
    print(cmp[["positive_rate", "brier", "average_precision", "roc_auc"]].round(4).to_string())
    print(f"Model beats baseline on {args.valid_until + 1}-{args.test_until}: {'YES' if beats else 'NO'}")
    print("Top features:", ", ".join(list(metrics["feature_importance_gain"])[:6]))
    print(f"Wrote {len(table):,} rows to {args.out / 'cells_weekly.parquet'}")


if __name__ == "__main__":
    main()
