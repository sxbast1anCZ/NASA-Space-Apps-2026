# Findings, block 5: spatial patterns

Notebook: `notebooks/05_spatial.ipynb` (owner: Felipe). Task: `docs/open-tasks.md`, task 1. Input: `processed/harmonized/cells_daily.parquet` (harmonized hotspots per 0.25° cell and `burn_date`) and `processed/quality/static_mask_cells.parquet`.
Output: `NASA_Data_Sources/processed/spatial/cell_regimes.parquet` and `regime_names.csv` (git-ignored).

Units: harmonized hotspots (VIIRS-equivalent, the sum of `hotspots_harmonized`). Hotspots are detections, not fires and not burned area. Densities are per km², with the cell area `(0.25 * 111.32)² * cos(cell_lat + 0.125)`. MODIS era: 2001-2011 (estimated from MODIS with the block 3 factors). VIIRS era: 2012-2025 (Suomi-NPP).

## Decisions

| Decision | Value | Why |
|---|---|---|
| Number of fire regimes | **4** (k-means on the 12 monthly shares of each cell, 2012-2025) | Highest silhouette (0.37 against 0.26 for k = 5 and 6). k = 5 adds a "flat profile" group that mixes central Chile with the Paraná wetlands; k = 6 splits the north into August and September, which block 4.2 already shows per region. |
| Regime names | 0 **Winter-spring** (peak August), 1 **January pulse**, 2 **Late summer** (peak February, tail to April), 3 **December pulse** | Named by timing, not vegetation: only monthly profiles were used. |
| Which regimes are recurring | Winter-spring and Late summer. The January and December pulses are mostly one season (2016/17 holds 33% and 37% of their hotspots) | Use the two pulses as "summer grassland pulses", not as a stable calendar. |
| Unit of the calendar | Keep the administrative region. Show the cell regime where a region mixes regimes (14 of 35 regions) | 21 regions hold one regime, including every large northern region. A single profile for a mixed region averages two seasons. |
| Smallest cell size the app should offer for an anomaly calendar | **0.5°** | 25% of 0.5° cells are reliable (82% of hotspots) against 15% of 0.25° cells (67%). 1° reaches 45% (94%) but its cells are about 90 km wide. |
| Cell sizes for counts and maps | 0.25° stays, with a per-cell `reliable` flag (peak-month median ≥ 10, the block 4 threshold) | Below the threshold the calendar shows counts and no anomaly colour, or falls back to the region. |
| Months counted for zero shares | 310 complete months (January 2001 to October 2026), not 312 | November 2026 has 12 days and December 2026 has not happened: counting them as zero months would inflate the zeros. |

## Results

### 5.1 Density maps

- **Where it burns.** The 30-35°S band holds 52% of the 2012-2025 hotspots (0.13 per km² per year); 35-45°S has 0.04 to 0.05; south of 45°S under 0.01. The densest cells (0.8 to 1.1 per km² per year) are the Paraná islands of Entre Ríos and Santa Fe, then Formosa and the Salta lowlands. In Chile the dense band is Maule to La Araucanía.
- **Area correction.** A 0.25° cell is 728 km² at 20°S and 444 km² at 55°S (39% less). It matters little for the ranking because the southern counts are very small.
- **Ratio map, VIIRS era / MODIS era** (2,484 cells with at least 50 hotspots in each era): median 0.76 (log2 -0.39), 61% of cells within a factor 2.
- **Harmonization check: no region outline.** The log2 ratio jumps about the same between neighbouring cells inside a region (median 0.63) and across a region border (0.69). The region and month factors of block 3 do not draw their borders on the map.
- **What the ratio shows instead**: less fire in the VIIRS era in the dry Chaco (Santiago del Estero 0.42, Salta 0.46, San Luis and Catamarca 0.43), more in central-south Chile (Maule and Ñuble 1.52, Biobío 1.42: 2017 and 2023), Neuquén (1.56) and Chubut (2.46), and sharp lines along the Paraná delta and the Corrientes wetlands (2020 and 2022). These are known changes in fire activity. The overall 0.76 is not a trend claim (block 4: the sign depends on the window).

### 5.2 Fire regimes

2,282 cells have at least 100 harmonized hotspots in 2012-2025; they hold 97.6% of the hotspots of the period.

| Regime | Cells | Hotspots 2012-2025 | Peak month (share) | Months for 80% | Largest season (share) | Where |
|---|---|---|---|---|---|---|
| 0 Winter-spring | 1,610 | 2,200,000 | August (24%) | 7 | 2020/21 (14%) | Chaco, Santiago del Estero, Santa Fe, Formosa, Salta, Corrientes, Entre Ríos, northern Buenos Aires |
| 1 January pulse | 186 | 153,986 | January (60%) | 5 | 2016/17 (33%) | La Pampa, southern Mendoza, Río Negro; a few cells in central Chile |
| 2 Late summer | 354 | 342,087 | February (30%) | 6 | 2022/23 (16%) | Central-south Chile (Maule to Los Lagos), Andes of Neuquén and Chubut, north-east Corrientes and Misiones |
| 3 December pulse | 132 | 80,785 | December (52%) | 4 | 2016/17 (37%) | Southern La Pampa, Río Negro, southern Buenos Aires; Santiago and Valparaíso |

