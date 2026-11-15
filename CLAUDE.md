# NASA Space Apps 2026: harmonized MODIS and VIIRS hotspots

What the challenge asks: `docs/challenge-requirements.md`. Conventions: `CONTRIBUTING.md`.
What each document is for: `docs/README.md`.

## Project status

> Written in English per `CONTRIBUTING.md`. Last updated 2026-11-15.

**If you are an agent starting work here, read `docs/agent-handoff.md` first.** It has the context,
the rules and the open tasks. This section is only a summary.

- **Base case, done:** MODIS and VIIRS hotspots harmonized into one series (VIIRS-equivalent
  hotspots), and a web app with a burn calendar per area and period (`backend/`, `frontend/`).
- **EDA, done:** 9 of 9 blocks. Results in `docs/findings/`, decisions in `docs/eda-findings.md`,
  loose ends in `docs/eda-closing-plan.md`.
- **Added value, in progress:** a weekly outlook of where fire activity is most likely is in the app
  (`scripts/risk_model.py`). A next-day outlook is trained, with a reason for each alert and wind for
  the live day, and it is in the app as "Next-day outlook" (`docs/findings/09-daily-model.md`); the
  model is frozen (technical handoff: `docs/daily-model-handoff.md`). The outlook also gives the area
  of the cells in alert, and for each fire of the day before the chance it is detected again and the
  zone where its next hotspots usually fall (`scripts/fire_zones.py`, `docs/findings/10-fire-zones.md`).
  A view of the current situation is not built.
- **Geography:** Chile and Argentina only. **Deadline:** Sunday 2026-11-15, 12:00 (Chile time).

How to build the data and run everything: `docs/eda-runbook.md`. `NASA_Data_Sources/`,
`External_Data_Sources/` and `.env` are git-ignored. Never commit keys.

Rules that never change:

- Count per day, month and year with `burn_date`, `burn_month`, `burn_year` (the day runs from 06:00
  to 06:00 local solar time). `acq_date`, `year` and `month` are UTC and only for matching FIRMS.
- Use the rows that pass the quality filter: `NASA_Data_Sources/processed/harmonized/hotspots_kept.parquet`.
- One satellite per period; never add satellites together.
- A hotspot is a thermal detection in a pixel: not a fire, not burned area, not damage. No detections
  does not mean no fire.
- No trend claims. Do not promise ignition prediction: say "where fire activity is most likely".
- Never push to `main`; one pull request per task; wait for the audit comment before merging.

Other tooling: the Runpod MCP server is configured in `.mcp.json` (`scripts/runpod_mcp.mjs` reads
`RUNPOD_API_KEY` from `.env`). Nothing in the project needs it: the risk model trains in seconds on a laptop.
