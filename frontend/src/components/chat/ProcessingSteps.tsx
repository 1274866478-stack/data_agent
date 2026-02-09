/**
 * # ProcessingSteps AI处理步骤展示组件
 *
 * ## [MODULE]
 * **文件名**: ProcessingSteps.tsx
 * **职责**: 可视化展示AI推理和SQL生成的各个处理步骤，支持折叠展开和耗时统计
 * **作者**: Data Agent Team
 * **版本**: 1.1.0
 *
 * ## [INPUT]
 * - **steps**: ProcessingStep[] - 处理步骤数组
 * - **className**: string (可选) - 自定义样式类名
 * - **defaultExpanded**: boolean (可选) - 默认是否展开，默认true
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 折叠卡片式的步骤列表或null
 * - **副作用**: 无副作用
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [@/lib/utils.ts](../../lib/utils.ts) - 工具函数（cn）
 * - [lucide-react](https://lucide.dev) - 图标库（12种步骤图标）
 * - [@/types/chat.ts](../../types/chat.ts) - ProcessingStep类型定义
 *
 * **下游依赖**:
 * - 无直接下游组件
 *
 * **调用方**:
 * - [./MessageList.tsx](./MessageList.tsx) - 消息列表中展示AI推理过程
 *
 * ## [STATE]
 * - **isExpanded**: boolean - 步骤列表展开/折叠状态
 *
 * ## [SIDE-EFFECTS]
 * - 根据步骤状态自动选择对应图标（6步AI流程）
 * - 自动计算总耗时和完成进度
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
    MessageSquare, // 新增：内容生成
    Shield, // 新增：思考/上下文检索
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

// 根据步骤编号和标题返回对应的图标
function getStepIcon(step: number, title: string, status: ProcessingStep['status']) {
  const iconClass = 'w-4 h-4'

  // 根据状态返回状态图标
  if (status === 'running') {
    return <Loader2 className={cn(iconClass, 'animate-spin text-primary')} />
  }
  if (status === 'error') {
    return <XCircle className={cn(iconClass, 'text-destructive')} />
  }
  if (status === 'completed') {
    // 🔧 新增：步骤 0 特殊处理（理解问题/思考规划阶段）
    if (step === 0) {
      return <Brain className={cn(iconClass, 'text-green-500')} />
    }
    // 智能匹配：基于标题关键词（优先级最高，支持不同场景）
    // 意图理解类
    if (title.includes('意图') || title.includes('理解') || title.includes('用户问题')) {
      return <MessageSquare className={cn(iconClass, 'text-green-500')} />
    }
    // 上下文检索/思考类
    if (title.includes('检索') || title.includes('上下文') || title.includes('知识')) {
      return <Brain className={cn(iconClass, 'text-green-500')} />
    }
    // Schema/数据库类
    if (title.includes('Schema') || title.includes('数据库') || title.includes('表结构')) {
      return <TableProperties className={cn(iconClass, 'text-green-500')} />
    }
    // 策略/Prompt构建类
    if (title.includes('策略') || title.includes('Prompt') || title.includes('构建')) {
      return <Wand2 className={cn(iconClass, 'text-green-500')} />
    }
    // SQL生成类
    if (title.includes('SQL') && (title.includes('生成') || title.includes('构建'))) {
      return <Code2 className={cn(iconClass, 'text-green-500')} />
    }
    // 内容生成类（非SQL）
    if (title.includes('生成') || title.includes('回复') || title.includes('内容')) {
      return <Sparkles className={cn(iconClass, 'text-green-500')} />
    }
    // 安全检查类
    if (title.includes('安全') || title.includes('检查') || title.includes('合规')) {
      return <Shield className={cn(iconClass, 'text-green-500')} />
    }
    // 优化/输出完成类
    if (title.includes('优化') || title.includes('输出') || title.includes('完成') || title.includes('最终')) {
      return <CheckCircle2 className={cn(iconClass, 'text-green-500')} />
    }
    // SQL提取/代码类
    if (title.includes('提取') || title.includes('代码')) {
      return <FileCode className={cn(iconClass, 'text-green-500')} />
    }
    // 执行/查询类
    if (title.includes('执行') || title.includes('查询') || title.includes('运行')) {
      return <Zap className={cn(iconClass, 'text-green-500')} />
    }
    // 图表可视化类
    if (title.includes('图表') || title.includes('可视化') || title.includes('展示')) {
      return <BarChart3 className={cn(iconClass, 'text-green-500')} />
    }
    // 数据源类
    if (title.includes('数据源') || title.includes('连接')) {
      return <Database className={cn(iconClass, 'text-green-500')} />
    }

    // 回退到步骤编号映射（0-8步Agent SQL流程）
    switch (step) {
      case 0: return <Brain className={cn(iconClass, 'text-green-500')} />  // 🔧 新增：理解问题/思考规划
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

// 获取步骤的状态颜色 - DataLab Tiffany 色系
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

// 渲染SQL代码块（简单版本，用于非步骤4）- DataLab 深色风格
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

  // 🔧 默认只显示前5行，避免占用过多空间（从50改为5）
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
        <span className="text-xs font-medium text-primary">可视化数据</span>
        <span className="text-xs text-primary/70">
          表格 · {table.row_count} 行 × {table.columns.length} 列
          {hasMoreColumns && ` (显示前${MAX_COLUMNS}列)`}
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
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, rowIndex) => {
              // 🔧 修复：支持两种 rows 格式（数组格式和对象格式）
              const isArrayRow = Array.isArray(row)
              
              return (
                <tr key={rowIndex} className="odd:bg-card even:bg-muted hover:bg-primary/5">
                  {limitedColumns.map((col, colIndex) => {
                    const cellValue = isArrayRow ? row[colIndex] : row[col]
                    return (
                      <td
                        key={col}
                        className="px-3 py-1.5 border-b text-foreground align-top"
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
              : `共 ${table.row_count} 行，当前显示前 ${Math.min(DEFAULT_MAX_ROWS, table.row_count)} 行`
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
 * 解析数据分析文本，提取总结和图表说明
 * 返回: { summary: 总结部分, chartDescriptions: 图表说明数组 }
 */
