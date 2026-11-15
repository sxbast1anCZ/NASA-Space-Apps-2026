# Next-day outlook: technical handoff

For the person who takes over the next-day model. It says what exists, how it was built, how to run
it again, what to watch for and what to do next. Written on 2026-11-15, on `main` at `09dcaee`.

Results and their limits are in `docs/findings/09-daily-model.md`; the plan the work followed is
`docs/modeling-plan.md`, section 0. This file does not repeat their tables in full.

## 1. In one paragraph

The model says, for every 0.25° cell of Chile and Argentina, how likely it is that the satellite sees
at least one hotspot tomorrow. It is one LightGBM per country, trained on what the satellite saw up
to today and on the history of each cell. It has no weather. On three years it never saw (2023-2025)
it catches 78% (Argentina) and 79% (Chile) of the fire cell-days while flagging about 12% of the
cells, and it beats three simple baselines. It is **frozen**: nothing below needs to be run again to
show the app.

## 2. What is where

| Script | What it does | Reads | Writes (under `NASA_Data_Sources/processed/`) |
|---|---|---|---|
| `scripts/daily_panel.py` | Builds the table of cells and days: target, features, splits, baselines | `harmonized/hotspots_kept.parquet`, `quality/outage_days.csv` | `daily/panel.parquet`, `daily/panel_summary.json`, and `risk/cells_daily.parquet` **with the baseline** |
| `scripts/daily_train.py` | Trains two runs per country, picks one, scores the test years, replaces the app file | `daily/panel.parquet` | `daily/predictions.parquet`, `daily/model_<country>.txt`, `risk/cells_daily.parquet`, `risk/daily_model.json`, and the metrics below |
| `scripts/daily_eval.py` | Thresholds, confusion matrices, scores and breakdowns. `daily_train.py` calls it; it also runs alone | panel, predictions | `risk/daily_metrics.json`, `risk/daily_metrics.md` |
| `scripts/daily_explain.py` | Reasons of each alert, from SHAP values | panel, `daily/model_<country>.txt`, `risk/daily_model.json`, `risk/cells_daily.parquet` | `risk/cells_daily_reasons.parquet` |
| `scripts/daily_wind.py` | Wind of the live day for the cells in alert (Open-Meteo, needs network) | `risk/cells_daily.parquet` | `risk/wind_live.parquet` |
| `scripts/fire_zones.py` | Groups the hotspots of each day into fires; for each one, the chance it is detected again the next day and the zones (50, 80, 90%) where its next hotspots fall. Not a model: a table fitted on 2013-2022 (`docs/findings/10-fire-zones.md`) | `harmonized/hotspots_kept.parquet`, `quality/outage_days.csv` | `risk/fire_zones.parquet`, `risk/fire_zone_points.parquet`, `risk/fire_zones.json`, `risk/fire_zones.md` |
| `backend/main.py`, `frontend/src/` | The "Next-day outlook" section of the web app, with the area in alert and the fire zones | the files in `risk/` | |

Tests: `tests/test_daily_panel.py`, `test_daily_train.py`, `test_daily_eval.py`, `test_daily_explain.py`,
`test_daily_wind.py`, and the daily part of `test_api.py`. `pytest` runs 127 tests in about 10 seconds;
none needs the real data or the network.

The data files are not in git. On 2026-11-15 the full set exists only on Sebastián's machine:

| File | Size | Needed by |
|---|---|---|
| `daily/panel.parquet` | 161 MB | training, explanations |
| `daily/predictions.parquet` | 76 MB | evaluation |
| `daily/model_argentina.txt`, `model_chile.txt` | 1.9 MB, 0.6 MB | explanations, scoring a new day |
| `risk/cells_daily.parquet` | 36 MB | **the app** |
| `risk/cells_daily_reasons.parquet` | 12 MB | **the app** |
| `risk/wind_live.parquet` | 17 KB | **the app** |
| `risk/daily_model.json`, `daily_metrics.json`, `daily_metrics.md`, `daily_roc.json`, `daily_roc.png` | small | reports |

## 3. The data

**Source.** `harmonized/hotspots_kept.parquet`: 7,000,520 hotspots that pass the quality filter of
EDA block 1 (no low confidence, no static heat sources, no volcanoes or offshore, no Easter Island or
Malvinas). It is step 7 of `docs/eda-runbook.md`.

