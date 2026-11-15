// Towns near fire: distances from each town to the hotspots or alert cells on the map, and whether
// the wind of the day blows from the fire towards the town. Distances are great-circle, in km.
import type { Hotspots } from './data.ts'

export type Town = [string, number, number, number, string | null] // name, lat, lon, population, region
export type WindField = { date: string; west: number; south: number; step: number; nx: number; ny: number; u: number[]; v: number[]; max: number }
export type Fire = { lat: number; lon: number; frp: number; i: number; kind: 'hotspot' | 'alert'; p?: number }

export type Exposure = {
  t: number // index in the town list
  name: string; lat: number; lon: number; pop: number; region: string | null
  nearest: number // km to the nearest fire
  bearing: number // degrees from the town to the nearest fire
  within10: number; within25: number; maxFrp: number
  level: 0 | 1 | 2 | 3 // 3: fire within 5 km, 2: 10 km, 1: 25 km
  windToward: boolean // the wind at the nearest fire blows towards the town
  windKmh: number | null
  fires: Fire[] // fires within 25 km, nearest first
}

const R = 6371
const rad = Math.PI / 180
export function km(lat1: number, lon1: number, lat2: number, lon2: number) {
  const a = Math.sin(((lat2 - lat1) * rad) / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(((lon2 - lon1) * rad) / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(a))
}
export function bearing(lat1: number, lon1: number, lat2: number, lon2: number) {
  const y = Math.sin((lon2 - lon1) * rad) * Math.cos(lat2 * rad)
  const x = Math.cos(lat1 * rad) * Math.sin(lat2 * rad) - Math.sin(lat1 * rad) * Math.cos(lat2 * rad) * Math.cos((lon2 - lon1) * rad)
  return (Math.atan2(y, x) / rad + 360) % 360
}

/** Wind (u east, v north, km/h) at a point, bilinear on the grid; null outside it. */
export function windAt(f: WindField | null, lat: number, lon: number): [number, number] | null {
  if (!f) return null
  const x = (lon - f.west) / f.step, y = (lat - f.south) / f.step
  if (x < 0 || y < 0 || x > f.nx - 1 || y > f.ny - 1) return null
  const x0 = Math.min(Math.floor(x), f.nx - 2), y0 = Math.min(Math.floor(y), f.ny - 2)
  const dx = x - x0, dy = y - y0
  const at = (arr: number[], i: number, j: number) => arr[j * f.nx + i]
  const lerp = (arr: number[]) =>
    at(arr, x0, y0) * (1 - dx) * (1 - dy) + at(arr, x0 + 1, y0) * dx * (1 - dy) + at(arr, x0, y0 + 1) * (1 - dx) * dy + at(arr, x0 + 1, y0 + 1) * dx * dy
  return [lerp(f.u), lerp(f.v)]
}

export function exposures(towns: Town[], fires: Fire[], wind: WindField | null): Exposure[] {
  if (!fires.length) return []
  // Bucket the fires in 0.25 degree cells so each town only looks at its neighbourhood.
  const grid = new Map<string, Fire[]>()
  const key = (a: number, b: number) => `${Math.floor(a / 0.25)}|${Math.floor(b / 0.25)}`
  for (const f of fires) {
    const k = key(f.lat, f.lon)
    const g = grid.get(k)
    if (g) g.push(f); else grid.set(k, [f])
  }
  const out: Exposure[] = []
  towns.forEach(([name, lat, lon, pop, region], t) => {
    const near: (Fire & { d: number })[] = []
    const cy = Math.floor(lat / 0.25), cx = Math.floor(lon / 0.25)
    for (let a = -2; a <= 2; a++) for (let b = -2; b <= 2; b++) {
      for (const f of grid.get(`${cy + a}|${cx + b}`) ?? []) {
        const d = km(lat, lon, f.lat, f.lon)
        if (d <= 25) near.push({ ...f, d })
      }
    }
    if (!near.length) return
    near.sort((p, q) => p.d - q.d)
    const n = near[0]
    const w = windAt(wind, n.lat, n.lon)
    let windToward = false, windKmh: number | null = null
    if (w) {
      windKmh = Math.hypot(w[0], w[1])
      const downwind = (Math.atan2(w[0], w[1]) / rad + 360) % 360
      const toTown = bearing(n.lat, n.lon, lat, lon)
      const diff = Math.abs(((downwind - toTown + 540) % 360) - 180)
      windToward = windKmh >= 8 && diff <= 45
    }
    out.push({
      t, name, lat, lon, pop, region, nearest: n.d, bearing: bearing(lat, lon, n.lat, n.lon),
      within10: near.filter((f) => f.d <= 10).length, within25: near.length, maxFrp: Math.max(...near.map((f) => f.frp)),
      level: n.d <= 5 ? 3 : n.d <= 10 ? 2 : 1, windToward, windKmh, fires: near.slice(0, 12),
    })
  })
  return out.sort((a, b) => b.level - a.level || Number(b.windToward) - Number(a.windToward) || b.pop - a.pop)
}

export function firesFrom(h: Hotspots | null, window: [number, number], filter: ((h: Hotspots, i: number) => boolean) | null): Fire[] {
  if (!h) return []
  const out: Fire[] = []
  for (let i = 0; i < h.count; i++) {
    if (h.day[i] < window[0] || h.day[i] > window[1]) continue
    if (filter && !filter(h, i)) continue
    out.push({ lat: h.lat[i], lon: h.lon[i], frp: h.frp[i], i, kind: 'hotspot' })
  }
  return out
}

const COMPASS_ES = ['norte', 'noreste', 'este', 'sureste', 'sur', 'suroeste', 'oeste', 'noroeste']
const COMPASS_EN = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west']
export const compass = (deg: number, lang: 'es' | 'en') => (lang === 'es' ? COMPASS_ES : COMPASS_EN)[Math.round(deg / 45) % 8]
