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

import { ScrollArea } from '@/components/ui/scroll-area'
import { Markdown } from '@/components/ui/markdown'
import { PlainText } from '@/components/ui/plain-text'
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
import React, { useCallback, useMemo } from 'react'

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
    return <Loader2 className={cn(iconClass, 'animate-spin text-blue-500')} />
  }
  if (status === 'error') {
    return <XCircle className={cn(iconClass, 'text-red-500')} />
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
  return <Clock className={cn(iconClass, 'text-gray-400')} />
}

// 获取步骤的状态颜色
function getStatusColor(status: ProcessingStep['status']) {
  switch (status) {
    case 'completed':
      return 'border-green-200 bg-green-50'
    case 'running':
      return 'border-blue-200 bg-blue-50'
    case 'error':
      return 'border-red-200 bg-red-50'
    default:
      return 'border-gray-200 bg-gray-50 dark:bg-slate-800'
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
    <div className="mt-2 rounded-md bg-slate-100 overflow-hidden border border-slate-200">
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between px-3 py-1.5 bg-slate-200 border-b border-slate-300 hover:bg-slate-300 transition-colors"
      >
        <span className="text-xs font-medium text-slate-700 flex items-center gap-2">
          <Code2 className="w-3.5 h-3.5 text-indigo-600" />
          SQL
          <span className="text-slate-500 font-normal">
            ({lineCount} 行, {charCount} 字符)
          </span>
        </span>
        {isExpanded ? (
          <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
        )}
      </button>
      {isExpanded && (
        <pre className="p-3 overflow-x-auto max-h-64 overflow-y-auto bg-white dark:bg-slate-800">
          <code className="text-xs text-slate-800 font-mono">{sql}</code>
        </pre>
      )}
    </div>
  )
})

