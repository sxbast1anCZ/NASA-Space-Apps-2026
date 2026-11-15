# Modelling plan: next-day fire occurrence, four models by country and season

Written on 2026-11-14 from the modelling brief of the team and `docs/eda-conclusions-for-modeling.md`.
It is a plan: no model in it has been trained. Every statement is marked as one of:

- **Observed:** a number computed from the data or taken from the EDA.
- **Hypothesis:** an explanation that was not tested.
- **Recommendation:** a choice proposed here, open to change.

Two people do the work, each with their own files: **Vicente** builds the data and the evaluation
(lane A), **Felipe** selects features and trains the models (lane B). Section 11 has the split.

## 1. Read this first

1. **"Fire" means "at least one VIIRS hotspot in a 0.25° cell on one day".** It is a thermal detection,
   not an ignition and not burned area. A false negative is a cell-day with a hotspot that the model
   did not flag. Some "no fire" labels are fires nobody saw (clouds, small fires), so part of the
   false alarms are not errors and the scores have a ceiling.
2. **The season cut of the brief runs through the fire season of both countries** (section 3). The
   four models are still the design; two comparison experiments say whether the cut costs detections.
3. **The full brief does not fit before the deadline** (Sunday 2026-11-15, 12:00 Chile time): 12
   algorithm-and-segment runs with two importance methods, tuning and four final models. Section 12
   orders the work so that something complete exists at every stage.
4. **Rules that do not change:** `burn_date` as the day, one satellite at a time, the quality filter,
   outage days are "not observed", wording "where fire activity is most likely". Details in
   `docs/eda-conclusions-for-modeling.md`, section 2.

## 2. Problem definition

| Item | Definition | Status |
|---|---|---|
| Target | `fire` = 1 if the cell has at least one hotspot on `burn_date` D+1 | From the EDA |
| Satellite of the target | Suomi-NPP until 2026-10-31, NOAA-20 after. Never both | From the EDA |
| Unit | One 0.25° cell and one day. The cell is named by its south-west corner | From the EDA |
| Horizon | One day: features end on day D, the target is day D+1 | From the EDA |
| Cells in the panel | Cells with at least one detection before the year being scored | From the EDA |
| Positive class | `fire` = 1 | From the brief |
| Alternative targets | 0.1° cells, or "10 or more hotspots" (a large-activity day). Not recommended now: the first multiplies the rows by six, the second has 9% of the positives | Recommendation |

Known when the prediction is made (end of day D), and nothing else may enter a feature:

| Group | Known at the end of D | Not known |
|---|---|---|
| Hotspots | Every detection up to D | Anything on D+1 |
| Weather (NASA POWER) | Up to D-3: the source is three days behind | D-2 to D+1 |
| Weather forecast for D+1 | Not in the project | |
| Static layers | Population, coordinates | |

Occurrence and behaviour are different problems. Occurrence asks "will this cell have a hotspot
tomorrow", for every cell, and has labels (the hotspots). Behaviour asks "how will this fire grow",
only for an active fire, and needs labels the project does not have (section 9).

## 3. What the data say about the starting hypotheses

All numbers in this section are **observed**: Suomi-NPP, kept rows, `burn_date` 2013-2025, 0.25° cells,
597,937 fire cell-days. A cell belongs to the country of most of its hotspots.

Share of each month in the fire cell-days of the country (%):

| | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Chile, fire cell-days | 8.4 | 9.4 | 13.9 | 15.4 | 11.2 | 4.9 | 3.4 | 4.1 | 7.2 | 8.6 | 6.6 | 6.9 |
| Chile, hotspots | 19.3 | 21.6 | 15.5 | 13.3 | 7.8 | 2.7 | 1.4 | 1.6 | 3.0 | 4.0 | 3.9 | 6.0 |
| Argentina, fire cell-days | 5.5 | 5.1 | 5.4 | 4.5 | 3.9 | 5.5 | 10.3 | 20.6 | 17.3 | 10.6 | 6.4 | 5.0 |
| Argentina, hotspots | 8.1 | 6.3 | 4.6 | 3.0 | 2.3 | 3.2 | 8.3 | 21.9 | 19.3 | 11.2 | 6.3 | 5.5 |

