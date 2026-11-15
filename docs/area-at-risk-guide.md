# Area at risk: how it is built and how to use it

The next-day outlook (`findings/09-daily-model.md`) says how likely a hotspot is in each 0.25° cell
tomorrow. This adds the answer to "how much area is at risk, and where will an active fire show up
next?". This guide covers what was added, how it is wired into the pipeline and the app, how to use it,
and how to run it again. Results and limits are in `findings/10-fire-zones.md`.

Written on 2026-11-15 on branch `feat/fire-zones`.

## 1. What it adds

| Piece | Question it answers | Where |
|---|---|---|
| **Area of the cells in alert** | How many km² does the outlook flag today, and in which regions? | `backend/main.py` (`daily_area`), status line under the map |
| **Expected area with activity** | Adding chance × cell area, about how many km² of cells will show a hotspot? | Same |
| **Fires of the day before** | Where did the satellite see fire, grouped into fires? | `scripts/fire_zones.py`, red dots and rings on the map |
| **Chance a fire is detected again** | Will the satellite see this fire again tomorrow? | Same, in the tooltip and the list of fires |
| **Zone of likely activity** | If it is detected again, where will its next hotspots likely appear, and how large is that zone? | Same, blue bands on the map |

None of these is burned area, a perimeter or a direction of spread. There are no burned-area labels in
the project (`modeling-plan.md`, section 9).

## 2. How to use it in the app

### Find a fire

1. In **Next-day outlook**, choose a day. **Latest day** shows the outlook for tomorrow, built on the fires seen yesterday.
2. Narrow the area if needed: choose a country and a region, or draw a rectangle on the map.
3. The side panel lists the **10 largest fires** of that area, with the chance that each one keeps
   burning. Click one: the page scrolls to the map and zooms to the fire.
4. On the map, point at a **red ring** for its numbers. Click it to zoom in.

The fire layer is on by default once a day is chosen. The checkbox "Fires of the day before (red) and
where they may show up next (blue)" turns it off.

### What each colour means

A legend under the map explains every layer that is on. In short:

| On the map | Meaning |
|---|---|
| Yellow to red squares | Chance that the satellite sees at least one hotspot in that 25 × 25 km cell on the chosen day |
| Dark outline on a square (zoom in) | Cell in alert: among the cells flagged to catch 8 of 10 fire cell-days |
| Small red dot | A hotspot seen on the day before: heat detected by the satellite in one pixel |
| Red ring | A fire: hotspots of that day less than 1 km apart. Size grows with its number of hotspots |
| Dark blue band | Where **half** of the fire's next-day hotspots fell, for past fires of the same size that kept burning |
| Blue band with an outline | Where **8 of 10** fell. Its area is the "zone" in km² |
| Light blue band | Where **9 of 10** fell |
| Purple shading (optional checkbox) | 5, 10 and 25 km around every hotspot of the day before, for all fires together (the older rings) |

**Red is what was seen; blue is what may come next.**

### Reading a fire's numbers

Pointing at a red ring shows, for example:

> **Fire of 145 hotspots on 2026-11-12** (Santiago del Estero)
> Chance it is detected again on 2026-11-13: **79%** (fires of this size in 2013-2022).
> If it is, 8 of 10 of its hotspots usually fall within 7.0 km of today's: a zone of 297 km². 9 of 10 within 12.9 km (772 km²).

For a past day it also says what happened: whether the fire was detected again, and how many of its
hotspots fell inside the 80% zone.

### Reading the area of the cells

The status line under the map says, for the chosen day and area:

> The cells in alert cover 605,643 km² of 3,182,782 km² (most in Santiago del Estero, 88,965 km²; ...);
> adding chance times area, about 113,396 km² of cells would show a hotspot.

- The **area in alert** is large on purpose: catching 8 of 10 fires means flagging about 12% of the
  cells. It is the area to watch, not the area that will burn.
