# Incendios en Chile y Argentina: síntesis para el desafío MODIS–VIIRS

**NASA Space Apps Challenge 2026 · Antofagasta**  
**Fecha de investigación:** 14 de noviembre de 2026.  
**Propósito:** comprender el problema de los registros satelitales de actividad de fuego y su relación con los incendios recurrentes en Chile y Argentina. El documento reúne evidencia, contexto regional, límites de las fuentes y preguntas abiertas de investigación.

## 1. Hallazgos principales

- **El problema central es la comparabilidad de la historia observada del fuego.** Al cambiar de MODIS a VIIRS cambian la resolución, la sensibilidad y las oportunidades de observación. Una subida de detecciones puede deberse parcialmente al instrumento, además de a cambios reales del fuego.
- **Chile y Argentina tienen regímenes de fuego heterogéneos.** Chile central y Patagonia concentran actividad en verano; Córdoba y el Chaco presentan otros patrones. Los agregados nacionales no describen por completo esas diferencias.
- **Puntos calientes, incendios y hectáreas son indicadores distintos.** Un incendio puede producir muchas detecciones durante varios días; las quemas agrícolas también aparecen. El daño a personas y ecosistemas depende de la localización y exposición, además de la actividad térmica.
- **La ausencia de detecciones tiene varias explicaciones posibles.** Puede corresponder a ausencia de fuego, fuego no detectado, nubosidad o falta de observación. Un archivo de puntos por sí solo no distingue estas situaciones.
- **Las estadísticas institucionales también tienen límites de comparabilidad.** Cambian los períodos de reporte, la cobertura territorial y los métodos de registro. Las diferencias entre fuentes no representan necesariamente cambios reales en la actividad de fuego.

Las secciones siguientes desarrollan estos hallazgos, identifican sus fuentes y explicitan lo que no quedó verificado.

## 2. Qué pide el desafío y qué proviene del adjunto

