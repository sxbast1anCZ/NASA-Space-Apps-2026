import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useEffect, useRef } from 'react'
import type { Box, RiskCell } from './api.ts'
import { RISK_BINS } from './api.ts'

const riskBin = (p: number) => RISK_BINS.findLast((b) => p >= b.from)

const toBounds = (b: Box): L.LatLngBoundsExpression => [
  [b.south, b.west],
  [b.north, b.east],
]
const round = (v: number) => Math.round(v * 1000) / 1000

/**
 * Map of Chile and Argentina. While `drawing` is on, dragging draws a rectangle and reports it.
 * `box` is the user's selection; `used` is the block of 0.25° cells the data really covers.
 * `risk` paints one square per cell; cells under 5% are left out to keep the map readable.
 * shortcut: mouse only, touch screens must type the coordinates; add pointer events if needed.
 */
export function MapPicker(props: {
  box: Box | null
  used: Box | null
  drawing: boolean
  onDraw: (b: Box) => void
  risk: RiskCell[] | null
  cellDegrees: number
}) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const layers = useRef<L.LayerGroup | null>(null)
  const riskLayer = useRef<L.LayerGroup | null>(null)
  const onDraw = useRef(props.onDraw)
  useEffect(() => {
    onDraw.current = props.onDraw
  })

  useEffect(() => {
    const m = L.map(el.current!, { center: [-38, -65], zoom: 4, minZoom: 3 })
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(m)
    riskLayer.current = L.layerGroup().addTo(m) // under the selection outlines
    layers.current = L.layerGroup().addTo(m)
    map.current = m
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
  }, [props.risk, props.cellDegrees])

  return <div ref={el} className="map" aria-label="Map to choose the area of interest" />
}
