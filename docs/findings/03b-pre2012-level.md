# 3b. Why the harmonized series is higher before 2012

Notebook: `notebooks/03b_pre2012_level.ipynb`. Figure: `docs/findings/03b-pre2012-level.png`.
Input: `processed/harmonized/hotspots_kept.parquet` (pipeline step 7, data downloaded on 2026-11-14).
This study follows up on item 1 of section 4 in `docs/findings/eda-summary-and-harmonization.md`.

The question: the harmonized series averages 273,820 VIIRS-equivalent hotspots a year in 2001-2011 and
203,561 in 2013-2025, a ratio of **1.35**. Is that higher level real fire activity, or an artefact of the
factors, the MODIS collections, old static sources or Terra-only years?

Statements marked **(inference)** are interpretation, not something the data proves.

## Decisions (proposed, for the team to confirm)

| Topic | Proposal | Why |
|---|---|---|
| Harmonization method | Keep it as it is (region × month × pass, 2012-2021, `K = 200`) | The level difference does not come from the factors (sections 1 to 3) |
| Shrinkage | Keep `K >= 50`; never use the raw regional ratio (`K = 0`) | `K = 0` moves the level up to 1.46; with any `K >= 50` it stays between 1.34 and 1.38 |
| Reference median in the app | Say which years the median uses. Consider 2013 onward (VIIRS only) as the default, or let the user pick | With all years, 71% of recent region-months in Salta and Santiago del Estero look "below the median" (section 6) |
| Trend claims | No change: still no trend claim | The level difference is real in the data, but its cause is not proven, and the window issue of block 4.7 remains |

## 1. The factors are not the cause: MODIS alone shows the same drop

No factor applied. Mean per year, kept rows, Terra + Aqua:

| Unit | 2003-11 / 2013-17 | 2003-11 / 2013-21 |
|---|---|---|
| Rows | 1.51 | 1.35 |
| Fire-days (0.25° cell-day) | 1.49 | 1.33 |

The harmonized series over the same windows gives 1.355 (rows) and 1.327 (fire-days). It is the same
ratio: the factors are nearly constant in time and only change the unit. They do not create the level
difference.

The VIIRS / MODIS ratio is stable from year to year in the calibration period, which is what backward
extrapolation needs:

| 2013-2021 | Coefficient of variation | Slope (% of mean per year) |
|---|---|---|
| Rows (2.93 to 3.40) | 4.4% | -0.25 |
| Fire-days (1.82 to 2.07) | 4.5% | -0.96 |

This cannot be checked before 2012, when VIIRS did not exist. It only shows that nothing in 2013-2021
suggests the ratio drifts.

## 2. Terra only and Aqua only give the same history

Each satellite fitted on its own factors (2012-2021, `K = 200`) and applied to 2003-2011:

| Year | 2003 | 2004 | 2005 | 2006 | 2007 | 2008 | 2009 | 2010 | 2011 |
|---|---|---|---|---|---|---|---|---|---|
| Terra / Aqua, rows | 0.93 | 1.00 | 1.04 | 1.01 | 1.01 | 1.03 | 1.00 | 0.97 | 1.01 |
| Terra / Aqua, fire-days | 0.90 | 0.97 | 0.99 | 1.02 | 0.97 | 1.07 | 1.06 | 0.95 | 1.01 |

Level 2003-11 / 2013-25: Terra 1.38, Aqua 1.39, both together 1.37 (rows). Fire-days: 1.38, 1.39, 1.36.
The morning and the afternoon instrument agree within 7% every year (4% or less from 2004). So the
factors are not specific to one satellite or one pass time.

Limit: both use the same VIIRS reference and the same assumption that the ratio holds before 2012.
Their agreement rules out a satellite-specific problem. It does not prove the assumption.

## 3. The level barely moves with the window, `K` or the unit

Level 2001-11 / 2013-25:

| Window | Rows, K=0 | K=50 | K=200 | K=1000 | Country only | Fire-days, K=200 |
|---|---|---|---|---|---|---|
| 2012-2021 (current) | 1.37 | 1.35 | **1.35** | 1.35 | 1.37 | 1.30 |
| 2012-2014 | 1.46 | 1.35 | 1.34 | 1.34 | 1.34 | 1.35 |
| 2012-2016 | 1.43 | 1.35 | 1.34 | 1.35 | 1.36 | 1.34 |
| 2013-2019 | 1.40 | 1.36 | 1.35 | 1.35 | 1.36 | 1.33 |
| 2017-2021 | 1.38 | 1.35 | 1.35 | 1.36 | 1.38 | 1.27 |
| 2019-2021 | 1.41 | 1.35 | 1.35 | 1.36 | 1.38 | 1.26 |
| 2012-2025 (crosses the drift) | 1.38 | 1.36 | 1.36 | 1.36 | 1.38 | 1.30 |

