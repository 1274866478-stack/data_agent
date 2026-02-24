/**
 * # ProcessingSteps AI处理步骤展示组件
 *
 * ## [MODULE]
 * **文件�?*: ProcessingSteps.tsx
 * **职责**: 可视化展示AI推理和SQL生成的各个处理步骤，支持折叠展开和耗时统计
 * **作�?*: Data Agent Team
 * **版本**: 1.1.0
 *
 * ## [INPUT]
 * - **steps**: ProcessingStep[] - 处理步骤数组
 * - **className**: string (可�? - 自定义样式类�?
 * - **defaultExpanded**: boolean (可�? - 默认是否展开，默认true
 *
 * ## [OUTPUT]
 * - **返回�?*: JSX.Element - 折叠卡片式的步骤列表或null
 * - **副作�?*: 无副作用
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心�?
 * - [@/lib/utils.ts](../../lib/utils.ts) - 工具函数（cn�?
 * - [lucide-react](https://lucide.dev) - 图标库（12种步骤图标）
 * - [@/types/chat.ts](../../types/chat.ts) - ProcessingStep类型定义
 *
 * **下游依赖**:
 * - 无直接下游组�?
 *
 * **调用�?*:
 * - [./MessageList.tsx](./MessageList.tsx) - 消息列表中展示AI推理过程
 *
 * ## [STATE]
 * - **isExpanded**: boolean - 步骤列表展开/折叠状�?
 *
 * ## [SIDE-EFFECTS]
 * - 根据步骤状态自动选择对应图标�?步AI流程�?
 * - 自动计算总耗时和完成进�?
 * - 支持查看详情（如SQL语句）的折叠面板
 *
 * ## [PERFORMANCE]
 * - 使用 React.memo 防止不必要的重新渲染
 * - 使用 useMemo 缓存计算结果
 * - 使用 useCallback 稳定回调函数引用
 */
'use client'

import { Markdown } from '@/components/ui/markdown'
import { PlainText } from '@/components/ui/plain-text'
import { PulseIndicator } from '@/components/ui/PulseIndicator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { formatNumeric } from '@/utils/numberFormat'
import { friendlyFieldName } from '@/utils/fieldDisplay'
import { ProcessingStep, StepChartData, StepTableData } from '@/types/chat'
import ReactECharts from 'echarts-for-react'
import {
    BarChart3,
    Brain,
    CheckCircle2,
    ChevronDown,
    ChevronUp,
    Clock,
    Code2,
    Database,
    FileCode,
    Loader2,
    MessageSquare, // 新增：内容生�?
    Shield, // 新增：思�?上下文检�?
    Sparkles,
    TableProperties,
    Wand2,
    XCircle,
    Zap
} from 'lucide-react'
import React, { useCallback, useEffect, useMemo } from 'react'

interface ProcessingStepsProps {
  steps: ProcessingStep[]
  className?: string
  defaultExpanded?: boolean
  outputFormat?: 'markdown' | 'plain'
}

// 统一的乱码修正常量
const STEP_MOJIBAKE_MAP: Record<string, string> = {
  '鐞嗚В闂': '理解问题',
  '鐞嗚В闂': '理解问题',
  '鍒╃敤鍔涙ā寮�': '调用工具',
}

// 清洗步骤标题/描述的辅助函数
const sanitizeStepText = (text?: string | null, fallback?: string): string | undefined => {
  if (text === undefined || text === null) return fallback
  let result = String(text)
  // 已知乱码映射
  for (const [bad, good] of Object.entries(STEP_MOJIBAKE_MAP)) {
    if (result.includes(bad)) result = result.replace(new RegExp(bad, 'g'), good)
  }
  // 兜底：遇到“鐞嗚”直接替换
  if (result.includes('鐞嗚')) result = '理解问题'
  // 移除不可见字符
  result = result.replace(/[^\x20-\x7E\u4e00-\u9fa5，。？！：；、（）【】《》“”‘’·]/g, '').trim()
  return result.length > 0 ? result : fallback
}

const sanitizeStep = (step: ProcessingStep, idxFallback?: number): ProcessingStep => ({
  ...step,
  title: sanitizeStepText(step.title, idxFallback !== undefined ? `步骤${idxFallback}` : step.title),
  description: sanitizeStepText(step.description),
  message: sanitizeStepText((step as any).message),
})

// 判断是否为数字（字符串或数字类型均可）
function isNumeric(value: any): boolean {
  if (value === null || value === undefined) return false
  if (typeof value === 'number') return Number.isFinite(value)
  if (typeof value === 'string') return /^-?\d+(\.\d+)?$/.test(value.trim())
  return false
}

function getStepIcon(step: number, title: string, status: ProcessingStep['status']) {
  const iconClass = 'w-4 h-4'
  // 状态优先：运行/错误
  if (status === 'running') return <Loader2 className={cn(iconClass, 'animate-spin text-primary')} />
  if (status === 'error') return <XCircle className={cn(iconClass, 'text-destructive')} />

  const t = (title || '').toLowerCase()

  if (status === 'completed') {
    if (t.includes('意图') || t.includes('理解') || t.includes('用户问题') || t.includes('intent') || step === 0) {
      return <Brain className={cn(iconClass, 'text-green-500')} />
    }
    if (t.includes('检索') || t.includes('上下文') || t.includes('知识') || t.includes('retriev') || t.includes('context')) {
      return <Brain className={cn(iconClass, 'text-green-500')} />
    }
    if (t.includes('schema') || t.includes('数据库') || t.includes('表结构')) {
      return <TableProperties className={cn(iconClass, 'text-green-500')} />
    }
    if (t.includes('策略') || t.includes('prompt') || t.includes('构建')) {
      return <Wand2 className={cn(iconClass, 'text-green-500')} />
    }
    if (t.includes('sql') && (t.includes('生成') || t.includes('构建'))) {
      return <Code2 className={cn(iconClass, 'text-green-500')} />
    }
    if (t.includes('生成') || t.includes('回复') || t.includes('内容')) {
      return <Sparkles className={cn(iconClass, 'text-green-500')} />
    }
    if (t.includes('安全') || t.includes('检测') || t.includes('合规')) {
      return <Shield className={cn(iconClass, 'text-green-500')} />
    }
    if (t.includes('优化') || t.includes('输出') || t.includes('完成') || t.includes('最终')) {
      return <CheckCircle2 className={cn(iconClass, 'text-green-500')} />
    }
    if (t.includes('提取') || t.includes('代码')) {
      return <FileCode className={cn(iconClass, 'text-green-500')} />
    }
    if (t.includes('执行') || t.includes('查询') || t.includes('运行')) {
      return <Zap className={cn(iconClass, 'text-green-500')} />
    }
    if (t.includes('图表') || t.includes('可视化') || t.includes('展示')) {
      return <BarChart3 className={cn(iconClass, 'text-green-500')} />
    }
    if (t.includes('数据源') || t.includes('连接')) {
      return <Database className={cn(iconClass, 'text-green-500')} />
    }

    // 兜底按步骤编号映射
    switch (step) {
      case 0: return <Brain className={cn(iconClass, 'text-green-500')} />
      case 1: return <MessageSquare className={cn(iconClass, 'text-green-500')} />
      case 2: return <TableProperties className={cn(iconClass, 'text-green-500')} />
      case 3: return <Wand2 className={cn(iconClass, 'text-green-500')} />
      case 4: return <Code2 className={cn(iconClass, 'text-green-500')} />
      case 5: return <FileCode className={cn(iconClass, 'text-green-500')} />
      case 6: return <Zap className={cn(iconClass, 'text-green-500')} />
      case 7: return <BarChart3 className={cn(iconClass, 'text-green-500')} />
      default: return <CheckCircle2 className={cn(iconClass, 'text-green-500')} />
    }
  }

  // pending 状态
  return <Clock className={cn(iconClass, 'text-muted-foreground')} />
}

