# Agent handoff: context and open tasks

For any coding agent that starts work on this repository with no earlier conversation. Written on
2026-11-14. Deadline of the hackathon: Sunday 2026-11-15, 12:00 (Chile time).

Read this file first. It tells you what exists, what is decided, and which tasks are open. Each task
is written so that one agent can take it without asking, and so that two agents do not edit the same
files.

## 1. The project in six lines

- NASA Space Apps 2026, challenge "Harmonization of MODIS and VIIRS Hot Spots". Brief: `challenge-brief.es.md`.
- Scope: Chile and Argentina, November 2000 to today.
- **Base case (what NASA asks):** one comparable series of fire hotspots from two sensors, shown in a
  web app as a burn calendar per area and period. It works on `main`.
- **Added value (ours):** a view of the current fire situation and a view of where fire activity is
  most likely next. A weekly outlook is in the app. A next-day outlook is not built.
- The exploratory analysis (EDA) is finished: 9 of 9 blocks ran. What is left are loose ends.
- The team decided to stop polishing the base case and move to the added value. Take only the
  tasks below; do not open new analysis.

## 2. Where things are

| You need | Read |
|---|---|
| How to build the data and run every notebook, with expected numbers | `docs/eda-runbook.md` |
| Every decision taken, in one list | `docs/eda-findings.md` |
| Results per block | `docs/findings/NN-*.md` (blocks 0 to 8, plus `03b` and the summary) |
| Loose ends with their reasons | `docs/eda-closing-plan.md` |
| Pull request rules and file ownership | `docs/work-split.md`, `CONTRIBUTING.md` |
| The web app | `backend/main.py` (FastAPI + DuckDB), `frontend/src/` (React + Vite + Leaflet + ECharts) |
| The pipeline | `scripts/build_hotspots.py`, `scripts/harmonize.py`, `scripts/risk_baseline.py`, `scripts/risk_model.py`, `scripts/risk_weather.py` |
| Tests | `tests/` (57 pass on `main`) |

Data is not in git. It lives under `NASA_Data_Sources/processed/` and each machine builds it with the
runbook (about 50 minutes and a FIRMS key), or receives the folder from a teammate.

| File under `NASA_Data_Sources/processed/` | Content |
|---|---|
| `hotspots/` | Every hotspot, both sensors, with time fields. 8,042,380 rows |
| `quality/quality_flags.parquet` | One row per hotspot with `keep` (quality filter of block 1) |
| `harmonized/hotspots_kept.parquet` | The hotspots that pass the filter. 7,000,520 rows. **Start here for any analysis** |
| `harmonized/cells_daily.parquet` | Harmonized hotspots per 0.25° cell and day. Sum `hotspots_harmonized`; never count rows |
| `risk/cells_weekly.parquet` | Probability of fire activity per cell and week |
| `spatial/cell_regimes.parquet`, `population/cells.parquet` | Fire regime and people per cell |

## 3. Rules you must follow

1. **Days are `burn_date`** (06:00 to 06:00 local solar time). Months and years are `burn_month` and
   `burn_year`. Never count by `acq_date`.
2. **Only rows that pass the quality filter.** Read `hotspots_kept.parquet`, or join the flags and
   keep `keep`.
3. **Never add satellites together.** One satellite per period: MODIS before 2012-02-01, Suomi-NPP
   until 2026-10-31, NOAA-20 after.
4. **Units are VIIRS-equivalent hotspots.** A hotspot is a detection, not a fire, not burned area.
5. **Never compare a partial period with a complete one.** The last complete `burn_date` is the
   newest one minus a day.
6. **No trend claims. No "we predict where a fire will start".** Say "where fire activity is most likely".
7. **Do not change the harmonization method.** Two studies checked it (`03-modis-vs-viirs.md`,
   `03b-pre2012-level.md`): factors per region, month and pass, fitted on 2012-2021, shrinkage 200.
8. Everything in the repository is in English. Commits follow Conventional Commits.
9. **Never push to `main`.** One branch and one pull request per task. Run `pytest` first. In the
   description say what changed, how you checked it, what you did not do.
10. **Wait for the audit comment before merging**, and read it. A merge before the audit put three
    defects on `main` on 2026-11-14.
11. Never commit data, `.env` or keys.
12. If a number from your run differs from the runbook or the findings, stop and report it. Do not
    work around it.

## 4. Open tasks

Take one. Say in the team chat which one. Tasks in the same lane touch the same files: one agent per
lane at a time.

