/**
 * # [API-CLIENT] 前端API客户 *
 * ## [MODULE]
 * HTTP客户端，处理与FastAPI后端的通信
 *
 * ## [INPUT]
 * - API端点路径
 * - 请求数据 (body/query/params)
 * - 认证令牌
 *
 * ## [OUTPUT]
 * - API响应数据
 * - 错误信息
 * - 流式事件 (SSE)
 *
 * ## [LINK]
 * **上游依赖**:
 * - [./utils.ts](./utils.ts) - 工具函数
 * - [../store/](../store/_folder.md) - 状态管 * - [../types/chat.ts](../types/chat.ts) - 类型定义
 *
 * **下游依赖**:
 * - fetch API - HTTP请求
 * - process.env - 环境变量 (NEXT_PUBLIC_API_URL)
 * - [http://localhost:8004](http://localhost:8004) - 后端API服务
 *
 * **调用*:
 * - [../services/](../services/_folder.md) - 业务服务 * - [../components/](../components/_folder.md) - React组件
 * - [../store/](../store/_folder.md) - 状态管理Action
 *
 * ## [STATE]
 * - apiClient: ApiClient 单例实例
 * - baseURL: API基础URL
 * - token: 认证令牌 (可
 *
 * ## [SIDE-EFFECTS]
 * - HTTP请求发 * - localStorage读写 (令牌缓存)
 */

export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
  status: 'success' | 'error'
}

export interface ChatQueryRequest {
  query: string
  session_id?: string
  history?: Array<{ role: 'user' | 'assistant' | 'system'; content: string }>
  context?: {
    data_sources?: string[]
    documents?: string[]
    max_results?: number
  }
  connection_id?: string | number  // 数据源连接ID，用于启Agent
  use_v2?: boolean  // 是否使用 AgentV2 (默认 true)
}

export interface ChatQueryResultTable {
  columns: string[]
  rows: Record<string, unknown>[]
  row_count: number
}

export interface ChatQueryChart {
  chart_type?: ChartType | string
  title?: string
  x_field?: string
  y_field?: string
  /**
   * 图表图片data URL ?HTTP URL（如果后端返回的是静态图   */
  chart_image?: string | null
  /**
   * ECharts JSON 配置字符串（用于前端动态渲染）
   */
  chart_config?: string | null
}

export interface ChatQueryResponse {
  answer: string
  sources?: string[]
  reasoning?: string
  confidence?: number
  execution_time?: number
  /**
   * 结构化查询结果表（如Agent 返回了数据）?   */
  table?: ChatQueryResultTable
  /**
   * 图表配置/图片信息（如Agent 返回了可视化）?   */
  chart?: ChatQueryChart
  /**
   * ECharts JSON 配置选项（用于前端直接渲染图表）?   */
  echarts_option?: Record<string, any>
  insight?: string
  context_info?: Record<string, any>
}

// LLM Chat Completion 接口（匹配后端API）
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  thinking?: string
}

// 导入流式响应类型和解析器
import {
    StreamCallbacks,
    StreamEvent,
    StreamEventType,
    V2CancelResponse,
    V2PauseResponse,
    V2ResumeResponse,
    V2SessionState,
    V2StreamCallbacks,
    // 日志流式查询类型
    LogStreamCallbacks,
    LogStreamStartData,
    LogStreamProgressData,
    LogStreamFileStatusData,
    LogStreamBatchData,
    LogStreamDoneData,
    LogStreamErrorData,
    LogStreamFileInfoData,
    LogStreamErrorCountData,
} from '../types/chat'
import { parseStreamResponse } from '../utils/stream-parser'

export interface ChatCompletionRequest {
  messages: ChatMessage[]
  provider?: string
  model?: string
  max_tokens?: number
  temperature?: number
  stream?: boolean
  enable_thinking?: boolean
  data_source_ids?: string[]  // 指定使用的数据源ID列表
  use_agent?: boolean  // 是否使用 LangGraph Agent 模式
}

// 后端实际返回的响应格式（简化格式）
export interface BackendChatCompletionResponse {
  content: string
  thinking?: string
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  model?: string
  provider?: string
  finish_reason?: string
  created_at?: string
}

// OpenAI 风格的响应格式（保留用于兼容性）
export interface ChatCompletionResponse {
  id: string
  model: string
  choices: Array<{
    index: number
    message: ChatMessage
    finish_reason: string
  }>
  usage: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}

export interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

// ============================================================
// Agent API 类型定义
// ============================================================

export type ChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'area' | 'table';
export type InsightImportance = 'high' | 'medium' | 'low';
export type InsightType = 'trend' | 'anomaly' | 'comparison' | 'summary' | 'forecast';

export interface AgentQueryResult {
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
  column_types?: Record<string, string>;
}

export interface AgentChartConfig {
  chart_type: ChartType;
  title?: string;
  x_field?: string;
  y_field?: string;
  series_field?: string;
  colors?: string[];
  show_legend?: boolean;
  show_grid?: boolean;
}

export interface AgentInsight {
  type: InsightType;
  title: string;
  description: string;
  importance: InsightImportance;
  metrics?: Record<string, unknown>;
}

export interface AgentDataAnalysis {
  total?: number;
  average?: number;
  max_value?: number;
  min_value?: number;
  trend?: 'increasing' | 'decreasing' | 'stable' | 'volatile';
  change_rate?: number;
}

export interface AgentVisualizationResponse {
  success: boolean;
  answer?: string;
  sql?: string;
  data?: AgentQueryResult;
  chart?: AgentChartConfig;
  analysis?: AgentDataAnalysis;
  insights?: AgentInsight[];
  suggestions?: string[];
  error?: string;
  execution_time?: number;
}

export interface AgentQueryRequest {
  question: string;
  data_source_id: string;
  thread_id?: string;
  options?: Record<string, unknown>;
}

export interface AgentQueryResponse {
  success: boolean;
  data?: AgentVisualizationResponse;
  error?: string;
  request_id?: string;
  timestamp?: string;
}

// 导入日志工具
import logger from './logger'

export class ApiClient {
  private baseURL: string
  private defaultHeaders: Record<string, string>
  private _tenantId: string | null = null

