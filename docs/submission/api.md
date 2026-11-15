# API

FastAPI (`backend/main.py`, and `backend/ui.py` for the map's extra endpoints) on DuckDB.

- Base URL when run locally: `http://localhost:8000`. Interactive docs: `/docs`; schema: `/openapi.json`.
- Dates are `YYYY-MM-DD` and are burn days (06:00 to 06:00 local solar time).
- Area filters, where accepted: `west`, `south`, `east`, `north` (a box), or `country` and `admin1`.

## Base case (`backend/main.py`)

| Endpoint | Parameters | Returns |
|---|---|---|
| `GET /api/meta` | none | `first_date`, `data_through`, `viirs_start` (2012-02-01), `cell_degrees` (0.25), `regions`, `risk_weeks`, `risk_days` (newest first; the first is the live day) |
| `GET /api/calendar` | area, `from`, `to`, `reference` (`recent` = 2013 on, default; `all`) | `months`: `year`, `month`, `hotspots`, `raw`, `estimated`, `provisional`, `partial`, `median`, `ratio`, `reliable`; `current`; `reference` |
| `GET /api/hotspots.csv` | area, `from`, `to` | One row per kept hotspot; header `x-hotspot-count` |

## Outlook and area at risk (`backend/main.py`)

| Endpoint | Parameters | Returns |
|---|---|---|
| `GET /api/risk` | `week`, area | Weekly outlook: `cells` = `[cell_lat, cell_lon, probability, baseline]` |
| `GET /api/risk/daily` | `date`, area | `cells` = `[cell_lat, cell_lon, probability, historical rate, alert 0/1]`; `wind` = `[cell_lat, cell_lon, downwind degrees, max km/h]` for cells in alert; `area` = `cells`, `alert_cells`, `cells_km2`, `alert_km2`, `expected_km2`, `regions` |
| `GET /api/risk/daily/cell` | `date`, `cell_lat`, `cell_lon` | `probability`, `baseline_probability`, `alert`, `reasons` (`text`, `share`), `wind` (`wind_from_deg`, `downwind_deg`, `wind_max_kmh`, `gust_max_kmh`, `rh_min_pct`, `tmax_c`) or null |
| `GET /api/risk/daily/hotspots` | `date`, area | Hotspots of the day before, thinned to 0.02°, for the 5, 10 and 25 km rings |
| `GET /api/risk/daily/zones` | `date`, area | `fires` = `[fire_id, lat, lon, hotspots, p_continue, r50_km, r80_km, r90_km, area50_km2, area80_km2, area90_km2, continued, next_hotspots, next_in_r80, admin1]`, largest first (`continued` is null for the live day); `points` = `[fire_id, lat, lon]`; `available`; `truncated`; `summary` = `fires`, `likely`, `expected_continuing`, `area80_km2` |

Example, `GET /api/risk/daily/cell?date=2024-02-03&cell_lat=-33.25&cell_lon=-71.75`:

```json
{
  "date": "2024-02-03", "cell_lat": -33.25, "cell_lon": -71.75,
  "probability": 0.93, "baseline_probability": 0.03, "alert": true,
  "reasons": [
    { "text": "Today's fire here had 128 hotspots, and it was still burning at night", "share": 0.5 },
    { "text": "Fire was detected in this cell today, and on 2 of the last 7 days", "share": 0.29 }
  ],
  "wind": null
}
```

`wind` is filled only for the live day.

## Map (`backend/ui.py`)

| Endpoint | What it gives |
|---|---|
| `GET /api/ui/hotspots` | Hotspots of a period (up to 45 days) in columns, for the map |
| `GET /api/ui/days` | Harmonized hotspots per day, for the timeline |
| `GET /api/ui/density`, `/api/ui/yearly`, `/api/ui/series` | Aggregates for the history view |
| `GET /api/ui/regimes`, `/api/ui/static` | Fire regimes and static heat sources |
| `GET /api/ui/regions` | Last 7 days of each region against the same days of earlier years, and alerts for tomorrow |
| `GET /api/ui/boundaries` | Simplified region polygons (GeoJSON) |
| `GET /api/ui/towns` | Towns, for exposure near fires |
| `GET /api/ui/windfield`, `/api/ui/weather` | Wind field and current weather from Open-Meteo |