| Task | Lane | Effort | Priority |
|---|---|---|---|
| T1 Merge pull request 21 | docs | 20 min | high |
| T2 Fill the Suomi-NPP outages | scripts | 45 min | high |
| T3 One anomaly definition in the app | app | 1 h | high |
| T4 Make notebook 06 run on every machine | notebooks | 10 min | high |
| T5 Tests for the risk scripts | scripts | 45 min | medium |
| T6 Re-run block 4 on harmonized data, fix notebooks 01 and 04 | notebooks | 1.25 h | medium |
| T7 Population and fire regime in the app | app | 1 h | medium |
| T8 Events: group hotspots into fires | scripts | 2 h | medium |
| T9 README pipeline section | docs | 15 min | low |

Everything else in `docs/eda-closing-plan.md` (items B2 to B5, B7 and all of priority C) is **not** to
be done now.

### T1. Merge pull request 21 (docs)

- **What:** pull request 21 (`feat/m3-pre2012-level`, by Vicente) adds a study of why the series is
  higher before 2012 and a summary of blocks 5 to 7. It conflicts with `main`.
- **Its conclusion:** keep the method. The drop after 2012 is in raw MODIS too (ratio 1.35), it sits
  in Salta and Santiago del Estero between July and November, and the factors do not cause it.
- **Steps:** merge `main` into the branch. Conflicts are in `docs/eda-runbook.md` (keep both sets of
  table rows), `docs/findings/eda-summary-and-harmonization.md` (keep the pull request's text; `main`
  only changed one sentence in the introduction and added a note in section 2.4, which the study now
  replaces) and `docs/findings/03-harmonization.png` (regenerate with `python scripts/harmonize.py`).
- **Done when:** the pull request is mergeable, `pytest` passes, the audit comment is in, it is merged.
- **Do not:** edit the study's numbers.

### T2. Fill the Suomi-NPP outages (scripts)

- **Problem:** Suomi-NPP did not report from 2022-07-26 to 2022-08-09. NOAA-20 recorded 7,715
  hotspots on those days; `cells_daily.parquet` has none. Five more outages in 2024 and 2026 (24 days).
  The outage list is `NASA_Data_Sources/processed/quality/outage_days.csv` (satellite, start, end).
- **Fix, in `scripts/harmonize.py`:** on a `burn_date` inside a Suomi-NPP outage, the series takes
  NOAA-20 rows instead (weight 1: NOAA-20 / Suomi-NPP is 0.93 to 1.03). The rule lives where
  `in_series` is defined. Outages before NOAA-20 existed (April 2018) and all MODIS outages have no
  substitute. A day without observation has no rows to flag, so write those days to
  `harmonized/outage_days_in_series.csv` (date, sensor in the series) for the app to mark the months.
- **Tests:** in `tests/test_harmonize.py`, a synthetic case with an outage day where NOAA-20 has rows.
- **Done when:** harmonized hotspots between 2022-07-26 and 2022-08-09 are close to 7,715 (they were
  0); VIIRS counts outside outage days are unchanged; `docs/findings/03-modis-vs-viirs.md`, the
  runbook's expected numbers and `docs/eda-findings.md` are updated; `pytest` passes.
- **Do not:** touch the factors. The calibration years 2012-2021 contain no Suomi-NPP outage.
- **After merging:** everyone re-runs `python scripts/harmonize.py`, then the risk scripts.

### T3. One anomaly definition in the app (app)

- **Problem:** the app computes `x / median` over all years, including the year being judged. The EDA
  decided otherwise (`docs/eda-findings.md`, "Calendar and anomalies"), and pull request 21 shows the
  cost: with an all-years median, 71% of recent months in Salta and Santiago del Estero look "below
  the median", against 46% with a reference from 2013 on. A median of 0 gives ratios above 500.
- **Fix, in `backend/main.py` (`/api/calendar`) and `frontend/src/App.tsx`:**
  1. Ratio = `(x + 1) / (median + 1)`.
  2. The reference of a month leaves out the year being judged.
  3. Reference years: 2013 to the last complete year by default; a parameter `reference=all` keeps
     the full record. Return the reference years in the response and show them next to the number.
  4. `reliable` = reference median of at least 10. When false, the calendar shows the count and no
     anomaly colour.
  5. Show the rank next to the ratio in the key figures.
- **Tests:** extend `tests/test_api.py`: ratio with a zero median, the leave-one-out reference, the
  default and the `all` reference, the `reliable` flag.
- **Done when:** tests pass, `npm run build` and `npm run lint` are clean, and you opened the app and
  checked a region (for example Salta) in both reference modes.
- **Do not:** change the count view or the CSV.

### T4. Make notebook 06 run on every machine (notebooks)

- **Problem:** `notebooks/06_case_studies.ipynb` fails on some machines with duckdb 2.0.0:
  `date_trunc('hour', acq_datetime)` on a nanosecond `TIMESTAMPTZ`.
- **Fix:** in the "pass by pass" query, group by `date_trunc('hour', acq_datetime::TIMESTAMP)`.
  Re-run the notebook; its tables must not change.
- **Done when:** it runs on a machine where it failed, and on one where it did not.

### T5. Tests for the risk scripts (scripts)

