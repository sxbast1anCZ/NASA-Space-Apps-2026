// Interface text in Spanish (default) and English.
export type Lang = 'es' | 'en'

const es = {
  brand: 'Fireguard',
  brandSub: 'Calendario armonizado de fuego · Chile y Argentina',
  search: 'Buscar región o escribir "lat, lon"',
  modeHistory: 'Historia', modeNow: 'Ahora', modeForecast: 'Pronóstico',
  modeHistoryHint: 'Focos armonizados desde 2000', modeNowHint: 'Focos detectados los últimos días',
  modeForecastHint: 'Dónde es más probable la actividad',
  whole: 'Año completo', play: 'Reproducir', pause: 'Pausa',
  tomorrow: 'Próximo día', weeks: 'Próximas semanas', week: 'Semana del',
  layers: 'Capas', basemap: 'Mapa base', dark: 'Oscuro', satellite: 'Satélite',
  L_towns: 'Poblados', L_hotspots: 'Focos', L_heat: 'Calor', L_density: 'Densidad 3D', L_risk: 'Probabilidad', L_rings: 'Distancia',
  L_wind: 'Viento', L_regimes: 'Regímenes', L_static: 'Industria', L_regions: 'Anomalía regional', L_3d: 'Vista 3D',
  allArea: 'Chile y Argentina', drawBox: 'Dibujar área', clear: 'Quitar selección', drawHint: 'Arrastra en el mapa para dibujar el área',
  who: '¿Cómo vas a usar Fireguard?', whoSub: 'Elige tu perfil: ordenamos el mapa y los paneles para ti. Puedes cambiarlo cuando quieras.',
  start: 'Entrar al mapa', profile: 'Perfil',
  more: 'Ver más', less: 'Ver menos',
  last7: 'Focos últimos 7 días', vsMedian: 'vs. mediana 2013–2025', alertsTomorrow: 'Celdas en alerta, próximo día',
  thisMonth: 'Este mes', rankOf: 'de', rankMonth: 'lugar entre', years: 'años',
  calendar: 'Calendario de quemas', count: 'Cantidad', anomaly: 'Anomalía',
  typicalYear: 'Año típico vs. este año', last30: 'Últimos 30 días vs. lo normal',
  ranking: 'Regiones: semana vs. lo normal', sensors: 'MODIS vs. VIIRS: crudo y armonizado',
  downloads: 'Descargas', csv: 'CSV de focos', json: 'Calendario (JSON)', png: 'Imagen del mapa',
  topFires: 'Focos más intensos', copy: 'Copiar', copied: 'Copiado',
  aboveNormal: 'Sobre lo normal', normal: 'Normal', belowNormal: 'Bajo lo normal', fewData: 'Pocos datos',
  timesMedian: '× la mediana',
  hotspot: 'Foco', frp: 'Potencia radiativa', localTime: 'Hora local', confidence: 'Confianza', sat: 'Satélite',
  conf: ['baja', 'nominal', 'alta'], night: 'noche', day: 'día',
  probTomorrow: 'probabilidad de actividad', histRate: 'Tasa histórica de esta celda en esta época',
  inAlert: 'En alerta', notAlert: 'Sin alerta', why: 'Por qué', windCtx: 'Viento',
  viewHistory: 'Ver historial de este lugar', close: 'Cerrar',
  notForecast: 'Indica dónde es más probable la actividad de fuego, no que un incendio vaya a empezar.',
  estimated: 'Antes de 2012: estimado desde MODIS, escalado a VIIRS.',
  provisional: 'Datos casi en tiempo real: provisionales.',
  detections: 'focos', loading: 'Cargando…', noData: 'Sin datos para esta selección',
  legendHot: 'Potencia del foco (MW)', legendDensity: 'Focos armonizados por celda', legendRisk: 'Probabilidad',
  legendRegions: 'Semana vs. mediana', legendRegimes: 'Régimen de fuego', legendRings: 'Fuego del día siguiente cayó a',
  regimes: ['Invierno-primavera', 'Pulso de enero', 'Fin de verano', 'Pulso de diciembre'],
  sources: 'Datos: NASA FIRMS (MODIS, VIIRS) · Límites: IGN Argentina, geoBoundaries · Viento: Open-Meteo',
  method: 'Cada foco MODIS se convierte a equivalente VIIRS con factores por región y mes calibrados en 2012–2021, para que el sensor de origen ya no importe.',
  harmonized: 'Armonizado', modisRaw: 'MODIS crudo', viirsRaw: 'VIIRS crudo', median: 'Mediana', thisYear: 'Este año',
  ringsShare: (km: number, s: number) => `${Math.round(s * 100)}% a menos de ${km} km`,
  shown: (n: string) => `${n} focos en el mapa`,
  exposure: 'Población cerca del fuego', fewer: 'menos', moreFire: 'más', viewRegion: 'Ver región', region: 'Región', archive: 'Revisar un día pasado',
}
type Dict = typeof es

