# EDA summary: key results and what they mean for the harmonization

Written on 2026-11-14 after re-running the pipeline of `docs/eda-runbook.md` (steps 5 to 9) and the
notebooks 00, 01, 03 and 04 on the data downloaded that day. Every number below comes from that run
or from the findings files it reproduced. Statements marked **(inference)** are interpretation, not
something the data proves. Blocks 2, 5, 6 and 7 are planned in `docs/eda-plan.md` but not run.

## 1. What was checked

| Check | Result |
|---|---|
| Hotspot table | 8,042,380 rows, as expected |
| Quality filter | 7,000,520 rows kept (12.95% removed) |
| Harmonized dataset | 1,020,967 cell-day rows, 949 factors |
| Risk panel | 2,689,584 rows; model beats baseline on 2023-2025 (average precision 0.555 against 0.510) |
| Notebooks 00, 01, 03, 04 | Run top to bottom without errors |
| Tests | 41 pass. `tests/test_api.py` could not be collected (`fastapi` is not installed here), so the 57 tests in the runbook are not confirmed |

## 2. Results that matter for the harmonization

Each row says what the EDA found, where, and what it changes or constrains.

### 2.1 The two sensors differ in a way one factor cannot fix

| Finding | Evidence | Effect on the harmonization |
|---|---|---|
| Suomi-NPP sees 2.8 to 3.7 times the MODIS hotspots per year | Block 3.1 | Counts must be rescaled to a common unit (VIIRS-equivalent). |
| The ratio depends on the pass: against Aqua it is 3.4 to 4.0 by day and 13 to 19 by night | Block 3.2 | A single factor would mix two populations. Factors are fitted per pass. |
| The ratio depends on the region: 2.08 (Los Ríos) to 5.88 (Neuquén) among 33 regions | Block 3.2 | One national factor is not enough. Factors are per region, shrunk towards the country. |
| The night share of rows changes with the month: VIIRS Chile goes from about 15% in winter to about 55% in January | Block 4.6 | The mix of day and night fires moves with the season, so a factor fitted without the pass would be biased by month. |
| The ratio does not depend on how much fire a region-month has (2.7 to 3.4 from small to very large) | Block 3.2 | No non-linear method is needed. |

Fire-days (0.25° cell and day with at least one hotspot) have a much lower and steadier ratio: 1.7 to
2.1 in block 3, against 4.9 for rows in block 4.5. Most of the gap in rows is therefore points per
fire, which fits the 1 km against 375 m pixel. That reading is supported by the data but not proven:
the block that would separate pixel size from sensitivity (matching near-simultaneous detections,
3.5) was not done. The night ratio of 13 to 19 is not explained by pixel size alone.

### 2.2 Where the factors are valid

| Finding | Evidence | Effect |
|---|---|---|
| Terra and Aqua pass times drift from 2022: Terra 10.2 h to 8.6 h, Aqua 13.9 h to 15.8 h (2026) | Block 0.5 | The calibration window is 2012-2021. MODIS is not used for the series after 2011. |
| In 2002-2011 the day-pass times match the calibration window (Terra 10.2 to 10.3 h, Aqua 13.9 h) | Block 0.5 table | Extrapolating the factors back to 2002-2011 does not cross an orbit change. **(inference from the table)** |
| In the drift years the MODIS-based estimate misses VIIRS: 2022 is 12% low and 2024 is 13% high | `validation_yearly.csv` | Shows the error size of an extreme or drift year. It does not enter the series, which uses VIIRS there. |
| Yearly errors of 4% or less in 2012-2021 | `validation_yearly.csv` | These years are inside the fit window: not evidence for 2000-2011. |
| Fitting on one half of 2012-2021 and predicting the other half: total error -1.0% and -1.6% | Block 3.11 | The only out-of-sample check of the extrapolation, and it covers 10 years. |
| Typical error per region and month: about 14% (Argentina) and 24% (Chile) | Block 3.10 | The calendar should not show region-month anomalies of Chile as precise. |
| Before July 2002 only Terra observed | Block 0.7 | 2000-2002 uses separate Terra factors and is the least reliable part. |

