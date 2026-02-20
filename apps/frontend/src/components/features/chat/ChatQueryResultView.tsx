/**
 * ChatQueryResultView 查询结果可视化卡片
 * - 展示图表与表格（仅保留与图表相关的列）
 */
'use client'

import { useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { ChatQueryChart, ChatQueryResultTable } from '@/types/api/chat'
import { cn } from '@/lib/utils'
import { friendlyFieldName } from '@/utils/fieldDisplay'
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

  // 仅展示与图表相关的字段，防止出现无关字段
  const relevantColumns = useMemo(() => {
    const allColumns = table?.columns || []

    if (chart && allColumns.length > 0) {
      const chartFields: string[] = []
      if (chart.x_field && allColumns.includes(chart.x_field)) {
        chartFields.push(chart.x_field)
      }
      if (
        chart.y_field &&
        allColumns.includes(chart.y_field) &&
        !chartFields.includes(chart.y_field)
      ) {
        chartFields.push(chart.y_field)
      }
      if (chartFields.length > 0) return chartFields
    }

    return allColumns.slice(0, MAX_COLUMNS)
  }, [table, chart])

  const limitedRows = table?.rows.slice(0, MAX_ROWS) || []
  const displayRelevantColumns = useMemo(
    () => relevantColumns.map(col => friendlyFieldName(col)),
    [relevantColumns]
  )
  const chartType = chart?.chart_type?.toLowerCase()

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
              {chart.chart_config ? (
                <DynamicChart
                  config={chart.chart_config}
                  title={chart.title}
                  chartType={chart.chart_type}
                  className="w-full"
                />
              ) : chart.chart_image ? (
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
                ? `查询结果表（相关字段: ${displayRelevantColumns.join(', ')}）`
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
                        {friendlyFieldName(col)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {limitedRows.map((row, rowIndex) => (
                    <tr
                      key={rowIndex}
                      className="odd:bg-white dark:bg-slate-800 even:bg-gray-50 dark:bg-slate-800/60"
                    >
                      {relevantColumns.map((col, colIndex) => {
                        const raw = Array.isArray(row)
                          ? row[colIndex]
                          : (row as Record<string, any>)[col]
                        if (raw === undefined || raw === null) {
                          return (
                            <td key={col} className="px-3 py-1.5 border-b text-gray-800 align-top max-w-xs">
                              <span className="line-clamp-3 break-words" />
                            </td>
                          )
                        }
                        const formatted = formatNumeric(raw)
                        const text = formatted !== '' || raw === 0 ? formatted : String(raw)
                        return (
                          <td key={col} className="px-3 py-1.5 border-b text-gray-800 align-top max-w-xs">
                            <span className="line-clamp-3 break-words">{text}</span>
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                  {limitedRows.length === 0 && (
                    <tr>
                      <td colSpan={relevantColumns.length} className="px-3 py-4 text-center text-gray-500">
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