- The **expected area** is close to the observed area over many days (1.03 in Chile, 1.08 in
  Argentina on 2023-2025) but noisy for one day (median error 30 to 47%). Say "about".
- Regions are named only when no single region is chosen: with one region, its border cells would
  name the neighbours.

### Wording for the pitch and the interface

| Say | Do not say |
|---|---|
| "Where this fire will most likely show up tomorrow" | "The area that will burn", "the fire will spread here" |
| "Chance it is still detected tomorrow" | "Chance it is still burning" (clouds can hide a fire) |
| "Area of the cells in alert" | "Area at risk of burning", "burned area" |
| "A fire: hotspots closer than 1 km" | Counting hotspots as fires |

## 3. How it is integrated

```
harmonized/hotspots_kept.parquet ─┐
quality/outage_days.csv ──────────┴─> scripts/fire_zones.py ─> risk/fire_zones.parquet ──────┐
                                                             risk/fire_zone_points.parquet ─┤
                                                             risk/fire_zones.json, .md      │
                                                                                            ├─> backend/main.py ─> frontend
scripts/daily_panel.py ─> daily_train.py ─> risk/cells_daily.parquet ───────────────────────┘
                                            (the outlook, unchanged)
```

`fire_zones.py` reads only the hotspot table and the outage days. It does not depend on the outlook
scripts and does not change their files.

### `scripts/fire_zones.py`

| Step | What it does | Function |
|---|---|---|
| 1 | Loads the hotspots of the target satellite: Suomi-NPP before 2026-11-01, NOAA-20 after (never both) | `load_target` |
| 2 | For each observed day D, links hotspots closer than 1 km into fires | `group_fires`, `day_fires` |
| 3 | Marks the fires that had a hotspot within 2 km on D-1 ("active the day before") | `active_before` |
| 4 | Groups the hotspots of D+1 the same way; a group that comes within 2 km of a fire continues it, and each of its hotspots gets its distance to the fire | `continuation` |
| 5 | Fits a table on predicted days 2013-2022: the share of fires that continued, and the 50/80/90% distances, by country, size class and "active the day before"; groups with fewer than 200 fires fall back to wider ones | `calibrate`, `lookup` |
| 6 | Zone area: union of circles around the fire's hotspots (thinned to 200 m), computed on a grid of radius/8, scaled so that one hotspot gives exactly πr² | `union_areas`, `add_areas` |
| 7 | Scores the table on 2023-2025 and writes the files for the app (2023 to the live day) | `evaluate`, `main` |

Outage days of the target satellite are not observed: no fire is scored against them.

### Files written (under `NASA_Data_Sources/processed/risk/`)

| File | Content |
|---|---|
| `fire_zones.parquet` | One row per fire of D, keyed by the predicted day `burn_date` = D+1 (and `seen_date` = D): `fire_id`, centre `lat`/`lon`, `country`, `admin1`, `hotspots`, `frp_sum_mw`, `size_class`, `active`, `p_continue`, `r50_km`/`r80_km`/`r90_km`, `area50_km2`/`area80_km2`/`area90_km2`, and what happened: `continued`, `next_hotspots`, `next_in_r80` (empty for the live day) |
| `fire_zone_points.parquet` | `burn_date`, `fire_id`, `lat`, `lon` of each fire's hotspots, thinned to 0.002° |
| `fire_zones.json`, `fire_zones.md` | The fitted table, the scores on 2023-2025 and the settings |

The full column contract is also in `daily-model-handoff.md`, section 7.

### Backend (`backend/main.py`)

| Change | Detail |
|---|---|
| `GET /api/risk/daily` | Adds `area`: `cells`, `alert_cells`, `cells_km2`, `alert_km2`, `expected_km2`, and `regions` (the same per region, largest first). Cell area on a sphere (`CELL_KM2`); region of a cell from table `cell_region` (the region of most of its rows) |
| `GET /api/risk/daily/zones?date=` | New. Same area filters as the other endpoints. Returns `fires` (largest first), `points` (up to `ZONE_POINTS` = 6,000 hotspots, largest fires first; the largest always gets its own), `truncated`, `summary` (`fires`, `likely`, `expected_continuing`, `area80_km2`) and `seen_date` |
| `DAILY_FILES` | Two optional files more (`zones`, `zone_points`). Without them the app starts and the zones are empty |

