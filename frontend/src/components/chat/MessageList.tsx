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
import { EChartsRenderer } from './EChartsRenderer'
import { ChatQueryResultView } from './ChatQueryResultView'
import { ProcessingSteps } from './ProcessingSteps'

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
        // 解析逻辑：将 message.content 拆分成"纯文本部分"和"图表配置部分"
        const content = message.content || ''
        const chartRegex = /\[CHART_START\]([\s\S]*?)\[CHART_END\]/ // 匹配图表标记
        const match = content.match(chartRegex)
        
        let textToRender = content
        let chartOption = null
        
        if (match) {
          try {
            const jsonStr = match[1].trim()
            chartOption = JSON.parse(jsonStr)
            
            // 关键：将图表代码从显示的文本中移除，避免重复显示乱码
            textToRender = content.replace(match[0], '').trim()
          } catch (e) {
            console.error('Failed to parse chart JSON:', e)
            // 如果解析失败，保留原文以便调试
          }
        }
        
        // 如果 metadata 中有 echarts_option，优先使用（用于向后兼容）
        if (!chartOption && message.metadata?.echarts_option) {
          chartOption = message.metadata.echarts_option
        }

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
                    {/* 1. 渲染清洗后的 Markdown 文本 */}
                    {message.role === 'user' ? (
                      <p className="text-base whitespace-pre-wrap">{textToRender}</p>
                    ) : (
                      <>
                        <Markdown content={textToRender} />
                        {/* 流式响应光标闪烁效果 */}
                        {message.status === 'sending' && (
                          <span className="inline-block w-2 h-5 ml-1 bg-gray-600 animate-pulse" />
                        )}
                      </>
                    )}
                    
                    {/* 2. 如果解析到了图表配置，渲染图表（仅对 assistant 消息显示） */}
                    {message.role === 'assistant' && chartOption && (
                      <div className="mt-4 w-full">
                        <EChartsRenderer
                          echartsOption={chartOption}
                          title={
                            (typeof chartOption.title === 'object' 
                              ? chartOption.title?.text 
                              : chartOption.title) || 
                            '数据可视化'
                          }
                        />
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* 如果有结构化结果或图表，追加展示（仅对 assistant 消息显示） */}
              {message.role === 'assistant' && message.metadata && (message.metadata.table || message.metadata.chart) && (
                <ChatQueryResultView
                  table={message.metadata.table}
                  chart={message.metadata.chart}
                />
              )}

              {/* 显示AI推理步骤（仅对 assistant 消息显示） */}
              {message.role === 'assistant' && (() => {
                // 调试日志
                console.log('[MessageList] 检查processing_steps:', message.id, message.metadata?.processing_steps)
                return message.metadata?.processing_steps && message.metadata.processing_steps.length > 0
              })() && (
                <ProcessingSteps
                  steps={message.metadata.processing_steps}
                  defaultExpanded={true}
                />
              )}

              {/* 🔴 第三道防线：检测工具调用失败并显示警告图标 */}
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

              {/* 🔴 第三道防线：默认展开显示推理过程和工具输出 */}
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