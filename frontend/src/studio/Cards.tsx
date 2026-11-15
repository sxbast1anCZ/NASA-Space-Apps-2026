import type { EChartsOption } from 'echarts'
import { ArrowDownRight, ArrowUpRight, CalendarRange, Copy, Download, FileJson, Minus, Satellite } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Chart } from '../Chart.tsx'
import { INFERNO, RATIO_BINS, ratioHex } from './colors.ts'
import type { Area, Calendar, Daily, DayCount, Hotspots, RegionRow, SeriesYear } from './data.ts'
import { SATS, addDays, api } from './data.ts'
import type { Lang, T } from './i18n.ts'
import { MONTHS, compact, nf, shortDate, shortRegion } from './i18n.ts'

// Chart colours follow the light or dark theme of the page.
const light = () => document.documentElement.dataset.theme === 'light'
const ink2 = (): string => (light() ? '#273449' : '#c9d1e0')
const ink3 = (): string => (light() ? '#5b6577' : '#aab3c5')
const bgc = () => (light() ? '#ffffff' : '#0d1220')
const fg = (a: number) => (light() ? `rgba(15,23,42,${a})` : `rgba(255,255,255,${a})`)
const axis = () => ({ axisLine: { lineStyle: { color: fg(0.18) } }, axisLabel: { color: ink3(), fontSize: 10 }, splitLine: { lineStyle: { color: fg(0.06) } } })
const tip = () => ({ backgroundColor: light() ? 'rgba(255,255,255,.95)' : 'rgba(14,18,28,.92)', borderColor: fg(0.12), textStyle: { color: light() ? '#111827' : '#eef2f8', fontSize: 12 } })
const toolbox = () => ({ right: 0, top: -4, iconStyle: { borderColor: ink3() }, feature: { saveAsImage: { title: 'PNG', pixelRatio: 2, backgroundColor: bgc() } } })

function useAsync<V>(f: () => Promise<V> | null, deps: unknown[]): { data: V | null; error: string | null } {
  const [s, set] = useState<{ data: V | null; error: string | null }>({ data: null, error: null })
  useEffect(() => {
    let live = true
    const p = f()
    if (!p) { set({ data: null, error: null }); return }
    set((o) => ({ data: o.data, error: null }))
    p.then((data) => live && set({ data, error: null })).catch((e) => live && set({ data: null, error: String(e.message ?? e) }))
    return () => { live = false }
  }, deps)
  return s
}

export type Ctx = {
  lang: Lang; t: T; theme: 'dark' | 'light'; area: Area; through: string; daily: Daily | null; hotspots: Hotspots | null
  dayWindow: [number, number]; regions: RegionRow[] | null; regionCountry: Map<string, string>; keep: ((h: Hotspots, i: number) => boolean) | null; filtered: boolean; onRegion: (c: string, a: string) => void
  onFly: (lon: number, lat: number) => void; historyYear: number
}

function Trend({ ratio, reliable, t }: { ratio: number; reliable: boolean; t: T }) {
  if (!reliable) return <span className="pill grey">{t.fewData}</span>
  if (ratio >= 1.25) return <span className="pill hot"><ArrowUpRight size={13} />{t.aboveNormal}</span>
  if (ratio < 0.8) return <span className="pill cool"><ArrowDownRight size={13} />{t.belowNormal}</span>
  return <span className="pill ok"><Minus size={13} />{t.normal}</span>
}

function inArea(area: Area, lat: number, lon: number, region: string | null | undefined, rc: Map<string, string>) {
  if (area.kind === 'all') return true
  if (area.kind === 'country') return !!region && rc.get(region) === area.country
  if (area.kind === 'region') return region === area.admin1
  return lon >= area.west && lon <= area.east && lat >= area.south && lat <= area.north
}
function cellInArea(area: Area, lat: number, lon: number, bounds?: number[]) {
  if (area.kind === 'all') return true
  if (area.kind === 'country') return false
  const b = area.kind === 'box' ? [area.west, area.south, area.east, area.north] : bounds
  if (!b) return false
  return lon + 0.25 > b[0] && lon < b[2] && lat + 0.25 > b[1] && lat < b[3]
}