### Frontend (`frontend/src/`)

| File | Change |
|---|---|
| `api.ts` | Types `DailyArea`, `ZoneFire`, `Zones`; `getDailyZones`; colours `FIRE_RED`, `ZONE_COLORS` |
| `MapPicker.tsx` | Fire layer: three panes for the blue bands (drawn opaque, made see-through as a whole so overlaps read as one flat area, with no mouse events so the cells stay clickable), a pane for the red hotspots, and a pane of SVG red rings with tooltip and click-to-zoom. New props `zones`, `focus` (zoom to a fire) and `legend` |
| `MapLegend.tsx` | New. The legend under the map, showing only the layers that are on |
| `App.tsx` | Fire layer on by default, "How to find a fire", the list of fires, the area sentence of the status line, the fire summary |
| `index.css` | Map 420 px high; styles of the legend, guide, list and tooltip |

### Tests

| File | Covers |
|---|---|
| `tests/test_fire_zones.py` (15) | Distances against the great circle (and the two cases of the review), grouping and its ids, size classes, union area, "active the day before", continuation and ties between fires, majority country, the table and its fallbacks, scores, the whole run on synthetic fires, that the table never reads the test years, that outage days are never scored |
| `tests/test_api.py` (3 new, 1 changed) | Area per day and region against hand-computed cell areas, the zones endpoint and its filters, the point budget, the app without the zone files |

`pytest` runs 145 tests in about 40 seconds; none needs the real data.

## 4. How to run it again

```bash
python scripts/fire_zones.py
```

Run it whenever `hotspots_kept.parquet` is rebuilt. It takes about 2.5 minutes on a laptop with 10
cores and 12 GB: 1.5 minutes to group the fires of every day since 2012, 1 minute for the areas. Then
restart the API (`uvicorn backend.main:app`) and rebuild the frontend (`npm run build` in `frontend/`).

To check it: `risk/fire_zones.md` should show about 83% of next-day hotspots inside the 80% zones on
2023-2025, and the last `burn_date` of `fire_zones.parquet` should equal the live day of
`cells_daily.parquet`.

## 5. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| No red or blue on the map | `risk/fire_zones.parquet` is missing: run `scripts/fire_zones.py` and restart the API |
| The browser shows an older version of the page | It cached `index.html`: reload without the cache (Ctrl+F5) |
| Zones look like thin halos | Zoom in, or click the fire: most zones are 1 to 4 km wide |
| "Too many fires for the whole area" | More than 6,000 hotspots in the view: only the largest fires are drawn. Choose a region |
| The run is very slow or the machine swaps | The area step packs up to 4 million grid cells per batch (`max_cells` in `union_areas`); lower it on a small machine. Do not go back to `shapely.buffer` of a MultiPoint: it takes minutes per large fire |

## 6. Results in short (details in `findings/10-fire-zones.md`)

| | Value on 2023-2025 |
|---|---|
| Fires scored | 169,332 |
| Chance of being detected again | Calibrated: within 4 points of the observed share in every size class but one |
| Brier score against one rate for all fires | 10.6% better |
| Next-day hotspots inside the 50 / 80 / 90% zones | 55.4% / 83.3% / 92.0% |
| Chile | Zones too narrow: about 75% inside the 80% zone |
| Distances | On a sphere (`to_km`); a first version on a plane was wrong by up to 66% and was fixed before merging (`findings/10-fire-zones.md`) |
| Live day (2026-11-13) | 283 fires; 12 with 50% or more; 80% zones add up to 4,054 km² |
