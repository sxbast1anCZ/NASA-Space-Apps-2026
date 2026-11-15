// Colour ramps. Perceptual and colour-blind safe: inferno for counts, yellow-red for probability,
// blue-white-red for anomalies, Okabe-Ito for the regimes.
import type { RegionRow } from './data.ts'

type RGB = [number, number, number]
const hex = (h: string): RGB => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]

export const INFERNO = ['#420a68', '#6a176e', '#932667', '#bc3754', '#dd513a', '#f37819', '#fca50a', '#f6d746', '#fcffa4']
const INF = INFERNO.map(hex)
export function densityColor(x: number): [number, number, number, number] {
  const f = Math.max(0, Math.min(1, x)) * (INF.length - 1)
  const i = Math.floor(f), k = f - i
  const a = INF[i], b = INF[Math.min(i + 1, INF.length - 1)]
  return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k, 215]
}

export const FRP_BINS = [
  { from: 0, label: '< 5', color: '#ffd166' },
  { from: 5, label: '5–20', color: '#ff9f1c' },
  { from: 20, label: '20–100', color: '#ff4d2e' },
  { from: 100, label: '> 100', color: '#ff2d95' },
]
const FRP = FRP_BINS.map((b) => ({ from: b.from, rgb: hex(b.color) }))
export const frpColor = (frp: number): RGB => FRP.findLast((b) => frp >= b.from)!.rgb

export type Bin = { from: number; label: string; color: string }
export const DAILY_BINS: Bin[] = [
  { from: 0.02, label: '2–5%', color: '#ffffb2' },
  { from: 0.05, label: '5–10%', color: '#fecc5c' },
  { from: 0.1, label: '10–25%', color: '#fd8d3c' },
  { from: 0.25, label: '25–50%', color: '#f03b20' },
  { from: 0.5, label: '> 50%', color: '#bd0026' },
]
export const WEEKLY_BINS: Bin[] = [
  { from: 0.05, label: '5–10%', color: '#ffffb2' },
  { from: 0.1, label: '10–25%', color: '#fecc5c' },
  { from: 0.25, label: '25–50%', color: '#fd8d3c' },
  { from: 0.5, label: '50–75%', color: '#f03b20' },
  { from: 0.75, label: '> 75%', color: '#bd0026' },
]
export function binColor(bins: Bin[], v: number, alpha = 200): [number, number, number, number] {
  const b = bins.findLast((x) => v >= x.from) ?? bins[0]
  return [...hex(b.color), alpha]
}

export const RATIO_BINS = [
  { from: 0, label: '< 0,5×', color: '#2166ac' },
  { from: 0.5, label: '0,5–0,8×', color: '#92c5de' },
  { from: 0.8, label: '≈ 1×', color: '#e8e8e8' },
  { from: 1.25, label: '1,25–2×', color: '#f4a582' },
  { from: 2, label: '> 2×', color: '#b2182b' },
]
export function ratioColor(r: RegionRow): [number, number, number, number] {
  if (!r.reliable) return [120, 120, 130, 40]
  const b = RATIO_BINS.findLast((x) => r.ratio >= x.from)!
  return [...hex(b.color), 120]
}
export const ratioHex = (r: RegionRow) => (r.reliable ? RATIO_BINS.findLast((x) => r.ratio >= x.from)!.color : '#777b86')

export const REGIME_HEX = ['#E69F00', '#56B4E9', '#009E73', '#CC79A7']
export const REGIME_COLORS = REGIME_HEX.map(hex)
