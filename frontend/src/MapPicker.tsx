import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useEffect, useRef, useState } from 'react'
import type { Box, CellDetail, Daily, Rings, RiskCell } from './api.ts'
import { RISK_BINS } from './api.ts'

const riskBin = (p: number) => RISK_BINS.findLast((b) => p >= b.from)

const toBounds = (b: Box): L.LatLngBoundsExpression => [
  [b.south, b.west],
  [b.north, b.east],
]
const round = (v: number) => Math.round(v * 1000) / 1000
const DETAIL_ZOOM = 7 // from here a 0.25° cell is about 45 pixels wide
const pct = (v: number) => (v < 0.01 ? 'under 1%' : `${Math.round(v * 100)}%`)
const COMPASS = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west']
const compass = (deg: number) => COMPASS[Math.round(deg / 45) % 8]

/** End point of a line of `length` degrees of latitude from a point, towards a compass direction. */
function towards(lat: number, lon: number, deg: number, length: number): [number, number] {
  const a = (deg * Math.PI) / 180
  return [lat + length * Math.cos(a), lon + (length * Math.sin(a)) / Math.cos((lat * Math.PI) / 180)]
}

/** What a click on a cell of the next-day outlook shows. Built with text nodes: nothing is read as HTML. */
function detailCard(d: CellDetail): HTMLElement {
  const card = document.createElement('div')
  card.className = 'cell-card'
  const add = (tag: string, text: string, className = '') => {
    const el = document.createElement(tag)
    el.textContent = text
    if (className) el.className = className
    return card.appendChild(el)
  }
  add('strong', `${pct(d.probability)} chance of fire activity on ${d.date}`)
  add('p', `${d.alert ? 'In alert. ' : 'Not in alert. '}Historical rate of this cell at this time of the year: ${pct(d.baseline_probability)}.`)
  if (d.reasons.length) {
    add('p', 'Why the model flags it:', 'label')
    const list = card.appendChild(document.createElement('ol'))
    for (const r of d.reasons) {
      const li = list.appendChild(document.createElement('li'))
      li.textContent = `${r.text} (${Math.round(r.share * 100)}% of the push)`
    }
  }
  if (d.wind) {
    const w = d.wind
    add('p', `Wind that day: from the ${compass(w.wind_from_deg)}, blowing towards the ${compass(w.downwind_deg)}, up to `
      + `${Math.round(w.wind_max_kmh)} km/h with gusts of ${Math.round(w.gust_max_kmh)} km/h. Lowest humidity ${Math.round(w.rh_min_pct)}%, `
      + `highest temperature ${Math.round(w.tmax_c)} °C.`)
    add('p', 'Weather data by Open-Meteo.com. The model does not use it.', 'note')
  }
  add('p', 'It is where activity is most likely, not a forecast that a fire will start.', 'note')
  return card
}

/**
 * Map of Chile and Argentina. While `drawing` is on, dragging draws a rectangle and reports it.
 * `box` is the user's selection; `used` is the block of 0.25° cells the data really covers.
 * `risk` paints one square per cell; cells under 5% are left out to keep the map readable.
 * `daily` is the next-day outlook: the same squares, with an outline on the cells in alert and an arrow
 * where the wind blows to. `rings` shades the surroundings of the hotspots of the day before.
 * A click on a daily cell calls `onCell`; `detail` opens as a popup on its cell.
 * shortcut: mouse only, touch screens must type the coordinates; add pointer events if needed.
 */