/** A number that counts up to its value. */
function Count({ value, lang, digits = 0 }: { value: number; lang: Lang; digits?: number }) {
  const [shown, setShown] = useState(0)
  const from = useRef(0)
  useEffect(() => {
    const start = performance.now(), a = from.current
    let id = 0
    const step = (now: number) => {
      const k = Math.min(1, (now - start) / 700), e = 1 - (1 - k) ** 3
      setShown(a + (value - a) * e)
      if (k < 1) id = requestAnimationFrame(step); else from.current = value
    }
    id = requestAnimationFrame(step)
    return () => cancelAnimationFrame(id)
  }, [value])
  return <>{nf(lang, digits).format(shown)}</>
}

// ------------------------------------------------------------------ summary
export function Summary({ c }: { c: Ctx }) {
  const { t, lang } = c
  const days = useAsync(() => (c.through ? api.days(c.area, addDays(c.through, -29), c.through) : null), [c.area, c.through])
  const cal = useAsync(() => api.calendar(c.area, 'recent'), [c.area])
  const d = days.data?.days ?? []
  const last7 = d.slice(-7).reduce((s, x) => s + x.hotspots, 0)
  const med7 = d.slice(-7).reduce((s, x) => s + x.median, 0)
  const ratio = (last7 + 1) / (med7 + 1)
  const row = c.area.kind === 'region' ? c.regions?.find((r) => r.admin1 === (c.area as { admin1: string }).admin1) : undefined
  const alerts = useMemo(() => {
    if (!c.daily) return null
    if (c.area.kind === 'country' && c.regions) return c.regions.filter((r) => r.country === (c.area as { country: string }).country).reduce((n, r) => n + r.alerts, 0)
    if (c.area.kind === 'region' && row) return row.alerts
    return c.daily.cells.filter((x) => x[4] === 1 && cellInArea(c.area, x[0], x[1], row?.bounds)).length
  }, [c.daily, c.area, row])
  const cur = cal.data?.current
  // With filters on, the first figure counts the filtered raw detections of the last 7 days.
  const filt = useMemo(() => {
    const h = c.hotspots
    if (!c.filtered || !h || !c.keep) return null
    let n = 0
    const from = Math.max(...h.day) - 6
    for (let i = 0; i < h.count; i++) if (h.day[i] >= from && c.keep(h, i)) n++
    return n
  }, [c.filtered, c.hotspots, c.keep])
  return (
    <div className="kpis">
      {filt !== null && (
        <div className="kpi wide filt">
          <span className="kpi-label">{lang === 'es' ? 'Detecciones con el filtro, últimos 7 días (sin armonizar)' : 'Detections with the filter, last 7 days (not harmonized)'}</span>
          <span className="kpi-value"><Count value={filt} lang={lang} /></span>
        </div>
      )}
      <div className="kpi">
        <span className="kpi-label">{t.last7}</span>
        <span className="kpi-value">{days.data ? <Count value={last7} lang={lang} /> : '—'}</span>
        <span className="kpi-sub">{days.data && <>{nf(lang, 1).format(ratio)}{t.timesMedian} · <Trend ratio={ratio} reliable={med7 >= 10} t={t} /></>}</span>
      </div>
      <div className="kpi">
        <span className="kpi-label">{t.alertsTomorrow}</span>
        <span className="kpi-value alert">{alerts === null ? '—' : <Count value={alerts} lang={lang} />}</span>
        <span className="kpi-sub">{c.daily ? shortDate(c.daily.date, lang) : ''}</span>
      </div>
      <div className="kpi wide">
        <span className="kpi-label">{t.thisMonth} · {cur ? `${MONTHS[lang][cur.month - 1]} 1–${cur.days}` : ''}</span>
        <span className="kpi-value">{cur ? <Count value={cur.hotspots} lang={lang} /> : '—'}</span>
        <span className="kpi-sub">{cur?.rank && <>#{cur.rank} {t.rankMonth} {cur.years_compared + 1} {t.years} · <Trend ratio={cur.ratio ?? 1} reliable={cur.reliable} t={t} /></>}</span>
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ top hotspots
export function TopFires({ c }: { c: Ctx }) {
  const { t, lang } = c
  const [copied, setCopied] = useState(-1)
  const top = useMemo(() => {
    const h = c.hotspots
    if (!h) return []
    const out: number[] = []
    for (let i = 0; i < h.count && out.length < 8; i++) { // already sorted by FRP, strongest first
      if (h.day[i] >= c.dayWindow[0] && h.day[i] <= c.dayWindow[1] && (c.keep ? c.keep(h, i) : inArea(c.area, h.lat[i], h.lon[i], h.region[i], c.regionCountry))) out.push(i)
    }
    return out
  }, [c.hotspots, c.dayWindow, c.area, c.regionCountry, c.keep])
  const h = c.hotspots
  if (!h) return <p className="muted">{t.loading}</p>
  if (!top.length) return <p className="muted">{t.noData}</p>
  return (
    <ol className="fires">
      {top.map((i, k) => (
        <li key={i}>
          <button className="fire" onClick={() => c.onFly(h.lon[i], h.lat[i])}>
            <span className="fire-rank">{k + 1}</span>
            <span className="fire-main">
              <b>{nf(lang).format(h.frp[i])} MW</b>
              <small>{h.region[i] ? shortRegion(h.region[i]!) : ''} · {shortDate(addDays(h.from, h.day[i]), lang)} {h.time[i]} · {SATS[h.sat[i]]}</small>
            </span>
          </button>
          <button className="icon-btn" title={t.copy} onClick={() => {
            navigator.clipboard?.writeText(`${h.lat[i].toFixed(4)}, ${h.lon[i].toFixed(4)}`)
            setCopied(i); setTimeout(() => setCopied(-1), 1200)
          }}>{copied === i ? '✓' : <Copy size={14} />}</button>
        </li>
      ))}
    </ol>
  )
}

// ------------------------------------------------------------------ region ranking
export function Ranking({ c }: { c: Ctx }) {
  const { t, lang } = c
  if (!c.regions) return <p className="muted">{t.loading}</p>
  const only = c.area.kind === 'country' || c.area.kind === 'region' ? c.area.country : null
  const rows = [...c.regions].filter((r) => (r.hotspots_7d > 0 || r.alerts > 0) && (!only || r.country === only))
    .sort((a, b) => Number(b.reliable) - Number(a.reliable) || b.ratio - a.ratio).slice(0, 12)
  const max = Math.max(...rows.map((r) => Math.min(r.ratio, 10)), 2)
  return (
    <ul className="ranking">
      {rows.map((r) => (
        <li key={r.country + r.admin1}>
          <button onClick={() => c.onRegion(r.country, r.admin1)}>
            <span className="flag">{r.country === 'Chile' ? 'CL' : 'AR'}</span>
            <span className="rname">{shortRegion(r.admin1)}</span>
            <span className="bar"><i style={{ width: `${(Math.min(r.ratio, 10) / max) * 100}%`, background: ratioHex(r) }} /></span>
            <span className="rval">{r.reliable ? `${nf(lang, 1).format(r.ratio)}×` : '·'}</span>
            <span className="ralert" title={t.alertsTomorrow}>{r.alerts ? `⚠ ${r.alerts}` : ''}</span>
          </button>
        </li>
      ))}
    </ul>
  )
}

// ------------------------------------------------------------------ calendar heatmap
export function BurnCalendar({ c }: { c: Ctx }) {
  const { t, lang } = c
  const [view, setView] = useState<'count' | 'ratio'>('count')
  const cal = useAsync(() => api.calendar(c.area, 'recent'), [c.area])
  const option = useMemo<EChartsOption | null>(() => {
    const d = cal.data
    if (!d) return null
    const years = [...new Set(d.months.map((m) => m.year))].sort((a, b) => b - a)
    const max = Math.max(1, ...d.months.map((m) => m.hotspots))
    return {
      toolbox: toolbox(), tooltip: { ...tip(), formatter: (p: unknown) => {
        const m = (p as { data: { m: Calendar['months'][number] } }).data.m
        return `<b>${MONTHS[lang][m.month - 1]} ${m.year}</b><br>${nf(lang).format(m.hotspots)} ${t.detections}` +
          (m.median !== null ? `<br>${t.median}: ${nf(lang).format(m.median)}` : '') +
          (m.ratio !== null && m.reliable ? `<br>${nf(lang, 2).format(m.ratio)}${t.timesMedian}` : '') +
          (m.estimated ? `<br><i>${t.estimated}</i>` : '') + (m.provisional ? `<br><i>${t.provisional}</i>` : '')
      } },
      grid: { left: 34, right: 4, top: 18, bottom: 34 },
      xAxis: { type: 'category', data: MONTHS[lang].map((m) => m[0]), position: 'top', ...axis(), splitLine: { show: false } },
      yAxis: { type: 'category', data: years.map(String), inverse: true, ...axis(), axisLabel: { ...axis().axisLabel, fontSize: 9, interval: 1 } },
      visualMap: view === 'count'
        ? { type: 'continuous', min: 0, max: Math.sqrt(max), dimension: 2, orient: 'horizontal', left: 'center', bottom: 0, itemHeight: 120, itemWidth: 10,
            inRange: { color: INFERNO }, text: [compact(lang).format(max), '0'], textStyle: { color: ink3(), fontSize: 10 }, calculable: false }
        : { type: 'piecewise', pieces: RATIO_BINS.map((b, i) => ({ gte: b.from, lt: RATIO_BINS[i + 1]?.from, label: b.label, color: b.color })),
            dimension: 2, orient: 'horizontal', left: 'center', bottom: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: ink3(), fontSize: 9 },
            outOfRange: { color: fg(0.05) } },
      series: [{
        type: 'heatmap', itemStyle: { borderColor: bgc(), borderWidth: 1, borderRadius: 2 },
        data: d.months.map((m) => ({ value: [m.month - 1, years.indexOf(m.year), view === 'count' ? Math.sqrt(m.hotspots) : (m.reliable && m.ratio !== null ? m.ratio : -1)], m })),
      }],
    } as EChartsOption
  }, [cal.data, view, lang, c.theme])
  return (
    <>
      <div className="seg small">
        <button className={view === 'count' ? 'on' : ''} onClick={() => setView('count')}>{t.count}</button>
        <button className={view === 'ratio' ? 'on' : ''} onClick={() => setView('ratio')}>{t.anomaly}</button>
      </div>
      {option ? <Chart option={option} height={420} label={t.calendar} /> : <p className="muted">{cal.error ?? t.loading}</p>}
      <p className="foot">{t.estimated}</p>
    </>
  )
}

// ------------------------------------------------------------------ typical year
export function TypicalYear({ c }: { c: Ctx }) {
  const { t, lang } = c
  const cal = useAsync(() => api.calendar(c.area, 'recent'), [c.area])
  const option = useMemo<EChartsOption | null>(() => {
    const d = cal.data
    if (!d) return null
    const year = Number(d.to.slice(0, 4))
    const cur = MONTHS[lang].map((_, i) => d.months.find((m) => m.year === year && m.month === i + 1)?.hotspots ?? null)
    const prev = MONTHS[lang].map((_, i) => d.months.find((m) => m.year === year - 1 && m.month === i + 1)?.hotspots ?? null)
    return {
      toolbox: toolbox(), tooltip: { ...tip(), trigger: 'axis' }, legend: { top: 0, left: 0, textStyle: { color: ink2(), fontSize: 10 }, itemWidth: 12, itemHeight: 8 },
      grid: { left: 40, right: 6, top: 30, bottom: 22 },
      xAxis: { type: 'category', data: MONTHS[lang], ...axis() },
      yAxis: { type: 'value', ...axis(), axisLabel: { ...axis().axisLabel, formatter: (v: number) => compact(lang).format(v) } },
      series: [
        { name: `${t.median} ${d.reference.from_year}–${d.reference.to_year}`, type: 'bar', data: d.median_by_month, itemStyle: { color: 'rgba(160,175,210,.35)', borderRadius: [3, 3, 0, 0] } },
        { name: String(year - 1), type: 'line', data: prev, symbol: 'none', lineStyle: { color: '#7aa7ff', width: 1.5, type: 'dashed' } },
        { name: String(year), type: 'line', data: cur, symbolSize: 6, lineStyle: { color: '#ff7a1a', width: 2.5 }, itemStyle: { color: '#ff7a1a' }, areaStyle: { color: 'rgba(255,122,26,.12)' } },
      ],
    } as EChartsOption
  }, [cal.data, lang, c.theme])
  return option ? <Chart option={option} height={210} label={t.typicalYear} /> : <p className="muted">{t.loading}</p>
}

// ------------------------------------------------------------------ last 30 days
export function Last30({ c }: { c: Ctx }) {
  const { t, lang } = c
  const days = useAsync(() => (c.through ? api.days(c.area, addDays(c.through, -29), c.through) : null), [c.area, c.through])
  const option = useMemo<EChartsOption | null>(() => {
    const d: DayCount[] = days.data?.days ?? []
    if (!d.length) return null
    return {
      toolbox: toolbox(), tooltip: { ...tip(), trigger: 'axis' },
      grid: { left: 40, right: 6, top: 16, bottom: 22 },
      xAxis: { type: 'category', data: d.map((x) => shortDate(x.date, lang)), ...axis(), axisLabel: { ...axis().axisLabel, interval: 6 } },
      yAxis: { type: 'value', ...axis(), axisLabel: { ...axis().axisLabel, formatter: (v: number) => compact(lang).format(v) } },
      series: [
        { name: t.detections, type: 'bar', data: d.map((x) => ({ value: x.hotspots, itemStyle: { color: x.hotspots > x.median * 2 && x.median > 2 ? '#ff4d2e' : '#ff9f1c', borderRadius: [2, 2, 0, 0] } })) },
        { name: t.median, type: 'line', data: d.map((x) => x.median), symbol: 'none', step: 'middle', lineStyle: { color: ink2(), width: 1.5, type: 'dashed' } },
      ],
    } as EChartsOption
  }, [days.data, lang, c.theme])
  return option ? <Chart option={option} height={170} label={t.last30} /> : <p className="muted">{days.error ?? t.loading}</p>
}

// ------------------------------------------------------------------ sensors
export function Sensors({ c }: { c: Ctx }) {
  const { t, lang } = c
  const s = useAsync(() => api.series(c.area), [c.area])
  const option = useMemo<EChartsOption | null>(() => {
    const y: SeriesYear[] = (s.data?.years ?? []).filter((r) => r.year >= 2001)
    if (!y.length) return null
    return {
      toolbox: toolbox(), tooltip: { ...tip(), trigger: 'axis' }, legend: { top: 0, left: 0, textStyle: { color: ink2(), fontSize: 10 }, itemWidth: 12, itemHeight: 8 },
      grid: { left: 44, right: 6, top: 30, bottom: 22 },
      xAxis: { type: 'category', data: y.map((r) => String(r.year)), ...axis() },
      yAxis: { type: 'value', ...axis(), axisLabel: { ...axis().axisLabel, formatter: (v: number) => compact(lang).format(v) } },
      series: [
        { name: t.modisRaw, type: 'line', data: y.map((r) => r.modis_raw || null), symbol: 'none', lineStyle: { color: '#E69F00', width: 1.5 } },
        { name: t.viirsRaw, type: 'line', data: y.map((r) => r.viirs_raw || null), symbol: 'none', lineStyle: { color: '#56B4E9', width: 1.5 } },
        { name: t.harmonized, type: 'line', data: y.map((r) => r.harmonized), symbolSize: 5, lineStyle: { color: '#ff7a1a', width: 3 }, itemStyle: { color: '#ff7a1a' },
          areaStyle: { color: 'rgba(255,122,26,.10)' }, markArea: { silent: true, itemStyle: { color: 'rgba(255,255,255,.04)' }, data: [[{ xAxis: '2001' }, { xAxis: '2011' }]] } },
      ],
    } as EChartsOption
  }, [s.data, lang, c.theme])
  return (
    <>
      {option ? <Chart option={option} height={220} label={t.sensors} /> : <p className="muted">{s.error ?? t.loading}</p>}
      <p className="foot"><Satellite size={12} /> {t.method}</p>
    </>
  )
}

// ------------------------------------------------------------------ downloads
export function Downloads({ c }: { c: Ctx }) {
  const { t } = c
  const [busy, setBusy] = useState(false)
  const from = `${c.historyYear}-01-01`, to = `${c.historyYear}-12-31`
  const recentFrom = addDays(c.through, -13)
  return (
    <div className="downloads">
      <a className="dl" href={api.csvUrl(c.area, recentFrom, c.through)} download><Download size={15} />{t.csv} · 14 d</a>
      <a className="dl" href={api.csvUrl(c.area, from, to)} download><Download size={15} />{t.csv} · {c.historyYear}</a>
      <button className="dl" disabled={busy} onClick={async () => {
        setBusy(true)
        try {
          const d = await api.calendar(c.area, 'recent')
          const a = document.createElement('a')
          a.href = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' }))
          a.download = 'burn-calendar.json'; a.click(); URL.revokeObjectURL(a.href)
        } finally { setBusy(false) }
      }}><FileJson size={15} />{t.json}</button>
      {/* The classic view lets the user choose the years of the calendar and of the CSV. */}
      <a className="dl" href="#classic"><CalendarRange size={15} />{t.byPeriod}</a>
    </div>
  )
}
