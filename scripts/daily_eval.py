"""Evaluation of the next-day models, with false negatives first (docs/modeling-plan.md, card 2).

"Fire" is the positive class: a cell and day with at least one hotspot. A false negative is a fire
cell-day that was not flagged. Recall alone means nothing here (flagging every cell gives 1.0), so
every result carries the number of alerts next to it.

Inputs (NASA_Data_Sources/processed/):
    daily/panel.parquet         from scripts/daily_panel.py: burn_date, cell_lat, cell_lon, country,
                                admin1, segment, split, fire, new_cell, p_hist, p_persist, p_near
    daily/predictions.parquet   optional, from scripts/daily_train.py: burn_date, cell_lat, cell_lon,
                                model, probability

Outputs (NASA_Data_Sources/processed/risk/):
    daily_metrics.json          one record per country, score, operating point, split and group
                                (a threshold of null with no alerts means that nothing fitted the budget)
    daily_metrics.md            the same, as tables to read

Thresholds are chosen on the `tune` rows of each country and applied unchanged to `test`.

Run:  python scripts/daily_eval.py [--min-recall 0.80]
"""

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "NASA_Data_Sources" / "processed"
KEYS = ["burn_date", "cell_lat", "cell_lon"]
RULES = ("p_persist", "p_near")     # yes/no rules: evaluated as they are, with no threshold to choose
BASELINES = ("p_hist",) + RULES
BREAKDOWNS = ("segment", "year", "month", "new_cell", "admin1")   # of the test rows
NAN = float("nan")


def _arrays(y, p) -> tuple[np.ndarray, np.ndarray]:
    """Labels as booleans; a missing score ranks below every real one, so it is never flagged first."""
    return np.asarray(y).astype(bool), np.nan_to_num(np.asarray(p, dtype="float64"), nan=-1.0)


def _ratio(a: float, b: float) -> float:
    return a / b if b else NAN


# ---------------------------------------------------------------- thresholds

def pick_threshold(y, p, min_recall: float) -> float:
    """The highest threshold t such that flagging `p >= t` catches at least `min_recall` of the fires."""
    if not 0 < min_recall <= 1:
        raise ValueError("min_recall must be above 0 and at most 1")
    y, p = _arrays(y, p)
    positives = np.sort(p[y])[::-1]
    if not len(positives):
        raise ValueError("no fire rows: a threshold cannot be chosen")
    needed = max(math.ceil(min_recall * len(positives) - 1e-9), 1)   # 0.8 * 15 is 12.000000000000002
    return float(positives[needed - 1])


def threshold_within_budget(p, max_alerts: int) -> float:
    """The lowest threshold that flags at most `max_alerts` rows.

    Scores tied at the cut are left out together: the budget is never exceeded and the labels play no
    part in who is flagged. Returns infinity (nothing flagged) when no threshold fits the budget.
    """
    _, p = _arrays([], p)
    if max_alerts <= 0 or not len(p):
        return float("inf")
    ranked = np.sort(p)[::-1]
    if max_alerts >= len(p):
        return float(ranked[-1])
    cut = ranked[max_alerts - 1]
    if ranked[max_alerts] < cut:              # no tie across the cut: exactly max_alerts rows
        return float(cut)
    above = ranked[ranked > cut]
    return float(above[-1]) if len(above) else float("inf")


# ---------------------------------------------------------------- scores

def scores(y, p, threshold: float, n_days: int | None = None) -> dict:
    """Confusion matrix and the scores of the plan for one set of rows. NaN where a score has no meaning."""
    y, p = _arrays(y, p)
    flag = p >= threshold
    tp, fp = int((flag & y).sum()), int((flag & ~y).sum())
    fn, tn = int((~flag & y).sum()), int((~flag & ~y).sum())

    def recall_top(share: float) -> float:
        return _ratio(float((y & (p >= threshold_within_budget(p, int(share * len(p))))).sum()), tp + fn)

    return {
        "rows": len(y),
        "fire": tp + fn,
        "threshold": float(threshold),
        "tn": tn, "fp": fp, "fn": fn, "tp": tp,
        "recall": _ratio(tp, tp + fn),
        "fn_rate": _ratio(fn, tp + fn),
        "precision": _ratio(tp, tp + fp),
        "f2": _ratio(5 * tp, 5 * tp + 4 * fn + fp) if tp + fn else NAN,
        "pr_auc": float(average_precision_score(y, p)) if 0 < tp + fn < len(y) else NAN,
        "false_alarm_rate": _ratio(fp, fp + tn),
        "flagged_share": _ratio(tp + fp, len(y)),
        "alerts_per_day": _ratio(tp + fp, n_days) if n_days else NAN,
        "recall_top_5pct": recall_top(0.05),
        "recall_top_10pct": recall_top(0.10),
    }


