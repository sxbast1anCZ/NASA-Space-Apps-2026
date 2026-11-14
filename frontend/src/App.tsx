import type { EChartsOption } from 'echarts'
import { useEffect, useMemo, useState } from 'react'
import type { Box, Calendar, Meta, Month, Search } from './api.ts'
import { errorText, getCalendar, getMeta, saveFile, searchParams } from './api.ts'
import { Chart } from './Chart.tsx'
import { MapPicker } from './MapPicker.tsx'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
// Colour-blind safe ramps: viridis for counts, blue-white-red for the ratio to the median.
const VIRIDIS = ['#440154', '#46327e', '#365c8d', '#277f8e', '#1fa187', '#4ac16d', '#a0da39', '#fde725']
const RATIO_BINS = [
  { lt: 0.5, label: 'under half the median', color: '#2166ac' },
  { gte: 0.5, lt: 0.8, label: '0.5 to 0.8 times', color: '#92c5de' },
  { gte: 0.8, lt: 1.25, label: 'near the median', color: '#f0f0f0' },
  { gte: 1.25, lt: 2, label: '1.25 to 2 times', color: '#f4a582' },
  { gte: 2, label: 'over twice the median', color: '#b2182b' },
]
const VIIRS_COLOR = '#D55E00'
const MODIS_COLOR = '#E8B48A'

const compact = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 })
const full = new Intl.NumberFormat('en', { maximumFractionDigits: 0 })
const yearOf = (isoDate: string) => Number(isoDate.slice(0, 4))
const ordinal = (n: number) => `${n}${['th', 'st', 'nd', 'rd'][n % 100 > 10 && n % 100 < 14 ? 0 : Math.min(n % 10, 4) % 4]}`
const toolbox = { feature: { saveAsImage: { title: 'Save as image', pixelRatio: 2 } } }

function ratioOf(m: Month, median: (number | null)[]) {
  const med = median[m.month - 1]
  return med ? m.hotspots / med : null
}

function notes(m: Month) {
  return [
    m.estimated && 'estimated from MODIS',
    m.provisional && 'provisional data',
    m.partial && 'month not finished',
  ].filter(Boolean)
}

function calendarOption(data: Calendar, view: 'count' | 'ratio'): EChartsOption {
  const years = [...new Set(data.months.map((m) => m.year))].sort((a, b) => b - a)
  const max = Math.max(1, ...data.months.map((m) => m.hotspots))
  const cells = data.months.map((m) => {
    const ratio = ratioOf(m, data.median_by_month)
    // Counts are coloured on a square-root scale so that ordinary months are not all dark.
    const shade = view === 'count' ? Math.sqrt(m.hotspots) : (ratio ?? '-')
    return { value: [m.month - 1, years.indexOf(m.year), shade], month: m, ratio }
  })
  return {
    aria: { enabled: true },
    toolbox,
    grid: { left: 48, right: 12, top: 30, bottom: 78 },
    xAxis: { type: 'category', data: MONTHS, position: 'top', splitArea: { show: true } },
    yAxis: { type: 'category', data: years.map(String), inverse: true },
    tooltip: {
      formatter: (p) => {
        const { month: m, ratio } = (p as unknown as { data: (typeof cells)[number] }).data
        const med = data.median_by_month[m.month - 1]
        return [
          `<b>${MONTHS[m.month - 1]} ${m.year}</b>: ${full.format(m.hotspots)} hotspots`,
          med === null ? '' : `Median for ${MONTHS[m.month - 1]}: ${full.format(med)}`,
          ratio === null ? '' : `${ratio.toFixed(2)} times the median`,
          ...notes(m),
        ].filter(Boolean).join('<br>')
      },
    },
    visualMap:
      view === 'count'
        ? {
            type: 'continuous', min: 0, max: Math.sqrt(max), dimension: 2, orient: 'horizontal',
            left: 'center', bottom: 8, inRange: { color: VIRIDIS }, text: [compact.format(max), '0'],
            calculable: false, formatter: (v) => compact.format(Number(v) ** 2),
          }
        : { type: 'piecewise', pieces: RATIO_BINS, dimension: 2, orient: 'horizontal', left: 'center', bottom: 8 },
    series: [{
      type: 'heatmap',
      data: cells,
      label: {
        show: true, fontSize: 10, color: '#111', textBorderColor: '#fff', textBorderWidth: 2,
        formatter: (p) => {
          const { month: m, ratio } = (p as unknown as { data: (typeof cells)[number] }).data
          const text = view === 'count' ? compact.format(m.hotspots) : ratio === null ? '–' : `${ratio.toFixed(1)}×`
          return m.partial ? `${text}*` : text
        },
      },
      itemStyle: { borderColor: '#fff', borderWidth: 1 },
    }],
  }
}

