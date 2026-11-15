import {
  AlertTriangle, ChevronDown, Cloud, CloudDrizzle, CloudFog, CloudLightning, CloudRain, CloudSnow, CloudSun, Droplets, Flame, Leaf,
  Moon, Snowflake, Sun, Sunrise, Sunset, Thermometer, Wind,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { Area } from './data.ts'
import { api } from './data.ts'
import type { Lang } from './i18n.ts'
import { MONTHS } from './i18n.ts'

export type Place = { name: string; lat: number; lon: number; country?: string }
type Weather = {
  timezone: string
  current: { temperature_2m: number; relative_humidity_2m: number; apparent_temperature: number; precipitation: number; weather_code: number
    wind_speed_10m: number; wind_direction_10m: number; wind_gusts_10m: number; is_day: number }
  daily: { temperature_2m_max: number; temperature_2m_min: number; sunrise: string; sunset: string }
}

const weatherCache = new Map<string, Promise<Weather>>()
function getWeather(lat: number, lon: number) {
  const k = `${lat.toFixed(2)},${lon.toFixed(2)}`
  if (!weatherCache.has(k)) {
    weatherCache.set(k, fetch(`/api/ui/weather?lat=${lat.toFixed(3)}&lon=${lon.toFixed(3)}`).then((r) => {
      if (!r.ok) throw new Error(String(r.status))
      return r.json()
    }).catch((e) => { weatherCache.delete(k); throw e }))
  }
  return weatherCache.get(k)!
}

// WMO weather codes, grouped.
function sky(code: number, day: boolean, lang: Lang): { Icon: typeof Sun; text: string } {
  const es = lang === 'es'
  if (code === 0) return { Icon: day ? Sun : Moon, text: es ? 'Despejado' : 'Clear' }
  if (code <= 2) return { Icon: CloudSun, text: es ? 'Parcial' : 'Partly cloudy' }
  if (code === 3) return { Icon: Cloud, text: es ? 'Nublado' : 'Overcast' }
  if (code <= 48) return { Icon: CloudFog, text: es ? 'Niebla' : 'Fog' }
  if (code <= 57) return { Icon: CloudDrizzle, text: es ? 'Llovizna' : 'Drizzle' }
  if (code <= 67 || (code >= 80 && code <= 82)) return { Icon: CloudRain, text: es ? 'Lluvia' : 'Rain' }
  if (code <= 77 || code === 85 || code === 86) return { Icon: CloudSnow, text: es ? 'Nieve' : 'Snow' }
  return { Icon: CloudLightning, text: es ? 'Tormenta' : 'Thunderstorm' }
}

/** Southern-hemisphere season of a local date. */
function season(m: number, d: number, lang: Lang) {
  const md = m * 100 + d
  const es = lang === 'es'
  if (md >= 1221 || md < 320) return { Icon: Sun, text: es ? 'Verano' : 'Summer', cls: 'summer' }
  if (md < 621) return { Icon: Leaf, text: es ? 'Otoño' : 'Autumn', cls: 'autumn' }
  if (md < 922) return { Icon: Snowflake, text: es ? 'Invierno' : 'Winter', cls: 'winter' }
  return { Icon: Sun, text: es ? 'Primavera' : 'Spring', cls: 'spring' }
}

const COMPASS_ES = ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO']
const COMPASS_EN = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']

function useClock() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return now
}

function parts(now: Date, tz: string, lang: Lang) {
  const loc = lang === 'es' ? 'es-CL' : 'en-GB'
  const f = new Intl.DateTimeFormat(loc, { timeZone: tz, hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  const g = new Intl.DateTimeFormat(loc, { timeZone: tz, weekday: 'long', day: 'numeric', month: 'long' })
  const n = new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }).format(now)
  return { time: f.format(now), date: g.format(now), m: Number(n.slice(5, 7)), d: Number(n.slice(8, 10)) }
}

/** Two clocks when no place is chosen. */
export function DualClock({ lang }: { lang: Lang }) {
  const now = useClock()
  const cl = parts(now, 'America/Santiago', lang), ar = parts(now, 'America/Argentina/Buenos_Aires', lang)
  const s = season(cl.m, cl.d, lang)
  return (
    <div className="now-strip">
      <span className="clock"><b>{cl.time.slice(0, 5)}</b><small>Chile</small></span>
      <span className="clock"><b>{ar.time.slice(0, 5)}</b><small>Argentina</small></span>
      <span className={`season ${s.cls}`}><s.Icon size={13} />{s.text}</span>
    </div>
  )
}

