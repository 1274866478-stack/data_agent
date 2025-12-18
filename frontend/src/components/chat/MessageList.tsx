'use client'

import { useEffect, useRef, useImperativeHandle, forwardRef, useState } from 'react'
import { User, Bot } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Markdown } from '@/components/ui/markdown'
import { ChatMessage } from '@/store/chatStore'
import { cn } from '@/lib/utils'
import { EChartsRenderer } from './EChartsRenderer'
import { ChatQueryResultView } from './ChatQueryResultView'

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
                      <Markdown content={textToRender} />
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

              {/* 时间戳 */}
              <div className={cn(
                'text-xs text-gray-500 mt-1',
                message.role === 'user' ? 'text-right' : 'text-left'
              )}>
                {formatTimestamp(message.timestamp)}
                {message.status === 'sending' && ' • 发送中...'}
                {message.status === 'error' && ' • 发送失败'}
              </div>

              {/* 简化的元数据显示 */}
              {message.metadata && (
                <div className="mt-2 text-xs text-gray-500">
                  {message.metadata.reasoning && (
                    <div className="mb-1">
                      <strong>推理：</strong> {message.metadata.reasoning}
                    </div>
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