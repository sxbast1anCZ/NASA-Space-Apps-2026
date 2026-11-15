# 9. Next-day outlook: the model that ships

Scripts: `scripts/daily_panel.py`, `scripts/daily_train.py`, `scripts/daily_eval.py`,
`scripts/daily_explain.py`, `scripts/daily_wind.py`. Plan: `docs/modeling-plan.md`, section 0.
Trained on 2026-11-15 on the data downloaded on 2026-11-14. Every number below was computed from
those files; statements marked **(inference)** are interpretation.

## Decisions

| Topic | Decision | Why |
|---|---|---|
| Model | **Kept as it is.** One LightGBM per country (Chile, Argentina), all months | It beats the three baselines on years it never saw. There is no time before the deadline, and no complementary data, to improve it further (section 5) |
| Alert threshold | The one that catches 80% of fire on 2021-2022: 0.046 (Argentina), 0.024 (Chile) | False negatives first. A higher recall is a threshold change, with its cost in alerts (section 3) |
| Calendar features | In for Chile, out for Argentina | The two runs are equal within 0.001 of ROC AUC; the script keeps the one with fewer alerts on 2021-2022 |
| Reasons | Each alert carries up to three sentences from the model's SHAP values | So that an alert says why, in words a person can check |
| Spread | Rings of 5, 10 and 25 km around the hotspots of the last day, from past data. Wind direction is shown as context | No data to forecast a perimeter (section 7) |
| Wording | "Where fire activity is most likely tomorrow". Never "a fire will start here" | A hotspot is a detection, and the model ranks places |

## 1. What was built

| Part | Content |
|---|---|
| Target | At least one VIIRS hotspot in a 0.25° cell on `burn_date` D+1 (Suomi-NPP until 2026-10-31, NOAA-20 after) |
| Rows | 20,068,773 cell-days with a target, predicted days 2014 to 2025; 4,991 cells for the live day, 2026-11-13 |
| Features | 23: fire in the cell on each of the last 7 days, fire-days in 7 and 30 days, days since the last fire, hotspots and FRP of the day, night detection; fire in the 8 neighbours and in the next ring; historical rate of the cell for that time of the year; day of the week; latitude and longitude. Chile adds month and day of the year (26) |
| Not in the model | Weather, vegetation, terrain, population, other satellites |
| Split | Train 2014-2020, tune 2021-2022, test 2023-2025. The first 7 days of 2021 and 2023 are in no split |
| Training | LightGBM with the settings of the weekly model, early stopping on tune by average precision: 523 rounds (Argentina), 157 (Chile). On a Runpod CPU pod with 16 cores: 40 seconds for the panel, 8 minutes for training and scoring |
| Not done | Feature selection, SHAP-based selection, XGBoost, Random Forest, hyperparameter search, calibration check, uncertainty intervals (all in the full plan) |

## 2. Results on the test years (2023-2025)

Fire is the positive class. Thresholds come from 2021-2022 and are applied unchanged.

| | Argentina | Chile |
|---|---|---|
| Cell-days, and with fire | 4,293,722 and 106,843 | 1,003,903 and 12,989 |
| True positives | 83,342 | 10,278 |
| False negatives | 23,501 | 2,711 |
| False positives | 440,403 | 106,483 |
| True negatives | 3,746,476 | 884,431 |
| **Recall** | **78.0%** | **79.1%** |
| False negative rate | 22.0% | 20.9% |
| Precision | 15.9% | 8.8% |
| F2 | 0.438 | 0.305 |
| PR-AUC (average precision) | 0.359 | 0.269 |
| ROC AUC | 0.921 | 0.925 |
| False alarm rate | 10.5% | 10.7% |
| Alerts per day | 489 | 109 |

Against the baselines:

| | Recall | Precision | Alerts per day | PR-AUC | ROC AUC |
|---|---|---|---|---|---|
| **Argentina, model** | 78.0% | 15.9% | 489 | 0.359 | 0.921 |
| Rule: fire today in the cell or a neighbour | 64.0% | 12.9% | 495 | 0.092 | 0.765 |
| Historical rate, same recall target | 82.2% | 9.4% | 869 | 0.196 | 0.884 |
| Rule: fire today in the cell | 32.4% | 32.5% | 99 | 0.122 | 0.654 |
| **Chile, model** | 79.1% | 8.8% | 109 | 0.269 | 0.925 |
| Rule: fire today in the cell or a neighbour | 48.7% | 8.8% | 67 | 0.049 | 0.710 |
| Historical rate, same recall target | 78.3% | 6.5% | 146 | 0.150 | 0.898 |
| Rule: fire today in the cell | 24.3% | 24.4% | 12 | 0.069 | 0.617 |

