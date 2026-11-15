# 10. Area at risk: cells in alert and zones around active fires

Scripts: `scripts/fire_zones.py` (zones), `backend/main.py` (area of the cells in alert). Run on
2026-11-15 on the data downloaded on 2026-11-14. Every number below was computed from those files;
statements marked **(inference)** are interpretation.

The next-day outlook (`09-daily-model.md`) says where a hotspot is most likely tomorrow, cell by cell.
This adds two answers to "how much area is at risk":

1. **The area of the cells in alert**, and the expected area of cells with activity, for any day and
   area of the app.
2. **For each fire seen today**, the chance that it is detected again tomorrow and the zone where its
   next hotspots usually fall, with that zone's area in km².

Neither is burned area, a perimeter or a direction of spread (`docs/modeling-plan.md`, section 9:
there are no burned-area or perimeter labels in the project).

## Decisions

| Topic | Decision | Why |
|---|---|---|
| Burned area | **Not estimated** | No labels (MCD64A1 or perimeters are not downloaded). Hotspots times pixel size is not burned area |
| Area of the cells in alert | Area of each 0.25° cell on the sphere, added over the cells in alert | A 0.25° cell is about 700 km² at 25° S and 450 km² at 54° S: counting cells overstates the south |
| Expected area | Probability times cell area, added up | The probabilities are calibrated on the test years (section 1), so the sum is close to the area that shows hotspots |
| A fire | Hotspots of one day closer than 1 km, connected (task T8, one day at a time) | VIIRS pixels are 375 m; 1 km joins neighbouring pixels of one front |
| Fire continues | A group of hotspots of the next day comes within 2 km of the fire | Two separate questions: will it still burn, and where. With a fixed radius, unrelated new fires 20 to 50 km away were counted as the fire's spread |
| Chance of continuing | Share of past fires of the same size class, country and "active the day before" that continued | A table, readable and scored on unseen years. FRP of a single hotspot did not change the chance in the first look (2018-2019) |
| Zone | Union of circles around the fire's hotspots, with the 50, 80 and 90% radii of the distance from its next-day hotspots to its hotspots of today | Measured on the same fire, per size class |
| Years | Fitted on predicted days 2013-2022, scored on 2023-2025, used unchanged for the live day | Same split logic as the outlook |

## 1. Area of the cells in alert

`GET /api/risk/daily` now returns `area` for the day and the selected area: cells scored, cells in
alert, their area in km², the expected area of cells with activity, and the same by region (a cell
belongs to the region of most of its rows). Cell area on a sphere of radius 6,371 km.

**Is "probability times area" a fair estimate?** On the test years (2023-2025, the model, not the
baseline), against the area of the cells that really had a hotspot:

| | Days | Expected km² per day | Observed km² per day | Ratio | Daily correlation | Median daily error | Area of cells in alert per day | Share of fire area inside alert cells |
|---|---|---|---|---|---|---|---|---|
| Argentina | 1,071 | 72,217 | 67,050 | 1.08 | 0.82 | 30% | 330,233 | 78.5% |
| Chile | 1,071 | 7,875 | 7,645 | 1.03 | 0.63 | 47% | 68,590 | 78.5% |

The probabilities are calibrated by bin as well:

| Probability given | Cell-days | Mean probability | Share with a hotspot |
|---|---|---|---|
| Under 1% | 3,786,167 | 0.28% | 0.23% |
| 1-5% | 954,809 | 2.3% | 2.2% |
| 5-20% | 405,162 | 9.9% | 9.3% |
| 20-50% | 122,650 | 30.9% | 28.6% |
| 50% or more | 28,837 | 63.7% | 61.5% |

- Over many days the expected area is within 3 to 8% of the observed one, slightly high.
- **One day is noisy**: the expected area is off by a median of 30% (Argentina) and 47% (Chile), and
  on quiet days it runs high (the 90th percentile of expected over observed is 3 to 4). Say "about".
- The area of the cells in alert is large by design: the threshold flags about 12% of the cells to
  catch 8 of 10 fire cell-days. It is the area to watch, not the area that will burn.

