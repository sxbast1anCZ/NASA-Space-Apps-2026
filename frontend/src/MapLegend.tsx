import { FIRE_RED, RISK_BINS, ZONE_COLORS } from './api.ts'

/**
 * What each thing on the map means, for the layers that are on. Shown under the map, so that the colours
 * are explained where they are seen.
 */
export function MapLegend(props: {
  day: string | null       // predicted day of the next-day outlook, when it is on
  seen: string | null      // day of the fires, when the fire layer is on
  rings: boolean
  week: string | null      // week of the weekly outlook, when it is on
}) {
  if (!props.day && !props.week) return null
  return (
    <div className="map-legend" aria-label="What the map shows">
      <div>
        <h3>{props.day ? `Chance of fire activity on ${props.day}` : `Chance of fire activity in the week of ${props.week}`}</h3>
        <p>Each square is a cell of about 25 × 25 km. The colour is the chance that the satellite sees at least one hotspot in it.</p>
        <ul className="legend">
          {RISK_BINS.map((b) => <li key={b.label}><span style={{ background: b.color }} />{b.label}</li>)}
          {props.day && <li><span className="outlined" />In alert (outline, zoom in)</li>}
        </ul>
      </div>
      {props.seen && (
        <div>
          <h3>Fires seen on {props.seen}</h3>
          <ul className="legend single">
            <li><span className="dot" style={{ background: FIRE_RED, borderColor: FIRE_RED }} />A hotspot: heat detected by the satellite</li>
            <li><span className="ring" style={{ borderColor: FIRE_RED }} />A fire: hotspots less than 1 km apart. Point at it for its numbers, click it to zoom in</li>
          </ul>
        </div>
      )}
      {props.seen && (
        <div>
          <h3>Where each fire may show up on {props.day}, if the satellite detects it again</h3>
          <ul className="legend single">
            <li><span style={{ background: ZONE_COLORS.half, opacity: 0.75 }} />Half of its next hotspots fall here</li>
            <li><span style={{ background: ZONE_COLORS.most, opacity: 0.65, borderColor: ZONE_COLORS.edge, borderWidth: 2 }} />8 of 10 fall inside the outline</li>
            <li><span style={{ background: ZONE_COLORS.nearly, opacity: 0.6 }} />9 of 10 fall here</li>
          </ul>
          <p>From fires of the same size in 2013-2022. It is where the satellite will likely see the fire again, not the area that will burn. Clouds or the hours of the passes can hide a fire that is still burning.</p>
        </div>
      )}
      {props.rings && (
        <div>
          <h3>Shaded purple</h3>
          <p>5, 10 and 25 km around every hotspot of the day before: how far next-day fire usually fell, for all fires together.</p>
        </div>
      )}
    </div>
  )
}
