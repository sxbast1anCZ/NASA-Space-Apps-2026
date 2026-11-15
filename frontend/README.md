# Web app: Fireguard

React + TypeScript + Vite, with MapLibre GL and deck.gl for the map. It talks to the API in
`backend/main.py` plus the extra endpoints in `backend/ui.py`.

## What it shows

- **History**: harmonized hotspots per 0.25° cell since 2000, by year and month, in 2D or 3D. The
  filter switches the map to raw MODIS or raw VIIRS to compare the sensors.
- **Now**: hotspots of the last 14 days, with playback, heat map and spread distances.
- **Outlook**: next-day probability of fire activity with the reason for each alert, the coming
  weeks, and past days to check the model.
- Wind flow (Open-Meteo), towns of 5,000 people or more near fire (GeoNames) as 3D houses, local
  time, season and current weather of the selected place.
- NASA GIBS imagery of the day (true colour and fire false colour), light and dark themes, Spanish
  and English, four user profiles (firefighter, early warning, land manager, science).

## Code

- `src/studio/Studio.tsx`: the page, its state, the time line, legend and cards.
- `src/studio/MapStage.tsx`: map, deck.gl layers and the wind particles.
- `src/studio/Cards.tsx`, `Towns.tsx`, `LocalNow.tsx`, `DayPicker.tsx`, `Brand.tsx`: panels.
- `src/studio/exposure.ts`: towns near fire and wind direction.
- `src/studio/data.ts`: API client. `i18n.ts`: texts. `personas.ts`: profiles and layers per mode.
- The earlier page (`src/App.tsx`, `src/MapPicker.tsx`) is kept but not used.

## Run

Needs the processed data of the pipeline (see the README at the repo root) and, for the towns:

```bash
mkdir -p NASA_Data_Sources/geonames && cd NASA_Data_Sources/geonames
curl -O https://download.geonames.org/export/dump/cities5000.zip && unzip cities5000.zip
awk -F'\t' '$9=="CL"||$9=="AR"' cities5000.txt > cl_ar.tsv
```

Then, from the repo root:

```bash
./run-ui.sh   # API on :8000 (uvicorn backend.ui:app) and the web app on :5173
```

Wind and weather come from Open-Meteo, which allows about 600 locations per minute: a new wind day
(459 grid points) may take a minute to load. Fetched days are cached in
`NASA_Data_Sources/processed/ui/`.

Data credits: NASA FIRMS, NASA EOSDIS GIBS, IGN Argentina, geoBoundaries, GeoNames, Open-Meteo,
Esri, CARTO, OpenStreetMap.