function parseAnalysisText(text: string): { summary: string; chartDescriptions: string[] } {
  if (!text) return { summary: '', chartDescriptions: [] }

  // 🔧 先过滤详细分析模块（数据概览、数值统计、数据预览）
  const filteredText = filterDetailedAnalysis(text)

  // 查找第一个图表标题的位置（如"第一个图表"、"图表1"等）
  const chartTitlePattern = /(?:第\s*[一二三四五六七八九十\d]+\s*个?图表[:：]?\s*)|(?:图表\s*[一二三四五六七八九十\d]+[:：]?\s*)/i
  const firstChartIndex = filteredText.search(chartTitlePattern)

  // 如果找到图表标题，分割文本
  if (firstChartIndex > 0) {
    const summaryPart = filteredText.substring(0, firstChartIndex).trim()
    const chartPart = filteredText.substring(firstChartIndex)

    // 解析图表说明
    const chartDescriptions: string[] = []
    const parts = chartPart.split(chartTitlePattern)

    // 找到所有图表标题
    const chartTitles = chartPart.match(/(?:第\s*[一二三四五六七八九十\d]+\s*个?图表[:：]?\s*[^。\n]*)|(?:图表\s*[一二三四五六七八九十\d]+[:：]?\s*[^。\n]*)/gi)

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
 * 移除 **、*、# 等 Markdown 格式标记
 */
function cleanMarkdownSymbols(text: string): string {
  if (!text || typeof text !== 'string') return text
  return text
    .replace(/\*\*/g, '')        // 移除加粗标记
    .replace(/\*/g, '')          // 移除斜体标记
    .replace(/^#+\s*/, '')       // 移除标题级标记
    .trim()
}

/**
 * 安全深拷贝，避免循环引用导致的 JSON 序列化失败
 * 使用 structuredClone 或递归浅拷贝作为后备方案
 */
function safeDeepClone<T>(obj: T): T {
  if (!obj || typeof obj !== 'object') return obj

  // 优先使用 structuredClone（现代浏览器支持）
  if (typeof structuredClone !== 'undefined') {
    try {
      return structuredClone(obj)
    } catch {
      // 如果 structuredClone 失败，使用后备方案
    }
  }

  // 后备方案：递归浅拷贝（处理常见对象结构）
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
 * 规范化 ECharts 配置，确保纵坐标标签完整显示
 * 自动添加合理的 grid 配置和坐标轴边距
 */
function normalizeEChartsOption(option: any): any {
  if (!option || typeof option !== 'object') return option

  // 深拷贝避免修改原始配置，使用安全拷贝方法
  const normalized = safeDeepClone(option)

  // 🔧 新增：清理标题中的 Markdown 符号
  if (normalized.title?.text) {
    normalized.title.text = cleanMarkdownSymbols(normalized.title.text)
  }

  // 修复：如果有 grid 配置，强制修正可能导致截断的值
  if (normalized.grid) {
    if (Array.isArray(normalized.grid)) {
      normalized.grid.forEach((g: any) => {
        // 强制设置合理值，防止图表被截断
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
      })
    } else if (normalized.yAxis.axisLabel && normalized.yAxis.axisLabel.margin === undefined) {
      normalized.yAxis.axisLabel.margin = 20
    }
  }

  // 确保 xAxis 也有合理配置
  if (normalized.xAxis) {
    if (Array.isArray(normalized.xAxis)) {
      normalized.xAxis.forEach((axis: any) => {
        if (axis.axisLabel && axis.axisLabel.margin === undefined) {
          axis.axisLabel.margin = 15
        }
      })
    } else if (normalized.xAxis.axisLabel && normalized.xAxis.axisLabel.margin === undefined) {
      normalized.xAxis.axisLabel.margin = 15
    }
  }

  return normalized
}

// 渲染图表
function renderChart(chart: StepChartData, description?: string) {
  // 🔧 新增：调试日志
  console.log('[ProcessingSteps] renderChart 调用，chart 数据:', {
    has_echarts_option: !!chart.echarts_option,
    has_chart_image: !!chart.chart_image,
    chart_type: chart.chart_type,
    title: chart.title,
  })

  // 图表说明文字（显示在图表上方）
  const descriptionElement = description && description.trim() && (
    <div className="mb-2 p-3 rounded-md bg-primary/5 border border-primary/20">
      <div className="text-xs font-medium text-primary mb-1">图表说明</div>
      <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">
        {description}
      </p>
    </div>
  )

  if (chart.echarts_option) {
    console.log('[ProcessingSteps] ✅ 使用 echarts_option 渲染图表')
    // 规范化配置，确保坐标轴标签完整显示
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

  // 🔧 计划修复4：图表配置存在但渲染失败时显示错误提示
  if (chart && !chart.echarts_option && !chart.chart_image) {
    console.warn('[ProcessingSteps] ⚠️ 图表配置存在但无可渲染内容:', chart)
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

// 🔧 新增：将图表和表格合并渲染到同一个"可视化数据"区域
function renderVisualization(
  chart: StepChartData | null,
  table: StepTableData | null,
  description?: string
) {
  // 🔧 新增：调试日志
  console.log('[ProcessingSteps] renderVisualization 调用:', {
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
        <span className="text-xs text-primary/70">{table.row_count} 行 × {table.columns.length} 列</span>
      </div>
      <ScrollArea>
        <table className="w-full text-xs border-collapse">
          <thead className="bg-muted sticky top-0 z-10">
            <tr>
              {table.columns.slice(0, 10).map(col => (
                <th key={col} className="px-3 py-2 border-b border-border text-left font-medium text-foreground whitespace-nowrap bg-muted">{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.slice(0, 20).map((row, rowIndex) => {
              // 🔧 修复：支持两种 rows 格式
              // 格式1: 数组格式 [[val1, val2], ...] - 后端 execute_query 返回的格式
              // 格式2: 对象格式 [{col1: val1, col2: val2}, ...] - 某些其他来源的格式
              const isArrayRow = Array.isArray(row)
              
              return (
                <tr key={rowIndex} className="odd:bg-card even:bg-muted hover:bg-primary/5">
                  {table.columns.slice(0, 10).map((col, colIndex) => {
                    // 如果 row 是数组，使用索引访问；如果是对象，使用列名访问
                    const cellValue = isArrayRow ? row[colIndex] : row[col]
                    return (
                      <td key={col} className="px-3 py-1.5 border-b border-border text-foreground align-top">
                        <span className="break-words whitespace-pre-wrap">
                          {cellValue !== undefined && cellValue !== null ? String(cellValue) : ''}
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
        {/* 先显示表格数据，再显示图表 */}
        {tableElement}
        {chartElementWithTitle}
      </div>
    </>
  )
}

/**
 * 🆕 过滤技术性步骤，只展示业务相关步骤
 *
 * 需要隐藏的技术性步骤（内部实现细节）：
 * - list_tables: 获取表列表（元数据操作）
 * - get_schema: 获取表结构（元数据操作）
 * - connect_db: 连接数据库（基础设施）
 * - validate_query: SQL验证（内部校验）
 * - 调用工具: 所有工具调用步骤
 *
 * 更新：扩展隐藏关键词列表，包含更多技术细节步骤
 */
function filterTechnicalSteps(steps: ProcessingStep[]): ProcessingStep[] {
  // 需要隐藏的步骤标题关键词（这些是技术实现细节，用户不需要看到）
  const HIDDEN_STEP_KEYWORDS = [
    // 原有关键词
    'list_tables',
    'get_schema',
    'get_recommended_tables',
    '获取表列表',
    '获取表结构',
    '连接数据库',
    'SQL验证',
    'validate_query',
    '元数据获取',
    'Schema检索',
    // 🆕 新增：根据截图实际标题（计划修复1）
    '列出数据库表',           // 截图中的实际标题
    '获取数据库结构',         // 截图中的实际标题
    // 🆕 新增：过滤重复的技术步骤
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

  // 🆕 需要去重的步骤关键词（相同标题只保留最后一个 completed 状态）
  const DUPLICATE_STEP_KEYWORDS = [
    'SQL生成中',
    '生成SQL中',
    '执行查询中',
    '数据分析中',
    '处理中',
    '生成中',
    '查询结果',  // 🆕 计划修复3：合并重复的"查询结果"步骤
  ]

  // 第一步：过滤掉技术性步骤
  let filtered = steps.filter(step => {
    const titleLower = (step.title || '').toLowerCase()

    // 🔧 计划修复5：明确保留图表和可视化相关步骤
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
      console.log('[ProcessingSteps] 🔧 保留图表步骤:', step.title)
      return true
    }

    // 🆕 计划修复2：通用过滤 - 所有以"调用工具:"开头的步骤都隐藏
    if (titleLower.startsWith('调用工具:') || titleLower.startsWith('调用工具：')) {
      return false
    }

    // 检查是否是隐藏的技术性步骤
    const isHidden = HIDDEN_STEP_KEYWORDS.some(keyword =>
      titleLower.includes(keyword.toLowerCase())
    )

    return !isHidden
  })

  // 🆕 第二步：去重逻辑 - 相同标题的步骤只保留最后一个（特别是 completed 状态的）
  const stepMap = new Map<string, ProcessingStep>()

  for (const step of filtered) {
    const title = step.title || ''
    // 检查是否是需要去重的步骤类型
    const isDuplicateType = DUPLICATE_STEP_KEYWORDS.some(keyword =>
      title.includes(keyword)
    )

    if (isDuplicateType) {
      // 对于需要去重的步骤，总是用新的覆盖旧的（保留最后一个）
      // 🆕 计划修复3：对于"查询结果"步骤，优先保留有数据的
      const existing = stepMap.get(title)
      if (title.includes('查询结果')) {
        const existingRowCount = existing?.content_data?.table?.row_count ?? 0
        const currentRowCount = step?.content_data?.table?.row_count ?? 0
        const existingHasData = existingRowCount > 0
        const currentHasData = currentRowCount > 0
        if (currentHasData || !existingHasData) {
          stepMap.set(title, step)
        }
      } else {
        stepMap.set(title, step)
      }
    } else {
      // 对于不需要去重的步骤，使用 step + title 作为唯一键
      const uniqueKey = `${step.step}_${title}`
      stepMap.set(uniqueKey, step)
    }
  }

  // 转换回数组
  filtered = Array.from(stepMap.values())

  // 第三步：按步骤号排序
  filtered.sort((a, b) => a.step - b.step)

  // 重新编号步骤，使其连续
  return filtered.map((step, index) => ({
    ...step,
    step: index + 1, // 重新编号从1开始
  }))
}

/**
 * 过滤硬编码的示例内容（通过特征指纹识别）
 * 只过滤包含特定硬编码数值的段落
 */
function filterExampleContent(text: string): string {
  // 硬编码示例内容的特征指纹（这些数值不会出现在真实数据中）
  const EXAMPLE_FINGERPRINTS = [
    '11.53亿元',      // 硬编码的年度销售额
    '9,610万元',      // 硬编码的月均销售额
    '约1.10亿元',     // 硬编码的峰值
  ]

  // 按段落分割
  const paragraphs = text.split(/\n\n+/)

  // 只过滤包含特征指纹的段落，其他段落保留
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

  // 源码泄露检测模式
  const LEAK_PATTERNS = [
    /^#{2,}\s+\w+.*#{2,}\s*[📊📈📉💼🔍]/,  // 多级标题 + emoji
    /^#{2,}\s+202[0-9]年.*#{2,}/,             // 年份标题组合
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
 * 需要过滤的区块：
 * - 📈 数据概览
 * - 🔢 数值统计
 * - 📋 数据预览
 * - 返回 X 条记录
 * - 包含 X 个字段
 * - 各字段统计信息
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
    /^•\s+\w+:\s+最小=.*,\s+最大=.*,\s+平均=/,
    /^\s*\w+:\s*最小=.*,\s*最大=/,
    /^\s*总记录数:/,
    /^\s*字段列表:/,
  ]

  for (const line of lines) {
    const trimmed = line.trim()
    const originalLine = line  // 保留原始行（包括缩进）

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

    // 遇到新的主要区块时停止跳过（如"📊 可视化"、"## 分析结论"等）
    if (skipSection) {
      if (/^(📊|##\s|###\s|^分析结论|^数据洞察)/.test(trimmed)) {
        skipSection = false
      } else {
        continue  // 跳过当前行
      }
    }

    filteredLines.push(originalLine)
  }

  // 清理多余的空行
  const result = filteredLines
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')  // 最多保留两个连续换行
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
                  💡 修复建议：
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
        // 🔧 先应用详细分析过滤，再应用 Markdown 源码泄露过滤
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
        const isLoading = step.status === 'running'  // 新增：检测加载状态

        return outputFormat === 'plain' ? (
          <PlainText
            content={filteredText}
            className="text-sm leading-relaxed"
            isLoading={isLoading}  // 新增：传递加载状态
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
  summary?: string  // 数据分析总结（非图表部分）
  step6Table?: StepTableData | null  // 🔧 步骤6的表格数据，用于与图表合并显示
  outputFormat?: 'markdown' | 'plain'
}

function renderStepContentWithDescriptions({ step, chartDescriptions, chartIndex, summary, step6Table, outputFormat = 'markdown' }: RenderStepContentOptions) {
  if (!step.content_type || !step.content_data) return null

  // 🔧 修改：任何图表类型的步骤都使用 renderVisualization 合并表格和图表（不再检查固定步骤号）
  if (step.content_type === 'chart') {
    const description = chartDescriptions[chartIndex]

    // 🔧 修复：兼容两种数据格式
    // 格式1: { content_data: { chart: { echarts_option: {...} } } }
    // 格式2: { content_data: { chart: {...} } }  (chart 本身就是 echarts_option)
    const stepLevelChart = (step as any).echarts_option
    const contentChart = step.content_data.chart

    // 🔧 关键修复：创建新空对象，避免循环引用
    const chartToRender: StepChartData = {}

    // 如果 contentChart 本身就是 ECharts 配置（有 title/xAxis/yAxis/series 等字段）
    // 使用浅拷贝将其包装到 echarts_option 中
    if (contentChart && !contentChart.echarts_option) {
      const hasEChartsFields = contentChart.title || contentChart.xAxis ||
                              contentChart.yAxis || contentChart.series ||
                              contentChart.legend || contentChart.grid ||
                              contentChart.tooltip || contentChart.dataset
      if (hasEChartsFields) {
        chartToRender.echarts_option = { ...contentChart }  // 浅拷贝打破循环
      }
    }

    // 如果 contentChart 已经有 echarts_option，直接使用
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
      // 使用新的 renderVisualization 函数合并图表和表格
      return renderVisualization(chartToRender, step6Table || null, description)
    }
  }

  // 如果是数据分析步骤（text类型），显示总结部分（如果有）
  // 优先检查 message/title 是否包含"数据分析"，兜底检查步骤号8（向后兼容）
  const isDataAnalysisStep = (
    (step.message === '数据分析' || step.title === '数据分析') ||
    step.step === 8
  ) && step.content_type === 'text'

  if (isDataAnalysisStep) {
    // 如果有总结（summary），显示总结；否则显示过滤后的原始文本
    let textToShow = summary && summary.trim() ? summary : step.content_data.text

    // 🔧 应用详细分析过滤（如果使用的是原始文本）
    if (!summary || !summary.trim()) {
      textToShow = filterDetailedAnalysis(step.content_data.text || '')
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

export const ProcessingSteps = React.memo(function ProcessingSteps({ steps, className, defaultExpanded = true, outputFormat = 'markdown' }: ProcessingStepsProps) {
  const [isExpanded, setIsExpanded] = React.useState(defaultExpanded)

  // 使用 useCallback 稳定回调函数
  const handleToggle = useCallback(() => {
    setIsExpanded(prev => !prev)
  }, [])

  // 🔧 第三次修复：详细的调试日志
  console.log('[ProcessingSteps] 🔧 渲染，steps:', steps?.map(s => ({ step: s.step, status: s.status, title: s.title?.substring(0, 20) })))
  console.log('[ProcessingSteps] 🔧 completedSteps:', steps?.filter(s => s.status === 'completed').length, '/', steps?.length)

  if (!steps || steps.length === 0) return null

  // 🆕 过滤技术性步骤，只展示业务相关步骤
  const filteredSteps = useMemo(() => filterTechnicalSteps(steps), [steps])

  // 如果过滤后没有步骤，不渲染
  if (filteredSteps.length === 0) return null

  // 🔧 新增：提取和配对图表说明
  // 1. 查找数据分析文本步骤（动态查找最后一个 content_type === 'text' 的步骤）
  // 优先查找 message/title 包含"数据分析"的步骤，否则查找最后一个 text 类型步骤
  const analysisStep = useMemo(
    () => {
      // 优先查找明确标记为"数据分析"的步骤
      const dataAnalysisStep = filteredSteps.find(s =>
        (s.message === '数据分析' || s.title === '数据分析') &&
        s.content_type === 'text' &&
        s.content_data?.text
      )
      if (dataAnalysisStep) return dataAnalysisStep

      // 兜底：查找最后一个 text 类型的步骤（通常是数据分析）
      const textSteps = filteredSteps.filter(s => s.content_type === 'text' && s.content_data?.text)
      return textSteps.length > 0 ? textSteps[textSteps.length - 1] : null
    },
    [filteredSteps]
  )
  const analysisText = analysisStep?.content_data?.text || ''

  // 2. 解析文本：提取总结和图表说明
  const { summary, chartDescriptions } = useMemo(
    () => parseAnalysisText(analysisText),
    [analysisText]
  )

  // 🔧 修改：按内容类型提取表格数据（不再依赖固定步骤号）- 使用过滤后的步骤
  // 找到最后一个包含表格数据的步骤
  const tableDataStep = useMemo(() => {
    const tableSteps = filteredSteps.filter(s => s.content_type === 'table' && s.content_data?.table)
    console.log('[ProcessingSteps] 查找表格步骤:', {
      allSteps: filteredSteps.map(s => ({ step: s.step, title: s.title, content_type: s.content_type, hasTable: !!s.content_data?.table })),
      tableSteps: tableSteps.length,
    })
    return tableSteps.length > 0 ? tableSteps[tableSteps.length - 1] : null
  }, [filteredSteps])
  const tableData = tableDataStep?.content_data?.table || null
  console.log('[ProcessingSteps] 提取的表格数据:', tableData ? `${tableData.row_count} 行 x ${tableData.columns?.length} 列` : 'null')

  // 🔧 新增：如果没有找到表格数据但有步骤，打印所有步骤详情用于诊断
  useEffect(() => {
    if (!tableData && filteredSteps.length > 0) {
      console.warn('[ProcessingSteps] ⚠️ 没有找到表格数据，所有步骤详情:', filteredSteps.map(s => ({
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

  // 🔧 修改：按内容类型检测是否有图表（不再依赖固定步骤号）- 使用过滤后的步骤
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

  // 4. 使用 useMemo 缓存容器类名 - DataLab 玻璃态风格
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

  // 5. 使用 useMemo 缓存标题栏类名 - Tiffany 色系
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
      {/* 标题栏 */}
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
              {stats.totalDuration > 0 && ` • ${formatDuration(stats.totalDuration)}`})
            </span>
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
      </button>

      {/* Tiffany 渐变进度条 - 更细更精致 */}
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
            // 🔧 在 map 外部维护图表索引计数器
            let currentChartIndex = 0

            return filteredSteps.map((step, index) => {
              // 🔧 重构：支持多图表 - 使用 step号 + chart_index 作为唯一key
              const chartIndexAttr = step.content_data?.chart?.chart_index
              const uniqueKey = chartIndexAttr !== undefined
                ? `step-${step.step}-chart-${chartIndexAttr}`
                : `step-${step.step || index}`

              // 🔧 修改：按内容类型计算图表索引（不再依赖固定步骤号）
              let thisChartIndex = currentChartIndex
              if (step.content_type === 'chart') {
                thisChartIndex = currentChartIndex
                currentChartIndex++  // 为下一个图表递增索引
              }

              // 🔧 修改：按内容类型判断，如果有表格数据且有图表，则跳过表格步骤的独立渲染
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
                    {/* 🔧 修改：步骤0即使在 completed 状态也显示 content_preview（用于显示临时内容） */}
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

                    {/* 🔧 渲染步骤内容（使用配对版本的函数） */}
                    {/* 🔧 步骤6表格在有步骤7图表时跳过（会合并到步骤7显示） */}
                    {!shouldSkipTableStep && renderStepContentWithDescriptions({
                      step,
                      chartDescriptions,
                      chartIndex: thisChartIndex,
                      summary,
                      step6Table: tableData,
                      outputFormat
                    })}

                  {/* 详情（如SQL内容） - 仅当没有content_type时显示 */}
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