- With `K >= 50`, every window gives 1.34 to 1.38 in rows and 1.26 to 1.38 in fire-days.
- Only `K = 0` (each region's raw ratio, noisy in small regions) moves it up to 1.46.
- The level holds with medians instead of means (1.47) and without 2020 (1.47), so one extreme VIIRS year
  does not explain it.
- No hotspot-month needed a fallback factor in any run.

## 4. Collections and old static sources are not the cause

- **Collections.** MODIS 2003-2011 against 2013-2017 is the same collection (6.2, used for 2000-2017)
  with stable orbits. The raw drop there is 1.51, larger than the 1.35 against 2013-2021. A collection
  change cannot explain a drop that happens inside one collection.
- **Static sources that stopped before 2012.** The block 1 mask only knows sources seen by VIIRS in
  2012-2025. Kept MODIS rows in persistent 0.01° cells, using the same rules in two 9-year windows:

  | Rule | 2003-2011 | 2013-2021 |
  |---|---|---|
  | ≥15 days, ≥6 months, ≥4 years | 0.99% of rows (181 cells) | 2.28% (236 cells) |
  | ≥20 days, ≥6 months, ≥5 years | 0.82% (112) | 2.19% (203) |
  | ≥30 days, ≥8 months, ≥5 years | 0.07% (8) | 0.83% (48) |

  Persistent cells are a smaller share before 2012, not a larger one. Unmasked old sources cannot add
  more than about 1% to the early period, far from the 35% gap.
- **Terra-only years (2001 to mid-2002).** The level is the same when they are left out: 1.37 for
  2003-11 against 2013-25.

## 5. Where and when the higher level is

Excess = mean harmonized hotspots per year, 2003-2011 minus 2013-2025: 278,883 - 203,561 = 75,322.

| Region | 2003-11 | 2013-25 | Ratio | Share of the excess |
|---|---|---|---|---|
| Santiago del Estero | 43,606 | 16,990 | 2.57 | 35% |
| Salta | 37,142 | 14,750 | 2.52 | 30% |
| Chaco | 28,193 | 17,731 | 1.59 | 14% |
| Entre Ríos | 13,855 | 8,907 | 1.56 | 7% |
| Misiones | 9,459 | 5,131 | 1.84 | 6% |
| Formosa | 24,757 | 27,614 | 0.90 | -4% |
| La Pampa | 4,396 | 6,560 | 0.67 | -3% |
| Río Negro | 2,456 | 4,493 | 0.55 | -3% |

- **Two regions hold 65% of the excess,** and 79% with Chaco: the dry Chaco of northern Argentina.
- **Argentina: 1.44. Chile: 0.78.** Chile is *higher* after 2012 (Bío-Bío, Maule, Ñuble, La Araucanía
  all below 1).
- **July to November hold 100% of the excess** (September alone 32%). January and February are higher
  after 2012 (ratios 0.56 and 0.70), which is the Chilean summer season.

The decline shows up **inside each sensor**, in raw counts:

| | 2011 | 2012 | 2013 | 2014 | 2015 |
|---|---|---|---|---|---|
| Salta, MODIS | 10,597 | 7,937 | 10,414 | **3,873** | 3,451 |
| Salta, VIIRS | | 23,362* | 42,803 | **10,639** | 9,989 |
| Santiago del Estero, MODIS | 13,250 | **6,700** | 7,827 | 4,045 | 4,689 |

\* 2012 VIIRS starts in late January.

In Salta both sensors fall by about three quarters between 2013 and 2014, two years after the switch.
In Santiago del Estero MODIS halves from 2011 to 2012 on its own. Raw MODIS 2003-11 / 2013-21 is 2.34 in
Salta and 2.23 in Santiago del Estero, the same as the harmonized ratios.

## 6. Effect on the reference median of the app

Median monthly count, Argentina, all years 2001-2025 against VIIRS years 2013-2025: 1.76 times higher
in July, 1.20 to 1.39 in most other months. In Chile the all-years median is lower in summer and
October-November (0.69 to 0.86).

Share of 2013-2025 region-months below the reference (region-months with a VIIRS median of 10 or more):

| Reference | Regions | Below the median | Below half the median |
|---|---|---|---|
| 2001-2025 | All | 48.8% | 20.1% |
| 2013-2025 | All | 45.6% | 17.2% |
| 2001-2025 | Salta + Santiago del Estero | **71.2%** | **34.0%** |
| 2013-2025 | Salta + Santiago del Estero | 46.2% | 11.9% |

Across all regions the effect is small. In the regions that hold the excess, an all-years median makes a
normal recent month look low most of the time.

## 7. What this means

- The 1.35 difference is **in the MODIS record itself**: it appears without factors, in both satellites,
  inside one MODIS collection, and in Salta inside VIIRS too. The harmonization neither creates it nor
  removes it. Explanations 2 (factors), 3 (collections), 4 (old static sources) and 5 (Terra-only years)
  of the original list are not supported as the main cause.
- The most likely reading is **a real drop in fire activity in the dry Chaco of Argentina**, mainly in
  the winter-spring burning season, after about 2012-2014. **(inference)** It fits land clearing with
  fire in Salta and Santiago del Estero in the 2000s. The Native Forest Law (Law 26.331, 2007) is one
  candidate cause but was not tested here. **(inference, not checked)**
- What is still not excluded: a change shared by both MODIS instruments that affects only some regions
  around 2012. That seems unlikely, but this study cannot rule it out without independent data.

## 8. Limits and what was not done

- **No independent data.** Every check uses FIRMS hotspots. Burned area MCD64A1 shares MODIS input, so it
  would not be independent either. Deforestation maps for the dry Chaco (for example Hansen / Global
  Forest Watch tree cover loss, or the national native forest monitoring) are the natural next check
  for section 7. Not done.
- The stability of the VIIRS / MODIS ratio is tested only inside 2013-2021. Before 2012 it is assumed.
- Fire-days are counted per 0.25° cell, day and region, without the pass split (a cell-day can have
  both passes).
- The static-source rules for MODIS are ad hoc thresholds, not checked against `fire_type` labels the
  way block 1 did for VIIRS.
- 2012 is left out of every level ratio (a mixed MODIS/VIIRS year).
- The function in the notebook re-implements `scripts/harmonize.py` in order to change its parameters.
  It matches `cells_daily.parquet` within 0.031% per year (VIIRS years exactly), but it is a second copy
  of the method. If the method changes, update both.