  constructor() {
    // 🔧 临时修复：默认使V1 API（V2 ?DeepAgents 框架兼容性问题）
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    }
    logger.info('ApiClient', 'ApiClient initialized', { baseURL: this.baseURL })
  }

  // 设置租户ID
  setTenantId(tenantId: string) {
    this._tenantId = tenantId
  }

  // 获取租户ID
  get tenantId(): string {
    return this._tenantId || 'default_tenant'
  }

  // 获取 V2 API 基础 URL
  private get v2BaseURL(): string {
    // 从当baseURL 转换V2 URL
    // http://localhost:8004/api/v1 -> http://localhost:8004/api/v2
    return this.baseURL.replace('/api/v1', '/api/v2')
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const startTime = performance.now()
    const method = options.method || 'GET'

    try {
      const url = `${this.baseURL}${endpoint}`

      // 记录API请求
      logger.apiRequest(method, endpoint, options.body)

      // 从localStorage获取token，开发环境下使用开发token

      // 从localStorage获取token，开发环境下使用开发token
      let token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null

      // 开发环境：如果没有token，使用开发token
      if (!token && process.env.NODE_ENV === 'development') {
        token = 'dev_token'
        console.log('开发环境：使用开发token')
      }

      const response = await fetch(url, {
        ...options,
        headers: {
          ...this.defaultHeaders,
          ...(token && { Authorization: `Bearer ${token}` }),
          ...options.headers,
        },
      })

      // 处理HTTP错误状态
      if (!response.ok) {
        const duration = performance.now() - startTime
        const errorText = await response.text()

        // 记录API错误
        logger.apiResponse(method, endpoint, response.status, duration)

        return {
          status: 'error',
          error: `HTTP ${response.status}: ${errorText || response.statusText}`,
        }
      }

      // 尝试解析JSON响应
      let data: any
      try {
        data = await response.json()
      } catch {
        const text = await response.text()
        const duration = performance.now() - startTime

        // 记录API成功响应
        logger.apiResponse(method, endpoint, response.status, duration)

        return {
          status: 'success',
          data: text as T,
        }
      }

      const duration = performance.now() - startTime
      // 记录API成功响应
      logger.apiResponse(method, endpoint, response.status, duration)

      return {
        status: 'success',
        data,
      }
    } catch (error) {
      const duration = performance.now() - startTime
      console.error('API Request Error:', error)

      // 记录API异常
      logger.apiError(method, endpoint, error)

      return {
        status: 'error',
        error: error instanceof Error ? error.message : 'Network error',
      }
    }
  }

  /**
   * 发送聊天查   * 优先 V2 API > V1 Agent > LLM Chat
   *
   * 路由逻辑:
   * 1. 如果 use_v2=true (默认)，使V2 API (AgentV2 DeepAgents)
   * 2. 如果提供connection_id ?use_v2=false，使V1 Agent 查询
   * 3. 否则使用 LLM Chat Completions API
   */
  async sendQuery(request: ChatQueryRequest): Promise<ApiResponse<ChatQueryResponse>> {
    try {
      console.log('[ApiClient] 发送查询请', request)
      console.log('[ApiClient] API Base URL:', this.baseURL)

      // 默认使用 V2 (除非明确设置 use_v2=false)
      const useV2 = request.use_v2 !== false

      // 如果启用 V2，使V2 API
      if (useV2) {
        console.log('[ApiClient] 使用 AgentV2 查询')
        return await this.sendV2Query(request)
      }

      // 如果提供connection_id，使V1 Agent 查询端点
      if (request.connection_id) {
        return await this.sendAgentQuery(request)
      }

      // 否则使用 LLM Chat Completions API（原有逻辑）
      // 构建消息列表，包含历史消息
      // 注意：不添加系统提示词，让后端根据数据源上下文构建完整的系统提示
      const messages: ChatMessage[] = []

      // 添加历史对话消息（保持上下文）
      if (request.history && request.history.length > 0) {
        // 限制历史消息数量，避免超出token限制（保留最近的20条消息）
        const recentHistory = request.history.slice(-20)
        for (const msg of recentHistory) {
          if (msg.role !== 'system') {  // 跳过历史中的system消息
            messages.push({
              role: msg.role,
              content: msg.content
            })
          }
        }
        console.log(`[ApiClient] 包含 ${recentHistory.length} 条历史消息`)
      }

      // 添加当前用户消息
      messages.push({
        role: 'user',
        content: request.query
      })

      // 转换为LLM Chat Completions格式
      // 注意：不指定 model，让后端使用默认配置（智谱 GLM-4）
      const chatRequest: ChatCompletionRequest = {
        messages,
        // model 不指定，使用后端默认配置
        temperature: 0.7,
        stream: false,
        enable_thinking: false,  // 禁用思考模式以加快响应速度
        data_source_ids: request.context?.data_sources,  // 传递数据源ID
        use_agent: false,  // 禁用 LangGraph Agent 模式，使用直接LLM调用
      }

      console.log('[ApiClient] 转换后的请求, 消息数量:', chatRequest.messages.length, '数据', chatRequest.data_source_ids, 'Agent模式:', chatRequest.use_agent)

      const response = await this.request<BackendChatCompletionResponse>('/llm/chat/completions', {
        method: 'POST',
        body: JSON.stringify(chatRequest),
      })

      console.log('[ApiClient] 收到响应:', response)

      // 转换响应格式以兼容现有代码
      if (response.status === 'success' && response.data) {
        const llmResponse = response.data

        // 后端返回的是简化格式，直接使用 content 字段
        const answer = llmResponse.content || '抱歉，我现在无法回答这个问题'

        console.log('[ApiClient] 解析成功, answer:', answer.substring(0, 100))

        return {
          status: 'success',
          data: {
            answer,
            sources: [],
            reasoning: llmResponse.thinking,
            confidence: 0.9,
            execution_time: 0
          }
        }
      }

      // 如果响应状态不是 success，返回错误
      console.error('[ApiClient] API返回错误:', response)
      return response as unknown as ApiResponse<ChatQueryResponse>

    } catch (error) {
      console.error('[ApiClient] 发送查询失', error)
      return {
        status: 'error',
        error: error instanceof Error ? error.message : '发送查询失败',
        data: undefined
      }
    }
  }

  /**
   * 发Agent 查询（使/query 端点   * 使用 LangGraph SQL Agent 进行智能数据分析
   */
  async sendAgentQuery(request: ChatQueryRequest): Promise<ApiResponse<ChatQueryResponse>> {
    try {
      console.log('[ApiClient] 发Agent 查询请求:', request)

      // 构建 QueryRequest
      // 注意：后端 Agent 查询实际路径为 /api/v1/agent/query
      // 这里只构造请求体，路径在下面的 this.request 调用中指定
      const queryRequest = {
        query: request.query,
        connection_id: request.connection_id,  // 保持字符串类型
        session_id: request.session_id,        // 传递 session_id 用于多轮对话上下文（如图表拆分）
        enable_cache: true,
        force_refresh: false
      }

      console.log('[ApiClient] Agent 查询请求', queryRequest)

      // 后端实际路由使用 /query，携connection_id 即会Agent 分支
      const response = await this.request<any>('/query', {
        method: 'POST',
        body: JSON.stringify(queryRequest),
      })

      console.log('[ApiClient] Agent 查询响应:', response)

      // 转换响应格式（兼容两种返回格式）
      if (response.status === 'success' && response.data) {
        const queryResponse = response.data

        // 兼容两种结构        // 1) 旧版 QueryV3: { explanation, generated_sql, results, row_count, confidence_score, processing_time_ms, ... }
        // 2) 新版 Agent:   { success, data: { answer, sql, data, chart, analysis, insights, execution_time, ... }, error }
        const top = queryResponse
        const nested = queryResponse?.data

        // 文本答案优先级：
        // 1) 顶层 answer（例如：后端直接返回 answer 字段        // 2) data.answer（Agent 典型格式        // 3) 顶层 explanation / data.explanation
        // 4) 顶层 generated_sql / data.generated_sql
        let answer =
          top?.answer ??
          nested?.answer ??
          top?.explanation ??
          nested?.explanation ??
          top?.generated_sql ??
          nested?.generated_sql ??
          ''

        // 如果没有任何可用文本，尝试使用错误信息，否则使用兜底文案
        if (!answer) {
          const rawError = nested?.error || top?.error

          // 将常见的后端错误翻译为更友好的提示
          const normalizeError = (msg?: string) => {
            if (!msg) return ''
            const lower = msg.toLowerCase()
            if (lower.includes('no such file or directory') || lower.includes('errno 2')) {
              return `后端执行失败：缺少必要的文件或目录（${msg}）。请检Agent 依赖/临时目录是否存在。`
            }
            return msg
          }

          const friendlyError = normalizeError(rawError)

          if (friendlyError) {
            answer = `查询失败: ${friendlyError}`
          } else {
            answer = '查询已执行，但未返回解释或数据'
          }
        }

        // 如果有查询结果，尽量给出一个简要的“有数据”提示，避免静默
        let formattedAnswer = answer
        const tableData = nested?.data || top?.results
        const rowCount: number =
          (nested?.data && typeof nested.data.row_count === 'number' ? nested.data.row_count : undefined) ??
          (typeof top?.row_count === 'number' ? top.row_count : undefined) ??
          (Array.isArray(tableData) ? tableData.length : 0)

        if (rowCount && rowCount > 0) {
          formattedAnswer += `\n\n查询结果已生成（${rowCount} 行），已在下方以表格/图表形式展示。`
        }

        // 统一提取结构化表格数据
        let table: ChatQueryResultTable | undefined
        if (nested?.data && Array.isArray(nested.data.rows) && Array.isArray(nested.data.columns)) {
          table = {
            columns: nested.data.columns as string[],
            rows: nested.data.rows as Record<string, unknown>[],
            row_count: typeof nested.data.row_count === 'number'
              ? nested.data.row_count
              : nested.data.rows.length,
          }
        } else if (Array.isArray(top?.results)) {
          const rows = top.results as Record<string, unknown>[]
          const columns = rows.length > 0 ? Object.keys(rows[0]) : []
          table = {
            columns,
            rows,
            row_count: typeof top.row_count === 'number' ? top.row_count : rows.length,
          }
        }

        // 统一提取图表信息
        let chart: ChatQueryChart | undefined
        const topExecution = top?.execution_result
        if (nested?.chart || topExecution) {
          // 将 echarts_option JSON 对象转换为字符串（用于 DynamicChart 组件）
          const echartsOption =
            nested?.echarts_option ??
            nested?.data?.echarts_option ??
            top?.echarts_option ??
            topExecution?.echarts_option ??
            undefined

          chart = {
            chart_type: nested?.chart?.chart_type || topExecution?.chart_type,
            title: nested?.chart?.title || topExecution?.chart_title,
            x_field: nested?.chart?.x_field,
            y_field: nested?.chart?.y_field,
            // 优先使用 echarts_option，转换为 JSON 字符串
            chart_config: echartsOption ? JSON.stringify(echartsOption) : undefined,
            // 回退到静态图
            chart_image: nested?.chart?.chart_image ?? topExecution?.chart_data ?? null,
          }
        }

        // 推理/解释：优先使用显reasoning / explanation 字段
        const reasoning =
          nested?.reasoning ??
          top?.reasoning ??
          nested?.explanation ??
          top?.explanation

        // 置信度：兼容旧字段和可能的扩展字段
        const confidence =
          (typeof nested?.confidence === 'number' ? nested.confidence : undefined) ??
          (typeof top?.confidence === 'number' ? top.confidence : undefined) ??
          (typeof top?.confidence_score === 'number' ? top.confidence_score : undefined) ??
          (typeof nested?.confidence_score === 'number' ? nested.confidence_score : undefined) ??
          0.8

        // 执行时间：兼processing_time_ms / execution_time
        const executionTime =
          (typeof nested?.execution_time === 'number' ? nested.execution_time : undefined) ??
          (typeof top?.execution_time === 'number' ? top.execution_time : undefined) ??
          (typeof top?.processing_time_ms === 'number' ? top.processing_time_ms : undefined) ??
          (typeof nested?.processing_time_ms === 'number' ? nested.processing_time_ms : undefined) ??
          0

        // 提取 ECharts 配置选项（用于前端直接渲染图表）
        // 确保从后端响应的所有可能位置提取：
        // 1. data.echarts_option（嵌套数据中的顶层）
        // 2. data.data?.echarts_option（深层嵌套）
        // 3. top.echarts_option（响应顶层）
        // 4. execution_result.echarts_option（执行结果中）
        const echartsOption =
          nested?.echarts_option ??
          nested?.data?.echarts_option ??
          top?.echarts_option ??
          topExecution?.echarts_option ??
          undefined

        // 调试日志（仅在开发环境）
        if (process.env.NODE_ENV === 'development' && echartsOption) {
          console.log('[ApiClient] ?ECharts option extracted:', {
            hasOption: !!echartsOption,
            keys: Object.keys(echartsOption || {}),
            source: nested?.echarts_option ? 'nested' :
                   nested?.data?.echarts_option ? 'nested.data' :
                   top?.echarts_option ? 'top' :
                   topExecution?.echarts_option ? 'execution_result' : 'unknown'
          })
        }

        return {
          status: 'success',
          data: {
            answer: formattedAnswer,
            sources: [],
            reasoning,
            confidence,
            execution_time: executionTime,
            table,
            chart,
            echarts_option: echartsOption,  // 添加 ECharts 配置选项
          }
        }
      }

      // 如果响应状态不是 success，返回错误
      console.error('[ApiClient] Agent 查询返回错误:', response)
      return response as ApiResponse<ChatQueryResponse>

    } catch (error) {
      console.error('[ApiClient] Agent 查询失败:', error)
      return {
        status: 'error',
        error: error instanceof Error ? error.message : 'Agent 查询失败',
        data: undefined
      }
    }
  }

  /**
   * 发V2 查询（使AgentV2 DeepAgents 框架   * 新版查询端点，基AgentV2 架构
   */
  async sendV2Query(request: ChatQueryRequest): Promise<ApiResponse<ChatQueryResponse>> {
    // 🔧 添加超时控制器（120秒）
    const QUERY_TIMEOUT = 120000  // 120秒
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), QUERY_TIMEOUT)

    try {
      console.log('[ApiClient] 发V2 查询请求:', request)

      // 构建 V2 查询请求
      const queryRequest = {
        query: request.query,
        connection_id: request.connection_id,
        session_id: request.session_id,
        max_results: request.context?.max_results || 100,
        include_chart: true,  // 🔧 启用图表生成
      }

      console.log('[ApiClient] V2 查询请求', queryRequest)

      // 使用 V2 端点
      const url = `${this.v2BaseURL}/query/`
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          ...this.defaultHeaders,
        },
        body: JSON.stringify(queryRequest),
        signal: controller.signal,  // 🔧 添加超时信号
      })

      // 🔧 清除超时定时      clearTimeout(timeoutId)

      console.log('[ApiClient] V2 查询响应状', response.status)

      if (!response.ok) {
        const errorText = await response.text()
        return {
          status: 'error',
          error: `HTTP ${response.status}: ${errorText || response.statusText}`,
        }
      }

      const data = await response.json()
      console.log('[ApiClient] V2 查询响应数据:', data)

      // 转换 V2 响应格式为通用格式
      if (data.success && data.answer) {
        return {
          status: 'success',
          data: {
            answer: data.answer,
            sources: [],
            reasoning: data.reasoning_log ? JSON.stringify(data.reasoning_log) : undefined,
            confidence: 0.9,
            execution_time: data.processing_time_ms,
            table: data.data ? {
              columns: [],
              rows: data.data,
              row_count: data.row_count || 0,
            } : undefined,
            chart: data.chart_config,
            echarts_option: data.chart_config,
          }
        }
      }

      return {
        status: 'error',
        error: data.error || '查询失败',
      }

    } catch (error: any) {
      // 🔧 清除超时定时      clearTimeout(timeoutId)

      console.error('[ApiClient] V2 查询失败:', error)

      // 🔧 处理超时错误
      if (error.name === 'AbortError') {
        return {
          status: 'error',
          error: '请求超时（超20秒），请简化查询条件或稍后重试',
          data: undefined
        }
      }

      return {
        status: 'error',
        error: error instanceof Error ? error.message : 'V2 查询失败',
        data: undefined
      }
    }
  }

  /**
   * V2 流式查询（使AgentV2 深度代理 + Server-Sent Events?   *
   * ## 功能
   * - 实时流式输出查询结果
   * - 推送处理步骤更   * - 显示进度百分   * - 支持取消操作
   *
   * ## 事件类型
   * - `start`: 查询开   * - `step`: 处理步骤更新
   * - `progress`: 进度更新 (0-100)
   * - `data`: 答案数据   * - `error`: 错误信息
   * - `done`: 完成信号
   *
   * @param request 查询请求
   * @param callbacks V2流式事件回调
   * @param abortSignal 可选的取消信号
   * @returns AbortController 用于中断请求
   */
  async streamV2Query(
    request: ChatQueryRequest,
    callbacks: V2StreamCallbacks,
    abortSignal?: AbortSignal
  ): Promise<AbortController> {
    const controller = new AbortController()
    const signal = abortSignal || controller.signal

    // 🔧 添加前端超时保护（120秒）
    const QUERY_TIMEOUT = 120000  // 120秒（毫秒）
    let timeoutId: NodeJS.Timeout | undefined

    // 创建超时控制器
    const timeoutController = new AbortController()
    const combinedSignal = abortSignal || controller.signal

    // 设置超时定时器
    timeoutId = setTimeout(() => {
      timeoutController.abort()
      callbacks.onError?.({
        error: '请求超时',
        error_type: 'timeout',
        detail: '查询时间过长（超过120秒），请稍后重试或简化查询条件',
      })
      console.warn('[ApiClient] V2 流式查询超时')
    }, QUERY_TIMEOUT)

    try {
      console.log('[ApiClient] 发V2 流式查询请求:', request)

      // 构建 V2 流式查询请求
      const queryRequest = {
        query: request.query,
        connection_id: request.connection_id,
        session_id: request.session_id,
        max_results: request.context?.max_results || 100,
        include_chart: true,  // 🔧 启用图表生成
      }

      // 使用 V2 流式端点
      const url = `${this.v2BaseURL}/query/stream`

      // 从localStorage获取token
      let token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
      if (!token && process.env.NODE_ENV === 'development') {
        token = 'dev_token'
      }

      // 🔧 链接超时信号fetch - 使用组合信号
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify(queryRequest),
        signal: combinedSignal,
      })

      // 🔧 清除超时定时器（请求已成功发送）
      if (timeoutId) {
        clearTimeout(timeoutId)
        timeoutId = undefined
      }

      if (!response.ok) {
        const errorText = await response.text()
        callbacks.onError?.({
          error: `HTTP ${response.status}`,
          detail: errorText || response.statusText,
        })
        return controller
      }

      // 检查响应类型是否为text/event-stream
      const contentType = response.headers.get('content-type')
      if (!contentType?.includes('text/event-stream')) {
        callbacks.onError?.({
          error: '服务器未返回流式响应',
          error_type: 'invalid_response_type',
        })
        return controller
      }

      // 读取流式响应
      const reader = response.body?.getReader()
      if (!reader) {
        callbacks.onError?.({
          error: '无法读取响应',
          error_type: 'stream_read_error',
        })
        return controller
      }

      // 🔧 改进 SSE 解析：使用缓冲区正确处理跨数据包分片
      const decoder = new TextDecoder()
      let buffer = ''  // 缓冲区累积未处理的数据
      let currentEventType = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) break

        // 解码并累积到缓冲区
        buffer += decoder.decode(value, { stream: true })

        // 按双换行符分割完整事件（SSE 事件以 \n\n 结尾）
        const eventBoundary = '\n\n'
        let eventEndIndex: number

        while ((eventEndIndex = buffer.indexOf(eventBoundary)) !== -1) {
          // 提取完整事件
          const eventBlock = buffer.slice(0, eventEndIndex)
          buffer = buffer.slice(eventEndIndex + eventBoundary.length)

          // 解析事件块中的各行
          const lines = eventBlock.split('\n')
          let eventData = ''

          for (const line of lines) {
            if (line.startsWith('event:')) {
              currentEventType = line.slice(6).trim()
            } else if (line.startsWith('data:')) {
              // 支持多行 data（虽然通常是单行）
              eventData += (eventData ? '\n' : '') + line.slice(5).trim()
            }
          }

          // 只有当有数据时才解析和触发回调
          if (eventData) {
            try {
              const data = JSON.parse(eventData)

              switch (currentEventType) {
                case 'start':
                  callbacks.onStart?.(data)
                  break
                case 'step':
                  callbacks.onStep?.(data)
                  break
                case 'progress':
                  callbacks.onProgress?.(data)
                  break
                case 'data':
                  callbacks.onData?.(data)
                  break
                case 'done':
                  callbacks.onDone?.(data)
                  break
                case 'error':
                  callbacks.onError?.(data)
                  break
                default:
                  if (currentEventType) {
                    console.log('[ApiClient] 未知事件类型:', currentEventType, data)
                  }
              }
            } catch (parseError) {
              // 仅在非空数据时记录错误，避免解析空字符串的噪音日志
              if (eventData.trim()) {
                console.error('[ApiClient] 解析事件数据失败:', parseError, eventData.substring(0, 100))
              }
            }
          }
        }
      }

    } catch (error: any) {
      // 🔧 清除超时定时器
      if (timeoutId) {
        clearTimeout(timeoutId)
        timeoutId = undefined
      }

      if (error.name !== 'AbortError') {
        console.error('[ApiClient] V2 流式查询错误:', error)
        callbacks.onError?.({
          error: error.message || '流式查询失败',
          error_type: 'network_error',
          detail: error.message
        })
      }
    }

    return controller
  }

  /**
   * V1 流式查询（使AgentV1 + Server-Sent Events?   *
   * ## 功能
   * - 实时流式输出查询结果
   * - 推送处理步骤更   * - Token 级别的内容流式输   *
   * ## 事件类型
   * - `start`: 查询开   * - `step`: 处理步骤更新
   * - `content`: AI生成的内容增   * - `tool_start`: 工具调用开   * - `tool_end`: 工具调用结束
   * - `error`: 错误信息
   * - `done`: 完成信号
   *
   * @param request 查询请求
   * @param callbacks V1流式事件回调（使用相同的 StreamCallbacks?   * @param abortSignal 可选的取消信号
   * @returns AbortController 用于中断请求
   */
  async streamV1Query(
    request: ChatQueryRequest,
    callbacks: V2StreamCallbacks,
    abortSignal?: AbortSignal
  ): Promise<AbortController> {
    const controller = new AbortController()
    const signal = abortSignal || controller.signal

    // 添加前端超时保护（120秒）
    const QUERY_TIMEOUT = 120000  // 120秒（毫秒）
    let timeoutId: NodeJS.Timeout | undefined

    // 创建超时控制器
    const timeoutController = new AbortController()
    const combinedSignal = abortSignal || controller.signal

    // 设置超时定时器
    timeoutId = setTimeout(() => {
      timeoutController.abort()
      callbacks.onError?.({
        error: '请求超时',
        error_type: 'timeout',
        detail: '查询时间过长（超过120秒），请稍后重试或简化查询条件',
      })
      console.warn('[ApiClient] V1 流式查询超时')
    }, QUERY_TIMEOUT)

    try {
      console.log('[ApiClient] 发V1 流式查询请求:', request)

      // 构建 V1 流式查询请求
      const queryRequest = {
        query: request.query,
        connection_id: request.connection_id,
        session_id: request.session_id,
        db_type: 'postgresql',  // 默认数据库类型
      }

      // 使用 V1 流式端点
      const url = `${this.baseURL}/llm/query/stream`

      // 从localStorage获取token
      let token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null
      if (!token && process.env.NODE_ENV === 'development') {
        token = 'dev_token'
      }

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify(queryRequest),
        signal: combinedSignal,
      })

      // 清除超时定时器（请求已发送）
      if (timeoutId) {
        clearTimeout(timeoutId)
        timeoutId = undefined
      }

      if (!response.ok) {
        const errorText = await response.text()
        callbacks.onError?.({
          error: `HTTP ${response.status}`,
          detail: errorText || response.statusText,
        })
        return controller
      }

      // 检查响应类型
      const contentType = response.headers.get('content-type')
      if (!contentType?.includes('text/event-stream')) {
        callbacks.onError?.({
          error: '服务器未返回流式响应',
          error_type: 'invalid_response_type',
        })
        return controller
      }

      // 读取流式响应
      const reader = response.body?.getReader()
      if (!reader) {
        callbacks.onError?.({
          error: '无法读取响应',
          error_type: 'stream_read_error',
        })
        return controller
      }

      // SSE 解析
      const decoder = new TextDecoder()
      let buffer = ''
      let currentEventType = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // 按双换行符分割完整事件
        const eventBoundary = '\n\n'
        let eventEndIndex: number

        while ((eventEndIndex = buffer.indexOf(eventBoundary)) !== -1) {
          const eventBlock = buffer.slice(0, eventEndIndex)
          buffer = buffer.slice(eventEndIndex + eventBoundary.length)

          const lines = eventBlock.split('\n')
          let eventData = ''

          for (const line of lines) {
            if (line.startsWith('event:')) {
              currentEventType = line.slice(6).trim()
            } else if (line.startsWith('data:')) {
              eventData += (eventData ? '\n' : '') + line.slice(5).trim()
            }
          }

          if (eventData) {
            try {
              const data = JSON.parse(eventData)

              switch (currentEventType) {
                case 'start':
                  callbacks.onStart?.(data)
                  break
                case 'step':
                  callbacks.onStep?.(data)
                  break
                case 'content':
                  // V1 ?content 事件包含 content ?accumulated 字段
                  callbacks.onData?.(data)
                  break
                case 'tool_start':
                  callbacks.onStep?.(data)
                  break
                case 'tool_end':
                  callbacks.onStep?.(data)
                  break
                case 'done':
                  callbacks.onDone?.(data)
                  break
                case 'error':
                  callbacks.onError?.(data)
                  break
                default:
                  if (currentEventType) {
                    console.log('[ApiClient] V1 未知事件类型:', currentEventType, data)
                  }
              }
            } catch (parseError) {
              if (eventData.trim()) {
                console.error('[ApiClient] 解析 V1 事件数据失败:', parseError, eventData.substring(0, 100))
              }
            }
          }
        }
      }

    } catch (error: any) {
      if (timeoutId) {
        clearTimeout(timeoutId)
        timeoutId = undefined
      }

      if (error.name !== 'AbortError') {
        console.error('[ApiClient] V1 流式查询错误:', error)
        callbacks.onError?.({
          error: error.message || '流式查询失败',
          error_type: 'network_error',
          detail: error.message
        })
      }
    }

    return controller
  }

  /**
   * V2 流式会话管理方法
   */

  /**
   * 获取 V2 流式会话状   * @param sessionId 会话ID
   */
  async getV2SessionState(sessionId: string): Promise<V2SessionState> {
    const response = await fetch(`${this.v2BaseURL}/query/stream/session/${sessionId}`)
    if (!response.ok) {
      throw new Error(`获取会话状态失 ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * 暂停 V2 流式查询
   * @param sessionId 会话ID
   */
  async pauseV2Session(sessionId: string): Promise<V2PauseResponse> {
    const response = await fetch(`${this.v2BaseURL}/query/stream/session/${sessionId}/pause`, {
      method: 'POST',
    })
    if (!response.ok) {
      throw new Error(`暂停会话失败: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * 恢复 V2 流式查询
   * @param sessionId 会话ID
   */
  async resumeV2Session(sessionId: string): Promise<V2ResumeResponse> {
    const response = await fetch(`${this.v2BaseURL}/query/stream/session/${sessionId}/resume`, {
      method: 'POST',
    })
    if (!response.ok) {
      throw new Error(`恢复会话失败: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * 取消 V2 流式查询
   * @param sessionId 会话ID
   */
  async cancelV2Session(sessionId: string): Promise<V2CancelResponse> {
    const response = await fetch(`${this.v2BaseURL}/query/stream/session/${sessionId}`, {
      method: 'DELETE',
    })
    if (!response.ok) {
      throw new Error(`取消会话失败: ${response.statusText}`)
    }
    return response.json()
  }

  /**
   * 获取会话列表
   */
  async getSessions(): Promise<ApiResponse<ChatSession[]>> {
    return this.request<ChatSession[]>('/chat/sessions')
  }

  /**
   * 创建新会   */
  async createSession(title: string): Promise<ApiResponse<ChatSession>> {
    return this.request<ChatSession>('/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({ title }),
    })
  }

  /**
   * 删除会话
   */
  async deleteSession(sessionId: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/chat/sessions/${sessionId}`, {
      method: 'DELETE',
    })
  }

  /**
   * 清空会话历史
   */
  async clearHistory(sessionId: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/chat/sessions/${sessionId}/messages`, {
      method: 'DELETE',
    })
  }

  /**
   * 获取会话详情
   */
  async getSession(sessionId: string): Promise<ApiResponse<ChatSession>> {
    return this.request<ChatSession>(`/chat/sessions/${sessionId}`)
  }

  /**
   * 流式聊天完成接口（新版本 - 使用回调方式   * 支持SSE流式调用，使用回调函数处理事   * @param request 聊天完成请求
   * @param callbacks 流式事件回调
   * @param abortSignal 可选的取消信号
   * @returns AbortController 用于中断请求
   */
  async streamChatCompletionWithCallbacks(
    request: ChatCompletionRequest,
    callbacks: StreamCallbacks,
    abortSignal?: AbortSignal
  ): Promise<AbortController> {
    const controller = new AbortController()
    const signal = abortSignal || controller.signal

    try {
      const url = `${this.baseURL}/llm/chat/completions`

      // 从localStorage获取token
      let token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null

      // 开发环境：如果没有token，使用开发token
      if (!token && process.env.NODE_ENV === 'development') {
        token = 'dev_token'
      }

      // 确保stream为true
      const streamRequest = {
        ...request,
        stream: true,
      }

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify(streamRequest),
        signal,
      })

      if (!response.ok) {
        const errorText = await response.text()
        callbacks.onError(`HTTP ${response.status}: ${errorText || response.statusText}`)
        return controller
      }

      // 检查响应类型是否为text/event-stream
      const contentType = response.headers.get('content-type')
      if (!contentType?.includes('text/event-stream')) {
        callbacks.onError('服务器未返回流式响应')
        return controller
      }

      // 读取流式响应
      const reader = response.body?.getReader()
      if (!reader) {
        callbacks.onError('无法读取响应')
        return controller
      }

      // 使用新的解析器处理流
      await parseStreamResponse(reader, callbacks, signal)

    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('[ApiClient] 流式请求错误:', error)
        callbacks.onError(error.message || '流式请求失败')
      }
    }

    return controller
  }

  /**
   * 流式聊天完成接口（旧版本 - 保持向后兼容   * 支持SSE流式调用，返回异步生成器
   * @deprecated 建议使用 streamChatCompletionWithCallbacks
   */
  async *streamChatCompletion(
    request: ChatCompletionRequest,
    abortSignal?: AbortSignal
  ): AsyncGenerator<StreamEvent, void, unknown> {
    // 为了向后兼容，保留原有实    // 但内部使用新的解析器
    const events: StreamEvent[] = []
    let isDone = false
    let error: string | null = null

    const callbacks: StreamCallbacks = {
      onContent: (delta) => {
        events.push({ type: 'content', content: delta, finished: false })
      },
      onThinking: (delta) => {
        events.push({ type: 'thinking', thinking: delta, finished: false })
      },
      onToolInput: (toolName, args) => {
        events.push({ type: 'tool_input', tool_input: args, finished: false })
      },
      onToolResult: (data) => {
        events.push({ type: 'tool_result', data, finished: false })
      },
      onChartConfig: (data) => {
        events.push({ type: 'chart_config', data, finished: false })
      },
      onProcessingStep: (step) => {
        events.push({ type: 'processing_step', step, finished: false })
      },
      onError: (err) => {
        error = err
        events.push({ type: 'error', error: err, finished: true })
      },
      onDone: () => {
        isDone = true
        events.push({ type: 'done', finished: true })
      },
    }

    // 启动流式解析（不等待完成    this.streamChatCompletionWithCallbacks(request, callbacks, abortSignal)

    // 轮询并yield事件
    while (!isDone && !error) {
      while (events.length > 0) {
        yield events.shift()!
      }
      await new Promise(resolve => setTimeout(resolve, 10)) // 短暂延迟
    }

    // 处理剩余事件
    while (events.length > 0) {
      yield events.shift()!
    }
  }

  /**
   * 健康检   */
  async healthCheck(): Promise<ApiResponse<{
    status: string
    services: Record<string, boolean>
    timestamp: string
  }>> {
    return this.request('/health/status')
  }

  /**
   * 测试数据源连   */
  async testDataSource(dataSourceId: string): Promise<ApiResponse<{
    status: 'success' | 'error'
    message: string
    latency?: number
  }>> {
    return this.request(`/data-sources/${dataSourceId}/test`, {
      method: 'POST',
    })
  }

  /**
   * 获取数据源列   */
  async getDataSources(tenantId?: string): Promise<ApiResponse<any[]>> {
    const tenant = tenantId || 'default_tenant'
    return this.request<any[]>(`/data-sources?tenant_id=${tenant}`)
  }

  /**
   * 创建数据   */
  async createDataSource(dataSource: {
    name: string
    connection_type: string
    connection_string: string
    description?: string
  }): Promise<ApiResponse<any>> {
    return this.request<any>('/data-sources', {
      method: 'POST',
      body: JSON.stringify(dataSource),
    })
  }

  /**
   * 获取文档列表
   */
  async getDocuments(): Promise<ApiResponse<any[]>> {
    return this.request<any[]>('/documents')
  }

  /**
   * 上传文档
   */
  async uploadDocument(file: File): Promise<ApiResponse<any>> {
    const formData = new FormData()
    formData.append('file', file)

    return this.request<any>('/documents', {
      method: 'POST',
      body: formData,
      headers: {}, // 不设置Content-Type，让浏览器自动设置multipart/form-data
    })
  }

  /**
   * 删除文档
   */
  async deleteDocument(documentId: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/documents/${documentId}`, {
      method: 'DELETE',
    })
  }

  // ============================================================
  // Agent API 方法
  // ============================================================

  /**
   * 发Agent 查询
   * 使用 LangGraph Agent 进行智能数据分析
   */
  async agentQuery(request: AgentQueryRequest): Promise<ApiResponse<AgentQueryResponse>> {
    try {
      console.log('[ApiClient] Agent 查询请求:', request)

      // 添加 tenant_id 作为查询参数
      const tenantId = this.tenantId || 'default_tenant'
      const response = await this.request<AgentQueryResponse>(`/agent/query?tenant_id=${tenantId}`, {
        method: 'POST',
        body: JSON.stringify(request),
      })

      console.log('[ApiClient] Agent 响应:', response)
      return response

    } catch (error) {
      console.error('[ApiClient] Agent 查询失败:', error)
      return {
        status: 'error',
        error: error instanceof Error ? error.message : 'Agent query failed',
      }
    }
  }

  /**
   * 重置 Agent
   */
  async resetAgent(dataSourceId: string): Promise<ApiResponse<{ success: boolean; message: string }>> {
    return this.request<{ success: boolean; message: string }>(`/agent/reset/${dataSourceId}`, {
      method: 'POST',
    })
  }

  // ============================================================
  // 日志 API 方法
  // ============================================================

  /**
   * 获取指定会话的后端日   */
  async getSessionLogs(sessionId: string, limit = 100): Promise<ApiResponse<any>> {
    return this.request(`/logs/backend/session/${sessionId}?limit=${limit}`)
  }

  /**
   * 获取最近的后端日志
   */
  async getRecentLogs(limit = 100, level?: string): Promise<ApiResponse<any>> {
    const params = new URLSearchParams({ limit: limit.toString() })
    if (level) params.append('level', level)
    return this.request(`/logs/backend/recent?${params.toString()}`)
  }

  /**
   * 获取错误日志
   */
  async getErrorLogs(limit = 50, hours?: number): Promise<ApiResponse<any>> {
    const params = new URLSearchParams({ limit: limit.toString() })
    if (hours) params.append('hours', hours.toString())
    return this.request(`/logs/backend/errors?${params.toString()}`)
  }

  /**
   * 获取后端日志摘要
   */
  async getLogSummary(): Promise<ApiResponse<any>> {
    return this.request('/logs/backend/summary')
  }

  // ============================================================
  // 日志流式查询方法 (SSE)
  // ============================================================

  /**
   * 流式获取会话日志
   */
  async streamSessionLogs(
    sessionId: string,
    callbacks: LogStreamCallbacks,
    options?: {
      limit?: number;
      batch_size?: number;
      abortSignal?: AbortSignal;
    }
  ): Promise<AbortController> {
    const controller = new AbortController();
    const signal = options?.abortSignal || controller.signal;

    try {
      const params = new URLSearchParams({
        limit: String(options?.limit ?? 100),
        batch_size: String(options?.batch_size ?? 50),
      });

      const response = await fetch(
        `${this.baseURL}/logs/backend/session/${sessionId}/stream?${params}`,
        {
          headers: { ...this.defaultHeaders, 'Accept': 'text/event-stream' },
          signal,
        }
      );

      if (!response.ok) {
        callbacks.onError?.({
          type: 'error',
          error: `HTTP ${response.status}`,
          error_type: 'network_error',
          detail: response.statusText,
        });
        return controller;
      }

      await this._processLogStream(response, callbacks);
      return controller;
    } catch (error: unknown) {
      if ((error as Error).name !== 'AbortError') {
        callbacks.onError?.({
          type: 'error',
          error: (error as Error).message || '流式请求失败',
          error_type: 'network_error',
          detail: (error as Error).message,
        });
      }
      return controller;
    }
  }

  /**
   * 流式获取最近日   */
  async streamRecentLogs(
    callbacks: LogStreamCallbacks,
    options?: {
      limit?: number;
      level?: string;
      batch_size?: number;
      abortSignal?: AbortSignal;
    }
  ): Promise<AbortController> {
    const controller = new AbortController();
    const signal = options?.abortSignal || controller.signal;

    try {
      const params = new URLSearchParams({
        limit: String(options?.limit ?? 100),
        batch_size: String(options?.batch_size ?? 50),
        ...(options?.level && { level: options.level }),
      });

      const response = await fetch(
        `${this.baseURL}/logs/backend/recent/stream?${params}`,
        {
          headers: { ...this.defaultHeaders, 'Accept': 'text/event-stream' },
          signal,
        }
      );

      if (!response.ok) {
        callbacks.onError?.({
          type: 'error',
          error: `HTTP ${response.status}`,
          error_type: 'network_error',
          detail: response.statusText,
        });
        return controller;
      }

      await this._processLogStream(response, callbacks);
      return controller;
    } catch (error: unknown) {
      if ((error as Error).name !== 'AbortError') {
        callbacks.onError?.({
          type: 'error',
          error: (error as Error).message || '流式请求失败',
          error_type: 'network_error',
        });
      }
      return controller;
    }
  }

  /**
   * 流式获取错误日志
   */
  async streamErrorLogs(
    callbacks: LogStreamCallbacks,
    options?: {
      limit?: number;
      hours?: number;
      batch_size?: number;
      abortSignal?: AbortSignal;
    }
  ): Promise<AbortController> {
    const controller = new AbortController();
    const signal = options?.abortSignal || controller.signal;

    try {
      const params = new URLSearchParams({
        limit: String(options?.limit ?? 50),
        batch_size: String(options?.batch_size ?? 50),
        ...(options?.hours && { hours: String(options.hours) }),
      });

      const response = await fetch(
        `${this.baseURL}/logs/backend/errors/stream?${params}`,
        {
          headers: { ...this.defaultHeaders, 'Accept': 'text/event-stream' },
          signal,
        }
      );

      if (!response.ok) {
        callbacks.onError?.({
          type: 'error',
          error: `HTTP ${response.status}`,
          error_type: 'network_error',
          detail: response.statusText,
        });
        return controller;
      }

      await this._processLogStream(response, callbacks);
      return controller;
    } catch (error: unknown) {
      if ((error as Error).name !== 'AbortError') {
        callbacks.onError?.({
          type: 'error',
          error: (error as Error).message || '流式请求失败',
          error_type: 'network_error',
        });
      }
      return controller;
    }
  }

  /**
   * 流式获取日志摘要
   */
  async streamLogSummary(
    callbacks: LogStreamCallbacks,
    abortSignal?: AbortSignal
  ): Promise<AbortController> {
    const controller = new AbortController();
    const signal = abortSignal || controller.signal;

    try {
      const response = await fetch(
        `${this.baseURL}/logs/backend/summary/stream`,
        {
          headers: { ...this.defaultHeaders, 'Accept': 'text/event-stream' },
          signal,
        }
      );

      if (!response.ok) {
        callbacks.onError?.({
          type: 'error',
          error: `HTTP ${response.status}`,
          error_type: 'network_error',
          detail: response.statusText,
        });
        return controller;
      }

      await this._processLogStream(response, callbacks);
      return controller;
    } catch (error: unknown) {
      if ((error as Error).name !== 'AbortError') {
        callbacks.onError?.({
          type: 'error',
          error: (error as Error).message || '流式请求失败',
          error_type: 'network_error',
        });
      }
      return controller;
    }
  }

  /**
   * 处理日志 SSE 流响   */
  private async _processLogStream(
    response: Response,
    callbacks: LogStreamCallbacks
  ): Promise<void> {
    const reader = response.body?.getReader();
    if (!reader) {
      callbacks.onError?.({
        type: 'error',
        error: '无法读取响应',
        error_type: 'stream_read_error',
      });
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const eventBoundary = '\n\n';
        let eventEndIndex: number;

        while ((eventEndIndex = buffer.indexOf(eventBoundary)) !== -1) {
          const eventBlock = buffer.slice(0, eventEndIndex);
          buffer = buffer.slice(eventEndIndex + eventBoundary.length);

          const lines = eventBlock.split('\n');
          let eventType = '';
          let eventData = '';

          for (const line of lines) {
            if (line.startsWith('event:')) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              eventData += (eventData ? '\n' : '') + line.slice(5).trim();
            }
          }

          if (eventData) {
            try {
              const data = JSON.parse(eventData);
              this._dispatchLogStreamEvent(eventType, data, callbacks);
            } catch (e) {
              console.warn('[ApiClient] 解析日志事件失败:', e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * 分发日志流式事件
   */
  private _dispatchLogStreamEvent(
    eventType: string,
    data: unknown,
    callbacks: LogStreamCallbacks
  ): void {
    switch (eventType) {
      case 'start':
        callbacks.onStart?.(data as LogStreamStartData);
        break;
      case 'progress':
        callbacks.onProgress?.(data as LogStreamProgressData);
        break;
      case 'file_status':
        callbacks.onFileStatus?.(data as LogStreamFileStatusData);
        break;
      case 'log_batch':
        callbacks.onLogBatch?.(data as LogStreamBatchData);
        break;
      case 'done':
        callbacks.onDone?.(data as LogStreamDoneData);
        break;
      case 'error':
        callbacks.onError?.(data as LogStreamErrorData);
        break;
      case 'file_info':
        callbacks.onFileInfo?.(data as LogStreamFileInfoData);
        break;
      case 'error_count':
        callbacks.onErrorCount?.(data as LogStreamErrorCountData);
        break;
      default:
        console.log('[ApiClient] 未知的日志事件类', eventType, data);
    }
  }
}

// 创建全局API客户端实例
export const apiClient = new ApiClient()
// 便捷的API函数导出
export const api = {
  chat: {
    sendQuery: (request: ChatQueryRequest) => apiClient.sendQuery(request),
    sendV2Query: (request: ChatQueryRequest) => apiClient.sendV2Query(request),
    streamChatCompletion: (
      request: ChatCompletionRequest,
      abortSignal?: AbortSignal
    ) => apiClient.streamChatCompletion(request, abortSignal),
    getSessions: () => apiClient.getSessions(),
    createSession: (title: string) => apiClient.createSession(title),
    deleteSession: (sessionId: string) => apiClient.deleteSession(sessionId),
    clearHistory: (sessionId: string) => apiClient.clearHistory(sessionId),
    getSession: (sessionId: string) => apiClient.getSession(sessionId),
  },
  agent: {
    query: (request: AgentQueryRequest) => apiClient.agentQuery(request),
    reset: (dataSourceId: string) => apiClient.resetAgent(dataSourceId),
  },
  dataSources: {
    getAll: () => apiClient.getDataSources(),
    create: (dataSource: any) => apiClient.createDataSource(dataSource),
    test: (dataSourceId: string) => apiClient.testDataSource(dataSourceId),
  },
  documents: {
    getAll: () => apiClient.getDocuments(),
    upload: (file: File) => apiClient.uploadDocument(file),
    delete: (documentId: string) => apiClient.deleteDocument(documentId),
  },
  health: () => apiClient.healthCheck(),
  // V2 API (AgentV2)
  v2: {
    query: (request: ChatQueryRequest) => apiClient.sendV2Query(request),
  },
  // 日志 API
  logs: {
    getSession: (sessionId: string, limit?: number) => apiClient.getSessionLogs(sessionId, limit),
    getRecent: (limit?: number, level?: string) => apiClient.getRecentLogs(limit, level),
    getErrors: (limit?: number, hours?: number) => apiClient.getErrorLogs(limit, hours),
    getSummary: () => apiClient.getLogSummary(),
    // 流式日志方法
    streamSession: (
      sessionId: string,
      callbacks: LogStreamCallbacks,
      options?: { limit?: number; batch_size?: number; abortSignal?: AbortSignal }
    ) => apiClient.streamSessionLogs(sessionId, callbacks, options),
    streamRecent: (
      callbacks: LogStreamCallbacks,
      options?: { limit?: number; level?: string; batch_size?: number; abortSignal?: AbortSignal }
    ) => apiClient.streamRecentLogs(callbacks, options),
    streamErrors: (
      callbacks: LogStreamCallbacks,
      options?: { limit?: number; hours?: number; batch_size?: number; abortSignal?: AbortSignal }
    ) => apiClient.streamErrorLogs(callbacks, options),
    streamSummary: (
      callbacks: LogStreamCallbacks,
      abortSignal?: AbortSignal
    ) => apiClient.streamLogSummary(callbacks, abortSignal),
  },
}




