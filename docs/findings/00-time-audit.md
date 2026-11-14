# Block 0 findings: time audit

Source: `notebooks/00_time_audit.ipynb`, run on 2026-11-14 on the rebuilt table (8,042,380 rows,
2000-11-01 to 2026-11-14 13:37 UTC). Plan: `docs/eda-plan.md`, block 0.

## Decisions

| Decision | Value | Evidence |
|---|---|---|
| Day key | `burn_date` (06:00 to 06:00 local solar time). Confirmed. | 0 rows between 04:30 and 07:00 local solar time, for every satellite, year and latitude band |
| Calibration window | 2012-2021 | Terra and Aqua day passes are stable through 2021 and drift from 2022 (see 0.5) |
| Month and year | Derive from `burn_date` (`burn_month`, `burn_year`, `season_year`) | Cheap to do right; the choice moves monthly totals by less than 2% in 95% of months |
| Week | 52 fixed 7-day bins, as proposed in the plan | ISO weeks put 26,960 rows in a different year and 8,212 rows in a week 53 |

## What the table has now

`scripts/build_hotspots.py` adds, through `scripts/timefields.py`:
`solar_time_h`, `pass_slot`, `burn_date`, `burn_year`, `burn_month`, `season_year`, `tz_name`,
`utc_offset_min`, `local_wall_time`, `local_date`. `acq_date`, `year`, `month` and the `year=`
partition stay in UTC. The build fails if a detection is closer than 30 minutes to the 06:00 cut.

`season_year` is the year the July-June season starts: 2016 means July 2016 to June 2017.

## Results

### 0.1 The source is UTC

- `acq_time`: no missing values and no bad formats (range `0005` to `2356`).
- Local solar time peaks where the orbits say it should: Terra 9.5-10.5 h, Aqua and the three VIIRS
  satellites 13.5-14.5 h.

### 0.2 Rows that change day, month and year

| Satellite | Civil date differs from UTC date | `burn_date` differs from UTC date |
|---|---|---|
| Terra | 14.15% | 26.11% |
| Aqua | 0.00% | 8.19% |
| Suomi-NPP | 0.00% | 28.59% |
| NOAA-20 | 0.00% | 27.86% |
| NOAA-21 | 0.00% | 29.29% |

- Against UTC, the civil date moves 3,755 rows to another month and 386 to another year.
  `burn_date` moves 67,658 rows to another month, 6,257 to another year and 1,734 to another season.
- Civil midnight splits the Terra night pass. Argentina: 86,043 rows at 23 h and 63,529 at 00 h.
  Chile: 6,755 at 23 h and 16,812 at 00 h.
- Solar midnight splits the VIIRS night pass: 2.39% of VIIRS night rows fall before it.

### 0.3 The 06:00 cut

- No rows between 04:30 and 07:00 local solar time.
- **The margin is shrinking with the orbit drift.** The latest night detection before the cut was at
  about 2.2 h through 2022 and is at 4.27 h in 2026 (Aqua). The earliest day detection after the cut
  was at about 9.0 h and is at 7.49 h in 2026 (Terra). The cut is still more than an hour away on
  both sides, and MODIS ends in 2027, but the build guard must stay.

### 0.4 `pass_slot` against `daynight`

They agree except for 47 rows flagged `N` in the day pass (MODIS 24, VIIRS 23), all south of 35°S.
Use `pass_slot` for sensor comparisons.

### 0.5 Orbit drift

Median local solar time of the day pass:

| Satellite | Stable period | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| Terra | 10.2 h (2002-2021) | 10.02 | 9.81 | 9.51 | 9.10 | 8.64 |
| Aqua | 13.9 h (2002-2022) | 13.96 | 14.17 | 14.53 | 15.04 | 15.77 |
| Suomi-NPP | 13.8 h | 13.81 | 13.90 | 13.85 | 13.92 | 14.02 |
| NOAA-20 | 13.8 h | 13.83 | 13.82 | 13.84 | 13.83 | 13.97 |

The drift is the same in every latitude band. MODIS in 2023-2026 does not observe at the same hour
as MODIS in 2002-2021, so those years cannot be used to fit a MODIS to VIIRS factor.

### 0.6 Civil time

16 IANA zones: 12 in Argentina, 4 in Chile (Santiago, Coyhaique, Punta Arenas, Easter).
Observed offsets match the history of each zone (UTC-2 summers of 2007-2009, UTC-4 in western
provinces). Every region maps to a zone; an unknown region stops the build.

### 0.7 Coverage

| Satellite | First detection (UTC) | Last detection (UTC) |
|---|---|---|
| Terra | 2000-11-01 | 2026-11-14 |
| Aqua | 2002-07-04 | 2026-11-14 |
| Suomi-NPP | 2012-01-20 | 2026-11-02 04:23 (3 rows that day) |
| NOAA-20 | 2018-04-01 | 2026-11-14 |
| NOAA-21 | 2023-03-01 | 2026-11-14 |

Last complete UTC day: 2026-11-13. Last complete `burn_date`: 2026-11-12, because the night of the
13th was still arriving at download time. November 2026 is partial.

### 0.8 Calendars

- Calendar year and July-June season give very different totals for the same label
  (2020: 1,070,208 rows by calendar year, 892,308 by season). The app must say which one it shows.
- ISO weeks: 8,212 rows fall in a week 53 and 26,960 rows get an ISO year different from
  `burn_year`. With 52 fixed 7-day bins, 24,618 rows (0.3%) fall after day 364 and join bin 52.

### 0.9 Sensitivity to the day convention

- Monthly totals (months with at least 1,000 rows), `burn_date` against UTC: median difference 0%,
  95th percentile below 2%, extremes -8.5% and +6.0%.
- Ranking of years: 2 of 42 positions change, none in the top 5 of either sensor.
- Fire-days (0.25° cell × day, 2019-2021): counting by UTC or civil date instead of `burn_date`
  inflates VIIRS by 1.41% and changes MODIS by about 0.2%. The day key matters most for the metric
  that compares the two sensors.

## For other modules

- Count per day, month, year or season with the `burn_*` columns.
- Compare the current month with the same days of other years, and stop at `burn_date` 2026-11-12.
- On macOS, `scripts/download_firms_api.sh` needs GNU `date`: `brew install coreutils` and put
  `/opt/homebrew/opt/coreutils/libexec/gnubin` first in `PATH`.
