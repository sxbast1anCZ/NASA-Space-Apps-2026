# Block 6 findings: Valparaíso, February 2024

Source: `notebooks/06_case_studies.ipynb`. Plan: `docs/eda-plan.md`, block 6, limited to this case
(`docs/work-split.md`, module M5).

**Status:** the notebook is ready and was tested end to end on a synthetic table with the real
schema. The numbers in "Results" are filled after running it on the real table.

## Case definition

| Field | Value |
|---|---|
| Fire | Complejo Las Tablas - Reserva Lago Peñuelas, then Lo Moscoso (Quilpué) |
| Box | Latitude -33.25 to -32.95, longitude -71.75 to -71.30 |
| Window | `burn_date` 2024-01-30 to 2024-02-10 |
| Reported start | 2024-02-02 12:05, `America/Santiago` (UTC-3 in February 2024) |
| Region in the table | Valparaíso (`admin1` contains "Valpara") |

## Reported timeline (civil time, 2 February 2024)

| Time | Event | Source |
|---|---|---|
| 12:00-13:00 | First sighting at Fundo Las Tablas, opposite the Lago Peñuelas reserve | UC technical note on the Peñuelas tower |
| 12:05 | CONAF brigades start work at Complejo Las Tablas (CONAF operations log) | BioBioChile |
| 12:50 | First local news alert | Ex-Ante |
| 13:09 | Route 68 cut at km 91 | Ex-Ante |
| Afternoon | CONAF reports 30 ha, then 480 ha, "extreme behaviour" | Ex-Ante, Meteored |
| 2-3 February | The fire reaches Viña del Mar, Quilpué and Villa Alemana | Government reconstruction plan |
| Final | About 9,216 ha (CIGIDEN), 138 deaths, 6,974 homes destroyed | `docs/population-and-past-fires.md` |

## What to expect from the satellites

From block 0 (`docs/findings/00-time-audit.md`): Aqua and the VIIRS satellites pass at about 13.5 to
14.5 h local solar time, and Terra at about 9.5 to 10.5 h. At longitude -71.5, local solar time is
UTC - 4.77 h, while civil time in February 2024 was UTC - 3 h. Civil time is therefore about 1.8 h
ahead of solar time:

| Pass | Local solar time | Civil time |
|---|---|---|
| Terra, morning | 9.5-10.5 h | about 11:15-12:15 |
| Aqua and VIIRS, afternoon | 13.5-14.5 h | about 15:15-16:15 |
| VIIRS, night | about 01:30 h | about 03:15 (next day, same `burn_date`) |

The Terra pass of 2 February is at or before the reported start, so the first possible detection is
the afternoon pass, **about 3 hours after the fire started**. This is a limit of polar-orbiting
hotspots that the pitch should state: they confirm and map a fire, they do not detect it in its first
minutes (geostationary sensors such as GOES do that, every 10 minutes, at coarser resolution).

## Results (fill after running the notebook)

| Question | Result |
|---|---|
| First detection per satellite and delay after 12:05 | _pending_ |
| Suomi-NPP / MODIS points on `burn_date` 2-3 February | _pending_ (block 3 factor for Valparaíso in February is in `factors.csv`) |
| February 2024 against the median February 2001-2023, case box and region | _pending_ |
| Rank of February 2024 among all Februaries | _pending_ |
| Risk percentile of the case cells in the week of 2 February 2024 (out of sample) | _pending_ |

Figures written by the notebook: `06-valparaiso-hotspots.png` (MODIS against VIIRS points, coloured
by hours after the start) and `06-valparaiso-february.png` (harmonized February counts per year).

## Limits

- Hotspots are not burned area: the event's 9,216 ha cannot be read from the point count.
- The box contains other fires of the same days (Camino Las Docas, Lo Moscoso). The notebook does not
  separate them; event clustering (block 3.7) was not done.
- Reported times come from press and official logs, with minutes of uncertainty.

## Sources

- [UC technical note on the Peñuelas tower (first sighting 12:00-13:00)](https://madera.uc.cl/images/proyectos/Documentos_Torre_experimental_Penuelas/nota-tecnica-torre-penuelas.pdf)
- [CONAF operations log, start at 12:05 (BioBioChile)](https://www.biobiochile.cl/noticias/nacional/region-de-valparaiso/2024/05/29/megaincendio-en-valparaiso-revelan-que-90-puntos-fueron-editados-en-bitacora-de-operaciones-de-conaf.shtml)
- [Timeline of 2 February 2024 (Ex-Ante)](https://www.ex-ante.cl/?p=196137)
- [CONAF report of 480 ha (Meteored)](https://www.meteored.cl/noticias/actualidad/violento-incendio-forestal-en-reserva-penuelas-obliga-a-cortar-transito-por-ruta-68-santiago.html)
- [Government reconstruction plan](https://www.desarrollosocialyfamilia.gob.cl/storage/docs/Plan_reconstruccion_140524.pdf)
