import { CalendarDays, ChevronLeft, ChevronRight, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { Lang } from './i18n.ts'
import { MONTHS, shortDate } from './i18n.ts'

const WEEK = { es: ['L', 'M', 'M', 'J', 'V', 'S', 'D'], en: ['M', 'T', 'W', 'T', 'F', 'S', 'S'] }
const pad = (n: number) => String(n).padStart(2, '0')
// Day of the week of a calendar date, Monday = 0, computed in UTC so the time zone never shifts it.
const weekday = (y: number, m: number, d: number) => (new Date(Date.UTC(y, m - 1, d)).getUTCDay() + 6) % 7
const daysIn = (y: number, m: number) => new Date(Date.UTC(y, m, 0)).getUTCDate()

/** A glass calendar that only lets the user pick the days that have data. */
export function DayPicker({ lang, days, value, onPick, label }: {
  lang: Lang; days: string[]; value: string | null; onPick: (d: string) => void; label: string
}) {
  const [open, setOpen] = useState(false)
  const set = useMemo(() => new Set(days), [days])
  const sorted = useMemo(() => [...days].sort(), [days])
  const first = sorted[0] ?? '2023-01-01', last = sorted.at(-1) ?? '2026-12-31'
  const start = value ?? last
  const [ym, setYm] = useState<[number, number]>([Number(start.slice(0, 4)), Number(start.slice(5, 7))])
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false) }
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('mousedown', close)
    window.addEventListener('keydown', esc)
    return () => { window.removeEventListener('mousedown', close); window.removeEventListener('keydown', esc) }
  }, [open])

  const [y, m] = ym
  const canPrev = `${y}-${pad(m)}` > first.slice(0, 7)
  const canNext = `${y}-${pad(m)}` < last.slice(0, 7)
  const move = (d: number) => setYm(([yy, mm]) => (mm + d < 1 ? [yy - 1, 12] : mm + d > 12 ? [yy + 1, 1] : [yy, mm + d]))
  const years = [...new Set(sorted.map((d) => Number(d.slice(0, 4))))]
  const cells: (number | null)[] = [...Array(weekday(y, m, 1)).fill(null), ...Array.from({ length: daysIn(y, m) }, (_, i) => i + 1)]
  const inMonth = sorted.filter((d) => d.startsWith(`${y}-${pad(m)}`)).length

  return (
    <div className="daypick" ref={box}>
      <button className={`daypick-btn ${value ? 'on' : ''}`} onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <CalendarDays size={15} />
        <span><small>{label}</small><b>{value ? `${shortDate(value, lang)} ${value.slice(0, 4)}` : (lang === 'es' ? 'Elegir fecha' : 'Pick a date')}</b></span>
      </button>
      {open && (
        <div className="daypick-pop glass" role="dialog">
          <div className="dp-head">
            <button disabled={!canPrev} onClick={() => move(-1)} aria-label="prev"><ChevronLeft size={16} /></button>
            <b>{MONTHS[lang][m - 1]} {y}</b>
            <button disabled={!canNext} onClick={() => move(1)} aria-label="next"><ChevronRight size={16} /></button>
            <button className="dp-x" onClick={() => setOpen(false)} aria-label="close"><X size={14} /></button>
          </div>
          <div className="dp-years">
            {years.map((yy) => <button key={yy} className={yy === y ? 'on' : ''} onClick={() => setYm([yy, yy === y ? m : Number((sorted.find((d) => d.startsWith(String(yy))) ?? `${yy}-01`).slice(5, 7))])}>{yy}</button>)}
          </div>
          <div className="dp-grid">
            {WEEK[lang].map((d, i) => <span key={i} className="dp-wd">{d}</span>)}
            {cells.map((d, i) => {
              if (d === null) return <span key={i} />
              const iso = `${y}-${pad(m)}-${pad(d)}`
              const ok = set.has(iso)
              return (
                <button key={i} disabled={!ok} className={`dp-day ${iso === value ? 'sel' : ''} ${ok ? 'ok' : ''}`}
                  onClick={() => { onPick(iso); setOpen(false) }}>{d}</button>
              )
            })}
          </div>
          <p className="dp-foot">{inMonth} {lang === 'es' ? 'días con pronóstico este mes' : 'days with an outlook this month'}</p>
        </div>
      )}
    </div>
  )
}
