# Findings, block 4: temporal patterns and burn calendar

Notebook: `notebooks/04_calendar.ipynb` (owner: Vicente, module M3). Input: the hotspot table and the filter flags of `docs/findings/01-quality.md`. Output: `NASA_Data_Sources/processed/calendar/monthly_by_region.parquet` (git-ignored).

**Status.** The harmonized dataset (contract C2, M2) does not exist yet, so every statistic here is **per sensor** (MODIS: Terra, Aqua; VIIRS: Suomi-NPP, NOAA-20). The code takes a table of counts, so it runs again on the harmonized counts (section "When C2 exists").
Nothing below is a harmonized result or a harmonized trend.

## Definitions the API should use

| Item | Definition |
|---|---|
| Rows | Hotspots with `keep = true` in `quality_flags.parquet`. |
| Fire-days | Distinct (0.25 degree cell, `burn_date`) pairs with at least one hotspot. Less sensitive to the VIIRS / MODIS gap in points per fire: the Suomi-NPP / Aqua ratio is 2.7 for fire-days against 4.9 for rows (2013-2025). Candidate metric for block 3. |
| Day, month, year | From `burn_date`. Dates travel as `YYYY-MM-DD` text. |
| Last complete day | The data say it: 2026-11-13. November 2026 has 13 days and is never shown next to complete months. |
| Anomaly, reference | Same month, same region, the other years of the reference period (leave-one-out: the year being judged is not in its reference). |
| `ratio` | (x + 1) / (median + 1). The pseudo-count keeps it finite when the median is 0. |
| `percentile` | Share of reference years below x, ties counting half. Shown together with the ratio: the ratio says how big, the percentile says how unusual. |
| `reliable` | Reference median at least **10 rows**. Below it, show the count and no colour. This keeps 99.6% of the rows and 74% of region-months. |
| Current month | Days 1 to N of the month in every other year, with N from the data (13 for November 2026), using **one satellite present in every year** (NOAA-20 for 2019-2025; Aqua only as a check, its orbit has drifted). |
| Provisional | A month with NRT rows is labelled provisional (`nrt_rows` in the monthly file). Today: August 2026 onward for VIIRS (from 31 July), September 2026 onward for MODIS. |
| Year in rankings | Calendar year by default; season (July to June, labelled by the year it ends) as an option. Always say which one. |
| Colours | Counts: a sequential colour-blind-safe ramp (cividis in the notebook) on a log scale. Anomalies: a diverging purple-orange ramp (not red-green). The ramps are a recommendation; they were not user-tested. |

Scale: a single colour scale for the whole country shows only northern Argentina (peak months of 22 to 29% of the year, tens of thousands of rows). Use a scale per region, or colour by percentile.

## Findings

- **Seasonality (4.2).** Northern Argentina (Formosa, Santa Fe, Corrientes, Chaco, Santiago del Estero, Salta, Entre Rios) peaks in August or September with 22 to 29% of the year in the peak month; the peak month is stable (77 to 100% of years within a month of the long-run peak).
  Central-south Chile peaks in summer: Maule January (41%), Biobio February (37%), La Araucania March (33%), Nuble April (29%). Patagonia and the Pampas are short and sharp: Chubut February (43%, 3 months for 80%), La Pampa January (43%), Rio Negro December (35%); Cordoba peaks in September (36%).
  Peaks that move from year to year: Buenos Aires (46% of years near the peak month), Mendoza and Neuquen (38%). Nationally, the daily median peaks from mid-August to mid-September (about 1,200 rows per day) with a secondary bump in January and February (about 450). These profiles feed block 5.2 (regimes).
- **Anomalies (4.3).** With the definitions above the known events stand out (Suomi-NPP, reference 2013-2025): Valparaiso February 2024 (435 rows, median 37, ratio 11.5, percentile 1.00); Nuble February 2023 (98 times); La Araucania February 2023 (13 times); Corrientes January and February 2022 (40 and 46 times); Cordoba September 2024 (10 times, but percentile 0.83: two years had more).
  This is a sanity check of the calendar, not a case study (block 6 belongs to M5).
- **Current month (4.4).** On NOAA-20, 1 to 13 November 2026 in northern Argentina is **2.1 times the median** (percentile 0.57; wide spread across 7 reference years; 2020 had 19,181 rows); Formosa and Chaco 3.4 times, Santiago del Estero 2.9 times (percentile 0.71 to 0.86). It is above the median but inside the historical range.
  Chile: NOAA-20 says 1.4 times (percentile 0.86), Aqua says 0.5 times (0.04): the satellites disagree and Chile has few rows in early November. All 2026 numbers are NRT.
- **Ranking of years and months (4.5).** Aqua and Suomi-NPP agree on years (Spearman 0.93 for both countries and Argentina, 0.68 for Chile) and months (0.96 over 156 months). **2020 is the most active year for every sensor**; for Argentina the top 3 are 2013, 2020 and 2022; for Chile 2015, 2017 and 2023. The top 2 months are August and September 2020.
  The filter and the day convention do not change the ranking (Spearman 0.97 to 0.999 and 0.995 to 1.0; 0.96% of rows change month between UTC and `burn_date`). **The year convention does, in Argentina**: calendar year and season give Spearman 0.45 (Suomi-NPP) and 0.68 (Aqua), because a July to June season splits the August to October peak; in Chile they agree (0.88 and 0.82).
- **Night pass and weekly cycle (4.6).** VIIRS sees 25% of its rows on the night pass in Argentina and 34% in Chile; MODIS 12% and 20%. The sensors do not see the same mix, so the harmonization should be estimated per `pass_slot`.
  Afternoon-pass fire-days drop on weekends in both countries and both sensors: Sunday is 37% below the weekly mean in Argentina and 28 to 30% in Chile; Saturday 15% and 4 to 8%. This is consistent with a large share of burning started or managed by people; it does not say which fires are legal or intentional.
- **Trends (4.7).** Within one sensor and its stable period, Terra (2001-2021) and Aqua (2003-2022) decrease by 2.4 to 2.9% of their median per year (intervals exclude zero); Suomi-NPP (2013-2025) shows none; on the same years 2013-2022 both sensors show about +4% per year with intervals that include zero.
  **The sign depends on the window, so the app makes no trend claim.** A harmonized trend needs the period controls of the plan (E1 without Aqua, the number of satellites, the Aqua and Terra drift after 2022).

## When C2 exists

1. Replace the `base` table by the harmonized cells (`hotspots_harmonized` as the value, `burn_date` as the day key, `provisional` as the NRT flag) and re-run the aggregates.
2. Re-run 4.3 with the full reference period (the 2013-2025 reference here is the VIIRS era only; the MODIS era needs the harmonized values).
3. Re-run 4.5: after harmonization, the ranking of years has to agree between the MODIS-based and the VIIRS-based part of the series.

## Limits

- Per-sensor series. The MODIS years (2001-2022) and the VIIRS years (2012-2026) have different levels, so heatmaps of the two must not be read as one series.
- Region-level numbers for Chile are small (hundreds to a few thousand rows per year in the south), so Chilean rankings and early-month comparisons are fragile.
- The reference of the anomaly (13 VIIRS years, 7 for NOAA-20) is short. The percentile has a resolution of about 1/12.
- The weekly cycle uses the afternoon pass only and `burn_date` as the civil weekday; M1 will provide civil local dates and the check can be repeated.