**Target.** `fire` = 1 if the cell has at least one hotspot of the target satellite on the predicted
`burn_date`. A hotspot is a thermal detection, not an ignition.

| Rule | Value | Why |
|---|---|---|
| Day | `burn_date`: 06:00 to 06:00 local solar time | An afternoon and the night after it are one day |
| Satellite | Suomi-NPP until 2026-10-31, NOAA-20 from 2026-11-01. Never both | Adding satellites changes the count of detections, not the fire |
| Cell | `floor(coordinate / 0.25) * 0.25`, named by its south-west corner | The grid of the harmonized dataset |
| Country and region of a cell | Those of most of its hotspots | Border cells |
| Cells scored in year Y | Cells with a detection before Y | Otherwise the table contains cells because they burn later |
| Outage days of the satellite | No row predicts them; a lag that falls on one is missing, not 0 | Not observed is not "no fire" |

**The panel.** One row per cell and predicted day.

| | Rows |
|---|---|
| With a target, predicted days 2014-2025 | 20,068,773 |
| Live day (2026-11-13), no target | 4,991 (4,046 Argentina, 945 Chile) |
| Fire cell-days 2013-2025 | 597,937 (2.56% of the cell-days) |

Columns: `burn_date`, `cell_lat`, `cell_lon`, `country`, `admin1`, `segment` (country and season
group, for reports), `season_label`, `split`, `fire`, `new_cell`, `p_hist`, `p_persist`, `p_near`,
then 26 features.

| `split` | Predicted days | Argentina | Chile | Use |
|---|---|---|---|---|
| `train` | 2014-2020 | 9,188,991 | 2,076,356 | Fit |
| `tune` | 2021-2022 | 2,787,618 | 649,912 | Early stopping, threshold, choice of run |
| `test` | 2023-2025 | 4,293,722 | 1,003,903 | One final score |
| `gap` | First 7 days of 2021 and of 2023 | | | In no split, so that one fire is not on both sides. The 2023 ones are shown in the app |
| `live` | The day after the last complete day | 4,046 | 945 | The current outlook; `fire` is empty |

**Features.** Every one reads days up to D only, where D is the day before the predicted day. A test
rewrites the future and checks that no feature changes.

| Feature | Meaning |
|---|---|
| `lag_fire_d0` ... `lag_fire_d6` | Fire in the cell on D, D-1 ... D-6 |
| `lag_fire_days_7`, `lag_fire_days_30` | Days with fire in the 7 and 30 days ending on D (observed days only) |
| `lag_days_since_fire` | Days from the last fire of the cell to D, capped at 365 |
| `lag_hotspots_d0`, `lag_frp_sum_d0`, `lag_frp_max_d0`, `lag_night_d0` | Hotspots, summed and maximum FRP (MW) on D; 1 if a night pass saw fire |
| `nbr_fire_d0`, `nbr_hotspots_d0` | Of the 8 neighbours: how many had fire on D, and their hotspots |
| `nbr_ring2_fire_d0` | Of the 16 cells of the next ring, how many had fire on D |
| `nbr_fire_days_7` | Fire-days of the 8 neighbours in the 7 days ending on D |
| `hist_doy_rate` | Rate of fire of the cell for that day of the year, 7 days each side, every earlier year, shrunk towards the cell's own rate with 15 pseudo-days |
| `hist_cell_rate` | Overall rate of fire of the cell in earlier years |
| `cal_dow` | Day of the week of the predicted day |
| `cal_month`, `cal_doy_sin`, `cal_doy_cos` | Calendar. Left out by default |
| `geo_lat`, `geo_lon` | South-west corner of the cell |

**Baselines**, stored in the panel and scored like a model:

| Column | Rule |
|---|---|
| `p_hist` | `hist_doy_rate` |
| `p_persist` | Fire in the cell on D |
| `p_near` | Fire on D in the cell or one of its 8 neighbours. `new_cell` is its opposite |

## 4. Techniques

**Model.** LightGBM, binary objective, one model per country. Settings taken from the weekly model
(`PARAMS` in `scripts/risk_model.py`) and not tuned:

