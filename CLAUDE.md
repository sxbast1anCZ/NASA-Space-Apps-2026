# NASA Space Apps Challenge 2026: Armonización de hotspots de MODIS y VIIRS

> **Versión en español.** El original para agentes/LLM es `challenge-brief.en.md` (inglés). Si hay dudas de interpretación, manda el original.
>
> **Fuentes combinadas en este archivo**
> 1. Página oficial del desafío (pestañas Details y Resources): https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/ (leída el 2026-11-14)
> 2. Audio de presentación de la autora del desafío (4:51), transcrito con Whisper y corregido a mano. Archivo original: `2026 Challenge Harmonization of MODIS and VIIRS Hot Spots.mp3`
>
> **Quién habla en el audio:** Marina Compagnucci, CONAE (Comisión Nacional de Actividades Espaciales, Argentina), grabado en el Centro Espacial Teófilo Tabanera, Córdoba, Argentina.
>
> **Cómo usar este archivo:** las secciones 1-8 son una síntesis estructurada de ambas fuentes. La sección 9 es la transcripción completa del audio, traducida. Si un resumen y una fuente no coinciden, manda la fuente. La sección 7 lista las diferencias entre la página oficial y el audio.

---

## 1. Metadatos (página oficial)

| Campo | Valor |
|---|---|
| Título del desafío | Harmonization of MODIS and VIIRS Hot Spots (Armonización de hotspots de MODIS y VIIRS) |
| Evento | 2026 NASA Space Apps Challenge |
| Dificultad | Intermedia, Avanzada |
| Materias | Ciencias de la Tierra (Earth Science), Software |
| Crédito de la foto del desafío | CONAE (Comisión Nacional de Actividades Espaciales de Argentina) |
| Pestañas de la página | Details, Resources, Teams |

## 2. Resumen en un párrafo

Construir una **aplicación web** que entregue un **calendario armonizado de actividad de quemas** basado en hotspots (puntos calientes) de incendio activo. Une el largo registro histórico de **MODIS** (Terra/Aqua, desde los 2000 hasta hoy, en retiro) con el registro más nuevo y detallado de **VIIRS**, de modo que el sensor de origen deje de importar. Los usuarios (equipos de respuesta a emergencias, científicos, gestores de tierras, bomberos) eligen un área de interés y un rango de fechas, y ven y descargan analíticas y visualizaciones de actividad de fuego: qué meses y años tuvieron más fuego y cómo se compara el mes actual con la mediana histórica.

## 3. Planteamiento del problema

- Los satélites han rastreado hotspots de incendio activo por **más de dos décadas**.
- El registro está **dividido entre sensores cuyos datos no se pueden comparar directamente**. MODIS y VIIRS difieren en:
  - resolución espacial
  - sensibilidad
  - horario de observación (horas de paso del satélite)
- Los sensores MODIS (en los satélites Terra y Aqua) **se acercan al final de su vida operativa** y están siendo reemplazados por VIIRS.
- Sin armonización, los gestores de incendios no tienen una imagen consistente de **cuándo y dónde hubo quemas**, y parte del registro histórico se pierde en la práctica.
- A medida que aumentan la frecuencia y la intensidad de los incendios, los gestores necesitan un calendario de hotspots actualizado y consistente para ver rápido, por ejemplo, **qué mes y qué años tuvieron la mayor actividad de fuego**, y para **comparar el mes actual con la mediana histórica** de un área seleccionada.

## 4. Objetivos (oficiales)

Desarrollar un **calendario armonizado de actividad de quemas** basado en hotspots de incendio activo, dentro de una aplicación web, que combine la extensa serie histórica de MODIS con la continuidad y el mayor detalle de VIIRS, para entregar una **serie temporal consistente de actividad de hotspots**.

Enfoque sugerido en **dos partes**:

### Parte 1: Armonización de hotspots
- Hacer comparables los hotspots de MODIS y VIIRS para que, al terminar esta fase, "el sensor de origen ya no importe y el foco sean los patrones, las tendencias y las anomalías".

### Parte 2: Aplicación web
- Recibe como entrada los datos de hotspots armonizados.
- El usuario puede **elegir una región y un rango de fechas específico**, y luego **descargar analíticas y visualizaciones** de la actividad de fuego.
- Incluye un **calendario de actividad de quemas** que muestre el **número de hotspots detectados desde principios de los 2000 hasta hoy**, construido sobre el dataset armonizado. Debería mostrar:
  - qué épocas del año tienen más incendios
  - qué años tuvieron más actividad de quemas
  - cómo se compara un incendio actual con los anteriores
