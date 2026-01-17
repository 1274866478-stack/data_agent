'use client'

import React, { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import { EChartsOption } from 'echarts'

interface DynamicChartProps {
  config: string | object  // JSON string or object
  title?: string
  chartType?: string
  className?: string
}

export function DynamicChart({ config, title, chartType, className }: DynamicChartProps) {
  const option: EChartsOption = useMemo(() => {
    try {
      const parsed = typeof config === 'string' ? JSON.parse(config) : config
      return {
        ...parsed,
        title: { text: title || parsed.title?.text, ...parsed.title },
      }
    } catch {
      return { title: { text: 'Invalid chart config' } }
    }
  }, [config, title])

  return (
    <ReactECharts
      option={option}
      style={{ height: '400px', width: '100%' }}
      className={className}
      notMerge={true}
      lazyUpdate={true}
    />
  )
}
