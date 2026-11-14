# Closing the EDA: loose ends, how to close them, and what the product can rely on

Written on 2026-11-14 on `main` at `8648016`. All 9 blocks of `docs/eda-plan.md` have run. This
document lists every loose end found in the findings files, says how to close each one, and states
what the EDA already settles for the next phase: the harmonized burn calendar NASA asks for, a view
of the current fire situation, and a view of where fire activity is most likely next.

Results per block: `docs/findings/`. How to run everything: `docs/eda-runbook.md`.

## 1. What is solid

| Result | Evidence | Where |
|---|---|---|
| The day key (`burn_date`) splits no satellite pass | 0 detections between 04:30 and 07:00 local solar time, any satellite, year or latitude | Block 0 |
| The quality filter does not bend the series | The static-source mask removes 2.2% of MODIS before 2018 and 2.0% after; a filter by label would remove 7.0% and 11.8% | Block 1 |
| The harmonization reproduces what one sensor saw | Raw MODIS and the harmonized series have the same ratio between 2003-2011 and 2013-2021: 1.35 | Block 3 |
| The MODIS-era level does not depend on the method's settings | Shrinkage 50 to 1,000 and three fit windows move it by at most 0.6% | Block 3 |
| Two independent sensors tell the same history | 2003-2011 estimated from Terra alone and from Aqua alone agree within 4% in 8 of 9 years | Block 3 |
| The factors are stable inside the years we can check | Fit on one half of 2012-2021, predict the other: -1.0% and -1.6% | Block 3 |
| The factors leave no outline on the map | The ratio between eras jumps as much inside a region as across a border | Block 5 |
| The calendar flags known events | 9 of 12 case months are the highest of 26 years; two of them are from the MODIS era | Block 6 |
| The night gap between sensors is sensitivity | At the same steady sources on the same nights: VIIRS about 50% of nights, MODIS 2 to 4% | Block 2 |
| The risk model beats the historical rate out of sample | Average precision 0.563 against 0.510 on 2023-2025 | Block 8 |

## 2. Loose ends

Priority **A**: changes a number the user will see, or protects one. Close before building on top.
Priority **B**: improves the evidence or unlocks a feature. Close if time allows.
Priority **C**: cannot be closed with the data we have. State it as a limit.

Effort is an estimate for one person with a coding agent.

### Priority A

| # | Loose end | Why it matters | How to close it | Effort |
|---|---|---|---|---|
| A1 | **Satellite outages leave holes in the series.** Suomi-NPP was out from 26 July to 9 August 2022; NOAA-20 recorded 7,715 hotspots on those days and the series has none. Five more Suomi-NPP outages in 2024 and 2026 (24 days). | August 2022 is undercounted in the calendar, in northern Argentina's peak season. | In `scripts/harmonize.py`, use NOAA-20 on the outage days of Suomi-NPP (`quality/outage_days.csv`; NOAA-20 / Suomi-NPP is 0.93 to 1.03). For the MODIS-era outages (Terra 2001, 2002, 2003, 2008; Aqua 2002, 2005) there is no substitute: add an `outage` flag per day so the app can mark the month as partly observed. Test, regenerate, update block 3 findings. | 45 min |
| A2 | **Block 4 is per sensor.** Its three re-runs on the harmonized data are pending. | The calendar statistics the team documented (seasonality, anomalies, rankings) are not the ones the app shows. | Re-run `notebooks/04_calendar.ipynb` with `cells_daily.parquet` as its base table (its own section "When C2 exists"). Fix its two defects at the same time (A6). | 45 min |
| A3 | **Two anomaly definitions.** Block 4: `(x + 1) / (median + 1)`, reference without the year being judged, no colour when the median is under 10. App: `x / median`, reference includes the year, no threshold. | The same month gets two different numbers in the documents and in the app. | Apply block 4's definition in `backend/main.py` (`ratio`, `reliable`, leave-one-out median) and in the calendar view; tests. | 45 min |
| A4 | **The reference years mix two levels.** 2003-2011 is 1.35 times higher than 2013-2021 (real, per MODIS). | "Compared with the median" changes with the years chosen: a normal recent month looks low against the 2000s. | Default reference: the last 10 complete years; the full record stays as an option. State the reference next to the number. Decide with the team. | 30 min |
| A5 | **Season label.** `season_year` is the year the July-June season starts; block 4 labels by the year it ends. | Two documents name the same season differently. | Keep the start year (it is in the table and in the risk scripts), write seasons as "2016/17" everywhere, fix the sentence in `04-calendar.md`. | 10 min |
| A6 | **Four defects in notebooks 01 and 04**: tangled plots (no `ORDER BY`), a wrong year in a text, a check that does not find Bío-Bío, a sentence about VIIRS `fire_type`. | They do not change data, but the committed outputs are the evidence. | Fix and re-run both notebooks. Listed in `docs/findings/eda-summary-and-harmonization.md`, section 5. | 30 min |
| A7 | **No tests for `scripts/risk_model.py` and `scripts/risk_weather.py`.** | The value-added layer rests on them, and block 8's leak checks are by reading the code. | Synthetic-panel tests: features use no information from the scored week, test years never enter training, the weather window ends the day before the week. | 45 min |

