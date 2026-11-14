# NASA Space Apps 2026: Harmonization of MODIS and VIIRS Hot Spots

## Getting the data

The hotspot data is not stored in this repository (about 585 MB). Download it with:

```bash
./scripts/download_firms.sh
```

- Needs `bash` and `curl` (on Windows, run it from Git Bash). No account or API key.
- Source: [FIRMS Country Yearly Summary](https://firms.modaps.eosdis.nasa.gov/country/), Chile and Argentina.
- Output: `NASA_Data_Sources/<SENSOR>/<Country>/<file>.csv`, one file per year (96 files).
- Sensors: `MODIS` (2000–2025), `VIIRS_SNPP` (2012–2025), `VIIRS_NOAA20` (2018–2025).
- Safe to re-run: files already downloaded are skipped.

### 2026 and VIIRS NOAA-21 (FIRMS API)

The yearly files stop at 2025 and do not include NOAA-21. To fill that gap:

1. Get a free MAP_KEY at <https://firms.modaps.eosdis.nasa.gov/api/map_key/>.
2. Copy `.env.example` to `.env` and set `FIRMS_MAP_KEY=` (`.env` is git-ignored, never commit the key).
3. Run:

```bash
./scripts/download_firms_api.sh
```

- Output: `NASA_Data_Sources/<SENSOR>/API_bbox/<SENSOR>_<YYYY-MM>.csv`, one file per month.
- Covers 2026 for `MODIS`, `VIIRS_SNPP` and `VIIRS_NOAA20`, and `VIIRS_NOAA21` from March 2023.
- Uses standard processing (SP) while available and near-real-time (NRT) after that. Months not fully covered by SP are re-downloaded on every run, because NRT data gets revised.
- The query is a bounding box around Chile and Argentina, so it includes points from neighbouring countries. Clip to the country borders when processing.
- NOAA-21 files are not in the yearly layout (`<SENSOR>/<Country>/`), they only exist under `API_bbox/`.

## Population data (WorldPop)

Used by the risk and impact extension to estimate the population near a fire. See `docs/population-and-past-fires.md`.

```bash
./scripts/download_population.sh            # 2024 by default
YEAR=2020 ./scripts/download_population.sh  # any year from 2015 to 2030
```

- Needs `bash` and `curl`. No account or API key.
- Source: [WorldPop R2025A](https://hub.worldpop.org/geodata/listing?id=135), constrained population counts, about 100 m per cell.
- Output: `External_Data_Sources/WorldPop/<Country>/<file>.tif` (git-ignored), one GeoTIFF per country.
- Safe to re-run: files already downloaded are skipped.

## Runpod MCP server

`.mcp.json` registers the official [Runpod MCP server](https://github.com/runpod/runpod-mcp) (pinned to 4.12.0) so Claude Code can manage pods, endpoints and volumes.

1. Create an API key in the Runpod console (Settings → API Keys).
2. Add `RUNPOD_API_KEY=` to your `.env` (see `.env.example`). The key never leaves your machine and is not committed.
3. Restart the session and approve the `runpod` server when asked.

`scripts/runpod_mcp.mjs` reads the key from `.env` and passes only that variable to the server.

## Building the unified hotspot table

All downloads (yearly country files and monthly API files) come with slightly different columns.
`scripts/build_hotspots.py` merges them into one Parquet dataset with a single schema:

```bash
pip install -r requirements.txt
./scripts/download_boundaries.sh
python scripts/build_hotspots.py
```

- Output: `NASA_Data_Sources/processed/hotspots/year=YYYY/` (about 8.0 million rows, takes about 2 minutes).
- Common names for MODIS and VIIRS columns (`bright_mir_k`, `bright_tir_k`, `frp_mw`, ...), normalised
  satellite names, UTC time, `processing` (SP or NRT) and a common `confidence_level` (low, nominal, high).
- Every point gets `country` and `admin1` (region or province) from the same boundary polygons, so
  yearly and API rows use identical borders. FIRMS' own label is kept as `country_firms`; the two agree
  on 99.98% of yearly rows. API rows outside Chile and Argentina (bounding box) are dropped.
- It does not harmonise MODIS against VIIRS. See `docs/eda-plan.md` for the next steps.

### Boundary sources

One source per country, because neither covers both well. `scripts/download_boundaries.sh` downloads both
to `NASA_Data_Sources/boundaries/<Country>.geojson`.

| | Chile | Argentina |
|---|---|---|
| Source | [geoBoundaries](https://www.geoboundaries.org/) gbOpen, ADM1 simplified (William & Mary geoLab), pinned to release commit `9469f09` | [Instituto Geográfico Nacional](https://www.ign.gob.ar/) (IGN), WFS layer `ign:provincia` at `wms.ign.gob.ar`, EPSG:4326 |
| Original data | Biblioteca del Congreso Nacional (BCN), OCHA ROLAC | IGN, Argentina's official mapping agency |
| Units | 16 regions | 24 (23 provinces and CABA), with name (`nam`) and INDEC code (`in1`) |
| Size | 8 MB | 112 MB, about 4 million vertices |
| Terms | CC BY 3.0 IGO: credit the source | Free reuse and redistribution under Art. 2 of Law 27.275 (stated by the WFS service); credit IGN |

Things to know:

- **geoBoundaries' Argentina file is not used:** it is missing Entre Ríos (the Paraná delta, about 343k hotspots
  in our table), misspells La Rioja as "La Roja" and has one coarse polygon per province.
- **Chile names come mis-encoded** (`RegiÃ³n`); `build_hotspots.py` fixes them. The file includes Easter Island
  (in Valparaíso) and no Antarctic territory.
- **IGN's Tierra del Fuego polygon follows Argentina's official definition:** it includes the Malvinas/Falklands
  and the Antarctic claim, so the 130 Falklands hotspots are labelled Argentina.
- **Polygons are simplified to about 100 m** when loaded, well below the 375 m VIIRS pixel.
- **The two sources do not share a border line**, so small gaps and overlaps remain along the Andes. Where they
  overlap, the first match wins (Argentina is checked first). This explains part of the 1,205 border
  disagreements with FIRMS. Points outside both polygons (10,476, mostly coastal) keep FIRMS' country and get
  no `admin1`.
- Credit both sources in the web app.

## Running the web app

The app needs the hotspot table, the quality flags and the harmonized dataset:

```bash
python scripts/build_hotspots.py
jupyter nbconvert --to notebook --execute --output-dir /tmp notebooks/01_quality.ipynb   # quality flags, about 3 minutes
python scripts/harmonize.py
```

```bash
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
uvicorn backend.main:app --port 8000
```

Open http://localhost:8000. The API serves the built web app.

For development, run the API with `uvicorn backend.main:app --reload` and the web app with
`npm run dev` inside `frontend/` (it proxies `/api` to port 8000). API docs: http://localhost:8000/docs.
Tests: `pytest`.