## 2. Zones around active fires

**What was built.** For every day since February 2012, the hotspots of the target satellite are
grouped into fires: 1,006,039 fires, of which 795,682 (predicted days 2013-2022) fit the table and
170,142 (2023-2025) score it. For each fire, the app shows:

- the chance that it is detected again the next day (a hotspot within 2 km);
- the radii within which 50, 80 and 90% of its next-day hotspots fell in 2013-2022, if it was;
- the area of each zone: the union of circles of that radius around its hotspots (thinned to 200 m);
- for past days, what happened: detected again or not, and how many of its hotspots fell inside the 80% zone.

**First look (2018-2019), the reason for the two questions.** With one radius of up to 50 km, the
median distance from a next-day hotspot to a fire of one hotspot was 13 km, because most of those
next-day hotspots were other fires. Fires of one hotspot had something within 1 km the next day only
5% of the time; fires of 100 hotspots or more, 79%. So the chance of continuing and the zone of a
continuing fire are measured apart.

### The table (fitted on 2013-2022)

Size is the number of hotspots of the fire on the day it was seen.

| Size | Fires | Chance of being detected again: not active the day before | Active the day before | r50 | r80 | r90 |
|---|---|---|---|---|---|---|
| 1 | 430,856 | 7.3% | 16.9% | 1.0 km | 1.9 km | 2.5 km |
| 2-4 | 271,411 | 12.8% | 25.2% | 0.8 km | 1.8 km | 2.5 km |
| 5-19 | 81,583 | 27.9% | 44.8% | 0.6 km | 1.8 km | 2.9 km |
| 20-99 | 11,112 | 55.3% | 69.6% | 0.6 km | 2.1 km | 3.9 km |
| 100+ | 720 | 80.2% | 86.3% | 0.9 km | 4.2 km | 10.4 km |

Both countries pooled; the app uses the country rows when they have at least 200 fires (and 200
next-day hotspots for the radii), and the pooled rows otherwise. All rows are in
`risk/fire_zones.json` and `risk/fire_zones.md`.

- A fire that was already active the day before is about twice as likely to be detected again when it is small.
- **Where a continuing fire's next hotspots fall barely depends on its size**: 8 of 10 within about
  2 km of today's hotspots. Large fires get much larger zones because they have many more hotspots to
  draw circles around, and their 90% radius is wider (10 km for 100+ hotspots).

### Scores on 2023-2025 (unseen)

| Country | Size | Fires | Chance given | Share detected again | Inside r50 | Inside r80 | Inside r90 | Median zone r80 |
|---|---|---|---|---|---|---|---|---|
| Argentina | 1 | 80,597 | 8.5% | 9.0% | 56.8% | 83.4% | 92.2% | 11.5 km² |
| Argentina | 2-4 | 52,333 | 15.2% | 16.4% | 57.0% | 84.1% | 92.6% | 12.9 km² |
| Argentina | 5-19 | 15,696 | 33.7% | 35.1% | 56.1% | 84.8% | 93.4% | 17.8 km² |
| Argentina | 20-99 | 1,957 | 62.4% | 62.2% | 54.1% | 84.7% | 94.6% | 39.3 km² |
| Argentina | 100+ | 105 | 82.7% | 83.8% | 61.3% | 88.6% | 97.8% | 140 km² |
| Chile | 1 | 10,088 | 7.6% | 6.7% | 40.9% | 75.6% | 87.6% | 9.1 km² |
| Chile | 2-4 | 6,447 | 14.2% | 12.7% | 40.9% | 72.3% | 82.9% | 11.5 km² |
| Chile | 5-19 | 2,426 | 33.6% | 31.5% | 42.6% | 73.0% | 87.8% | 24.2 km² |
| Chile | 20-99 | 443 | 76.4% | 79.7% | 62.8% | 90.6% | 97.7% | 45.3 km² |
| Chile | 100+ | 50 | 84.1% | 100% | 58.7% | 77.8% | 81.4% | 543 km² |
| **All** | | **170,142** | | **14.9%** | **55.5%** | **83.6%** | **92.5%** | |