export function MapPicker(props: {
  box: Box | null
  used: Box | null
  drawing: boolean
  onDraw: (b: Box) => void
  risk: RiskCell[] | null
  daily: Daily | null
  rings: Rings | null
  detail: CellDetail | null
  onCell: (lat: number, lon: number) => void
  cellDegrees: number
}) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const layers = useRef<L.LayerGroup | null>(null)
  const riskLayer = useRef<L.LayerGroup | null>(null)
  const ringLayer = useRef<L.LayerGroup | null>(null)
  const onDraw = useRef(props.onDraw)
  const onCell = useRef(props.onCell)
  // Outlines and wind arrows only when a cell is wide enough to hold them; far out they hide the colours.
  const [close, setClose] = useState(false)
  useEffect(() => {
    onDraw.current = props.onDraw
    onCell.current = props.onCell
  })

  useEffect(() => {
    const m = L.map(el.current!, { center: [-38, -65], zoom: 4, minZoom: 3 })
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(m)
    ringLayer.current = L.layerGroup().addTo(m) // under the cells
    riskLayer.current = L.layerGroup().addTo(m) // under the selection outlines
    layers.current = L.layerGroup().addTo(m)
    map.current = m
    m.on('zoomend', () => setClose(m.getZoom() >= DETAIL_ZOOM))
    // Leaflet measures its container once; tell it when the layout changes.
    const observer = new ResizeObserver(() => m.invalidateSize())
    observer.observe(el.current!)
    return () => {
      observer.disconnect()
      m.remove()
    }
  }, [])

  useEffect(() => {
    const m = map.current!
    if (!props.drawing) return
    let start: L.LatLng | null = null
    let rect: L.Rectangle | null = null
    m.dragging.disable()
    m.getContainer().style.cursor = 'crosshair'
    const down = (e: L.LeafletMouseEvent) => {
      start = e.latlng
      rect = L.rectangle(L.latLngBounds(start, start), { color: '#0072B2', weight: 2 }).addTo(m)
    }
    const move = (e: L.LeafletMouseEvent) => {
      if (start) rect?.setBounds(L.latLngBounds(start, e.latlng))
    }
    const up = (e: L.LeafletMouseEvent) => {
      if (!start) return
      const b = L.latLngBounds(start, e.latlng)
      rect?.remove()
      start = rect = null
      if (b.getWest() < b.getEast() && b.getSouth() < b.getNorth())
        onDraw.current({
          west: round(b.getWest()), south: round(b.getSouth()), east: round(b.getEast()), north: round(b.getNorth()),
        })
    }
    m.on('mousedown', down).on('mousemove', move).on('mouseup', up)
    return () => {
      m.off('mousedown', down).off('mousemove', move).off('mouseup', up)
      rect?.remove()
      m.dragging.enable()
      m.getContainer().style.cursor = ''
    }
  }, [props.drawing])

  useEffect(() => {
    const group = layers.current!
    group.clearLayers()
    if (props.used)
      L.rectangle(toBounds(props.used), { color: '#D55E00', weight: 1, dashArray: '4 4', fill: false }).addTo(group)
    if (props.box) {
      L.rectangle(toBounds(props.box), { color: '#0072B2', weight: 2, fillOpacity: 0.08 }).addTo(group)
      map.current!.fitBounds(toBounds(props.used ?? props.box), { padding: [30, 30], maxZoom: 9 })
    } else if (props.used) {
      map.current!.fitBounds(toBounds(props.used), { padding: [10, 10] })
    }
  }, [props.box, props.used])

  useEffect(() => {
    const group = riskLayer.current!
    group.clearLayers()
    const renderer = L.canvas() // thousands of squares: one canvas instead of one SVG node each
    for (const [lat, lon, p, base] of props.risk ?? []) {
      const bin = riskBin(p)
      if (!bin) continue
      L.rectangle([[lat, lon], [lat + props.cellDegrees, lon + props.cellDegrees]], {
        renderer, stroke: false, fillColor: bin.color, fillOpacity: 0.7,
      })
        .bindTooltip(`${Math.round(p * 100)}% this week (historical rate ${Math.round(base * 100)}%)`)
        .addTo(group)
    }
    const size = props.cellDegrees
    for (const [lat, lon, p, base, alert] of props.daily?.cells ?? []) {
      const bin = riskBin(p)
      if (!bin && !alert) continue
      L.rectangle([[lat, lon], [lat + size, lon + size]], {
        renderer, stroke: close && alert === 1, color: '#3b0a12', weight: 1, fillColor: bin?.color ?? '#ffffb2', fillOpacity: 0.7,
      })
        .bindTooltip(`${pct(p)} on ${props.daily!.date}${alert ? ', in alert' : ''} (historical rate ${pct(base)}). Click for the reasons.`)
        .on('click', () => onCell.current(lat, lon))
        .addTo(group)
    }
    for (const [lat, lon, deg] of close ? props.daily?.wind ?? [] : []) {
      // An arrow from the centre of the cell towards where the wind blows, with a two-stroke head.
      const from: [number, number] = [lat + size / 2, lon + size / 2]
      const tip = towards(from[0], from[1], deg, size * 0.42)
      const style = { renderer, color: '#1b1f24', weight: 1.2, interactive: false }
      L.polyline([from, tip], style).addTo(group)
      L.polyline([towards(tip[0], tip[1], deg + 150, size * 0.14), tip, towards(tip[0], tip[1], deg - 150, size * 0.14)], style).addTo(group)
    }
  }, [props.risk, props.daily, props.cellDegrees, close])

  useEffect(() => {
    const group = ringLayer.current!
    group.clearLayers()
    if (!props.rings) return
    const renderer = L.canvas()
    // Largest ring first, so the fills add up and the map gets darker near the fire.
    for (const ring of [...props.rings.rings].sort((a, b) => b.km - a.km))
      for (const [lat, lon] of props.rings.points)
        L.circle([lat, lon], { renderer, radius: ring.km * 1000, stroke: false, fillColor: '#7a0177', fillOpacity: 0.07, interactive: false }).addTo(group)
    for (const [lat, lon] of props.rings.points)
      L.circleMarker([lat, lon], { renderer, radius: 2, stroke: false, fillColor: '#3b0a12', fillOpacity: 0.9, interactive: false }).addTo(group)
  }, [props.rings])

  useEffect(() => {
    const d = props.detail
    if (!d) return
    const popup = L.popup({ maxWidth: 320 })
      .setLatLng([d.cell_lat + props.cellDegrees / 2, d.cell_lon + props.cellDegrees / 2])
      .setContent(detailCard(d))
      .openOn(map.current!)
    return () => {
      popup.remove()
    }
  }, [props.detail, props.cellDegrees])

  return <div ref={el} className="map" aria-label="Map to choose the area of interest" />
}
