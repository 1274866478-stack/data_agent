/**
 * # ProcessingSteps AI处理步骤展示组件
 *
 * ## [MODULE]
 * **文件名**: ProcessingSteps.tsx
 * **职责**: 可视化展示AI推理和SQL生成的各个处理步骤，支持折叠展开和耗时统计
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
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
 */
'use client'

import React from 'react'
import { cn } from '@/lib/utils'
import {
  Database,
  Search,
  FileCode,
  Play,
  CheckCircle2,
  XCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  Clock,
  MessageSquare,
  TableProperties,
  Wand2,
  Code2,
  Zap,
  BarChart3,
  Table,
  Brain,      // 新增：思考/上下文检索
  Sparkles,   // 新增：内容生成
  Shield,     // 新增：安全检查
} from 'lucide-react'
import { ProcessingStep, StepContentType, StepContentData, StepTableData, StepChartData } from '@/types/chat'
import ReactECharts from 'echarts-for-react'
import { ScrollArea } from '@/components/ui/scroll-area'

interface ProcessingStepsProps {
  steps: ProcessingStep[]
  className?: string
  defaultExpanded?: boolean
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
      return 'border-gray-200 bg-gray-50'
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

function SQLCodeRenderer({ sql, defaultExpanded = false }: SQLCodeRendererProps) {
  const [isExpanded, setIsExpanded] = React.useState(defaultExpanded)

  // 计算SQL行数
  const lineCount = sql.split('\n').length
  const charCount = sql.length

  return (
    <div className="mt-2 rounded-md bg-gray-900 overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-1.5 bg-gray-800 border-b border-gray-700 hover:bg-gray-700 transition-colors"
      >
        <span className="text-xs font-medium text-gray-300 flex items-center gap-2">
          <Code2 className="w-3.5 h-3.5" />
          SQL
          <span className="text-gray-500 font-normal">
            ({lineCount} 行, {charCount} 字符)
          </span>
        </span>
        {isExpanded ? (
          <ChevronUp className="w-3.5 h-3.5 text-gray-400" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
        )}
      </button>
      {isExpanded && (
        <pre className="p-3 overflow-x-auto max-h-64 overflow-y-auto">
          <code className="text-xs text-green-400 font-mono">{sql}</code>
        </pre>
      )}
    </div>
  )
}

// 渲染SQL代码块（简单版本，用于非步骤4）
function renderSQLCode(sql: string) {
  return (
    <div className="mt-2 rounded-md bg-gray-900 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-800 border-b border-gray-700">
        <span className="text-xs font-medium text-gray-300">SQL</span>
      </div>
      <pre className="p-3 overflow-x-auto">
        <code className="text-xs text-green-400 font-mono">{sql}</code>
      </pre>
    </div>
  )
}

// 渲染数据表格（组件形式，支持状态管理）
interface TableDataRendererProps {
  table: StepTableData
}

function TableDataRenderer({ table }: TableDataRendererProps) {
  const [isExpanded, setIsExpanded] = React.useState(false)

  // 默认显示更多行（50行），列数不限
  const DEFAULT_MAX_ROWS = 50
  const MAX_COLUMNS = 10  // 增加列数限制
  const limitedColumns = table.columns.slice(0, MAX_COLUMNS)

  // 根据展开状态决定显示行数
  const displayRows = isExpanded ? table.rows : table.rows.slice(0, DEFAULT_MAX_ROWS)
  const hasMoreRows = table.row_count > DEFAULT_MAX_ROWS
  const hasMoreColumns = table.columns.length > MAX_COLUMNS

  return (
    <div className="mt-2 rounded-md border border-gray-200 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-50 border-b border-gray-200">
        <span className="text-xs font-medium text-gray-700">查询结果</span>
        <span className="text-xs text-gray-500">
          {table.row_count} 行 × {table.columns.length} 列
          {hasMoreColumns && ` (显示前${MAX_COLUMNS}列)`}
        </span>
      </div>
      <ScrollArea>
        <table className="w-full text-xs border-collapse">
          <thead className="bg-gray-50 sticky top-0 z-10">
            <tr>
              {limitedColumns.map(col => (
                <th
                  key={col}
                  className="px-3 py-2 border-b text-left font-medium text-gray-700 whitespace-nowrap bg-gray-50"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, rowIndex) => (
              <tr key={rowIndex} className="odd:bg-white even:bg-gray-50/60 hover:bg-blue-50/30">
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
        <div className="px-3 py-1.5 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
          <span className="text-xs text-gray-500">
            {isExpanded
              ? `显示全部 ${table.row_count} 行`
              : `共 ${table.row_count} 行，当前显示前 ${Math.min(DEFAULT_MAX_ROWS, table.row_count)} 行`
            }
            {hasMoreColumns && ` · 仅展示前 ${MAX_COLUMNS} 列`}
          </span>
          {hasMoreRows && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium"
            >
              {isExpanded ? '收起' : '展开全部'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// 渲染图表
function renderChart(chart: StepChartData) {
  if (chart.echarts_option) {
    return (
      <div className="mt-2 rounded-md border border-blue-200 overflow-hidden bg-white">
        <div className="flex items-center justify-between px-3 py-1.5 bg-blue-50 border-b border-blue-200">
          <span className="text-xs font-medium text-blue-700">数据可视化</span>
          {chart.chart_type && (
            <span className="text-xs text-blue-500 uppercase">{chart.chart_type}</span>
          )}
        </div>
        <div className="p-2">
          <ReactECharts
            option={chart.echarts_option}
            style={{ width: '100%', minHeight: '400px' }}
            opts={{ renderer: 'canvas' }}
            notMerge={false}
            lazyUpdate={false}
          />
        </div>
      </div>
    )
  }

  if (chart.chart_image) {
    return (
      <div className="mt-2 rounded-md border border-blue-200 overflow-hidden bg-white">
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
    )
  }

  return null
}

// 渲染步骤内容
function renderStepContent(step: ProcessingStep) {
  if (!step.content_type || !step.content_data) return null

  switch (step.content_type) {
    case 'sql':
      if (step.content_data.sql) {
        // 步骤4（SQL生成）使用可折叠版本
        if (step.step === 4) {
          return <SQLCodeRenderer sql={step.content_data.sql} defaultExpanded={false} />
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
  }

  return null
}

export function ProcessingSteps({ steps, className, defaultExpanded = true }: ProcessingStepsProps) {
  const [isExpanded, setIsExpanded] = React.useState(defaultExpanded)
  
  // 调试日志
  console.log('[ProcessingSteps] 渲染，steps数量:', steps?.length, steps)
  
  if (!steps || steps.length === 0) return null

  // 计算总耗时
  const totalDuration = steps.reduce((sum, step) => sum + (step.duration || 0), 0)
  const completedSteps = steps.filter(s => s.status === 'completed').length
  const hasError = steps.some(s => s.status === 'error')
  const isRunning = steps.some(s => s.status === 'running')

  return (
    <div className={cn(
      'mt-3 rounded-lg border overflow-hidden',
      hasError ? 'border-red-200 bg-red-50/50' : 
      isRunning ? 'border-blue-200 bg-blue-50/50' : 
      'border-emerald-200 bg-emerald-50/50',
      className
    )}>
      {/* 标题栏 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'w-full px-3 py-2 flex items-center justify-between text-sm font-medium',
          'hover:bg-black/5 transition-colors',
          hasError ? 'text-red-800' : 
          isRunning ? 'text-blue-800' : 
          'text-emerald-800'
        )}
      >
        <div className="flex items-center gap-2">
          {isRunning ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : hasError ? (
            <XCircle className="w-4 h-4" />
          ) : (
            <CheckCircle2 className="w-4 h-4" />
          )}
          <span>
            AI 推理过程 
            <span className="ml-2 text-xs font-normal opacity-75">
              ({completedSteps}/{steps.length} 步骤完成
              {totalDuration > 0 && ` · ${formatDuration(totalDuration)}`})
            </span>
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
      </button>

      {/* 步骤列表 */}
      {isExpanded && (
        <div className="px-3 pb-3 space-y-2">
          {steps.map((step, index) => {
            // 🔧 重构：支持多图表 - 使用 step号 + chart_index 作为唯一key
            const chartIndex = step.content_data?.chart?.chart_index
            const uniqueKey = chartIndex !== undefined
              ? `step-${step.step}-chart-${chartIndex}`
              : `step-${step.step || index}`

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
                  {step.status === 'running' && step.content_preview && (
                    <div className="mt-2 p-2 rounded-md bg-blue-50 border border-blue-200">
                      <div className="flex items-center gap-1.5 mb-1">
                        <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
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

                  {/* 渲染步骤内容（SQL、表格、图表） */}
                  {renderStepContent(step)}

                  {/* 详情（如SQL内容） - 仅当没有content_type时显示 */}
                  {step.details && !step.content_type && (
                    <details className="mt-1">
                      <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                        查看详情
                      </summary>
                      <pre className="mt-1 p-2 bg-white/50 rounded text-xs overflow-x-auto max-h-96 overflow-y-auto">
                        <code>{step.details}</code>
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            </div>
          )})}  {/* 🔧 闭合 map 回调函数的 return 和函数体 */}
        </div>
      )}
    </div>
  )
}

