/**
 * # ChatQueryResultView 聊天查询结果视图组件
 *
 * ## [MODULE]
 * **文件名**: ChatQueryResultView.tsx
 * **职责**: 展示AI聊天查询的结果数据，包括图表可视化和数据表格
 * **作者**: Data Agent Team
 * **版本**: 1.1.0
 *
 * ## [INPUT]
 * - **table?: ChatQueryResultTable** - 查询结果表格数据，包含列名、行数据和总行数
 * - **chart?: ChatQueryChart** - 查询结果图表数据，包含图表类型、标题和图片URL
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element | null - 查询结果展示界面，包含图表卡片和数据表格卡片
 *
 * ## [LINK]
 * **上游依赖**:
 * - [@/lib/api-client](../../lib/api-client.ts) - 提供查询结果类型定义
 * - [@/components/ui/card](../ui/card.tsx) - 卡片容器组件
 * - [@/components/ui/scroll-area](../ui/scroll-area.tsx) - 滚动区域组件
 * - [@/lib/utils](../../lib/utils.ts) - cn() 工具函数
 *
 * **下游依赖**:
 * - [MessageList.tsx](./MessageList.tsx) - 在消息列表中展示查询结果
 * - [ChatInterface.tsx](./ChatInterface.tsx) - 在聊天界面中集成查询结果展示
 *
 * ## [STATE]
 * - **MAX_ROWS: 20** - 表格最大显示行数
 * - **MAX_COLUMNS: 8** - 表格最大显示列数
 * - **relevantColumns: string[]** - 与图表相关的列名数组（仅展示图表使用字段）
 * - **limitedRows: Record<string, any>[]** - 限制后的行数据数组
 * - **chartType: string** - 图表类型（小写）
 *
 * ## [SIDE-EFFECTS]
 * - **数据限制**: 自动截断过大的表格数据（最多20行×8列）
 * - **字段过滤**: 如果有图表配置，只展示图表使用的字段（x_field, y_field）
 * - **样式适配**: 根据是否有图表调整表格卡片样式
 * - **响应式展示**: 图表图片自适应宽度，表格支持滚动查看
 * - **空状态处理**: 无数据时显示"查询未返回数据"提示
 */
'use client'

import React, { useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ChatQueryChart, ChatQueryResultTable, ChartType } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import { formatNumeric } from '@/utils/numberFormat'
import { DynamicChart } from './DynamicChart'

interface ChatQueryResultViewProps {
  table?: ChatQueryResultTable
  chart?: ChatQueryChart
}

const MAX_ROWS = 20
const MAX_COLUMNS = 8

export function ChatQueryResultView({ table, chart }: ChatQueryResultViewProps) {
  if (!table && !chart) return null

  // ========================================================================
  // 🔥 修复：只展示与图表相关的字段（防止展示不相关的幻觉字段）
  // ========================================================================
  // 如果有图表配置，只展示图表使用的字段
  // 否则展示所有字段（明细表格视图）
  const relevantColumns = useMemo(() => {
    const allColumns = table?.columns || []

    // 如果有图表配置，优先使用图表相关字段
    if (chart && allColumns.length > 0) {
      const chartFields: string[] = []

      // 添加 X 轴字段
      if (chart.x_field && allColumns.includes(chart.x_field)) {
        chartFields.push(chart.x_field)
      }

      // 添加 Y 轴字段
      if (chart.y_field && allColumns.includes(chart.y_field) && !chartFields.includes(chart.y_field)) {
        chartFields.push(chart.y_field)
      }

      // 如果找到了图表相关字段，只返回这些字段
      if (chartFields.length > 0) {
        console.log(`📊 [前端组件] 使用图表相关字段: ${chartFields.join(', ')}`)
        return chartFields
      }
    }

    // 默认返回所有列（限制数量）
    return allColumns.slice(0, MAX_COLUMNS)
  }, [table, chart])

  const limitedRows = table?.rows.slice(0, MAX_ROWS) || []
  const chartType = (chart?.chart_type as ChartType | string | undefined)?.toLowerCase()

  return (
    <div className="mt-3 space-y-3">
      {chart && (
        <Card className="border-blue-100 bg-blue-50/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-blue-900 flex items-center justify-between">
              <span>{chart.title || '数据可视化图表'}</span>
              {chartType && chartType !== 'table' && (
                <span className="text-xs font-normal text-blue-500 uppercase">
                  {chartType}
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="rounded-md overflow-hidden bg-white dark:bg-slate-800 border border-blue-100">
              {/* 优先渲染动态图表 */}
              {chart.chart_config ? (
                <DynamicChart
                  config={chart.chart_config}
                  title={chart.title}
                  chartType={chart.chart_type}
                  className="w-full"
                />
              ) : chart.chart_image ? (
                /* 回退到静态图片 */
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={chart.chart_image}
                  alt={chart.title || '查询结果图表'}
                  className="w-full h-auto object-contain"
                />
              ) : null}
            </div>
          </CardContent>
        </Card>
      )}

      {table && relevantColumns.length > 0 && (
        <Card className={cn('border-gray-100', !chart && 'bg-gray-50 dark:bg-slate-800/60')}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-gray-900">
              {chart && chart.x_field && chart.y_field
                ? `查询结果表（相关字段: ${relevantColumns.join(', ')}）`
                : `查询结果表（前 ${limitedRows.length} 行）`}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <ScrollArea className="w-full max-h-72 rounded-md border bg-white dark:bg-slate-800">
              <table className="w-full text-xs border-collapse">
                <thead className="bg-gray-50 dark:bg-slate-800">
                  <tr>
                    {relevantColumns.map(col => (
                      <th
                        key={col}
                        className="px-3 py-2 border-b text-left font-medium text-gray-700 whitespace-nowrap"
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {limitedRows.map((row, rowIndex) => (
                    <tr key={rowIndex} className="odd:bg-white dark:bg-slate-800 even:bg-gray-50 dark:bg-slate-800/60">
                      {relevantColumns.map(col => (
                        <td
                          key={col}
                          className="px-3 py-1.5 border-b text-gray-800 align-top max-w-xs"
                        >
                          <span className="line-clamp-3 break-words">
                            {(() => {
                              const raw = row[col]
                              if (raw === undefined || raw === null) return ''
                              const formatted = formatNumeric(raw)
                              return formatted !== '' || raw === 0 ? formatted : String(raw)
                            })()}
                          </span>
                        </td>
                      ))}
                    </tr>
                  ))}
                  {limitedRows.length === 0 && (
                    <tr>
                      <td
                        colSpan={relevantColumns.length}
                        className="px-3 py-4 text-center text-gray-500"
                      >
                        查询未返回数据
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </ScrollArea>
            {table.row_count > limitedRows.length && (
              <p className="mt-1 text-[11px] text-gray-500">
                共 {table.row_count} 行，仅展示前 {limitedRows.length} 行。
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}



