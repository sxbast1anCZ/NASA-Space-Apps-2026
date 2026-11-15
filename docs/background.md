# Background: sensors, literature and sources

What the team learned before the analysis that is not written anywhere else. The plan and the stack
that came with it were replaced by `docs/eda-findings.md` and the code.

## Key context

### MODIS is ending, and S-NPP has already stopped

- NASA plans to end data collection for **Terra MODIS in January 2027** and **Aqua MODIS around September 2027**.
- Both satellites are **drifting out of their orbits**. This has affected MODIS pixel size, scan gaps and diurnal sampling, with significant impacts since late 2024.
- **Important:** FIRMS **stopped producing new Suomi NPP (S-NPP) VIIRS data on 2026-11-02**. Historical S-NPP data stays available, but **recent data must come from NOAA-20 and NOAA-21**.

### Overpass times matter

- **Aqua MODIS and S-NPP VIIRS** cross the equator at about 13:30 and 01:30 local time. Their observations are nearly simultaneous, so they are the natural pair for calibration.
- **Terra MODIS** is the only morning overpass (about 3 hours before Aqua). It has no VIIRS counterpart.
- **NOAA-20 and NOAA-21** fly in the same orbital plane as S-NPP, about 50 minutes apart.

### The sensor gap is large and region-dependent

- MODIS pixel is **1 km**, VIIRS pixel is **375 m**. VIIRS detects many more and smaller fires.
- A study in Northeast Asia found that MODIS missed **65%** of VIIRS fire pixels in forests and **83%** in low-biomass lands.
- A study across South America found the S-NPP/Aqua detection ratio ranged from **6.81 (Venezuela)** down to **3.87 (Chile, the lowest)**, and it varied a lot even inside a country.
- **Conclusion:** a single global correction factor is not enough. Calibration must be **regional and seasonal**.

---

## Other data and services

- **CONAE Hot Spot Catalog** (Argentina): web catalog of MODIS and VIIRS hotspots. Useful for validation, and it is the catalog of the challenge author's agency.
- **FIRMS Static Thermal Anomalies layer**: FIRMS' own layer of industrial heat sources. The project built its own mask instead (`docs/findings/01-quality.md`).

## How the literature approaches harmonization

- **Regional statistical calibration.** The NASA VIIRS burned area paper (VNP64A1) states that regional-scale statistical calibration will likely be needed to build a single consistent MODIS/VIIRS record.
- **Region and biome lookup tables.** GFED5NRT converts VIIRS active fire counts into values consistent with the MODIS-era record using region- and biome-specific lookup tables.
- **Quantile mapping.** Widely used to remove cross-sensor bias (MODIS FRP swath bias in CAMS GFAS, the MRBA60 harmonized burned area dataset).

---

## Sources

- [FIRMS Archive Download](https://firms.modaps.eosdis.nasa.gov/download/)
- [FIRMS API, area endpoint](https://firms.modaps.eosdis.nasa.gov/api/area/csv)
- [FIRMS active fire data attributes (MODIS and VIIRS)](https://earthdata.nasa.gov/data/tools/firms/active-fire-data-attributes-modis-viirs)
- [Transitioning from S-NPP VIIRS: what FIRMS users need to know (NASA Earthdata)](https://www.earthdata.nasa.gov/news/blog/transitioning-from-s-npp-viirs-omps-what-nasa-firms-users-need-know)
- [Drifting away from MODIS: CAMS Global Fire Assimilation System](https://atmosphere.copernicus.eu/drifting-away-modis-cams-global-fire-assimilation-system)
- [MODIS Terra/Aqua drift (NASA LDOPE)](https://landweb.modaps.eosdis.nasa.gov/displayissue?id=1254)
- [ARSET 2026 Advanced FIRMS Q&A (static thermal anomalies, confidence)](https://d3vpnmsr9g81nw.cloudfront.net/s3fs-public/2026-02/arset-2026-advfirms-part2-qa.pdf)
- [MODIS vs VIIRS fire detection in Northeast Asia (Remote Sensing, 2020)](https://mdpi.com/2072-4292/12/18/2870)
- [Quantitative differences between Aqua/MODIS and S-NPP/VIIRS fire pixels in South America](https://periodicos.ufpe.br/revistas/jhrs/article/download/256618/43434)
- [NASA VIIRS burned area product VNP64A1](https://geog.umd.edu/sites/geog.umd.edu/files/pubs/1-s2.0-S0034425725004109-main.pdf)
- [GFED5NRT (ESSD, 2026)](https://essd.copernicus.org/articles/18/7535/2026/)
- [Correcting swath-dependent bias of MODIS FRP with quantile mapping (Remote Sensing, 2019)](https://www.mdpi.com/2072-4292/11/10/1205)
- [MRBA60 harmonized burned area dataset](https://meetingorganizer.copernicus.org/Plinius19/Plinius19-103.html)
- [CONAE Hot Spot Catalog user manual](https://catalogos5.conae.gov.ar/catalogofocos/Docs/033_CONAE_AQUA-TERRA-NOAA20_MODIS-VIIRS_FC_VISOR_ManualUsuarios_e01.pdf)
- [Chile 2022–2023 fire season (Ex-Ante)](https://www.ex-ante.cl/?p=145180)
- [Chile fire seasons by region (24horas)](https://www.24horas.cl/data/incendios-forestales-quemado-39-mas-hectareas-promedio-temporadas)
- [Valparaíso 2024 fire and vulnerability (Revista Planeo UC)](https://ojs.uc.cl/index.php/RP/article/download/75685/65916/258460)
