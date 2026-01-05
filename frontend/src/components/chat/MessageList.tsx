/**
 * # [MESSAGE_LIST] 消息列表组件
 *
 * ## [MODULE]
 * **文件名**: MessageList.tsx
 * **职责**: 渲染聊天消息列表，支持Markdown渲染、图表显示、流式响应、高亮定位、错误提示和停止生成
 *
 * ## [INPUT]
 * Props:
 * - **className?: string** - 可选的CSS类名
 * - **messages: ChatMessage[]** - 要显示的消息数组
 * - **highlightedMessageId?: string | null** - 需要高亮显示的消息ID
 *
 * ## [OUTPUT]
 * UI组件:
 * - **消息气泡**: 用户消息（蓝色右侧）和助手消息（灰色左侧）
 * - **Markdown渲染**: 支持富文本格式、代码块、列表等
 * - **图表显示**: 解析并渲染ECharts图表配置（从[CHART_START]标记或metadata）
 * - **结构化结果**: 显示表格数据和图表（通过ChatQueryResultView）
 * - **推理步骤**: 显示AI处理步骤（通过ProcessingSteps）
 * - **错误提示**: 显示数据源连接失败警告（AlertTriangle图标）
 * - **工具调用状态**: 显示工具调用成功/失败状态
 * - **停止生成按钮**: 流式响应时显示停止按钮
 * - **高亮效果**: 搜索结果高亮显示（3秒后自动清除）
 * - **Ref方法**: scrollToMessage, scrollToBottom
 *
 * **上游依赖**:
 * - [../../store/chatStore.ts](../../store/chatStore.ts) - 聊天状态管理Store
 * - [./EChartsRenderer.tsx](./EChartsRenderer.tsx) - ECharts图表渲染器
 * - [./ChatQueryResultView.tsx](./ChatQueryResultView.tsx) - 查询结果视图
 * - [./ProcessingSteps.tsx](./ProcessingSteps.tsx) - 处理步骤显示
 * - [../ui/markdown.tsx](../ui/markdown.tsx) - Markdown渲染器
 * - [../ui/card.tsx](../ui/card.tsx) - 卡片组件
 * - lucide-react - 图标库 (User, Bot, AlertTriangle, Square)
 *
 * **下游依赖**:
 * - [./ChatInterface.tsx](./ChatInterface.tsx) - 聊天界面（调用此组件的ref方法）
 *
 * **调用方**:
 * - [ChatInterface.tsx](./ChatInterface.tsx) - 聊天主界面
 *
 * ## [STATE]
 * - **Ref管理**: messagesEndRef（滚动到底部）, messageRefs（消息位置映射）
 * - **本地高亮**: localHighlightId（本地高亮状态，3秒后清除）
 * - **流式状态**: streamingStatus, streamingMessageId（从chatStore读取）
 *
 * ## [SIDE-EFFECTS]
 * - 自动滚动到底部（messages变化时）
 * - 高亮消息自动滚动（highlightedMessageId变化时）
 * - 定时器操作（高亮3秒后自动清除）
 * - 调用stopStreaming（用户点击停止生成按钮）
 * - console日志输出（调试图表解析和processing_steps）
 */

'use client'

import { useEffect, useRef, useImperativeHandle, forwardRef, useState } from 'react'
import { User, Bot, AlertTriangle, Square } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Markdown } from '@/components/ui/markdown'
import { Button } from '@/components/ui/button'
import { ChatMessage, useChatStore } from '@/store/chatStore'
import { cn } from '@/lib/utils'
import { ProcessingSteps } from './ProcessingSteps'

/**
 * 从消息内容中移除图表标记和Markdown表格，避免与推理步骤中的内容重复显示
 * - 如果有 AI 推理步骤，移除所有内容（所有内容都在 ProcessingSteps 中展示）
 * - 图表已通过 ProcessingSteps 的步骤7展示
 * - 表格已通过 ProcessingSteps 的步骤6展示
 * - 数据分析已通过 ProcessingSteps 的步骤8展示
 */
