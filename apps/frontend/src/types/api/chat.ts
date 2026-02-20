export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ChatQueryRequest {
  query: string
  session_id?: string
  history?: ChatMessage[]
  context?: {
    data_sources?: string[]
  }
  connection_id?: string
}

export interface ChatCompletionRequest {
  messages: ChatMessage[]
  session_id?: string
  stream?: boolean
}

export interface ChatQueryResultTable {
  columns: string[]
  rows: Array<Record<string, any> | any[]>
  row_count: number
}

export interface ChatQueryChart {
  type?: string
  title?: string
  data?: Record<string, any>
  chart_type?: string
  chart_config?: Record<string, any>
  chart_image?: string
  x_field?: string
  y_field?: string
}

export interface ChatQueryResponse {
  answer: string
  table?: ChatQueryResultTable
  chart?: ChatQueryChart
  sources?: string[]
  reasoning?: string
  confidence?: number
}

export interface V2StreamCallbacks {
  onProgress?: (progress: number) => void
  onStep?: (step: string, data: any) => void
  onContent?: (content: string) => void
  onTable?: (table: ChatQueryResultTable) => void
  onChart?: (chart: ChatQueryChart) => void
  onComplete?: () => void
  onError?: (error: string) => void
}