- **Same cost as the neighbour rule:** with at most the alerts of that rule on 2021-2022 (422,703 and
  53,010, matched exactly), the model catches 79.1% against 64.0% in Argentina and 68.4% against
  48.7% in Chile on the test years.
- **Every test year:** the model beats the rule and the historical rate in 2023, 2024 and 2025, in
  both countries.
- **Precision is low and must be said:** 5 of 6 alerts in Argentina and 10 of 11 in Chile had no
  hotspot the next day. It is the price of asking for 80% of an event that happens in 1 to 3% of
  cell-days. Some of those are fires the satellite did not see **(inference)**.
- **ROC AUC flatters:** almost every cell-day has no fire, so it is easy to rank them right; the
  historical rate alone reaches 0.88 to 0.90. Quote PR-AUC and precision next to it.

The full table, per season group, year, month and region, is `risk/daily_metrics.md`; the curves are
`risk/daily_roc.json` (both in the data folder, not in git).

## 3. Where the misses are, and what a higher recall costs

| At the alert threshold, test years | Recall | Share of all misses |
|---|---|---|
| Argentina, fire in the cell or a neighbour the day before | 95.3% | 14% |
| Argentina, no fire nearby the day before ("new cells") | 47.1% | 86% |
| Chile, fire nearby the day before | 97.0% | 7% |
| Chile, new cells | 62.2% | 92% |

Nine of ten misses are fires that appear where nothing showed the day before. More training on the
same features does not fix that: the model lacks information there, not capacity **(inference)**.

The cost of a higher recall with this model (from the ROC curve of the test years):

| Recall target | Alerts per day, Argentina | Alerts per day, Chile | Cells flagged |
|---|---|---|---|
| 80% | 533 | 112 | 12 to 13% |
| 85% | 689 | 146 | 16 to 17% |
| 90% | 946 | 192 | 21 to 24% |
| 95% | 1,479 | 298 | 32 to 37% |

By month the recall is lowest where fire is scarce: December in Argentina (54%), July and August in
Chile (53 to 55%).

## 4. Reasons for each alert

`scripts/daily_explain.py` splits the score of every alert into the contribution of each feature
(TreeSHAP, built into LightGBM), adds the features up into six groups and writes one sentence for
each group that pushes the score up, strongest first. 645,945 alerts are explained (2023-2025 and the
live day); 98% have three reasons.

| Group | Example of its sentence |
|---|---|
| Recent fire in the cell | "Fire was detected in this cell today, and on 5 of the last 7 days" |
| Strength of today's fire | "Today's fire here had 128 hotspots, and it was still burning at night" |
| Fire nearby | "3 of the 8 neighbouring cells had fire today" |
| History of the place | "In earlier years this cell had fire on 9% of the days at this time of the year" |
| Calendar | "The day of the week and the time of the year" |
| Place | "This part of the country has more fire activity" |

Valparaíso, predicted day 3 February 2024, probability 0.93: (1) "Today's fire here had 128 hotspots,
and it was still burning at night", 50% of the push; (2) "Fire was detected in this cell today, and
on 2 of the last 7 days", 29%; (3) history, 11%.

What a reason is not:

- **Not a cause.** It says which inputs moved the model's score, not why there is fire.
- **Not weather.** The model has none, so no sentence can say "because it is hot and windy".
- **Mostly "there is or was fire here or next to it".** The first reason is the recent fire of the
  cell or of its neighbours for 79% of the alerts, and the history of the place for the other 21%.

The script fits the model of the test years again (it is not saved) and stops unless its
probabilities equal the app file (difference below 0.00001; it was 0.00000003 for Chile).

## 5. Why the model is not tuned further

Decided on 2026-11-15, with ten hours left and the interface not yet built.