function yearsOption(data: Calendar): EChartsOption {
  const complete = data.years.filter((y) => !y.partial).map((y) => y.hotspots).sort((a, b) => a - b)
  const median = complete.length ? complete[Math.floor((complete.length - 1) / 2)] : null
  const viirsYear = yearOf('2012-02-01')
  return {
    aria: { enabled: true },
    toolbox,
    grid: { left: 56, right: 16, top: 30, bottom: 30 },
    tooltip: {
      trigger: 'axis',
      formatter: (ps) => {
        const y = data.years[(ps as unknown as { dataIndex: number }[])[0].dataIndex]
        return `<b>${y.year}</b>: ${full.format(y.hotspots)} hotspots` +
          (y.year < viirsYear ? '<br>estimated from MODIS' : '') + (y.partial ? '<br>year not complete' : '')
      },
    },
    xAxis: { type: 'category', data: data.years.map((y) => String(y.year)) },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => compact.format(v) } },
    series: [{
      type: 'bar',
      data: data.years.map((y) => ({
        value: y.hotspots,
        itemStyle: { color: y.year < viirsYear ? MODIS_COLOR : VIIRS_COLOR, opacity: y.partial ? 0.45 : 1 },
      })),
      markLine: median === null ? undefined : {
        symbol: 'none', lineStyle: { color: '#333', type: 'dashed' },
        label: { formatter: `median ${compact.format(median)}`, position: 'insideEndTop' },
        data: [{ yAxis: median }],
      },
    }],
  }
}

function seasonOption(data: Calendar): EChartsOption {
  return {
    aria: { enabled: true },
    toolbox,
    grid: { left: 56, right: 16, top: 30, bottom: 30 },
    tooltip: { trigger: 'axis', valueFormatter: (v) => `${full.format(Number(v))} hotspots` },
    xAxis: { type: 'category', data: MONTHS },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => compact.format(v) } },
    series: [{ type: 'bar', data: data.median_by_month.map((v) => v ?? 0), itemStyle: { color: '#277f8e' } }],
  }
}

function calendarCsv(data: Calendar) {
  const head = 'year,month,hotspots_harmonized,hotspots_raw,estimated_from_modis,provisional,partial,median_for_month,ratio_to_median'
  const rows = data.months.map((m) => {
    const ratio = ratioOf(m, data.median_by_month)
    return [m.year, m.month, m.hotspots, m.raw, m.estimated, m.provisional, m.partial,
      data.median_by_month[m.month - 1] ?? '', ratio === null ? '' : ratio.toFixed(3)].join(',')
  })
  return new Blob([[head, ...rows].join('\n') + '\n'], { type: 'text/csv' })
}

function KeyFigures({ data }: { data: Calendar }) {
  const c = data.current
  const days = c.days >= 28 && !data.months.at(-1)?.partial ? '' : `1–${c.days} `
  const byMonth = MONTHS.map((_, i) =>
    data.months.filter((m) => m.month === i + 1 && !m.partial).reduce((sum, m) => sum + m.hotspots, 0))
  const peak = byMonth.indexOf(Math.max(...byMonth))
  const top = data.years.filter((y) => !y.partial).sort((a, b) => b.hotspots - a.hotspots)[0]
  return (
    <div className="figures">
      <div>
        <h3>{days}{MONTHS[c.month - 1]} {c.year}</h3>
        <p className="big">{full.format(c.hotspots)} hotspots</p>
        <p>
          {c.median === null ? 'No earlier years to compare with.'
            : c.ratio === null ? `The median of the same days in ${c.years_compared} earlier years is 0.`
            : `${c.ratio.toFixed(1)} times the median of the same days in ${c.years_compared} earlier years (${full.format(c.median)}).`}
          {c.rank !== null && ` ${ordinal(c.rank)} highest of ${c.years_compared + 1}.`}
        </p>
      </div>
      <div>
        <h3>Month with most fire</h3>
        <p className="big">{byMonth[peak] ? MONTHS[peak] : '–'}</p>
        <p>By total hotspots over the selected years.</p>
      </div>
      <div>
        <h3>Year with most fire</h3>
        <p className="big">{top?.hotspots ? top.year : '–'}</p>
        <p>{top?.hotspots ? `${full.format(top.hotspots)} hotspots. Complete years only.` : 'No complete year in the selection.'}</p>
      </div>
    </div>
  )
}