- Opcional: **rampas de color** que representen similitudes y diferencias en el conteo de hotspots entre meses (accesibles e intuitivas).
- Opcional: un **CSV descargable** con los hotspots detectados en una búsqueda.

> El audio agrega: el usuario podría "elegir un día específico, una región particular, y visualizar su historial de actividad de fuego, y probablemente obtener algunas analíticas". Los equipos también pueden tomar un **enfoque completamente distinto**, que es "igual de bueno".

## 5. Consideraciones posibles (oficiales; opcionales, no obligatorias)

- **Público objetivo:** equipos de alerta temprana y respuesta a emergencias, científicos, gestores de tierras, bomberos.
- **Interactividad:** por ejemplo, un mapa donde el usuario **dibuje el área de interés**, o una opción para **ingresar latitud y longitud**.
- **Rampas de color accesibles.**
- Un **calendario de quemas** como vista central.
- Concentrarse en pocos índices y cifras clave, presentados como visualizaciones de datos, por ejemplo:
  - **comparaciones históricas**, incluidas **anomalías respecto de promedios multianuales**
  - **número de incendios detectados y reportados**
- La página dice que podrían agregarse más recursos antes del hackathon.

## 6. Datos y recursos

### Oficiales (pestaña Resources)
- **FIRMS (NASA Earthdata): Fire Information for Resource Management System**: https://www.earthdata.nasa.gov/data/tools/firms
  - Da acceso a imágenes satelitales globales casi en tiempo real, incendios/hotspots activos y productos relacionados (ubicación, extensión e intensidad de la actividad de incendios). La página sugiere "armonizar los hotspots de NASA Earthdata FIRMS".
- Aviso en la página: NASA no respalda a entidades no gubernamentales de EE. UU.; en sitios no gubernamentales de EE. UU., los participantes deben cumplir los términos de uso de datos de ese sitio.

### Del audio
- Usar el sitio de NASA FIRMS, más recursos de CONAE y de otras agencias espaciales.

### Otros enlaces oficiales
- Preguntas frecuentes para participantes: https://www.spaceappschallenge.org/resources/participant-faqs/
- Guías y recursos para participantes: https://www.spaceappschallenge.org/resources/
- Space Apps Connect (preguntas): https://github.com/nasa/spaceapps

## 7. Diferencias y vacíos entre las fuentes

- **Audio vs. página sobre la pérdida de datos:** el audio dice que sin un método de comparación "casi 10 años de información histórica se perderán" (transcripción de baja confianza; verificar escuchando el audio). La página oficial no da esa cifra; solo dice que el registro abarca "más de dos décadas".
- **Solo en el audio:** casos de uso de alerta temprana (incendios, inundaciones, derrames de petróleo), el ejemplo de Chilecito, La Rioja (Argentina, julio de 2026) y la frase de que los equipos pueden usar un enfoque completamente distinto.
- **Solo en la página:** dificultad, materias, descarga de CSV, rampas de color, comparación de anomalías contra la mediana histórica, idea de dibujar el área en un mapa, accesibilidad.
- **No especificado en ninguna fuente:** el método de armonización, el stack tecnológico, el alcance geográfico, el rango exacto de fechas, los criterios de evaluación y los productos o endpoints concretos de FIRMS a usar (por ejemplo, qué archivos de MODIS y VIIRS, qué filtros de confianza). Quedan a decisión del equipo.

## 8. Contexto del dominio

- Regímenes de fuego: algunos ecosistemas necesitan fuego periódico, pero los cambios en intensidad, extensión y frecuencia dañan el clima, la sociedad y la biodiversidad, y ponen en peligro vidas y bienes. Los incendios son cada vez más de origen humano.
- "Actividad de quemas" incluye incendios forestales en vegetación natural y bosques, además de fuegos de origen humano por agricultura, limpieza de terrenos, quema de residuos y actividades industriales.
- La detección se basa principalmente en mediciones de **infrarrojo medio (MIR) e infrarrojo térmico (TIR)**, donde la combustión activa produce su señal más fuerte. Los sensores térmicos también detectan erupciones volcánicas y calor industrial como las antorchas de gas.
- Durante un incendio activo, los hotspots ayudan a los científicos a ubicar dónde es más probable que haya fuego y a esperar el paso de un satélite. Luego las imágenes aportan detalle y, al final, un mapa del área quemada. Los hotspots siguen siendo útiles para juzgar dónde el fuego puede o no propagarse.
- Los modelos climáticos proyectan que el clima propicio para incendios será más común e intenso.
- Audio: el equipo de CONAE da alerta temprana y respuesta a emergencias por eventos que duran de días a semanas. **Casi la mitad son incendios.**

