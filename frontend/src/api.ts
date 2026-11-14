// Client of backend/main.py. Dates are burn dates as 'YYYY-MM-DD' text: never build a JS Date
// from them (new Date('2024-02-02') shows as 1 February in Chile).

export type Box = { west: number; south: number; east: number; north: number }

export type Search = {
  box: Box | null
  country: string
  admin1: string
  fromYear: number
  toYear: number
}

export type Meta = {
  first_date: string
  data_through: string
  viirs_start: string
  cell_degrees: number
  regions: { country: string; admin1: string }[]
  risk_weeks: string[] // first the week in progress; empty when there is no risk layer
}

/** [cell_lat, cell_lon, probability, baseline_probability]; the cell is identified by its south-west corner. */
export type RiskCell = [number, number, number, number]

export type Month = {
  year: number
  month: number
  hotspots: number
  raw: number
  estimated: boolean // MODIS scaled to VIIRS-equivalent counts
  provisional: boolean // near-real-time data, replaced about 5 months later
  partial: boolean
  // Anomaly against the same month of the reference years, leaving out the month's own year.
  median: number | null
  ratio: number | null // (hotspots + 1) / (median + 1); null for a partial month
  reliable: boolean // false when the median is under 10: show the count, not the ratio
}

export type Reference = 'recent' | 'all'

export type Calendar = {
  from: string
  to: string
  data_through: string
  cells: number
  bounds: [number, number, number, number] | null // west, south, east, north of the cells used
  months: Month[]
  reference: { mode: Reference; from_year: number | null; to_year: number | null }
  median_by_month: (number | null)[] // over the reference years
  years: { year: number; hotspots: number; partial: boolean }[]
  current: {
    year: number
    month: number
    days: number
    hotspots: number
    median: number | null
    ratio: number | null
    reliable: boolean
    years_compared: number
    rank: number | null
  }
}

export function searchParams(s: Search): URLSearchParams {
  const p = new URLSearchParams({ from: `${s.fromYear}-01-01`, to: `${s.toYear}-12-31` })
  if (s.box) for (const [k, v] of Object.entries(s.box)) p.set(k, String(v))
  if (s.country) p.set('country', s.country)
  if (s.admin1) p.set('admin1', s.admin1)
  return p
}

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(await errorText(r))
  return r.json()
}

export async function errorText(r: Response): Promise<string> {
  const body = await r.json().catch(() => null)
  const detail = body?.detail
  return typeof detail === 'string' ? detail : `Request failed (${r.status})`
}

export const getMeta = () => get<Meta>('/api/meta')
export const getCalendar = (s: Search, reference: Reference) =>
  get<Calendar>(`/api/calendar?${searchParams(s)}&reference=${reference}`)
export function getRisk(week: string, s: Search) {
  const p = searchParams(s)
  p.delete('from')
  p.delete('to')
  p.set('week', week)
  return get<{ week_start: string; cells: RiskCell[] }>(`/api/risk?${p}`)
}

export function saveFile(name: string, content: Blob) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(content)
  a.download = name
  a.click()
  URL.revokeObjectURL(a.href)
}

// Probability of fire activity in a cell during the week. Yellow to dark red, light to dark.
export const RISK_BINS = [
  { from: 0.05, label: '5 to 10%', color: '#ffffb2' },
  { from: 0.1, label: '10 to 25%', color: '#fecc5c' },
  { from: 0.25, label: '25 to 50%', color: '#fd8d3c' },
  { from: 0.5, label: '50 to 75%', color: '#f03b20' },
  { from: 0.75, label: 'over 75%', color: '#bd0026' },
]