| Setting | Value |
|---|---|
| `learning_rate` | 0.05 |
| `num_leaves` | 31 |
| `min_data_in_leaf` | 200 |
| `feature_fraction`, `bagging_fraction`, `bagging_freq` | 0.8, 0.8, 1 |
| `lambda_l2` | 1.0 |
| `seed` | 42 |
| Rounds | Up to 2,000, early stopping after 50 rounds without a better average precision on `tune` |
| Class weights | None: the probabilities stay close to rates, and the threshold does the work for recall |

**Two runs per country.** `lgbm` (23 features, no calendar) and `lgbm_calendar` (26 features).

| | Run kept | Rounds | Threshold | Cells flagged on tune |
|---|---|---|---|---|
| Argentina | `lgbm` | 523 (`lgbm_calendar`: 77) | 0.0463 | 14.5% (14.6%) |
| Chile | `lgbm_calendar` | 157 (`lgbm`: 254) | 0.0242 | 12.4% (12.8%) |

The two runs differ by 0.001 of ROC AUC. Do not read the choice as "calendar helps in Chile".

**Threshold: false negatives first.** `daily_eval.pick_threshold` takes the highest threshold that
catches at least 80% of the fire cell-days of `tune`. It is applied unchanged to `test` and to the
live day. `--min-recall` changes the 80%.

**Choice of the run.** The one that flags fewer cells on `tune` at that recall.

**Does the model go to the app?** Only if, on `tune`, it beats both baselines:

- against `p_hist`: fewer cells flagged at the same recall;
- against `p_near`: more recall with at most the alerts of the rule.
  `daily_eval.threshold_within_budget` enforces "at most": scores tied at the cut are left out
  together, so the model never gets more alerts than the rule and labels play no part.

Otherwise `risk/cells_daily.parquet` carries the baseline (`probability` = `p_hist`, `alert` = `p_near`).
`risk/daily_model.json` records which one was used and the numbers of the check.

**Scoring.** The test years are scored by the model fitted on `train`, the one the threshold was
chosen for. Only for the live day the kept run is fitted again on every row with a target, with the
same number of rounds, and saved as `daily/model_<country>.txt`.

**Scores reported.** Confusion matrix, recall, false negative rate, precision, F2, PR-AUC (average
precision), ROC AUC, false alarm rate, alerts per day, recall in the top 5% and 10% of cell-days. By
country, and for the test years by season group, year, month, region and `new_cell`. Accuracy is not
reported: 97% of cell-days have no fire.

**Reasons (SHAP).** `daily_explain.py` uses TreeSHAP as built into LightGBM
(`booster.predict(..., pred_contrib=True)`); the `shap` package is not needed. For each alert the
contributions are added up into six groups (recent fire in the cell, strength of today's fire, fire
nearby, history of the place, calendar, place). The groups that push the score up become one sentence
each, strongest first, with the values of that cell, plus their share of the push. Contributions are
in log-odds and add up to the raw score.

**Spread rings.** Not a model. Measured once on Suomi-NPP 2013-2025: of the hotspots of day D+1, 38%
lie within 5 km of a hotspot of day D, 50% within 10 km, 69% within 25 km, 82% within 50 km. The app
shades those distances around the hotspots of the day before (`RINGS` in `backend/main.py`).

**Wind.** `daily_wind.py` asks the Open-Meteo forecast API for the daily dominant wind direction,
maximum speed and gusts, minimum humidity and maximum temperature at the centre of each cell in alert
on the live day. It is shown as context. The model does not use it and nothing checks that fire
moves downwind.

## 5. Results in short

Test years 2023-2025, at the alert threshold:

| | Recall | False negative rate | Precision | PR-AUC | ROC AUC | Alerts per day |
|---|---|---|---|---|---|---|
| Argentina, model | 78.0% | 22.0% | 15.9% | 0.359 | 0.921 | 489 |
| Argentina, `p_near` | 64.0% | 36.0% | 12.9% | 0.092 | 0.765 | 495 |
| Chile, model | 79.1% | 20.9% | 8.8% | 0.269 | 0.925 | 109 |
| Chile, `p_near` | 48.7% | 51.3% | 8.8% | 0.049 | 0.710 | 67 |

- Share of the gain: in Argentina `lag_fire_days_30` 30%, `lag_days_since_fire` 25%, `lag_fire_days_7`
  12%; in Chile `hist_doy_rate` 34%, `lag_days_since_fire` 18%, `lag_frp_sum_d0` 11%.
