# Open tasks: block 5 (Felipe) and block 7 (Luciano)

> **Both tasks are done and merged** (pull requests 16 and 15). Results: `docs/findings/05-spatial.md`
> and `docs/findings/07-population.md`. This file is kept as the record of what was asked.
> For the current state of the EDA, read `docs/eda-runbook.md`.

Written on 2026-11-14 for Felipe, Luciano and their coding agents. Two independent EDA blocks that
nobody has started. They touch different files, so they can run at the same time.

Read `docs/eda-runbook.md` first: it has the pipeline, the rules every block follows and the state
of the other blocks. The plan of each block is in `docs/eda-plan.md`.

| Task | Owner | Block | Result |
|---|---|---|---|
| Spatial patterns | Felipe | 5 | Where it burns, when each place burns, and how fine the map can be |
| Population and exposure | Luciano | 7 | How many people live where it burns |

Time box: about 3 hours each. Each task says what is the minimum and what to skip if time runs out.

## Prerequisites for both

1. **Code.** `git pull origin main`, then `pip install -r requirements.txt` in Python 3.12.
2. **Data.** Both tasks start from two files that are not in git:

   | File | Size | Content |
   |---|---|---|
   | `NASA_Data_Sources/processed/harmonized/hotspots_kept.parquet` | 152 MB | One row per hotspot that passes the quality filter |
   | `NASA_Data_Sources/processed/harmonized/cells_daily.parquet` | 3 MB | Harmonized hotspots per 0.25° cell and day |

   Two ways to get them:
   - **Fast:** ask Sebastian to share the folder `NASA_Data_Sources/processed/harmonized/` and copy
     it to the same path in your checkout.
   - **From scratch:** steps 2 to 7 of the pipeline in `docs/eda-runbook.md` (about 50 minutes, needs a
     FIRMS key in `.env`).
3. **Check the data** before starting. This must print `7000520` and `1020967`:

   ```bash
   python -c "import duckdb; d='NASA_Data_Sources/processed/harmonized/'; print(duckdb.sql(f\"SELECT count(*) FROM '{d}hotspots_kept.parquet'\").fetchall()[0][0], duckdb.sql(f\"SELECT count(*) FROM '{d}cells_daily.parquet'\").fetchall()[0][0])"
   ```

4. **Branch.** One branch per task from `main`: `feat/m4-spatial` (Felipe), `feat/m5-population`
   (Luciano). Never push to `main`.

Rules that apply to everything you compute (details in the runbook):

- Days, months and years come from `burn_date`, `burn_month`, `burn_year`. Never from `acq_date`.
- Harmonized counts are the **sum of `hotspots_harmonized`** in `cells_daily.parquet`. Never count rows.
- A cell is identified by its south-west corner: `cell_lat = floor(latitude * 4) / 4`, same for longitude.
- Compare one satellite with one satellite. For VIIRS use `satellite = 'Suomi-NPP'` (2012 to October 2026).
- Hotspots are detections, not fires, and not burned area.

## Task 1 (Felipe): block 5, spatial patterns

### Why

The harmonization works per administrative region, and the app colours one map for two countries.
We do not know yet whether regions are the right unit, how the fire season differs from place to
place, or how small an area can be before the calendar is mostly zeros.

### Extra prerequisites

- `pip install scikit-learn` and add `scikit-learn` as the last line of `requirements.txt`.
- For 5.3 only: `NASA_Data_Sources/processed/quality/static_mask_cells.parquet` (7 KB; ask Sebastian
  for it, or run pipeline step 6).
- Optional, to draw borders on the maps: `./scripts/download_boundaries.sh` (118 MB, no key).

### Steps

Work in `notebooks/05_spatial.ipynb`. Use DuckDB to aggregate and matplotlib to draw.

1. **Density map (5.1).** Harmonized hotspots per cell and year, per km². A 0.25° cell is not the same
   size everywhere: `area_km2 = (0.25 * 111.32) ** 2 * cos(radians(cell_lat + 0.125))`. It loses about
   40% of its area between 20°S and 55°S, so a map of raw counts favours the north.
   Draw three maps: 2001-2011 (MODIS era, estimated), 2012-2025 (VIIRS era), and their ratio.
   The ratio map is a check of the harmonization: it should show changes in fire, not the outline of a region.
2. **Fire regimes (5.2).** For each cell with at least 100 harmonized hotspots in 2012-2025, compute
   the share of its hotspots in each of the 12 calendar months. Cluster those 12-number profiles
   with k-means; try 4, 5 and 6 groups. Map the groups and describe each one: peak month, how many
   months hold 80% of the fire. Then compare with the administrative regions: which regions contain
   two or more groups?
3. **Sparse cells (5.4).** For each cell, the share of the 312 months (2001-2026) with zero hotspots.
   Repeat with cells of 0.5° and 1°. Report, for each cell size, how many cells have a historical
   median of at least 10 hotspots in their peak month (the reliability threshold of block 4).
4. **Static sources (5.3), only if time allows.** Map the cells of `static_mask_cells.parquet` and
   list the ten cells with most days of detections, with their region.

### Deliverables

