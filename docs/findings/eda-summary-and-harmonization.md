# EDA summary: key results and what they mean for the harmonization

Written on 2026-11-14 after re-running the pipeline of `docs/eda-runbook.md` (steps 5 to 9) and the
notebooks 00, 01, 03 and 04 on the data downloaded that day. Blocks 5, 6 and 7 were run afterwards on
the same data (section 2.5). Every number below comes from those runs or from the findings files they
reproduced. Statements marked **(inference)** are interpretation, not something the data proves.
Block 2 is planned in `docs/eda-plan.md` but not run.

## 1. What was checked

| Check | Result |
|---|---|
| Hotspot table | 8,042,380 rows, as expected |
| Quality filter | 7,000,520 rows kept (12.95% removed) |
| Harmonized dataset | 1,020,967 cell-day rows, 949 factors |
| Risk panel | 2,689,584 rows; model beats baseline on 2023-2025 (average precision 0.555 against 0.510) |
| Notebooks 00, 01, 03, 04 | Run top to bottom without errors |
| Notebooks 05, 06, 07 | Run top to bottom without errors, after two fixes to my environment (not to the repository). 06 failed with duckdb 2.0.0 and ran from a copy with one cast added (section 5). 07 needed `rasterio` and the two WorldPop rasters (160 MB). About 25 numbers compared with `05-spatial.md`, `06-case-studies.md` and `07-population.md` are identical |
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

### 2.5 Blocks 5, 6 and 7: space, past fires and population

None of these blocks changes the factors or contradicts the method (region × month × pass, fitted on
2012-2021, `K = 200`). They add three checks that the method passes, three places where it has not been
tested, and what the calendar must show.

**Block 5, spatial patterns** (`05-spatial.md`)

| Finding | Evidence | Effect on the harmonization |
|---|---|---|
| The VIIRS-era / MODIS-era density map has no region outline: the jump of the log2 ratio between neighbouring cells is 0.63 inside a region and 0.69 across a region border. Median ratio 0.76 over 2,484 cells, 61% within a factor 2 | 5.1 | The region factors leave no seams in space. This checks for seams, not the level. |
| The ratio is lowest in the dry Chaco (Santiago del Estero 0.42, Salta 0.46, San Luis and Catamarca 0.43) and highest in the centre-south of Chile (Maule and Ñuble 1.52) and Chubut (2.46) | 5.1 | Same places and direction as the 1.35 level difference of section 2.4: `03b-pre2012-level.md` puts 65% of that excess in Salta and Santiago del Estero. Two views of one pattern (1 / 1.35 = 0.74 against 0.76, different statistics, so only roughly comparable **(inference)**). Still no cause. |
| 14 of the 35 regions with classified cells hold two or more fire regimes; 21 hold one, including every large region of the north | 5.2 | The factor is per region, so in those 14 it averages cells with different seasons (La Pampa: 58% of its hotspots in the January pulse, 19% in the December pulse, 14% in winter-spring). Whether the VIIRS / MODIS ratio differs between regimes inside a region was not tested. |
| Two of the four regimes (January and December pulses) are mostly one season: 33% and 37% of their hotspots fall in 2016/17. Fitted on 2012-2018 and 2019-2025 separately, the regimes agree weakly (adjusted Rand index 0.27) | 5.2 | Regimes are not a stable stratum for the factors; do not replace the region with them **(inference)**. |
| My own query, not in the notebooks: of the December to February Suomi-NPP hotspots in the 2012-2021 calibration window, 48% (La Pampa), 59% (Río Negro) and 65% (Maule) belong to season 2016/17 | `hotspots_kept.parquet` | The summer factors of those regions rest heavily on one season. Their values (2.2 to 3.3) sit in the range of other months and are well supported (La Pampa December: 6,163 VIIRS and 2,090 MODIS rows), except Maule December (651 and 256), where the shrinkage matters. Whether they hold in other summers was not tested. |
| 0.25° cells are mostly empty: the median cell has no hotspot in 90% of 310 months. Only 759 cells (15%, holding 67% of hotspots) reach a median of 10 in their peak month; 0.5° gives 25% and 82%. South of 45°S and in northern Chile no cell size reaches it | 5.4 | The factors are not applied per cell, so they are unaffected. The calendar needs the reliability flag, and 0.5° is the smallest cell for an anomaly colour. The block 3.10 error per region and month (14% Argentina, 24% Chile) comes on top. |
| 483 persistent static cells (Neuquén 141, Buenos Aires 73, Entre Ríos 43); the ten busiest have 2,600 to 3,800 days of detections | 5.3 | Confirms the mask is needed. It was built on 2012-2025, so the limit of section 2.2b stands. The site names are a reading of coordinates, not checked. |

**Block 6, past fire cases** (`06-case-studies.md`)