- **Problem:** `scripts/risk_model.py` and `scripts/risk_weather.py` have no tests. The leak checks of
  block 8 were made by reading the code.
- **Add `tests/test_risk_model.py`** on a small synthetic panel: `history_features` uses nothing from
  the scored week or later; `neighbour_ids` returns the 8 neighbours and -1 at the edge; the test
  years never enter training. **Add `tests/test_risk_weather.py`:** `weekly_features` windows end the
  day before the week starts; `days_since_rain` counts correctly; a missing POWER value becomes NaN.
- **Do not:** call the NASA POWER API in a test. Do not change the scripts unless a test finds a bug;
  if it does, report it in the pull request.

### T6. Re-run block 4 on harmonized data, fix notebooks 01 and 04 (notebooks)

- **Problem:** block 4 ran before the harmonized dataset existed, so its statistics are per sensor.
  Its section "When C2 exists" lists three re-runs. Notebooks 01 and 04 have four small defects
  listed in `docs/findings/eda-summary-and-harmonization.md`, section 5.
- **Owner:** Vicente wrote both notebooks. Ask before taking this one.
- **Done when:** `04_calendar.ipynb` reads `cells_daily.parquet`, `docs/findings/04-calendar.md` has
  harmonized numbers, the four defects are fixed, and both notebooks run top to bottom.

### T7. Population and fire regime in the app (app)

- **What:** show, for the selected area, the people living there (`population/cells.parquet`) and when
  that place usually burns (`spatial/cell_regimes.parquet`, names in `regime_names.csv`).
- **Fix:** two optional fields in `/api/calendar`, read like the risk layer is read (the app must work
  when the files are missing). One line in the key figures.
- **Wording:** "people living in the selected area", never "people affected".
- **Depends on:** nothing. Same lane as T3: do not run both at once.

### T8. Events: group hotspots into fires (scripts)

- **Why:** the challenge mentions "number of fires". A view of the current situation should say
  "N active fires", and every case study and exposure figure today uses boxes, not fires.
- **Sketch:** link hotspots closer than about 1 km whose `burn_date` differs by at most 1 day; each
  connected group is an event. `scipy.spatial.cKDTree` over a sliding window of days.
  Output `NASA_Data_Sources/processed/events/events.parquet`: event id, first and last `burn_date`,
  hotspots, centre, country, region.
- **Check on the nine cases** of `docs/findings/06-case-studies.md`: Valparaíso 2024 should be a
  few events, not hundreds; Puerto Patriada should separate from the small fire of 3 and 4 January.
- **Do not:** use it to change the harmonized counts.

### T9. README pipeline section (docs)

- `README.md` explains the pipeline only up to the hotspot table. Replace that part with a short
  section that points to `docs/eda-runbook.md`. Do not repeat the runbook.

## 5. The next phase, so that tasks point the right way

Three views. The EDA settles this much (details in `docs/eda-closing-plan.md`, section 4):

| View | State | What is known |
|---|---|---|
| Burn calendar | On `main` | Needs T2 and T3 to match the EDA |
| Current situation | Not built | Hotspots of the last passes (afternoon about 15:00 to 16:30, night about 02:00 to 04:00 civil time). `scripts/download_firms_api.sh` already fetches them and needs a schedule. It confirms and maps a fire; in the one case with an hour (Valparaíso 2024) the first detection came 2 hours 16 minutes after the fire started. T8 would let it count fires |
| Where activity is most likely next | Weekly outlook on `main`; next-day not built | Weekly: average precision 0.563 against 0.510 for the historical rate. Day to day: a cell with fire today has fire tomorrow 33% of the time (base rate 2.6%), and 65% of tomorrow's fire cells are in or next to today's. A next-day view will mostly show today's fires and their surroundings. Tomorrow's weather needs a forecast source: NASA POWER is three days behind |

## 6. Things that will trip you

- macOS: `scripts/download_firms_api.sh` needs GNU `date` (`brew install coreutils`); LightGBM needs
  `brew install libomp`.
- Do not run project scripts with `python -I`.
- `scripts/harmonize.py` rewrites `docs/findings/03-harmonization.png`. Commit it only when the
  numbers changed on purpose.
- A later download gives slightly different row counts (near-real-time months are revised):
  8,042,448 rows and 7,000,575 kept were seen the same day. `cells_daily.parquet` had the same rows.
- The quality flags come from a notebook (`01_quality.ipynb`). `harmonize.py` stops if they are
  missing or older than the hotspot table.
- Region names: use the ones in the hotspot table (40 regions). The raw boundary file of Chile has
  broken accents; `build_hotspots.fix_mojibake` repairs them.
- A squash merge of a stacked pull request leaves the next one in conflict. Do not stack; if you
  must, rebase the second one on `main` after the first merges, and never delete a branch whose pull
  request is still open.
