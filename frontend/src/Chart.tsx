import * as echarts from 'echarts'
import { useEffect, useRef } from 'react'

/** An ECharts chart that follows its container size. `label` is what a screen reader announces. */
export function Chart({ option, height, label }: { option: echarts.EChartsOption; height: number; label: string }) {
  const el = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    const c = echarts.init(el.current!)
    chart.current = c
    const observer = new ResizeObserver(() => c.resize())
    observer.observe(el.current!)
    return () => {
      observer.disconnect()
      c.dispose()
    }
  }, [])

  useEffect(() => {
    chart.current?.setOption(option, true)
  }, [option])

  return <div ref={el} style={{ height }} role="img" aria-label={label} />
}
