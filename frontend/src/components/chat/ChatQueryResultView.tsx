'use client'

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ChatQueryChart, ChatQueryResultTable, ChartType } from '@/lib/api-client'
import { cn } from '@/lib/utils'

interface ChatQueryResultViewProps {
  table?: ChatQueryResultTable
  chart?: ChatQueryChart
}

const MAX_ROWS = 20
const MAX_COLUMNS = 8

export function ChatQueryResultView({ table, chart }: ChatQueryResultViewProps) {
  if (!table && !chart) return null

  const limitedColumns = table?.columns.slice(0, MAX_COLUMNS) || []
  const limitedRows = table?.rows.slice(0, MAX_ROWS) || []

  const chartType = (chart?.chart_type as ChartType | string | undefined)?.toLowerCase()

  return (
    <div className="mt-3 space-y-3">
      {chart && chart.chart_image && (
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
            <div className="rounded-md overflow-hidden bg-white border border-blue-100">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={chart.chart_image}
                alt={chart.title || '查询结果图表'}
                className="w-full h-auto object-contain"
              />
            </div>
          </CardContent>
        </Card>
      )}

      {table && limitedColumns.length > 0 && (
        <Card className={cn('border-gray-100', !chart && 'bg-gray-50/60')}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-gray-900">
              查询结果表（前 {limitedRows.length} 行）
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <ScrollArea className="w-full max-h-72 rounded-md border bg-white">
              <table className="w-full text-xs border-collapse">
                <thead className="bg-gray-50">
                  <tr>
                    {limitedColumns.map(col => (
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
                    <tr key={rowIndex} className="odd:bg-white even:bg-gray-50/60">
                      {limitedColumns.map(col => (
                        <td
                          key={col}
                          className="px-3 py-1.5 border-b text-gray-800 align-top max-w-xs"
                        >
                          <span className="line-clamp-3 break-words">
                            {row[col] !== undefined && row[col] !== null
                              ? String(row[col])
                              : ''}
                          </span>
                        </td>
                      ))}
                    </tr>
                  ))}
                  {limitedRows.length === 0 && (
                    <tr>
                      <td
                        colSpan={limitedColumns.length}
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



