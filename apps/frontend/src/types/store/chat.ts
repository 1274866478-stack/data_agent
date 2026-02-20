export type StreamingStatus = 'idle' | 'streaming' | 'paused' | 'error' | 'completed'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  status?: 'sending' | 'sent' | 'error'
  metadata?: {
    sources?: string[]
    reasoning?: string
    confidence?: number
    table?: import('@/types/api/chat').ChatQueryResultTable
    chart?: import('@/types/api/chat').ChatQueryChart
    echarts_option?: Record<string, any>
    processing_steps?: Array<import('@/types/chat').ProcessingStep>
    progress?: number
    insight?: string
    insights?: string[]
    query_chain?: import('@/types/chat').QueryChainItem[]
    chart_validation?: import('@/types/chat').ChartValidation
    lineage?: import('@/types/chat').CellLineage[]
    context_info?: Record<string, any>
  }
}

export interface ChatSession {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  messages: ChatMessage[]
  isActive: boolean
}