| Hypothesis of the brief | Result |
|---|---|
| Chile has more fire in spring and summer | **Partly.** September to February holds 58% of the hotspots but only 47% of the fire cell-days, which is the target. Chile's season is January to May: 78% of the hotspots and 58% of the fire cell-days. Spring (September to November) is low: 11% of the hotspots. The busiest months for the target are March and April |
| Argentina concentrates in August and September | **Yes.** The two months hold 38% of the fire cell-days and 41% of the hotspots. July to October holds 59% of the fire cell-days |
| August and September fall in different season groups | **Yes, and it matters.** The cut on 1 September splits the peak of Argentina in two halves of similar size, one per model |

Regional differences (**observed**; peak month by fire cell-days):

- **Argentina:** August is the peak in almost every large province (Santa Fe, Formosa, Corrientes,
  Chaco, Santiago del Estero, Buenos Aires, Entre Ríos, Misiones, Tucumán, Mendoza, Córdoba, La Pampa).
  Salta, Río Negro and Catamarca peak in September. Neuquén peaks in March, with 9% in August.
- **Chile:** La Araucanía peaks in March, Bío-Bío and Ñuble in April, Maule in May, O'Higgins in
  September, the Metropolitan region in December (74% of its fire cell-days from September to February).

**Hypothesis:** the Chilean activity from March to May is mostly agricultural burning. It has fewer
hotspots per fire cell-day than summer (3.6 against 5.6). This was not checked against any record of
burn permits.

Size of the four segments (**observed**; panel rows before removing outage days and cells not yet
eligible):

| Model | Months | Cells | Panel rows | Fire cell-days | Base rate | Train (to 2020) | Tune (2021-22) | Test (2023-25) |
|---|---|---|---|---|---|---|---|---|
| CL-PV | Sep-Feb | 966 | 2,275,896 | 29,930 | 1.32% | 18,303 | 4,768 | 6,859 |
| CL-OI | Mar-Aug | 966 | 2,310,672 | 33,563 | 1.45% | 22,537 | 4,805 | 6,222 |
| AR-PV | Sep-Feb | 4,036 | 9,508,816 | 265,854 | 2.80% | 158,929 | 50,850 | 56,075 |
| AR-OI | Mar-Aug | 4,036 | 9,654,112 | 268,590 | 2.78% | 176,990 | 39,964 | 51,635 |

The smallest test year has 1,862 fire cell-days (CL-OI, 2024). Every segment has enough positives to
train and to evaluate. The two segments of a country have almost the same base rate: the cut does not
separate a high season from a low one.

**Recommendation.** Keep the four models of the brief as the main design and run two comparisons on
the same rows:

| Experiment | What it is | Question it answers |
|---|---|---|
| E1, annual | One model per country, all months | Does splitting by season reduce false negatives at all? |
| E2, seasons from the data | Chile: January-May and June-December. Argentina: July-October and November-June | Does a cut that keeps each fire season whole do better than the cut of the brief? |

E2 changes one table (month to segment) and nothing else. If E1 or E2 wins, it is a team decision
(section 13), because the project rule is to ship the best scoring option.

**Seasons that cross a year.** A spring-summer season runs from September to February and is named by
the year it starts: "PV 2023/24" is September 2023 to February 2024 (January and February belong to
the season of the year before). Autumn-winter stays inside one calendar year. The label is used for
reports only; the split is by calendar year (section 5).

## 4. Data preparation

### 4.1 The panel (contract between the two lanes)

One file, `NASA_Data_Sources/processed/daily/panel.parquet`. One row per cell and predicted day.
Lane A writes it, lane B only reads it.

| Column | Meaning |
|---|---|
| `burn_date` | The day predicted (D+1) |
| `cell_lat`, `cell_lon` | South-west corner of the cell |
| `country`, `admin1` | Country and region of most hotspots of the cell |
| `segment` | `CL-PV`, `CL-OI`, `AR-PV`, `AR-OI`, from the country and the month of `burn_date` |
| `season_label` | For example `PV 2023/24`, `OI 2024` |
| `split` | `train`, `tune`, `test` (section 5) |
| `fire` | Target, 0 or 1 |
| `new_cell` | 1 if neither the cell nor its 8 neighbours had fire on D |
| `p_hist`, `p_persist`, `p_near` | The three baselines (section 4.3) |
| feature columns | Prefixes `lag_`, `nbr_`, `hist_`, `cal_`, `geo_`, `wx_` (section 4.2) |

