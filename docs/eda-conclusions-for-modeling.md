# EDA conclusions for the prediction model

What the exploratory analysis settles before training a model that says where fire activity is most
likely next. Written on 2026-11-14. Self-contained: an agent can start from this file.

Sources: `docs/findings/` (blocks 0 to 8), `docs/eda-findings.md` (every decision), and the scripts
`scripts/risk_baseline.py`, `scripts/risk_model.py`, `scripts/risk_weather.py`, which already
implement the weekly version of everything below.

## 1. What to predict, and what not to

| Target | Definition | State |
|---|---|---|
| Weekly outlook | At least one VIIRS hotspot in a 0.25° cell during a 7-day week | Built, in the app |
| Next-day outlook | At least one VIIRS hotspot in a 0.25° cell on `burn_date` D+1, with data through D | Not built: this is the model to train |

Not possible with this data, and not to be claimed:

- **Where a fire will start.** Most fires are started by people; a hotspot appears after the fire exists.
- **How severe a fire will be.** In the week of the Valparaíso fire of 2024 the model gave 0.48 to
  the cell where it ran: high, and no different from an ordinary summer week.
- **Burned area or damage.** A hotspot is a thermal detection in a pixel.
- **A large-fire target.** It needs hotspots grouped into events, which was not done.

Wording for anything shown to users: "where fire activity is most likely".

## 2. The data to train on

Everything is under `NASA_Data_Sources/processed/` (not in git; build it with `docs/eda-runbook.md`).

| File | Use | Size |
|---|---|---|
| `harmonized/hotspots_kept.parquet` | Hotspots that pass the quality filter. Source of the target and of every fire feature | 7,000,520 rows, 152 MB |
| `quality/outage_days.csv` | Days a satellite did not report. Those days are "not observed", never "no fire" | 19 runs |
| `weather/weekly.parquet`, `weather/power_daily/` | NASA POWER weather: 1,466 points (one per 0.5° block), daily from September 2011 | 38 MB weekly; 1,466 daily CSV files |
| `population/cells.parquet` | People per cell (2024). A proxy for human ignitions | 6,149 cells |
| `spatial/cell_regimes.parquet` | Fire regime and peak month per cell | 2,282 cells |

Rules that the training data must follow (each one comes from a block of the EDA):

1. **Day key:** `burn_date`, the day from 06:00 to 06:00 local solar time. It keeps an afternoon and
   the night that follows in the same day. Counting by civil date moves the peak of a fire to the
   wrong day (Valparaíso: 923 hotspots on burn date 2 February, split in two by civil date).
2. **One satellite at a time.** The target uses Suomi-NPP from 2012-02-01 to 2026-10-31 and NOAA-20
   after. Satellites with detections per day go from 1 (2001) to 5 (2025): a target that adds
   satellites learns the number of satellites.
3. **VIIRS only.** MODIS reports a steady heat source on 2 to 4% of nights, VIIRS on about 50%. Do
   not train on the MODIS era, and do not use harmonized counts as a target.
4. **Quality filter on.** No low-confidence rows, no static heat sources, no Easter Island or Malvinas.
5. **Outage days are missing data.** Suomi-NPP was out for 15 days in 2022 and 24 days in 2024 and 2026.
6. **2026 from August on is provisional** (near-real-time data that FIRMS will revise). Do not test on it.

Size of the problem at 0.25°:

| Panel | Rows | Share with fire |
|---|---|---|
| Weekly, 2016-2025 (in use) | about 2.5 million cell-weeks | 9 to 14% per year |
| Daily, 2013-2025 | about 24.5 million cell-days (5,152 cells, 4,748 days) | 2.56% (597,937 fire cell-days) |

## 3. What the EDA says carries signal

Share of the weekly model's gain, test years 2023-2025:

| Signal | Share |
|---|---|
| Historical rate of the cell for that week of the year | 56.4% |
| Fire in the cell in the previous 4 weeks | 28.6% |
| Fire in the 8 neighbouring cells the week before | 7.6% |
| Fire in the cell the week before | 1.9% |
| Position and season | 2.8% |
| Ten weather features | 2.4% (days since rain 1.0%) |

Day to day (Suomi-NPP, 2013-2025):

| Fact | Value |
|---|---|
| A cell with fire today has fire tomorrow | 33.3% of the time; the base rate is 2.56% |
| Tomorrow's fire cells that had fire today | 33.3% |
| Tomorrow's fire cells with fire today in the cell or one of its 8 neighbours | 64.7% |

What follows for the next-day model:

- **Two thirds of tomorrow is today and its surroundings.** A next-day model will be strong mostly
  because of persistence. Say so.
- **The other third starts where nothing showed the day before.** That is the part worth modelling,
  and the only place where weather, season and people can add something. Report the score on those
  cells separately ("new fire cells"), or the headline number will hide whether the model learned
  anything beyond persistence.
- **Weather added little at weekly scale** (average precision 0.555 to 0.563). The likely reasons:
  the historical rate already carries the usual weather of each place and week, the weather grid is
  coarse (0.5°), and a week is long. Whether daily weather helps more was not tested.