- Nine of ten misses are in cells with no fire in the cell or its neighbours the day before
  (recall there: 47% in Argentina, 62% in Chile; 95 to 97% elsewhere).

## 6. How to run it again

Before: the data of `docs/eda-runbook.md` up to step 7 (`hotspots_kept.parquet`) and step 6
(`quality/outage_days.csv`). Then, from the repository root:

```bash
python scripts/daily_panel.py      # panel, and the app file with the baseline
python scripts/daily_train.py      # models, metrics, and the app file with the model
python scripts/daily_explain.py    # reasons of the alerts
python scripts/daily_wind.py       # wind of the live day (network)
python scripts/fire_zones.py       # fires of each day and their zones (independent of the four above)
```

Order matters: `daily_panel.py` writes the app file with the baseline, so the three scripts after it
must run again. `daily_eval.py` can run alone to rebuild the metrics from the panel and the
predictions.

| Step | Time measured | Where |
|---|---|---|
| Panel | 40 seconds | Runpod, 16 vCPU |
| Training and scoring | 8 minutes | Runpod, 16 vCPU |
| Evaluation alone | About a minute (30 seconds on 9 million made-up rows) | Laptop, 10 cores |
| Reasons | 2.5 minutes | Laptop, 10 cores |
| Wind | A few minutes, mostly waiting between requests | Laptop |

**On Runpod, as it was done.** A CPU pod, not a GPU: LightGBM here runs on the CPU.

1. Pod: CPU "General Purpose" (`cpu3g`), 16 vCPU and 64 GB, template `runpod-ubuntu-2404`, port
   `22/tcp`, SSH on. It cost 0.64 USD per hour; the whole run was about 14 minutes.
2. Copy over SSH: the five scripts (`daily_panel.py`, `daily_train.py`, `daily_eval.py`,
   `risk_model.py`, `risk_baseline.py`), `hotspots_kept.parquet` (145 MB) and `outage_days.csv`.
   **Never `.env` or any key**: nothing in these scripts needs one.
3. `pip install pandas pyarrow numpy lightgbm scikit-learn duckdb`, then the first two commands above
   with `--kept`, `--quality` and `--out` pointing at the copied files.
4. Copy the `daily/` and `risk/` folders back, then delete the pod and check that it is gone.

**Reproducible.** Fitting Chile again on the laptop with the recorded rounds gave the stored
probabilities to within 0.00000003, with no alert changed. `daily_explain.py` relies on this: it
fits the model of the test years again and stops if it does not match the app file.

## 7. Contracts with the app

`risk/cells_daily.parquet`: `burn_date` (a date), `cell_lat`, `cell_lon`, `probability`,
`baseline_probability`, `alert` (0 or 1). Every cell of every predicted day of 2023-2025 and the live
day: 5,337,042 rows, 1,079 days. Days of a satellite outage are absent, and so is everything between
2026-01-01 and the live day.

`risk/cells_daily_reasons.parquet`: the alerts only (645,945 rows), with `reason_1` to `reason_3` and
`share_1` to `share_3`.

`risk/wind_live.parquet`: the alerts of the live day (900 rows), with `wind_from_deg`, `downwind_deg`,
`wind_max_kmh`, `gust_max_kmh`, `rh_min_pct`, `tmax_c`.

`risk/fire_zones.parquet`: one row per fire of day D, keyed by the predicted day `burn_date` = D+1 (and
`seen_date` = D), from 2023 to the live day: `fire_id`, `lat`, `lon` (centre), `country`, `admin1`,
`hotspots`, `frp_sum_mw`, `size_class`, `active` (fire the day before, null if not observed),
`p_continue`, `r50_km`, `r80_km`, `r90_km`, `area50_km2`, `area80_km2`, `area90_km2`, and what happened:
`continued`, `next_hotspots`, `next_in_r80` (null for the live day and when D+1 was an outage day).
`risk/fire_zone_points.parquet`: `burn_date`, `fire_id`, `lat`, `lon` of its hotspots, thinned to 0.002°.

Endpoints, in `backend/main.py`: `/api/meta` (`risk_days`), `/api/risk/daily` (with `area`: km2 of the
cells in alert and probability times cell area, by region), `/api/risk/daily/cell`,
`/api/risk/daily/hotspots`, `/api/risk/daily/zones`. The app starts without the files; the section then
does not appear, and without the zone files the zones are empty.