- **The chance is calibrated** on unseen years: in every row the share detected again is within 3.5
  points of the chance given, except the 50 largest Chilean fires (84% given, all continued).
- **Brier score** of the table 0.113 against 0.127 for one rate for every fire (the rate of 2013-2022,
  14.1%): 10.5% better. Most fires are single hotspots with a low chance; the table's value
  is in telling the few large, persistent fires apart.
- **The zones hold in Argentina** (83 to 89% of next-day hotspots inside the 80% zone).
- **In Chile they are too narrow for small fires** (72 to 76% inside the 80% zone) and for the
  largest ones (78%). Chilean fires of 2023-2025 spread further from one day to the next than those of
  2013-2022 **(inference: 2023 and 2024 had very large fires in Chile, `06-case-studies.md`, and a few
  of them weigh heavily on 50 fires; not checked fire by fire)**. Read the 80% zone in Chile as about 75%.

### The live day

For 2026-11-13 (fires of 2026-11-12, NOAA-20): 289 fires, 255 in Argentina and 34 in Chile; 12 with
a chance of 50% or more, about 49 expected to be detected again; their 80% zones add up to 4,016 km².
The largest, 145 hotspots in Santiago del Estero, has a chance of 80% and an 80% zone of 111 km².

## 3. In the app

| Piece | What it does |
|---|---|
| `GET /api/risk/daily?date=` | Adds `area`: cells, cells in alert, km² of each, expected km², and the same by region |
| `GET /api/risk/daily/zones?date=` | The fires of the day before in the selected area, largest first, with chance, radii, areas and what happened; their hotspots for the map (up to 6,000, largest fires first) |
| Status line of the outlook | "The cells in alert cover X km² of Y km² (most in ...); adding chance times area, about Z km² of cells would show a hotspot. That is the area of the 0.25° cells, not burned area." Regions are named only for a box or a country |
| Checkbox "Fires of the day before (red) and where they may show up next (blue)", on by default | Red: each hotspot of the day before as a dot, and each fire as a red ring (point at it for its numbers, click to zoom). Blue: its zones as flat bands, dark for half of its next-day hotspots, outlined for 8 of 10, light for 9 of 10. The zones never take the mouse, so the cells under them stay clickable |
| "How to find a fire" and the list of fires | Four steps in the side panel, and the 10 largest fires of the selected area with their chance of burning tomorrow; a click zooms the map to the fire |
| Legend under the map | Explains every layer that is on: the cells and their colours, the alert outline, hotspots, fires, the three blue bands, the purple rings |

Red is what the satellite saw; blue is what may come next; yellow to red is the chance per cell. The app starts without the zone files: the
zones are then empty.

## Limits

- **Not burned area, not a perimeter, not a direction.** The zone is where the next detections of a
  fire usually fall. A fire that jumps further than 2 km from all its hotspots counts as a new fire.
- **Detected again** depends on clouds, the hours of the passes and the size of the fire: "not
  detected" is not "out".
- **One day of grouping.** Fires are not followed across days (task T8 is only half done), so a long
  fire is a new "fire" every day; "active the day before" is the only memory.
- **No weather, wind, fuel or slope.** The wind arrows of the outlook are not used here.
- **Satellite.** The table was fitted on Suomi-NPP; from 2026-11-01 the live day uses NOAA-20, which
  sees 0.93 to 1.03 times as many hotspots per year. Not scored.
- **The expected area of the cells** is calibrated over many days, noisy for one day (section 1).
- **Chile, 2023-2025**: zones narrower than they claim (section 2).

## How to run

```bash
python scripts/fire_zones.py
```

About 2.5 minutes on a laptop (10 cores, 12 GB): 1.5 minutes to group the fires of every day, 1 minute
for the areas. Independent of the outlook scripts. Tests: `tests/test_fire_zones.py` (13), and the zone
and area tests in `tests/test_api.py`.