Rows left out: predicted days on which the target satellite was out (`quality/outage_days.csv`), and
cells with no detection before that year. First predicted year: 2014, so that the history features
have at least two earlier years (**recommendation**; 2012 and 2013 are history only).

### 4.2 Features

All of them use days up to D only. Names are proposals; the prefix is the contract.

| Group | Features | Source | Notes |
|---|---|---|---|
| Persistence `lag_` | Fire on D, D-1 ... D-6; fire-days in the last 7 and 30 days; days since the last fire (capped at 365); hotspots on D; summed and maximum FRP on D; night-pass detection on D | `hotspots_kept.parquet` | A lag that falls on an outage day is missing, not 0 |
| Spread `nbr_` | Neighbours (of 8) with fire on D; their hotspots on D; cells with fire in the next ring (of 16); neighbour fire-days in the last 7 days | same | Reuse `neighbour_ids` of `scripts/risk_model.py` |
| History `hist_` | Rate of fire of the cell for that day of the year, 7 days each side, earlier years only, shrunk towards the rate of the cell; overall rate of the cell in earlier years | same | Same idea as `baseline_for_year` of `scripts/risk_baseline.py` |
| Calendar `cal_` | Day of the week, sine and cosine of the day of the year, month | `burn_date` | Fire-days fall 28 to 37% on Sundays (EDA) |
| Place `geo_` | Latitude, longitude, people per km² | `population/cells.parquet` | Population needs the WorldPop step of the runbook. If the file is missing, run without it and say so |
| Weather `wx_` | Rain in 30 and 90 days, days since rain, mean maximum temperature in 3 and 14 days, humidity and vapour pressure deficit in 14 days, mean and maximum wind in 7 days, soil wetness | `weather/power_daily/` (1,466 points, 0.5°) | **Every window ends on D-3**, as it will in operation. Reuse `days_since_rain` of `scripts/risk_weather.py` |

Not used, with the reason:

- **Fire regime of the cell** (`spatial/cell_regimes.parquet`): it was fitted on 2012-2025, so it has
  seen the test years. Use it only if it is refitted on years up to 2020.
- **`admin1` as a feature:** many categories and it repeats what latitude and longitude say. It stays
  in the panel for the reports.
- **Vegetation, topography, fuel, wind direction, forecasts:** not in the project (section 10).

Data cleaning, as the brief asks:

| Topic | Treatment |
|---|---|
| Missing values | Left as missing. LightGBM, XGBoost and Random Forest (scikit-learn 1.4 or later) handle them. No imputation, so nothing to fit |
| Duplicates | Near-duplicate hotspots are kept by the quality filter. The target is 0 or 1 per cell-day, so they do not change it; they add to `hotspots on D` (0.3 to 0.4% of rows) |
| Outliers | FRP and hotspot counts have long tails. Trees depend only on the order of the values: no cap, no transform |
| Units | As in `docs/data-contracts.md`: FRP in MW, rain in mm, temperature in °C, wind in m/s |
| Categorical | None goes into the models, except the day of the week as an integer |

### 4.3 Baselines

Computed by lane A and stored in the panel. Every model must be compared with the three.

| Baseline | Rule | Known result (EDA) |
|---|---|---|
| `p_hist` | Historical rate of the cell for that day of the year, earlier years only | Not computed for days yet |
| `p_persist` | Fire in the cell on D | Recall 33%, precision 33% |
| `p_near` | Fire on D in the cell or one of its 8 neighbours | Recall 64.7%; precision not computed |

`p_near` matters most for this brief: a rule with no model already catches about two thirds of the
fire cell-days. A model earns its place by catching more at the same number of alerts.

## 5. Splits