const EMPTY_BOX = { north: '', south: '', west: '', east: '' }

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null)
  const [search, setSearch] = useState<Search | null>(null)
  const [data, setData] = useState<Calendar | null>(null)
  const [error, setError] = useState('')
  const [view, setView] = useState<'count' | 'ratio'>('count')
  const [drawing, setDrawing] = useState(false)
  const [coords, setCoords] = useState(EMPTY_BOX)
  const [coordError, setCoordError] = useState('')
  const [download, setDownload] = useState('')

  useEffect(() => {
    getMeta()
      .then((m) => {
        setMeta(m)
        setSearch({ box: null, country: '', admin1: '', fromYear: yearOf(m.first_date), toYear: yearOf(m.data_through) })
      })
      .catch((e: Error) => setError(e.message))
  }, [])

  useEffect(() => {
    if (!search) return
    let stale = false
    getCalendar(search)
      .then((d) => {
        if (stale) return
        setData(d)
        setError('')
      })
      .catch((e: Error) => !stale && setError(e.message))
    return () => {
      stale = true
    }
  }, [search])

  const calendar = useMemo(() => data && calendarOption(data, view), [data, view])
  const years = useMemo(() => data && yearsOption(data), [data])
  const season = useMemo(() => data && seasonOption(data), [data])

  if (!meta || !search) return <main className="loading">{error || 'Loading…'}</main>

  const setBox = (box: Box | null) => {
    setDrawing(false)
    setCoordError('')
    setCoords(box ? { north: String(box.north), south: String(box.south), west: String(box.west), east: String(box.east) } : EMPTY_BOX)
    setSearch({ ...search, box, country: '', admin1: '' })
  }
  const applyCoords = () => {
    const [north, south, west, east] = [coords.north, coords.south, coords.west, coords.east].map(Number)
    const filled = Object.values(coords).every((v) => v.trim() !== '')
    if (!filled || [north, south, west, east].some(Number.isNaN)) return setCoordError('Fill in the four limits with numbers.')
    if (south >= north || west >= east) return setCoordError('South must be below north, and west must be left of east.')
    if (Math.abs(north) > 90 || Math.abs(south) > 90 || Math.abs(west) > 180 || Math.abs(east) > 180)
      return setCoordError('Latitude goes from -90 to 90 and longitude from -180 to 180.')
    setBox({ north, south, west, east })
  }
  const setRegion = (country: string, admin1: string) => {
    setCoords(EMPTY_BOX)
    setSearch({ ...search, box: null, country, admin1 })
  }
  const downloadHotspots = async () => {
    setDownload('Preparing the file…')
    try {
      const r = await fetch(`/api/hotspots.csv?${searchParams(search)}`)
      if (!r.ok) return setDownload(await errorText(r))
      saveFile('hotspots.csv', await r.blob())
      setDownload(`${full.format(Number(r.headers.get('x-hotspot-count')))} hotspots downloaded.`)
    } catch {
      setDownload('The download failed. Check that the API is running.')
    }
  }

  const allYears = Array.from({ length: yearOf(meta.data_through) - yearOf(meta.first_date) + 1 }, (_, i) => yearOf(meta.first_date) + i)
  const countries = [...new Set(meta.regions.map((r) => r.country))]
  const used = data?.bounds ? { west: data.bounds[0], south: data.bounds[1], east: data.bounds[2], north: data.bounds[3] } : null
  const areaName = search.box ? 'the drawn area' : search.admin1 || search.country || 'Chile and Argentina'

  return (
    <div className="layout">
      <header>
        <h1>Harmonized burn calendar</h1>
        <p>
          Fire hotspots in Chile and Argentina since {yearOf(meta.first_date)}, with MODIS and VIIRS on one scale.
          Data through {meta.data_through}.
        </p>
      </header>

      <aside>
        <section>
          <h2>Area</h2>
          <button type="button" className={drawing ? 'active' : ''} aria-pressed={drawing} onClick={() => setDrawing(!drawing)}>
            {drawing ? 'Drag on the map…' : 'Draw a rectangle on the map'}
          </button>
          <fieldset>
            <legend>Or type the limits (degrees)</legend>
            {(['north', 'south', 'west', 'east'] as const).map((k) => (
              <label key={k}>
                {k}
                <input inputMode="decimal" value={coords[k]} onChange={(e) => setCoords({ ...coords, [k]: e.target.value })} />
              </label>
            ))}
            <button type="button" onClick={applyCoords}>Apply</button>
            {coordError && <p role="alert" className="error">{coordError}</p>}
          </fieldset>
          <label>
            Or choose a country
            <select value={search.country} onChange={(e) => setRegion(e.target.value, '')}>
              <option value="">Chile and Argentina</option>
              {countries.map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          <label>
            Region or province
            <select value={search.admin1} disabled={!search.country} onChange={(e) => setRegion(search.country, e.target.value)}>
              <option value="">All</option>
              {meta.regions.filter((r) => r.country === search.country).map((r) => <option key={r.admin1}>{r.admin1}</option>)}
            </select>
          </label>
          {search.box && <button type="button" onClick={() => setBox(null)}>Clear the area</button>}
        </section>

        <section>
          <h2>Period</h2>
          <div className="row">
            <label>
              From
              <select value={search.fromYear} onChange={(e) => setSearch({ ...search, fromYear: Number(e.target.value), toYear: Math.max(search.toYear, Number(e.target.value)) })}>
                {allYears.map((y) => <option key={y}>{y}</option>)}
              </select>
            </label>
            <label>
              To
              <select value={search.toYear} onChange={(e) => setSearch({ ...search, toYear: Number(e.target.value), fromYear: Math.min(search.fromYear, Number(e.target.value)) })}>
                {allYears.map((y) => <option key={y}>{y}</option>)}
              </select>
            </label>
          </div>
        </section>

        <section>
          <h2>Download</h2>
          <button type="button" disabled={!data} onClick={() => data && saveFile('burn-calendar.csv', calendarCsv(data))}>
            Calendar table (CSV)
          </button>
          <button type="button" onClick={downloadHotspots}>Hotspots of this search (CSV)</button>
          {download && <p role="status">{download}</p>}
          <p className="hint">Each chart has a button to save it as an image.</p>
        </section>
      </aside>

      <main>
        <MapPicker box={search.box} used={used} drawing={drawing} onDraw={setBox} />
        {error && <p role="alert" className="error">{error}</p>}
        {data && calendar && years && season && (
          data.cells === 0 ? (
            <p className="empty">
              No hotspot was ever detected in this area. No detections does not mean no fire: clouds,
              small fires and the time of the satellite pass can hide one.
            </p>
          ) : (
            <>
              <p className="hint">
                Showing {areaName}: {full.format(data.cells)} cells of {meta.cell_degrees}° (dashed outline on the map).
              </p>
              <KeyFigures data={data} />

              <section>
                <div className="title">
                  <h2>Burn calendar</h2>
                  <div role="group" aria-label="What the colours show">
                    <button type="button" className={view === 'count' ? 'active' : ''} aria-pressed={view === 'count'} onClick={() => setView('count')}>Hotspots</button>
                    <button type="button" className={view === 'ratio' ? 'active' : ''} aria-pressed={view === 'ratio'} onClick={() => setView('ratio')}>Compared with the median</button>
                  </div>
                </div>
                <Chart option={calendar} height={data.years.length * 22 + 120} label={`Hotspots per month and year in ${areaName}`} />
                <p className="hint">
                  Hotspots in VIIRS-equivalent units, by calendar year. Days run from 06:00 to 06:00 local solar time.
                  Before {MONTHS[1]} 2012 the counts are MODIS detections scaled to the VIIRS level: estimates, within
                  about 14% (Argentina) and 24% (Chile) for a region and month. * marks a month that is not finished.
                </p>
              </section>

              <div className="pair">
                <section>
                  <h2>Hotspots per year</h2>
                  <Chart option={years} height={260} label={`Hotspots per year in ${areaName}`} />
                  <p className="hint">Light bars: estimated from MODIS. Faded bars: year not complete.</p>
                </section>
                <section>
                  <h2>A typical year</h2>
                  <Chart option={season} height={260} label={`Median hotspots per calendar month in ${areaName}`} />
                  <p className="hint">Median of each calendar month over the selected years.</p>
                </section>
              </div>
            </>
          )
        )}
      </main>

      <footer>
        Data: NASA FIRMS (MODIS Collection 6.1, VIIRS 375 m). A hotspot is a thermal detection in a pixel, not a
        fire: one fire can produce many. Low-confidence detections and static heat sources are left out. Map © OpenStreetMap contributors.
      </footer>
    </div>
  )
}
