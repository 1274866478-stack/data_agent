'use client'

import { useEffect, useRef, useState } from 'react'
import { User, Bot, AlertCircle, CheckCircle, Brain, Eye, EyeOff, ChevronDown, ChevronUp } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Markdown } from '@/components/ui/markdown'
import { Badge } from '@/components/ui/badge'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Separator } from '@/components/ui/separator'
import { AnswerExplanation, ReasoningPath, SourceCitations, EvidenceChain, ReasoningQualityScore } from '@/components/xai'
import { useChatStore, ChatMessage } from '@/store/chatStore'
import { cn } from '@/lib/utils'

interface MessageListProps {
  className?: string
}

export function MessageList({ className }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { currentSession, deleteMessage, isLoading } = useChatStore()
  const [expandedXAIMessages, setExpandedXAIMessages] = useState<Set<string>>(new Set())
  const [selectedXAITab, setSelectedXAITab] = useState<Record<string, string>>({})

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [currentSession?.messages])

  // XAI 相关工具函数
  const toggleXAIExpansion = (messageId: string) => {
    setExpandedXAIMessages(prev => {
      const newSet = new Set(prev)
      if (newSet.has(messageId)) {
        newSet.delete(messageId)
      } else {
        newSet.add(messageId)
      }
      return newSet
    })
  }

  const hasXAIData = (message: ChatMessage) => {
    return message.metadata && (
      message.metadata.reasoning ||
      message.metadata.sources ||
      message.metadata.confidence ||
      message.metadata.xai_analysis ||
      message.metadata.reasoning_steps ||
      message.metadata.evidence_chain ||
      message.metadata.source_traces
    )
  }

  const getXAITabKey = (messageId: string, tab: string) => `${messageId}-${tab}`

  const renderXAIControls = (message: ChatMessage) => {
    if (!hasXAIData(message) || message.role !== 'assistant') return null

    const messageId = message.id
    const isExpanded = expandedXAIMessages.has(messageId)
    const currentTab = selectedXAITab[messageId] || 'explanation'

    return (
      <div className="mt-2">
        <Collapsible
          open={isExpanded}
          onOpenChange={() => toggleXAIExpansion(messageId)}
        >
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start h-auto p-2 text-xs bg-muted/30 hover:bg-muted/50"
            >
              <Brain className="w-3 h-3 mr-2" />
              <span className="flex-1 text-left">AI 推理解释</span>
              <div className="flex items-center gap-1">
                {message.metadata.confidence && (
                  <Badge variant="outline" className="text-xs">
                    置信度 {Math.round(message.metadata.confidence * 100)}%
                  </Badge>
                )}
                {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </div>
            </Button>
          </CollapsibleTrigger>

          <CollapsibleContent className="mt-2">
            <Card className="border-blue-200 bg-blue-50/30">
              <CardContent className="p-4">
                {/* XAI 标签页导航 */}
                <div className="flex flex-wrap gap-1 mb-4 pb-2 border-b">
                  {[
                    { id: 'explanation', label: '答案解释', icon: <Brain className="w-3 h-3" /> },
                    { id: 'reasoning', label: '推理路径', icon: <Eye className="w-3 h-3" /> },
                    { id: 'evidence', label: '证据链', icon: <Eye className="w-3 h-3" /> },
                    { id: 'sources', label: '数据源', icon: <Eye className="w-3 h-3" /> },
                    { id: 'quality', label: '质量评分', icon: <Eye className="w-3 h-3" /> }
                  ].map(tab => (
                    <Button
                      key={tab.id}
                      variant={currentTab === tab.id ? 'default' : 'ghost'}
                      size="sm"
                      onClick={() => setSelectedXAITab(prev => ({
                        ...prev,
                        [messageId]: tab.id
                      }))}
                      className="text-xs h-7 px-2"
                    >
                      <div className="flex items-center gap-1">
                        {tab.icon}
                        {tab.label}
                      </div>
                    </Button>
                  ))}
                </div>

                {/* XAI 标签页内容 */}
                <div className="min-h-[200px]">
                  {currentTab === 'explanation' && (
                    <AnswerExplanation
                      query={message.metadata.query || ''}
                      answer={message.content}
                      explanationSteps={message.metadata.explanation_steps}
                      confidenceExplanation={message.metadata.confidence_explanation}
                      alternativeAnswers={message.metadata.alternative_answers}
                      explanationQualityScore={message.metadata.explanation_quality_score || 0}
                      processingMetadata={message.metadata.processing_metadata}
                    />
                  )}

                  {currentTab === 'reasoning' && (
                    <ReasoningPath
                      reasoningSteps={message.metadata.reasoning_steps || []}
                      decisionTree={message.metadata.decision_tree || {}}
                      processingTime={message.metadata.processing_time || 0}
                      showVisualization={true}
                    />
                  )}

                  {currentTab === 'evidence' && (
                    <EvidenceChain
                      chains={message.metadata.evidence_chains || []}
                      evidenceNodes={message.metadata.evidence_nodes || {}}
                      query={message.metadata.query || ''}
                      answer={message.content}
                      showVisualization={true}
                      allowInteraction={true}
                    />
                  )}

                  {currentTab === 'sources' && (
                    <SourceCitations
                      sources={message.metadata.source_traces || message.metadata.sources || []}
                      answer={message.content}
                      query={message.metadata.query || ''}
                      showStats={true}
                      allowSearch={true}
                    />
                  )}

                  {currentTab === 'quality' && (
                    <ReasoningQualityScore
                      query={message.metadata.query || ''}
                      answer={message.content}
                      qualityBreakdown={message.metadata.quality_breakdown}
                      processingMetadata={message.metadata.processing_metadata}
                      showDetailedAnalysis={true}
                      allowExport={true}
                    />
                  )}
                </div>
              </CardContent>
            </Card>
          </CollapsibleContent>
        </Collapsible>
      </div>
    )
  }

  // 渲染单个消息
  const renderMessage = (message: ChatMessage) => {
    const isUser = message.role === 'user'
    const isSystem = message.role === 'system'

    return (
      <div
        key={message.id}
        className={cn(
          'flex gap-3 p-4 transition-colors hover:bg-muted/20',
          isUser && 'flex-row-reverse',
          isSystem && 'justify-center'
        )}
      >
        {!isSystem && (
          <div className="flex-shrink-0">
            <div className={cn(
              'w-8 h-8 rounded-full flex items-center justify-center',
              isUser ? 'bg-primary text-primary-foreground' : 'bg-muted'
            )}>
              {isUser ? (
                <User className="w-4 h-4" />
              ) : (
                <Bot className="w-4 h-4" />
              )}
            </div>
          </div>
        )}

        <div className={cn(
          'flex flex-col gap-2 max-w-[70%]',
          isUser && 'items-end',
          isSystem && 'max-w-[80%] text-center'
        )}>
          {/* 消息内容 */}
          <Card className={cn(
            'p-3 shadow-sm',
            isUser && 'bg-primary text-primary-foreground',
            isSystem && 'bg-muted/50 border-dashed',
            !isUser && !isSystem && 'bg-background'
          )}>
            {isUser || isSystem ? (
              <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                {message.content}
              </div>
            ) : (
              <Markdown
                content={message.content}
                className="text-sm leading-relaxed [&_p]:mb-2 [&_p:last-child]:mb-0"
              />
            )}

            {/* 元数据信息 */}
            {message.metadata && (
              <div className="mt-3 pt-3 border-t border-border/50">
                {message.metadata.sources && message.metadata.sources.length > 0 && (
                  <div className="mb-2">
                    <p className="text-xs font-medium mb-1">数据来源：</p>
                    <ul className="text-xs space-y-1">
                      {message.metadata.sources.map((source, index) => (
                        <li key={index} className="text-muted-foreground">
                          • {source}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {message.metadata.confidence && (
                  <div className="mb-2">
                    <span className="text-xs text-muted-foreground">
                      置信度：{Math.round(message.metadata.confidence * 100)}%
                    </span>
                  </div>
                )}

                {message.metadata.reasoning && (
                  <details className="text-xs">
                    <summary className="cursor-pointer font-medium text-muted-foreground">
                      推理过程
                    </summary>
                    <p className="mt-1 text-muted-foreground">
                      {message.metadata.reasoning}
                    </p>
                  </details>
                )}
              </div>
            )}

            {/* XAI 推理解释组件 */}
            {renderXAIControls(message)}
          </Card>

          {/* 状态和时间戳 */}
          <div className={cn(
            'flex items-center gap-2 text-xs text-muted-foreground',
            isUser && 'flex-row-reverse'
          )}>
            {/* 状态指示器 */}
            <div className="flex items-center gap-1">
              {message.status === 'sending' && (
                <>
                  <div className="w-1 h-1 bg-current rounded-full animate-pulse"></div>
                  <span>发送中</span>
                </>
              )}
              {message.status === 'sent' && !isSystem && (
                <CheckCircle className="w-3 h-3 text-green-500" />
              )}
              {message.status === 'error' && !isSystem && (
                <AlertCircle className="w-3 h-3 text-destructive" />
              )}
            </div>

            {/* 时间戳 */}
            <span>
              {message.timestamp.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
              })}
            </span>

            {/* 删除按钮 */}
            {!isSystem && (
              <Button
                variant="ghost"
                size="sm"
                className="h-auto p-0 text-xs opacity-0 hover:opacity-100 transition-opacity"
                onClick={() => deleteMessage(message.id)}
              >
                删除
              </Button>
            )}
          </div>
        </div>
      </div>
    )
  }

  const messages = currentSession?.messages || []

  return (
    <div className={cn('flex-1 overflow-y-auto', className)}>
      <div className="max-w-4xl mx-auto">
        {messages.length === 0 ? (
          // 空状态
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="w-12 h-12 bg-muted rounded-full flex items-center justify-center mb-4">
              <Bot className="w-6 h-6 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-medium mb-2">开始对话</h3>
            <p className="text-muted-foreground text-sm max-w-md">
              我是您的AI助手，可以帮助您分析数据、回答问题、提供洞察。请输入您的问题开始对话。
            </p>

            {/* 建议问题 */}
            <div className="mt-6 flex flex-wrap gap-2 justify-center">
              {[
                '我的数据有哪些来源？',
                '分析最近的销售趋势',
                '查看客户数据洞察',
                '生成业务报告'
              ].map((suggestion, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    // 这里可以添加自动填入建议问题的功能
                    const input = document.querySelector('textarea') as HTMLTextAreaElement
                    if (input) {
                      input.value = suggestion
                      input.dispatchEvent(new Event('input', { bubbles: true }))
                    }
                  }}
                  disabled={isLoading}
                  className="text-xs"
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          // 消息列表
          <div className="space-y-1">
            {messages.map(renderMessage)}

            {/* 加载指示器 */}
            {isLoading && (
              <div className="flex gap-3 p-4">
                <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="flex flex-col gap-2">
                  <Card className="p-3 shadow-sm bg-background">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <div className="w-1 h-1 bg-current rounded-full animate-pulse"></div>
                        <div className="w-1 h-1 bg-current rounded-full animate-pulse delay-75"></div>
                        <div className="w-1 h-1 bg-current rounded-full animate-pulse delay-150"></div>
                      </div>
                      <span className="text-sm text-muted-foreground">
                        AI 正在思考中...
                      </span>
                    </div>
                  </Card>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 滚动锚点 */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}