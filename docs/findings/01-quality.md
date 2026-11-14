# Findings, block 1: integrity and quality

Notebook: `notebooks/01_quality.ipynb` (owner: Vicente, module M3). Input: the unified table as built on 2026-11-14 (8,042,380 rows, no `burn_date` yet: the notebook derives it with the project formula).
Output files (git-ignored, in `NASA_Data_Sources/processed/quality/`): `quality_flags.parquet`, `static_mask_cells.parquet`, `outage_days.csv`.

## Decisions

These answer the open "Filters" and "Easter Island and Malvinas/Falklands" rows of the decision table in `docs/eda-plan.md`.

| Decision | Value | Why |
|---|---|---|
| Confidence | **Drop `low`** in both sensors | VIIRS `low` is daytime only and concentrated in the Atacama desert (48-49% of daytime rows in Antofagasta and Atacama) and the north-west (15-19%): sun glint on bare ground. Dropping it moves Suomi-NPP / Aqua only from 5.4 to 5.2. `high only` is not usable (ratio 1.3, the two scales differ). |
| Static sources | **Persistence mask for every row, SP and NRT**, both sensors | Differs from the proposal. The `fire_type` label of MODIS jumps from 2% of rows (through 2017) to 9% (2018 on) at the collection change `6.2` to `6.03`; VIIRS stays flat. A label filter would remove about 5 more points of MODIS after 2018 (7.0% before, 11.8% after) and create a fake decline. The mask removes 1 to 4% of MODIS rows in every year. |
| Volcano and offshore | Drop `fire_type` 1 and 3 in **SP rows only** | `fire_type` is empty in NRT rows. 0.2% and 0.3% of VIIRS SP rows. |
| `fire_type` 2 label | Not used as a filter | Replaced by the mask (see above). |
| Easter Island, Malvinas / Falklands | **Outside the analysis, flagged** | 467 rows (longitude west of -76) and 130 rows (Tierra del Fuego region east of -63.5). |
| Rows without region | **Nearest region within 5 km** (`admin1_fixed`) | All 10,476 are within 7.3 km of a polygon; 10,473 within 5 km (coastal rows). 3 rows stay without region. |
| NRT months | Keep, flag `provisional` | September 2026 looks real (see 1.4); this cannot be proven before SP arrives. |
| Near duplicates | Keep | 0.33-0.39% of VIIRS rows share minute and 0.001 degree cell with another. None in MODIS. |
| Outage days | List in `outage_days.csv`, exclude from "days with fire" statistics | 19 runs of at least 3 days with zero detections where the satellite normally records at least 5 per day. |

The recommended filter (`keep` in `quality_flags.parquet`) removes **14.9% of VIIRS rows** (9.0% low confidence, 5.9% static mask) and **6.9% of MODIS rows**.
It lowers the Suomi-NPP / Aqua ratio by about 8% in every year (5.4 to 4.9 on average) and keeps its shape. It removes more VIIRS than MODIS, so **the harmonization has to be calibrated on filtered rows** (block 3).

Static mask rule: 0.005 degree cells (about 500 m) of VIIRS SP rows 2012-02 to 2025-12 with detections on at least 60 days, in at least 9 calendar months and in at least 5 years: 483 cells.
87% of the SP rows inside are labelled non-vegetation and the mask holds 91% of all labelled rows. Matching of a point uses the 0.01 degree cell and its 8 neighbours, so the 1 km MODIS pixels and NRT rows are covered. Rules B (chosen), A, C and D are compared in the notebook.

## What the table contains (by sub-block)

- **1.1 Availability.** Zero-detection days are 0.2% to 1.6% of days per satellite. 19 runs of 3 or more days, all flagged as likely outage: the largest are Terra 2001-06-15 to 2001-07-02 (18 days), Aqua 2022-03-31 to 2022-04-16 (17), Suomi-NPP 2022-07-26 to 2022-08-09 (15), Terra 2022-10-10 to 2022-10-22 (13).
  We did not check them against NASA notices. Last complete day: 2026-11-13 (Terra has 7 rows on the 14th); Suomi-NPP ends on 2026-11-01 by `burn_date`.