// 获取步骤的状态颜�?- DataLab Tiffany 色系
function getStatusColor(status: ProcessingStep['status']) {
  switch (status) {
    case 'completed':
      return 'border-tiffany-500/30 bg-tiffany-500/10'
    case 'running':
      return 'border-tiffany-400/50 bg-tiffany-400/20'
    case 'error':
      return 'border-red-500/30 bg-red-500/10'
    default:
      return 'border-slate-200 dark:border-slate-700 bg-slate-100/50 dark:bg-slate-800/50'
  }
}

// 格式化耗时
function formatDuration(ms?: number) {
  if (!ms) return ''
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

// 🔧 表格辅助：选择维度键（优先字符串列�?
function pickKeyColumn(columns: string[], rows: any[]): string {
  if (!columns || columns.length === 0) return ''
  const sampleRow = rows && rows.length > 0 ? rows[0] : null
  if (sampleRow) {
    for (const col of columns) {
      const val = Array.isArray(sampleRow) ? sampleRow[columns.indexOf(col)] : (sampleRow as any)[col]
      if (typeof val === 'string' && val.trim().length > 0) return col
    }
  }
  // 兜底使用首列
  return columns[0]
}

// 🔧 将行转换为对象，兼容数组与对象形�?
function rowToObj(columns: string[], row: any): Record<string, any> {
  if (Array.isArray(row)) {
    const obj: Record<string, any> = {}
    columns.forEach((col, idx) => {
      obj[col] = row[idx]
    })
    return obj
  }
  return { ...(row as Record<string, any>) }
}

// 🔧 计算列名 Jaccard 相似�?
function columnSimilarity(colsA: string[], colsB: string[]): number {
  const setA = new Set(colsA.map(c => c.toLowerCase()))
  const setB = new Set(colsB.map(c => c.toLowerCase()))
  const intersection = [...setA].filter(x => setB.has(x)).length
  const union = new Set([...setA, ...setB]).size || 1
  return intersection / union
}

// 🔧 合并相邻相似表格步骤（减少步�?/9重复表）
function mergeSimilarTableSteps(steps: ProcessingStep[]): ProcessingStep[] {
  if (!steps || steps.length === 0) return steps

  const merged: ProcessingStep[] = []
  let i = 0
  while (i < steps.length) {
    const current = steps[i]
    const next = steps[i + 1]

    const isCurrentTable = current.content_type === 'table' && current.content_data?.table
    const isNextTable = next && next.content_type === 'table' && next.content_data?.table

    // 仅处理相邻表�?
    if (isCurrentTable && isNextTable) {
      const tableA = current.content_data!.table as StepTableData
      const tableB = next.content_data!.table as StepTableData

      const sim = columnSimilarity(tableA.columns, tableB.columns)
      const rowClose = Math.abs((tableA.row_count || 0) - (tableB.row_count || 0)) <= 1

      if (sim >= 0.8 && rowClose) {
        // 选择维度�?
        const keyCol = pickKeyColumn(tableA.columns, tableA.rows)

        const sources = [
          tableA.source_label || current.title || current.message || `step-${current.step}`,
          tableB.source_label || next!.title || next!.message || `step-${next!.step}`
        ]

        // 初始化合并列：保�?key 列，其余列带来源后缀防冲�?
        const mergedColumns: string[] = []
        const suffixCache = new Map<string, string>()
        const ensureColumn = (col: string, sourceLabel: string) => {
          if (!mergedColumns.includes(col)) {
            mergedColumns.push(col)
            suffixCache.set(col, '')
          } else if (col !== keyCol) {
            const withSuffix = `${col}（${sourceLabel}）`
            if (!mergedColumns.includes(withSuffix)) {
              mergedColumns.push(withSuffix)
              suffixCache.set(col, sourceLabel)
            }
          }
        }

        tableA.columns.forEach(col => ensureColumn(col, sources[0]))
        tableB.columns.forEach(col => ensureColumn(col, sources[1]))

        // 行外连接
        const mergedRowMap: Record<string, Record<string, any>> = {}
        const ingest = (table: StepTableData, sourceLabel: string) => {
          table.rows.forEach((row, idx) => {
            const obj = rowToObj(table.columns, row)
            const keyValRaw = obj[keyCol]
            const keyVal = (keyValRaw === undefined || keyValRaw === null)
              ? `__idx_${idx}_${sourceLabel}`
              : String(keyValRaw)
            if (!mergedRowMap[keyVal]) {
              mergedRowMap[keyVal] = { [keyCol]: keyValRaw }
            }
            for (const col of table.columns) {
              const targetCol = (col !== keyCol && suffixCache.get(col)) ? `${col}（${sourceLabel}）` : col
              mergedRowMap[keyVal][targetCol] = obj[col]
            }
          })
        }

        ingest(tableA, sources[0])
        ingest(tableB, sources[1])

        const mergedRows = Object.values(mergedRowMap)

        const mergedStep: ProcessingStep = {
          ...current,
          content_data: {
            ...(current.content_data || {}),
            table: {
              columns: mergedColumns,
              rows: mergedRows,
              row_count: mergedRows.length,
              source_label: sources.join(' / '),
              merged_from_steps: [current.step, next!.step],
            }
          }
        }

        merged.push(mergedStep)
        i += 2
        continue
      }
    }

    merged.push(current)
    i += 1
  }

  return merged
}

// 渲染SQL代码块（可折叠版本）
interface SQLCodeRendererProps {
  sql: string
  defaultExpanded?: boolean
}

const SQLCodeRenderer = React.memo(function SQLCodeRenderer({ sql, defaultExpanded = false }: SQLCodeRendererProps) {
  const [isExpanded, setIsExpanded] = React.useState(defaultExpanded)

  // 使用 useCallback 稳定回调函数
  const handleToggle = useCallback(() => {
    setIsExpanded(prev => !prev)
  }, [])

  // 计算SQL行数和字符数
  const lineCount = sql.split('\n').length
  const charCount = sql.length

  return (
    <div className="mt-2 rounded-md bg-slate-900 overflow-hidden border border-slate-700">
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between px-3 py-1.5 bg-slate-800 border-b border-slate-700 hover:bg-slate-700 transition-colors"
      >
        <span className="text-xs font-medium text-slate-300 flex items-center gap-2">
          <Code2 className="w-3.5 h-3.5 text-primary" />
          SQL
          <span className="text-slate-500 font-normal">
            ({lineCount} lines, {charCount} chars)
          </span>
        </span>
        {isExpanded ? (
          <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
        )}
      </button>
      {isExpanded && (
        <pre className="p-3 overflow-x-auto max-h-64 overflow-y-auto bg-slate-900">
          <code className="text-xs text-secondary font-mono">{sql}</code>
        </pre>
      )}
    </div>
  )
})

// 渲染SQL代码块（简单版本，用于非步�?�? DataLab 深色风格
function renderSQLCode(sql: string) {
  return (
    <div className="mt-2 rounded-md bg-slate-900 overflow-hidden border border-slate-700">
      <div className="flex items-center justify-between px-3 py-1.5 bg-slate-800 border-b border-slate-700">
        <span className="text-xs font-medium text-slate-300 flex items-center gap-2">
          <Code2 className="w-3.5 h-3.5 text-primary" />
          SQL
        </span>
      </div>
      <pre className="p-3 overflow-x-auto bg-slate-900">
        <code className="text-xs text-secondary font-mono">{sql}</code>
      </pre>
    </div>
  )
}

// 渲染数据表格（组件形式，支持状态管理）
interface TableDataRendererProps {
  table: StepTableData
}

const TableDataRenderer = React.memo(function TableDataRenderer({ table }: TableDataRendererProps) {
  const [isExpanded, setIsExpanded] = React.useState(false)

  // 使用 useCallback 稳定回调函数
  const handleToggle = useCallback(() => {
    setIsExpanded(prev => !prev)
  }, [])

  // 🔧 默认只显示前5行，避免占用过多空间（从50改为5�?
  const DEFAULT_MAX_ROWS = 5
  const MAX_COLUMNS = 10  // 增加列数限制

  // 使用 useMemo 缓存计算结果
  const limitedColumns = useMemo(
    () => table.columns.slice(0, MAX_COLUMNS),
    [table.columns]
  )

  const displayRows = useMemo(
    () => isExpanded ? table.rows : table.rows.slice(0, DEFAULT_MAX_ROWS),
    [isExpanded, table.rows]
  )

  const hasMoreRows = table.row_count > DEFAULT_MAX_ROWS
  const hasMoreColumns = table.columns.length > MAX_COLUMNS

  return (
    <div className="mt-2 rounded-md border border-primary/20 overflow-hidden bg-card">
      <div className="flex items-center justify-between px-3 py-1.5 bg-primary/5 border-b border-primary/20">
        <span className="text-xs font-medium text-primary">可视化数据表</span>
        <span className="text-xs text-primary/70">
          表格 · {table.row_count} 行 × {table.columns.length} 列
          {hasMoreColumns && ` (仅展示前 ${MAX_COLUMNS} 列)`}
        </span>
      </div>
      <ScrollArea>
        <table className="w-full text-xs border-collapse">
          <thead className="bg-muted sticky top-0 z-10">
            <tr>
              {limitedColumns.map(col => (
                <th
                  key={col}
                  className="px-3 py-2 border-b text-left font-medium text-foreground whitespace-nowrap bg-muted"
                >
                  {friendlyFieldName(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, rowIndex) => {
              // 🔧 修复：支持两�?rows 格式（数组格式和对象格式�?
              const isArrayRow = Array.isArray(row)
              
              return (
                <tr key={rowIndex} className="odd:bg-card even:bg-muted hover:bg-primary/5">
                  {limitedColumns.map((col, colIndex) => {
                    const cellValue = isArrayRow ? row[colIndex] : row[col]
                    const numeric = isNumeric(cellValue)
                    return (
                      <td
                        key={col}
                        className={cn(
                          'px-3 py-1.5 border-b text-foreground align-top',
                          numeric && 'text-right tabular-nums'
                        )}
                      >
                        <span className="break-words whitespace-pre-wrap">
                          {cellValue !== undefined && cellValue !== null
                            ? String(cellValue)
                            : ''}
                        </span>
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </ScrollArea>
      {/* 展开/收起按钮 */}
      {(hasMoreRows || hasMoreColumns) && (
        <div className="px-3 py-1.5 bg-primary/5 border-t border-primary/20 flex items-center justify-between">
          <span className="text-xs text-primary">
            {isExpanded
              ? `显示全部 ${table.row_count} 行`
              : `共 ${table.row_count} 行，当前显示 ${Math.min(DEFAULT_MAX_ROWS, table.row_count)} 行`
            }
            {hasMoreColumns && ` · 仅展示前 ${MAX_COLUMNS} 列`}
          </span>
          {hasMoreRows && (
            <button
              onClick={handleToggle}
              className="text-xs text-primary hover:text-primary/80 font-medium"
            >
              {isExpanded ? '收起' : '展开全部'}
            </button>
          )}
        </div>
      )}
    </div>
  )
})

/**
 * 解析数据分析文本，提取总结和图表说�?
 * 返回: { summary: 总结部分, chartDescriptions: 图表说明数组 }
 */
function parseAnalysisText(text: string): { summary: string; chartDescriptions: string[] } {
  if (!text) return { summary: '', chartDescriptions: [] }

  // 🔧 先过滤详细分析模块（数据概览、数值统计、数据预览）
  const filteredText = filterDetailedAnalysis(text)

  // 查找第一个图表标题的位置（如"第一个图�?�?图表1"等）
  const chartTitlePattern = /(?:第\s*[一二三四五六七八九十\d]+\s*�?图表[:：]?\s*)|(?:图表\s*[一二三四五六七八九十\d]+[:：]?\s*)/i
  const firstChartIndex = filteredText.search(chartTitlePattern)

  // 如果找到图表标题，分割文�?
  if (firstChartIndex > 0) {
    const summaryPart = filteredText.substring(0, firstChartIndex).trim()
    const chartPart = filteredText.substring(firstChartIndex)

    // 解析图表说明
    const chartDescriptions: string[] = []
    const parts = chartPart.split(chartTitlePattern)

    // 找到所有图表标�?
    const chartTitles = chartPart.match(/(?:第\s*[一二三四五六七八九十\d]+\s*�?图表[:：]?\s*[^。\n]*)|(?:图表\s*[一二三四五六七八九十\d]+[:：]?\s*[^。\n]*)/gi)

    if (chartTitles && chartTitles.length > 0) {
      let contentIndex = 1  // 跳过第一个空部分
      for (let i = 0; i < chartTitles.length; i++) {
        const title = chartTitles[i].trim()
        const content = parts[contentIndex]?.trim() || ''
        if (title || content) {
          chartDescriptions.push(`${title}${content ? '：' + content : ''}`)
        }
        contentIndex++
      }
    }

    return {
      summary: summaryPart,
      chartDescriptions: chartDescriptions.length > 0 ? chartDescriptions : []
    }
  }

  // 没有找到图表标题，返回过滤后的整个文本作为总结
  return { summary: filteredText, chartDescriptions: [] }
}

/**
 * 🔧 清理图表标题中的 Markdown 符号
 * 移除 **�?�? �?Markdown 格式标记
 */
function cleanMarkdownSymbols(text: string): string {
  if (!text || typeof text !== 'string') return text
  return text
    .replace(/\*\*/g, '')        // 移除加粗标记
    .replace(/\*/g, '')          // 移除斜体标记
    .replace(/^#+\s*/, '')       // 移除标题级标�?
    .trim()
}

/**
 * 安全深拷贝，避免循环引用导致�?JSON 序列化失�?
 * 使用 structuredClone 或递归浅拷贝作为后备方�?
 */
function safeDeepClone<T>(obj: T): T {
  if (!obj || typeof obj !== 'object') return obj

  // 优先使用 structuredClone（现代浏览器支持�?
  if (typeof structuredClone !== 'undefined') {
    try {
      return structuredClone(obj)
    } catch {
      // 如果 structuredClone 失败，使用后备方�?
    }
  }

  // 后备方案：递归浅拷贝（处理常见对象结构�?
  if (Array.isArray(obj)) {
    return obj.map(item => safeDeepClone(item)) as any
  }

  const cloned: any = {}
  for (const key in obj) {
    if (obj.hasOwnProperty(key) && typeof obj[key] === 'object' && obj[key] !== null) {
      cloned[key] = safeDeepClone(obj[key])
    } else {
      cloned[key] = obj[key]
    }
  }
  return cloned
}

/**
 * 规范�?ECharts 配置，确保纵坐标标签完整显示
 * 自动添加合理�?grid 配置和坐标轴边距
 */
function normalizeEChartsOption(option: any): any {
  if (!option || typeof option !== 'object') return option

  // 深拷贝避免修改原始配置，使用安全拷贝方法
  const normalized = safeDeepClone(option)

  // 🔧 新增：清理标题中�?Markdown 符号
  if (normalized.title?.text) {
    normalized.title.text = cleanMarkdownSymbols(normalized.title.text)
  }

  // 修复：如果有 grid 配置，强制修正可能导致截断的�?
  if (normalized.grid) {
    if (Array.isArray(normalized.grid)) {
      normalized.grid.forEach((g: any) => {
        // 强制设置合理值，防止图表被截�?
        g.left = '15%'
        g.right = '5%'
        g.bottom = '10%'
        g.top = '15%'
        g.containLabel = true
      })
    } else {
      normalized.grid.left = '15%'
      normalized.grid.right = '5%'
      normalized.grid.bottom = '10%'
      normalized.grid.top = '15%'
      normalized.grid.containLabel = true
    }
  } else {
    // 没有 grid 配置时，添加默认配置
    normalized.grid = {
      left: '15%',
      right: '5%',
      bottom: '10%',
      top: '15%',
      containLabel: true
    }
  }

  // 确保 yAxis 有足够的空间显示标签
  if (normalized.yAxis) {
    if (Array.isArray(normalized.yAxis)) {
      normalized.yAxis.forEach((axis: any) => {
        if (axis.axisLabel && axis.axisLabel.margin === undefined) {
          axis.axisLabel.margin = 20
        }
        if (axis.axisLabel && !axis.axisLabel.formatter) {
          axis.axisLabel.formatter = (val: any) => formatNumeric(val)
        }
      })
    } else if (normalized.yAxis.axisLabel && normalized.yAxis.axisLabel.margin === undefined) {
      normalized.yAxis.axisLabel.margin = 20
      if (!normalized.yAxis.axisLabel.formatter) {
        normalized.yAxis.axisLabel.formatter = (val: any) => formatNumeric(val)
      }
    }
  }

  // 确保 xAxis 也有合理配置
  if (normalized.xAxis) {
    if (Array.isArray(normalized.xAxis)) {
      normalized.xAxis.forEach((axis: any) => {
        if (axis.axisLabel && axis.axisLabel.margin === undefined) {
          axis.axisLabel.margin = 15
        }
        if (axis.axisLabel && !axis.axisLabel.formatter) {
          axis.axisLabel.formatter = (val: any) => formatNumeric(val)
        }
      })
    } else if (normalized.xAxis.axisLabel && normalized.xAxis.axisLabel.margin === undefined) {
      normalized.xAxis.axisLabel.margin = 15
      if (!normalized.xAxis.axisLabel.formatter) {
        normalized.xAxis.axisLabel.formatter = (val: any) => formatNumeric(val)
      }
    }
  }

  return normalized
}

// 渲染图表
function renderChart(chart: StepChartData, description?: string) {
  // 🔧 调试日志
  console.log({
    has_echarts_option: !!chart.echarts_option,
    has_chart_image: !!chart.chart_image,
    chart_type: chart.chart_type,
    title: chart.title,
  })

  // 图表说明文字（显示在图表上方�?
  const descriptionElement = description && description.trim() && (
    <div className="mb-2 p-3 rounded-md bg-primary/5 border border-primary/20">
      <div className="text-xs font-medium text-primary mb-1">图表说明</div>
      <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">
        {description}
      </p>
    </div>
  )

  if (chart.echarts_option) {
    // 规范化配置，确保坐标轴标签完整显�?
    const normalizedOption = normalizeEChartsOption(chart.echarts_option)

    return (
      <>
        {descriptionElement}
        <div className="mt-2 rounded-md border border-primary/20 bg-card">
          <div className="flex items-center justify-between px-3 py-1.5 bg-primary/5 border-b border-primary/20">
            <span className="text-xs font-medium text-primary">数据可视化</span>
            {chart.chart_type && (
              <span className="text-xs text-primary/70 uppercase">{chart.chart_type}</span>
            )}
          </div>
          <div className="p-2" style={{ minHeight: '420px' }}>
            <ReactECharts
              option={normalizedOption}
              style={{ width: '100%', height: '400px' }}
              opts={{ renderer: 'canvas' }}
              notMerge={false}
              lazyUpdate={false}
            />
          </div>
        </div>
      </>
    )
  }

  if (chart.chart_image) {
    return (
      <>
        {descriptionElement}
        <div className="mt-2 rounded-md border border-primary/20 overflow-hidden bg-card">
          <div className="flex items-center justify-between px-3 py-1.5 bg-primary/5 border-b border-primary/20">
            <span className="text-xs font-medium text-primary">数据可视化</span>
          </div>
          <div className="p-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={chart.chart_image}
              alt={chart.title || '图表'}
              className="w-full h-auto rounded"
            />
          </div>
        </div>
      </>
    )
  }

  // 🔧 计划修复4：图表配置存在但渲染失败时显示错误提�?
  if (chart && !chart.echarts_option && !chart.chart_image) {
    console.warn('[ProcessingSteps] ⚠️ 图表配置存在但无可渲染内�?', chart)
    return (
      <div className="mt-2 p-3 rounded-md bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700">
        <div className="text-xs text-yellow-700 dark:text-yellow-300">
          ⚠️ 图表配置不完整，无法显示图表
        </div>
      </div>
    )
  }

  return null
}

// 🔧 新增：将图表和表格合并渲染到同一�?可视化数�?区域
function renderVisualization(
  chart: StepChartData | null,
  table: StepTableData | null,
  description?: string
) {
  // 🔧 调试日志
  console.log({
    has_chart: !!chart,
    has_table: !!table,
    chart_has_echarts_option: !!chart?.echarts_option,
    chart_has_image: !!chart?.chart_image,
    chart_type: chart?.chart_type,
    table_rows: table?.row_count,
  })

  if (!chart && !table) return null

  const descriptionElement = description && description.trim() && (
    <div className="mb-2 p-3 rounded-md bg-primary/5 border border-primary/20">
      <div className="text-xs font-medium text-primary mb-1">图表说明</div>
      <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">{description}</p>
    </div>
  )

  const chartTypeLabel = chart?.chart_type || ''

  const chartElement = chart?.echarts_option ? (
    <div className="p-2" style={{ minHeight: '420px' }}>
      <ReactECharts
        option={normalizeEChartsOption(chart.echarts_option)}
        style={{ width: '100%', height: '400px' }}
        opts={{ renderer: 'canvas' }}
        notMerge={false}
        lazyUpdate={false}
      />
    </div>
  ) : chart?.chart_image ? (
    <div className="p-2">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={chart.chart_image} alt={chart.title || '图表'} className="w-full h-auto rounded" />
    </div>
  ) : null

  const tableElement = table ? (
      <div className="border-b border-primary/30">
        <div className="flex items-center justify-between px-3 py-1.5 bg-primary/5">
          <span className="text-xs font-medium text-primary flex items-center gap-1.5">
            <TableProperties className="w-3.5 h-3.5" />
            查询数据
          </span>
        <span className="text-xs text-primary/70 flex items-center gap-2">
          {table.source_label && (
            <span className="px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
              {table.source_label}
            </span>
          )}
          {table.row_count} 行 × {table.columns.length} 列
        </span>
        </div>
        <ScrollArea>
        <table className="w-full text-xs border-collapse">
          <thead className="bg-muted sticky top-0 z-10">
            <tr>
              {table.columns.slice(0, 10).map(col => (
                <th key={col} className="px-3 py-2 border-b border-border text-left font-medium text-foreground whitespace-nowrap bg-muted">
                  {friendlyFieldName(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.slice(0, 20).map((row, rowIndex) => {
              // 🔧 修复：支持两�?rows 格式
              // 格式1: 数组格式 [[val1, val2], ...] - 后端 execute_query 返回的格�?
              // 格式2: 对象格式 [{col1: val1, col2: val2}, ...] - 某些其他来源的格�?
              const isArrayRow = Array.isArray(row)
              
              return (
                <tr key={rowIndex} className="odd:bg-card even:bg-muted hover:bg-primary/5">
                  {table.columns.slice(0, 10).map((col, colIndex) => {
                    // 如果 row 是数组，使用索引访问；如果是对象，使用列名访�?
                    const rawValue = isArrayRow ? row[colIndex] : row[col]
                    const formatted = rawValue !== undefined && rawValue !== null
                      ? formatNumeric(rawValue, { thousandSeparator: false })
                      : ''
                    const cellValue =
                      formatted !== '' || rawValue === 0
                        ? formatted
                        : (rawValue !== undefined && rawValue !== null ? String(rawValue) : '')
                    return (
                      <td key={col} className="px-3 py-1.5 border-b border-border text-foreground align-top">
                        <span className="break-words whitespace-pre-wrap">
                          {cellValue}
                        </span>
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </ScrollArea>
      {table.row_count > 20 && (
        <div className="px-3 py-1.5 bg-primary/5 text-center border-t border-primary/30">
          <span className="text-xs text-primary">共 {table.row_count} 行，显示前 20 行</span>
        </div>
      )}
    </div>
  ) : null

  // 图表区域添加标题
  const chartElementWithTitle = chartElement ? (
    <div>
      <div className="flex items-center justify-between px-3 py-1.5 bg-emerald-50/50 border-b border-emerald-100">
        <span className="text-xs font-medium text-emerald-700 flex items-center gap-1.5">
          <BarChart3 className="w-3.5 h-3.5" />
          图表分析
        </span>
        {chart?.chart_type && (
          <span className="text-xs text-emerald-500 uppercase">{chart.chart_type}</span>
        )}
      </div>
      {chartElement}
    </div>
  ) : null


  return (
    <>
      {descriptionElement}
      <div className="mt-2 rounded-md border border-primary/30 bg-card">
        <div className="flex items-center justify-between px-3 py-1.5 bg-primary/5 border-b border-primary/30">
          <span className="text-xs font-medium text-primary">📊 可视化数据</span>
          <span className="text-xs text-primary/70">
            {table && '数据表格'}{table && chartElementWithTitle && ' + '}{chartElementWithTitle && '图表分析'}
          </span>
        </div>
        {/* 先显示表格数据，再显示图�?*/}
        {tableElement}
        {chartElementWithTitle}
      </div>
    </>
  )
}

/**
 * 🆕 过滤技术性步骤，只展示业务相关步�?
 *
 * 需要隐藏的技术性步骤（内部实现细节）：
 * - list_tables: 获取表列表（元数据操作）
 * - get_schema: 获取表结构（元数据操作）
 * - connect_db: 连接数据库（基础设施�?
 * - validate_query: SQL验证（内部校验）
 * - 调用工具: 所有工具调用步�?
 *
 * 更新：扩展隐藏关键词列表，包含更多技术细节步�?
 */
function filterTechnicalSteps(steps: ProcessingStep[]): ProcessingStep[] {
  const HIDDEN_STEP_KEYWORDS = [
    'list_tables',
    'get_schema',
    'get_recommended_tables',
    '获取表列',
    '获取表结构',
    '连接数据源',
    'sql验证',
    'validate_query',
    '元数据获取',
    'schema检索',
    '列出数据库表',
    '获取数据库结构',
    '数据源连接中',
    '模式加载中',
    '知识库查询中',
    '上下文检索',
    '知识检索',
    '向量检索',
    '加载模式',
    '加载数据',
    '正在连接',
    '连接中',
    '验证中',
    '检查中',
    '初始化',
    '准备中',
  ]

  const DUPLICATE_STEP_KEYWORDS = [
    'sql生成',
    '生成sql',
    '执行查询',
    '数据分析',
    '处理',
    '生成',
    '查询结果',
  ]

  let filtered = steps.filter(step => {
    const titleLower = (step.title || '').toLowerCase()

    const isChartStep = (
      titleLower.includes('图表') ||
      titleLower.includes('可视化') ||
      titleLower.includes('数据分布') ||
      titleLower.includes('分布图') ||
      titleLower.includes('趋势图') ||
      titleLower.includes('柱状图') ||
      titleLower.includes('折线图') ||
      titleLower.includes('饼图') ||
      step.content_type === 'chart'
    )
    if (isChartStep) {
      return true
    }

    if (titleLower.startsWith('调用工具:') || titleLower.startsWith('调用工具：')) {
      return false
    }

    const isHidden = HIDDEN_STEP_KEYWORDS.some(keyword =>
      titleLower.includes(keyword.toLowerCase())
    )

    return !isHidden
  })

  const stepMap = new Map<string, ProcessingStep>()

  for (const step of filtered) {
    const title = step.title || ''
    const titleLower = title.toLowerCase()
    const isDuplicateType = DUPLICATE_STEP_KEYWORDS.some(keyword =>
      titleLower.includes(keyword.toLowerCase())
    )

    if (isDuplicateType) {
      const existing = stepMap.get(titleLower)
      if (titleLower.includes('查询结果')) {
        const existingRowCount = existing?.content_data?.table?.row_count ?? 0
        const currentRowCount = step?.content_data?.table?.row_count ?? 0
        const existingHasData = existingRowCount > 0
        const currentHasData = currentRowCount > 0
        if (currentHasData || !existingHasData) {
          stepMap.set(titleLower, step)
        }
      } else {
        stepMap.set(titleLower, step)
      }
    } else {
      const uniqueKey = `${step.step}_${title}`
      stepMap.set(uniqueKey, step)
    }
  }

  filtered = Array.from(stepMap.values())
  filtered.sort((a, b) => a.step - b.step)

  return filtered
}

function filterExampleContent(text: string): string {
  // 硬编码示例内容的特征指纹（这些数值不会出现在真实数据中）
  const EXAMPLE_FINGERPRINTS = [
    '11.53亿元',      // 硬编码的年度销售额
    '9,610万元',      // 硬编码的月均销售额
    '�?.10亿元',     // 硬编码的峰�?
  ]

  // 按段落分�?
  const paragraphs = text.split(/\n\n+/)

  // 只过滤包含特征指纹的段落，其他段落保�?
  const filtered = paragraphs
    .filter(para => {
      return !EXAMPLE_FINGERPRINTS.some(fingerprint =>
        para.includes(fingerprint)
      )
    })
    .join('\n\n')

  return filtered.trim()
}

/**
 * 🔧 过滤 Markdown 源码泄露内容
 * 移除 AI 输出中可能泄露的 Markdown 源码标记
 */
function filterMarkdownLeaks(text: string): string {
  if (!text) return text

  const lines = text.split('\n')
  const filteredLines: string[] = []

  // 源码泄露检测模�?
  const LEAK_PATTERNS = [
    /^#{2,}\s+\w+.*#{2,}\s*[📊📈📉💼🔍]/,  // 多级标题 + emoji
    /^#{2,}\s+202[0-9].*#{2,}/,             // 年份标题组合
    /^##\s+.*###\s*$/,                        // 任意 ##...### 模式
    /^(##|###)\s+.*\1\s+/,                   // 重复标题标记
    /^(##|###)\s.*(数据概览|趋势分析|📊)/,   // 特征词汇组合
  ]

  for (const line of lines) {
    const trimmed = line.trim()
    const isLeak = LEAK_PATTERNS.some(pattern => pattern.test(trimmed))
    if (!isLeak) {
      filteredLines.push(line)
    }
  }

  return filteredLines.join('\n')
}

/**
 * 🆕 过滤详细数据分析模块
 * 隐藏数据概览、数值统计、数据预览等技术细节，只保留简洁的分析总结
 *
 * 需要过滤的区块�?
 * - 📈 数据概览
 * - 🔢 数值统�?
 * - 📋 数据预览
 * - 返回 X 条记�?
 * - 包含 X 个字�?
 * - 各字段统计信�?
 */
function filterDetailedAnalysis(text: string): string {
  if (!text) return text

  const lines = text.split('\n')
  const filteredLines: string[] = []
  let skipSection = false

  // 需要跳过的区块起始标记
  const SECTION_START_PATTERNS = [
    /^📈\s*\*\*数据概览\*\*/,
    /^\*\*📈\s*数据概览\*\*/,
    /^\*\*🔢\s*数值统计\*\*/,
    /^\*\*📋\s*数据预览\*\*/,
    /^📋\s*\*\*数据预览\*\*/,
    /^数据概览/,
    /^数值统计/,
    /^数据预览/,
  ]

  // 需要跳过的详细统计行（用于处理没有标题的情况）
  const DETAIL_LINE_PATTERNS = [
    /^•\s+返回\s+\d+\s+条记录/,
    /^•\s+包含\s+\d+\s+个字段/,
    /^•\s+\w+:\s+最小.*,\s+最大.*,\s+平均=/,
    /^\s*\w+:\s*最小.*,\s*最大.*/,
    /^\s*总记录数:/,
    /^\s*字段列表:/,
  ]

  for (const line of lines) {
    const trimmed = line.trim()
    const originalLine = line  // 保留原始行（包括缩进�?

    // 检查是否进入需要跳过的区块
    const isSectionStart = SECTION_START_PATTERNS.some(pattern => pattern.test(trimmed))
    if (isSectionStart) {
      skipSection = true
      continue
    }

    // 检查是否是详细统计行（独立判断，即使不在区块内也跳过）
    const isDetailLine = DETAIL_LINE_PATTERNS.some(pattern => pattern.test(trimmed))
    if (isDetailLine) {
      continue
    }

    // 遇到新的主要区块时停止跳过（�?📊 可视�?�?## 分析结论"等）
    if (skipSection) {
      if (/^(📊|##\s|###\s|^分析结论|^数据洞察)/.test(trimmed)) {
        skipSection = false
      } else {
        continue  // 跳过当前�?
      }
    }

    filteredLines.push(originalLine)
  }

  // 清理多余的空�?
  const result = filteredLines
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')  // 最多保留两个连续换�?
    .trim()

  return result
}

// 渲染步骤内容
function renderStepContent(step: ProcessingStep, outputFormat: 'markdown' | 'plain' = 'markdown') {
  if (!step.content_type || !step.content_data) return null

  switch (step.content_type) {
    case 'sql':
      if (step.content_data.sql) {
        // 步骤4（SQL生成）使用可折叠版本，默认展开
        if (step.step === 4) {
          return <SQLCodeRenderer sql={step.content_data.sql} defaultExpanded={true} />
        }
        return renderSQLCode(step.content_data.sql)
      }
      break
    case 'table':
      if (step.content_data.table) {
        return <TableDataRenderer table={step.content_data.table} />
      }
      break
    case 'chart':
      if (step.content_data.chart) {
        return renderChart(step.content_data.chart)
      }
      break
    case 'error':
      if (step.content_data.error) {
        const suggestion = step.content_data.suggestion
        return (
          <div className="mt-2 p-3 rounded-md bg-red-50 border border-red-200">
            <div className="flex items-center gap-2 mb-2">
              <XCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
              <span className="text-sm font-semibold text-red-700">SQL 执行错误</span>
            </div>
            <p className="text-xs text-red-700 mb-2 whitespace-pre-wrap">{step.content_data.error}</p>
            {suggestion && (
              <div className="mt-2 p-2 bg-red-100 rounded border border-red-300">
                <div className="text-xs font-medium text-red-800 mb-1 flex items-center gap-1">
                  💡 修复建议�?
                </div>
                <p className="text-xs text-red-700 whitespace-pre-wrap leading-relaxed">{suggestion}</p>
              </div>
            )}
          </div>
        )
      }
      break
    case 'text':
      if (step.content_data.text) {
        // 🔧 先应用详细分析过滤，再应�?Markdown 源码泄露过滤
        const detailFiltered = filterDetailedAnalysis(step.content_data.text)
        const filteredText = filterMarkdownLeaks(detailFiltered)
        return (
          <div className="mt-2 p-3 rounded-md bg-primary/5 border border-primary/20">
            <div className="text-xs font-medium text-primary mb-1">数据分析</div>
            <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">
              {filteredText}
            </p>
          </div>
        )
      }
      break
    case 'answer':
      if (step.content_data.text) {
        // 🔧 先应用详细分析过滤，再过滤硬编码示例内容
        const detailFiltered = filterDetailedAnalysis(step.content_data.text)
        const filteredText = filterExampleContent(detailFiltered)
        const isLoading = step.status === 'running'  // 新增：检测加载状�?

        return outputFormat === 'plain' ? (
          <PlainText
            content={filteredText}
            className="text-sm leading-relaxed"
            isLoading={isLoading}  // 新增：传递加载状�?
          />
        ) : (
          <Markdown content={filteredText} className="text-sm prose-base" />
        )
      }
      break
  }

  return null
}

// 🔧 新增：渲染步骤内容（带图表说明配对功能）
interface RenderStepContentOptions {
  step: ProcessingStep
  chartDescriptions: string[]
  chartIndex: number
  summary?: string  // 数据分析总结（非图表部分�?
  step6Table?: StepTableData | null  // 🔧 步骤6的表格数据，用于与图表合并显�?
  outputFormat?: 'markdown' | 'plain'
}

function renderStepContentWithDescriptions({ step, chartDescriptions, chartIndex, summary, step6Table, outputFormat = 'markdown' }: RenderStepContentOptions) {
  if (!step.content_type || !step.content_data) return null

  // 🔧 修改：任何图表类型的步骤都使�?renderVisualization 合并表格和图表（不再检查固定步骤号�?
  if (step.content_type === 'chart') {
    const description = chartDescriptions[chartIndex]

    // 🔧 修复：兼容两种数据格�?
    // 格式1: { content_data: { chart: { echarts_option: {...} } } }
    // 格式2: { content_data: { chart: {...} } }  (chart 本身就是 echarts_option)
    const stepLevelChart = (step as any).echarts_option
    const contentChart = step.content_data.chart

    // 🔧 关键修复：创建新空对象，避免循环引用
    const chartToRender: StepChartData = {}

    // 如果 contentChart 本身就是 ECharts 配置（有 title/xAxis/yAxis/series 等字段）
    // 使用浅拷贝将其包装到 echarts_option �?
    if (contentChart && !contentChart.echarts_option) {
      const hasEChartsFields = contentChart.title || contentChart.xAxis ||
                              contentChart.yAxis || contentChart.series ||
                              contentChart.legend || contentChart.grid ||
                              contentChart.tooltip || contentChart.dataset
      if (hasEChartsFields) {
        chartToRender.echarts_option = { ...contentChart }  // 浅拷贝打破循�?
      }
    }

    // 如果 contentChart 已经�?echarts_option，直接使�?
    if (contentChart?.echarts_option && !chartToRender.echarts_option) {
      chartToRender.echarts_option = contentChart.echarts_option
    }

    // 保留其他字段
    if (contentChart?.chart_image) chartToRender.chart_image = contentChart.chart_image
    if (contentChart?.chart_type) chartToRender.chart_type = contentChart.chart_type
    if (contentChart?.title) chartToRender.title = contentChart.title

    // 如果有步骤级别的 echarts_option，使用它
    if (stepLevelChart && !chartToRender.echarts_option) {
      chartToRender.echarts_option = stepLevelChart
    }

    if (chartToRender && (chartToRender.echarts_option || chartToRender.chart_image)) {
      // 使用新的 renderVisualization 函数合并图表和表�?
      return renderVisualization(chartToRender, step6Table || null, description)
    }
  }

  // 如果是数据分析步骤（text类型），显示总结部分（如果有�?
  // 优先检�?message/title 是否包含"数据分析"，兜底检查步骤号8（向后兼容）
  const isDataAnalysisStep = (
    (step.message === '数据分析' || step.title === '数据分析') ||
    step.step === 8
  ) && step.content_type === 'text'

  if (isDataAnalysisStep) {
    // 如果有总结（summary），显示总结；否则显示过滤后的原始文�?
    let textToShow = summary && summary.trim() ? summary : step.content_data.text

    // 🔧 应用详细分析过滤（如果使用的是原始文本）
    if (!summary || !summary.trim()) {
      textToShow = filterDetailedAnalysis(step.content_data.text || '')
    }

    // 🔧 数据时间跨度提示：若仅包含到 11 月且缺少 12 月，则补充说明
    const shouldAddDecemberNote = (() => {
      if (!step6Table || !step6Table.columns || !step6Table.rows) return false
      const monthColIndex = step6Table.columns.findIndex(col => {
        if (typeof col !== 'string') return false
        const lower = col.toLowerCase()
        return lower.includes('month') || col.includes('月份')
      })
      if (monthColIndex === -1) return false

      const parseMonth = (val: any): number | null => {
        if (val === undefined || val === null) return null
        if (typeof val === 'number') return val
        const str = String(val)
        const ym = str.match(/20\d{2}[-/](1[0-2]|0?[1-9])/)
        if (ym) return parseInt(ym[1], 10)
        const zh = str.match(/(1[0-2]|0?[1-9])\s*月/)
        if (zh) return parseInt(zh[1], 10)
        const pure = str.match(/^(1[0-2]|0?[1-9])$/)
        if (pure) return parseInt(pure[1], 10)
        return null
      }

      const monthValues = step6Table.rows
        .map(row => Array.isArray(row) ? row[monthColIndex] : (row as any)[step6Table.columns[monthColIndex]])
        .map(parseMonth)
        .filter((m): m is number => typeof m === 'number' && m >= 1 && m <= 12)

      if (monthValues.length === 0) return false
      const maxMonth = Math.max(...monthValues)
      return maxMonth === 11 && !monthValues.includes(12)
    })()

    if (shouldAddDecemberNote && textToShow && !textToShow.includes('12月数据暂缺')) {
      textToShow = `${textToShow.trim()}\n\n注：12月数据暂缺或尚未产生。`
    }

    if (!textToShow) return null

    return (
      <div className="mt-2 p-3 rounded-md bg-primary/5 border border-primary/20">
        <div className="text-xs font-medium text-primary mb-1">数据分析总结</div>
        {outputFormat === 'plain' ? (
          <PlainText content={textToShow} className="text-sm leading-relaxed" />
        ) : (
          <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">
            {textToShow}
          </p>
        )}
      </div>
    )
  }

  // 其他情况使用原有逻辑
  return renderStepContent(step, outputFormat)
}

export const ProcessingSteps = React.memo(function ProcessingSteps({ steps, className, defaultExpanded = false, outputFormat = 'markdown' }: ProcessingStepsProps) {
  const [isExpanded, setIsExpanded] = React.useState(defaultExpanded)

  // 当 props 变化时同步折叠状态，确保首屏默认收起
  React.useEffect(() => {
    setIsExpanded(defaultExpanded)
  }, [defaultExpanded])

  // 使用 useCallback 稳定回调函数
  const handleToggle = useCallback(() => {
    setIsExpanded(prev => !prev)
  }, [])

  // 🔧 第三次修复：详细的调试日�?

  if (!steps || steps.length === 0) return null

  // 🆕 过滤技术性步骤，只展示业务相关步�?
  const filteredSteps = useMemo(() => {
    const cleaned = steps.map((s, i) => sanitizeStep(s, s.step ?? i + 1))
    return mergeSimilarTableSteps(filterTechnicalSteps(cleaned))
  }, [steps])

  // 如果过滤后没有步骤，不渲�?
  if (filteredSteps.length === 0) return null

  // 🔧 新增：提取和配对图表说明
  // 1. 查找数据分析文本步骤（动态查找最后一�?content_type === 'text' 的步骤）
  // 优先查找 message/title 包含"数据分析"的步骤，否则查找最后一�?text 类型步骤
  const analysisStep = useMemo(
    () => {
      // 优先查找明确标记�?数据分析"的步�?
      const dataAnalysisStep = filteredSteps.find(s =>
        (s.message === '数据分析' || s.title === '数据分析') &&
        s.content_type === 'text' &&
        s.content_data?.text
      )
      if (dataAnalysisStep) return dataAnalysisStep

      // 兜底：查找最后一�?text 类型的步骤（通常是数据分析）
      const textSteps = filteredSteps.filter(s => s.content_type === 'text' && s.content_data?.text)
      return textSteps.length > 0 ? textSteps[textSteps.length - 1] : null
    },
    [filteredSteps]
  )
  const analysisText = analysisStep?.content_data?.text || ''

  // 2. 解析文本：提取总结和图表说�?
  const { summary, chartDescriptions } = useMemo(
    () => parseAnalysisText(analysisText),
    [analysisText]
  )

  // 🔧 修改：按内容类型提取表格数据（不再依赖固定步骤号�? 使用过滤后的步骤
  // 找到最后一个包含表格数据的步骤
  const tableDataStep = useMemo(() => {
    const tableSteps = filteredSteps.filter(s => s.content_type === 'table' && s.content_data?.table)
    console.log({
      allSteps: filteredSteps.map(s => ({ step: s.step, title: s.title, content_type: s.content_type, hasTable: !!s.content_data?.table })),
      tableSteps: tableSteps.length,
    })
    return tableSteps.length > 0 ? tableSteps[tableSteps.length - 1] : null
  }, [filteredSteps])
  const tableData = tableDataStep?.content_data?.table || null

  // 🔧 新增：如果没有找到表格数据但有步骤，打印所有步骤详情用于诊�?
  useEffect(() => {
    if (!tableData && filteredSteps.length > 0) {
      console.warn('[ProcessingSteps] ⚠️ 没有找到表格数据，所有步骤详�?', filteredSteps.map(s => ({
        step: s.step,
        title: s.title,
        content_type: s.content_type,
        has_content_data: !!s.content_data,
        content_data_keys: s.content_data ? Object.keys(s.content_data) : [],
        has_table: !!s.content_data?.table,
        has_chart: !!s.content_data?.chart,
      })))
    }
  }, [filteredSteps, tableData])

  // 🔧 修改：按内容类型检测是否有图表（不再依赖固定步骤号�? 使用过滤后的步骤
  const hasChart = useMemo(() => {
    return filteredSteps.some(s => s.content_type === 'chart' && s.content_data?.chart)
  }, [filteredSteps])

  // 3. 使用 useMemo 计算统计信息 - 使用过滤后的步骤
  const stats = useMemo(() => {
    const totalDuration = filteredSteps.reduce((sum, step) => sum + (step.duration || 0), 0)
    const completedSteps = filteredSteps.filter(s => s.status === 'completed').length
    const hasError = filteredSteps.some(s => s.status === 'error')
    const isRunning = filteredSteps.some(s => s.status === 'running')
    return { totalDuration, completedSteps, hasError, isRunning }
  }, [filteredSteps])

  // 4. 使用 useMemo 缓存容器类名 - DataLab 玻璃态风�?
  const containerClassName = useMemo(
    () => cn(
      'mt-4 rounded-2xl border overflow-hidden shadow-lg',
      stats.hasError ? 'border-red-400/30 bg-red-50/50 dark:bg-red-900/10' :
      stats.isRunning ? 'border-tiffany-400/50 bg-tiffany-50/50 dark:bg-tiffany-900/10' :
      'border-tiffany-500/30 bg-tiffany-50/30 dark:bg-tiffany-900/10',
      className
    ),
    [stats.hasError, stats.isRunning, className]
  )

  // 5. 使用 useMemo 缓存标题栏类�?- Tiffany 色系
  const headerClassName = useMemo(
    () => cn(
      'w-full px-4 py-3 flex items-center justify-between text-sm font-semibold',
      'hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors',
      stats.hasError ? 'text-red-600 dark:text-red-400' :
      stats.isRunning ? 'text-tiffany-600 dark:text-tiffany-400' :
      'text-tiffany-700 dark:text-tiffany-300'
    ),
    [stats.hasError, stats.isRunning]
  )

  return (
    <div className={containerClassName}>
      {/* 标题�?*/}
      <button
        onClick={handleToggle}
        className={headerClassName}
      >
        <div className="flex items-center gap-2">
          {stats.isRunning ? (
            <PulseIndicator variant="processing" size="md" />
          ) : stats.hasError ? (
            <XCircle className="w-4 h-4" />
          ) : (
            <CheckCircle2 className="w-4 h-4" />
          )}
          <span>
            Reasoning Process
            <span className="ml-2 text-xs font-normal opacity-75 font-mono">
              ({stats.completedSteps}/{filteredSteps.length} steps
              {stats.totalDuration > 0 && ` · ${formatDuration(stats.totalDuration)}`})
            </span>
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
      </button>

      {/* Tiffany 渐变进度�?- 更细更精�?*/}
      <div className="px-4 pb-3">
        <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden shadow-inner">
          <div
            className={cn(
              'h-full rounded-full transition-all duration-500 ease-out',
              stats.isRunning ? 'bg-gradient-to-r from-primary-300 via-primary-400 to-primary-500 animate-subtle-pulse shadow-glow' :
              stats.hasError ? 'bg-gradient-to-r from-red-400 to-red-500' :
              'bg-gradient-to-r from-primary-400 to-primary-600'
            )}
            style={{ width: `${(stats.completedSteps / filteredSteps.length) * 100}%` }}
          />
        </div>
        <div className="flex justify-between mt-1.5 text-[10px] text-slate-400 dark:text-slate-500">
          <span>{stats.completedSteps} / {filteredSteps.length} 步骤</span>
          <span className="font-mono">{Math.round((stats.completedSteps / filteredSteps.length) * 100)}%</span>
        </div>
      </div>

      {/* 步骤列表 */}
      {isExpanded && (
        <div className="px-3 pb-3 space-y-2">
          {(() => {
            // 🔧 �?map 外部维护图表索引计数�?
            let currentChartIndex = 0

            return filteredSteps.map((step, index) => {
              // 🔧 重构：支持多图表 - 使用 step�?+ chart_index 作为唯一key
              const chartIndexAttr = step.content_data?.chart?.chart_index
              const uniqueKey = chartIndexAttr !== undefined
                ? `step-${step.step}-chart-${chartIndexAttr}`
                : `step-${step.step || index}`

              // 🔧 修改：按内容类型计算图表索引（不再依赖固定步骤号�?
              let thisChartIndex = currentChartIndex
              if (step.content_type === 'chart') {
                thisChartIndex = currentChartIndex
                currentChartIndex++  // 为下一个图表递增索引
              }

              // 🔧 修改：按内容类型判断，如果有表格数据且有图表，则跳过表格步骤的独立渲�?
              const shouldSkipTableStep = step.content_type === 'table' && hasChart

              return (
                <div
                  key={uniqueKey}
                  className={cn(
                    'rounded-lg border p-2.5 transition-all duration-200 hover:shadow-sm',
                    getStatusColor(step.status),
                    step.status === 'running' && 'ring-1 ring-primary-300/50 shadow-glow'
                  )}
                >
                <div className="flex items-start gap-2">
                  {/* 步骤图标 */}
                  <div className="mt-0.5">
                    {getStepIcon(step.step, step.title, step.status)}
                  </div>

                  {/* 步骤内容 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                        {step.step}. {step.title}
                      </span>
                      {step.duration && step.status === 'completed' && (
                        <span className="text-xs text-muted-foreground">
                          {formatDuration(step.duration)}
                        </span>
                      )}
                    </div>

                    {step.description && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {step.description}
                      </p>
                    )}

                    {/* 🔧 实时内容预览（当步骤正在运行时），支持打字机光标效果 */}
                    {/* 🔧 修改：步�?即使�?completed 状态也显示 content_preview（用于显示临时内容） */}
                    {(step.status === 'running' || (step.step === 0 && step.content_preview)) && step.content_preview && (
                      <div className="mt-2 p-2 rounded-md bg-primary/10 border border-primary/30">
                        <div className="flex items-center gap-1.5 mb-1">
                          {step.status === 'running' ? (
                            <Loader2 className="w-3 h-3 animate-spin text-primary" />
                          ) : (
                            <CheckCircle2 className="w-3 h-3 text-green-500" />
                          )}
                          <span className="text-xs font-medium text-primary">
                            {step.message === '数据分析' || step.title === '数据分析' ? '正在生成分析...' : '正在生成...'}
                          </span>
                        </div>
                        <div className={cn(
                          "text-xs text-foreground whitespace-pre-wrap break-words max-h-48 overflow-y-auto",
                          (step.message === '数据分析' || step.title === '数据分析' || step.step === 8) ? "font-normal leading-relaxed" : "font-mono"
                        )}>
                          {filterDetailedAnalysis(step.content_preview || '')}
                          {/* 🔧 打字机光标效果（仅在流式输出时显示） */}
                          {step.streaming && (
                            <span className="inline-block w-0.5 h-4 bg-primary animate-pulse ml-0.5 align-middle" />
                          )}
                        </div>
                      </div>
                    )}

                    {/* 🔧 渲染步骤内容（使用配对版本的函数�?*/}
                    {/* 🔧 步骤6表格在有步骤7图表时跳过（会合并到步骤7显示�?*/}
                    {!shouldSkipTableStep && renderStepContentWithDescriptions({
                      step,
                      chartDescriptions,
                      chartIndex: thisChartIndex,
                      summary,
                      step6Table: tableData,
                      outputFormat
                    })}

                  {/* 详情（如SQL内容�?- 仅当没有content_type时显�?*/}
                  {step.details && !step.content_type && (
                    <details className="mt-1">
                      <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                        查看详情
                      </summary>
                      <pre className="mt-1 p-2 bg-white dark:bg-slate-800/50 rounded text-xs overflow-x-auto max-h-96 overflow-y-auto">
                        <code>{step.details}</code>
                      </pre>
                    </details>
                  )}
                  </div>
                </div>
              </div>
            )
            })
          })()}
        </div>
      )}
    </div>
  )
})