## 8. Things that will bite

| Trap | What to do |
|---|---|
| `daily_panel.py` overwrites the app file with the baseline | Run `daily_train.py`, `daily_explain.py` and `daily_wind.py` after it |
| Live rows are inside the panel, `split` = `live`, `fire` empty | Filter on `split` before using `fire`. There is no `live.parquet` |
| `daily_train.py` stops if a country has no live rows | Rebuild the panel, or pass `--no-live` and accept an app file without the current day |
| `gap` rows | They are scored for the app and never evaluated. Do not add them to a split |
| `burn_date` in the app file is a date, not a timestamp | Keep it: the panel script and the app agree on it |
| A lag on an outage day is missing | Leave it missing; LightGBM handles it. Do not fill with 0 |
| Features that would leak | `spatial/cell_regimes.parquet` was fitted on 2012-2025, so it has seen the test years. Do not use it unless refitted on years up to 2020. Never use the year as a feature |
| `acq_date`, `year`, `month` of the hotspot table | They are UTC. Use `burn_date` |
| Open-Meteo answers 429 | The free limit is 600 calls a minute and each location counts. The script sends 25 at a time and waits 65 seconds on a 429 |
| Open-Meteo history | 2 weeks of one point is one call and the free limit is 10,000 a day: the history of 1,466 points is about 459,000 calls. Not possible on the free tier |
| The live threshold | It was chosen for the model fitted on 2014-2020 and is applied to the model fitted on every year. That pair was never scored on unseen data |
| Near-real-time data | The live day uses data that FIRMS revises later, and from November 2026 the satellite is NOAA-20 (0.93 to 1.03 of Suomi-NPP per year) |
| ROC AUC of 0.92 | It flatters: almost every cell-day has no fire, and the historical rate alone reaches 0.88 to 0.90. Quote PR-AUC and precision with it |
| The reasons | They say what moved the score, not what causes fire, and they can never mention weather |

## 9. What was not done, in the order worth doing

| Next step | Evidence | Size |
|---|---|---|
| Other satellites as features: detections of NOAA-20, NOAA-21, Terra and Aqua on day D in the cell and its neighbours | Of the fires in "new cells" of 2023-2025, 32% had such a detection the day before; the signal marks 7.5% of new cells, with four times their usual rate of fire. NOAA-20 exists since 2018 and NOAA-21 since 2023, so few training years carry it | New columns in `daily_panel.py`, one retraining |
| Longer memory of the cell: fire in the last 60, 90 and 365 days; the same week of earlier years | None measured | Small |
| Weather up to D-3 from NASA POWER (already downloaded, daily since 2011, no wind direction) | It added 0.008 of average precision to the weekly model; not tested for days | Medium: join 1,466 points to cells |
| Weather of D+1 as a forecast | Needs a paid Open-Meteo plan for the history, or another source. A model trained on observed weather of D+1 gives an optimistic score | Large |
| A higher recall with this model | A threshold change: 90% of fire costs 946 alerts a day in Argentina and 192 in Chile | `--min-recall 0.90` |
| Feature selection, tuning, XGBoost, Random Forest | The misses come from missing information, so expect one or two points | Medium |
| Calibration check and uncertainty intervals | Not done | Small |
| Validate the wind arrows | Compare the move of hotspots from D to D+1 with the wind direction | Medium |

To add features: put the columns in `daily_panel.py` with one of the prefixes `lag_`, `nbr_`, `hist_`,
`geo_`, `wx_`. `daily_train.py` picks them up by prefix, and `daily_explain.py` needs the new prefix or
names in its `GROUPS` and a sentence in `sentence()`.

## 10. Where to read more

| Question | File |
|---|---|
| Full results, limits, why the model is frozen | `docs/findings/09-daily-model.md` |
| The plan, the original four-model brief and what was cut | `docs/modeling-plan.md` |
| What the EDA says about predicting fire | `docs/eda-conclusions-for-modeling.md` |
| How to build the data from zero | `docs/eda-runbook.md` |
| Rules of the repository and open tasks | `docs/agent-handoff.md`, `CONTRIBUTING.md` |
| The weekly outlook (older, different target) | `docs/findings/08-risk-model.md`, `scripts/risk_model.py` |