| Split | Predicted days | Use |
|---|---|---|
| `train` | 2014 to 2020 | Fit models |
| `tune` | 2021 and 2022 | Early stopping, hyperparameters, feature selection, thresholds, choice of algorithm |
| `test` | 2023 to 2025 | One final evaluation. Nothing is chosen on it |

- **Why calendar years:** the same split as the weekly model, the same rows for the four models and
  for experiments E1 and E2, and it keeps every result comparable.
- **A fire on both sides of a boundary:** 1 January is inside the Chilean summer. Leave out the first
  7 predicted days of 2021 and of 2023 (**recommendation**), so that one fire is not in two splits.
- **Space:** neighbouring cells are not independent, and the model will be used on the same cells in
  later years, so the split is in time, not in space. The dependence is handled in the uncertainty
  (section 8), by resampling whole weeks.
- **Several years:** every score is reported for 2021 and 2022 separately in `tune`, and for 2023, 2024
  and 2025 separately in `test`. An expanding window (train to 2019, score 2020, and so on) is the
  stronger check and costs three more trainings per run: do it only if time allows.
- **Nothing is fitted outside `train`:** baselines and history features of year Y use years before Y.
  There is no imputation and no scaling. Feature selection and thresholds use `tune`.
- **2026 is not used:** from August it is provisional, and the satellite of the target changes in November.

## 6. Feature selection: 12 runs

Four segments times three algorithms. Each run is independent: the same panel rows, its own
importances, its own list of kept variables.

Starting configuration (**recommendation**):

| | LightGBM | XGBoost | Random Forest |
|---|---|---|---|
| Start | The `PARAMS` of `scripts/risk_model.py`; up to 2,000 rounds, early stopping on `tune` | `tree_method=hist`, learning rate 0.05, depth 6, `subsample` 0.8, `colsample_bytree` 0.8, `eval_metric=aucpr`, early stopping | 300 trees, depth 16, at least 100 rows per leaf, `max_features=sqrt`, `max_samples` 1,000,000 per tree |
| To tune | `num_leaves`, `min_data_in_leaf`, `feature_fraction`, `lambda_l2` | `max_depth`, `min_child_weight`, `subsample`, `colsample_bytree`, `reg_lambda` | `max_depth`, `min_samples_leaf`, `max_features` |
| Budget | 15 random settings | 15 random settings | 15 random settings |

Imbalance (1.3 to 2.8% positives): the default is **no reweighting**, so that the probabilities stay
calibrated and the threshold does the work for recall. One alternative per algorithm is compared on
`tune`: a positive weight of the square root of negatives over positives (LightGBM, XGBoost) or
`class_weight="balanced_subsample"` (Random Forest), followed by isotonic calibration on `tune`. Keep
the alternative only if it has fewer false negatives at the same number of alerts.

Importance, for each of the 12 runs:

| Method | How | Role |
|---|---|---|
| Permutation | On `tune`, drop in average precision, 5 repeats, a random sample of up to 500,000 rows, separately for 2021 and 2022 | Decides |
| SHAP | Mean absolute value on 50,000 rows of `tune` (LightGBM and XGBoost; Random Forest on 10,000 rows, or skipped if too slow, and the report says so) | Decides together with permutation |
| Native (gain or impurity) | From the fitted model | Complement only |

Status of each variable, in each run:

| Status | Rule |
|---|---|
| Kept | Permutation importance more than 2 standard deviations above zero in both tune years |
| Unstable | Above zero in one tune year only. Kept, and flagged |
| Discarded | Not above zero in either year **and** mean absolute SHAP below 1% of the top variable. Never because the native importance is zero |
| Correlated group | Variables with a Spearman correlation of 0.9 or more (on `train`) are permuted together. The group is kept or discarded as one; the report names its strongest member |

Before and after: refit with the kept variables. The shorter list is accepted if average precision on
`tune` falls by no more than 0.002 and the false negatives at the chosen threshold rise by no more
than 1%. Otherwise the full list stays.

The final list of a model is the list of the algorithm that wins its segment (section 7). The four
models may end with four different lists. No common list is imposed.

## 7. Training and choice of the four final models

For each segment:

1. Tune each algorithm with its budget on `tune` (section 6), with the variables it kept.
2. Pick the threshold of each algorithm on `tune` (section 8).
3. Choose the algorithm with the fewest alerts on `tune` at the required recall. If two are within
   each other's uncertainty interval, take the higher average precision; if still tied, LightGBM
   (fastest to retrain).
4. Refit the winner on `train` plus `tune` with the chosen settings (number of rounds fixed from step
   1), and score `test` once.

Comparisons, on the same rows and with the same rule for the threshold: the three baselines,
experiment E1 (annual model per country) and experiment E2 (seasons from the data). They are scored
per segment of the brief, so that each of the four models has a direct rival.

If a segment's model does not beat `p_near` and `p_hist` on `tune`, the report says so and the
baseline is what the app shows for that segment.

## 8. Evaluation with false negatives first

**Threshold rule (recommendation).** For each model, on `tune`: the highest threshold whose recall is
at least `R_min`. It is then applied unchanged to `test`. `R_min` is a pending decision; the plan uses
0.80 until the team sets it. Lowering the threshold always catches more fire and always raises more
alerts: recall 1.0 is reached by flagging every cell, so recall is never reported without the number
of alerts.

For each of the 12 runs, the four final models, the baselines and E1 and E2:

| Output | Content |
|---|---|
| Confusion matrix | TN, FP, FN, TP, labelled |
| Scores | Recall, false negative rate (FN / (FN + TP)), precision, F2, PR-AUC (average precision), false alarm rate (FP / (FP + TN)) |
| Cost | Alerts per day (mean number of cells flagged) and share of cells flagged |
| Threshold | Value, and that it came from `tune` at `R_min` |
| Size | Rows and fire cell-days evaluated |
| Fixed budget | Recall when the top 5% and the top 10% of cell-days are flagged (the weekly model reports the top 10%) |

Breakdowns of the false negatives of the four final models:

- per test year, per month and per region (`admin1`);
- **new fire cells** (`new_cell` = 1) against cells with fire nearby the day before. The EDA says this
  is where a model can add something, and the headline hides it;
- by weather: terciles of days since rain and of maximum wind;
- **Argentina, August and September separately**, and the change of model: score the last 14 days of
  August and the first 14 of September with both Argentine models and compare alerts per day and
  recall. The same for Chile around 1 March. If there is a jump, blend the two probabilities over 7
  days each side (**recommendation**, to be tested);
- per country and year, joining the predictions of its two seasonal models.

Calibration: reliability table in ten probability bins, per model, on `test`. Needed only if the app
shows probabilities or risk levels (pending decision). The weekly model reads slightly high (29% said,
26% observed).

Uncertainty: resample whole weeks of the test period with replacement, 200 times, and report the 2.5
and 97.5 percentiles of recall, false alarm rate and average precision. Three test years is a short
record: say it.

What cannot be promised: zero false negatives. Every missed fire that the threshold recovers costs
more alerts, and a share of the misses are fires in cells where nothing showed the day before.

## 9. Fire behaviour: what is feasible

None of this is part of the four models. **Observed** in this project: of the hotspots of day D+1,
38% lie within 5 km of a hotspot of day D, 50% within 10 km, 69% within 25 km and 82% within 50 km
(Suomi-NPP, 2013-2025; large fires weigh more). That ring is the only behaviour-like output the data
support today, and it has no direction.

| Objective | Labels and data needed | In the project | Verdict |
|---|---|---|---|
| Burned area | Fire perimeters or a burned-area product (for example MODIS MCD64A1, national fire statistics) | No. Hotspots times pixel size is not burned area | Not feasible now |
| Direction and speed of spread | The fire front at successive times; wind speed and direction near the fire, as a forecast; fuel and slope | Partly: hotspot positions at each pass (up to 6 passes a day since 2023). Wind direction is not downloaded, and the weather grid is 50 km | A rough speed (km per day) between passes is possible once hotspots are grouped into events. Not a forecast |
| Perimeter | Mapped perimeters to train and to score | No | Not feasible now |
| Zones potentially affected | The same, or an empirical ring | The ring above | Feasible now as a ring; a ring stretched downwind needs wind direction |

For each, if the data are added:

- **When:** only during an active fire, for the next 12 to 24 hours. Before a fire exists there is
  nothing to spread; that case is the occurrence model.
