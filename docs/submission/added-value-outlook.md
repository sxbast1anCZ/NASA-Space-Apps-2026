# Added value 1: next-day outlook

Source and full tables: `docs/findings/09-daily-model.md`.

## 1. The question

Brigades and emergency services ask "where should we look tomorrow, and why?". The outlook ranks every
0.25° cell of Chile and Argentina by how likely it is to show at least one VIIRS hotspot the next day.
It says **where fire activity is most likely tomorrow**, not where a fire will start.

## 2. Target and split

$$y_{c,d+1} = 1 \text{ if cell } c \text{ has at least one hotspot of the target satellite on burn day } d+1$$

- Target satellite: Suomi-NPP until 2026-10-31, NOAA-20 from 2026-11-01. Never added together.
- Outage days have no target: not observed is not "no fire".

| Set | Years | Use |
|---|---|---|
| Train | 2014-2020 | Fit the model |
| Tune | 2021-2022 | Early stopping and the alert threshold |
| Gap | First 7 days of 2021 and 2023 | In no set |
| Test | 2023-2025 | Final score on years never seen |
| Live | 2026-11-13 | 4,991 cells |

20,068,773 cell-days with a target in all.

## 3. Features

Only information up to day D. 23 features; Chile adds month and day of the year (26).

- Fire in the cell on each of the last 7 days; fire-days in 7 and 30 days; days since the last fire.
- Hotspots and FRP of the day; night detection.
- Fire in the 8 neighbours and in the next ring.
- Historical rate of the cell for that time of the year.
- Day of the week; latitude and longitude.

Not in the model: weather, vegetation, terrain, population, other satellites.

## 4. Model and results

One LightGBM per country. The alert threshold is the one that catches 80% of fire on 2021-2022
(0.046 in Argentina, 0.024 in Chile), applied unchanged to the test years.

| Test years 2023-2025 | Argentina | Chile |
|---|---|---|
| **Recall** (fire cell-days caught) | **78.0%** | **79.1%** |
| Precision | 15.9% | 8.8% |
| PR-AUC (average precision) | 0.359 | 0.269 |
| ROC AUC | 0.921 | 0.925 |
| Alerts per day | 489 | 109 |

Against the baselines:

| | Argentina PR-AUC | Chile PR-AUC |
|---|---|---|
| **Model** | **0.359** | **0.269** |
| Historical rate of the cell | 0.196 | 0.150 |
| Rule: fire today in the cell | 0.122 | 0.069 |
| Rule: fire today in the cell or a neighbour | 0.092 | 0.049 |

- With the same number of alerts as the neighbour rule, the model catches 79.1% against 64.0% in
  Argentina and 68.4% against 48.7% in Chile.
- It beats the baselines in every test year, in both countries.
- **Precision is low and must be said:** 5 of 6 alerts in Argentina and 10 of 11 in Chile had no
  hotspot the next day. That is the price of catching 80% of an event that happens on 1 to 3% of
  cell-days.
- Nine of ten misses are fires that appear where nothing showed the day before.

## 5. Reasons for each alert

`scripts/daily_explain.py` splits each alert's score into the contribution of each feature (TreeSHAP),
adds them up into six groups and writes one sentence for each group that pushes the score up.

```json
{
  "date": "2024-02-03",
  "cell_lat": -33.25,
  "cell_lon": -71.75,
  "probability": 0.93,
  "alert": true,
  "reasons": [
    { "text": "Today's fire here had 128 hotspots, and it was still burning at night", "share": 0.5 },
    { "text": "Fire was detected in this cell today, and on 2 of the last 7 days", "share": 0.29 }
  ]
}
```

A reason says which inputs moved the score, not why there is fire, and never mentions weather (the
model has none).

## 6. Wind of the live day

For the cells in alert of the live day, `scripts/daily_wind.py` reads the Open-Meteo forecast: the
direction the wind comes from and blows to, maximum speed and gusts, minimum relative humidity and
maximum temperature. The map draws an arrow downwind. The wind is context only: it is not in the model.
