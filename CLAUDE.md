# NASA Space Apps 2026: harmonized MODIS and VIIRS hotspots

What the challenge asks: `docs/challenge-requirements.md`. Conventions: `CONTRIBUTING.md`.
What each document is for: `docs/README.md`.

## Project status

> Written in English per `CONTRIBUTING.md`, like every document in the repository. Last updated 2026-11-15.

**If you are an agent starting work here, read `docs/agent-handoff.md` first.** It has the context,
the rules and the open tasks. This section is only a summary.

- **Base case, done:** MODIS and VIIRS hotspots harmonized into one series (VIIRS-equivalent
  hotspots), and a web app with a burn calendar per area and period (`backend/`, `frontend/`).
- **EDA, done:** 9 of 9 blocks. Results in `docs/findings/`, decisions in `docs/eda-findings.md`,
  loose ends in `docs/eda-closing-plan.md`.
- **Added value, done for the deadline:**
  - A weekly outlook of where fire activity is most likely (`scripts/risk_model.py`).
  - A next-day outlook per 0.25° cell, with a reason for each alert and wind for the live day, shown
    in the app as "Next-day outlook" (`docs/findings/09-daily-model.md`). The model is frozen
    (technical handoff: `docs/daily-model-handoff.md`).
  - The area at risk: km² of the cells in alert, and for each fire of the day before the chance it is
    detected again and the zone where its next hotspots usually fall (`scripts/fire_zones.py`). How
    it is built and used: `docs/area-at-risk-guide.md`; results and limits: `docs/findings/10-fire-zones.md`.
  - Not built: a view of the current situation, burned area, perimeters, direction of spread.
- **Geography:** Chile and Argentina only. **Deadline:** Sunday 2026-11-15, 12:00 (Chile time).

How to build the data and run everything: `docs/eda-runbook.md`, then the scripts of
`docs/daily-model-handoff.md` (section 6). `NASA_Data_Sources/`, `External_Data_Sources/` and `.env`
are git-ignored. Never commit keys. Tests: `pytest` (about 140 tests, no real data needed).

Rules that never change:

- Count per day, month and year with `burn_date`, `burn_month`, `burn_year` (the day runs from 06:00
  to 06:00 local solar time). `acq_date`, `year` and `month` are UTC and only for matching FIRMS.
- Use the rows that pass the quality filter: `NASA_Data_Sources/processed/harmonized/hotspots_kept.parquet`.
- One satellite per period; never add satellites together.
- A hotspot is a thermal detection in a pixel: not a fire, not burned area, not damage. No detections
  does not mean no fire. A "fire" in this project is a group of hotspots of one day less than 1 km apart.
- No trend claims. Do not promise ignition prediction: say "where fire activity is most likely". A
  fire zone is where the next hotspots of a fire usually fall, not the area that will burn.
- Never push to `main`; one pull request per task; wait for the audit comment before merging.

Other tooling: the Runpod MCP server is configured in `.mcp.json` (`scripts/runpod_mcp.mjs` reads
`RUNPOD_API_KEY` from `.env`). Nothing in the project needs it: the models train in minutes on a laptop.
