# Guide to the documents

What each document in this repository is for, and which ones to read first. Updated on 2026-11-15.

Every document is in English except one, marked below. Numbers and decisions live in one place each:
if two documents disagree, the one marked **current** wins.

## New to the project: read these, in this order

| Step | Document | Why |
|---|---|---|
| 1 | `challenge-requirements.md` | What NASA asks, in one page |
| 2 | `../README.md` | How to get the data, build the hotspot table and run the web app |
| 3 | `eda-findings.md` | Every decision already taken, in tables. Read it before changing anything |
| 4 | `findings/03-modis-vs-viirs.md` | How MODIS and VIIRS were put on one scale: the core of the challenge |
| 5 | `findings/09-daily-model.md` | The next-day outlook: what it does, how well, and its limits |
| 6 | `../CONTRIBUTING.md` | Rules for branches, commits and pull requests |

## At the root of the repository

| Document | What it is |
|---|---|
| `README.md` | How to get the data, build the unified hotspot table, run the web app and add the risk layer |
| `CONTRIBUTING.md` | Language (English), commit format, pull request rules |
| `CLAUDE.md` | Short status of the project and the rules that never change. AI agents read it first |

## The challenge and its background

| Document | What it is | State |
|---|---|---|
| `challenge-requirements.md` | What the challenge asks, summarized from the official page | Current |
| `background.md` | The sensors (MODIS, VIIRS), the literature and the data sources | Reference |
| `population-and-past-fires.md` | Population data sources, the exposure method and the past fires used as cases | Reference |

## Data: how to build it and what each file holds

| Document | What it is | State |
|---|---|---|
| `eda-runbook.md` | **How to run everything**: downloads, the pipeline step by step with expected numbers and times, each notebook, and which file answers which question | Current |
| `data-contracts.md` | The files that the modules hand to each other, with their columns | Current |

## The exploratory analysis (EDA)

| Document | What it is | State |
|---|---|---|
| `eda-findings.md` | **The decision record**: one row per decision, with the block that took it | Current |
| `eda-plan.md` | The original plan of the nine blocks | Historical: it is what was planned, not what was found |
| `eda-closing-plan.md` | What is solid in the EDA, its loose ends, and what it settles for the product | Current for the open questions |
| `findings/eda-summary-and-harmonization.md` | A second reading of the EDA by another team member: key results and what they mean for the harmonization | Current, written before blocks 2 and 8 |

One findings file per block, each with its notebook in `notebooks/`:

| Document | Question it answers |
|---|---|
| `findings/00-time-audit.md` | Which clock and which day to count with (`burn_date`, 06:00 to 06:00 solar time) |
| `findings/01-quality.md` | Which hotspots to keep: confidence, static heat sources, volcanoes, outages |
| `findings/02-observation-effort.md` | How much each satellite really sees, and what "no hotspots" means |
| `findings/03-modis-vs-viirs.md` | How MODIS compares with VIIRS, the harmonization method and how accurate it is |
| `findings/03b-pre2012-level.md` | Why the series is higher before 2012 (it is in the raw data, not caused by the method) |
| `findings/04-calendar.md` | Seasons, anomalies and how to draw the burn calendar |
| `findings/05-spatial.md` | Where fire is, fire regimes, and the smallest cell that makes sense |
| `findings/06-case-studies.md` | Whether known fires (Valparaíso 2024 and others) show up in the data |
| `findings/07-population.md` | How many people live near the hotspots |
| `findings/08-risk-model.md` | The weekly outlook: inputs, validation, what weather adds |
| `findings/09-daily-model.md` | The next-day outlook: results, reasons, rings, wind, limits |

The `.png` files in `findings/` are the figures of those documents.

## The prediction models

| Document | What it is | State |
|---|---|---|
| `eda-conclusions-for-modeling.md` | What the EDA settles before training: targets, data rules, where the signal is, numbers to beat | Current |
| `modeling-plan.md` | The plan of the next-day model. **Section 0 is what was done**; sections 1 to 14 are the full brief (four models, three algorithms), which was not done | Section 0 current, the rest historical |
| `findings/09-daily-model.md` | Results of the next-day model and why it is frozen | Current |
| `daily-model-handoff.md` | **Technical handoff** of the next-day model: data, techniques, how to run it again, traps, next steps | Current |
| `findings/08-risk-model.md` | The weekly outlook, which is older and has a different target | Current |

## Working on the project

| Document | What it is | State |
|---|---|---|
| `agent-handoff.md` | Context, rules and task cards for AI agents | Tasks T1 to T4 are done; T5 to T9 are still open; the model work came after it |

## Which document answers my question

| Question | Document |
|---|---|
| How do I get the data and run the pipeline? | `eda-runbook.md` |
| Why is the day not the calendar day? | `findings/00-time-audit.md` |
| Why were these hotspots dropped? | `findings/01-quality.md` |
| What is a "VIIRS-equivalent hotspot" and how good is the estimate? | `findings/03-modis-vs-viirs.md` |
| What did we decide about X? | `eda-findings.md` |
| What can and cannot be claimed in the pitch? | `eda-closing-plan.md`, and the "Limits" section of each findings file |
| How was the next-day model trained, and how do I retrain it? | `daily-model-handoff.md` |
| What do the columns of this file mean? | `data-contracts.md`, `eda-runbook.md` |
