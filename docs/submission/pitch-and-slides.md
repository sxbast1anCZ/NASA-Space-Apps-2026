# Pitch, slides and video

Limits of the global rules: 7 slides or a 30-second video, in English. Local pitch: 120 seconds in four
parts (problem, solution, evidence, next step).

Wording rules for every text below: a hotspot is a thermal detection, not a fire; say "where fire
activity is most likely", never "where a fire will start"; no trend claims.

## 1. The idea in one sentence

> We help fire agencies, brigades and emergency services decide where to look first, with one
> 26-year satellite record of hotspots that is consistent across MODIS and VIIRS, and a next-day
> outlook that says why each place is flagged.

## 2. Pitch, 120 seconds

### 0:00-0:25 Problem

> Chile and Argentina watch for fire from space. For 25 years that view came from MODIS; since 2012
> it also comes from VIIRS, which has sharper pixels and sees about three times as many hotspots for
> the same fires. MODIS is ending: NASA plans to stop Terra in January 2027 and Aqua around September
> 2027. If you put the two records side by side, you see a jump in 2012 that is the sensor, not the
> fire. Today's detections lose their history.

### 0:25-0:55 Solution

> We built Fireguard. First, we put 26 years of hotspots, from 2000 to 2026, on one VIIRS-equivalent
> scale, with factors per region, month and satellite pass, after removing low-confidence detections,
> industrial heat sources and volcanoes. Second, a burn calendar for any region and period, on cells
> of 0.25 degrees, that compares each month with its usual level. Then we went beyond the challenge:
> a next-day outlook of where fire activity is most likely tomorrow, with the reasons for each alert
> and the forecast wind, and for each fire seen today, the zone where its next hotspots usually fall.

### 0:55-1:30 Evidence

> - **Real data:** 8 million FIRMS detections; 7 million pass the quality filter.
> - **The harmonization holds:** the factors predict the yearly VIIRS total within 2% in Argentina
>   and 5% in Chile on years they did not see.
> - **The outlook was tested on three years it never saw, 2023 to 2025:** it catches 78% of the
>   cell-days with fire activity in Argentina and 79% in Chile, flagging about one cell in eight,
>   with nearly twice the average precision of the best baseline.
> - **Working software:** an API with 149 automated tests and the Fireguard map, which you can try.

### 1:30-2:00 Next step

> Next, we would add weather to the model, which has none today, other satellites as early signals for
> new fires, and alerts sent to the brigades. A hotspot is not a fire, and no detection does not mean
> no fire, so Fireguard says where to look first, and shows why. Thank you.

## 3. Slides (7)

| # | Title | Content |
|---|---|---|
| 1 | Fireguard: one hotspot record for Chile and Argentina | Challenge name; team, roles and Antofagasta 2026; a full-screen capture of the app |
| 2 | The problem: a sensor jump in the record | MODIS (1 km pixel, 2000 on, ending 2027) and VIIRS (375 m, 2012 on); VIIRS sees about 3 times as many hotspots; raw counts jump in 2012 |
| 3 | Base case: 26 years on one scale | Quality filter (12.95% removed); burn day 06:00 to 06:00 local solar time; factors per region, month and pass (2012-2021); one satellite per period; calendar against the monthly median |
| 4 | Added value 1: next-day outlook | One LightGBM per country; 78.0% and 79.1% of fire cell-days caught on 2023-2025 with about 12% of cells flagged; PR-AUC 0.359 and 0.269 vs 0.196 and 0.150; reasons per alert; Open-Meteo wind for the live day |
| 5 | Added value 2: area at risk and fire zones | km² of the cells in alert and expected km², by region; fires = hotspots linked within 1 km; chance of being detected again; 50, 80 and 90% zones (83.3% of next-day hotspots inside the 80% zone on 2023-2025) |
| 6 | How it is built and checked | DuckDB and Parquet; FastAPI; React, MapLibre, deck.gl; 149 tests; case study Valparaíso and Viña del Mar, 2-3 February 2024 (34 times the February median) |
| 7 | Limits and next steps | Not burned area, not ignition; no weather in the model yet; next: weather, other satellites as early signals, alerts to brigades. Closing line: "Where to look first, and why." |

## 4. Video, 30 seconds (English captions)

| Time | Picture | Caption |
|---|---|---|
| 0:00-0:03 | App title over the map of Chile and Argentina | We are team Fireguard from Antofagasta, on NASA's MODIS-VIIRS harmonization challenge. |
| 0:03-0:08 | Yearly chart: raw MODIS and VIIRS, the jump in 2012 | MODIS is ending, and VIIRS sees about three times as many hotspots. Raw records jump in 2012. |
| 0:08-0:15 | History view, moving through the years; the calendar of one region | We put 26 years on one VIIRS-equivalent scale, with a monthly calendar against the usual level. |
| 0:15-0:23 | Outlook view: a cell in Valparaíso, its reasons, its wind; the zones of a fire | A next-day outlook shows where fire activity is most likely, why, and where a fire's next hotspots usually fall. |
| 0:23-0:30 | Area in alert, CSV download, repository link | Open data and open code: where to look first, and why. |