### 2.2b Collections and orbits are not the same problem

- Terra / Aqua rows stay between 0.55 and 0.67 through 2023 (no step at the 2018 collection change)
  and fall to 0.51 and 0.46 in 2024 and 2025: the orbit drift, not the collection (block 1.5).
- The `fire_type` 2 label share of MODIS jumps from 2.3% (mean 2000-2017) to 7.5% (2018-2025). A
  filter by label would remove 7.0% of MODIS rows before 2018 and 11.8% after, creating a fake
  decline of about 5 points. The static-source mask removes 2.2% before and 2.0% after (blocks 1.5,
  1.6, decisions). So the filter uses the mask, and `fire_type` only for volcano and offshore rows.
- The mask only knows sources active in 2012-2025. Static sources that stopped before 2012 are not
  in it, so MODIS-era counts may keep a few. **(inference)**

### 2.3 Data and period issues that touch the series

| Finding | Evidence | Effect |
|---|---|---|
| NOAA-20 / Suomi-NPP is 0.93 to 1.03 per country and year | Block 3.9 | No factor for the switch on 2026-11-01. It leaves a possible step of a few percent. |
| Suomi-NPP stopped on 2026-11-02 | Block 0.7 | The series moves to NOAA-20 from 2026-11-01. |
| August 2026 onward (VIIRS) and September 2026 onward (MODIS) are provisional | Block 1.4 | Those months will be revised when the standard data replaces them (January to April 2027). The archive copy in `archive_nrt/2026-11-14` lets the team measure the revision. |
| September 2026 is the highest September on NOAA-20 since 2018 (2.6 times August, 3.9 times October) | Block 1.4, corrected plot | Made of a few pulses (15 of 91 days with 1,000 rows or more hold 52% of the rows); plausibly real, not proven. |
| 19 runs of 3 or more zero days are likely outages: Terra 2001 (18 days), Aqua 2022 (17), Suomi-NPP 2022 (15), Terra 2022 (13) | Block 1.1 | They lower the count of the satellite that was reference in that period. They were not checked against NASA notices. |
| 0.33% to 0.39% of VIIRS rows are near duplicates; 0.23% repeat a point within 3 hours | Block 1.2 | Not removed. Small effect on counts. |
| VIIRS edge-of-swath pixels repeat a detection within 3 hours in 12.5% of rows (2.2% at nadir); MODIS 2.1% at the edge | Block 1.9 | The scan angle was meant to be tested as a covariate of the ratio in block 3. The block 3 notebook has no such test: it does not read `scan_km`. |

### 2.4 What the series looks like, and the open problem

The harmonized series averages **273,833 hotspots a year in 2001-2011 and 203,561 in 2013-2025, a
ratio of 1.35** (`cells_daily.parquet`, calendar years). Raw MODIS is also higher before 2012. There is
no obvious step at the 2012 switch. The data cannot say whether the higher level is real fire
activity, the factors, the MODIS collections (6.2, then 6.03, then 61.03) or something else.

Within one sensor and one stable period (block 4.7):

| Series | Years | Slope, % of median per year | 95% interval |
|---|---|---|---|
| Terra rows | 2001-2021 | -2.4 | -3.9 to -1.3 |
| Aqua rows | 2003-2022 | -2.9 | -4.8 to -1.1 |
| Suomi-NPP rows | 2013-2025 | +0.3 | -2.9 to +5.7 |
| Aqua rows | 2013-2022 | +4.0 | -1.3 to +15.3 |
| Suomi-NPP rows | 2013-2022 | +4.6 | -1.7 to +16.5 |

The sign depends on the window, so the project rule is **no trend claim**. This matters for the app:
the "median of the same month in other years" mixes the higher MODIS-era level with the VIIRS era, so
the current-month comparison depends on which years enter the reference.