### Glosario
| Término | Significado |
|---|---|
| MODIS | Moderate Resolution Imaging Spectroradiometer, en Terra y Aqua. Registro largo, en retiro. |
| VIIRS | Visible Infrared Imaging Radiometer Suite. Sensor sucesor, más detalle, continuidad. |
| Hotspot | Píxel detectado por satélite con alta probabilidad de incendio activo. |
| FIRMS | Fire Information for Resource Management System de NASA. |
| TIR / MIR | Bandas de infrarrojo térmico / medio usadas para detectar incendios activos. |
| AOI | Área de interés seleccionada por el usuario. |
| Calendario de actividad de quemas (de fuego) | Vista tiempo-por-región del conteo de hotspots que muestra patrones estacionales, anomalías y tendencias. |
| CONAE | Comisión Nacional de Actividades Espaciales, la agencia espacial de Argentina. |

---

## 9. Transcripción completa del audio (traducida al español)

El audio original está en inglés; el texto en inglés corregido está en `challenge-brief.en.md`. Frases de menor confianza: "visualizar su historial de actividad de fuego" (la transcripción cruda decía "fire duty history") y "casi 10 años".

Hola, soy Marina Compagnucci de la CONAE, la Agencia Espacial Argentina. En este momento estamos en el Centro Espacial Teófilo Tabanera, ubicado en Córdoba, Argentina. Soy autora del desafío llamado Armonización de hotspots de MODIS y VIIRS.

Tengo el privilegio de trabajar con un equipo de científicos que brindan alerta temprana y respuesta a emergencias ante diversos eventos que ocurren alrededor del mundo. Esos eventos son incendios, inundaciones y derrames de petróleo, que pueden durar desde unos pocos días hasta incluso semanas. Casi la mitad de esas emergencias son incendios. Ya sean incendios forestales en áreas boscosas o incendios de origen humano por actividades agrícolas, industriales o de limpieza de terrenos.

En el caso de incendios en curso, estos científicos usan hotspots satelitales para monitorearlos y saber dónde están las mayores probabilidades de incendios activos. Pero hay otra herramienta poderosa que también usa hotspots, en este caso integrando datos históricos y recientes provenientes de los hotspots. Esta herramienta se llama Calendario de Actividad de Quemas, también Calendario de Actividad de Fuego, y ayuda a visualizar tendencias, anomalías o incluso patrones estacionales en el comportamiento del fuego. Por ejemplo, te muestra cuántos hotspots tiene un área en particular a lo largo de distintos años. Consideren que los modelos climáticos proyectan que el clima propicio para incendios será más común e intenso, así que estas herramientas, tanto el calendario como los hotspots, son muy importantes.

Las imágenes que están viendo fueron procesadas para un incendio que ocurrió en Chilecito, La Rioja, Argentina, en julio de 2026. Al comienzo del evento, los científicos usaron hotspots para inspeccionar el área y esperar el paso de un satélite. Luego, con las imágenes, pueden trabajar con más detalle, pero los hotspots siguen siendo importantes, ya que pueden identificar áreas donde los incendios podrían o no propagarse. Hacia el final del evento, tienen más detalle del área quemada.

Ahora sí hemos llegado al núcleo del desafío. Aunque MODIS y VIIRS han rastreado hotspots de incendio activo por más de dos décadas, el problema es que este registro está dividido entre dos sensores distintos cuyos datos no se pueden comparar directamente. ¿Por qué? Porque tienen distinta resolución espacial, distintas sensibilidades e incluso distintos horarios de observación. Y para empeorar las cosas, los sensores MODIS están terminando su vida operativa y siendo reemplazados por sensores VIIRS, así que si no existe un método para comparar sus datos, casi 10 años de información histórica se perderán, y los gestores de incendios se quedarán sin un calendario histórico que les diga cuándo y dónde han ocurrido incendios.