### Priority B

| # | Loose end | What closing it gives | How | Effort |
|---|---|---|---|---|
| B1 | **No events.** A case is a box, not a fire (blocks 3.7, 6, 7, 8). | A "number of fires" figure (the challenge mentions it), people near each fire, a large-fire target, and a summary of the current situation as "N active fires". | Link hotspots closer than about 1 km and 1 day into events (`scipy.spatial.cKDTree` per day window). Check on the nine cases of block 6. | 2 h |
| B2 | Valparaíso timeline with sources and the check against the risk layer are on `feat/m5-valparaiso-case`, not on `main`. | The demo case with its sources in one place. | Add the timeline table to `06-case-studies.md`; the risk check is already in block 8. | 20 min |
| B3 | Near-simultaneous Aqua and Suomi-NPP detections were not matched (3.5). | Separates pixel size from sensitivity by day. Block 2 already shows sensitivity at night. | Match on UTC within 10, 30 and 60 minutes and the real pixel size. | 1.5 h |
| B4 | Scan angle was not tested as a covariate of the ratio (planned in block 1). | Says whether edge-of-swath pixels bias the factors. | Ratio per scan-angle bin in notebook 03. | 40 min |
| B5 | Two of the four fire regimes are one season (2016/17); months were clustered as 12 unrelated numbers. | Regimes that describe a calendar and not a year. | Cluster on the full harmonized record (2001-2025) with circular month features. | 40 min |
| B6 | The app does not use population or fire regimes. | "People living in the selected area" and "when this place burns" in the product. | Two small API fields from `population/cells.parquet` and `spatial/cell_regimes.parquet`. | 1 h |
| B7 | Block 7 was run on one machine only; `population/cells.parquet` is not everywhere. | Reproducibility of the exposure numbers. | Run `scripts/download_population.sh` and notebook 07 on a second machine and compare the totals. | 20 min |

### Priority C: limits to state, not to fix

| # | Limit | Where to state it |
|---|---|---|
| C1 | Hotspots are detections, not fires, burned area or damage. | App footer (done), pitch |
| C2 | "No hotspots" is not "no fire": clouds, small fires, pass times. Winter counts in central and southern Chile and Neuquén are a lower bound. Nothing can be said about observation quality south of 40°S. | App (wording in block 2), pitch |
| C3 | MODIS-era values are estimates: about 2% (Argentina) and 5% (Chile) per year, 14% and 24% per region and month. 2000-2002 is the least reliable part. | App tooltip (done), calendar note |
| C4 | Night fires of the MODIS era are added as a proportion, not observed. | Calendar note |
| C5 | The MODIS collection change of 2018 is not ruled out as part of the 1.35 difference. | `03-modis-vs-viirs.md` (done) |
| C6 | August 2026 onward is provisional and will be revised by FIRMS (January to April 2027). The copy in `archive_nrt/2026-11-14` allows measuring the revision then. | App (done), runbook |
| C7 | Outage days come from the data, not from NASA notices. The static mask only knows sources active in 2012-2025. | `01-quality.md` (done) |
| C8 | Exposure is not damage; one population year (2024); residents only. | `07-population.md` (done), pitch |
| C9 | The risk model predicts at least one hotspot, not severity. Three test years. | `08-risk-model.md` (done), app text (done), pitch |
| C10 | No trend claim: the sign depends on the window. | Pitch |