def breakdown(df: pd.DataFrame, p_col: str, threshold: float, by, y_col: str = "fire") -> pd.DataFrame:
    """`scores` for each group of `by` (one column name or a list). One row per group."""
    by = [by] if isinstance(by, str) else list(by)
    rows = [
        {**dict(zip(by, key if isinstance(key, tuple) else (key,))),
         **scores(g[y_col], g[p_col], threshold, g["burn_date"].nunique())}
        for key, g in df.groupby(by, observed=True)
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- the whole report

def evaluate(df: pd.DataFrame, score_cols, min_recall: float) -> pd.DataFrame:
    """Every score column, per country: threshold from `tune`, scores on `tune` and `test`.

    Operating points: `rule` (a yes/no baseline as it is), `recall` (the threshold that reaches
    `min_recall` on tune) and `alerts of p_near` (the threshold that flags at most as many tune rows as
    the p_near rule, never more, so that a model and the rule are compared at the same cost).
    """
    df = df.assign(year=df["burn_date"].dt.year, month=df["burn_date"].dt.month)
    records = []
    for country, g in df.groupby("country", observed=True):
        tune, test = g[g["split"] == "tune"], g[g["split"] == "test"]
        if tune.empty or not tune["fire"].any():
            raise SystemExit(f"{country}: no tune rows with fire, a threshold cannot be chosen")
        near_alerts = int((tune["p_near"] >= 0.5).sum()) if "p_near" in g else None
        for col in score_cols:
            if col in RULES:
                points = {"rule": 0.5}
            else:
                points = {"recall": pick_threshold(tune["fire"], tune[col], min_recall)}
                if near_alerts is not None:
                    points["alerts of p_near"] = threshold_within_budget(tune[col], near_alerts)
            for point, t in points.items():
                head = {"country": country, "score": col, "operating_point": point}
                for split, part in (("tune", tune), ("test", test)):
                    if len(part):
                        records.append({**head, "split": split, "group": "all",
                                        **scores(part["fire"], part[col], t, part["burn_date"].nunique())})
                for by in (b for b in BREAKDOWNS if b in test and len(test)):
                    for row in breakdown(test, col, t, by).to_dict("records"):
                        records.append({**head, "split": "test", "group": f"{by}={row.pop(by)}", **row})
    return pd.DataFrame(records)


def load(panel: Path, predictions: Path | None) -> tuple[pd.DataFrame, list[str]]:
    """Tune and test rows of the panel, with one column per model of the predictions file."""
    import pyarrow.parquet as pq

    wanted = KEYS + ["country", "admin1", "segment", "split", "fire", "new_cell", *BASELINES]
    have = [c for c in wanted if c in pq.read_schema(panel).names]
    missing = {"burn_date", "cell_lat", "cell_lon", "country", "split", "fire"} - set(have)
    if missing:
        raise SystemExit(f"{panel} lacks {sorted(missing)} (docs/modeling-plan.md, section 4.1)")
    df = pd.read_parquet(panel, columns=have, filters=[("split", "in", ["tune", "test"])])
    df["burn_date"] = pd.to_datetime(df["burn_date"])
    score_cols = [c for c in BASELINES if c in df]
    if predictions is not None and predictions.exists():
        pred = pd.read_parquet(predictions)
        pred["burn_date"] = pd.to_datetime(pred["burn_date"])
        wide = pred.pivot(index=KEYS, columns="model", values="probability").reset_index()
        df = df.merge(wide, on=KEYS, how="left")
        score_cols += [c for c in wide.columns if c not in KEYS]
    return df, score_cols


def to_markdown(res: pd.DataFrame, min_recall: float) -> str:
    cols = ["country", "score", "operating_point", "split", "rows", "fire", "threshold", "tn", "fp", "fn",
            "tp", "recall", "fn_rate", "precision", "f2", "pr_auc", "false_alarm_rate", "alerts_per_day"]

    def cell(v) -> str:
        if isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                return "" if math.isnan(v) else "none flagged"
            return f"{v:,.0f}" if v >= 100 else f"{v:.3f}"
        return f"{v:,}" if isinstance(v, int) else str(v)

    def table(part: pd.DataFrame, columns: list[str]) -> list[str]:
        lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
        return lines + ["| " + " | ".join(cell(v) for v in row) + " |"
                        for row in part[columns].itertuples(index=False, name=None)]

    out = ["# Next-day outlook: evaluation", "",
           f"Thresholds chosen on tune (2021-2022) for a recall of {min_recall:.2f}, applied to test. "
           "Fire is the positive class.", "", "## All rows", ""]
    out += table(res[res["group"] == "all"], cols)
    for by, title in (("segment", "By season group"), ("new_cell", "New fire cells (1) against the rest (0)"),
                      ("year", "By test year")):
        part = res[res["group"].str.startswith(f"{by}=")]
        if len(part):
            out += ["", f"## {title} (test)", ""] + table(part, ["group"] + [c for c in cols if c != "split"])
    return "\n".join(out) + "\n"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--panel", type=Path, default=DATA / "daily" / "panel.parquet")
    ap.add_argument("--predictions", type=Path, default=DATA / "daily" / "predictions.parquet")
    ap.add_argument("--out", type=Path, default=DATA / "risk")
    ap.add_argument("--min-recall", type=float, default=0.80)
    args = ap.parse_args(argv)
    if not args.panel.exists():
        raise SystemExit(f"{args.panel} not found. Build it with scripts/daily_panel.py")

    df, score_cols = load(args.panel, args.predictions)
    res = evaluate(df, score_cols, args.min_recall)
    args.out.mkdir(parents=True, exist_ok=True)
    payload = f'{{"min_recall": {args.min_recall}, "results": {res.to_json(orient="records")}}}\n'
    (args.out / "daily_metrics.json").write_text(payload)   # to_json writes NaN as null
    (args.out / "daily_metrics.md").write_text(to_markdown(res, args.min_recall))
    head = res[(res["group"] == "all") & (res["split"] == "test")]
    print(head[["country", "score", "operating_point", "recall", "fn", "alerts_per_day", "pr_auc"]]
          .to_string(index=False))
    print(f"Written: {args.out / 'daily_metrics.json'} and daily_metrics.md")


if __name__ == "__main__":
    main()
