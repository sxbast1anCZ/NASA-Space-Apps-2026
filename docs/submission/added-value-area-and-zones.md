# Added value 2: area at risk and zones around active fires

Source and full tables: `docs/findings/10-fire-zones.md`; how to use it: `docs/area-at-risk-guide.md`.

A 0.25° cell is about 700 km²: too large for a crew. This adds two answers:

1. **How much area is in alert**, for any day and area of the app.
2. **For each fire seen today**, the chance that it is detected again tomorrow and the zone where its
   next hotspots usually fall.

Neither is burned area, a perimeter or a direction of spread: the project has no burned-area or
perimeter labels.

## 1. Area of the cells in alert

The area of a 0.25° cell on a sphere of radius 6,371 km:

$$A = R^2 \cdot \Delta\lambda \cdot (\sin\varphi_N - \sin\varphi_S)$$

About 700 km² at 25° S, 647 km² at 33° S (Valparaíso) and 453 km² at 54° S.

`GET /api/risk/daily` returns, for the day and area selected:

- `alert_km2`: the area of the cells in alert;
- `expected_km2`: the sum of probability times cell area, the area of cells where a hotspot would be
  seen, on average over days like this one;
- the same by region.

On the test years (2023-2025):

| | Expected km² per day | Observed km² per day | Ratio | Median daily error | Fire area inside alert cells |
|---|---|---|---|---|---|
| Argentina | 72,217 | 67,050 | 1.08 | 30% | 78.5% |
| Chile | 7,875 | 7,645 | 1.03 | 47% | 78.5% |

Over many days the expected area is within 3 to 8%; one day is noisy, so say "about".

## 2. Zones around active fires

- **A fire**: hotspots of one burn day linked closer than 1 km (distances on a sphere, connected
  groups). 1,001,394 fires since February 2012.
- **Detected again**: a hotspot the next day within 2 km of the fire.
- **Zone**: the union of circles around the fire's hotspots, with the radii within which 50, 80 and
  90% of next-day hotspots fell in 2013-2022, per size class.

### The table (fitted on 2013-2022, both countries pooled)

| Size (hotspots) | Fires | Detected again: not active the day before | Active the day before | r50 | r80 | r90 |
|---|---|---|---|---|---|---|
| 1 | 427,122 | 7.3% | 17.0% | 1.0 km | 1.9 km | 2.4 km |
| 2-4 | 271,097 | 12.7% | 25.4% | 0.8 km | 1.8 km | 2.5 km |
| 5-19 | 81,972 | 27.9% | 44.8% | 0.6 km | 1.8 km | 2.9 km |
| 20-99 | 11,138 | 55.8% | 69.5% | 0.6 km | 2.1 km | 3.8 km |
| 100+ | 716 | 78.8% | 86.5% | 0.9 km | 4.0 km | 8.3 km |

The app uses the country rows when they have at least 200 fires.

### Scores on 2023-2025 (unseen)

- 169,332 fires; 14.9% detected again. Inside the 50, 80 and 90% zones: 55.4%, 83.3% and 92.0% of the
  next-day hotspots.
- The chance is calibrated: in every row the share detected again is within 4 points of the chance
  given, except the 54 largest Chilean fires (84% given, all detected again). Brier score 0.114 against
  0.127 for one rate for every fire.
- The zones hold in Argentina (83 to 91% inside the 80% zone). In Chile they are too narrow for small
  fires and the largest ones: read the 80% zone there as about 75%.

### Live day

2026-11-13 (fires of 2026-11-12, NOAA-20): 283 fires, 12 with a chance of 50% or more, about 49
expected to be detected again; their 80% zones add up to 4,054 km².

## 3. In the app

Red is what the satellite saw (hotspots and a ring per fire); blue is where its next hotspots usually
fall (the three bands); yellow to red is the chance per cell. The side panel lists the 10 largest fires
of the area with their chance of being detected again.

## Limits

- Not burned area, not a perimeter, not a direction.
- "Not detected" is not "out": clouds and pass times matter.
- Fires are not followed across days; "active the day before" is the only memory.
- No weather, fuel or slope.
