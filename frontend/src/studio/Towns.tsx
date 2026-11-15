import { ChevronDown, Flame, Home, Navigation, Radar, Users, Wind, X } from 'lucide-react'
import { useState } from 'react'
import { SATS, addDays, type Hotspots } from './data.ts'
import { compass, type Exposure } from './exposure.ts'
import type { Lang } from './i18n.ts'
import { compact, nf, shortDate, shortRegion } from './i18n.ts'
import { LocalNow } from './LocalNow.tsx'

const LEVEL = {
  es: ['', 'Fuego a menos de 25 km', 'Fuego a menos de 10 km', 'Fuego a menos de 5 km'],
  en: ['', 'Fire within 25 km', 'Fire within 10 km', 'Fire within 5 km'],
}
export const LEVEL_HEX = ['#96a0b2', '#fcc43c', '#ff8028', '#eb2828']

/** Panel card: towns near fire, the most exposed first. Expands from 5 to all. */
export function TownsExposed({ lang, exposed, known, onTown }: { lang: Lang; exposed: Exposure[]; known: boolean; onTown: (e: Exposure) => void }) {
  const [all, setAll] = useState(false)
  // No town list on this machine is not the same as no town near a fire.
  if (!known) return <p className="muted">{lang === 'es' ? 'Sin datos de poblados en este equipo: falta NASA_Data_Sources/geonames/cl_ar.tsv.' : 'No town data on this machine: NASA_Data_Sources/geonames/cl_ar.tsv is missing.'}</p>
  if (!exposed.length) return <p className="muted">{lang === 'es' ? 'Ningún poblado de más de 5.000 habitantes a menos de 25 km de un foco.' : 'No town over 5,000 people within 25 km of a hotspot.'}</p>
  const people = exposed.reduce((n, e) => n + e.pop, 0)
  const toward = exposed.filter((e) => e.windToward).length
  const shown = all ? exposed : exposed.slice(0, 5)
  return (
    <>
      <div className="expo-sum">
        <div><Users size={15} /><b>{compact(lang).format(people)}</b><small>{lang === 'es' ? 'personas en poblados a < 25 km' : 'people in towns within 25 km'}</small></div>
        <div><Home size={15} /><b>{exposed.length}</b><small>{lang === 'es' ? 'poblados' : 'towns'}</small></div>
        <div className={toward ? 'warn' : ''}><Wind size={15} /><b>{toward}</b><small>{lang === 'es' ? 'con viento hacia ellos' : 'wind blowing at them'}</small></div>
      </div>
      <ul className="towns">
        {shown.map((e) => (
          <li key={e.t}>
            <button onClick={() => onTown(e)}>
              <span className="house" style={{ color: LEVEL_HEX[e.level] }}><Home size={16} fill="currentColor" /></span>
              <span className="tmain"><b>{e.name}</b><small>{e.region ? shortRegion(e.region) : ''} · {compact(lang).format(e.pop)} hab.</small></span>
              <span className="tdist"><b>{nf(lang, 1).format(e.nearest)} km</b><small>{e.within25} {lang === 'es' ? 'focos' : 'hotspots'}</small></span>
              {e.windToward && <span className="twind" title={lang === 'es' ? 'El viento sopla desde el fuego hacia el poblado' : 'Wind blows from the fire to the town'}><Wind size={13} /></span>}
            </button>
          </li>
        ))}
      </ul>
      {exposed.length > 5 && (
        <button className="more slim" onClick={() => setAll((a) => !a)}>
          <ChevronDown size={14} style={{ transform: all ? 'rotate(180deg)' : '' }} />
          {all ? (lang === 'es' ? 'Ver menos' : 'Show less') : `${lang === 'es' ? 'Ver los' : 'Show all'} ${exposed.length}`}
        </button>
      )}
      <p className="foot">{lang === 'es' ? 'Poblados de 5.000 habitantes o más (GeoNames). Distancia al foco o celda en alerta más cercana. Viento a 10 m (Open-Meteo).' : 'Towns of 5,000 people or more (GeoNames). Distance to the nearest hotspot or alert cell. Wind at 10 m (Open-Meteo).'}</p>
    </>
  )
}

