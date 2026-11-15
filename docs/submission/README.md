# Submission package: Fireguard

NASA Space Apps Challenge 2026. Challenge: Harmonization of MODIS and VIIRS Hot Spots. Local event:
Antofagasta, Chile. Geography: Chile and Argentina.

Texts for the pitch, the slides, the 30-second video and the project page, in one place. Every number
here comes from a findings document of this repository; when they disagree, the findings document wins
(`docs/README.md`). Checked against `main` on 2026-11-15.

| Document | What it is |
|---|---|
| `pitch-and-slides.md` | The idea in one sentence, the 120-second pitch, the 7 slides and the 30-second video script |
| `base-case.md` | The base case: quality filter, burn day, harmonization and the burn calendar |
| `added-value-outlook.md` | Added value 1: the next-day outlook, its reasons and the wind of the live day |
| `added-value-area-and-zones.md` | Added value 2: area of the cells in alert and zones around active fires |
| `api.md` | The API endpoints, with their parameters and responses |
| `install-and-run.md` | How to install, build the data and run the app and the tests |
| `app_manifest.json` | The same facts in JSON |

## Summary

### Base case (what the challenge asks)

- **One series, 2000 to 2026, in VIIRS-equivalent hotspots.** 8,042,380 FIRMS detections (MODIS
  Terra and Aqua; VIIRS Suomi-NPP, NOAA-20 and NOAA-21) for Chile and Argentina; 7,000,520 pass the
  quality filter (12.95% removed: low confidence, static heat sources, volcanoes and offshore).
- **One satellite per period, never added together.** MODIS times a factor until January 2012,
  Suomi-NPP from February 2012 to October 2026, NOAA-20 from November 2026. NOAA-20 fills the
  Suomi-NPP outage days.
- **Factors per region, calendar month and pass** (day or night), fitted on 2012-2021 and shrunk
  towards the country factor. Region-month error (WAPE, leave-one-year-out): 13.9% in Argentina and
  24.0% in Chile; error of the yearly total 2.1% and 5.3%.
- **Burn day** from 06:00 to 06:00 local solar time, so that an afternoon fire and its night pass
  count on the same day.
- **Burn calendar** for any region, box or period on 0.25° cells: hotspots per month against the
  median of the same month in 2013 to the last complete year, `(x + 1) / (median + 1)`. CSV download.

### Added value 1: next-day outlook

- One LightGBM per country ranks every 0.25° cell by how likely it is to show at least one VIIRS
  hotspot tomorrow: "where fire activity is most likely tomorrow", not where a fire will start.
- Test years never seen in training (2023-2025): it catches **78.0% (Argentina) and 79.1% (Chile)**
  of the cell-days with a hotspot while flagging about 12% of the cells. PR-AUC 0.359 and 0.269,
  against 0.196 and 0.150 for the best baseline (the historical rate of the cell).
- Each alert carries up to three reasons in plain words (TreeSHAP), and the cells in alert of the live
  day carry the wind, gusts, minimum humidity and maximum temperature forecast by Open-Meteo.

### Added value 2: area at risk and zones around active fires

- The area in km² of the cells in alert and the expected area of cells with activity, by region. Over
  many days the expected area is within 3 to 8% of the observed one; on one day it is noisy.
- Each fire seen today (hotspots linked closer than 1 km) gets the chance of being detected again
  tomorrow and the zones where 50, 80 and 90% of its next hotspots usually fall. On 2023-2025, 83.3% of
  next-day hotspots fell inside the 80% zone.
- Not burned area, not a perimeter, not a direction of spread.

### Software

FastAPI and DuckDB backend; React, MapLibre and deck.gl app (Fireguard, with History, Now and Outlook
views; the earlier calendar app stays at `/#classic`). 149 automated tests, all passing on
2026-11-15.
