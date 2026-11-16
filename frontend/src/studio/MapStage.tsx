/* eslint-disable @typescript-eslint/no-explicit-any */
import { MapboxOverlay } from '@deck.gl/mapbox'
import { HeatmapLayer } from '@deck.gl/aggregation-layers'
import { TripsLayer } from '@deck.gl/geo-layers'
import { GeoJsonLayer, PolygonLayer, ScatterplotLayer, SolidPolygonLayer } from '@deck.gl/layers'
import { SimpleMeshLayer } from '@deck.gl/mesh-layers'
import { HOUSE_MESH } from './houseMesh.ts'
import type { Exposure, Town, WindField } from './exposure.ts'
import { windAt } from './exposure.ts'
import type { Layer, PickingInfo } from '@deck.gl/core'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { Area, Daily, GeoFeature, Hotspots, RegionRow, Rings } from './data.ts'
import type { LayerId, Mode } from './personas.ts'
import { DAILY_BINS, densityColor, frpColor, ratioColor, REGIME_COLORS, WEEKLY_BINS, binColor } from './colors.ts'

export type Pick =
  | { kind: 'hotspot'; i: number; x: number; y: number }
  | { kind: 'cell'; lat: number; lon: number; x: number; y: number }
  | { kind: 'density'; lat: number; lon: number; value: number; x: number; y: number }
  | { kind: 'town'; t: number; x: number; y: number }

export type MapProps = {
  mode: Mode
  layers: Set<LayerId>
  basemap: Basemap
  imageryDate: string
  theme: 'dark' | 'light'
  tilt: boolean
  hotspots: Hotspots | null
  dayWindow: [number, number]
  density: [number, number, number][] | null
  regimes: [number, number, number, number, number][] | null
  statics: [number, number, number][] | null
  daily: Daily | null
  weekly: [number, number, number, number][] | null
  rings: Rings | null
  boundaries: GeoFeature[] | null
  regionRows: RegionRow[] | null
  area: Area
  windField: WindField | null
  townList: Town[] | null
  exposed: Exposure[]
  showTowns: boolean
  hotFilter: ((h: Hotspots, i: number) => boolean) | null
  focus: { bounds: number[]; key: number; pitch?: number } | null
  drawing: boolean
  onBox: (b: { west: number; south: number; east: number; north: number }) => void
  onRegion: (country: string, admin1: string) => void
  onPick: (p: Pick | null) => void
  onHover: (text: string | null, x: number, y: number) => void
  regimeNames: string[]
}

const HEAT_RANGE: [number, number, number][] = [[65, 10, 105], [140, 25, 110], [205, 60, 75], [245, 120, 30], [252, 190, 40], [252, 255, 164]]
const LEVEL_RGB: [number, number, number][] = [[150, 160, 178], [252, 196, 60], [255, 128, 40], [235, 40, 40]]
const HOME: [[number, number], [number, number]] = [[-78, -56], [-52, -17]]
const cell = (lat: number, lon: number, s = 0.25): [number, number][] => [[lon, lat], [lon + s, lat], [lon + s, lat + s], [lon, lat + s]]

const DEM = {
  type: 'raster-dem' as const,
  tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
  encoding: 'terrarium' as const, tileSize: 256, maxzoom: 12,
  attribution: 'Relieve: Mapzen / AWS Terrain Tiles',
}
export type Basemap = 'dark' | 'satellite' | 'truecolor' | 'firecolor'

/** NASA GIBS layer for a day: VIIRS NOAA-20 from April 2018, MODIS Terra before. */
export function gibsLayer(kind: 'truecolor' | 'firecolor', date: string) {
  const viirs = date >= '2018-04-01'
  if (kind === 'truecolor') return { id: viirs ? 'VIIRS_NOAA20_CorrectedReflectance_TrueColor' : 'MODIS_Terra_CorrectedReflectance_TrueColor', sensor: viirs ? 'VIIRS · NOAA-20' : 'MODIS · Terra' }
  return { id: viirs ? 'VIIRS_NOAA20_CorrectedReflectance_BandsM11-I2-I1' : 'MODIS_Terra_CorrectedReflectance_Bands721', sensor: viirs ? 'VIIRS · NOAA-20' : 'MODIS · Terra' }
}
export const gibsTile = (kind: 'truecolor' | 'firecolor', date: string, z = '{z}', y = '{y}', x = '{x}') =>
  `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${gibsLayer(kind, date).id}/default/${date}/GoogleMapsCompatible_Level9/${z}/${y}/${x}.jpg`

