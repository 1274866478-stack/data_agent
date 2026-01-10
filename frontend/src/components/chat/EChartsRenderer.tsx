/**
 * # EChartsRenderer ECharts图表渲染器
 *
 * ## [MODULE]
 * **文件名**: EChartsRenderer.tsx
 * **职责**: 封装echarts-for-react库，提供类型安全和默认配置的图表渲染组件
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - **echartsOption**: Record<string, any> | null - ECharts配置对象
 * - **title**: string (可选) - 图表标题
 * - **height**: number | string (可选) - 图表高度，默认400px
 * - **loading**: boolean (可选) - 是否显示加载状态
 * - **className**: string (可选) - 自定义样式类名
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - Card包装的ECharts图表或null或错误提示
 * - **副作用**: 无副作用
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [echarts-for-react](https://github.com/hustcc/echarts-for-react) - ECharts React封装
 * - [@/components/ui/*](../ui/) - UI基础组件（Card, Alert）
 * - [lucide-react](https://lucide.dev) - 图标库
 *
 * **下游依赖**:
 * - 无直接下游组件
 *
 * **调用方**:
 * - [./MessageList.tsx](./MessageList.tsx) - 消息列表中渲染图表
 * - [./ChatQueryResultView.tsx](./ChatQueryResultView.tsx) - 查询结果视图
 *
 * ## [STATE]
 * - **chartRef**: Ref<ReactECharts> - ECharts组件引用
 *
 * ## [SIDE-EFFECTS]
 * - 自动添加默认的title和tooltip配置
 * - 验证配置有效性，无效时显示错误提示
 * - 配置为null时不渲染任何内容
 */
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
  const titleConfig = echartsOption.title || (title ? { text: title } : { text: '数据可视化' })

  // 标题样式配置 - 调整字体大小避免压住图表内容
  const normalizedTitle = typeof titleConfig === 'string'
    ? {
        text: titleConfig,
        textStyle: { fontSize: 14, fontWeight: 'normal' },
        padding: [5, 0, 10, 0], // 上右下左内边距
      }
    : {
        ...titleConfig,
        textStyle: {
          fontSize: 14,
          fontWeight: 'normal',
          ...titleConfig.textStyle,
        },
        padding: titleConfig.padding || [5, 0, 10, 0],
      }

  const validatedOption = {
    ...echartsOption,
    title: normalizedTitle,
    // 确保 tooltip 存在
    tooltip: echartsOption.tooltip || { trigger: 'axis' },
    // 增加 grid 顶部间距，为标题预留空间
    grid: echartsOption.grid || { top: 60, containLabel: true },
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