- **Models:** tree models predict one number per row and do not carry shape or direction. Area fits a
  regression on the logarithm with quantiles. Spread and perimeter need a spatial model or a physical
  simulator fed with fuel, terrain and wind.
- **Scores:** area, error on the logarithm and coverage of the interval; perimeter, overlap between
  the predicted and the mapped area; direction, angle error; speed, error in km per hour.
- **Uncertainty:** intervals or several simulated runs, never one line on a map.
- **First step:** group hotspots into events (task T8 of `docs/agent-handoff.md`). Nothing here works
  without it.

## 10. Operation and extra data

**Choosing the model.** A table from (country of the cell, month of the predicted day) to the model.
The switch is on 1 March and 1 September, with the check of section 8.

**Each day:** when the FIRMS near-real-time data of day D are in, build the features, score every
cell with the model of its segment, and write `NASA_Data_Sources/processed/risk/cells_daily.parquet`
(`burn_date`, `cell_lat`, `cell_lon`, `probability`, `baseline_probability`, plus `alert` and `segment`).

Known gaps between training and operation:

- Models are trained on final data and used on near-real-time data, which have no `fire_type`, so the
  volcano and offshore filter does not apply to them. The static mask does.
- From November 2026 the target satellite is NOAA-20 (0.93 to 1.03 of Suomi-NPP per year).
- Weather is three days behind. The features already assume it.

**Monitoring:** each week, recall and alerts per day of the last 28 days, next to the three baselines.
Retrain once a year, after the data of the season become final.

Extra data, by priority (**recommendation**; none was checked for coverage or access):

| Data | Use | Priority | Resolution needed |
|---|---|---|---|
| Weather forecast for D+1 (wind, temperature, humidity) | The only weather that can describe tomorrow | High | 10 to 25 km, daily or 3-hourly |
| Wind direction | Direction of the ring around active fires | High | Same |
| Land cover and vegetation state | Separates forest, grassland and crops; green or dry | High | 250 m to 1 km, every 16 days |
| Agricultural burn permits and calendars | Explains the March to May activity in Chile | Medium | Region, daily |
| Slope and aspect | Spread, and where fire is unlikely | Medium | 30 to 90 m, static |
| Drought index, soil moisture | Slow fuel dryness | Medium | 5 to 25 km, weekly |
| Roads and settlements | Human ignitions, beyond population | Medium | Static |
| Historical perimeters and ignition points | Labels for behaviour (section 9) | High for behaviour, low for occurrence | Event level |
| Suppression actions | Explains fires that stop | Low | Event level |

## 11. Work split

One lane per person, no shared files. Each task is one pull request.

### Lane A, Vicente: data, baselines and evaluation

| Task | What | Files | Done when |
|---|---|---|---|
| A1 | Daily panel: target, segments, splits, `new_cell`, persistence, spread, history and calendar features | `scripts/daily_panel.py`, `tests/test_daily_panel.py` | The panel exists; its fire cell-days per segment match the table of section 3 after outage days are removed; a test proves no feature reads day D+1 or later |
| A2 | The three baselines in the panel | same | `p_persist` gives recall and precision near 33%, `p_near` recall near 64.7% |
| A3 | Evaluation module: threshold rule, confusion matrix, scores, breakdowns, weekly bootstrap | `scripts/daily_eval.py`, `tests/test_daily_eval.py` | Tests with hand-made cases pass; the baselines have their full table per segment and year |
| A4 | Weather and population features, with the D-3 rule | `scripts/daily_panel.py` | Panel updated; a test proves no weather window reaches past D-3 |
| A5 | Findings: the hypothesis check of section 3 made reproducible, segment sizes, baseline results | `docs/findings/09a-daily-panel.md` | Merged |

A1 goes first and alone: lane B needs it. A4 comes after A3, so that lane B can start on a panel
without weather and rerun when it arrives.

### Lane B, Felipe: selection, training and final models