- `notebooks/05_spatial.ipynb`, run top to bottom, committed with outputs.
- `docs/findings/05-spatial.md`: a "Decisions" table first, then results, then limits. The decisions
  to make: the number of fire regimes and their names, and the smallest cell size the app should offer.
- `NASA_Data_Sources/processed/spatial/cell_regimes.parquet` (not in git) with the columns
  `cell_lat`, `cell_lon`, `regime`, `peak_month`, `hotspots_per_km2_year`.
- The line of block 5 in the status table of `docs/eda-runbook.md` changed to done.

### Done when

- Steps 1 to 3 are in the notebook and the findings file.
- The findings file answers: how many regimes, which regions mix regimes, what is the smallest
  usable cell size.
- The pull request is open.

### If time runs out

Skip step 4, then step 3 at 0.5° and 1°. Steps 1 and 2 are the minimum.

## Task 2 (Luciano): block 7, population and exposure

### Why

Valparaíso 2024 burned a small area and killed 138 people; February 2023 burned fifty times more
and killed 25. Hotspots alone cannot tell those apart. Population per cell lets the app and the pitch
say how many people live where the fire activity is.

### Extra prerequisites

- `pip install rasterio pyproj` and add both as the last lines of `requirements.txt`.
- WorldPop 2024, no account needed, 160 MB in total:

  ```bash
  ./scripts/download_population.sh
  ```

  It writes `External_Data_Sources/WorldPop/Chile/chl_pop_2024_CN_100m_R2025A_v1.tif` (62 MB) and
  `.../Argentina/arg_pop_2024_CN_100m_R2025A_v1.tif` (98 MB). The folder is git-ignored.

### Steps

Work in `notebooks/07_population.ipynb`.

1. **Check the rasters (7.1).** Print the coordinate system, pixel size, no-data value and shape of each
   file. Sum all valid pixels per country and compare with the latest census (Chile 2024, Argentina
   2022). Take the census totals from INE and INDEC and cite them. If the totals differ by more than
   5%, stop and find out why (usual cause: the no-data value was summed).
2. **Population per cell (7.2).** Aggregate to the 0.25° grid by **summing** the pixels of each cell.
   Never average and never resample with interpolation: both lose people. Read the raster in windows
   (`rasterio` blocks) instead of loading it whole. Check that the sum over all cells equals the
   total of step 1.
3. **Fire activity against population (7.5).** Join with `cells_daily.parquet`. Put the cells in four
   classes by people per km² (same cell area formula as task 1: `(0.25 * 111.32) ** 2 *
   cos(radians(cell_lat + 0.125))`): under 1, 1 to 10, 10 to 100, over 100. For each class report the
   number of cells, the people, and the harmonized hotspots in 2012-2025.
4. **Validate with two cases (7.6).** People living in the cells with fire, on the peak days:
   - Valparaíso, `burn_date` 2024-02-02 and 2024-02-03, box west -71.70, south -33.25, east -71.30, north -32.95.
   - Ñuble, Biobío and La Araucanía, `burn_date` 2023-02-03.
   The expected picture is far fewer hotspots and far more people for Valparaíso. Hotspot numbers for
   both cases are in `docs/findings/06-case-studies.md` (pull request 14).
5. **Population within 1, 5 and 10 km (7.4), only if time allows.** Needs distances in metres: one
   degree of longitude is 96 km at 30°S and 64 km at 55°S.

### Deliverables

- `notebooks/07_population.ipynb`, run top to bottom, committed with outputs.
- `docs/findings/07-population.md`: a "Decisions" table first, then results, then limits.
- `NASA_Data_Sources/processed/population/cells.parquet` (not in git) with the columns `cell_lat`,
  `cell_lon`, `population_2024`, `people_per_km2`. This is what the web app will read to show the
  people living in the selected area.
- The line of block 7 in the status table of `docs/eda-runbook.md` changed to done.

### Limits to write down, whatever the results

- Exposure is not damage: the numbers say who lives near fire activity, not who is affected.
- WorldPop models residents. Tourists and seasonal workers are not counted.
- One population year (2024) is used for every fire year. WorldPop starts in 2015, so earlier years
  have no matching population (7.3 of the plan): state it, do not fix it.
- A 0.25° cell is about 25 km wide: everyone in the cell counts as exposed, which overstates it.

### Done when

- Steps 1 to 4 are in the notebook and the findings file.
- The country totals match the censuses within 5%, and the grid total matches the raster total.
- The pull request is open.

### If time runs out

Skip step 5, then step 3. Steps 1, 2 and 4 are the minimum.

## Both tasks: how to hand in

1. Run the notebook top to bottom one last time and commit it with its outputs.
2. `pytest` must pass (57 tests). Neither task adds code under `scripts/`, so no new tests are needed.
3. Commits in English, Conventional Commits: `feat: add block 5 spatial patterns`.
4. Open a pull request against `main`. In the description: what changed, how it was checked, the
   decisions that affect other modules, and what was not done.
5. Wait for the audit comment before merging.
6. Edit only your own files (`notebooks/05_*`, `docs/findings/05-*` for Felipe; `notebooks/07_*`,
   `docs/findings/07-*` for Luciano), plus one line in `requirements.txt` and one line in the runbook.

If something in the data does not match this document, stop and ask in the team chat before working around it.