| What would help | State | Why not now |
|---|---|---|
| Other satellites as features | Measured, not built. Of the "new cell" fires of 2023-2025, 32% had a detection by NOAA-20, NOAA-21, Terra or Aqua in the cell or a neighbour the day before; that signal marks 7.5% of new cells, with four times their usual rate of fire | Needs new columns in the panel and a retraining. NOAA-20 exists since 2018 and NOAA-21 since 2023, so only three training years carry it |
| Weather of the day and a forecast for D+1 | Explored. Open-Meteo has hourly reanalysis since 1940 and forecasts, with wind direction and gusts, and needs no key | Its free tier allows 10,000 calls a day and counts 2 weeks of one point as one call: the history of our 1,466 points is about 459,000 calls. The plan that includes history is paid. OpenWeather gives one date and one point per call; Windy gives no past data |
| Weather already downloaded (NASA POWER) | In the repository's data, daily since 2011 | Three days behind, no wind direction, and it added 0.008 of average precision to the weekly model. Not tested for days |
| Longer memory of the cell (60, 90, 365 days; the same week of earlier years) | Not built | Time |
| Feature selection, tuning, other algorithms | Not done | Time. They usually move a score by one or two points, and the misses are a problem of missing information |
| Vegetation, land use, terrain, burn permits | Not in the project | No data |

## 6. Files for the interface

All in `NASA_Data_Sources/processed/risk/` (not in git; they have to be copied to the machine that
runs the app).

| File | Rows | Columns |
|---|---|---|
| `cells_daily.parquet` | 5,337,042: every cell and day of 2023-2025 (days of a satellite outage are absent) and 2026-11-13 | `burn_date`, `cell_lat`, `cell_lon`, `probability`, `baseline_probability`, `alert` |
| `cells_daily_reasons.parquet` | 645,945: the alerts only | `burn_date`, `cell_lat`, `cell_lon`, `reason_1` to `reason_3`, `share_1` to `share_3` |
| `wind_live.parquet` | 900: the alerts of 2026-11-13 | `burn_date`, `cell_lat`, `cell_lon`, `wind_from_deg`, `downwind_deg`, `wind_max_kmh`, `gust_max_kmh`, `rh_min_pct`, `tmax_c` |

There are no rows between 2026-01-01 and 2026-11-12: the day picker goes from 2025 to the live day.

## 7. Possible spread: what the data support

**Rings (observed).** Of the hotspots of day D+1, 38% lie within 5 km of a hotspot of day D, 50%
within 10 km, 69% within 25 km and 82% within 50 km (Suomi-NPP, 2013-2025; large fires weigh more).
A map for the general public can draw these rings around the hotspots of the last day, darker near
the fire, with the share next to each ring. It is where next-day detections fell in the past, not a
forecast of a perimeter, of burned area or of damage.

**Wind (context).** `scripts/daily_wind.py` reads the wind of the predicted day from Open-Meteo for
the cells in alert: where it comes from, where it blows to (`downwind_deg`), maximum speed and gusts,
minimum humidity and maximum temperature. On 2026-11-13 the 900 cells had a median maximum wind of
18 km/h (up to 43), gusts up to 76 km/h and a median maximum temperature of 37.5 °C. The interface can
draw an arrow, or stretch the ring, towards `downwind_deg`.

Limits of the wind layer:

- **Not validated.** Nothing in this project checks that hotspots move downwind. It is a wind
  forecast shown next to the fire, not a spread forecast.
- **Coarse.** One value per 0.25° cell and day; a fire follows local wind, slope and fuel.
- **Day.** Open-Meteo days are local civil days, not the 06:00 to 06:00 solar day of `burn_date`.
- **Licence.** Free for non-commercial use, CC BY 4.0: show "Weather data by Open-Meteo.com".

Burned area, speed of spread and a perimeter are not feasible with these data (`docs/modeling-plan.md`,
section 9).

## Limits

- Three test years. 2026 is not tested: it is provisional from August and the satellite changes in November.
- "No fire" often means "not seen": clouds, small or short fires, the hours of the passes.
- The alert threshold was set for the cell and the day. It says nothing about how large a fire is.
- The model was trained on final data and the live day uses near-real-time data, which FIRMS revises.
- The live day is scored by a model refitted on every year, with the threshold chosen for the model
  fitted on 2014-2020. That pair was not scored on unseen data.