| Task | What | Files | Done when |
|---|---|---|---|
| B1 | Environment: add `xgboost` and `shap` at the end of `requirements.txt`; a pod or machine with 8 or more cores and 32 GB | `requirements.txt` | The three libraries train on a small sample |
| B2 | One training function for the three algorithms, per segment, with early stopping; LightGBM on the four segments first | `scripts/daily_train.py`, `tests/test_daily_train.py` | Four LightGBM models scored on `tune` with lane A's module |
| B3 | Experiments E1 and E2 | same | Both scored per segment of the brief |
| B4 | The 12 selection runs: permutation, SHAP, statuses, before and after | `scripts/daily_select.py` | One table per segment, as in section 14 |
| B5 | Tuning, choice of the four final models, one run on `test` | `scripts/daily_train.py` | Metrics file and `risk/cells_daily.parquet` written |
| B6 | Findings: the 12 runs, the four models, E1 and E2, behaviour and operation | `docs/findings/09b-daily-models.md` | Merged |

While A1 is being built, Felipe does B1 and writes B2 against the contract of section 4.1, with a
small made-up panel in the tests.

What each lane hands to the other:

| From | To | What | When |
|---|---|---|---|
| A | B | `panel.parquet` with the columns of section 4.1 | After A1; again after A4 |
| A | B | `daily_eval.pick_threshold(y, p, min_recall)`, `daily_eval.scores(y, p, threshold)`, `daily_eval.breakdown(df, p_col, threshold, by)`, `daily_eval.bootstrap(df, p_col, threshold)` | After A3 |
| B | A | Predictions per row (`burn_date`, `cell_lat`, `cell_lon`, `model`, `probability`) in `daily/predictions.parquet` | After B2 and B5 |

Connecting `risk/cells_daily.parquet` to the web app is a separate task (backend and frontend) and is
not in either lane.

## 12. Order of work

The deadline is close. Each stage ends with something that can be shown.

| Stage | Content | Result |
|---|---|---|
| 1, must | A1, A2, A3, B1, B2 | Four LightGBM models against three baselines, with confusion matrices and thresholds |
| 2, should | B3, then B4 with permutation importance for XGBoost and Random Forest | The 12 runs and the answer to "does the season cut help" |
| 3, if time | A4 (weather), SHAP, tuning, bootstrap, the blend at the change of model | The full brief |

Rough cost of computing, **not measured**: the panel has about 22 million rows; one boosted model on
the largest segment (about 5 million training rows) should take minutes on 8 cores; Random Forest is
the slow one, which is why it is capped at one million rows per tree. A GPU does not help.

## 13. Decisions that are still open

| Decision | Who | Default used meanwhile |
|---|---|---|
| Minimum recall `R_min` | Team | 0.80 |
| How many alerts per day a user can look at | Team | None: reported, not limited |
| Cost of a missed fire against a false alarm | Team | None: F2 counts recall as twice as important as precision |
| Show probabilities, levels or only alerts | Team | Alerts and the probability, with calibration checked |
| If E1 or E2 beats the four models of the brief | Team | Report both; ship the best on `tune` |
| A source of weather forecasts | Team | None: no weather for D+1 |
| Where to train | Felipe | His machine or a Runpod CPU pod; never copy `.env` or keys |

## 14. Tables to fill

Empty on purpose: no run has been made.

Per run (12 runs, then the four final models, the baselines, E1 and E2):

| Segment | Model | Split | Rows | Fire | Threshold | TN | FP | FN | TP | Recall | FN rate | Precision | F2 | PR-AUC | False alarm rate | Alerts per day |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Per segment, importance and status:

| Variable | LightGBM permutation (2021, 2022) | LightGBM SHAP | LightGBM status | XGBoost permutation | XGBoost SHAP | XGBoost status | Random Forest permutation | Random Forest SHAP | Random Forest status | Reason if discarded |
|---|---|---|---|---|---|---|---|---|---|---|

Per segment, summary:

| Segment | Discarded by all three | Discarded by one or two (which) | Unstable | Before selection: PR-AUC, FN | After selection: PR-AUC, FN | List accepted |
|---|---|---|---|---|---|---|

Final models:

| Segment | Algorithm | Variables | Settings | Threshold | Recall on test (interval) | Alerts per day | Beats `p_near` | Beats E1 | Beats E2 |
|---|---|---|---|---|---|---|---|---|---|
