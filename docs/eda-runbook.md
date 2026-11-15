# EDA runbook: how to run everything, and where it stands

For team members and their coding agents. Last checked on 2026-11-14 on `main` at `c0f35d0`, with
Python 3.12 on macOS. Every command here was run on `main` that day, except notebook 07, which was
run by its author (it needs the WorldPop rasters).

Read this before `docs/eda-plan.md` (the plan) and `docs/findings/` (the results). Every decision in
one list: `docs/eda-findings.md`. Loose ends and how to close them: `docs/eda-closing-plan.md`.
Before training a prediction model: `docs/eda-conclusions-for-modeling.md`. The "Project
status" part of `CLAUDE.md` is older than this file: where they disagree, this file is right.

## Where the EDA stands

All 9 blocks are done. Each has open ends, listed below the table.

| Block | Topic | Status | Where |
|---|---|---|---|
| 0 | Time audit | **Done** | `notebooks/00_time_audit.ipynb`, `docs/findings/00-time-audit.md` |
| 1 | Integrity and quality | **Done** | `notebooks/01_quality.ipynb`, `docs/findings/01-quality.md` |
| 2 | Observation effort | **Done** | `notebooks/02_observation_effort.ipynb`, `docs/findings/02-observation-effort.md` |
| 3 | MODIS against VIIRS | **Done** | `notebooks/03_modis_vs_viirs.ipynb`, `docs/findings/03-modis-vs-viirs.md`, `scripts/harmonize.py` |
| 4 | Burn calendar | **Done, per sensor** | `notebooks/04_calendar.ipynb`, `docs/findings/04-calendar.md` |
| 5 | Spatial patterns | **Done** | `notebooks/05_spatial.ipynb`, `docs/findings/05-spatial.md` |
| 6 | Past fire cases | **Done** | `notebooks/06_case_studies.ipynb`, `docs/findings/06-case-studies.md` |
| 7 | Population (WorldPop) | **Done** | `notebooks/07_population.ipynb`, `docs/findings/07-population.md`, `processed/population/cells.parquet` |
| 8 | Risk model inputs | **Done** | `notebooks/08_risk_inputs.ipynb`, `docs/findings/08-risk-model.md`, `scripts/risk_baseline.py`, `scripts/risk_model.py`, `scripts/risk_weather.py` |

Open ends inside the done blocks:

- **Block 3:** matching of near-simultaneous detections (3.5), FRP (3.6), events (3.7) and quantile
  mapping were not done.
- **Block 4:** it ran before the harmonized dataset existed, so every statistic is per sensor. Its
  section "When C2 exists" lists the three re-runs that are still pending.
- **Block 5:** two of the four fire regimes are shaped by one season (2016/17). The recommendation of
  0.5° as the smallest cell for an anomaly calendar is not applied in the web app.
- **Block 6:** a case is a box or a set of regions, not an event. The Valparaíso timeline with
  sources and the check against the risk layer are on the branch `feat/m5-valparaiso-case`, not on `main`.
- **Block 7:** one population year (2024) for every fire year. The web app does not read
  `population/cells.parquet` yet.
- **Block 2:** the test with steady heat sources has 19 sites, all between 22°S and 40°S, and covers
  night passes only. External cloud data was not used.
- **Block 8:** the large-fire target was not defined, and `scripts/risk_model.py` and
  `scripts/risk_weather.py` have no tests. The week in progress has no weather features.

A summary of what the blocks mean for the harmonization, and what to test next:
`docs/findings/eda-summary-and-harmonization.md`.

## Pipeline, in order

Run from the repo root. Each step needs the ones above it. Data is git-ignored, so every laptop
builds its own copy.

| # | Command | Time (about) | Writes (under `NASA_Data_Sources/`) |
|---|---|---|---|
| 1 | `pip install -r requirements.txt` | | |
| 2 | `./scripts/download_firms.sh` | 5 min | `<SENSOR>/<Country>/*.csv`: 96 files, 585 MB |
| 3 | `./scripts/download_firms_api.sh` | 40 min | `<SENSOR>/API_bbox/*.csv`: 78 files |
| 4 | `./scripts/download_boundaries.sh` | 1 min | `boundaries/*.geojson`: 118 MB |
| 5 | `python scripts/build_hotspots.py` | 30 s | `processed/hotspots/`: 8,042,380 rows |
| 6 | `jupyter nbconvert --to notebook --execute --output-dir /tmp notebooks/01_quality.ipynb` | 3 min | `processed/quality/quality_flags.parquet`, `static_mask_cells.parquet`, `outage_days.csv` |
| 7 | `python scripts/harmonize.py` | 3 s | `processed/harmonized/hotspots_kept.parquet`, `cells_daily.parquet`, `factors.csv`, `outage_days_in_series.csv`, `validation_yearly.csv` |
| 8 | `python scripts/risk_baseline.py` | 3 s | `processed/risk/cells_weekly.parquet`, `baseline_eval.parquet`, `baseline_metrics.json` |
| 9 | `python scripts/risk_model.py --no-weather` | 10 s | `processed/risk/cells_weekly.parquet` (replaces step 8), `model_eval.parquet`, `model_metrics.json` |