Seasons run July to June and are labelled by the year they start (as `season_year`).

**Regions with two or more regimes** (a second regime with at least 10% of the region's classified cells and at least 3 cells): 14 of 35.

| Country | Regions that mix regimes | Strongest mixes (share of the region's hotspots) |
|---|---|---|
| Argentina | Buenos Aires, Chubut, Corrientes, La Pampa, Mendoza, Neuquén, Río Negro, San Juan, Santa Cruz | La Pampa: January pulse 58%, December pulse 19%, winter-spring 14%. Río Negro: December 42%, winter-spring 22%, late summer 21%. Neuquén: late summer 45%, winter-spring 38%. Corrientes: winter-spring 74%, late summer 24%. |
| Chile | Metropolitana, Atacama, Valparaíso, O'Higgins, Maule | Maule: January pulse 53%, late summer 38%. Metropolitana: December pulse 51%, January pulse 43%. |

One regime only: Catamarca, Chaco, Córdoba, Entre Ríos, Formosa, Jujuy, La Rioja, Misiones, Salta, San Luis, Santa Fe, Santiago del Estero, Tucumán; Antofagasta, Aysén, Coquimbo, La Araucanía, Los Lagos, Los Ríos, Ñuble, Biobío.

**Stability.** Fitted again on 2012-2018 and 2019-2025, the regimes agree only moderately: adjusted Rand index 0.27 between the halves (1,894 cells with at least 50 hotspots in both), 0.68 and 0.30 against the full period. The winter-spring regime is stable; the small summer regimes move with the big seasons.

`cell_regimes.parquet`: 2,282 rows, columns `cell_lat`, `cell_lon` (south-west corner), `regime` (0-3), `peak_month` (1-12, the cell's own peak month, which can differ from its regime's), `hotspots_per_km2_year` (harmonized, 2012-2025). Names in `regime_names.csv`.

### 5.4 Sparse cells

Zero share: months with no harmonized hotspot among the 310 complete months, for cells with at least one hotspot. Reliable: the cell's peak month has a median of at least 10 harmonized hotspots over 2001-2025 (zeros included).

| Cell size | Width (about) | Cells with fire | Median zero share | Cells empty > 90% of months | Reliable cells | Hotspots in reliable cells |
|---|---|---|---|---|---|---|
| 0.25° | 23 km | 5,143 | 89.7% | 2,532 | 759 (14.8%) | 66.5% |
| 0.5° | 46 km | 1,468 | 72.4% | 491 | 368 (25.1%) | 82.2% |
| 1° | 91 km | 411 | 39.0% | 65 | 184 (44.8%) | 93.6% |

Reliable 0.25° cells are in northern Argentina between 25°S and 35°S (608), the Argentine 35-40°S band (82) and the Chilean centre-south (61 between 35°S and 45°S). South of 45°S and in northern Chile no cell size reaches the threshold.

### 5.3 Static sources

483 persistent 0.005° cells in the block 1 mask (removed by the quality filter, so they are not in the maps above). Most cells: Neuquén (141, probably oil and gas flares), Buenos Aires (73), Entre Ríos (43), Mendoza (26), Antofagasta (25). The ten cells with most days (2,600 to 3,800 days in 2012-2025) are near the Chagres smelter (Valparaíso), the El Teniente / Caletones smelter (O'Higgins), Calama and the Antofagasta coast, one site in Atacama, and the Paraná at San Nicolás and Villa Constitución (steel plants) and Ensenada (refinery). The site names are a reading of the coordinates, not checked against a list of facilities.

## Limits

- **The MODIS era is an estimate.** Its densities are MODIS counts scaled with the block 3 factors; the ratio map tests those factors only for spatial artefacts, not for the overall level.
- **Regimes come from 14 years of one satellite.** Two of the four are shaped by one season (2016/17). A longer record (adding the harmonized MODIS era) or event-based counts would be needed to tell a regime from an extreme year. Not done.
- **k-means treats months as 12 separate dimensions**: December and January are as far apart as June and January. A circular feature (sine and cosine of the month) was not tried.
- **Only monthly timing** was used: no land cover, no climate. The names describe timing, not ecosystems.
- **Cells with fewer than 100 hotspots** (2,862 of 5,144 cells, 2.4% of the 2012-2025 hotspots) have no regime.
- **The region of a cell** is the region holding most of its hotspots; border cells belong to one region only here.
- **Reliability uses the peak month only.** A cell can be reliable in its peak month and empty the rest of the year; the calendar should test each month.
- **The task's 312 months** were replaced by 310 complete months (see Decisions).
- **Data**: built on a download of 2026-11-14 that gives 7,000,575 kept hotspots instead of the 7,000,520 of the runbook (55 more, NRT rows FIRMS revised). `cells_daily.parquet` has the expected 1,020,967 rows. The difference is far below any number here.
