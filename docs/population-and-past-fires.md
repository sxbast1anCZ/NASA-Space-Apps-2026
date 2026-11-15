# Population Exposure and Past Fire Case Studies

> Part of the **extension** (risk and impact), built on top of the harmonized burning activity calendar.
> Scope: Chile and Argentina. Compiled on 2026-11-14. Sources are listed at the end.

---

## 1. Population data sources

| Source | Resolution | Years | Role |
|---|---|---|---|
| **WorldPop R2025A (constrained)** | ~100 m GeoTIFF | 2015–2030, yearly | **Primary layer.** Same method for both countries, no break at the border. Fine enough to separate a populated hillside from an empty one (wildland-urban interface). |
| **NASA GPWv4** | ~1 km (0.008333°) | 2000–2020, every 5 years | NASA-branded alternative and fallback. Lighter, but too coarse for interface analysis. |
| **GHSL (EU JRC)** | ~100 m | 1975–2020, every 5 years | Population, built-up surface and degree of urbanization. The built-up layer can flag the wildland-urban interface directly. |
| **Chile Census 2024 (INE)** | City block / rural entity | 2024 | Official validation for Chile. 189 variables (people, households, dwellings) with updated census cartography. |
| **Argentina Census 2022 (INDEC)** | Census radius (`radio censal`) | 2022 | Official validation for Argentina. A ready-to-use Parquet version with CONICET radius cartography exists on source.coop. |

### Download

```bash
./scripts/download_population.sh            # WorldPop 2024 for Chile and Argentina
YEAR=2020 ./scripts/download_population.sh  # any year from 2015 to 2030
```

Output goes to `External_Data_Sources/WorldPop/<Country>/` (git-ignored).

---

## 2. Exposure method

1. **Group hot spots into events.** Nearby detections in space and time belong to the same fire.
2. **Build rings** of 1, 5 and 10 km around each event, plus a **downwind sector** using wind direction (NASA POWER or Open-Meteo forecast).
3. **Sum the population raster** inside each ring and sector (`rasterio` or `exactextract` in Python).
4. **Output:** "about X people within 5 km, Y of them downwind".

Precompute this per grid cell once, so the web app never loads the full rasters.

### Important limits

- **Exposure is not damage.** We report who is near the fire, not who will be affected. Hot spots do not measure burned area (see `docs/modeling-plan.md`, section 9).
- Gridded population models residential population. Tourists and seasonal workers are not included (relevant for Puerto Patriada).
- Wind direction is a simple heuristic, not a fire spread simulation.

---

## 3. Past fire case studies