Optional:

| Command | Time (about) | Purpose |
|---|---|---|
| `python scripts/risk_weather.py` | 2 h, resumable | NASA POWER weather for 1,466 points. Then run `python scripts/risk_model.py` without `--no-weather` (12 s): average precision 0.563 against 0.555 without weather. |
| `python scripts/risk_model.py --no-weather --out NASA_Data_Sources/processed/risk_no_weather` | 12 s | Second copy of the model output, needed by notebook 08 to compare with and without weather |
| `./scripts/download_population.sh` | not measured, 160 MB | WorldPop 2024 for Chile and Argentina, into `External_Data_Sources/WorldPop/`. Needed by notebook 07. No account. |

What each step needs:

- Step 3 needs `FIRMS_MAP_KEY` in `.env` (copy `.env.example`). Never commit `.env`.
- Step 3 on macOS needs GNU `date`: `brew install coreutils`, then
  `export PATH="/opt/homebrew/opt/coreutils/libexec/gnubin:$PATH"`.
- Step 6 also tries to download January 2019 through the FIRMS API as a cross-check. Without a key it
  prints `skipped` and continues.
- Step 9 on macOS needs `brew install libomp`.
- Do not run project scripts with `python -I`.

### Expected numbers

If your run gives different numbers, stop and find out why before analysing anything.

| After step | Check |
|---|---|
| 5 | `Wrote 8,042,380 rows`; 3 exact duplicates dropped; 1,149,423 API rows dropped as outside both countries |
| 6 | `quality_flags.parquet` has 8,042,380 rows; 7,000,520 with `keep` (12.95% removed) |
| 7 | `7,000,520 hotspots pass the quality filter`; `1,026,554 cell-day rows`; `raw 3,833,709 -> harmonized 6,026,318 hotspots`; `91 outage days in the series, 39 filled with NOAA-20`; 949 factors |
| 8 | `Wrote 2,689,584 rows`; 9 weeks not observed because of outages |
| 9 | `Model beats baseline on 2023-2025: YES` (average precision 0.555 against 0.510) |

The download date changes the first two rows: the recent months are near-real-time data that FIRMS
keeps revising. The numbers above are for data downloaded on 2026-11-14. A download later the same
day gave 8,042,448 rows and 7,000,575 kept (68 and 55 more); `cells_daily.parquet` had the same
number of rows with both downloads (1,020,967, counted before the Suomi-NPP outage days were filled).

## Running the analysis notebooks

Each notebook runs top to bottom. This command executes one without changing the file in git:

```bash
jupyter nbconvert --to notebook --execute --output-dir /tmp notebooks/00_time_audit.ipynb
```

| Notebook | Needs step | Time (about) | Also writes |
|---|---|---|---|
| `00_time_audit.ipynb` | 5 | 4 s | |
| `01_quality.ipynb` | 5 | 3 min | The quality files (it is pipeline step 6) |
| `03_modis_vs_viirs.ipynb` | 7 | 15 s | |
| `03b_pre2012_level.ipynb` | 7 | 2 min | `docs/findings/03b-pre2012-level.png` |
| `04_calendar.ipynb` | 6 | 30 s | `processed/calendar/monthly_by_region.parquet` |
| `05_spatial.ipynb` | 7 | 35 s | `processed/spatial/cell_regimes.parquet`, `regime_names.csv` |
| `06_case_studies.ipynb` | 7 | 5 s | `docs/findings/06-valparaiso-2024.png` |
| `07_population.ipynb` | 7 and the WorldPop download | 40 s | `processed/population/cells.parquet`, `docs/findings/07-population-density-classes.png` |
| `02_observation_effort.ipynb` | 6 | 15 s | `docs/findings/02-witness-rate.png` |
| `08_risk_inputs.ipynb` | 9, with and without weather (see Optional) | 5 s | `docs/findings/08-calibration.png` |

To change a notebook you own, edit it in Jupyter, run it top to bottom, and commit it with its
outputs: the outputs are the evidence.

## Which table to read

