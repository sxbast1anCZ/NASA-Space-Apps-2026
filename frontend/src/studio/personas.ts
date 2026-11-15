// The four audiences of the challenge. A persona only sets defaults: every layer and card stays reachable.
import type { Lang } from './i18n.ts'

export type Mode = 'history' | 'now' | 'forecast'
export type LayerId = 'towns' | 'hotspots' | 'heat' | 'density' | 'risk' | 'rings' | 'wind' | 'regimes' | 'static' | 'regions'
export type CardId = 'exposure' | 'summary' | 'top' | 'ranking' | 'calendar' | 'typical' | 'last30' | 'sensors' | 'downloads'
export type PersonaId = 'brigade' | 'emergency' | 'land' | 'science'

export type Persona = {
  id: PersonaId
  icon: 'flame' | 'siren' | 'trees' | 'microscope'
  color: string
  mode: Mode
  layers: LayerId[]
  cards: CardId[] // shown first, in this order; the rest sit behind "show more"
  name: Record<Lang, string>
  pitch: Record<Lang, string>
  bullets: Record<Lang, string[]>
}

export const PERSONAS: Persona[] = [
  {
    id: 'brigade', icon: 'flame', color: '#ff7a1a', mode: 'now', layers: ['hotspots', 'rings', 'towns', 'wind'],
    cards: ['summary', 'exposure', 'top'],
    name: { es: 'Brigadista', en: 'Firefighter' },
    pitch: { es: 'Dónde hay fuego ahora y hacia dónde puede ir.', en: 'Where fire is now and where it may go.' },
    bullets: {
      es: ['Focos de las últimas horas', 'Focos más intensos con coordenadas', 'Viento y distancias de avance'],
      en: ['Hotspots of the last hours', 'Most intense hotspots with coordinates', 'Wind and spread distances'],
    },
  },
  {
    id: 'emergency', icon: 'siren', color: '#ff3b5c', mode: 'forecast', layers: ['risk', 'wind', 'towns'],
    cards: ['summary', 'exposure', 'ranking'],
    name: { es: 'Alerta temprana', en: 'Early warning' },
    pitch: { es: 'Qué regiones están fuera de lo normal y qué viene mañana.', en: 'Which regions are off normal and what comes tomorrow.' },
    bullets: {
      es: ['Pronóstico del día siguiente', 'Ranking de regiones vs. lo normal', 'Motivo de cada alerta'],
      en: ['Next-day outlook', 'Regions ranked against normal', 'Reason for every alert'],
    },
  },
  {
    id: 'land', icon: 'trees', color: '#3ddc97', mode: 'history', layers: ['density'],
    cards: ['summary', 'calendar', 'typical'],
    name: { es: 'Gestión territorial', en: 'Land manager' },
    pitch: { es: 'Cuándo se quema tu territorio y cómo va este año.', en: 'When your land burns and how this year compares.' },
    bullets: {
      es: ['Calendario de quemas desde 2000', 'Temporada típica de tu región', 'Este año vs. la mediana'],
      en: ['Burn calendar since 2000', 'Typical season of your region', 'This year vs. the median'],
    },
  },
  {
    id: 'science', icon: 'microscope', color: '#7aa7ff', mode: 'history', layers: ['density', 'regimes'],
    cards: ['sensors', 'calendar', 'downloads'],
    name: { es: 'Ciencia', en: 'Science' },
    pitch: { es: 'Serie MODIS–VIIRS armonizada, regímenes y datos crudos.', en: 'Harmonized MODIS–VIIRS series, regimes and raw data.' },
    bullets: {
      es: ['MODIS y VIIRS crudos vs. armonizado', 'Regímenes de fuego por celda', 'CSV y JSON descargables'],
      en: ['Raw MODIS and VIIRS vs. harmonized', 'Fire regimes per cell', 'Downloadable CSV and JSON'],
    },
  },
]

export const ALL_CARDS: CardId[] = ['summary', 'exposure', 'top', 'ranking', 'calendar', 'typical', 'last30', 'sensors', 'downloads']

/** Layers that make sense in each time mode. */
export const MODE_LAYERS: Record<Mode, LayerId[]> = {
  history: ['density', 'heat', 'wind', 'regimes', 'static', 'towns'],
  now: ['hotspots', 'heat', 'wind', 'towns', 'regions', 'rings', 'static'],
  forecast: ['risk', 'heat', 'wind', 'towns', 'rings', 'hotspots', 'regimes'],
}
