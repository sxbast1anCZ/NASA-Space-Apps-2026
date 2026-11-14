# EDA decision record

One list of every decision the EDA took, with the block that took it. The evidence is in the findings
file of each block (`docs/findings/`). Last updated on 2026-11-14 on `main` at `8648016`.

If a decision changes, change it here and in the findings file of its block, in the same pull request.

## Time

| Decision | Value | Block |
|---|---|---|
| Day key | `burn_date`: 06:00 to 06:00 local solar time, `date(UTC + longitude / 15 h - 6 h)` | 0 |
| Month, year | `burn_month`, `burn_year`, from `burn_date` | 0 |
| Season | July to June, named by the year it starts and written "2016/17" (`season_year` = 2016) | 0 |
| Week | 52 fixed 7-day bins from 1 January; 29 February joins 28 February; the last bin has 8 days | 0, 8 |
| Clocks | UTC for storage and differences; local solar time for sensor questions; civil time for people | 0 |
| Sensor comparisons by pass | `pass_slot` (orbit), not `daynight` (sun angle) | 0 |
| Last complete day | The newest `burn_date` minus one; 2026-11-12 in the data of 2026-11-14 | 0, 4 |
| Partial periods | Compare with the same days (1 to N) of other years | 4 |

## Rows

| Decision | Value | Block |
|---|---|---|
| Quality filter | `keep` in `quality_flags.parquet` | 1 |
| Confidence | Drop `low` in both sensors | 1 |
| Static heat sources | Persistence mask (483 cells of 0.005°), for every row; the `fire_type` 2 label is not used | 1 |
| Volcano and offshore | Drop `fire_type` 1 and 3 in final (SP) rows | 1 |
| Outside the analysis | Easter Island and Malvinas/Falklands | 1 |
| Rows without region | Nearest region within 5 km, only if it is in the row's own country, with the name repaired | 1, 3 |
| Near duplicates | Kept (0.33 to 0.39% of VIIRS rows) | 1 |
| Provisional data | `processing = 'NRT'` is kept and labelled; August 2026 onward (VIIRS), September 2026 onward (MODIS) | 1 |
| Table for analysis | `harmonized/hotspots_kept.parquet` | 3 |

## Harmonization

| Decision | Value | Block |
|---|---|---|
| Units | VIIRS-equivalent hotspots | 3 |
| One sensor per period | MODIS before 2012-02-01; Suomi-NPP until 2026-10-31; NOAA-20 after | 3 |
| Method | Factor = Suomi-NPP / MODIS per region, calendar month and pass, shrunk towards the country factor with a weight of 200 MODIS detections | 3 |
| Calibration window | 2012-2021 (MODIS orbits drift from 2022) | 0, 3 |
| Before Aqua (before 2002-07-04) | Separate factors fitted on Terra rows | 3 |
| NOAA-20 | No factor (0.93 to 1.03 of Suomi-NPP per year) | 3 |
| Non-linear method | Not needed: the ratio does not depend on the size of the month | 3 |
| Grid | 0.25°, cell named by its south-west corner | 3 |
| Second metric | Fire-days (cell and day with fire): ratio 1.7 to 2.1 | 3, 4 |
| Accuracy to quote | Per year and country: about 2% (Argentina), 5% (Chile). Per region and month: 14% and 24% | 3 |

## Calendar and anomalies

| Decision | Value | Block |
|---|---|---|
| Year in rankings | Calendar year by default; always say which | 4 |
| Anomaly ratio | `(x + 1) / (median + 1)` | 4 |
| Reference of an anomaly | Same month, same area, the other years (the year judged is left out) | 4 |
| Reliable | Reference median of at least 10; below it, show the count and no colour | 4 |
| Colours | Sequential ramp for counts, diverging ramp for anomalies, both colour-blind safe, with numbers | 4 |
| Trends | No trend claim: the sign depends on the window | 4 |
| Smallest cell for an anomaly calendar | 0.5°; 0.25° for counts and maps | 5 |
| Unit of the calendar | Administrative region; show the cell regime where a region mixes regimes (14 of 35) | 5 |
| Fire regimes | 4, named by timing: winter-spring, January pulse, late summer, December pulse. Only the first and third are stable calendars | 5 |
| Cell density | Per km², with `(0.25 × 111.32)² × cos(latitude)` | 5 |

The web app does not follow the anomaly rows yet: see A3 and A4 in `docs/eda-closing-plan.md`.

## Observation

| Decision | Value | Block |
|---|---|---|
| Never add satellites | One satellite per period in every count | 2, 8 |
| Wording for "no hotspots" | "No hotspots detected. This does not mean there was no fire: clouds, small or short fires and the hours of the satellite passes can hide one." | 2 |
| Winter counts | A lower bound in central and southern Chile and in Neuquén | 2 |
| South of 40°S | No statement about observation quality | 2 |
| Outages | Listed in `quality/outage_days.csv` (19 runs); weeks with one are not observed in the risk target | 1, 8 |

## Cases, population, risk

| Decision | Value | Block |
|---|---|---|
| Demo case | Valparaíso and Viña del Mar, 2 and 3 February 2024 | 6 |
| Cases before VIIRS | Torres del Paine (December 2011), Paraná Delta (April 2008) | 6 |
| A case | A box or a set of regions; not an event | 6 |
| Population | WorldPop R2025A constrained, 2024, summed per cell; Chile rescaled to its 2024 census (factor 0.9374) | 7 |
| Exposure measure | People within 1, 5 and 10 km of the hotspots; the cell total overstates it | 7 |
| Risk target | At least one VIIRS hotspot (reference series, quality filter) in a cell and week | 8 |
| Baseline | Historical rate of the cell for that week and the two next to it, earlier years only | 8 |
| Risk layer | LightGBM with weather where tested out of sample or forecasting; the baseline elsewhere | 8 |
| Validation | Train to 2020, tune on 2021-2022, test on 2023-2025 | 8 |
| Scores | Average precision, Brier score, share of fire inside the top-ranked cell-weeks | 8 |
| Wording | "Where fire activity is most likely". Never "where a fire will start" | 8 |

## Open, with no decision

| Question | Options | See |
|---|---|---|
| Reference years for "compared with the median" | Last 10 complete years, or the full record | A4 in `docs/eda-closing-plan.md` |
| How processed data reaches other machines | Release asset, shared drive, or rebuild | Section 3 of `docs/eda-closing-plan.md` |
| Definition of a large fire | Needs events | B1 in `docs/eda-closing-plan.md` |