// 渲染SQL代码块（简单版本，用于非步骤4）
function renderSQLCode(sql: string) {
  return (
    <div className="mt-2 rounded-md bg-slate-100 overflow-hidden border border-slate-200">
      <div className="flex items-center justify-between px-3 py-1.5 bg-slate-200 border-b border-slate-300">
        <span className="text-xs font-medium text-slate-700 flex items-center gap-2">
          <Code2 className="w-3.5 h-3.5 text-indigo-600" />
          SQL
        </span>
      </div>
      <pre className="p-3 overflow-x-auto bg-white dark:bg-slate-800">
        <code className="text-xs text-slate-800 font-mono">{sql}</code>
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

  // 默认显示更多行（50行），列数不限
  const DEFAULT_MAX_ROWS = 50
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
    <div className="mt-2 rounded-md border border-blue-200 overflow-hidden bg-white dark:bg-slate-800">
      <div className="flex items-center justify-between px-3 py-1.5 bg-blue-50 border-b border-blue-200">
        <span className="text-xs font-medium text-blue-700">可视化数据</span>
        <span className="text-xs text-blue-500">
          表格 · {table.row_count} 行 × {table.columns.length} 列
          {hasMoreColumns && ` (显示前${MAX_COLUMNS}列)`}
        </span>
      </div>
      <ScrollArea>
        <table className="w-full text-xs border-collapse">
          <thead className="bg-gray-50 dark:bg-slate-800 sticky top-0 z-10">
            <tr>
              {limitedColumns.map(col => (
                <th
                  key={col}
                  className="px-3 py-2 border-b text-left font-medium text-gray-700 whitespace-nowrap bg-gray-50 dark:bg-slate-800"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, rowIndex) => (
              <tr key={rowIndex} className="odd:bg-white dark:bg-slate-800 even:bg-gray-50 dark:bg-slate-800/60 hover:bg-blue-50/30">
                {limitedColumns.map(col => (
                  <td
                    key={col}
                    className="px-3 py-1.5 border-b text-gray-800 align-top"
                  >
                    <span className="break-words whitespace-pre-wrap">
                      {row[col] !== undefined && row[col] !== null
                        ? String(row[col])
                        : ''}
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollArea>
      {/* 展开/收起按钮 */}
      {(hasMoreRows || hasMoreColumns) && (
        <div className="px-3 py-1.5 bg-blue-50 border-t border-blue-200 flex items-center justify-between">
          <span className="text-xs text-blue-600">
            {isExpanded
              ? `显示全部 ${table.row_count} 行`
              : `共 ${table.row_count} 行，当前显示前 ${Math.min(DEFAULT_MAX_ROWS, table.row_count)} 行`
            }
            {hasMoreColumns && ` · 仅展示前 ${MAX_COLUMNS} 列`}
          </span>
          {hasMoreRows && (
            <button
              onClick={handleToggle}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium"
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

  // 查找第一个图表标题的位置（如"第一个图表"、"图表1"等）
  const chartTitlePattern = /(?:第\s*[一二三四五六七八九十\d]+\s*个?图表[:：]?\s*)|(?:图表\s*[一二三四五六七八九十\d]+[:：]?\s*)/i
  const firstChartIndex = text.search(chartTitlePattern)

  // 如果找到图表标题，分割文本
  if (firstChartIndex > 0) {
    const summaryPart = text.substring(0, firstChartIndex).trim()
    const chartPart = text.substring(firstChartIndex)

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

  // 没有找到图表标题，返回整个文本作为总结
  return { summary: text, chartDescriptions: [] }
}

/**
 * 规范化 ECharts 配置，确保纵坐标标签完整显示
 * 自动添加合理的 grid 配置和坐标轴边距
 */
function normalizeEChartsOption(option: any): any {
  if (!option || typeof option !== 'object') return option

  // 深拷贝避免修改原始配置
  const normalized = JSON.parse(JSON.stringify(option))

  // 如果已有 grid 配置，确保 left 值足够大
  if (normalized.grid) {
    if (Array.isArray(normalized.grid)) {
      normalized.grid.forEach((g: any) => {
        if (!g.left || g.left === '3%' || g.left === '10%') {
          g.left = '15%'
        }
        if (!g.right || g.right === '4%' || g.right === '10%') {
          g.right = '5%'
        }
        if (!g.bottom || g.bottom === '3%') {
          g.bottom = '10%'
        }
        if (!g.containLabel) {
          g.containLabel = true
        }
      })
    } else {
      if (!normalized.grid.left || normalized.grid.left === '3%' || normalized.grid.left === '10%') {
        normalized.grid.left = '15%'
      }
      if (!normalized.grid.right || normalized.grid.right === '4%' || normalized.grid.right === '10%') {
        normalized.grid.right = '5%'
      }
      if (!normalized.grid.bottom || normalized.grid.bottom === '3%') {
        normalized.grid.bottom = '10%'
      }
      if (!normalized.grid.containLabel) {
        normalized.grid.containLabel = true
      }
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
  // 图表说明文字（显示在图表上方）
  const descriptionElement = description && description.trim() && (
    <div className="mb-2 p-3 rounded-md bg-blue-50 border border-blue-200">
      <div className="text-xs font-medium text-blue-700 mb-1">图表说明</div>
      <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
        {description}
      </p>
    </div>
  )

  if (chart.echarts_option) {
    // 规范化配置，确保坐标轴标签完整显示
    const normalizedOption = normalizeEChartsOption(chart.echarts_option)

    return (
      <>
        {descriptionElement}
        <div className="mt-2 rounded-md border border-blue-200 overflow-hidden bg-white dark:bg-slate-800">
          <div className="flex items-center justify-between px-3 py-1.5 bg-blue-50 border-b border-blue-200">
            <span className="text-xs font-medium text-blue-700">数据可视化</span>
            {chart.chart_type && (
              <span className="text-xs text-blue-500 uppercase">{chart.chart_type}</span>
            )}
          </div>
          <div className="p-2">
            <ReactECharts
              option={normalizedOption}
              style={{ width: '100%', minHeight: '400px' }}
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
        <div className="mt-2 rounded-md border border-blue-200 overflow-hidden bg-white dark:bg-slate-800">
          <div className="flex items-center justify-between px-3 py-1.5 bg-blue-50 border-b border-blue-200">
            <span className="text-xs font-medium text-blue-700">数据可视化</span>
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

  return null
}

// 🔧 新增：将图表和表格合并渲染到同一个"可视化数据"区域
function renderVisualization(
  chart: StepChartData | null,
  table: StepTableData | null,
  description?: string
) {
  if (!chart && !table) return null

  const descriptionElement = description && description.trim() && (
    <div className="mb-2 p-3 rounded-md bg-blue-50 border border-blue-200">
      <div className="text-xs font-medium text-blue-700 mb-1">图表说明</div>
      <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">{description}</p>
    </div>
  )

  const chartTypeLabel = chart?.chart_type || ''

  const chartElement = chart?.echarts_option ? (
    <div className="p-2">
      <ReactECharts
        option={normalizeEChartsOption(chart.echarts_option)}
        style={{ width: '100%', minHeight: '400px' }}
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
    <div className="border-t border-blue-200">
      <div className="flex items-center justify-between px-3 py-1.5 bg-blue-50/50">
        <span className="text-xs font-medium text-blue-600">数据明细</span>
        <span className="text-xs text-blue-500">{table.row_count} 行 × {table.columns.length} 列</span>
      </div>
      <ScrollArea>
        <table className="w-full text-xs border-collapse">
          <thead className="bg-gray-50 dark:bg-slate-800 sticky top-0 z-10">
            <tr>
              {table.columns.slice(0, 10).map(col => (
                <th key={col} className="px-3 py-2 border-b text-left font-medium text-gray-700 whitespace-nowrap bg-gray-50 dark:bg-slate-800">{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.slice(0, 20).map((row, rowIndex) => (
              <tr key={rowIndex} className="odd:bg-white dark:bg-slate-800 even:bg-gray-50 dark:bg-slate-800/60 hover:bg-blue-50/30">
                {table.columns.slice(0, 10).map(col => (
                  <td key={col} className="px-3 py-1.5 border-b text-gray-800 align-top">
                    <span className="break-words whitespace-pre-wrap">
                      {row[col] !== undefined && row[col] !== null ? String(row[col]) : ''}
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollArea>
      {table.row_count > 20 && (
        <div className="px-3 py-1.5 bg-blue-50/50 text-center">
          <span className="text-xs text-blue-600">共 {table.row_count} 行，显示前 20 行</span>
        </div>
      )}
    </div>
  ) : null

  return (
    <>
      {descriptionElement}
      <div className="mt-2 rounded-md border border-blue-200 overflow-hidden bg-white dark:bg-slate-800">
        <div className="flex items-center justify-between px-3 py-1.5 bg-blue-50 border-b border-blue-200">
          <span className="text-xs font-medium text-blue-700">可视化数据</span>
          <span className="text-xs text-blue-500">
            {chartTypeLabel}{chartTypeLabel && table && ' · '}{table && '表格'}
          </span>
        </div>
        {chartElement}
        {tableElement}
      </div>
    </>
  )
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
        return (
          <div className="mt-2 p-2 rounded-md bg-red-50 border border-red-200">
            <p className="text-xs text-red-700">{step.content_data.error}</p>
          </div>
        )
      }
      break
    case 'text':
      if (step.content_data.text) {
        return (
          <div className="mt-2 p-3 rounded-md bg-blue-50 border border-blue-200">
            <div className="text-xs font-medium text-blue-700 mb-1">数据分析</div>
            <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
              {step.content_data.text}
            </p>
          </div>
        )
      }
      break
    case 'answer':
      if (step.content_data.text) {
        return (
          <div className="mt-2 p-3 rounded-md bg-emerald-50 border border-emerald-200">
            <div className="text-xs font-medium text-emerald-700 mb-1">AI 回答</div>
            {outputFormat === 'plain' ? (
              <PlainText content={step.content_data.text} className="text-sm leading-relaxed" />
            ) : (
              <Markdown content={step.content_data.text} className="text-sm prose-base" />
            )}
          </div>
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
  if (step.content_type === 'chart' && step.content_data.chart) {
    const description = chartDescriptions[chartIndex]
    // 使用新的 renderVisualization 函数合并图表和表格
    return renderVisualization(step.content_data.chart, step6Table || null, description)
  }

  // 如果是步骤8（text类型的数据分析），显示总结部分（如果有）
  if (step.step === 8 && step.content_type === 'text') {
    // 如果有总结（summary），显示总结；否则显示原始文本
    const textToShow = summary && summary.trim() ? summary : step.content_data.text
    if (!textToShow) return null

    return (
      <div className="mt-2 p-3 rounded-md bg-blue-50 border border-blue-200">
        <div className="text-xs font-medium text-blue-700 mb-1">数据分析总结</div>
        {outputFormat === 'plain' ? (
          <PlainText content={textToShow} className="text-sm leading-relaxed" />
        ) : (
          <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
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

  // 调试日志
  console.log('[ProcessingSteps] 渲染，steps数量:', steps?.length, steps)

  if (!steps || steps.length === 0) return null

  // 🔧 新增：提取和配对图表说明
  // 1. 查找步骤8（数据分析文本）
  const step8 = useMemo(
    () => steps.find(s => s.step === 8 && s.content_type === 'text' && s.content_data?.text),
    [steps]
  )
  const analysisText = step8?.content_data?.text || ''

  // 2. 解析文本：提取总结和图表说明
  const { summary, chartDescriptions } = useMemo(
    () => parseAnalysisText(analysisText),
    [analysisText]
  )

  // 🔧 修改：按内容类型提取表格数据（不再依赖固定步骤号）
  // 找到最后一个包含表格数据的步骤
  const tableDataStep = useMemo(() => {
    const tableSteps = steps.filter(s => s.content_type === 'table' && s.content_data?.table)
    return tableSteps.length > 0 ? tableSteps[tableSteps.length - 1] : null
  }, [steps])
  const tableData = tableDataStep?.content_data?.table || null

  // 🔧 修改：按内容类型检测是否有图表（不再依赖固定步骤号）
  const hasChart = useMemo(() => {
    return steps.some(s => s.content_type === 'chart' && s.content_data?.chart)
  }, [steps])

  // 3. 使用 useMemo 计算统计信息
  const stats = useMemo(() => {
    const totalDuration = steps.reduce((sum, step) => sum + (step.duration || 0), 0)
    const completedSteps = steps.filter(s => s.status === 'completed').length
    const hasError = steps.some(s => s.status === 'error')
    const isRunning = steps.some(s => s.status === 'running')
    return { totalDuration, completedSteps, hasError, isRunning }
  }, [steps])

  // 4. 使用 useMemo 缓存容器类名
  const containerClassName = useMemo(
    () => cn(
      'mt-3 rounded-lg border overflow-hidden',
      stats.hasError ? 'border-red-200 bg-red-50/50' :
      stats.isRunning ? 'border-blue-200 bg-blue-50/50' :
      'border-emerald-200 bg-emerald-50/50',
      className
    ),
    [stats.hasError, stats.isRunning, className]
  )

  // 5. 使用 useMemo 缓存标题栏类名
  const headerClassName = useMemo(
    () => cn(
      'w-full px-3 py-2 flex items-center justify-between text-sm font-medium',
      'hover:bg-black/5 transition-colors',
      stats.hasError ? 'text-red-800' :
      stats.isRunning ? 'text-blue-800' :
      'text-emerald-800'
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
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : stats.hasError ? (
            <XCircle className="w-4 h-4" />
          ) : (
            <CheckCircle2 className="w-4 h-4" />
          )}
          <span>
            AI 推理过程 
            <span className="ml-2 text-xs font-normal opacity-75">
              ({stats.completedSteps}/{steps.length} 步骤完成
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

      {/* 进度条 */}
      <div className="px-3 pb-2">
        <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all duration-500 ease-out',
              stats.isRunning ? 'bg-blue-500 animate-pulse' :
              stats.hasError ? 'bg-red-500' :
              'bg-emerald-500'
            )}
            style={{ width: `${(stats.completedSteps / steps.length) * 100}%` }}
          />
        </div>
        <div className="flex justify-between mt-1 text-xs text-gray-600">
          <span>{stats.completedSteps} / {steps.length} 步骤</span>
          <span>{Math.round((stats.completedSteps / steps.length) * 100)}%</span>
        </div>
      </div>

      {/* 步骤列表 */}
      {isExpanded && (
        <div className="px-3 pb-3 space-y-2">
          {(() => {
            // 🔧 在 map 外部维护图表索引计数器
            let currentChartIndex = 0

            return steps.map((step, index) => {
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
                    'rounded-md border p-2 transition-all duration-300',
                    getStatusColor(step.status)
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
                      <span className={cn(
                        'text-xs font-medium',
                        step.status === 'completed' ? 'text-green-700' :
                        step.status === 'running' ? 'text-blue-700' :
                        step.status === 'error' ? 'text-red-700' :
                        'text-gray-600'
                      )}>
                        {step.step}. {step.title}
                      </span>
                      {step.duration && step.status === 'completed' && (
                        <span className="text-xs text-gray-500">
                          {formatDuration(step.duration)}
                        </span>
                      )}
                    </div>

                    {step.description && (
                      <p className="text-xs text-gray-600 mt-0.5">
                        {step.description}
                      </p>
                    )}

                    {/* 🔧 实时内容预览（当步骤正在运行时），支持打字机光标效果 */}
                    {/* 🔧 修改：步骤0即使在 completed 状态也显示 content_preview（用于显示临时内容） */}
                    {(step.status === 'running' || (step.step === 0 && step.content_preview)) && step.content_preview && (
                      <div className="mt-2 p-2 rounded-md bg-blue-50 border border-blue-200">
                        <div className="flex items-center gap-1.5 mb-1">
                          {step.status === 'running' ? (
                            <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
                          ) : (
                            <CheckCircle2 className="w-3 h-3 text-green-500" />
                          )}
                          <span className="text-xs font-medium text-blue-700">
                            {step.step === 8 ? '正在生成分析...' : '正在生成...'}
                          </span>
                        </div>
                        <div className={cn(
                          "text-xs text-gray-700 whitespace-pre-wrap break-words max-h-48 overflow-y-auto",
                          step.step === 8 ? "font-normal leading-relaxed" : "font-mono"
                        )}>
                          {step.content_preview}
                          {/* 🔧 打字机光标效果（仅在流式输出时显示） */}
                          {step.streaming && (
                            <span className="inline-block w-0.5 h-4 bg-blue-500 animate-pulse ml-0.5 align-middle" />
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
                      <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
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