- **Season differs by place.** Northern Argentina peaks in August and September; central-south Chile
  from January to March. Two of the four fire regimes are shaped by the 2016/17 season alone.
- **People leave a weekly cycle.** Fire-days fall 37% on Sundays in Argentina and 28 to 30% in Chile.
  The day of the week is a real feature for a daily model.
- **Labels are noisy.** Steady sources are reported about half as often in winter (clouds), and even
  VIIRS misses a source that is always on half the nights. A "no fire" label often means "not seen".
  Expect a ceiling on the scores, and do not read low winter counts as low risk.

## 4. Numbers to beat

Weekly, test years 2023-2025:

| | Average precision | Brier score | ROC AUC | Fire caught watching the top 10% |
|---|---|---|---|---|
| Baseline: historical rate | 0.510 | 0.0616 | 0.887 | 52.6% |
| Model, history only | 0.555 | 0.0577 | 0.900 | 56.7% |
| Model, with weather | 0.563 | 0.0572 | 0.902 | 57.1% |

Next-day: no model yet. Two baselines must be computed first and both must be beaten:

1. **Historical rate:** how often that cell had fire on that day of the year (a window of about a week
   on each side), in earlier years only.
2. **Persistence:** "tomorrow equals today". From section 3 it has a precision and a recall of about 33%.

## 5. Validation: keep this protocol

| Rule | Why |
|---|---|
| Train up to 2020, tune on 2021-2022, test on 2023-2025 | Test years are never seen; the same split as the weekly model, so numbers compare |
| Score year Y only on cells with a detection before Y | Otherwise the panel contains cells because they burn later |
| Baselines of year Y use years before Y only | No look-ahead |
| Every feature ends before the day (or week) being predicted | Lags end the day before; weather windows end the day before |
| Outage days and weeks are left out of training and scoring | They are not "no fire" |
| Report per year, and for "new fire cells" separately | 2023 is the weakest year for every method |
| Scores: average precision, Brier score, share of fire inside the top-ranked cells, calibration | 97% of cell-days have no fire, so accuracy means nothing |
| If the model does not beat both baselines, ship the better baseline | Already how `scripts/risk_model.py` behaves |

Calibration of the weekly model is slightly high (it says 29% where 26% happens). Check it again
for the daily model; a rare target (2.6%) makes it worse.

## 6. Features to try for the next-day model

In order of expected value. All known at the end of day D.

| Group | Features |
|---|---|
| Persistence | Fire in the cell on D, D-1 ... D-6; days since the last fire; hotspots and summed FRP on D; fire on the night pass of D (`pass_slot`) |
| Spread | Fire on D in the 8 neighbours and in the next ring; hotspots in the neighbours |
| History | Historical rate for the day of the year (earlier years only); the weekly baseline already built |
| Calendar | Day of the week; sine and cosine of the day of the year |
| Place | Latitude, longitude, fire regime, people per km² |
| Weather before D+1 | Rain in 30 and 90 days, days since rain, maximum temperature, humidity, vapour pressure deficit, wind (the `ante_*` features of `scripts/risk_weather.py`, with daily windows) |
| Weather on D+1 | Only if a forecast source is added. NASA POWER is three days behind: it can train a model but cannot feed tomorrow's outlook. Training with the weather that was later observed on D+1 gives an optimistic score; label it as such |

## 7. Model and compute

- **Start with LightGBM**, as the weekly model does. The weekly model trains in 12 seconds on a laptop.
- **The daily panel fits in memory:** about 24.5 million rows and 30 features in `float32` is about
  3 GB. Training takes minutes on a CPU.
- **Runpod:** a CPU pod with 8 or more cores and 32 GB of memory is enough, and useful mainly to keep
  a fanless laptop cool and to run several settings in parallel. A GPU does not help gradient
  boosting on this size.
- **A GPU is only needed for a different kind of model:** a network that reads maps of fire over
  several days (the domain is a grid of about 156 by 92 cells of 0.25°). The EDA gives no evidence
  that it would beat boosting, because persistence and history dominate. Treat it as an experiment
  with the same test years and baselines, not as the plan.
- **What to copy to the pod** (under 300 MB): the repository, `harmonized/hotspots_kept.parquet`,
  `quality/outage_days.csv`, `weather/`, `population/cells.parquet`, `spatial/cell_regimes.parquet`.
  Never copy `.env` or any key.

## 8. What the model must hand back

One file the web app can read, like the weekly one (`risk/cells_weekly.parquet`):

`NASA_Data_Sources/processed/risk/cells_daily.parquet` with `burn_date` (the day predicted),
`cell_lat`, `cell_lon` (south-west corner of the 0.25° cell), `probability`, `baseline_probability`.

Plus a metrics file with the scores of section 5, per year, for the model and both baselines.

## 9. Limits to carry into the pitch

- The outlook ranks places. It does not predict ignitions, severity or damage.
- Most of its skill is persistence and history. That is a fair result, not a weakness to hide.
- Three test years. Recent months are provisional.
- Observation is uneven: winter, clouds and the far south are seen less well, and nothing is known
  about observation quality south of 40°S.
- The week (or day) in progress has no weather features, because NASA POWER is three days behind.