## 3. Rankings are robust to the choices that were tested

From block 4.5, Spearman rank correlation of yearly rows:

| Comparison | Both countries | Argentina | Chile |
|---|---|---|---|
| Aqua against Suomi-NPP, 2013-2025 | 0.934 | 0.934 | 0.676 |
| Filter against no filter (Suomi-NPP) | 0.995 | 0.984 | 0.973 |
| `burn_date` against UTC date (Suomi-NPP) | 0.995 | 1.000 | 1.000 |
| Calendar year against July-June season (Suomi-NPP) | 0.566 | 0.451 | 0.879 |

2020 is the most active year in every sensor for both countries together. Chile's ranking is more
fragile because it has few rows. For Argentina the calendar year is the natural fire year: the August
to October peak is split by a July-June season. The calendar should say which year definition it uses.

## 4. What to test next, in order of how much it protects the series

These are suggestions **(inference)**, not decisions.

1. **The 1.35 level difference before 2012.** Harmonize Terra-only and Aqua-only separately for
   2003-2011 and see whether they agree; test the sensitivity of the level to the shrinkage constant
   (200) and to the calibration window; repeat with fire-days, whose ratio is steadier.
   **Done in `docs/findings/03b-pre2012-level.md`:** the difference is already in raw MODIS, is the same
   for Terra and Aqua, holds for every window and `K >= 50`, and 65% of it is in Salta and Santiago del
   Estero (July to November).
2. **Match near-simultaneous Aqua and Suomi-NPP detections** (block 3.5) to separate pixel size from
   sensitivity, especially at night.
3. **Test the scan angle** as a covariate of the ratio, as block 1 planned.
4. **Outages:** decide whether the harmonized counts are corrected or flagged for the 19 outage runs.
   I did not check how `scripts/harmonize.py` treats them.
5. **Re-run block 4** on `cells_daily.parquet`: the three re-runs listed in its section 4.8. Today
   every calendar statistic is per sensor.
6. **Settle the two open conventions** of the runbook: season label (start year in the table, end
   year in `04-calendar.md`) and anomaly ratio (`(x + 1) / (median + 1)` with a threshold of 10 rows in
   block 4, `x / median` with no threshold in the app).

## 5. Defects found in the notebooks

None of these changes the harmonized data. Nothing was edited in the repository for them.

1. **Four plots in `01_quality.ipynb` are tangled**: cells 8, 12, 18 and 27 have no `ORDER BY`, so the
   lines join points in arbitrary order. The committed outputs have the same defect. The NOAA-20
   plot of 2026 (cell 18) cannot be read as it stands.
2. **`04_calendar.ipynb`, section 4.4:** the text says Argentina's maximum of 19,181 rows on 1-13
   November was in 2020. In the data it is 2022 (2020 has 13,789). The percentile of 0.57 is right.
3. **`04_calendar.ipynb`, section 4.3:** the check for Bío-Bío 2023 matches the pattern `'Biob'`
   against "Bío-Bío" and finds nothing, so 6 rows come out for 7 checks.
4. **`01_quality.ipynb`, section 1.5:** the text says VIIRS stays flat in the `fire_type` 2 share; it
   ranges from 2.2% to 7.8% by year. The conclusion about the mask does not change.

Also: the notebook 04 filtered table has 7,000,515 rows with a region, against 7,000,520 in the
filter. Four of the five are the kept rows without region; the fifth was not traced.

## 6. Limits of this document

- A hotspot is a thermal detection in a pixel, not a fire. Absence of points does not prove absence of
  fire: the table has no cloud or overpass information.
- No result here says the harmonization is right; the only out-of-sample evidence is the half-split
  of 2012-2021 and the drift years 2022-2025.
- Block 8 (risk) has no notebook. Its metrics are in `NASA_Data_Sources/processed/risk/*.json`
  (git-ignored), and it does not include weather.