Por eso necesitamos su ayuda con este problema real y urgente. Su desafío, si deciden aceptarlo, es desarrollar un calendario armonizado de actividad de quemas que combine la extensa información histórica de MODIS con la continuidad y el mayor detalle de VIIRS, de modo que al final de este desafío tengamos una serie temporal consistente de actividad de hotspots. Todo esto en una aplicación web. Consideren usar el sitio web de NASA FIRMS y los recursos de nuestra agencia y de otras agencias para abordar este desafío.

Cuando pensamos el desafío, lo concebimos con dos partes para abordarlo. La primera es la armonización de hotspots de MODIS y VIIRS, de modo que al final de esta fase no importe si un hotspot vino de un sensor o del otro. El foco real está en las tendencias, anomalías y patrones que revelan.

La segunda parte es el desarrollo de la aplicación web que toma estos hotspots como entrada y los pone en un calendario, de modo que el usuario, por ejemplo, pueda elegir un día específico, una región particular, y visualizar su historial de actividad de fuego, y probablemente obtener algunas analíticas. O quizás ustedes y su equipo deciden abordar este desafío de una manera completamente distinta, y es igual de bueno.

Así que realmente esperamos con muchas ganas lo que su equipo se les ocurra. Saludos y mucha suerte.


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

El documento entregado, `challenge-brief.es.md`, describe **Harmonization of MODIS and VIIRS Hot Spots**: una aplicación web que combine el registro histórico de MODIS con VIIRS y permita consultar un calendario de actividad de fuego para una región y un intervalo temporal. La descripción pública del desafío corrobora ese objetivo general. [NASA Space Apps: desafío](https://www.spaceappschallenge.org/2026/challenges/harmonization-of-modis-and-viirs-hot-spots/).

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


## 7. convenciones
lee CONTRIBUTING.md para las convenciones

---

# Project status: data pipeline and EDA starting point

> **Current state, the full pipeline and the rules every block follows: `docs/eda-runbook.md`.**
> This section is older; where the two disagree, the runbook is right.

> Written in English per `CONTRIBUTING.md`. Last updated 2026-11-14.

## Team direction

- **Core (required by the challenge):** harmonise MODIS and VIIRS hotspots into one comparable series,
  then a web app with a burn activity calendar per region and date range.
- **Added value (our proposal):** a risk layer on top of the harmonised series: probability of fire
  activity per cell and week, and optionally probability of a large fire. Do not promise exact ignition
  prediction or hectares of damage. Baseline to beat: the historical median per cell and week.
- Geography: Chile and Argentina only.

## Data pipeline (reproducible from scratch)

```bash
pip install -r requirements.txt          # pandas, pyarrow, matplotlib, seaborn, shapely
./scripts/download_firms.sh              # yearly country CSVs, no key (96 files, ~573 MB)
./scripts/download_firms_api.sh          # 2026 + NOAA-21 via FIRMS Area API, needs FIRMS_MAP_KEY in .env
./scripts/download_boundaries.sh         # Chile + Argentina region polygons (~118 MB)
python scripts/build_hotspots.py         # unified Parquet table (~2 min)
```

| Step | Source | Output |
|---|---|---|
| Yearly files | FIRMS Country Yearly Summary (SP), clipped to country by FIRMS | `NASA_Data_Sources/<SENSOR>/<Country>/*.csv` |
| API files | FIRMS Area API, bbox `-76,-56,-53,-17`, SP while available then NRT, 5 days per request | `NASA_Data_Sources/<SENSOR>/API_bbox/<SENSOR>_<YYYY-MM>.csv` |
| Boundaries | Chile: geoBoundaries gbOpen CHL ADM1 simplified (16 regions). Argentina: IGN provinces WFS (24 provinces) | `NASA_Data_Sources/boundaries/<Country>.geojson` |
| Unified table | All of the above | `NASA_Data_Sources/processed/hotspots/year=YYYY/*.parquet` |

`NASA_Data_Sources/` and `.env` are git-ignored. Never commit keys.

Coverage by satellite: MODIS Terra 2000-11 →, Aqua 2002-07 →; VIIRS Suomi-NPP 2012-01 → 2026-11-02
(decommissioned), NOAA-20 2018-04 →, NOAA-21 2023-03 →. All end 2026-11-14 (download date).
**MODIS and VIIRS overlap 2012-2026: the harmonisation is calibrated in that window.**

## Unified table: `NASA_Data_Sources/processed/hotspots/`

Read with `pd.read_parquet("NASA_Data_Sources/processed/hotspots")`. `year` comes back as a category
(it is the partition column): cast with `.astype(int)`.

| Column | Meaning |
|---|---|
| `acq_datetime` (UTC), `acq_date`, `acq_time` (HHMM), `year`, `month`, `daynight` (D/N) | Acquisition time |
| `latitude`, `longitude` | Position |
| `country`, `admin1` | Country and region/province from the boundary polygons (same borders for every row) |
| `country_firms` | FIRMS' own country label, yearly rows only |
| `instrument` (MODIS/VIIRS), `satellite` (Terra, Aqua, Suomi-NPP, NOAA-20, NOAA-21) | Sensor |
| `processing` (SP/NRT), `version` | SP is final; NRT is provisional and gets replaced ~5 months later |
| `confidence_level` (low/nominal/high), `confidence_pct` (MODIS 0-100), `confidence_raw` | MODIS mapped as <30 low, 30-79 nominal, >=80 high |
| `bright_mir_k`, `bright_tir_k` | Brightness temperature: MODIS T21/T31, VIIRS I4/I5 (similar, not identical bands) |
| `frp_mw` | Fire radiative power (MW). Not burned area |
| `scan_km`, `track_km`, `pixel_area_km2` | Real pixel size (grows towards the swath edge) |
| `fire_type` | 0 vegetation, 1 volcano, 2 other static land source (e.g. gas flares), 3 offshore. Empty in NRT rows |
| `source` (`country_yearly`/`api_bbox`), `source_file` | Traceability |

What the merge does: common column names, normalised satellite names and time, common confidence level,
drops exact duplicates, labels country and region, drops API points outside Chile and Argentina
(they come from the bounding box). **It does not harmonise MODIS against VIIRS**: the sensor stays a
column. Harmonisation is the job of the EDA and the next step.

## Facts established so far

- 8,042,380 hotspots after merging (3 exact duplicates and 1,149,423 out-of-country API points dropped).
- Our country label agrees with FIRMS on 99.98% of yearly rows (1,205 disagree, all at the Chile-Argentina
  border). 10,476 yearly rows (0.15%, mostly coastal; Argentina 9,736, Chile 740) fall outside the
  simplified polygons: they keep FIRMS' country and have no `admin1`.
- **VIIRS detects about 4-6 times more points than MODIS per satellite** (2013: Suomi-NPP 261k, Aqua 46k).
- After clipping, NOAA-21 matches NOAA-20 (2024: 176,590 vs 179,307).
- MODIS has one collection version per year: `6.2` in 2000-2017, `6.03` in 2018-2022, `61.03` from 2023 to
  August 2026, `6.1NRT` from September 2026. The change to `61.03` happens when the orbit drift starts, so
  check jumps against VIIRS, not with MODIS alone.
- In 2026, MODIS is SP through August and VIIRS through July. Later months are NRT.
- In SP rows, static land sources (`fire_type` 2) are about 4% of points.
- 2020 is the peak year for every satellite.
- Most points are in northern Argentina (Formosa, Santa Fe, Corrientes, Santiago del Estero, Chaco, Salta).
  La Araucanía is the Chilean region with most points.
- Days with at least one detection per 0.25° cell narrow the VIIRS / MODIS gap to about 2.8 (2019-2021).
- 51,236 rows before 2002-07-04 are Terra only (no Aqua yet).
- Source asymmetries: Easter Island (467 rows) appears only in yearly files, because the API bounding box
  stops at -76°. Malvinas/Falklands (130 rows) appears only in API files.

## Time handling (measured and decided on 2026-11-14)

All numbers and the full rules are in `docs/eda-plan.md`. "Local solar time" is UTC hour + longitude / 15.

- `acq_datetime`, `acq_date`, `year`, `month` and the `year=` partition are **UTC**. Chile and Argentina
  are 3 to 5 hours behind.
- **Day key: `burn_date`** = `date(UTC + longitude / 15 h - 6 h)`, the day from 06:00 to 06:00 local solar
  time. It is the only cut that splits no satellite pass (0 rows between 04:30 and 07:00). Week, month,
  year and season (July-June) derive from it. The column does not exist yet: adding it
  (`scripts/timefields.py`) is the first step of the EDA.
- Do not count days by civil date: civil midnight splits the Terra night pass (Argentina: 86,043 rows at
  23 h, 63,529 at 00 h), which affects MODIS only. The UTC date is nearly clean but runs from about 20:00
  to 20:00 local time.
- UTC instants for time differences, local solar time for sensor questions, civil time (IANA zone per
  region, 16 zones) only for display, day of week and reported dates of past fires.
- Terra and Aqua orbits drift. Terra day pass: about 10.2 h local solar time through 2021, 8.6 h in 2026.
  Aqua: 13.9 h through 2022, 15.8 h in 2026. VIIRS is stable. Calibrate the harmonisation on 2012-2021.
- `daynight` follows the sun angle, not the pass.
- Last complete UTC day: 2026-11-13. November 2026 is partial: compare it only with the same days of
  other years.
- Tools: DuckDB needs `SET TimeZone='UTC'`. Never build JS dates from `YYYY-MM-DD` strings. Laptops run
  on Chile time, servers on UTC.

## Known limits of the data

- A hotspot is a thermal detection in a pixel, not a fire. One fire can produce many points; VIIRS
  (375 m) produces more points per fire than MODIS (1 km).
- No observation metadata (clouds, number of overpasses): absence of points does not prove absence of fire.
- No universal MODIS→VIIRS conversion factor exists (literature, see the research section above).
- Recent 2026 months are NRT: provisional and without `fire_type`. Re-running the API script refreshes them.
- Boundaries are simplified (~100 m tolerance). IGN's Tierra del Fuego polygon includes Malvinas and the
  Antarctic claim.

## Boundary sources

Full table and caveats in `README.md` ("Boundary sources"). Summary:

- **Chile: geoBoundaries** gbOpen CHL ADM1 simplified (William & Mary geoLab, release commit `9469f09`).
  16 regions. Original data from BCN and OCHA ROLAC. License CC BY 3.0 IGO (credit required).
- **Argentina: IGN** (Instituto Geográfico Nacional), WFS layer `ign:provincia`. 24 units (23 provinces
  and CABA), fields `nam` and `in1` (INDEC code). The service allows free reuse and redistribution under
  Art. 2 of Law 27.275; credit IGN.
- geoBoundaries' Argentina file is rejected (missing Entre Ríos, "La Roja", coarse geometry).
- The two sources do not share a border line: small gaps and overlaps along the Andes. First match wins,
  Argentina checked first. Part of the 1,205 disagreements with FIRMS come from this.
- Credit both sources in the web app.

## Gotchas found while building it

- geoBoundaries' Argentina ADM1 is missing Entre Ríos (and misspells La Rioja): do not use it.
- geoBoundaries' Chile names are mis-encoded (`RegiÃ³n`); `build_hotspots.py` fixes them.
- The FIRMS Area API omits the final newline in responses; `download_firms_api.sh` handles it now.
  Files downloaded before that fix were repaired (419 rows recovered).
- Do not run project scripts with `python -I`: pandas is installed in the user site-packages and `-I` hides it.
- `claude` CLI is not on PATH in the desktop app; MCP servers are registered in `.mcp.json`.

## EDA: where to start

The plan is in `docs/eda-plan.md`: time rules, the time fields to add to the table, and 9 blocks
(0 time audit, 1 quality, 2 observation effort, 3 MODIS vs VIIRS, 4 burn calendar, 5 spatial, 6 past fire
cases, 7 population, 8 risk model inputs). The time fields and block 0 come first; the other blocks can be
split among the team. No block has been run yet.

Decided: the day key is `burn_date`. Still open (the plan has a proposal for each):

- Week definition (proposal: 52 fixed 7-day bins) and year (calendar year and July-June season).
- Grid resolution (0.25°, also test 0.1°). Use density per km²: cell area shrinks about 40% from 20°S to 55°S.
- Whether to drop `low` confidence.
- Whether to drop `fire_type` 1-3 and how to flag static sources in NRT rows.
- Calibration window (proposal: 2012-2021) and reference pair (Aqua vs Suomi-NPP per pass; Terra has no
  VIIRS counterpart).
- Whether to group regions into fire regimes (Chaco, Pampas, central Chile, Patagonia) instead of
  administrative regions.
- Harmonisation candidates to test: ratio per regime/month, quantile mapping, days with fire, FRP
  detection threshold, event-based counts (clustering).
- Which population to use before 2015 (WorldPop covers 2015-2030).

Known issue: `docs/population-and-past-fires.md` says the 2017 season falls in the MODIS-only period, but
Suomi-NPP has data since January 2012.

Other tooling: the Runpod MCP server is configured in `.mcp.json` (`scripts/runpod_mcp.mjs` reads
`RUNPOD_API_KEY` from `.env`).