| Event | Impact | Why it matters for the pitch |
|---|---|---|
| **Valparaíso region, 2–3 Feb 2024** | 138 deaths (final count, Public Prosecutor). 6,974 homes destroyed, 65% of all homes destroyed by wildfires in the region over 10 years. Burned 34% of Viña del Mar and 38% of Valparaíso municipal area. About 9,216 ha (CIGIDEN). | **Central case.** Relatively small area, huge human impact because of nearby population. Directly justifies the exposure analysis. |
| **Ñuble, Biobío and La Araucanía, Feb 2023** | 25 deaths, about 441,000 ha, 1,987 homes destroyed, 7,038 people affected (Senapred, 19 Feb 2023). | **Contrast.** Far more hectares, fewer deaths. Area burned does not equal impact. |
| **Chile 2017 season** | 11 deaths, about 6,000 people affected, more than 1,500 homes destroyed, 467,000 ha. | Largest burned area on record. Both sensors saw it (Suomi-NPP has data since January 2012): VIIRS recorded 3.3 times as many hotspots as MODIS, so it shows the gap the harmonization closes. |
| **Torres del Paine, Dec 2011 – Jan 2012** | Started on 27 Dec 2011 near Lago Grey, about 17,600 ha of the national park. | **MODIS-only case.** Before VIIRS existed. The harmonized calendar ranks December 2011 first of 26 years for that area. |
| **Paraná Delta, Apr 2008** | About 207,000 ha of wetland islands (Entre Ríos and Buenos Aires); smoke covered Buenos Aires on 15–20 April. | **MODIS-only case.** The hotspot peak (18 April) falls inside the smoke episode, and the month ranks first of 26 years. |
| **Puerto Patriada, Chubut, Jan–Feb 2026** | Started 5 Jan, more than 30,000 ha of native forest, plantations and shrubland, controlled after 39 days. More than 3,000 people evacuated. Preventive evacuation avoided deaths. | **Positive counterexample.** Early warning and timely evacuation saved lives, which is what our tool supports. |
| **Córdoba 2024 and 2025, Corrientes 2022** | Córdoba 2024: 586 fires and 103,327 ha, 76% of it in September; Córdoba 2025: 675 fires but 21,183 ha (IDECOR provincial mapping, [2024](https://www.idecor.gob.ar/incendios-forestales-en-2024-datos-del-mapeo-provincial/), [2025](https://www.idecor.gob.ar/incendios-forestales-y-rurales-en-2025-los-datos-oficiales-del-mapeo-provincial/); IDECOR lowered its minimum mapped unit from 10 to 2 ha in 2024). Corrientes, Jan–Feb 2022: more than 10,000 km² affected, much of it wetland ([Saucedo, Perucca and Kurtz, Ecología Austral, 2023](https://ojs.ecologiaaustral.com.ar/index.php/Ecologia_Austral/article/view/2020)). | Different fire regimes inside Argentina. More fires does not mean more area burned, and fire also hits wetlands, not only forest. |
| **Chilecito, La Rioja, Jul 2026** | Example used by the challenge author (CONAE) in her audio briefing. | Connects our work to the author's own use case. |

### Demo idea: "What would the tool have shown?"

Replay **Valparaíso, 2 Feb 2024**:

1. Hot spots detected on 2–3 Feb 2024 on the map.
2. The harmonized calendar shows February as peak season for that area.
3. Weather context: heat and wind on those days.
4. Population within 5 km of the first detections.

This connects all four layers (harmonization, calendar, risk, exposure) in one real case.

What the satellites recorded for every case, pass by pass for Valparaíso: `docs/findings/06-case-studies.md`.

**Note:** official tolls changed a lot over the following days and months (Valparaíso started at 19 deaths and ended at 138). Always quote the final official figure with its source.

---

## 4. Sources

### Population
- [WorldPop population counts](https://hub.worldpop.org/project/categories?id=3)
- [WorldPop R2025A, 2015–2030 (100 m)](https://hub.worldpop.org/geodata/listing?id=135)
- [Comparison of gridded population datasets (IPUMS DHS)](https://tech.popdata.org/dhs-research-hub/posts/2024-08-30-pop-density/index.html)
- [NASA GPW datasets and tools (Earthdata)](https://www.earthdata.nasa.gov/data/projects/gpw/data-access-tools?page=0%2C3)
- [INE Chile, Census 2024 block-level data and cartography](https://www.radioagricultura.cl/noticias/nacional/ine-publica-bases-de-datos-a-nivel-de-manzana-y-cartografia-del-censo-de-poblacion-y-vivienda-2024_20251216/)
- [Argentina Census 2022 by census radius (source.coop)](https://source.coop/nlebovits/censo-argentino/2022)

### Past fires
- [Torres del Paine 2011, start of the fire (The Clinic)](https://www.theclinic.cl/2011/12/28/incendio-que-ha-quemado-20-hectareas-mantiene-en-alerta-roja-a-torres-del-paine/)
- [Paraná Delta 2008, official report (Secretaría de Ambiente)](https://www.argentina.gob.ar/sites/default/files/2025/07/2008_-_abril_incendios_delta_del_rio_parana_1.pdf)
- [Valparaíso 2024, 138 deaths (CNN Chile)](https://www.cnnchile.com/pais/fiscalia-suma-dos-nuevos-fallecidos-eleva-138-victimas-fatales-megaincendio-valparaiso/)
- [Valparaíso 2024, homes destroyed (Ex-Ante)](https://www.ex-ante.cl/?p=197213)
- [Valparaíso 2024, CIGIDEN damage report (Emol)](https://www.emol.com/noticias/Nacional/2024/02/15/1121815/cigiden-informe-danos-incendios-valparaiso.html)
- [February 2023 fires, daily tolls (Diario Financiero)](https://www.df.cl/empresas/actualidad/minuto-a-minuto-reportan-ocho-incendios-forestales-relevantes-en-cinco)
- [February 2023 fires and the 2017 precedent (TVN)](https://www.tvn-2.com/mundo/incendios-forestales-chile-no-ceden_1_2034335.html)
- [Puerto Patriada controlled after 39 days (ANBariloche)](https://www.anbariloche.com.ar/noticias/2026/02/13/102378-tras-39-dias-de-combate-declaran-controlado-el-incendio-de-puerto-patriada)
- [Puerto Patriada evacuations (Diario de Cuyo)](https://www.diariodecuyo.com.ar/argentina/incendios-en-chubut-la-investigacion-confirmo-hallazgos-de-combustible-donde-se-inicio-el-fuego-1818865.html)
- [Puerto Patriada, no fatalities (Cholila Online)](https://cholilaonline.ar/2026/01/el-incendio-en-puerto-patriada-destruyo-viviendas-sin-victimas.html)