## 3. Documentation still missing

| Gap | Fix | Effort |
|---|---|---|
| The plan promised `docs/eda-findings.md`, one record of every decision. The decisions are spread over nine findings files. | Written with this document: `docs/eda-findings.md`. | done |
| `CLAUDE.md`: its "Project status" section describes the project before any block ran. Agents load it first. | Replace that section with a short current status and pointers. | 20 min |
| `README.md` describes the pipeline up to the hotspot table, then the app. The quality notebook, the risk layer and the optional downloads are in the runbook only. | One "Pipeline" section that points to the runbook instead of repeating it. | 15 min |
| How the processed data reaches another laptop or a server is not written anywhere. Three people got it three ways today. | Decide (a release asset, a shared drive or rebuild) and write it in the runbook. Needed before deployment. | 15 min, after the decision |

## 4. What the EDA settles for the product

### The harmonized burn calendar (the challenge)

Ready today on `main`: area by drawing, coordinates or region; period; calendar per year and month;
comparison with the median of the same days; rankings; colour-blind-safe ramps; CSV of hotspots and of
the calendar; charts as images; estimates and provisional months labelled.

To make it match the EDA: A1 (outages), A3 (one anomaly definition), A4 (reference years).
Not built: a view of one day, a season view, touch drawing, deployment.

### A view of the current situation

What the EDA gives:

- The hotspots of the last passes can be shown as soon as FIRMS publishes them. The afternoon pass
  is at about 15:00 to 16:30 civil time and the night pass at about 02:00 to 04:00 (block 0, block 6).
  FIRMS states that near-real-time data arrives within about 3 hours of the pass; we did not measure it.
- The first detection came 2 to 3 hours after the fire started in the one case with an hour
  (Valparaíso 2024). The view confirms and maps; it does not raise the first alarm.
- Near-real-time rows have no `fire_type`. The static-source mask handles them (block 1).
- Context that already exists per cell: how unusual today is for this place and date (calendar),
  people living there (block 7), the fire regime (block 5).

What is missing: a scheduled download of the last days (the API script exists and needs the key),
and events (B1) to say "N active fires" instead of "N hotspots".

### A view of where fire activity is most likely next

What the EDA gives, for a weekly outlook (in the app today):

- The model ranks cells: watching the top 10% of cell-weeks catches 57% of the fire activity.
- Most of its skill is the history of the place and persistence. Weather adds little at this scale.

What the EDA gives, for a next-day outlook (not built):

- A cell with fire today has fire tomorrow 33% of the time, 13 times the base rate of 2.6%.
- 65% of tomorrow's fire cells are in or next to a cell with fire today. That part is predictable
  from today's hotspots. The other 35% starts where nothing showed the day before.
- So a next-day view will mostly say "the fires burning today, and their surroundings". That is
  useful, and it should be described that way.
- Weather for tomorrow needs a forecast. NASA POWER is three days behind, so it can train a model
  but cannot feed tomorrow's outlook. A forecast source would have to be added and tested.
- The same scripts work with days instead of weeks: baseline from the same days of earlier years,
  fire in the cell and its neighbours on the previous days, test on 2023-2025 against two baselines
  (the historical rate, and "same as today").

Wording for all of it: where fire activity is most likely. Not where a fire will start.

## 5. Suggested order

| Step | Items | Why first | Effort |
|---|---|---|---|
| 1 | A1 | It changes the dataset every other item reads | 45 min |
| 2 | A3, A4, A5 | One calendar definition for documents and app | 1.5 h |
| 3 | A2, A6 | The calendar block on the harmonized data, with clean outputs | 1.25 h |
| 4 | A7 | Protects the risk layer before it grows a daily version | 45 min |
| 5 | `CLAUDE.md`, `README.md`, data hand-off | Agents and deployment | 50 min |
| 6 | B1 | Unlocks "number of fires" and the current-situation summary | 2 h |
| 7 | B2, B6 | Demo and product | 1.5 h |

Steps 1 to 5 are about 5 hours for one person, less in parallel: A1 and A7 touch `scripts/`;
A2 and A6 touch notebooks 01 and 04; A3 to A5 touch `backend/` and `frontend/`.
