# Block 3 findings: MODIS against VIIRS, and the harmonization method

Sources: `notebooks/03_modis_vs_viirs.ipynb` and `scripts/harmonize.py`, run on 2026-11-14.
Plan: `docs/eda-plan.md`, block 3. Vegetation fires only, `burn_date` as the day key,
Suomi-NPP as the VIIRS reference. This replaces the v0 note.

## Decisions

| Decision | Value | Evidence |
|---|---|---|
| Units | VIIRS-equivalent hotspots | VIIRS is the sensor that continues |
| Method | Factor per region, calendar month and pass (day or night), shrunk towards the factor of the country, month and pass | Region and month beat three other candidates; splitting the passes then lowered the error in 6 of 8 comparisons (one tie, one worse) |
| Calibration window | 2012-2021 | MODIS orbits drift from 2022 (block 0) |
| NOAA-20 from November 2026 | No factor | NOAA-20 / Suomi-NPP is between 0.93 and 1.03 every year, 2019-2025 |
| Second metric | Fire-days (0.25° cell × day with fire) | Its VIIRS / MODIS ratio is lower and steadier: 1.9 to 2.2 |

## The harmonized dataset

`python scripts/harmonize.py` (about one second) writes, in `NASA_Data_Sources/processed/harmonized/`:

- `cells_daily.parquet` (contract C2 in `docs/work-split.md`): 1,089,694 rows, 3 MB. Easter Island and
  Malvinas/Falklands are left out (each appears in only one of the two download sources). The harmonized
  count of any area and period is the **sum of `hotspots_harmonized`**. A cell that crosses a region
  border has one row per region: always sum, never count rows.
- `factors.csv`: the 949 factors per region, month and pass. Day pass: 1.3 to 8.2, median 3.0.
  Night pass: 3.6 to 14.4, median 6.9 (Argentina) and 8.2 (Chile).
- `validation_yearly.csv`.

One sensor per period, so nothing is counted twice: MODIS before 2012-02-01, Suomi-NPP until
2026-10-31, NOAA-20 after. Factor: `(V + 200 × country_factor) / (M + 200)`, with V and M the
Suomi-NPP and MODIS counts of the region, month and pass in 2012-2021. Hotspots without a region use
the country factor of their month and pass. Before 2002-07-04 (no Aqua) a second set of factors, fitted on Terra rows, applies.

![Before and after harmonization](03-harmonization.png)

## How different the sensors are

- **Overall:** Suomi-NPP sees 3.2 to 3.7 times as many hotspots as MODIS (Terra + Aqua) per year in
  2013-2021, and 4.07 times in 2022.
- **By pass:** against Aqua alone, the ratio is about 4 in the afternoon pass and 12 to 18 in the
  night pass. MODIS misses most night fires.
- **By region:** from 2.4 (Los Ríos) to 8.0 (Neuquén) among the 33 regions with at least 500 MODIS
  hotspots. One national factor is not enough.
- **By size of the month:** no effect. The ratio stays between 2.9 and 3.7 from small to very large
  region-months, so a non-linear method is not needed.
- **Drift:** Aqua / Terra goes from 1.6-1.9 (2013-2023) to 2.2 in 2024 and 2.5 in 2025.

## Candidates and scores

Each candidate predicts the Suomi-NPP count of a region and month from its MODIS count.
WAPE = sum of absolute errors / sum of VIIRS over region-months (lower is better).

| Candidate | Argentina, leave-one-year-out | Chile, leave-one-year-out | Argentina, test 2022-2025 | Chile, test 2022-2025 |
|---|---|---|---|---|
| Country and month (v0) | 15.4% | 26.2% | 21.1% | 31.2% |
| Region, shrunk | 15.9% | 26.3% | 23.4% | 29.1% |
| **Region and month, shrunk** | **14.6%** | **24.6%** | **20.5%** | **27.4%** |
| Power law per region | 16.8% | 27.9% | 24.3% | 30.0% |

### Splitting the passes

Same region and month method, with a different MODIS input. `per pass` predicts day and night
separately, each from its own MODIS count, and adds them.

| Variant | Argentina, leave-one-year-out | Chile, leave-one-year-out | Argentina, test 2022-2025 | Chile, test 2022-2025 |
|---|---|---|---|---|
| All MODIS (region and month, above) | 14.6% | 24.6% | 20.5% | 27.4% |
| MODIS day pass only | 17.5% | 29.9% | 24.5% | 34.7% |
| Aqua only | 15.5% | 26.7% | 22.1% | 30.3% |
| **Per pass** | **13.7%** | 24.7% | **19.7%** | 30.9% |

Mean error of the yearly total:

| Variant | Argentina, leave-one-year-out | Chile, leave-one-year-out | Argentina, test 2022-2025 | Chile, test 2022-2025 |
|---|---|---|---|---|
| All MODIS | 4.1% | 9.1% | 7.4% | 22.4% |
| **Per pass** | **3.2%** | **7.2%** | **6.3%** | **20.5%** |

Per pass is the method in `scripts/harmonize.py`. It is better on every yearly total and on the
region-month error in Argentina, which has about 91% of the hotspots. It ties in Chile in
leave-one-year-out and is worse in Chile in the test years (30.9% against 27.4%).

## How far the factors can be trusted before 2012

Fitting on one half of the stable overlap and predicting the other half gives a total error of
-5.0% (2012-2016 → 2017-2021) and +3.6% (the reverse). The factors moved by about 5% inside the ten
years we can check.

## Limits to state in the app and the pitch

- A harmonized MODIS-era count is an estimate. Per year and country it is within about 3% (Argentina)
  and 7% (Chile) on average. Per region and month the typical error is 14% (Argentina) and 25% (Chile).
- Chile is harder: fewer hotspots, and the test years include the drift and the 2022-2023 megafires.
- 2022 is underestimated by 13.5% when predicted from MODIS. It does not affect the series, which uses
  VIIRS in that year, but it shows that extreme seasons stretch the method.
- Before July 2002 only Terra observed. Those factors are large (often above 7) and noisy:
  2000-2002 is the least reliable part of the series.
- The factor corrects the count, not the nature of the detection: night fires that MODIS did not see
  are added as a proportion, not recovered.

## Not done from block 3

Matching of near-simultaneous detections (3.5), FRP analysis (3.6), event clustering (3.7) and
quantile mapping.
