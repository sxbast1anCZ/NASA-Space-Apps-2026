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
}

export type Month = {
  year: number
  month: number
  hotspots: number
  raw: number
  estimated: boolean // MODIS scaled to VIIRS-equivalent counts
  provisional: boolean // near-real-time data, replaced about 5 months later
  partial: boolean
}

export type Calendar = {
  from: string
  to: string
  data_through: string
  cells: number
  bounds: [number, number, number, number] | null // west, south, east, north of the cells used
  months: Month[]
  median_by_month: (number | null)[]
  years: { year: number; hotspots: number; partial: boolean }[]
  current: {
    year: number
    month: number
    days: number
    hotspots: number
    median: number | null
    ratio: number | null
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
export const getCalendar = (s: Search) => get<Calendar>(`/api/calendar?${searchParams(s)}`)

export function saveFile(name: string, content: Blob) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(content)
  a.download = name
  a.click()
  URL.revokeObjectURL(a.href)
}
