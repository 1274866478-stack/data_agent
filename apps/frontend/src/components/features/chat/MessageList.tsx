/**
 * # [MESSAGE_LIST] 消息列表组件
 *
 * ## [MODULE]
 * **文件�?*: MessageList.tsx
 * **职责**: 渲染聊天消息列表，支持Markdown渲染、图表显示、流式响应、高亮定位、错误提示、停止生成和图表合并
 *
 * ## [INPUT]
 * Props:
 * - **className?: string** - 可选的CSS类名
 * - **messages: ChatMessage[]** - 要显示的消息数组
 * - **highlightedMessageId?: string | null** - 需要高亮显示的消息ID
 *
 * ## [OUTPUT]
 * UI组件:
 * - **消息气泡**: 用户消息（蓝色右侧）和助手消息（灰色左侧�?
 * - **Markdown渲染**: 支持富文本格式、代码块、列表等
 * - **图表显示**: 解析并渲染ECharts图表配置（从[CHART_START]标记或metadata�?
 * - **图表合并**: 多图表选择与合并功能（选中�?个时显示合并操作栏）
 * - **结构化结�?*: 显示表格数据和图表（通过ChatQueryResultView�?
 * - **推理步骤**: 显示AI处理步骤（通过ProcessingSteps�?
 * - **错误提示**: 显示数据源连接失败警告（AlertTriangle图标�?
 * - **工具调用状�?*: 显示工具调用成功/失败状�?
 * - **停止生成按钮**: 流式响应时显示停止按�?
 * - **高亮效果**: 搜索结果高亮显示�?秒后自动清除�?
 * - **Ref方法**: scrollToMessage, scrollToBottom
 *
 * **上游依赖**:
 * - [../../store/chatStore.ts](../../store/chatStore.ts) - 聊天状态管理Store（图表选择/合并状态）
 * - [./EChartsRenderer.tsx](./EChartsRenderer.tsx) - ECharts图表渲染�?
 * - [./ChatQueryResultView.tsx](./ChatQueryResultView.tsx) - 查询结果视图
 * - [./ProcessingSteps.tsx](./ProcessingSteps.tsx) - 处理步骤显示
 * - [../ui/markdown.tsx](../ui/markdown.tsx) - Markdown渲染�?
 * - [../ui/card.tsx](../ui/card.tsx) - 卡片组件
 * - [../ui/checkbox.tsx](../ui/checkbox.tsx) - Checkbox组件
 * - lucide-react - 图标�?(User, Bot, AlertTriangle, Square, Check, X)
 *
 * **下游依赖**:
 * - [./ChatInterface.tsx](./ChatInterface.tsx) - 聊天界面（调用此组件的ref方法�?
 *
 * **调用�?*:
 * - [ChatInterface.tsx](./ChatInterface.tsx) - 聊天主界�?
 *
 * ## [STATE]
 * - **Ref管理**: messagesEndRef（滚动到底部�? messageRefs（消息位置映射）
 * - **本地高亮**: localHighlightId（本地高亮状态，3秒后清除�?
 * - **流式状�?*: streamingStatus, streamingMessageId（从chatStore读取�?
 * - **图表选择**: selectedCharts, toggleChartSelection, clearChartSelection, mergeCharts, isMergingCharts
 *
 * ## [SIDE-EFFECTS]
 * - 自动滚动到底部（messages变化时）
 * - 高亮消息自动滚动（highlightedMessageId变化时）
 * - 定时器操作（高亮3秒后自动清除�?
 * - 调用stopStreaming（用户点击停止生成按钮）
 * - 调用toggleChartSelection（用户点击图表checkbox�?
 * - 调用clearChartSelection（用户点击清除选择按钮�?
 * - 调用mergeCharts（用户点击合并选中图表按钮�?
 * - console日志输出（调试图表解析和processing_steps�?
 */

'use client'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'
import type { ChatMessage } from '@/types/components/chat'
import { useChatListState } from '@/hooks/useChatListState'
import { AlertTriangle, Bot, Check, Square, User, X } from 'lucide-react'
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { ProcessingSteps } from './ProcessingSteps'
import { Badge } from '@/components/ui/badge'