| Finding | Evidence | Effect on the harmonization |
|---|---|---|
| The calendar flags every case: of 12 case-months, 9 rank first among 26 years and all rank in the top 4. That includes three MODIS-era months scaled to VIIRS (Torres del Paine Dec 2011 and Jan 2012, Paraná Delta April 2008), all rank 1 | 6.3 | Known events stay on top across the 2012 switch: the harmonized series does not bury MODIS-era fires. This tests ranks, not the scale. |
| The anomaly ratio breaks at the extremes: median 0.0 gives 514.7 (Torres del Paine), median 5 gives 510 (Puerto Patriada, Jan 2026), median 843 gives only 5.4 (Córdoba, Sep 2024, rank 3). Five of the 12 case-months have a median below 10 | 6.3 | Supports the block 4 threshold of 10 and the `(x + 1) / (median + 1)` form: the app's `x / median` divides by zero when the median is 0 **(inference)**. Rank compares better than ratio. This bears on the open convention of section 4. |
| MODIS-only cases: Torres del Paine 106 raw hotspots become 552 (factor 5.2); Paraná Delta 3,754 become 16,203 (factor 4.3) | 6.4 | With no VIIRS in the period, these months are the factor times a MODIS count. The ranks survive; the level depends on the factor alone. Hotspots are not hectares (about 17,600 and 207,000 ha), so burned area cannot check it. |
| Suomi-NPP / (Terra + Aqua) in each case window is 3.3 to 4.0 for the 2017 to 2024 cases and 6.6 for both 2026 cases (Puerto Patriada, Chilecito) | 6.2 | Fits the orbit drift of section 2.2: MODIS is a weaker reference after 2022, and it is not used in the series after 2011. **(inference)** |
| Valparaíso, 2-3 February 2024, pass by pass: first detection on the reported day (14:47 local, NOAA-20); on the peak night pass, NOAA-20 195, NOAA-21 206 and Suomi-NPP 223 hotspots against 4 for Aqua, 12 minutes apart from Suomi-NPP | 6.2, pass table | One pass, so an anecdote: a night ratio of about 56 against the 13 to 19 of block 3.2. Swath position was not checked. It points at the matching of block 3.5 (section 4, item 2). Night MODIS counts of a single event are rough even after the factor. |

**Block 7, population** (`07-population.md`)

| Finding | Evidence | Effect on the harmonization |
|---|---|---|
| WorldPop Chile totals 19.71 million against 18.48 million in the 2024 census (+6.68%), rescaled by 0.9374; Argentina 45.62 million against 45.89 million (-0.60%) | 7.1, 7.2 | None. Population does not enter the harmonization; it only affects the exposure numbers. |
| Fire is where few people live: cells under 1 person per km² hold 0.7% of people and 41.7% of the 2012-2025 hotspots; under 10 per km², 72%. Cells over 100 hold 73.1% of people and 5.5% of hotspots (3.4 hotspots per 1,000 people against 2,645) | 7.5 | The factors are fitted mostly on rural and wildland fire. Whether the ratio differs in the 5.5% of hotspots in dense cells (agricultural burns, small fires, urban heat the mask missed) was not tested. |
| Valparaíso 2024 has 1/20 of the hotspots of 3 February 2023 (19.9 times fewer) but similar exposure: 203,956 people within 1 km against 153,077; 1,063,455 within 10 km against 1,459,601 | 7.4, 7.6 | Both rank first in the calendar, which ranks activity, not exposure. Any importance ranking in the app needs a separate exposure layer; the harmonization stays in activity units. |
| One population year (2024) for every fire year, and WorldPop starts in 2015 | 7 limits | No exposure for MODIS-era events. Do not weight the series by population. |

**What changes in practice (inference).** The method stays. Three tests would protect it: factors by
regime against by region in the 14 mixed regions, summer factors fitted without 2016/17, and the ratio by
population-density class (section 4, items 7 to 9). For the app: the reliability flag and 0.5° as the
smallest cell with an anomaly colour; rank next to the ratio; no ranking by hotspot count alone.

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
   block 4, `x / median` with no threshold in the app). Block 6 favours the block 4 definition
   (section 2.5).

Added after blocks 5, 6 and 7:

7. **Factors by regime against by region** in the 14 regions that mix regimes (La Pampa, Río Negro,
   Neuquén, Corrientes, Maule and others). Compare the error out of sample, as in block 3.11.
8. **Summer factors without season 2016/17** for La Pampa, Río Negro and Maule: refit on 2012-2021
   minus that season and see how much the factors and the pre-2012 estimates move.
9. **The ratio by population-density class** (the four classes of block 7.5), to see whether the
   factors fitted on rural fire hold in the 5.5% of hotspots that fall in dense cells.
10. **A control for block 6.** It shows that known fires rank high, not how often an ordinary month
    does. Count how many region-months rank first or have a ratio above 20 without a known fire.

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
5. **`06_case_studies.ipynb` fails with duckdb 2.0.0** (installed here; `requirements.txt` only says
   `duckdb>=1.0`). The pass table of the Valparaíso case calls `date_trunc('hour', acq_datetime)` and
   duckdb cannot match it to the nanosecond `TIMESTAMPTZ` that pandas writes. I ran a copy with
   `acq_datetime::TIMESTAMPTZ` added in the `h` view (cell 1); every output matches the committed
   findings. The repository notebook was not edited. Notebooks 05 and 07 ran unchanged.

Also: the notebook 04 filtered table has 7,000,515 rows with a region, against 7,000,520 in the
filter. Four of the five are the kept rows without region; the fifth was not traced.

## 6. Limits of this document

- A hotspot is a thermal detection in a pixel, not a fire. Absence of points does not prove absence of
  fire: the table has no cloud or overpass information.
- No result here says the harmonization is right; the only out-of-sample evidence is the half-split
  of 2012-2021 and the drift years 2022-2025.
- Blocks 5, 6 and 7 describe where fire is, whether nine known cases show up, and who lives near
  them. They do not test the harmonization against an independent truth. The case list was chosen by
  the team and has no control months. Exposure is not damage, and WorldPop models residents only.
- Block 8 (risk) has no notebook. Its metrics are in `NASA_Data_Sources/processed/risk/*.json`
  (git-ignored), and it does not include weather.
