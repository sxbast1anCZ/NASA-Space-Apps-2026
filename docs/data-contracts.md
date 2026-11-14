# Data contracts

The files that pass from one part of the project to another, and their columns. Changing one
needs a message to the team and the agreement of whoever reads it. All paths are under
`NASA_Data_Sources/processed/` (not in git).

### C1. Hotspot table (M1 → M2, M3, M5)

`NASA_Data_Sources/processed/hotspots/`, columns as in `CLAUDE.md` plus: `solar_time_h`, `pass_slot`, `burn_date`, `burn_year`, `burn_month`, `season_year`, `tz_name`, `utc_offset_min`, `local_wall_time`, `local_date`. Every count per day, month, year or season uses the `burn_*` columns, never `acq_date`.

### C2. Harmonized dataset (M2 → M4, M3)

`NASA_Data_Sources/processed/harmonized/cells_daily.parquet`, one row per cell and day with fire.

| Column | Meaning |
|---|---|
| `burn_date` | Day key |
| `cell_lat`, `cell_lon` | South-west corner of the 0.25° cell |
| `country`, `admin1` | From the hotspot table |
| `hotspots_harmonized` | VIIRS-equivalent hotspot count |
| `hotspots_raw` | Count before harmonization |
| `sensor` | Sensor the row comes from (MODIS or VIIRS) |
| `provisional` | True for NRT data |

The CSV download and the day view read the hotspot table (C1) directly.

### C3. Risk output (M5 → M4)

`NASA_Data_Sources/processed/risk/cells_weekly.parquet`: `week_start` (a `burn_date`), `cell_lat`, `cell_lon`, `probability` (0 to 1), `baseline_probability` (historical frequency for that cell and week).

### C4. API (M4)

Felipe defines the endpoints and documents them in the app's README. Dates travel as `YYYY-MM-DD` text and filter on `burn_date` (time rules in `docs/eda-plan.md`).
