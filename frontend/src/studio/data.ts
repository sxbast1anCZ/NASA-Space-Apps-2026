// Client of backend/ui.py and backend/main.py for the full-screen studio.
// Dates are burn dates as 'YYYY-MM-DD' text: never build a JS Date from them for display.
import type { Calendar, CellDetail, Daily, Meta, Rings } from '../api.ts'

export type { Calendar, CellDetail, Daily, Meta, Rings }

export type Area =
  | { kind: 'all' }
  | { kind: 'country'; country: string }
  | { kind: 'region'; country: string; admin1: string; bounds?: number[] }
  | { kind: 'box'; west: number; south: number; east: number; north: number; label?: string }

export type Hotspots = {
  from: string; to: string; count: number; truncated: boolean
  lon: number[]; lat: number[]; frp: number[]; sat: number[]; night: number[]; day: number[]
  conf: number[]; time: string[]; region: (string | null)[]
}
export type DayCount = { date: string; hotspots: number; median: number }
export type RegionRow = {
  country: string; admin1: string; hotspots_7d: number; median_7d: number; ratio: number
  reliable: boolean; alerts: number; max_probability: number | null; bounds: number[]
}
export type Regions = { through: string; outlook_day: string | null; regions: RegionRow[] }
export type SeriesYear = { year: number; modis_raw: number; viirs_raw: number; harmonized: number }
export type GeoFeature = { type: 'Feature'; properties: { country?: string; admin1?: string; mask?: boolean }; geometry: unknown }

export const SATS = ['Terra', 'Aqua', 'Suomi-NPP', 'NOAA-20', 'NOAA-21']
export const isModis = (sat: number) => sat <= 1

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) {
    const body = await r.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Error ${r.status}`)
  }
  return r.json()
}

export function areaParams(a: Area): URLSearchParams {
  const p = new URLSearchParams()
  if (a.kind === 'country') {
    p.set('country', a.country)
  } else if (a.kind === 'region') {
    p.set('country', a.country)
    p.set('admin1', a.admin1)
  } else if (a.kind === 'box') {
    for (const k of ['west', 'south', 'east', 'north'] as const) p.set(k, String(a[k]))
  }
  return p
}
const qs = (a: Area, extra: Record<string, string>) => {
  const p = areaParams(a)
  for (const [k, v] of Object.entries(extra)) p.set(k, v)
  return p.toString()
}

const cache = new Map<string, Promise<unknown>>()
function cached<T>(url: string): Promise<T> {
  if (!cache.has(url)) cache.set(url, get<T>(url).catch((e) => { cache.delete(url); throw e }))
  return cache.get(url) as Promise<T>
}

export const api = {
  meta: () => cached<Meta>('/api/meta'),
  boundaries: () => cached<{ features: GeoFeature[] }>('/api/ui/boundaries'),
  hotspots: (from: string, to: string) => cached<Hotspots>(`/api/ui/hotspots?from=${from}&to=${to}`),
  days: (a: Area, from: string, to: string) => cached<{ days: DayCount[] }>(`/api/ui/days?${qs(a, { from, to })}`),
  density: (from: string, to: string, f?: { sensor: string; minConf: number; minFrp: number; time: string }) =>
    cached<{ cells: [number, number, number][]; estimated: boolean }>(`/api/ui/density?from=${from}&to=${to}` +
      (f && f.sensor !== 'harmonized' ? `&sensor=${f.sensor}&min_conf=${f.minConf}&min_frp=${f.minFrp}&time=${f.time}` : '')),
  yearly: () => cached<{ years: { year: number; modis: number; viirs: number; harmonized: number }[] }>('/api/ui/yearly'),
  regimes: () => cached<{ cells: [number, number, number, number, number][] }>('/api/ui/regimes'),
  statics: () => cached<{ points: [number, number, number][] }>('/api/ui/static'),
  regions: () => cached<Regions>('/api/ui/regions'),
  series: (a: Area) => cached<{ years: SeriesYear[] }>(`/api/ui/series?${qs(a, {})}`),
  calendar: (a: Area, reference: 'recent' | 'all') => cached<Calendar>(`/api/calendar?${qs(a, { reference })}`),
  daily: (date: string) => cached<Daily>(`/api/risk/daily?date=${date}`),
  rings: (date: string) => cached<Rings>(`/api/risk/daily/hotspots?date=${date}`),
  weekly: (week: string) => cached<{ cells: [number, number, number, number][] }>(`/api/risk?week=${week}`),
  cell: (date: string, lat: number, lon: number) => get<CellDetail>(`/api/risk/daily/cell?date=${date}&cell_lat=${lat}&cell_lon=${lon}`),
  towns: () => cached<{ towns: [string, number, number, number, string | null][] }>('/api/ui/towns'),
  windfield: (date: string) => cached<import('./exposure.ts').WindField>(`/api/ui/windfield?date=${date}`),
  csvUrl: (a: Area, from: string, to: string) => `/api/hotspots.csv?${qs(a, { from, to })}`,
}

/** Add days to a 'YYYY-MM-DD' text, in UTC so the local time zone never shifts it. */
export function addDays(iso: string, n: number): string {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + n)
  return d.toISOString().slice(0, 10)
}
export const lastDayOfMonth = (y: number, m: number) => new Date(Date.UTC(y, m, 0)).getUTCDate()