/** Local time, season, fire season and the weather right now at a place. Details expand on click. */
export function LocalNow({ lang, place, area, compact }: { lang: Lang; place: Place; area?: Area; compact?: boolean }) {
  const es = lang === 'es'
  const now = useClock()
  const [w, setW] = useState<Weather | null>(null)
  const [err, setErr] = useState(false)
  const [open, setOpen] = useState(false)
  const [peak, setPeak] = useState<{ rank: number; peak: number } | null>(null)

  useEffect(() => {
    let live = true
    setW(null); setErr(false)
    getWeather(place.lat, place.lon).then((x) => live && setW(x)).catch(() => live && setErr(true))
    return () => { live = false }
  }, [place.lat, place.lon])

  const tz = w?.timezone ?? (place.country === 'Argentina' ? 'America/Argentina/Buenos_Aires' : 'America/Santiago')
  const p = parts(now, tz, lang)
  const s = season(p.m, p.d, lang)

  // Fire season: where this month ranks in the typical year of the area.
  useEffect(() => {
    if (!area) return
    let live = true
    api.calendar(area, 'recent').then((c) => {
      const med = c.median_by_month.map((v) => v ?? 0)
      const order = med.map((v, i) => [v, i] as const).sort((a, b) => b[0] - a[0])
      const rank = order.findIndex(([, i]) => i === p.m - 1) + 1
      if (live) setPeak({ rank, peak: order[0][1] })
    }).catch(() => {})
    return () => { live = false }
  }, [area, p.m])

  const c = w?.current
  const sk = c ? sky(c.weather_code, c.is_day === 1, lang) : null
  // The "30-30-30" rule used by fire brigades: over 30 °C, under 30% humidity, wind over 30 km/h.
  const hits = c ? [c.temperature_2m >= 30, c.relative_humidity_2m <= 30, c.wind_speed_10m >= 30].filter(Boolean).length : 0
  const fireSeason = useMemo(() => {
    if (!peak) return null
    const level = peak.rank <= 3 ? 'high' : peak.rank <= 6 ? 'mid' : 'low'
    const text = level === 'high' ? (es ? 'Temporada alta de fuego' : 'Peak fire season') : level === 'mid' ? (es ? 'Temporada media' : 'Mid fire season') : (es ? 'Temporada baja' : 'Low fire season')
    return { level, text, peak: MONTHS[lang][peak.peak] }
  }, [peak, lang])

  return (
    <div className={`localnow ${compact ? 'compact' : ''}`}>
      <button className="ln-main" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className="ln-wx">
          {sk ? <sk.Icon size={compact ? 22 : 28} /> : <Thermometer size={22} />}
          <b>{c ? `${Math.round(c.temperature_2m)}°` : err ? '—' : '…'}</b>
        </span>
        <span className="ln-time">
          <b>{p.time.slice(0, 5)}<i>{p.time.slice(5)}</i></b>
          <small>{es ? 'Hora local' : 'Local time'} · {place.name}</small>
        </span>
        <ChevronDown size={15} className="ln-caret" style={{ transform: open ? 'rotate(180deg)' : '' }} />
      </button>
      <div className="ln-tags">
        <span className={`season ${s.cls}`}><s.Icon size={12} />{s.text}</span>
        {fireSeason && <span className={`fseason ${fireSeason.level}`} title={`${es ? 'Pico' : 'Peak'}: ${fireSeason.peak}`}><Flame size={12} />{fireSeason.text}</span>}
        {sk && <span className="sky">{sk.text}</span>}
        {hits >= 2 && <span className="danger"><AlertTriangle size={12} />{es ? `Clima favorable al fuego (${hits}/3 de 30-30-30)` : `Fire-prone weather (${hits}/3 of 30-30-30)`}</span>}
      </div>
      {open && c && w && (
        <div className="ln-details">
          <span className="ln-date">{p.date}</span>
          <div className="ln-grid">
            <span><Thermometer size={13} />{es ? 'Sensación' : 'Feels like'} <b>{Math.round(c.apparent_temperature)}°</b></span>
            <span><Droplets size={13} />{es ? 'Humedad' : 'Humidity'} <b>{c.relative_humidity_2m}%</b></span>
            <span><Wind size={13} style={{ transform: `rotate(${c.wind_direction_10m + 180}deg)` }} />{es ? 'Viento' : 'Wind'} <b>{Math.round(c.wind_speed_10m)} km/h {(es ? COMPASS_ES : COMPASS_EN)[Math.round(c.wind_direction_10m / 45) % 8]}</b></span>
            <span><Wind size={13} />{es ? 'Ráfagas' : 'Gusts'} <b>{Math.round(c.wind_gusts_10m)} km/h</b></span>
            <span><Thermometer size={13} />{es ? 'Mín / máx' : 'Min / max'} <b>{Math.round(w.daily.temperature_2m_min)}° / {Math.round(w.daily.temperature_2m_max)}°</b></span>
            <span><CloudRain size={13} />{es ? 'Lluvia' : 'Rain'} <b>{c.precipitation} mm</b></span>
            <span><Sunrise size={13} />{es ? 'Amanece' : 'Sunrise'} <b>{w.daily.sunrise.slice(11)}</b></span>
            <span><Sunset size={13} />{es ? 'Anochece' : 'Sunset'} <b>{w.daily.sunset.slice(11)}</b></span>
          </div>
          <small className="foot">{es ? 'Tiempo actual: Open-Meteo. Se actualiza cada 10 minutos.' : 'Current weather: Open-Meteo. Updated every 10 minutes.'}</small>
        </div>
      )}
    </div>
  )
}