function removeChartMarkers(content: string, hasProcessingSteps: boolean): string {
  // 如果有 AI 推理步骤，移除所有内容（避免重复）
  if (hasProcessingSteps) {
    return ''
  }

  let cleaned = content

  // 移除 [CHART_START]...[CHART_END] 标记
  cleaned = cleaned.replace(/\[CHART_START\].*?\[CHART_END\]/gs, '')

  // 移除 Markdown 表格（避免与 ProcessingSteps 步骤6重复）
  // 匹配以 | 开头的行，包含分隔符行 |---| 和数据行
  // 策略：找到表格开始（包含 | 的行），然后连续的 | 行都是表格的一部分
  const lines = cleaned.split('\n')
  const filteredLines: string[] = []
  let inTable = false
  let tableLineCount = 0

  for (const line of lines) {
    const trimmed = line.trim()
    // 检查是否是表格行（包含 | 且不是代码块）
    const isTableRow = trimmed.startsWith('|') && trimmed.endsWith('|')
    const isSeparator = /^\|[\s\-:|]+\|$/.test(trimmed)

    if (isTableRow) {
      if (!inTable) {
        inTable = true
        tableLineCount = 0
      }
      tableLineCount++
      // 跳过表格行，不添加到输出
      continue
    } else {
      if (inTable && tableLineCount > 0) {
        // 表格结束
        inTable = false
        tableLineCount = 0
      }
      filteredLines.push(line)
    }
  }

  cleaned = filteredLines.join('\n')

  // 清理多余的空行
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n')

  return cleaned
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
  
  // 获取流式状态
  const { streamingStatus, streamingMessageId, stopStreaming } = useChatStore()

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

  // 当外部高亮ID变化时，滚动到对应消息
  useEffect(() => {
    if (highlightedMessageId) {
      scrollToMessage(highlightedMessageId)
    }
  }, [highlightedMessageId])

  const formatTimestamp = (date: Date) => {
    return new Date(date).toLocaleTimeString()
  }

  // 判断消息是否高亮
  const isHighlighted = (messageId: string) =>
    messageId === highlightedMessageId || messageId === localHighlightId

  return (
    <div className={cn('space-y-4 p-4', className)}>
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
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-600'
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
              <Card className={cn(
                'inline-block w-full',
                message.role === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-100'
              )}>
                <CardContent className="p-3">
                  <div className="message-container">
                    {/* 渲染消息内容 */}
                    {message.role === 'user' ? (
                      <p className="text-base whitespace-pre-wrap">{message.content || ''}</p>
                    ) : (
                      // AI消息：所有内容在 ProcessingSteps 中展示，此处只显示流式光标
                      message.status === 'sending' && (
                        <span className="inline-block w-2 h-5 ml-1 bg-gray-600 animate-pulse" />
                      )
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* 显示AI推理步骤（包含SQL、表格、图表，仅对 assistant 消息显示） */}
              {message.role === 'assistant' && message.metadata?.processing_steps &&
               message.metadata.processing_steps.length > 0 && (
                <ProcessingSteps
                  steps={message.metadata.processing_steps}
                  defaultExpanded={message.status === 'sending'}
                />
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
                'text-xs text-gray-500 mt-1 flex items-center gap-2',
                message.role === 'user' ? 'justify-end' : 'justify-start'
              )}>
                <span>
                  {formatTimestamp(message.timestamp)}
                  {message.status === 'sending' && ' • 生成中...'}
                  {message.status === 'error' && ' • 发送失败'}
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

              {/* 推理过程和元数据（向后兼容） */}
              {message.metadata && (
                <div className="mt-2 text-xs space-y-2">
                  {/* 工具调用状态（默认展开） */}
                  {(message.metadata as any).tool_calls && (message.metadata as any).tool_calls.length > 0 && (
                    <details open className="bg-blue-50 border border-blue-200 rounded p-2">
                      <summary className="font-medium text-blue-800 cursor-pointer mb-1">工具调用状态</summary>
                      <div className="mt-1 space-y-1">
                        {(message.metadata as any).tool_calls.map((tc: any, idx: number) => (
                          <div key={idx} className="flex items-center gap-2 text-blue-700">
                            <span>• {tc.name || 'unknown'}</span>
                            {tc.status === 'error' && (
                              <span className="text-red-600">⚠️ 失败</span>
                            )}
                            {tc.status === 'success' && (
                              <span className="text-green-600">✓ 成功</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </details>
                  )}

                  {/* 推理过程（默认展开） */}
                  {message.metadata.reasoning && (
                    <details open className="bg-gray-50 border border-gray-200 rounded p-2">
                      <summary className="font-medium text-gray-700 cursor-pointer mb-1">推理过程</summary>
                      <p className="text-gray-600 mt-1 whitespace-pre-wrap">{message.metadata.reasoning}</p>
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