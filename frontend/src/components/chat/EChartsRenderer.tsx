'use client'

import React, { useEffect, useRef } from 'react'
import ReactECharts from 'echarts-for-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertCircle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface EChartsRendererProps {
  /** ECharts 配置选项 */
  echartsOption: Record<string, any> | null
  /** 图表标题（可选） */
  title?: string
  /** 图表高度（默认 400px） */
  height?: number | string
  /** 是否显示加载状态 */
  loading?: boolean
  /** 自定义样式类名 */
  className?: string
}

/**
 * ECharts 图表渲染组件
 * 使用 echarts-for-react 渲染交互式图表
 */
export function EChartsRenderer({
  echartsOption,
  title,
  height = 400,
  loading = false,
  className = '',
}: EChartsRendererProps) {
  const chartRef = useRef<ReactECharts>(null)

  // 如果没有配置，不渲染
  if (!echartsOption) {
    return null
  }

  // 验证配置有效性
  if (typeof echartsOption !== 'object' || Array.isArray(echartsOption)) {
    return (
      <Alert variant="destructive" className="mt-3">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          图表配置格式无效，无法渲染图表
        </AlertDescription>
      </Alert>
    )
  }

  // 确保配置有基本的图表结构
  const validatedOption = {
    ...echartsOption,
    // 如果没有 title，使用传入的 title 或默认值
    title: echartsOption.title || (title ? { text: title } : { text: '数据可视化' }),
    // 确保 tooltip 存在
    tooltip: echartsOption.tooltip || { trigger: 'axis' },
  }

  return (
    <Card className={`mt-3 border-blue-100 bg-blue-50/40 ${className}`}>
      {title && (
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold text-blue-900">
            {title}
          </CardTitle>
        </CardHeader>
      )}
      <CardContent className="pt-0">
        <div className="rounded-md overflow-hidden bg-white border border-blue-100">
          <ReactECharts
            ref={chartRef}
            option={validatedOption}
            style={{ height: typeof height === 'number' ? `${height}px` : height, width: '100%' }}
            loading={loading}
            opts={{ renderer: 'canvas' }}
            notMerge={false}
            lazyUpdate={false}
          />
        </div>
      </CardContent>
    </Card>
  )
}