const STYLE_URL = { dark: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json', light: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json' }
const styles: Partial<Record<'dark' | 'light', Promise<maplibregl.StyleSpecification>>> = {}
const loadStyle = (k: 'dark' | 'light') => (styles[k] ??= fetch(STYLE_URL[k]).then((r) => r.json()))
let currentTheme: 'dark' | 'light' = 'dark'

/** Imagery under the vector labels and borders of the dark style (raster label tiles need a key). */
async function styleFor(basemap: Basemap, date: string, theme: 'dark' | 'light'): Promise<maplibregl.StyleSpecification> {
  if (basemap === 'dark') return structuredClone(await loadStyle(theme))
  const dark = structuredClone(await loadStyle('dark'))
  const nasa = basemap === 'truecolor' || basemap === 'firecolor'
  const sat: maplibregl.SourceSpecification = nasa ? {
    type: 'raster', tileSize: 256, maxzoom: 9, tiles: [gibsTile(basemap, date)],
    attribution: `Imagen: NASA EOSDIS GIBS, ${gibsLayer(basemap, date).sensor} (${date})`,
  } : {
    type: 'raster', tileSize: 256, maxzoom: 18,
    tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
    attribution: 'Imagen: Esri, Maxar, Earthstar Geographics',
  }
  dark.sources = { ...dark.sources, sat }
  const keep = dark.layers.filter((l: maplibregl.LayerSpecification) => l.type === 'symbol' || /boundary/.test(l.id))
  for (const l of keep) {
    if (l.type === 'symbol') l.paint = { ...l.paint, 'text-color': '#eef2f8', 'text-halo-color': 'rgba(0,0,0,0.85)', 'text-halo-width': 1.4 }
  }
  dark.layers = [
    { id: 'sat', type: 'raster', source: 'sat', paint: nasa ? { 'raster-brightness-max': 0.92, 'raster-contrast': 0.1 } : { 'raster-saturation': -0.25, 'raster-brightness-max': 0.8 } },
    ...keep,
  ]
  return dark
}

// Additive blending: overlapping hotspots glow brighter, as in a long-exposure photo.
const GLOW = {
  blend: true, blendColorOperation: 'add', blendAlphaOperation: 'add',
  blendColorSrcFactor: 'src-alpha', blendColorDstFactor: 'one',
  blendAlphaSrcFactor: 'one', blendAlphaDstFactor: 'one-minus-src-alpha', depthWriteEnabled: false,
} as const