/**
 * 从消息内容中移除图表标记和Markdown表格，避免与推理步骤中的内容重复显示
 * - 如果是 AI 推理步骤，移除所有内容（所有内容都在 ProcessingSteps 中展示）
 * - 图表已通过 ProcessingSteps 的步骤展示
 * - 表格已通过 ProcessingSteps 的步骤展示
 * - 数据分析已通过 ProcessingSteps 的步骤展示
 */
function removeChartMarkers(content: string, hasProcessingSteps: boolean): string {
  // 如果是 AI 推理步骤，移除所有内容（避免重复）
  if (hasProcessingSteps) {
    return ''
  }

  let cleaned = content

  // 🔧 修复：改进 [CHART_START]...[CHART_END] 标记移除逻辑
  // 使用非贪婪匹配 + 跨行匹配，确保捕获所有变体
  cleaned = cleaned.replace(/\[CHART_START\][\s\S]*?\[CHART_END\]/gi, '')

  // 🔧 新增：过滤详细数据分析模块（数据概览、数值统计、数据预览）
  const lines = cleaned.split('\n')
  const filteredLines: string[] = []
  let skipSection = false

  // 需要跳过的区块起始标记
  const SECTION_START_PATTERNS = [
    /^📈\s*\*\*数据概览\*\*/,
    /^\*\*📈\s*数据概览\*\*/,
    /^\*\*🔢\s*数值统计\*\*/,
    /^\*\*📋\s*数据预览\*\*/,
    /^数据概览/,
    /^数值统计/,
    /^数据预览/,
  ]

  // 需要跳过的详细统计行
  const DETAIL_LINE_PATTERNS = [
    /^•\s+返回\s+\d+\s+条记录/,
    /^•\s+包含\s+\d+\s+个字段/,
    /^•\s+\w+:\s+最小.*,\s+最大.*,\s+平均=/,
    /^\s*\w+:\s*最小.*,\s*最大.*/,
    /^\s*总记录数:/,
    /^\s*字段列表:/,
  ]

  // 🔧 增强的源码泄露检测模式
  const LEAK_PATTERNS = [
    /^#{2,}\s+\w+.*#{2,}\s*[📊📈📉💼🔍]/,  // 多级标题 + emoji
    /^#{2,}\s+202[0-9].*#{2,}/,             // 年份标题组合
    /^#{2,}.*###.*$/,                        // 任意 ##...### 模式
    /^(##|###)\s+.*\1\s+/,                   // 重复标题标记
    /^(##|###)\s.*(数据概览|趋势分析|📊)/,   // 特征词汇组合
  ]

  let inTable = false
  let tableLineCount = 0

  for (const line of lines) {
    const trimmed = line.trim()

    // 🔧 优先检查是否进入需要跳过的详细分析区块
    const isSectionStart = SECTION_START_PATTERNS.some(pattern => pattern.test(trimmed))
    if (isSectionStart) {
      skipSection = true
      continue
    }

    // 检查是否是详细统计�?
    const isDetailLine = DETAIL_LINE_PATTERNS.some(pattern => pattern.test(trimmed))
    if (isDetailLine) {
      continue
    }

    // 遇到新的主要区块时停止跳�?
    if (skipSection) {
      if (/^(📊|##\s|###\s|^分析结论|^数据洞察)/.test(trimmed)) {
        skipSection = false
      } else {
        continue
      }
    }

    // 检查源码泄�?
    if (LEAK_PATTERNS.some(pattern => pattern.test(trimmed))) {
      continue
    }

    // 检查是否是表格�?
    const isTableRow = trimmed.startsWith('|') && trimmed.endsWith('|')
    const isSeparator = /^\|[\s\-:|]+\|$/.test(trimmed)

    if (isTableRow) {
      if (!inTable) {
        inTable = true
        tableLineCount = 0
      }
      tableLineCount++
      continue
    } else {
      if (inTable && tableLineCount > 0) {
        inTable = false
        tableLineCount = 0
      }
      filteredLines.push(line)
    }
  }

  cleaned = filteredLines.join('\n')

  // 清理多余的空行和残留标记
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n')
  cleaned = cleaned.replace(/\[CHART_START\]|\[CHART_END\]/gi, '')

  return cleaned.trim()
}

// 轻量关键词提取（前端备用）
const extractFocusKeyword = (query: string): string | null => {
  if (!query) return null
  const patterns = [
    /([\u4e00-\u9fa5A-Za-z0-9]+)\s*(?:卖|销量|销售|卖得|卖的|卖得怎么样|卖得如何)/,
    /([\u4e00-\u9fa5A-Za-z0-9]+)\s*(?:排行|排名|top)/,
  ]
  for (const pat of patterns) {
    const m = query.match(pat)
    if (m) return m[1]
  }
  return null
}

const filterStepTable = (step: any, keyword: string | null) => {
  if (!keyword || !step?.content_data?.table) return step
  const { columns, rows, row_count } = step.content_data.table
  const kw = keyword.toLowerCase()
  const hit = (row: any) => {
    if (Array.isArray(row)) {
      const obj = Object.fromEntries(columns.map((c: string, i: number) => [c, row[i]]))
      return Object.values(obj).some(v => String(v ?? '').toLowerCase().includes(kw))
    }
    return Object.values(row as Record<string, any>).some(v => String(v ?? '').toLowerCase().includes(kw))
  }
  const filtered = rows?.filter(hit) ?? []
  const table = {
    ...step.content_data.table,
    rows: filtered.length > 0 ? filtered : rows,
    row_count: filtered.length > 0 ? filtered.length : row_count,
  }
  return { ...step, content_data: { ...step.content_data, table } }
}

function InsightBanner({ insight }: { insight?: string }) {
  if (!insight) return null
  return (
    <Card className="bg-amber-50 border-amber-200 text-amber-900 mb-2">
      <CardContent className="py-3 flex items-start gap-2">
        <Badge variant="secondary" className="bg-amber-100 text-amber-900">洞察</Badge>
        <p className="text-sm leading-relaxed">{insight}</p>
      </CardContent>
    </Card>
  )
}

interface MessageListProps {
  className?: string
  messages: ChatMessage[]
  highlightedMessageId?: string | null
}

export interface MessageListRef {
  scrollToMessage: (messageId: string) => void
  scrollToBottom: () => void
}

export const MessageList = forwardRef<MessageListRef, MessageListProps>(
  function MessageList({ className, messages, highlightedMessageId }, ref) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messageRefs = useRef<Map<string, HTMLDivElement>>(new Map())
  const [localHighlightId, setLocalHighlightId] = useState<string | null>(null)
  
  // 获取流式状态和图表合并状�?
  const { streamingStatus, streamingMessageId, stopStreaming, selectedCharts, toggleChartSelection, clearChartSelection, mergeCharts, isMergingCharts } = useChatListState()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const scrollToMessage = (messageId: string) => {
    const messageEl = messageRefs.current.get(messageId)
    if (messageEl) {
      messageEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
      // 设置本地高亮状态，3秒后自动清除
      setLocalHighlightId(messageId)
      setTimeout(() => setLocalHighlightId(null), 3000)
    }
  }

  // 暴露方法给父组件
  useImperativeHandle(ref, () => ({
    scrollToMessage,
    scrollToBottom
  }))

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 当外部高亮ID变化时，滚动到对应消�?
  useEffect(() => {
    if (highlightedMessageId) {
      scrollToMessage(highlightedMessageId)
    }
  }, [highlightedMessageId])

  const formatTimestamp = (date: Date) => {
    return new Date(date).toLocaleTimeString()
  }

  // 检查消息是否包含图表（通过 processing_steps 中的 echarts_option�?
  const hasChart = (message: ChatMessage): boolean => {
    if (!message.metadata?.processing_steps) return false
    return message.metadata.processing_steps.some(step => step.echart_option !== undefined)
  }

  // 处理图表合并
  const handleMergeCharts = async () => {
    if (selectedCharts.length < 2) return
    await mergeCharts(selectedCharts)
  }

  // 判断消息是否高亮
  const isHighlighted = (messageId: string) =>
    messageId === highlightedMessageId || messageId === localHighlightId

  return (
    <div className={cn('space-y-4 p-4', className)}>
      {/* 图表合并操作栏（选中两个及以上时显示）*/}
      {selectedCharts.length >= 2 && (
        <div className="sticky top-0 z-10 bg-primary/10 border border-primary/30 rounded-lg p-3 flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2">
            <Check className="w-4 h-4 text-primary" />
            <span className="text-sm text-primary">
              已选中 <strong>{selectedCharts.length}</strong> 个图表
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => clearChartSelection()}
            >
              <X className="w-3 h-3 mr-1" />
              清除选择
            </Button>
            <Button
              size="sm"
              className="h-8 text-xs"
              onClick={handleMergeCharts}
              disabled={isMergingCharts}
            >
              {isMergingCharts ? (
                <>
                  <span className="w-3 h-3 mr-1 animate-spin">⏳</span>
                  合并中...
                </>
              ) : (
                <>
                  <Check className="w-3 h-3 mr-1" />
                  合并选中图表
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {messages.map((message) => {
        return (
          <div
            key={message.id}
            ref={(el) => {
              if (el) messageRefs.current.set(message.id, el)
            }}
            className={cn(
              'flex gap-3 group transition-all duration-300',
              message.role === 'user' ? 'flex-row-reverse' : 'flex-row',
              isHighlighted(message.id) && 'ring-2 ring-primary ring-offset-2 rounded-lg bg-primary/5'
            )}
          >
            {/* 头像 */}
            <div className={cn(
              'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
              message.role === 'user'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground'
            )}>
              {message.role === 'user' ? (
                <User className="w-4 h-4" />
              ) : (
                <Bot className="w-4 h-4" />
              )}
            </div>

            {/* 消息内容 */}
            <div className={cn(
              'flex-1 max-w-[80%]',
              message.role === 'user' ? 'flex-col items-end' : 'flex-col items-start'
            )}>
              {/* 🔧 重构：AI 消息�?processing_steps 时，不显示气泡卡片（所有内容在 ProcessingSteps 中展示） */}
              {(() => {
                const hasProcessingSteps = message.metadata?.processing_steps && message.metadata.processing_steps.length > 0
                const hasContent = message.content && message.content.trim().length > 0
                const isAssistantWithSteps = message.role === 'assistant' && hasProcessingSteps

                // AI 消息有步骤时，跳过气泡卡片渲染（不管状态和内容�?
                // 所有临时内容和最终结果都�?ProcessingSteps 的各个步骤中展示
                if (isAssistantWithSteps) {
                  return null
                }

                // 用户消息 - DataLab 风格
                if (message.role === 'user') {
                  return (
                    <div className="flex flex-col items-end gap-1">
                      <div className="bg-primary text-slate-900 px-6 py-4 rounded-2xl rounded-tr-sm shadow-soft max-w-md">
                        <p className="font-medium text-sm leading-relaxed">{message.content || ''}</p>
                      </div>
                      <span className="text-xs text-slate-400 px-2">
                        {formatTimestamp(message.timestamp)}
                      </span>
                    </div>
                  )
                }

                // AI 消息 (没有 processing_steps 的情�?
                if (!hasProcessingSteps && (hasContent || message.status === 'sending')) {
                  return (
                    <Card className="inline-block w-full bg-muted text-foreground">
                      <CardContent className="p-3">
                        <div className="message-container">
                          {hasContent && (
                            <p className="text-base whitespace-pre-wrap">{message.content}</p>
                          )}
                          {message.status === 'sending' && !hasProcessingSteps && (
                            <span className="inline-block w-2 h-5 ml-1 bg-gray-600 animate-pulse" />
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )
                }

                return null
              })()}

              {/* 显示AI推理步骤（包含SQL、表格、图表，仅对 assistant 消息显示�?*/}
              {message.role === 'assistant' && message.metadata?.processing_steps &&
               message.metadata.processing_steps.length > 0 && (
                <>
                  <InsightBanner insight={message.metadata.insight} />
                  <ProcessingSteps
                    key={message.id}
                    steps={message.metadata.processing_steps}
                    defaultExpanded={false}
                  />
                </>
              )}

              {/* 检测工具调用失败并显示警告 */}
              {message.role === 'assistant' && (
                (() => {
                  const hasSystemError = message.content.includes('SYSTEM ERROR') ||
                                         message.content.includes('无法获取数据') ||
                                         message.content.includes('工具调用失败') ||
                                         (message.metadata as any)?.tool_error === true ||
                                         (message.metadata as any)?.tool_status === 'error'
                  if (hasSystemError) {
                    return (
                      <div className="mt-2 flex items-center gap-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded p-2">
                        <AlertTriangle className="w-4 h-4" />
                        <span>数据源连接失败，以下回答可能不准确</span>
                      </div>
                    )
                  }
                  return null
                })()
              )}

              {/* 时间戳和停止按钮 */}
              <div className={cn(
                'text-xs text-muted-foreground mt-1 flex items-center gap-2',
                message.role === 'user' ? 'justify-end' : 'justify-start'
              )}>
                <span>
                  {formatTimestamp(message.timestamp)}
                  {message.status === 'sending' && ' · 生成中...'}
                  {message.status === 'error' && ' · 发送失败'}
                </span>
                {/* 停止生成按钮 */}
                {message.role === 'assistant' &&
                 message.status === 'sending' &&
                 streamingMessageId === message.id &&
                 streamingStatus !== 'idle' && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-xs"
                    onClick={() => stopStreaming()}
                  >
                    <Square className="w-3 h-3 mr-1" />
                    停止生成
                  </Button>
                )}
              </div>

              {/* 图表选择区域（仅在有图表�?assistant 消息显示�?*/}
              {message.role === 'assistant' && hasChart(message) && (
                <div className="mt-2 flex items-center gap-2">
                  <Checkbox
                    id={`chart-select-${message.id}`}
                    checked={selectedCharts.includes(message.id)}
                    onCheckedChange={() => toggleChartSelection(message.id)}
                    className="cursor-pointer"
                  />
                  <label
                    htmlFor={`chart-select-${message.id}`}
                    className="text-xs text-muted-foreground cursor-pointer select-none flex items-center gap-1"
                  >
                    {selectedCharts.includes(message.id) ? (
                      <>
                        <Check className="w-3 h-3 text-primary" />
                        已选中合并
                      </>
                    ) : (
                      '加入图表合并'
                    )}
                  </label>
                </div>
              )}

              {/* 推理过程和元数据（向后兼容） */}
              {message.metadata && (
                <div className="mt-2 text-xs space-y-2">
                  {/* 工具调用状态（默认展开�?*/}
                  {(message.metadata as any).tool_calls && (message.metadata as any).tool_calls.length > 0 && (
                    <details open className="bg-primary/10 border border-primary/30 rounded p-2">
                      <summary className="font-medium text-primary cursor-pointer mb-1">工具调用状态</summary>
                      <div className="mt-1 space-y-1">
                        {(message.metadata as any).tool_calls.map((tc: any, idx: number) => (
                          <div key={idx} className="flex items-center gap-2 text-primary">
                            <span>· {tc.name || 'unknown'}</span>
                            {tc.status === 'error' && (
                              <span className="text-red-600">⚠️ 失败</span>
                            )}
                            {tc.status === 'success' && (
                              <span className="text-green-600">✅ 成功</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </details>
                  )}

                  {/* 推理过程（默认展开�?*/}
                  {message.metadata.reasoning && (
                    <details open className="bg-muted border border-border rounded p-2">
                      <summary className="font-medium text-foreground cursor-pointer mb-1">推理过程</summary>
                      <p className="text-muted-foreground mt-1 whitespace-pre-wrap">{message.metadata.reasoning}</p>
                    </details>
                  )}

                  {message.metadata.sources && message.metadata.sources.length > 0 && (
                    <div className="mb-1">
                      <strong>数据源：</strong> {message.metadata.sources.join(', ')}
                    </div>
                  )}
                  {message.metadata.confidence && (
                    <div className="mb-1">
                      <strong>置信度：</strong> {Math.round(message.metadata.confidence * 100)}%
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )
      })}
      <div ref={messagesEndRef} />
    </div>
  )
})