/** Map card of a town: what threatens it, and on demand every nearby fire. */
export function TownCard({ lang, town, exposure, hot, x, y, onClose, onRegion }: {
  lang: Lang; town: [string, number, number, number, string | null]; exposure: Exposure | undefined; hot: Hotspots | null
  x: number; y: number; onClose: () => void; onRegion: (region: string) => void
}) {
  const [open, setOpen] = useState(false)
  const e = exposure
  const es = lang === 'es'
  return (
    <div className="pick town-card glass" style={{ left: Math.min(x + 16, window.innerWidth - 360), top: Math.max(80, Math.min(y - 20, window.innerHeight - 460)) }} role="dialog">
      <button className="close" onClick={onClose} aria-label="close"><X size={15} /></button>
      <span className="eyebrow" style={{ color: e ? LEVEL_HEX[e.level] : undefined }}><Home size={12} /> {e ? LEVEL[lang][e.level] : (es ? 'Sin focos a menos de 25 km' : 'No hotspot within 25 km')}</span>
      <div className="big">{town[0]}</div>
      <LocalNow lang={lang} place={{ name: town[0], lat: town[1], lon: town[2] }} compact />
      <dl>
        <dt>{es ? 'Población' : 'Population'}</dt><dd>{nf(lang).format(town[3])}</dd>
        {town[4] && <><dt>{es ? 'Región' : 'Region'}</dt><dd>{shortRegion(town[4])}</dd></>}
        {e && <>
          <dt>{es ? 'Fuego más cercano' : 'Nearest fire'}</dt><dd><b>{nf(lang, 1).format(e.nearest)} km</b> {es ? 'al' : 'to the'} {compass(e.bearing, lang)} <Navigation size={12} style={{ transform: `rotate(${e.bearing}deg)`, verticalAlign: -1 }} /></dd>
          <dt>{es ? 'Focos cerca' : 'Fires nearby'}</dt><dd>{e.within10} {es ? 'a < 10 km' : 'within 10 km'} · {e.within25} {es ? 'a < 25 km' : 'within 25 km'}</dd>
          <dt>{es ? 'Potencia máx.' : 'Max power'}</dt><dd>{nf(lang).format(e.maxFrp)} MW</dd>
        </>}
      </dl>
      {e && e.windKmh !== null && (
        <div className={`wind-verdict ${e.windToward ? 'bad' : ''}`}>
          <Wind size={16} />
          <span>{e.windToward
            ? (es ? `El viento (${Math.round(e.windKmh)} km/h) sopla desde el fuego hacia ${town[0]}.` : `The wind (${Math.round(e.windKmh)} km/h) blows from the fire towards ${town[0]}.`)
            : (es ? `El viento (${Math.round(e.windKmh)} km/h) no apunta hacia el poblado.` : `The wind (${Math.round(e.windKmh)} km/h) does not point at the town.`)}</span>
        </div>
      )}
      {e && (
        <>
          <button className="expand" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
            <ChevronDown size={14} style={{ transform: open ? 'rotate(180deg)' : '' }} />{open ? (es ? 'Ocultar focos' : 'Hide fires') : (es ? `Ver los ${e.fires.length} focos más cercanos` : `Show the ${e.fires.length} nearest fires`)}
          </button>
          {open && (
            <ol className="near-fires">
              {e.fires.map((f, k) => (
                <li key={k}>
                  {f.kind === 'alert' ? <Radar size={13} /> : <Flame size={13} />}
                  <span>{nf(lang, 1).format(km2(e, f))} km · {f.kind === 'alert' ? `${Math.round((f.p ?? 0) * 100)}% ${es ? 'prob.' : 'chance'}` : `${nf(lang).format(f.frp)} MW`}</span>
                  {f.kind === 'hotspot' && hot && <small>{shortDate(addDays(hot.from, hot.day[f.i]), lang)} {hot.time[f.i]} · {SATS[hot.sat[f.i]]}</small>}
                </li>
              ))}
            </ol>
          )}
        </>
      )}
      {town[4] && <button className="chip accent" onClick={() => onRegion(town[4]!)}>{es ? 'Ver región' : 'Open region'}: {shortRegion(town[4])}</button>}
      <p className="foot">{es ? 'Distancias en línea recta. Un foco es una detección térmica, no el perímetro del incendio.' : 'Straight-line distances. A hotspot is a thermal detection, not the fire perimeter.'}</p>
    </div>
  )
}

function km2(e: Exposure, f: { lat: number; lon: number }) {
  const R = 6371, r = Math.PI / 180
  const a = Math.sin(((f.lat - e.lat) * r) / 2) ** 2 + Math.cos(e.lat * r) * Math.cos(f.lat * r) * Math.sin(((f.lon - e.lon) * r) / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(a))
}