| You need | Read | Why |
|---|---|---|
| Any analysis of fire activity | `processed/harmonized/hotspots_kept.parquet` | One row per hotspot that passes the quality filter, with the region corrected. Same columns as the hotspot table. |
| Harmonized counts (MODIS and VIIRS on one scale) | `processed/harmonized/cells_daily.parquet` | Sum `hotspots_harmonized`. Never count rows: a cell on a region border has one row per region. |
| When each place burns | `processed/spatial/cell_regimes.parquet` | One row per cell with at least 100 hotspots in 2012-2025: fire regime (0 to 3), peak month, hotspots per km² per year. Names in `regime_names.csv`. |
| People living in a cell | `processed/population/cells.parquet` | `population_2024` and `people_per_km2` per 0.25° cell. Chile is rescaled to its 2024 census. |
| Data quality questions, or rows the filter drops | `processed/hotspots/` joined with `processed/quality/quality_flags.parquet` | Join on `satellite, acq_datetime, latitude, longitude`. Check that no row is left without a flag. |
| Risk per cell and week | `processed/risk/cells_weekly.parquet` | `probability` is the model where it was tested out of sample, the baseline elsewhere. |

With DuckDB:

```python
import duckdb
con = duckdb.connect()
con.execute("SET TimeZone='UTC'")
df = con.execute("""
    SELECT burn_year, burn_month, count(*) AS hotspots
    FROM read_parquet('NASA_Data_Sources/processed/harmonized/hotspots_kept.parquet')
    WHERE instrument = 'VIIRS' AND satellite = 'Suomi-NPP'
    GROUP BY ALL ORDER BY ALL
""").df()
```

## Rules every block follows

| Rule | Value | Decided in |
|---|---|---|
| Day key | `burn_date`: 06:00 to 06:00 local solar time. Month, year and season come from `burn_month`, `burn_year`, `season_year`. Never use `acq_date` for counting. | Block 0 |
| Week | 52 fixed 7-day bins; 29 February joins 28 February; the last bin has 8 days | Block 0, `scripts/risk_baseline.py` |
| Rows | `keep` from the quality flags: no low confidence, no static heat sources, no volcano or offshore rows | Block 1 |
| Outside the analysis | Easter Island and Malvinas/Falklands | Block 1 |
| Units | VIIRS-equivalent hotspots | Block 3 |
| Harmonization | Factor per region, calendar month and pass, fitted on 2012-2021 | Block 3 |
| One sensor per period | MODIS before 2012-02-01, Suomi-NPP until 2026-10-31, NOAA-20 after. On the 39 days of a Suomi-NPP outage, NOAA-20 instead of Suomi-NPP | Block 3 |
| Sensor comparisons | Use `pass_slot`, not `daynight`; compare one satellite with one satellite | Blocks 0 and 3 |
| Partial periods | Last complete `burn_date`: 2026-11-12. Compare the current month with the same days (1 to N) of other years. | Blocks 0 and 4 |
| Provisional data | `processing = 'NRT'`: August 2026 onward for VIIRS, September 2026 onward for MODIS | Block 1 |
| Trends | No trend claim: the sign depends on the window | Block 4 |
| Risk wording | Probability of fire activity per cell and week. Never "predicts where a fire will start". | `docs/data-contracts.md` |

Two points where the documents disagree and nobody has decided:

- **Season label.** `season_year` in the table is the year the July-June season starts (2016 = July
  2016 to June 2017). `docs/findings/04-calendar.md` labels a season by the year it ends.
- **Anomaly ratio.** Block 4 defines `(x + 1) / (median + 1)` with a reliability threshold of 10 rows.
  The web app uses `x / median` with no threshold.

## Adding a block

1. Take a block from the table at the top and say so to the team.
2. Branch from `main`: `feat/<module>-<block>`. Never push to `main`.
3. One notebook: `notebooks/<NN>_<name>.ipynb`. Start from `hotspots_kept.parquet`.
4. One findings file: `docs/findings/<NN>-<name>.md`, with a "Decisions" table first, then results,
   then limits. State what was not done.
5. Derived tables go under `NASA_Data_Sources/processed/<name>/` and stay out of git.
6. `pytest` must pass (57 tests today). Add tests for any logic that goes into `scripts/`.
7. Open a pull request. In the description: what changed, how it was checked, and every decision
   that affects another module. Wait for the audit comment before merging.

Columns of the files that pass between modules: `docs/data-contracts.md`. Pull request rules: `CONTRIBUTING.md`.

## Web app

```bash
cd frontend && npm install && npm run build && cd ..
uvicorn backend.main:app --port 8000
```

It needs steps 1 to 7. The risk outlook on the map appears when step 9 has run. Details in `README.md`.
