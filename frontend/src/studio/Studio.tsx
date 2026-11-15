import {
  Box as BoxIcon, CalendarDays, ChevronDown, ChevronLeft, ChevronRight, CircleDot, Clock, Factory, Flame, Globe2, Layers,
  Map as MapIcon, Microscope, Moon, Sun, Home, SlidersHorizontal, Plus, Minus as MinusIcon, MousePointerSquareDashed, Pause, Play, Radar, Search, Siren, Sparkles, Trees, Wind, X,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { BurnCalendar, Downloads, Last30, Ranking, Sensors, Summary, TopFires, TypicalYear, type Ctx } from './Cards.tsx'
import { DAILY_BINS, FRP_BINS, INFERNO, RATIO_BINS, REGIME_HEX, WEEKLY_BINS } from './colors.ts'
import type { Area, CellDetail, Daily, GeoFeature, Hotspots, Meta, Regions, Rings } from './data.ts'
import { SATS, addDays, api, isModis, lastDayOfMonth } from './data.ts'
import { DICT, MONTHS, compact, nf, shortDate, shortRegion, type Lang } from './i18n.ts'
import { MapStage, gibsLayer, type Basemap, type Pick } from './MapStage.tsx'
import { About, BasemapPicker, BrasaLogo, EventBadge, Splash } from './Brand.tsx'
import { ALL_CARDS, MODE_LAYERS, PERSONAS, type CardId, type LayerId, type Mode, type PersonaId } from './personas.ts'
import { DayPicker } from './DayPicker.tsx'
import { DualClock, LocalNow, type Place } from './LocalNow.tsx'
import { exposures, firesFrom, type Fire, type Town, type WindField } from './exposure.ts'
import { TownCard, TownsExposed, LEVEL_HEX } from './Towns.tsx'
import './studio.css'

const store = {
  get: (k: string) => { try { return localStorage.getItem(k) } catch { return null } },
  set: (k: string, v: string) => { try { localStorage.setItem(k, v) } catch { /* private mode */ } },
}
const PERSONA_ICON = { flame: Flame, siren: Siren, trees: Trees, microscope: Microscope }
const LAYER_ICON: Record<LayerId, typeof Flame> = {
  towns: Home, hotspots: Flame, heat: Sparkles, density: BoxIcon, risk: Radar, rings: CircleDot, wind: Wind, regimes: CalendarDays, static: Factory, regions: MapIcon,
}
const NOW_DAYS = 14

type Filters = { sensor: 'all' | 'modis' | 'viirs'; conf: 0 | 1 | 2; minFrp: number; time: 'all' | 'day' | 'night' }
const NO_FILTERS: Filters = { sensor: 'all', conf: 0, minFrp: 0, time: 'all' }

function FilterPanel({ lang, mode, value, onChange, onClose }: { lang: Lang; mode: Mode; value: Filters; onChange: (f: Filters) => void; onClose: () => void }) {
  const es = lang === 'es'
  const row = <K extends keyof Filters>(key: K, label: string, opts: [Filters[K], string][]) => (
    <div className="f-row">
      <span className="lbl">{label}</span>
      <div className="seg">{opts.map(([v, l]) => <button key={String(v)} className={value[key] === v ? 'on' : ''} onClick={() => onChange({ ...value, [key]: v })}>{l}</button>)}</div>
    </div>
  )
  return (
    <div className="filters glass" role="dialog">
      <div className="basemaps-head"><SlidersHorizontal size={14} /><b>{es ? 'Filtrar focos' : 'Filter hotspots'}</b><button onClick={onClose}><X size={14} /></button></div>
      {mode === 'history'
        ? row('sensor', es ? 'Serie del mapa' : 'Map series', [['all', es ? 'Armonizada' : 'Harmonized'], ['modis', es ? 'MODIS crudo' : 'Raw MODIS'], ['viirs', es ? 'VIIRS crudo' : 'Raw VIIRS']])
        : row('sensor', 'Sensor', [['all', es ? 'Todos' : 'All'], ['viirs', 'VIIRS 375 m'], ['modis', 'MODIS 1 km']])}
      {mode === 'history' && <p className="f-note">{value.sensor === 'all'
        ? (es ? 'La serie armonizada no se filtra por confianza ni potencia: elige MODIS o VIIRS crudo para usar esos filtros. Compara ambos en 2012–2026 para ver por qué hace falta armonizar.' : 'The harmonized series cannot be filtered by confidence or power: pick raw MODIS or VIIRS for those. Compare both over 2012–2026 to see why harmonization is needed.')
        : value.sensor === 'viirs' ? (es ? 'VIIRS empieza en 2012.' : 'VIIRS starts in 2012.') : (es ? 'MODIS: 2000 a hoy, píxel de 1 km.' : 'MODIS: 2000 to today, 1 km pixel.')}</p>}
      {row('conf', es ? 'Confianza mínima' : 'Minimum confidence', [[0, es ? 'Todas' : 'Any'], [1, 'Nominal'], [2, es ? 'Alta' : 'High']])}
      {row('minFrp', es ? 'Potencia mínima' : 'Minimum power', [[0, es ? 'Todas' : 'Any'], [5, '5 MW'], [20, '20 MW'], [100, '100 MW']])}
      {row('time', es ? 'Momento' : 'Time', [['all', es ? 'Todo' : 'All'], ['day', es ? 'Día' : 'Day'], ['night', es ? 'Noche' : 'Night']])}
      <button className="chip" onClick={() => onChange(NO_FILTERS)}><X size={13} />{es ? 'Quitar filtros' : 'Clear filters'}</button>
      <p className="foot">{es ? 'Se aplican al mapa, a los poblados expuestos y a los focos más intensos.' : 'They apply to the map, the exposed towns and the most intense hotspots.'}</p>
    </div>
  )
}

export default function Studio() {
  const [lang, setLang] = useState<Lang>((store.get('brasa.lang') as Lang) || 'es')
  const t = DICT[lang]
  const [theme, setTheme] = useState<'dark' | 'light'>(() => (store.get('brasa.theme') as 'dark' | 'light')
    || (window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark'))
  // Set before paint, so charts and the map read the right theme on their first render.
  document.documentElement.dataset.theme = theme
  useEffect(() => { store.set('brasa.theme', theme) }, [theme])
  const [personaId, setPersonaId] = useState<PersonaId | null>((store.get('brasa.persona') as PersonaId) || null)
  const persona = PERSONAS.find((p) => p.id === personaId) ?? PERSONAS[0]
  const [mode, setMode] = useState<Mode>(persona.mode)
  const [layers, setLayers] = useState<Set<LayerId>>(new Set([...persona.layers, 'rings', 'wind', 'risk', 'hotspots']))
  const [basemap, setBasemap] = useState<Basemap>((store.get('brasa.basemap') as Basemap) || 'dark')
  const [pickerOpen, setPickerOpen] = useState(false)
  const [aboutOpen, setAboutOpen] = useState(false)
  const [tilt, setTilt] = useState(false)
  const [area, setArea] = useState<Area>({ kind: 'all' })
  const [focus, setFocus] = useState<{ bounds: number[]; key: number; pitch?: number } | null>(null)
  const [drawing, setDrawing] = useState(false)
  const [pick, setPick] = useState<Pick | null>(null)
  const [hover, setHover] = useState<{ text: string; x: number; y: number } | null>(null)
  const [panelOpen, setPanelOpen] = useState(true)
  const [showAll, setShowAll] = useState(false)
  const [collapsed, setCollapsed] = useState<Partial<Record<CardId, boolean>>>({})
  const [moreLayers, setMoreLayers] = useState(false)

  const [meta, setMeta] = useState<Meta | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [boundaries, setBoundaries] = useState<GeoFeature[] | null>(null)
  const [regions, setRegions] = useState<Regions | null>(null)

  // History: a year and a month (0 = the whole year).
  const [year, setYear] = useState(2025)
  const [month, setMonth] = useState(0)
  const [flt, setFlt] = useState<Filters>(NO_FILTERS)
  const [playing, setPlaying] = useState(false)
  const [density, setDensity] = useState<[number, number, number][] | null>(null)
  const [regimes, setRegimes] = useState<[number, number, number, number, number][] | null>(null)
  const [statics, setStatics] = useState<[number, number, number][] | null>(null)
  const [yearTotals, setYearTotals] = useState<{ year: number; harmonized: number; modis: number; viirs: number }[]>([])

  // Now: the last NOW_DAYS days; the slider picks the last day shown and the window how many days back.
  const [nowHot, setNowHot] = useState<Hotspots | null>(null)
  const [nowDays, setNowDays] = useState<{ date: string; hotspots: number; median: number }[]>([])
  const [dayEnd, setDayEnd] = useState(NOW_DAYS - 1)
  const [span, setSpan] = useState(1)

  // Outlook: 'tomorrow', an archive day, or a week of the weekly layer.
  const [fcDay, setFcDay] = useState<string | null>(null)
  const [fcWeek, setFcWeek] = useState<string | null>(null)
  const [daily, setDaily] = useState<Daily | null>(null)
  const [liveDaily, setLiveDaily] = useState<Daily | null>(null)
  const [rings, setRings] = useState<Rings | null>(null)
  const [weekly, setWeekly] = useState<[number, number, number, number][] | null>(null)
  const [fcHot, setFcHot] = useState<Hotspots | null>(null)
  const [townList, setTownList] = useState<Town[] | null>(null)
  const [windField, setWindField] = useState<WindField | null>(null)
  const [windErr, setWindErr] = useState<string | null>(null)

  useEffect(() => { store.set('brasa.lang', lang); document.documentElement.lang = lang }, [lang])

  useEffect(() => {
    api.meta().then((m) => {
      setMeta(m)
      setFcDay(m.risk_days[0] ?? null)
      setYear(Number(m.data_through.slice(0, 4)) - 1)
    }).catch((e) => setError(String(e.message)))
    api.boundaries().then((b) => setBoundaries(b.features)).catch(() => {})
    api.regions().then(setRegions).catch(() => {})
    api.regimes().then((r) => setRegimes(r.cells)).catch(() => {})
    api.statics().then((s) => setStatics(s.points)).catch(() => {})
    api.towns().then((x) => setTownList(x.towns)).catch(() => {})
    api.yearly().then((s) => setYearTotals(s.years)).catch(() => {})
  }, [])

  const through = meta?.data_through ?? ''
  const nowFrom = through ? addDays(through, -(NOW_DAYS - 1)) : ''
  useEffect(() => {
    if (!through) return
    api.hotspots(nowFrom, through).then(setNowHot).catch(() => {})
    api.days({ kind: 'all' }, nowFrom, through).then((d) => setNowDays(d.days)).catch(() => {})
  }, [through])

  useEffect(() => {
    if (!meta) return
    const from = month ? `${year}-${String(month).padStart(2, '0')}-01` : `${year}-01-01`
    const to = month ? `${year}-${String(month).padStart(2, '0')}-${lastDayOfMonth(year, month)}` : `${year}-12-31`
    api.density(from, to, { sensor: flt.sensor === 'all' ? 'harmonized' : flt.sensor, minConf: flt.conf, minFrp: flt.minFrp, time: flt.time })
      .then((d) => setDensity(d.cells)).catch(() => {})
  }, [meta, year, month, flt])

  useEffect(() => {
    if (!fcDay) return
    api.daily(fcDay).then((d) => { setDaily(d); if (fcDay === meta?.risk_days[0]) setLiveDaily(d) }).catch(() => setDaily(null))
    api.rings(fcDay).then(setRings).catch(() => setRings(null))
    // What really happened that day, when the data has it: the check of the outlook.
    api.hotspots(fcDay, fcDay).then(setFcHot).catch(() => setFcHot(null))
  }, [fcDay])
  useEffect(() => {
    if (!fcWeek) { setWeekly(null); return }
    api.weekly(fcWeek).then((w) => setWeekly(w.cells)).catch(() => setWeekly(null))
  }, [fcWeek])
  useEffect(() => { if (meta?.risk_days[0]) api.daily(meta.risk_days[0]).then(setLiveDaily).catch(() => {}) }, [meta])

  // Playback: years in history, days in now.
  useEffect(() => {
    if (!playing) return
    const id = setInterval(() => {
      if (mode === 'history') setYear((y) => (y >= 2025 ? 2001 : y + 1))
      else if (mode === 'now') setDayEnd((d) => (d >= NOW_DAYS - 1 ? 0 : d + 1))
    }, mode === 'history' ? 1300 : 900)
    return () => clearInterval(id)
  }, [playing, mode])
  useEffect(() => {
    setPlaying(false)
    // Each mode opens with its main layer on, so the map is never empty after a switch.
    const main: Record<Mode, LayerId[]> = { history: ['density'], now: ['hotspots'], forecast: ['risk', 'wind'] }
    setLayers((s) => (MODE_LAYERS[mode].some((l) => s.has(l) && main[mode].includes(l)) ? s : new Set([...s, ...main[mode]])))
  }, [mode])

  useEffect(() => { store.set('brasa.basemap', basemap) }, [basemap])
  // Keyboard: 1 2 3 modes, space plays, arrows move in time, Esc closes.
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === 'INPUT') return
      if (e.key === '1') setMode('history')
      else if (e.key === '2') setMode('now')
      else if (e.key === '3') setMode('forecast')
      else if (e.key === ' ') { e.preventDefault(); setPlaying((p) => !p) }
      else if (e.key === 'Escape') { setPick(null); setDrawing(false); setPickerOpen(false); setAboutOpen(false); setFiltersOpen(false) }
      else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        const d = e.key === 'ArrowRight' ? 1 : -1
        setMode((m) => {
          if (m === 'history') setYear((y) => Math.min(2026, Math.max(2001, y + d)))
          if (m === 'now') setDayEnd((x) => Math.min(NOW_DAYS - 1, Math.max(0, x + d)))
          return m
        })
      }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [])

  function choosePersona(id: PersonaId) {
    const p = PERSONAS.find((x) => x.id === id)!
    setPersonaId(id)
    store.set('brasa.persona', id)
    setMode(p.mode)
    setLayers(new Set([...p.layers, ...(p.mode === 'forecast' ? ['risk', 'wind'] : []), ...(p.mode === 'now' ? ['hotspots'] : [])] as LayerId[]))
    setShowAll(false)
    setPanelOpen(true)
  }
  const toggle = (id: LayerId) => setLayers((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })

  function selectRegion(country: string, admin1: string) {
    const row = regions?.regions.find((r) => r.country === country && r.admin1 === admin1)
    setArea({ kind: 'region', country, admin1, bounds: row?.bounds })
    if (row) setFocus({ bounds: row.bounds, key: Date.now() })
    setPanelOpen(true)
  }
  function selectCountry(country: string | null) {
    setPick(null)
    if (!country) { setArea({ kind: 'all' }); setFocus({ bounds: [-78, -56, -52, -17], key: Date.now() }); return }
    setArea({ kind: 'country', country })
    const rows = (regions?.regions ?? []).filter((r) => r.country === country && !/Tierra del Fuego|Magallanes/.test(r.admin1) || r.country === country)
    if (rows.length) setFocus({
      bounds: [Math.min(...rows.map((r) => r.bounds[0])), Math.max(-56, Math.min(...rows.map((r) => r.bounds[1]))), Math.max(...rows.map((r) => r.bounds[2])), Math.max(...rows.map((r) => r.bounds[3]))],
      key: Date.now(),
    })
    setPanelOpen(true)
  }
  // admin1 -> country, to filter hotspots that carry only their region.
  const regionCountry = useMemo(() => new Map((meta?.regions ?? []).map((r) => [r.admin1, r.country])), [meta])
  const [filtersOpen, setFiltersOpen] = useState(false)
  const nFilters = (flt.sensor !== 'all' ? 1 : 0) + (flt.conf ? 1 : 0) + (flt.minFrp ? 1 : 0) + (flt.time !== 'all' ? 1 : 0)
  // One test per hotspot: the selected country or region, then the filters of the filter panel.
  const hotFilter = useMemo(() => {
    const byArea = area.kind === 'country' ? (r: string | null) => !!r && regionCountry.get(r) === area.country
      : area.kind === 'region' ? (r: string | null) => r === area.admin1 : null
    if (!byArea && !nFilters) return null
    return (h: Hotspots, i: number) => {
      if (byArea && !byArea(h.region[i])) return false
      if (flt.sensor === 'modis' && h.sat[i] > 1) return false
      if (flt.sensor === 'viirs' && h.sat[i] <= 1) return false
      if (h.conf[i] < flt.conf) return false
      if (h.frp[i] < flt.minFrp) return false
      if (flt.time === 'day' && h.night[i]) return false
      if (flt.time === 'night' && !h.night[i]) return false
      return true
    }
  }, [area, regionCountry, flt, nFilters])

  function selectBox(b: { west: number; south: number; east: number; north: number }, label?: string) {
    setArea({ kind: 'box', ...b, label })
    setDrawing(false)
    setFocus({ bounds: [b.west, b.south, b.east, b.north], key: Date.now() })
    setPanelOpen(true)
  }
  const fly = (lon: number, lat: number) => setFocus({ bounds: [lon - 0.15, lat - 0.12, lon + 0.15, lat + 0.12], key: Date.now() })

  const areaName = area.kind === 'all' ? t.allArea : area.kind === 'country' ? area.country : area.kind === 'region' ? shortRegion(area.admin1)
    : area.label ?? `${area.south.toFixed(2)}°, ${area.west.toFixed(2)}° → ${area.north.toFixed(2)}°, ${area.east.toFixed(2)}°`
  const areaCountry = area.kind === 'region' ? area.country : area.kind === 'country' ? (lang === 'es' ? 'País' : 'Country') : area.kind === 'all' ? 'Chile · Argentina' : 'lat / lon'
  const selCountry = area.kind === 'country' || area.kind === 'region' ? area.country : null

  // Day of the NASA imagery: follows the timeline.
  const imageryDate = !through ? '2026-11-12'
    : mode === 'now' ? addDays(nowFrom, dayEnd)
    : mode === 'forecast' ? (fcDay && fcDay <= through ? fcDay : through)
    : `${year}-${String(month || 8).padStart(2, '0')}-15` > through ? through : `${year}-${String(month || 8).padStart(2, '0')}-15`
  const nasaImagery = basemap === 'truecolor' || basemap === 'firecolor'

  // Wind field of the day on the map; not while playing, to stay inside Open-Meteo's rate limit.
  const wantWind = layers.has('wind') || layers.has('towns')
  useEffect(() => {
    if (!wantWind || playing || !through) return
    let live = true
    const id = setTimeout(() => {
      api.windfield(imageryDate).then((w) => { if (live) { setWindField(w); setWindErr(null) } })
        .catch((e) => live && setWindErr(String(e.message ?? e)))
    }, 250)
    return () => { live = false; clearTimeout(id) }
  }, [wantWind, imageryDate, playing, through])

  const mapHot = mode === 'now' ? nowHot : mode === 'forecast' && !fcWeek ? fcHot : null
  const dayWindow: [number, number] = mode === 'now' ? [Math.max(0, dayEnd - span + 1), dayEnd] : [0, 0]
  const shownCount = useMemo(() => {
    if (!mapHot) return 0
    let n = 0
    for (let i = 0; i < mapHot.count; i++) if (mapHot.day[i] >= dayWindow[0] && mapHot.day[i] <= dayWindow[1] && (!hotFilter || hotFilter(mapHot, i))) n++
    return n
  }, [mapHot, dayWindow[0], dayWindow[1], hotFilter])

  // Towns near fire: hotspots of the window (now), or the alert cells and that day's hotspots (outlook).
  const exposed = useMemo(() => {
    if (!townList || !layers.has('towns') || mode === 'history') return []
    let fires: Fire[] = []
    if (mode === 'now') fires = firesFrom(nowHot, dayWindow, hotFilter)
    else if (!fcWeek) {
      fires = firesFrom(fcHot, [0, 0], hotFilter)
      for (const c of daily?.cells ?? []) if (c[4] === 1) fires.push({ lat: c[0] + 0.125, lon: c[1] + 0.125, frp: 0, i: -1, kind: 'alert', p: c[2] })
    }
    const ex = exposures(townList, fires, windField)
    if (area.kind === 'country') return ex.filter((e) => e.region && regionCountry.get(e.region) === area.country)
    if (area.kind === 'region') return ex.filter((e) => e.region === area.admin1)
    return ex
  }, [townList, layers, mode, nowHot, fcHot, daily, fcWeek, dayWindow[0], dayWindow[1], hotFilter, windField, area, regionCountry])

  // With filters on, the day bars count the filtered raw detections instead of the harmonized series.
  const filteredDays = useMemo(() => {
    if (!nowHot || !hotFilter || !nFilters) return null
    const n = new Array(NOW_DAYS).fill(0)
    for (let i = 0; i < nowHot.count; i++) if (hotFilter(nowHot, i)) n[nowHot.day[i]]++
    return n as number[]
  }, [nowHot, hotFilter, nFilters])
  const filterLabel = !nFilters ? '' : [
    flt.sensor !== 'all' && (mode === 'history' ? (flt.sensor === 'modis' ? 'MODIS crudo' : 'VIIRS crudo') : flt.sensor.toUpperCase()),
    flt.conf && (flt.conf === 2 ? (lang === 'es' ? 'conf. alta' : 'high conf.') : (lang === 'es' ? 'conf. ≥ nominal' : 'conf. ≥ nominal')),
    flt.minFrp && `≥ ${flt.minFrp} MW`, flt.time !== 'all' && (flt.time === 'day' ? (lang === 'es' ? 'día' : 'day') : (lang === 'es' ? 'noche' : 'night')),
  ].filter(Boolean).join(' · ')

  // Place of the "now" strip: the largest town of the selected region, or of the country.
  const place = useMemo<Place | null>(() => {
    if (!townList || area.kind === 'all' || area.kind === 'box') return null
    const tw = area.kind === 'region' ? townList.find((x) => x[4] === area.admin1)
      : townList.find((x) => x[4] && regionCountry.get(x[4]) === area.country)
    return tw ? { name: tw[0], lat: tw[1], lon: tw[2], country: area.country } : null
  }, [townList, area, regionCountry])

  const ctx: Ctx = {
    filtered: nFilters > 0, keep: hotFilter, lang, t, theme, area, through, daily: liveDaily, hotspots: nowHot, dayWindow: mode === 'now' ? dayWindow : [NOW_DAYS - 1, NOW_DAYS - 1],
    regions: regions?.regions ?? null, regionCountry, onRegion: selectRegion, onFly: fly, historyYear: year,
  }
  const cardOrder: CardId[] = [...persona.cards, ...ALL_CARDS.filter((c) => !persona.cards.includes(c))]
  const visibleCards = showAll ? cardOrder : persona.cards
  const CARD_TITLE: Record<CardId, string> = {
    exposure: t.exposure, summary: areaName, top: t.topFires, ranking: t.ranking, calendar: t.calendar, typical: t.typicalYear,
    last30: t.last30, sensors: t.sensors, downloads: t.downloads,
  }
  const CARD: Record<CardId, (c: { c: Ctx }) => React.ReactNode> = {
    exposure: () => <TownsExposed lang={lang} exposed={exposed} onTown={(e) => { setFocus({ bounds: [e.lon - 0.45, e.lat - 0.35, e.lon + 0.45, e.lat + 0.35], key: Date.now() }); setTimeout(() => setPick({ kind: 'town', t: e.t, x: window.innerWidth / 2 + 60, y: window.innerHeight / 2 - 120 }), 700) }} />,
    summary: Summary, top: TopFires, ranking: Ranking, calendar: BurnCalendar, typical: TypicalYear,
    last30: Last30, sensors: Sensors, downloads: Downloads,
  }
  const regimeNames = t.regimes

  if (error) return <div className="fatal glass"><Flame /> <div><b>API</b><p>{error}</p><p className="muted">uvicorn backend.ui:app --port 8000</p></div></div>

  return (
    <div className="studio" data-mode={mode}>
      <MapStage
        mode={mode} layers={layers} basemap={basemap} imageryDate={imageryDate} theme={theme} tilt={tilt} hotspots={mapHot} dayWindow={dayWindow}
        density={density} regimes={regimes} statics={statics} daily={mode === 'forecast' ? daily : null}
        weekly={mode === 'forecast' ? weekly : null} rings={mode !== 'history' ? rings : null}
        boundaries={boundaries} regionRows={regions?.regions ?? null} area={area} hotFilter={hotFilter} windField={layers.has('wind') ? windField : null} townList={townList} exposed={exposed} showTowns={layers.has('towns')} focus={focus} drawing={drawing}
        onBox={(b) => selectBox(b)} onRegion={selectRegion} onPick={setPick} regimeNames={regimeNames}
        onHover={(text, x, y) => setHover(text ? { text, x, y } : null)}
      />
      <div className="vignette" />

      {/* ---------------------------------------------------------------- top bar */}
      <header className="topbar">
        <div className="brand glass">
          <BrasaLogo size={38} />
          <div><b>{t.brand}</b><span>{t.brandSub}</span></div>
        </div>
        <EventBadge lang={lang} onInfo={() => setAboutOpen(true)} />
        <SearchBox lang={lang} meta={meta} onRegion={selectRegion} onPoint={(lat, lon) => fly(lon, lat)} />
        <div className="personas glass" role="tablist" aria-label={t.profile}>
          {PERSONAS.map((p) => {
            const I = PERSONA_ICON[p.icon]
            return (
              <button key={p.id} role="tab" aria-selected={p.id === persona.id} className={p.id === persona.id ? 'on' : ''}
                style={{ '--pc': p.color } as React.CSSProperties} onClick={() => choosePersona(p.id)} title={p.pitch[lang]}>
                <I size={16} /><span>{p.name[lang]}</span>
              </button>
            )
          })}
        </div>
        <button className="theme-btn glass" onClick={() => setTheme((x) => (x === 'dark' ? 'light' : 'dark'))}
          title={theme === 'dark' ? (lang === 'es' ? 'Modo claro' : 'Light mode') : (lang === 'es' ? 'Modo oscuro' : 'Dark mode')} aria-label="theme">
          {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>
        <div className="lang glass">
          {(['es', 'en'] as Lang[]).map((l) => <button key={l} className={l === lang ? 'on' : ''} onClick={() => setLang(l)}>{l.toUpperCase()}</button>)}
        </div>
      </header>

      {/* ---------------------------------------------------------------- insight panel */}
      <aside className={`panel glass ${panelOpen ? '' : 'closed'}`} aria-label={areaName}>
        <button className="panel-toggle glass" onClick={() => setPanelOpen((o) => !o)} aria-label="panel">
          {panelOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
        </button>
        <div className="panel-head">
          <div>
            <span className="eyebrow" style={{ color: persona.color }}>{persona.name[lang]} · {areaCountry}</span>
            <h1>{areaName}</h1>
          </div>
          <div className="countries" role="group" aria-label={lang === 'es' ? 'País' : 'Country'}>
            <button className={!selCountry ? 'on' : ''} onClick={() => selectCountry(null)}><span className="flags"><FlagCL /><FlagAR /></span>{lang === 'es' ? 'Ambos' : 'Both'}</button>
            <button className={selCountry === 'Chile' ? 'on' : ''} onClick={() => selectCountry('Chile')}><FlagCL />Chile</button>
            <button className={selCountry === 'Argentina' ? 'on' : ''} onClick={() => selectCountry('Argentina')}><FlagAR />Argentina</button>
          </div>
          <label className="region-select">
            <MapIcon size={14} />
            <select value={area.kind === 'region' ? `${area.country}|${area.admin1}` : ''}
              onChange={(e) => {
                if (!e.target.value) return selectCountry(selCountry)
                const [c, a] = e.target.value.split('|')
                selectRegion(c, a)
              }} aria-label={t.region}>
              <option value="">{lang === 'es' ? `Todas las regiones${selCountry ? ` de ${selCountry}` : ''}` : `All regions${selCountry ? ` of ${selCountry}` : ''}`}</option>
              {(['Chile', 'Argentina'] as const).filter((c) => !selCountry || c === selCountry).map((c) => (
                <optgroup key={c} label={c}>
                  {(meta?.regions ?? []).filter((r) => r.country === c).sort((a, b) => shortRegion(a.admin1).localeCompare(shortRegion(b.admin1)))
                    .map((r) => <option key={r.admin1} value={`${c}|${r.admin1}`}>{shortRegion(r.admin1)}</option>)}
                </optgroup>
              ))}
            </select>
            <ChevronDown size={14} className="sel-caret" />
          </label>
          {place ? <LocalNow lang={lang} place={place} area={area} /> : <DualClock lang={lang} />}
        </div>
        <div className="cards">
          {visibleCards.map((id, k) => {
            const C = CARD[id]
            const isOpen = id === 'summary' || (collapsed[id] === undefined ? k < 2 : !collapsed[id])
            return (
              <section key={id} className={`card card-${id} ${isOpen ? '' : 'shut'}`}>
                {id !== 'summary' && (
                  <button className="card-head" onClick={() => setCollapsed((c) => ({ ...c, [id]: isOpen }))} aria-expanded={isOpen}>
                    <h2>{CARD_TITLE[id]}</h2><ChevronDown size={15} style={{ transform: isOpen ? 'rotate(180deg)' : '' }} />
                  </button>
                )}
                {isOpen && <C c={ctx} />}
              </section>
            )
          })}
          <button className="more" onClick={() => setShowAll((s) => !s)}>
            <ChevronDown size={15} style={{ transform: showAll ? 'rotate(180deg)' : '' }} />{showAll ? t.less : `${t.more} (${cardOrder.length - persona.cards.length})`}
          </button>
          <p className="sources">{t.sources}</p>
        </div>
      </aside>

      {/* ---------------------------------------------------------------- layer rail */}
      <nav className="rail glass" aria-label={t.layers}>
        <span className="rail-title"><Layers size={13} />{t.layers}</span>
        {MODE_LAYERS[mode].filter((id, k) => moreLayers || k < 4 || layers.has(id)).map((id) => {
          const I = LAYER_ICON[id]
          const label = t[`L_${id}` as const]
          return (
            <button key={id} className={layers.has(id) ? 'on' : ''} onClick={() => toggle(id)} aria-pressed={layers.has(id)}>
              <I size={18} /><span>{label}</span>
            </button>
          )
        })}
        {MODE_LAYERS[mode].length > 4 && (
          <button className="rail-more" onClick={() => setMoreLayers((x) => !x)} aria-expanded={moreLayers}>
            {moreLayers ? <MinusIcon size={15} /> : <Plus size={15} />}<span>{moreLayers ? (lang === 'es' ? 'Menos' : 'Less') : (lang === 'es' ? 'Más capas' : 'More')}</span>
          </button>
        )}
        <hr />
        <button className={filtersOpen || nFilters ? 'on alt' : ''} onClick={() => setFiltersOpen((o) => !o)}>
          <SlidersHorizontal size={18} /><span>{lang === 'es' ? 'Filtros' : 'Filters'}</span>{nFilters > 0 && <em className="badge">{nFilters}</em>}
        </button>
        <button className={tilt ? 'on' : ''} onClick={() => setTilt((x) => !x)} aria-pressed={tilt}><BoxIcon size={18} /><span>{t.L_3d}</span></button>
        <button className={pickerOpen || basemap !== 'dark' ? 'on alt' : ''} onClick={() => setPickerOpen((o) => !o)}>
          <Globe2 size={18} /><span>{t.basemap}</span>
        </button>
      </nav>

      {filtersOpen && <FilterPanel lang={lang} mode={mode} value={flt} onChange={setFlt} onClose={() => setFiltersOpen(false)} />}
      <Legend lang={lang} mode={mode} layers={layers} t={t} weekly={!!fcWeek} rings={rings} shown={mapHot ? t.shown(nf(lang).format(shownCount)) : null} filterLabel={filterLabel} onClearFilters={() => setFlt(NO_FILTERS)} />

      {/* ---------------------------------------------------------------- timeline */}
      <footer className="timeline glass">
        <div className="modes" role="tablist">
          {([['history', Clock, t.modeHistory, t.modeHistoryHint], ['now', Flame, t.modeNow, t.modeNowHint], ['forecast', Radar, t.modeForecast, t.modeForecastHint]] as const).map(([m, I, label, hint]) => (
            <button key={m} role="tab" aria-selected={mode === m} className={mode === m ? 'on' : ''} onClick={() => setMode(m)} title={hint}>
              <I size={16} /><span><b>{label}</b><small>{hint}</small></span>
            </button>
          ))}
        </div>
        <div className="track">
          {mode === 'history' && (
            <>
              <button className="play" onClick={() => setPlaying((p) => !p)} aria-label={playing ? t.pause : t.play}>{playing ? <Pause size={18} /> : <Play size={18} />}</button>
              <div className="years">
                <div className="bars">
                  {yearTotals.map((y) => {
                    const key = flt.sensor === 'all' ? 'harmonized' : flt.sensor
                    const max = Math.max(1, ...yearTotals.map((r) => r[key]))
                    return (
                      <button key={y.year} className={`ybar ${y.year === year ? 'on' : ''} ${y.year < 2012 && key === 'harmonized' ? 'est' : ''} ${key}`} onClick={() => setYear(y.year)}
                        title={`${y.year}: ${nf(lang).format(y[key])} ${t.detections}`}>
                        <i style={{ height: `${y[key] ? 8 + (y[key] / max) * 92 : 2}%` }} />
                        <span>{y.year % 5 === 0 || y.year === year ? `'${String(y.year).slice(2)}` : ''}</span>
                      </button>
                    )
                  })}
                </div>
                <div className="months">
                  <button className={month === 0 ? 'on' : ''} onClick={() => setMonth(0)}>{year} · {t.whole}</button>
                  {MONTHS[lang].map((m, i) => <button key={m} className={month === i + 1 ? 'on' : ''} onClick={() => setMonth(i + 1)}>{m}</button>)}
                </div>
              </div>
            </>
          )}
          {mode === 'now' && (
            <>
              <button className="play" onClick={() => setPlaying((p) => !p)} aria-label={playing ? t.pause : t.play}>{playing ? <Pause size={18} /> : <Play size={18} />}</button>
              <div className="days">
                <div className="bars">
                  {nowDays.map((d0, i) => {
                    const d = filteredDays ? { ...d0, hotspots: filteredDays[i] } : d0
                    const max = Math.max(1, ...(filteredDays ?? nowDays.map((x) => Math.max(x.hotspots, x.median))))
                    const inWin = i >= dayWindow[0] && i <= dayWindow[1]
                    return (
                      <button key={d.date} className={`dbar ${inWin ? 'on' : ''} ${i === dayEnd ? 'end' : ''}`} onClick={() => setDayEnd(i)}
                        title={`${shortDate(d.date, lang)}: ${nf(lang).format(d.hotspots)} · ${t.median} ${nf(lang).format(d.median)}`}>
                        <i style={{ height: `${6 + (d.hotspots / max) * 94}%` }} />
                        {!filteredDays && <em style={{ bottom: `${(d.median / max) * 100}%` }} />}
                        <span>{shortDate(d.date, lang)}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
              <div className="seg">
                {[1, 3, 7, 14].map((n) => <button key={n} className={span === n ? 'on' : ''} onClick={() => setSpan(n)}>{n}d</button>)}
              </div>
            </>
          )}
          {mode === 'forecast' && meta && (
            <div className="fc">
              <button className={`fc-chip big ${!fcWeek && fcDay === meta.risk_days[0] ? 'on' : ''}`} onClick={() => { setFcWeek(null); setFcDay(meta.risk_days[0]) }}>
                <Radar size={16} /><span><b>{t.tomorrow}</b><small>{meta.risk_days[0] ? shortDate(meta.risk_days[0], lang) : '—'}</small></span>
              </button>
              <div className="fc-weeks">
                <span className="lbl">{t.weeks}</span>
                {meta.risk_weeks.slice(0, 6).map((w) => (
                  <button key={w} className={`fc-chip ${fcWeek === w ? 'on' : ''}`} onClick={() => setFcWeek(w)}>{shortDate(w, lang)}</button>
                ))}
              </div>
              <div className="archive">
                <DayPicker lang={lang} days={meta.risk_days.slice(1)} value={!fcWeek && fcDay !== meta.risk_days[0] ? fcDay : null}
                  onPick={(d) => { setFcWeek(null); setFcDay(d) }} label={t.archive} />
              </div>
            </div>
          )}
        </div>
      </footer>

      {pickerOpen && <BasemapPicker lang={lang} value={basemap} date={imageryDate} onChange={(b) => setBasemap(b)} onClose={() => setPickerOpen(false)} />}
      {nasaImagery && (
        <div className="imagery glass"><span className="live-dot" />{lang === 'es' ? 'Imagen satelital NASA' : 'NASA satellite image'} · {gibsLayer(basemap as 'truecolor', imageryDate).sensor} · <b>{shortDate(imageryDate, lang)} {imageryDate.slice(0, 4)}</b>
          {basemap === 'firecolor' && <small>{lang === 'es' ? 'rojo-naranjo = calor / cicatriz; verde = vegetación' : 'red-orange = heat / scar; green = vegetation'}</small>}</div>
      )}
      {aboutOpen && <About lang={lang} onClose={() => setAboutOpen(false)} />}
      {!meta && <Splash lang={lang} />}
      {hover && !pick && <div className="hover glass" style={{ left: hover.x + 14, top: hover.y + 14 }}>{shortRegion(hover.text)}</div>}
      {pick?.kind === 'town' && townList && <TownCard lang={lang} town={townList[pick.t]} exposure={exposed.find((e) => e.t === pick.t)} hot={mode === 'now' ? nowHot : fcHot}
        x={pick.x} y={pick.y} onClose={() => setPick(null)} onRegion={(r) => { setPick(null); const c = regionCountry.get(r); if (c) selectRegion(c, r) }} />}
      {layers.has('wind') && (windField || windErr) && (
        <div className="wind-chip glass"><Wind size={14} />
          {windErr ? <span>{lang === 'es' ? 'Viento no disponible ahora (límite de Open-Meteo, reintenta en un minuto)' : 'Wind not available now (Open-Meteo limit, retry in a minute)'}</span>
            : <span>{lang === 'es' ? 'Viento a 10 m' : 'Wind at 10 m'} · {shortDate(windField!.date, lang)} {windField!.date.slice(0, 4)} · 15 h · {lang === 'es' ? 'máx.' : 'max'} {Math.round(windField!.max)} km/h</span>}
        </div>
      )}
      {pick && pick.kind !== 'town' && <PickCard pick={pick} lang={lang} hot={mapHot} day={fcDay} mode={mode} onClose={() => setPick(null)}
        onHistory={(region) => { setPick(null); const c = regionCountry.get(region); if (c) selectRegion(c, region) }} />}
      {drawing && <div className="draw-hint glass"><MousePointerSquareDashed size={16} />{t.drawHint}<button onClick={() => setDrawing(false)}><X size={14} /></button></div>}
      {!personaId && <Onboarding lang={lang} onPick={choosePersona} setLang={setLang} />}
    </div>
  )
}

// ------------------------------------------------------------------ search
function SearchBox({ lang, meta, onRegion, onPoint }: { lang: Lang; meta: Meta | null; onRegion: (c: string, a: string) => void; onPoint: (lat: number, lon: number) => void }) {
  const t = DICT[lang]
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const norm = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
  const coord = q.match(/^\s*(-?\d+(?:\.\d+)?)\s*[,; ]\s*(-?\d+(?:\.\d+)?)\s*$/)
  const hits = !q || coord ? [] : (meta?.regions ?? []).filter((r) => norm(r.admin1).includes(norm(q)) || norm(r.country).includes(norm(q))).slice(0, 7)
  return (
    <div className="search glass" onBlur={() => setTimeout(() => setOpen(false), 150)}>
      <Search size={16} />
      <input value={q} placeholder={t.search} onFocus={() => setOpen(true)} onChange={(e) => { setQ(e.target.value); setOpen(true) }}
        onKeyDown={(e) => {
          if (e.key !== 'Enter') return
          if (coord) { onPoint(Number(coord[1]), Number(coord[2])); setOpen(false) }
          else if (hits[0]) { onRegion(hits[0].country, hits[0].admin1); setQ(shortRegion(hits[0].admin1)); setOpen(false) }
        }} aria-label={t.search} />
      {open && (hits.length > 0 || coord) && (
        <ul className="results glass">
          {coord && <li><button onClick={() => { onPoint(Number(coord[1]), Number(coord[2])); setOpen(false) }}>📍 {coord[1]}, {coord[2]}</button></li>}
          {hits.map((r) => (
            <li key={r.country + r.admin1}><button onClick={() => { onRegion(r.country, r.admin1); setQ(shortRegion(r.admin1)); setOpen(false) }}>
              <span className="flag">{r.country === 'Chile' ? 'CL' : 'AR'}</span>{shortRegion(r.admin1)}
            </button></li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ legend
function Legend({ lang, mode, layers, t, weekly, rings, shown, filterLabel, onClearFilters }: { filterLabel: string; onClearFilters: () => void; lang: Lang; mode: Mode; layers: Set<LayerId>; t: typeof DICT.es; weekly: boolean; rings: Rings | null; shown: string | null }) {
  const blocks: React.ReactNode[] = []
  if (mode === 'history' && layers.has('density')) blocks.push(
    <div key="d"><b>{t.legendDensity}</b><div className="ramp" style={{ background: `linear-gradient(90deg, ${INFERNO.join(',')})` }} /><div className="ramp-ends"><span>{t.fewer}</span><span>{t.moreFire}</span></div></div>)
  if (layers.has('heat')) blocks.push(
    <div key="heat"><b>{t.L_heat} · {mode === 'forecast' ? t.legendRisk : t.detections}</b><div className="ramp" style={{ background: 'linear-gradient(90deg, rgba(65,10,105,.2), #8c196e, #cd3c4b, #f5781e, #fcbe28, #fcffa4)' }} /><div className="ramp-ends"><span>{t.fewer}</span><span>{t.moreFire}</span></div></div>)
  if ((mode === 'now' || mode === 'forecast') && layers.has('hotspots')) blocks.push(
    <div key="h"><b>{t.legendHot}</b><div className="sw">{FRP_BINS.map((b) => <span key={b.label}><i className="dot" style={{ background: b.color, boxShadow: `0 0 8px ${b.color}` }} />{b.label}</span>)}</div>
      <div className="sw"><span><i className="dot small" />VIIRS 375 m</span><span><i className="dot big" />MODIS 1 km</span></div></div>)
  if (mode === 'forecast' && layers.has('risk')) blocks.push(
    <div key="r"><b>{t.legendRisk}{weekly ? ` · ${t.week}` : ` · ${t.tomorrow}`}</b>
      <div className="sw">{(weekly ? WEEKLY_BINS : DAILY_BINS).map((b) => <span key={b.label}><i style={{ background: b.color }} />{b.label}</span>)}</div>
      {!weekly && <div className="sw"><span><i className="outlined" />{t.inAlert}</span></div>}</div>)
  if (mode === 'now' && layers.has('regions')) blocks.push(
    <div key="g"><b>{t.legendRegions}</b><div className="sw">{RATIO_BINS.map((b) => <span key={b.label}><i style={{ background: b.color }} />{b.label}</span>)}</div></div>)
  if (mode !== 'now' && layers.has('regimes')) blocks.push(
    <div key="m"><b>{t.legendRegimes}</b><div className="sw">{t.regimes.map((n, i) => <span key={n}><i style={{ background: REGIME_HEX[i] }} />{n}</span>)}</div></div>)
  if (mode !== 'history' && layers.has('rings') && rings) blocks.push(
    <div key="k"><b>{t.legendRings}</b><div className="sw col">{rings.rings.map((r) => <span key={r.km}><i style={{ background: `rgba(255,140,40,${r.km === 5 ? 0.6 : r.km === 10 ? 0.35 : 0.18})` }} />{t.ringsShare(r.km, r.share)}</span>)}</div></div>)
  if (layers.has('towns') && mode !== 'history') blocks.push(
    <div key="tw"><b>{t.L_towns}</b><div className="sw">{[3, 2, 1].map((l) => <span key={l}><Home size={13} fill={LEVEL_HEX[l]} color={LEVEL_HEX[l]} />{l === 3 ? '< 5 km' : l === 2 ? '< 10 km' : '< 25 km'}</span>)}<span><Wind size={13} />{t.fewer === 'menos' ? 'viento hacia el poblado' : 'wind towards town'}</span></div></div>)
  const [open, setOpen] = useState(() => store.get('t1.legend') === 'open')
  useEffect(() => { store.set('t1.legend', open ? 'open' : 'shut') }, [open])
  if (!blocks.length && !shown && !filterLabel) return null
  return (
    <div className={`legend glass ${open ? '' : 'shut'}`}>
      <button className="legend-head" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {shown ? <span className="shown">{shown}</span> : null}
        {filterLabel && <span className="filter-pill" onClick={(e) => { e.stopPropagation(); onClearFilters() }} title={lang === 'es' ? 'Quitar filtros' : 'Clear filters'}><SlidersHorizontal size={11} />{filterLabel}<X size={11} /></span>}
        <span className="legend-toggle">{lang === 'es' ? 'Leyenda' : 'Legend'}<ChevronDown size={13} style={{ transform: open ? 'rotate(180deg)' : '' }} /></span>
      </button>
      {open && blocks}
    </div>
  )
}

// ------------------------------------------------------------------ pick card
function PickCard({ pick, lang, hot, day, onClose, onHistory }: {
  pick: Pick; lang: Lang; hot: Hotspots | null; day: string | null; mode: Mode; onClose: () => void; onHistory: (region: string) => void
}) {
  const t = DICT[lang]
  const [detail, setDetail] = useState<CellDetail | null>(null)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    setDetail(null)
    if (pick.kind === 'cell' && day) api.cell(day, pick.lat, pick.lon).then(setDetail).catch(() => {})
  }, [pick, day])
  const x = Math.min(pick.x + 16, window.innerWidth - 340), y = Math.min(pick.y - 20, window.innerHeight - 380)
  let body: React.ReactNode = null
  if (pick.kind === 'hotspot' && hot) {
    const i = pick.i
    body = (
      <>
        <span className="eyebrow"><Flame size={12} /> {t.hotspot} · {isModis(hot.sat[i]) ? 'MODIS' : 'VIIRS'}</span>
        <div className="big">{nf(lang, 1).format(hot.frp[i])} <small>MW</small></div>
        <dl>
          <dt>{t.localTime}</dt><dd>{shortDate(addDays(hot.from, hot.day[i]), lang)} · {hot.time[i]} ({hot.night[i] ? t.night : t.day})</dd>
          <dt>{t.sat}</dt><dd>{SATS[hot.sat[i]]}</dd>
          <dt>{t.confidence}</dt><dd>{t.conf[hot.conf[i]]}</dd>
          <dt>Lat, lon</dt><dd>{hot.lat[i].toFixed(4)}, {hot.lon[i].toFixed(4)}</dd>
          {hot.region[i] && <><dt>{t.region}</dt><dd>{shortRegion(hot.region[i]!)}</dd></>}
        </dl>
      </>
    )
  } else if (pick.kind === 'cell') {
    body = detail ? (
      <>
        <span className="eyebrow"><Radar size={12} /> {shortDate(detail.date, lang)} · {detail.alert ? <b className="alert-tag">{t.inAlert}</b> : t.notAlert}</span>
        <div className="big">{Math.round(detail.probability * 100)}% <small>{t.probTomorrow}</small></div>
        <div className="meter"><i style={{ width: `${Math.min(100, detail.probability * 200)}%` }} /><em style={{ left: `${Math.min(100, detail.baseline_probability * 200)}%` }} /></div>
        <p className="muted">{t.histRate}: {Math.round(detail.baseline_probability * 100)}%</p>
        {detail.reasons.length > 0 && <><h3>{t.why}</h3><ol className="reasons">{detail.reasons.map((r) => <li key={r.text}><span>{r.text}</span><i style={{ width: `${r.share * 100}%` }} /></li>)}</ol></>}
        {detail.wind && <p className="wind"><Wind size={14} style={{ transform: `rotate(${detail.wind.downwind_deg - 90}deg)` }} /> {Math.round(detail.wind.wind_max_kmh)} km/h · {Math.round(detail.wind.rh_min_pct)}% HR · {Math.round(detail.wind.tmax_c)} °C</p>}
        <p className="foot">{t.notForecast}</p>
      </>
    ) : <p className="muted">{t.loading}</p>
  } else if (pick.kind === 'density') {
    body = (
      <>
        <span className="eyebrow"><BoxIcon size={12} /> {pick.lat.toFixed(2)}°, {pick.lon.toFixed(2)}° · 0,25°</span>
        <div className="big">{compact(lang).format(pick.value)} <small>{t.detections}</small></div>
        <p className="muted">{t.harmonized} (VIIRS eq.)</p>
      </>
    )
  }
  return (
    <div ref={ref} className="pick glass" style={{ left: x, top: Math.max(80, y) }} role="dialog">
      <button className="close" onClick={onClose} aria-label={t.close}><X size={15} /></button>
      {body}
      {pick.kind === 'hotspot' && hot?.region[pick.i] ? <button className="chip accent" onClick={() => onHistory(hot.region[pick.i]!)}><CalendarDays size={14} />{t.viewRegion}: {shortRegion(hot.region[pick.i]!)}</button> : null}
    </div>
  )
}

// ------------------------------------------------------------------ onboarding
function Onboarding({ lang, onPick, setLang }: { lang: Lang; onPick: (id: PersonaId) => void; setLang: (l: Lang) => void }) {
  const t = DICT[lang]
  return (
    <div className="onboard">
      <div className="onboard-box glass">
        <div className="lang inline">{(['es', 'en'] as Lang[]).map((l) => <button key={l} className={l === lang ? 'on' : ''} onClick={() => setLang(l)}>{l.toUpperCase()}</button>)}</div>
        <div className="onboard-logo"><BrasaLogo size={64} /></div>
        <span className="eyebrow center">NASA Space Apps Challenge 2026 · Antofagasta</span>
        <h1>{t.who}</h1>
        <p>{t.whoSub}</p>
        <div className="persona-grid">
          {PERSONAS.map((p) => {
            const I = PERSONA_ICON[p.icon]
            return (
              <button key={p.id} className="persona-card" style={{ '--pc': p.color } as React.CSSProperties} onClick={() => onPick(p.id)}>
                <span className="pi"><I size={26} /></span>
                <b>{p.name[lang]}</b>
                <span className="pitch">{p.pitch[lang]}</span>
                <ul>{p.bullets[lang].map((b) => <li key={b}>{b}</li>)}</ul>
              </button>
            )
          })}
        </div>
        <p className="sources">{t.sources}</p>
      </div>
    </div>
  )
}

// Small flags, drawn inline (emoji flags do not render on every system).
function FlagCL() {
  return (
    <svg className="flag-svg" viewBox="0 0 30 20" aria-hidden="true">
      <rect width="30" height="20" fill="#fff" /><rect y="10" width="30" height="10" fill="#d52b1e" /><rect width="10" height="10" fill="#0039a6" />
      <path d="M5 2.4l.9 2.7h2.8l-2.3 1.7.9 2.7L5 7.8 2.7 9.5l.9-2.7-2.3-1.7h2.8z" fill="#fff" />
    </svg>
  )
}
function FlagAR() {
  return (
    <svg className="flag-svg" viewBox="0 0 30 20" aria-hidden="true">
      <rect width="30" height="20" fill="#74acdf" /><rect y="6.67" width="30" height="6.67" fill="#fff" /><circle cx="15" cy="10" r="2.1" fill="#f6b40e" stroke="#85340a" strokeWidth=".4" />
    </svg>
  )
}
