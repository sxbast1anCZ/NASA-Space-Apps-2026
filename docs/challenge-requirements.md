# What the challenge asks

NASA Space Apps Challenge 2026, "Harmonization of MODIS and VIIRS Hot Spots". Author of the
challenge: Marina Compagnucci, CONAE (Argentina's space agency).
Official page: https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/
Read on 2026-11-14. If this summary and the page disagree, the page wins.

## The problem

- Satellites have recorded active fire hotspots for more than two decades, but the record is split
  between two sensors that cannot be compared directly: MODIS (Terra and Aqua, since 2000, near the
  end of its life) and VIIRS (newer, finer). They differ in pixel size, sensitivity and pass times.
- Without a way to compare them, fire managers lose a consistent history of when and where it burned.

## What to deliver

A **harmonized burning activity calendar in a web application**. Suggested in two parts:

1. **Harmonize the hotspots**, so that the sensor of origin no longer matters and the focus is on
   patterns, trends and anomalies.
2. **A web application** that takes the harmonized hotspots, lets the user choose a region and a date
   range, and lets them download analytics and visualizations. Its calendar shows the number of
   hotspots from the early 2000s to today: which periods of the year have more fire, which years had
   more, and how a current fire compares with earlier ones.

## Optional, mentioned by the challenge

- Colour ramps that show how months differ, accessible and intuitive.
- A downloadable CSV of the hotspots of a search.
- A map where the user draws the area, or enters latitude and longitude.
- A few key figures: comparisons with multi-year averages, number of fires detected and reported.
- Audience: early warning and emergency responders, scientists, land managers, firefighters.
- In her audio briefing the author adds: choosing a specific day, and that a completely different
  approach is just as welcome.

## Not specified

Harmonization method, technology, geography, date range, judging criteria. The team chose Chile and
Argentina, November 2000 to today.

## Data

FIRMS, NASA's Fire Information for Resource Management System:
https://www.earthdata.nasa.gov/data/tools/firms . The author also points to CONAE and other agencies.