El brief del desafío (resumido hoy en `docs/challenge-requirements.md`) describe **Harmonization of MODIS and VIIRS Hot Spots**: una aplicación web que combine el registro histórico de MODIS con VIIRS y permita consultar un calendario de actividad de fuego para una región y un intervalo temporal. La descripción pública del desafío corrobora ese objetivo general. [NASA Space Apps: desafío](https://www.spaceappschallenge.org/2026/challenges/harmonization-of-modis-and-viirs-hot-spots/).

Según el adjunto, sus dos componentes son armonizar los datos y visualizar la serie resultante. También menciona comparaciones históricas, descarga de resultados y selección de áreas; presenta rampas de color y algunas interacciones como sugerencias. **El método de armonización, la geografía y el alcance del prototipo quedan abiertos.** El foco Chile–Argentina procede de la solicitud del equipo.

**Límite de verificación:** se corroboraron el título y el resumen público indexado, pero no se recuperaron íntegramente las pestañas oficiales Details/Resources durante esta investigación. Por eso los requisitos detallados anteriores se atribuyen al adjunto, no a una nueva lectura completa de la página. Tampoco se verificaron el audio original, el ejemplo de Chilecito de julio de 2026 ni su afirmación sobre «casi diez años» de información que se perderían. Estos detalles permanecen sin verificación independiente.

Esta descripción documenta el contexto del desafío. El alcance de la investigación solicitada es entender el problema en Chile y Argentina.

## 3. Por qué importa en ambos países

### Chile: miles de eventos recurrentes y temporadas de daño excepcional

| Temporada | Incendios registrados | Superficie afectada |
|---|---:|---:|
| 2016–2017 | 5.274 | 570.197 ha |
| 2022–2023 | 6.982 | 429.103 ha |
| 2023–2024 | 5.958 | 73.835 ha |
| 2024–2025 | 6.272 | 91.631 ha |

Son temporadas completas, no años calendario. Fuentes: balances CONAF publicados por DIPRES para [2016–2017](https://www.dipres.gob.cl/597/articles-279870_doc_pdf.pdf) y [2022–2023](https://www.dipres.gob.cl/597/articles-340020_doc_pdf.pdf); para las últimas dos, [estrategia MINSAL 2025–2026, gráfico con fuente CONAF 2025](https://degreyd.minsal.cl/wp-content/uploads/2024/10/Estrategia-IIFF_2025-2026.pdf).

En 2022–2023, **167 incendios de al menos 200 ha —el 2,4% de los eventos— concentraron el 91,7% de la superficie afectada**. Esta concentración demuestra por qué el número de eventos no describe por sí solo la gravedad. [CONAF, Balance de Gestión Integral 2023](https://www.dipres.gob.cl/597/articles-340020_doc_pdf.pdf).

El régimen histórico se concentra principalmente entre **noviembre y marzo**, sobre todo en el centro-sur. La sequía prolongada, el calor, la humedad del combustible y el uso del suelo ayudan a explicar la variabilidad. Hay también actividad fuera del verano: la concentración estival no significa ausencia de incendios durante el resto del año. [CR2: megaincendios en un clima cambiante](https://www.cr2.cl/analisis-cr2-megaincendios-forestales-en-un-clima-cambiante/).

El incendio de **Valparaíso de febrero de 2024** evidencia otro aspecto: la proximidad a viviendas puede convertir un episodio relativamente localizado en una catástrofe social. La interfaz urbano-rural es el espacio donde asentamientos y vegetación se encuentran; su exposición ayuda a explicar por qué la superficie quemada y la gravedad social no guardan una relación simple. [NASA: Inferno Scars Valparaíso](https://science.nasa.gov/earth/earth-observatory/inferno-scars-valparaiso-152417/).

### Argentina: varios regímenes de fuego dentro del mismo país

Las ventanas orientativas de SINAGIR distinguen el verano austral en el sur, octubre–marzo en varias provincias del este/noreste y el período entre las primeras heladas y noviembre en Córdoba y otras provincias del centro/norte. Son orientaciones de riesgo, no límites fijos de ocurrencia. [SINAGIR: incendios forestales](https://www.argentina.gob.ar/sinagir/incendio-forestal).

Incluso dentro del Chaco hay diferencias: un estudio distingue una estación invierno–primavera en el Chaco seco y dos picos en el Chaco húmedo. La cobertura del suelo modifica la relación entre lluvia y fuego. [San Martín y colaboradores, Fire Ecology, 2023](https://link.springer.com/article/10.1186/s42408-023-00212-4).

Los siguientes casos ilustran distintas dimensiones del problema:

| Caso | Evidencia | Interpretación |
|---|---|---|
| Córdoba, 2024 | 586 incendios y 103.327 ha; el 76% de la superficie anual se quemó en septiembre. | Gran parte del daño anual se concentró en un solo mes. |
| Córdoba, 2025 | 675 incendios y 21.183 ha. | Hubo más eventos que en 2024, pero mucha menos superficie afectada. |
| Corrientes, enero–febrero de 2022 | Un estudio INTA/UNNE estimó más de 10.000 km² afectados, con fuerte participación de humedales. | La actividad de fuego afecta también ecosistemas distintos de los bosques. |

Fuentes: IDECOR, balances [2024](https://www.idecor.gob.ar/incendios-forestales-en-2024-datos-del-mapeo-provincial/) y [2025](https://www.idecor.gob.ar/incendios-forestales-y-rurales-en-2025-los-datos-oficiales-del-mapeo-provincial/); [Saucedo, Perucca y Kurtz, Ecología Austral, 2023](https://ojs.ecologiaaustral.com.ar/index.php/Ecologia_Austral/article/view/2020). IDECOR redujo desde 2024 su unidad mínima mapeable de 10 a 2 ha: los registros usados para estudiar tendencias también pueden cambiar de método.

Como referencia nacional, el CSV oficial de **superficie de incendios reportados**, descargado el 14/11/2026, suma 984.157 ha en 2020; 322.717 en 2021; 797.222 en 2022; 501.221 en 2023; 306.456 en 2024 y 466.722 en 2025. **Contiene provincias sin dato y no acredita cobertura exhaustiva**: estos valores no son directamente homologables al mapeo provincial ni a la tabla chilena. Sus columnas de 2026 tampoco tienen un corte visible y no se usan como balance anual. [Datos Argentina](https://datos.gob.ar/dataset/ambiente-incendios-forestales), [CSV oficial CIAM](https://ciam.ambiente.gob.ar/dt_csv.php?dt_id=416).

### Patagonia y los episodios de 2026: un caso binacional reciente

*State of Wildfires 2025–2026*, publicado el 11 de noviembre de 2026, analiza los incendios de enero en **Penco-Lirquén** y la **Patagonia norte**, incluidos Puerto Patriada y el entorno de Los Alerces. Identifica sequedad acumulada y condiciones meteorológicas extremas durante los episodios. Son eventos en ambos lados de los Andes; eso no implica que fueran un único incendio que cruzó la frontera. [Informe científico, secciones 6.1–6.2](https://essd.copernicus.org/articles/18/8037/2026/).

Estos episodios muestran que ambos países pueden experimentar condiciones favorables al fuego durante un mismo período, en territorios y ecosistemas distintos. La coincidencia temporal no demuestra una causa única. La descripción de anomalías históricas y la atribución causal al cambio climático son preguntas científicas diferentes.

### Causa humana y clima deben distinguirse

CONAF estima un origen humano del 99,7% de los incendios y SINAGIR comunica aproximadamente 95% para Argentina. Son estimaciones institucionales generales, no porcentajes calculados de manera homogénea para el mismo año; tampoco significan que todos sean intencionales. El satélite no permite determinar culpabilidad o legalidad. [CONAF: prevención](https://www.conaf.cl/incendios/prevencion-y-mitigacion/), [SINAGIR](https://www.argentina.gob.ar/sinagir/incendio-forestal).

Además, existen quemas de manejo agrícola y forestal. En Chile, «calendario de quemas» designa el sistema de días y horarios autorizados. Ese uso normativo del término es distinto del calendario histórico de actividad térmica descrito en el desafío. Una detección satelital no determina por sí sola si una quema estaba autorizada. [CONAF: uso del fuego](https://www.conaf.cl/incendios/prevencion-y-mitigacion/uso-del-fuego/).

## 4. Por qué los registros satelitales no son directamente comparables

| Aspecto | MODIS | VIIRS distribuido por FIRMS | Consecuencia |
|---|---|---|---|
| Resolución nominal de fuego activo | Aproximadamente 1 km | Aproximadamente 375 m | Un mismo frente puede generar más puntos VIIRS. |
| Sensibilidad | Menor para determinados fuegos pequeños | Mayor sensibilidad a fuegos pequeños y mejor detección nocturna | Los conteos no representan exactamente la misma población de fuegos detectables. |
| Confianza | Escala 0–100 | Categorías baja/nominal/alta | Las escalas de confianza no son equivalentes entre productos. |
| Plataformas | Terra y Aqua | S-NPP, NOAA-20 y NOAA-21 | Más satélites implican más oportunidades de observar un mismo fuego. |

Fuentes: descripciones NASA de [MODIS](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html) y [VIIRS](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html).

También cambian el horario de paso, el tamaño real del píxel fuera del nadir, las nubes y la disponibilidad de datos. La literatura reciente modela explícitamente esas diferencias: **no hay fundamento para adoptar un factor universal de conversión de conteos**. [Sofiev y Kouznetsov, 2026](https://gmd.copernicus.org/articles/19/10123/2026/).

Tres límites de interpretación:

1. **Un hotspot es una detección térmica dentro de un píxel.** Puede repetirse entre días, pasadas o satélites; también puede corresponder a volcanes o fuentes industriales. No identifica automáticamente un incendio independiente.
2. **Ausencia de puntos no demuestra ausencia de fuego.** Un CSV de detecciones no informa por sí solo si hubo observación despejada, nube o falta de cobertura. Esas categorías se encuentran en productos más completos, con máscaras de observación y controles de calidad; no en la sola lista de puntos. [Guía NASA VIIRS](https://viirsland.gsfc.nasa.gov/PDF/VIIRS_activefire_User_Guide.pdf).
3. **FRP no es superficie quemada.** Es potencia radiativa del fuego, expresada en MW. Tampoco corresponde multiplicar puntos por 1 km² o por 375×375 m para calcular hectáreas. [Descripción MODIS](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html).

## 5. Fuentes de información y sus límites

### FIRMS: base del registro histórico y reciente

El archivo consultado anuncia MODIS desde noviembre de 2000; S-NPP desde enero de 2012 hasta el 2 de noviembre de 2026; NOAA-20 desde abril de 2018 y NOAA-21 desde marzo de 2023. [Archivo FIRMS](https://firms.modaps.eosdis.nasa.gov/download/).

**La distribución de nuevos datos S-NPP cesó permanentemente el 2 de noviembre de 2026**, según NOAA. El archivo histórico permanece disponible, mientras NOAA-20 y NOAA-21 corresponden a otras plataformas con VIIRS. La continuidad entre plataformas es otra dimensión del problema de comparabilidad. [NOAA: aviso de cese de distribución, actualización del 2/11/2026](https://www.nesdis.noaa.gov/news/update-4-cessation-of-suomi-national-polar-orbiting-partnership-s-npp-data-users-november-02-2026-1540-utc-and-decommissioning-issued-november-2-2026-1800-utc).

Los datos recientes casi en tiempo real —NRT— son provisionales y el archivo los sustituye por procesamiento estándar con un retraso aproximado de cinco meses. Una consulta posterior puede devolver valores revisados. La plataforma, colección y nivel de procesamiento forman parte de la definición del dato; la cobertura temporal también puede diferir entre servicios. [Archivo FIRMS](https://firms.modaps.eosdis.nasa.gov/download/).

FIRMS ofrece descargas de archivo y consultas mediante API. Esta investigación revisó la documentación y las fechas de disponibilidad anunciadas; no descargó ni analizó el registro completo de hotspots de Chile y Argentina. Por tanto, los sesgos regionales entre sensores no quedaron cuantificados aquí. [Area API](https://firms.modaps.eosdis.nasa.gov/api/area), [disponibilidad](https://firms.modaps.eosdis.nasa.gov/api/data_availability/).

### Datos regionales para contraste

| Fuente | Qué aporta | Límite de interpretación |
|---|---|---|
| [CONAF: incendios 2010–2025](https://geoportal.cl/index.php/geoportal/catalog/42633/incendios-forestales-temporadas-2010-2025) | Puntos de origen, atributos del evento y superficie; temporadas julio–junio. | El origen no coincide necesariamente con todos los hotspots del incendio. |
| [IDECOR: áreas quemadas](https://www.idecor.gob.ar/mapas-de-areas-quemadas/) | Polígonos y registros provinciales de Córdoba. | Sus cambios de método y unidad mínima mapeable afectan la comparabilidad temporal. |
| [CONAE: consulta de focos y áreas quemadas](https://catalogos5.conae.gov.ar/catalogofocos/default.aspx) | Consulta regional de actividad e imágenes/productos. | La presencia de datos de ambos sensores no demuestra por sí sola que estén armonizados. |
| [CONAF: riesgo e interfaz](https://www.conaf.cl/incendios/analisis-nacional-de-riesgo-de-incendios-forestales/) | Contexto territorial de amenaza y exposición. | Es un análisis con metodología propia, distinto del conteo de actividad térmica. |

NASA FIRMS, CONAE y CONAF ya permiten monitorear puntos activos; **GWIS ofrece estadísticas históricas y comparaciones estacionales**, incluyendo series MODIS y VIIRS por separado. La existencia de herramientas de consulta y la comparabilidad científica de sus series son aspectos diferentes. [GWIS: aplicaciones](https://gwis.jrc.ec.europa.eu/applications), [CONAF: herramientas](https://www.conaf.cl/incendios/).

El producto MODIS MCD64A1 mide área quemada utilizando reflectancia y observaciones de fuego activo MODIS. Representa una variable distinta de los hotspots y comparte información con ese sensor: una coincidencia entre ambos productos no es una comprobación completamente independiente. [NASA: MCD64A1](https://www.earthdata.nasa.gov/data/catalog/lpcloud-mcd64a1-061).

## 6. Preguntas abiertas y límites de esta investigación

| Pregunta sobre el problema | Qué se conoce | Qué no quedó establecido aquí |
|---|---|---|
| ¿Qué parte de una variación del conteo es real y qué parte es instrumental? | Los sensores y plataformas tienen diferencias documentadas de resolución, sensibilidad y observación. | El tamaño y la variación regional de esos efectos en Chile y Argentina. |
| ¿Cuánto fuego no aparece en los archivos de puntos? | Las nubes, la falta de observación y los límites de sensibilidad pueden generar omisiones. | La tasa de omisión por ecosistema, estación y tipo de fuego en ambos países. |
| ¿Qué relación hay entre detecciones, eventos y daño? | Los ejemplos regionales muestran que la cantidad de eventos y la superficie afectada pueden evolucionar de forma distinta. | Una relación cuantitativa general entre hotspots, incendios individuales, superficie y consecuencias sociales. |
| ¿Hasta dónde son comparables las estadísticas oficiales? | Existen diferencias de cobertura, períodos de reporte y unidad mínima mapeable. | Una conciliación exhaustiva entre los registros nacionales, provinciales y satelitales. |
| ¿Los años extremos describen una tendencia sostenida? | Hay temporadas y episodios extremos documentados en ambos países. | Una estimación propia de tendencia multidecenal que separe los cambios observacionales de los cambios del fuego. |

Los ejemplos documentados describen dimensiones del problema; no constituyen un análisis completo de todas las regiones de Chile y Argentina. Los porcentajes generales sobre origen humano tampoco explican la causa de cada episodio. La estacionalidad describe concentraciones históricas y no determina cuándo ocurrirá el siguiente incendio.

La comparabilidad temporal también depende del período considerado: año calendario, temporada julio–junio de CONAF o acumulado parcial. Los registros de 2026 consultados no se presentan como cierres nacionales completos. Los detalles del desafío que solo pudieron leerse en el adjunto conservan el límite de verificación señalado en la sección 2.