export function MapStage(p: MapProps) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const overlay = useRef<MapboxOverlay | null>(null)
  const [zoom, setZoom] = useState(4)
  const [draft, setDraft] = useState<number[] | null>(null)
  const props = useRef(p)
  props.current = p

  // Map and deck.gl overlay, created once.
  useEffect(() => {
    const m = new maplibregl.Map({
      container: el.current!, style: { version: 8, sources: {}, layers: [] }, bounds: HOME, fitBoundsOptions: { padding: 40 },
      maxBounds: [[-115, -62], [-30, -8]], attributionControl: { compact: true }, canvasContextAttributes: { preserveDrawingBuffer: true },
    })
    m.on('style.load', () => addRelief(m))
    m.on('zoom', () => setZoom(Math.round(m.getZoom() * 8) / 8))
    m.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'bottom-right')
    m.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right')
    const o = new MapboxOverlay({ interleaved: false, layers: [] })
    m.addControl(o as unknown as maplibregl.IControl)
    map.current = m
    overlay.current = o
    return () => m.remove()
  }, [])

  useEffect(() => {
    let live = true
    currentTheme = p.theme
    styleFor(p.basemap, p.imageryDate, p.theme).then((st) => { if (live) map.current?.setStyle(st) })
    return () => { live = false }
  }, [p.basemap, p.theme, p.basemap === 'dark' || p.basemap === 'satellite' ? '' : p.imageryDate])
  useEffect(() => {
    map.current?.easeTo({ pitch: p.tilt ? 52 : 0, bearing: p.tilt ? -12 : 0, duration: 900 })
  }, [p.tilt])
  useEffect(() => {
    if (p.focus?.pitch !== undefined) {
      const b = p.focus.bounds
      map.current?.flyTo({ center: [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2], zoom: 9.3, pitch: p.focus.pitch, bearing: -18, duration: 1800, essential: true,
        padding: { top: 90, bottom: 170, left: 440, right: 110 } })
      return
    }
    if (p.focus) map.current?.fitBounds([[p.focus.bounds[0], p.focus.bounds[1]], [p.focus.bounds[2], p.focus.bounds[3]]],
      { padding: { top: 90, bottom: 170, left: 440, right: 110 }, maxZoom: 9, duration: 1400 })
  }, [p.focus?.key])

  // Wind flow: particles carried by the wind field, drawn on a canvas above the map with fading trails.
  const cv = useRef<HTMLCanvasElement>(null)
  const windOn = p.layers.has('wind') && !!p.windField
  useEffect(() => {
    const m = map.current, c = cv.current
    if (!m || !c) return
    const ctx = c.getContext('2d')!
    if (!windOn) { ctx.clearRect(0, 0, c.width, c.height); return }
    const f = p.windField!
    const light0 = props.current.theme === 'light' && props.current.basemap === 'dark'
    const dpr = window.devicePixelRatio || 1
    const resize = () => { c.width = c.clientWidth * dpr; c.height = c.clientHeight * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0) }
    resize()
    const N = Math.round(Math.min(3600, (c.clientWidth * c.clientHeight) / (light0 ? 380 : 300)))
    const box = [f.west, f.south, f.west + f.step * (f.nx - 1), f.south + f.step * (f.ny - 1)]
    // x, y: the particle on screen, kept from the last frame so each frame projects one point per particle.
    type P = { lon: number; lat: number; age: number; life: number; x: number; y: number }
    let view = [0, 0, 0, 0]
    const readView = () => {
      const b = m.getBounds()
      view = [Math.max(box[0], b.getWest()), Math.max(box[1], b.getSouth()), Math.min(box[2], b.getEast()), Math.min(box[3], b.getNorth())]
    }
    const spawn = (q: P) => {
      const [w, s, e, n] = view
      q.lon = w + Math.random() * Math.max(0.01, e - w); q.lat = s + Math.random() * Math.max(0.01, n - s)
      q.age = 0; q.life = 40 + Math.random() * 60
      const a = m.project([q.lon, q.lat])
      q.x = a.x; q.y = a.y
      return q
    }
    readView()
    const ps: P[] = Array.from({ length: N }, () => spawn({ lon: 0, lat: 0, age: 0, life: 0, x: 0, y: 0 }))
    const light = props.current.theme === 'light' && props.current.basemap === 'dark'
    // Streaks grouped in a few colour bands by speed: one stroke per band instead of one per particle.
    const BANDS = 6
    const bandColor = Array.from({ length: BANDS }, (_, i) => {
      const t = (i + 0.5) / BANDS
      return light
        ? `rgba(${Math.round(40 + 40 * t)},${Math.round(90 - 30 * t)},${Math.round(160 - 60 * t)},${0.18 + 0.45 * t})`
        : `rgba(${Math.round(200 + 55 * t)},${Math.round(235 - 60 * t)},${Math.round(255 - 140 * t)},${0.3 + 0.55 * t})`
    })
    const segs: number[][] = Array.from({ length: BANDS }, () => [])
    let id = 0, moving = false
    const onMove = () => { moving = true; ctx.clearRect(0, 0, c.clientWidth, c.clientHeight) }
    const onEnd = () => { moving = false; readView(); ps.forEach(spawn) }
    m.on('movestart', onMove); m.on('move', onMove); m.on('moveend', onEnd)
    window.addEventListener('resize', resize)
    const frame = () => {
      id = requestAnimationFrame(frame)
      if (moving) return
      ctx.globalCompositeOperation = 'destination-in'
      ctx.fillStyle = 'rgba(0,0,0,0.93)'
      ctx.fillRect(0, 0, c.clientWidth, c.clientHeight)
      ctx.globalCompositeOperation = 'source-over'
      ctx.lineWidth = 1.3
      ctx.lineCap = 'round'
      const degPerPx = 360 / (512 * 2 ** m.getZoom())
      const k = degPerPx / 22 // about 1 pixel per frame at 22 km/h
      for (const s of segs) s.length = 0
      for (const q of ps) {
        const w = windAt(f, q.lat, q.lon)
        if (!w || q.age++ > q.life) { spawn(q); continue }
        const sp = Math.hypot(w[0], w[1])
        const lon2 = q.lon + w[0] * k // Mercator: the same pixel step is cos(lat) degrees of latitude
        const lat2 = q.lat + w[1] * k * Math.cos((q.lat * Math.PI) / 180)
        const b = m.project([lon2, lat2])
        segs[Math.min(BANDS - 1, Math.floor((Math.min(1, sp / 45)) * BANDS))].push(q.x, q.y, b.x, b.y)
        q.lon = lon2; q.lat = lat2; q.x = b.x; q.y = b.y
      }
      for (let i = 0; i < BANDS; i++) {
        const s = segs[i]
        if (!s.length) continue
        ctx.strokeStyle = bandColor[i]
        ctx.beginPath()
        for (let j = 0; j < s.length; j += 4) { ctx.moveTo(s[j], s[j + 1]); ctx.lineTo(s[j + 2], s[j + 3]) }
        ctx.stroke()
      }
    }
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) frame()
    return () => {
      cancelAnimationFrame(id)
      m.off('movestart', onMove); m.off('move', onMove); m.off('moveend', onEnd)
      window.removeEventListener('resize', resize)
      ctx.clearRect(0, 0, c.clientWidth, c.clientHeight)
    }
  }, [windOn, p.windField, p.theme, p.basemap])

  // Box drawing: drag with the map pan switched off.
  useEffect(() => {
    const m = map.current
    if (!m || !p.drawing) return
    m.dragPan.disable()
    m.getCanvas().style.cursor = 'crosshair'
    let start: maplibregl.LngLat | null = null
    let last: number[] | null = null
    const down = (e: maplibregl.MapMouseEvent) => { start = e.lngLat }
    const move = (e: maplibregl.MapMouseEvent) => {
      if (!start) return
      last = [Math.min(start.lng, e.lngLat.lng), Math.min(start.lat, e.lngLat.lat), Math.max(start.lng, e.lngLat.lng), Math.max(start.lat, e.lngLat.lat)]
      setDraft(last)
    }
    const up = () => {
      if (start && last && last[2] - last[0] > 0.05 && last[3] - last[1] > 0.05) {
        const r = (v: number) => Math.round(v * 1000) / 1000
        props.current.onBox({ west: r(last[0]), south: r(last[1]), east: r(last[2]), north: r(last[3]) })
      }
      start = null
      setDraft(null)
    }
    m.on('mousedown', down); m.on('mousemove', move); m.on('mouseup', up)
    return () => {
      m.off('mousedown', down); m.off('mousemove', move); m.off('mouseup', up)
      m.dragPan.enable()
      m.getCanvas().style.cursor = ''
    }
  }, [p.drawing])

  // Hotspots of the selected days, filtered on the CPU (a few tens of thousands at most).
  const hot = useMemo(() => {
    const h = p.hotspots
    if (!h) return []
    const out: number[] = []
    const f = p.hotFilter
    for (let i = 0; i < h.count; i++) if (h.day[i] >= p.dayWindow[0] && h.day[i] <= p.dayWindow[1] && (!f || f(h, i))) out.push(i)
    return out.reverse() // weakest first, so the strongest are drawn on top
  }, [p.hotspots, p.dayWindow[0], p.dayWindow[1], p.hotFilter])
  const newest = useMemo(() => hot.filter((i) => p.hotspots!.day[i] === p.dayWindow[1]), [hot])

  const windPaths = useMemo(() => {
    if (!p.daily?.wind.length) return []
    const out: { path: number[][]; ts: number[]; speed: number }[] = []
    for (const [lat, lon, deg, kmh] of p.daily.wind) {
      const a = (deg * Math.PI) / 180
      const len = 0.1 + Math.min(kmh, 60) / 250
      for (let k = 0; k < 3; k++) {
        const off = (k - 1) * 0.06
        const y0 = lat + 0.125 + off * Math.sin(a), x0 = lon + 0.125 - off * Math.cos(a)
        const path: number[][] = [], ts: number[] = []
        for (let s = 0; s <= 8; s++) {
          path.push([x0 + (len * s / 8) * Math.sin(a) / Math.cos((lat * Math.PI) / 180), y0 + (len * s / 8) * Math.cos(a)])
          ts.push(s * 10 + k * 23)
        }
        out.push({ path, ts, speed: kmh })
      }
    }
    return out
  }, [p.daily])

  const regionColor = useMemo(() => {
    const m = new Map<string, RegionRow>()
    for (const r of p.regionRows ?? []) m.set(`${r.country}|${r.admin1}`, r)
    return m
  }, [p.regionRows])

  // Layer data derived once per input. deck.gl rebuilds a layer's buffers whenever its data array is a new
  // object, so these must not be recomputed while the map moves or animates.
  const [mask, regions] = useMemo(() => {
    const feats = p.boundaries ?? []
    return [feats.filter((f) => f.properties.mask), feats.filter((f) => !f.properties.mask)]
  }, [p.boundaries])
  const dimmed = useMemo(() => {
    const a = p.area
    if (a.kind !== 'country' && a.kind !== 'region') return null
    return regions.filter((f) => (a.kind === 'country' ? f.properties.country !== a.country : f.properties.admin1 !== a.admin1))
  }, [regions, p.area])
  const densityMax = useMemo(() => (p.density ?? []).reduce((m, c) => Math.max(m, c[2]), 1), [p.density])
  const riskCells = useMemo(() => (p.daily ? p.daily.cells.filter((c) => c[2] >= DAILY_BINS[0].from) : []), [p.daily])
  const alertCells = useMemo(() => riskCells.filter((c) => c[4] === 1), [riskCells])
  const heatCells = useMemo(() => (p.daily ? p.daily.cells.filter((c) => c[2] >= 0.02) : []), [p.daily])
  const weeklyCells = useMemo(() => (p.weekly ? p.weekly.filter((c) => c[2] >= WEEKLY_BINS[0].from) : []), [p.weekly])
  const exposedBy = useMemo(() => new Map(p.exposed.map((e) => [e.t, e])), [p.exposed])
  const haloTowns = useMemo(() => p.exposed.filter((e) => e.windToward || e.level >= 2), [p.exposed])
  // Fewer houses when zoomed out: only towns near fire, and big cities from zoom 6.
  const zoomBand = zoom >= 8 ? 8 : zoom >= 6 ? 6 : zoom >= 5.5 ? 5.5 : 0
  const shownTowns = useMemo(() => {
    const tl = p.townList
    if (!tl) return []
    return tl.map((_, i) => i).filter((i) => {
      const e = exposedBy.get(i)
      if (e) return zoomBand >= 5.5 || e.level >= 2 || tl[i][3] >= 50000
      return zoomBand >= 6 && tl[i][3] >= (zoomBand >= 8 ? 5000 : 100000)
    })
  }, [p.townList, exposedBy, zoomBand])

  // Layers that change only when their inputs change. The animated ones (wind streaks, pulse of the newest
  // hotspots, halo of exposed towns) are functions of the clock, built on every frame outside React.
  const layers = useMemo(() => {
    const L: (Layer | ((t: number) => Layer))[] = []
    const lightMap = p.theme === 'light' && p.basemap === 'dark'
    const on = (id: LayerId) => p.layers.has(id)
    const sel = p.area.kind === 'region' ? `${p.area.country}|${p.area.admin1}` : ''

    L.push(new GeoJsonLayer({ id: 'mask', data: mask as any, filled: true, stroked: false, getFillColor: p.theme === 'light' && p.basemap === 'dark' ? [233, 237, 243, 170] : [4, 6, 12, 150], updateTriggers: { getFillColor: [p.theme, p.basemap] } }))
    L.push(new GeoJsonLayer({
      id: 'regions', data: regions as any, pickable: true, filled: true, stroked: false,
      getFillColor: (f: GeoFeature) => {
        if (p.mode === 'now' && on('regions')) {
          const r = regionColor.get(`${f.properties.country}|${f.properties.admin1}`)
          return r ? ratioColor(r) : [0, 0, 0, 0]
        }
        return [0, 0, 0, 0]
      },
      updateTriggers: { getFillColor: [p.mode, on('regions'), regionColor, p.area, lightMap] },
    }))

    if (p.mode === 'history') {
      if (on('density') && p.density) {
        const max = densityMax
        L.push(new SolidPolygonLayer({
          id: 'density', data: p.density, pickable: true, extruded: p.tilt, material: { ambient: 0.6, diffuse: 0.5 },
          getPolygon: (c: number[]) => cell(c[0], c[1]),
          getElevation: (c: number[]) => Math.sqrt(c[2] / max) * 120000,
          getFillColor: (c: number[]) => densityColor(Math.sqrt(c[2] / max)),
          updateTriggers: { getFillColor: max, getElevation: max }, transitions: { getElevation: 600 },
        }))
      }
    }
    if (p.mode === 'history' && on('heat') && p.density) {
      L.push(new HeatmapLayer({
        id: 'heat-history', data: p.density, getPosition: (c: number[]): [number, number] => [c[1] + 0.125, c[0] + 0.125],
        getWeight: (c: number[]) => c[2], radiusPixels: 42, intensity: 1.2, threshold: 0.03, aggregation: 'SUM',
        colorRange: HEAT_RANGE, opacity: 0.85,
      }))
    }
    if (p.mode === 'forecast' && on('heat') && p.daily && !p.weekly) {
      L.push(new HeatmapLayer({
        id: 'heat-forecast', data: heatCells, getPosition: (c: number[]): [number, number] => [c[1] + 0.125, c[0] + 0.125],
        getWeight: (c: number[]) => c[2], radiusPixels: 46, intensity: 1.4, threshold: 0.05, colorRange: HEAT_RANGE, opacity: 0.85,
      }))
    }
    if (on('regimes') && p.regimes && p.mode !== 'now') {
      L.push(new SolidPolygonLayer({
        id: 'regimes', data: p.regimes, pickable: true,
        getPolygon: (c: number[]) => cell(c[0], c[1]),
        getFillColor: (c: number[]) => [...REGIME_COLORS[c[2]], p.mode === 'history' && on('density') ? 0 : 150] as [number, number, number, number],
        stroked: false, updateTriggers: { getFillColor: [p.mode, on('density')] },
      }))
      if (p.mode === 'history' && on('density')) {
        L.push(new PolygonLayer({
          id: 'regimes-outline', data: p.regimes, filled: false, stroked: true, lineWidthMinPixels: 1.2,
          getPolygon: (c: number[]) => cell(c[0], c[1]),
          getLineColor: (c: number[]) => [...REGIME_COLORS[c[2]], 200] as [number, number, number, number],
        }))
      }
    }

    if (p.mode === 'forecast') {
      if (on('risk') && p.weekly) {
        L.push(new SolidPolygonLayer({
          id: 'weekly', data: weeklyCells, pickable: false,
          getPolygon: (c: number[]) => cell(c[0], c[1]), getFillColor: (c: number[]) => binColor(WEEKLY_BINS, c[2], 190),
        }))
      } else if (on('risk') && p.daily) {
        L.push(new SolidPolygonLayer({
          id: 'risk', data: riskCells, pickable: true, extruded: p.tilt,
          getPolygon: (c: number[]) => cell(c[0], c[1]),
          getElevation: (c: number[]) => c[2] * 140000,
          getFillColor: (c: number[]) => binColor(DAILY_BINS, c[2], c[2] < 0.05 ? 70 : c[2] < 0.1 ? 140 : 210),
        }))
        L.push(new PolygonLayer({
          id: 'alerts', data: alertCells, filled: false, stroked: true,
          lineWidthMinPixels: 1, getLineColor: lightMap ? [120, 20, 10, 150] : [255, 236, 210, 120], getPolygon: (c: number[]) => cell(c[0], c[1]),
        }))
      }
      if (on('wind') && windPaths.length && !p.weekly) {
        L.push((t) => new TripsLayer({
          id: 'wind', data: windPaths, getPath: (d: { path: number[][] }) => d.path as [number, number][],
          getTimestamps: (d: { ts: number[] }) => d.ts, getColor: lightMap ? [20, 90, 150] : [190, 235, 255], opacity: 0.9,
          widthMinPixels: 2, capRounded: true, jointRounded: true, trailLength: 45, currentTime: (t * 60) % 130, fadeTrail: true,
        }))
      }
    }

    if (on('rings') && p.rings && p.mode !== 'history') {
      for (const r of [...p.rings.rings].reverse()) {
        L.push(new ScatterplotLayer({
          id: `ring-${r.km}`, data: p.rings.points, radiusUnits: 'meters', getRadius: r.km * 1000,
          getPosition: (d: number[]): [number, number] => [d[1], d[0]], getFillColor: [255, 140, 40, r.km === 25 ? 10 : r.km === 10 ? 16 : 26],
          stroked: false,
        }))
      }
    }

    if (on('static') && p.statics) {
      L.push(new ScatterplotLayer({
        id: 'static', data: p.statics, getPosition: (d: number[]): [number, number] => [d[1], d[0]], radiusUnits: 'pixels', getRadius: 4,
        filled: true, stroked: true, getFillColor: [0, 0, 0, 160], getLineColor: [120, 220, 255], lineWidthMinPixels: 1.5,
      }))
    }

    const showHot = p.hotspots && ((p.mode === 'now' && on('hotspots')) || (p.mode === 'forecast' && on('hotspots')))
    if (p.hotspots && p.mode === 'now' && on('heat')) {
      const h = p.hotspots
      L.push(new HeatmapLayer({
        id: 'heat', data: hot, getPosition: (i: number): [number, number] => [h.lon[i], h.lat[i]], getWeight: (i: number) => (h.sat[i] <= 1 ? 4 : 1),
        radiusPixels: 38, intensity: 1.1, threshold: 0.04,
        colorRange: HEAT_RANGE, opacity: 0.85,
      }))
    }
    if (showHot) {
      const h = p.hotspots!
      const pos = (i: number): [number, number] => [h.lon[i], h.lat[i]]
      L.push(new ScatterplotLayer({
        id: 'hot-glow', data: hot, getPosition: pos, radiusUnits: 'pixels', parameters: lightMap ? undefined : GLOW,
        getRadius: (i: number) => 5 + Math.min(14, Math.sqrt(h.frp[i])), getFillColor: (i: number) => [...frpColor(h.frp[i]), 34],
      }))
      L.push(new ScatterplotLayer({
        id: 'hot-core', data: hot, pickable: true, getPosition: pos, radiusUnits: 'meters',
        getRadius: (i: number) => (h.sat[i] <= 1 ? 500 : 190), radiusMinPixels: 1.6, radiusMaxPixels: 30,
        getFillColor: (i: number) => [...frpColor(h.frp[i]), 235], parameters: lightMap ? undefined : GLOW,
        stroked: lightMap, getLineColor: [90, 20, 0, 160], lineWidthMinPixels: 0.6,
      }))
      if (p.mode === 'now' && newest.length && newest.length < 20000) {
        // Constant accessors: the pulse moves through radiusScale and opacity, so no buffer is rebuilt per frame.
        L.push((t) => {
          const k = (t * 0.9) % 1
          return new ScatterplotLayer({
            id: 'hot-pulse', data: newest, getPosition: pos, radiusUnits: 'pixels', filled: false, stroked: true,
            getRadius: 1, radiusScale: 3 + k * 16, getLineColor: [255, 200, 120, 180], opacity: 1 - k, lineWidthMinPixels: 1,
          })
        })
      }
    }

    if (p.showTowns && p.townList) {
      const ex = exposedBy
      const zNow = zoom
      const big = shownTowns
      if (haloTowns.length) {
        L.push((t) => {
          const k = ((t * 14) % 10) / 10
          return new ScatterplotLayer({
            id: 'town-halo', data: haloTowns, radiusUnits: 'pixels',
            getPosition: (e: Exposure): [number, number] => [e.lon, e.lat], getRadius: 1, radiusScale: 14 + k * 10,
            filled: false, stroked: true, lineWidthMinPixels: 1.5, opacity: 1 - k,
            getLineColor: (e: Exposure) => [...LEVEL_RGB[e.level], 200] as [number, number, number, number],
          })
        })
      }
      // 3D houses that keep about the same size on screen (metres per pixel at about 33 degrees south).
      const mpp = (78271.5 * 0.84) / 2 ** zNow
      L.push(new SimpleMeshLayer({
        id: 'towns', data: big, pickable: true, mesh: HOUSE_MESH as any, sizeScale: mpp,
        getPosition: (i: number): [number, number, number] => [p.townList![i][2], p.townList![i][1], 0],
        getScale: (i: number) => {
          const k = ex.has(i) ? 7 + Math.min(5, Math.max(0, Math.log10(p.townList![i][3]) - 3.7) * 2.5) : 5
          return [k, k, k * 1.1]
        },
        getOrientation: (i: number) => [0, (p.townList![i][2] * 37) % 90, 0],
        getColor: (i: number) => {
          const e = ex.get(i)
          return e ? [...LEVEL_RGB[e.level], 255] as [number, number, number, number] : lightMap ? [150, 160, 178, 255] : [205, 214, 230, 235]
        },
        material: { ambient: 0.8, diffuse: 0.55, shininess: 40, specularColor: [255, 245, 230] },
        updateTriggers: { getColor: [p.exposed, lightMap], getScale: p.exposed },
      }))
    }
    // Dim everything outside the selected country or region, above the data layers.
    const a = p.area
    if (a.kind === 'country' || a.kind === 'region') {
      L.push(new GeoJsonLayer({
        id: 'dim', data: dimmed as any,
        filled: true, stroked: false,
        getFillColor: lightMap ? [233, 237, 243, a.kind === 'country' ? 215 : 150] : [4, 6, 12, a.kind === 'country' ? 200 : 130],
        updateTriggers: { getFillColor: [lightMap, a.kind] },
      }))
    }
    L.push(new GeoJsonLayer({
      id: 'outlines', data: regions as any, filled: false, stroked: true, lineWidthUnits: 'pixels',
      getLineWidth: (f: GeoFeature) => (`${f.properties.country}|${f.properties.admin1}` === sel ? 2.5 : 0.7),
      getLineColor: (f: GeoFeature) => (`${f.properties.country}|${f.properties.admin1}` === sel ? [255, 140, 30, 255] : lightMap ? [15, 23, 42, 70] : [255, 255, 255, 60]),
      updateTriggers: { getLineWidth: sel, getLineColor: [sel, lightMap] },
    }))
    const box = draft ?? (p.area.kind === 'box' ? [p.area.west, p.area.south, p.area.east, p.area.north] : null)
    if (box) {
      L.push(new PolygonLayer({
        id: 'box', data: [box], getPolygon: (b: number[]): [number, number][] => [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]],
        filled: true, getFillColor: [255, 170, 60, 25], stroked: true, getLineColor: [255, 170, 60, 255], lineWidthMinPixels: 2,
      }))
    }
    return L
  }, [p.mode, p.layers, p.tilt, p.hotspots, hot, newest, p.density, p.regimes, p.statics, p.daily, p.weekly, p.rings,
    mask, regions, dimmed, densityMax, riskCells, alertCells, heatCells, weeklyCells, exposedBy, haloTowns, shownTowns,
    regionColor, p.area, draft, windPaths, p.theme, p.basemap, p.showTowns, p.townList, p.exposed, zoom])

  // Animation clock: a requestAnimationFrame loop that hands deck.gl the layers of the frame. It never
  // touches React state, so the page does not re-render 60 times a second.
  const animated = layers.some((l) => typeof l === 'function')
  useEffect(() => {
    const o = overlay.current
    if (!o) return
    const build = (t: number) => layers.map((l) => (typeof l === 'function' ? l(t) : l))
    o.setProps({ layers: build((performance.now() / 1000) % 1000) })
    if (!animated || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    let id = 0
    const tick = () => { o.setProps({ layers: build((performance.now() / 1000) % 1000) }); id = requestAnimationFrame(tick) }
    id = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(id)
  }, [layers, animated])

  useEffect(() => {
    overlay.current?.setProps({
      onClick: (info: PickingInfo) => {
        if (props.current.drawing) return
        const cur = props.current
        const id = info.layer?.id
        if (!info.picked || !id) return cur.onPick(null)
        if (id === 'hot-core') return cur.onPick({ kind: 'hotspot', i: info.object as number, x: info.x, y: info.y })
        if (id === 'risk') { const c = info.object as number[]; return cur.onPick({ kind: 'cell', lat: c[0], lon: c[1], x: info.x, y: info.y }) }
        if (id === 'density') { const c = info.object as number[]; return cur.onPick({ kind: 'density', lat: c[0], lon: c[1], value: c[2], x: info.x, y: info.y }) }
        if (id === 'towns') return cur.onPick({ kind: 'town', t: info.object as number, x: info.x, y: info.y })
        if (id === 'regions') {
          const f = info.object as GeoFeature
          cur.onPick(null)
          return cur.onRegion(f.properties.country!, f.properties.admin1!)
        }
        cur.onPick(null)
      },
      onHover: (info: PickingInfo) => {
        const cur = props.current
        const id = info.layer?.id
        if (!info.picked || !id) return cur.onHover(null, 0, 0)
        if (id === 'regions') {
          const f = info.object as GeoFeature
          return cur.onHover(`${f.properties.admin1}`, info.x, info.y)
        }
        if (id === 'towns') {
          const tw = cur.townList![info.object as number]
          return cur.onHover(`🏠 ${tw[0]} · ${new Intl.NumberFormat('es-CL').format(tw[3])}`, info.x, info.y)
        }
        if (id === 'regimes') {
          const c = info.object as number[]
          return cur.onHover(cur.regimeNames[c[2]], info.x, info.y)
        }
        cur.onHover(null, 0, 0)
      },
      getCursor: ({ isHovering }: { isHovering: boolean }) => (props.current.drawing ? 'crosshair' : isHovering ? 'pointer' : 'grab'),
    })
  }, [])

  return (
    <>
      <div ref={el} className="stage" />
      <canvas ref={cv} className="windcanvas" />
    </>
  )
}

function addRelief(m: maplibregl.Map) {
  if (m.getSource('dem')) return
  m.addSource('dem', DEM)
  const first = m.getStyle().layers.find((l) => l.type === 'symbol')?.id
  m.addLayer({
    id: 'relief', type: 'hillshade', source: 'dem',
    paint: currentTheme === 'light'
      ? { 'hillshade-exaggeration': 0.35, 'hillshade-shadow-color': '#7d8799', 'hillshade-highlight-color': '#ffffff', 'hillshade-accent-color': '#9aa3b2' }
      : { 'hillshade-exaggeration': 0.45, 'hillshade-shadow-color': '#000000', 'hillshade-highlight-color': '#5a6b85', 'hillshade-accent-color': '#0b0f18' },
  }, first)
}