- **1.2 Duplicates and seams.** Only 0.23% of VIIRS rows repeat a point of the same satellite within 3 hours, 1% within 24 hours: real re-observation. The yearly to API seam (31 Dec 2025) is smooth. The 5-day API chunks show no lost or doubled days (positions 1 and 5 within 5% of the mean, as in the control).
- **1.3 Ranges.** No missing FRP or brightness. VIIRS I4 saturates at 367 K in 8.4% of rows, MODIS T21 at about 500 K in a few hundred rows. FRP is 0 in 317 MODIS rows and 3,369 VIIRS rows (0.06%), negative in 18 VIIRS rows. Five VIIRS rows have a zero brightness channel: ignore zeros in any brightness analysis.
- **1.4 SP against NRT.** NRT starts on 2026-07-31 for VIIRS and on 2026-08-31 for MODIS (collection `6.1NRT`). On NOAA-20, September 2026 is 2.6 times August and 3.9 times October (previous maxima since 2018: 1.4 and 3.1), but it is made of pulses of a few days in the usual northern Argentine regions and all four satellites show it.
  August and October 2026 are far below earlier years; September (25k NOAA-20 rows) is in the range of 2024 (44k) and 2025 (21k). We conclude: plausibly real, not shown to be inflated, kept as provisional.
  The 15 NRT source files were copied to `NASA_Data_Sources/archive_nrt/2026-11-14/` to measure the revision when SP replaces them (between January 2027 for August and April 2027 for November).
- **1.5 MODIS versions.** Terra / Aqua is between 0.55 and 0.67 through 2023 and falls to 0.51 (2024) and 0.46 (2025): the Terra drift, not the collection. Suomi-NPP / Aqua is 5.1 to 5.7 in 2013-2021 with no step in 2018, and moves between 4.7 and 6.3 afterwards (in years with a 17-day Aqua outage and a 15-day Suomi-NPP outage, and the start of the drift).
  The one clear break is the `fire_type` 2 share (above). January 2019 downloaded through the API (SP) matches the yearly files: all rows found, same `fire_type` and version, FRP equal within 0.05 MW in 100% of MODIS and 99.7% of VIIRS rows.
- **1.6 `fire_type` and mask.** `fire_type` 2 is 3.6% of MODIS and 4.8% of VIIRS SP rows. The mask rows are mostly in Buenos Aires province, Neuquen, Antofagasta, O'Higgins, Valparaiso and Santa Fe. In 2026, 5.2% of VIIRS NRT rows and 1.8% of MODIS NRT rows fall in the mask.
- **1.7 Confidence.** VIIRS `low`: 12.6% of daytime rows, none at night. MODIS `low`: 4.7% (day) and 7.0% (night). Dropping it removes 9.0% of VIIRS and 5.1% of MODIS rows.
- **1.8 Geography.** The 1,205 border disagreements with FIRMS (552 Argentina to Chile, 653 Chile to Argentina) sit a median of 0.3 km from the FIRMS country polygon (99% within 5.4 km; distances are upper bounds because 1 degree is taken as 111 km).
- **1.9 Scan geometry.** 60% of MODIS rows come from the nadir bin (median pixel 1.1 km2) and 5.7% from the two outer bins (7 to 9 km2); the FRP median grows from 13 MW to 93 MW. 69% of VIIRS rows are in the first bin (0.18 km2). Re-observation within 3 hours grows from 2.2% (nadir) to 12.5% (edge bin) for VIIRS and from 0% to about 2% for MODIS. Edge pixels are kept; block 3 should test the scan angle as a covariate.

## Using the flags

`quality_flags.parquet` has one row per hotspot (8,042,380) with the key (`satellite`, `acq_datetime`, `latitude`, `longitude`; unique) and the columns `in_static_mask`, `outside_analysis`, `is_low`, `is_volcano_offshore`, `provisional`, `keep`, `admin1_fixed`.
Join on the key and keep `keep`. The key does not depend on the time columns, so the file stays valid after M1 rebuilds the table, as long as the rows do not change; re-run the notebook if they do.

## Limits

- The mask only knows static sources that were active between 2012 and 2025. A new flare or smelter in 2026 is not masked.
- The 5 km region tolerance and the "within 3 hours" re-observation window are choices, not measurements of the truth.
- `outage_days.csv` is inferred from the data, not from NASA notices.
- Hotspots are detections. This block says nothing about whether a quiet cell had fire that was not seen.