const en: Dict = {
  ...es,
  brandSub: 'Harmonized fire calendar · Chile and Argentina',
  search: 'Search a region or type "lat, lon"',
  modeHistory: 'History', modeNow: 'Now', modeForecast: 'Outlook',
  modeHistoryHint: 'Harmonized hotspots since 2000', modeNowHint: 'Hotspots of the last days',
  modeForecastHint: 'Where fire activity is most likely',
  whole: 'Whole year', play: 'Play', pause: 'Pause',
  tomorrow: 'Next day', weeks: 'Next weeks', week: 'Week of',
  layers: 'Layers', basemap: 'Basemap', dark: 'Dark', satellite: 'Satellite',
  L_towns: 'Towns', L_hotspots: 'Hotspots', L_heat: 'Heat', L_density: '3D density', L_risk: 'Probability', L_rings: 'Distance',
  L_wind: 'Wind', L_regimes: 'Regimes', L_static: 'Industry', L_regions: 'Regional anomaly', L_3d: '3D view',
  allArea: 'Chile and Argentina', drawBox: 'Draw area', clear: 'Clear selection', drawHint: 'Drag on the map to draw the area',
  who: 'How will you use Fireguard?', whoSub: 'Pick your profile: we arrange the map and panels for you. You can change it any time.',
  start: 'Open the map', profile: 'Profile',
  more: 'Show more', less: 'Show less',
  last7: 'Hotspots, last 7 days', vsMedian: 'vs. 2013–2025 median', alertsTomorrow: 'Cells in alert, next day',
  thisMonth: 'This month', rankOf: 'of', rankMonth: 'place among', years: 'years',
  calendar: 'Burn calendar', count: 'Count', anomaly: 'Anomaly',
  typicalYear: 'Typical year vs. this year', last30: 'Last 30 days vs. normal',
  ranking: 'Regions: this week vs. normal', sensors: 'MODIS vs. VIIRS: raw and harmonized',
  downloads: 'Downloads', csv: 'Hotspots CSV', json: 'Calendar (JSON)', png: 'Map image',
  topFires: 'Most intense hotspots', copy: 'Copy', copied: 'Copied',
  aboveNormal: 'Above normal', normal: 'Normal', belowNormal: 'Below normal', fewData: 'Little data',
  timesMedian: '× the median',
  hotspot: 'Hotspot', frp: 'Fire radiative power', localTime: 'Local time', confidence: 'Confidence', sat: 'Satellite',
  conf: ['low', 'nominal', 'high'], night: 'night', day: 'day',
  probTomorrow: 'chance of fire activity', histRate: 'Historical rate of this cell at this time of year',
  inAlert: 'In alert', notAlert: 'Not in alert', why: 'Why', windCtx: 'Wind',
  viewHistory: 'History of this place', close: 'Close',
  notForecast: 'It shows where fire activity is most likely, not that a fire will start.',
  estimated: 'Before 2012: estimated from MODIS, scaled to VIIRS.',
  provisional: 'Near-real-time data: provisional.',
  detections: 'hotspots', loading: 'Loading…', noData: 'No data for this selection',
  legendHot: 'Hotspot power (MW)', legendDensity: 'Harmonized hotspots per cell', legendRisk: 'Probability',
  legendRegions: 'Week vs. median', legendRegimes: 'Fire regime', legendRings: 'Next-day fire fell within',
  regimes: ['Winter-spring', 'January pulse', 'Late summer', 'December pulse'],
  sources: 'Data: NASA FIRMS (MODIS, VIIRS) · Boundaries: IGN Argentina, geoBoundaries · Wind: Open-Meteo',
  method: 'Every MODIS hotspot is converted to a VIIRS equivalent with region and month factors calibrated on 2012–2021, so the source sensor no longer matters.',
  harmonized: 'Harmonized', modisRaw: 'MODIS raw', viirsRaw: 'VIIRS raw', median: 'Median', thisYear: 'This year',
  ringsShare: (km: number, s: number) => `${Math.round(s * 100)}% within ${km} km`,
  shown: (n: string) => `${n} hotspots on the map`,
  exposure: 'People near fire', fewer: 'fewer', moreFire: 'more', viewRegion: 'Open region', region: 'Region', archive: 'Check a past day',
}

export const DICT = { es, en }
export type T = Dict

export const MONTHS = {
  es: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
  en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
}

/** 'YYYY-MM-DD' to '13 nov' without building a local Date. */
export function shortDate(iso: string, lang: Lang) {
  const [, m, d] = iso.split('-').map(Number)
  return `${d} ${MONTHS[lang][m - 1].toLowerCase()}`
}
export const nf = (lang: Lang, digits = 0) => new Intl.NumberFormat(lang === 'es' ? 'es-CL' : 'en', { maximumFractionDigits: digits })
export const compact = (lang: Lang) => new Intl.NumberFormat(lang === 'es' ? 'es-CL' : 'en', { notation: 'compact', maximumFractionDigits: 1 })
export const shortRegion = (name: string) => name.replace(/^Región (de |del |de la )?/, '').replace('Metropolitana de Santiago', 'Metropolitana')
