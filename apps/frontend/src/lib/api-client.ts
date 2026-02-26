/**
 * API Client - Data Agent Backend API
 *
 * 提供与后端 FastAPI 的通信接口
 */

import type { ChatCompletionRequest, ChatQueryRequest, ChatQueryResponse, V2StreamCallbacks } from '@/types/api/chat'
import type { StreamCallbacks } from '@/types/chat'
import { responseErrorMessage } from '@/lib/api-error'
import { getStoredAuthToken } from '@/lib/auth-token'
import logger from '@/lib/logger'

const rawApiBase = process.env.NEXT_PUBLIC_API_URL

export const resolveApiBases = (base?: string) => {
  const fallbackV1 = 'http://localhost:8004/api/v1'
  const fallbackV2 = 'http://localhost:8004/api/v2'

  if (!base) {
    return { v1: fallbackV1, v2: fallbackV2 }
  }

  const normalized = base.replace(/\/+$/, '')
  if (normalized.includes('/api/v1')) {
    return { v1: normalized, v2: normalized.replace('/api/v1', '/api/v2') }
  }
  if (normalized.includes('/api/v2')) {
    return { v1: normalized.replace('/api/v2', '/api/v1'), v2: normalized }
  }
  if (normalized.endsWith('/api')) {
    return { v1: `${normalized}/v1`, v2: `${normalized}/v2` }
  }
  return { v1: `${normalized}/api/v1`, v2: `${normalized}/api/v2` }
}

export const { v1: API_BASE_URL, v2: API_V2_BASE_URL } = resolveApiBases(rawApiBase)

// ============================================
// 类型定义
// ============================================


// ============================================
// API 客户端类
// ============================================

class APIClient {
  private baseURL: string
  private static supportsV2Stream: boolean | null = null
  private static v2StreamProbePromise: Promise<boolean> | null = null

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
  }

  private getAuthHeaders(): Record<string, string> {
    const token = getStoredAuthToken()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  /**
   * V2 API 专用客户端（使用 V2 base URL）
   */
  static getV2Client(): APIClient {
    return new APIClient(API_V2_BASE_URL)
  }

  private static async probeV2StreamSupport(): Promise<boolean> {
    if (APIClient.supportsV2Stream !== null) {
      return APIClient.supportsV2Stream
    }
    if (APIClient.v2StreamProbePromise) {
      return APIClient.v2StreamProbePromise
    }

    APIClient.v2StreamProbePromise = (async () => {
      try {
        const apiRoot = API_V2_BASE_URL.replace(/\/api\/v2\/?$/, '')
        const response = await fetch(`${apiRoot}/openapi.json`, {
          headers: { Accept: 'application/json' },
        })
        if (!response.ok) {
          APIClient.supportsV2Stream = false
          return false
        }

        const openapi = await response.json()
        const hasStreamEndpoint = Boolean(openapi?.paths?.['/api/v2/query/stream'])
        APIClient.supportsV2Stream = hasStreamEndpoint
        return hasStreamEndpoint
      } catch {
        APIClient.supportsV2Stream = false
        return false
      } finally {
        APIClient.v2StreamProbePromise = null
      }
    })()

    return APIClient.v2StreamProbePromise
  }

  private async fallbackToNonStreamQuery(
    request: ChatQueryRequest,
    callbacks: V2StreamCallbacks,
    abortSignal?: AbortSignal
  ): Promise<AbortController> {
    const controller = new AbortController()
    const signal = abortSignal || controller.signal

    if (signal.aborted) return controller

    try {
      const fallback = await this.query(request, signal)
      if (signal.aborted) return controller

      const answer = (fallback as any)?.answer || ''
      if (answer) callbacks.onContent?.(answer)
      if ((fallback as any)?.table) callbacks.onTable?.((fallback as any).table)
      if ((fallback as any)?.chart) callbacks.onChart?.((fallback as any).chart)
      callbacks.onComplete?.()
    } catch (error) {
      if (!(error instanceof Error && error.name === 'AbortError')) {
        callbacks.onError?.(error instanceof Error ? error.message : '未知错误')
      }
    }

    return controller
  }

  /**
   * 通用请求方法
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`

    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getAuthHeaders(),
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      throw new Error(await responseErrorMessage(response, '请求失败'))
    }

    return response.json()
  }

  /**
   * V1 聊天完成 API（非流式）
   */
  async chatCompletion(request: ChatCompletionRequest): Promise<ChatQueryResponse> {
    return this.request<ChatQueryResponse>('/chat/completion', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  /**
   * V2 查询 API（非流式）
   */
  async query(request: ChatQueryRequest, abortSignal?: AbortSignal): Promise<ChatQueryResponse> {
    // 使用 V2 专用客户端，确保请求发送到正确的 URL
    const v2Client = APIClient.getV2Client()
    // FastAPI 根路由为 '/query/'，直接命中避免浏览器预检重定向。
    return v2Client.request<ChatQueryResponse>('/query/', {
      method: 'POST',
      body: JSON.stringify(request),
      signal: abortSignal,
    })
  }

  /**
   * V1 流式聊天完成（带回调）
   */
  async streamChatCompletionWithCallbacks(
    request: ChatCompletionRequest,
    callbacks: StreamCallbacks,
    abortSignal?: AbortSignal
  ): Promise<AbortController> {
    const controller = new AbortController()
    const signal = abortSignal || controller.signal

    const url = `${this.baseURL}/chat/completion`

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          ...this.getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ...request, stream: true }),
        signal,
      })

      if (!response.ok) {
        throw new Error(await responseErrorMessage(response, `HTTP error! status: ${response.status}`))
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('无法获取响应流')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          callbacks.onComplete?.()
          break
        }

        buffer += decoder.decode(value, { stream: true })

        // 处理 SSE 格式
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)

            if (data === '[DONE]') {
              callbacks.onComplete?.()
              break
            }

            try {
              const parsed = JSON.parse(data)

              if (parsed.content) {
                callbacks.onContent?.(parsed.content)
              }

              if (parsed.table) {
                callbacks.onTable?.(parsed.table)
              }

              if (parsed.chart) {
                callbacks.onChart?.(parsed.chart)
              }

              if (parsed.error) {
                callbacks.onError?.(parsed.error)
              }
            } catch (e) {
              logger.error('APIClient', '解析 SSE 数据失败', e)
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
      } else {
        callbacks.onError?.(error instanceof Error ? error.message : '未知错误')
      }
    }

    return controller
  }

  /**
   * 通用流式查询方法（V1 和 V2 通用）
   */
  async streamQuery(
    endpoint: string,
    request: ChatQueryRequest,
    callbacks: V2StreamCallbacks,
    abortSignal?: AbortSignal
  ): Promise<AbortController> {
    const controller = new AbortController()
    const signal = abortSignal || controller.signal

    const url = `${this.baseURL}${endpoint}`

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          ...this.getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
        signal,
      })

      if (!response.ok) {
        // Backward-compatible fallback: some deployments only expose non-stream V2 '/query/'.
        if (endpoint === '/query/stream' && response.status === 404) {
          APIClient.supportsV2Stream = false
          return this.fallbackToNonStreamQuery(request, callbacks, abortSignal)
        }
        throw new Error(await responseErrorMessage(response, `HTTP error! status: ${response.status}`))
      }

      if (endpoint === '/query/stream') {
        APIClient.supportsV2Stream = true
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('无法获取响应流')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()

        if (done) {
          callbacks.onComplete?.()
          break
        }

        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)

            if (data === '[DONE]') {
              callbacks.onComplete?.()
              break
            }

            try {
              const parsed = JSON.parse(data)

              // V2 特定的处理
              if (parsed.type === 'progress') {
                callbacks.onProgress?.(parsed.progress)
              } else if (parsed.type === 'step') {
                callbacks.onStep?.(parsed.step, parsed.data)
              } else if (parsed.type === 'content') {
                callbacks.onContent?.(parsed.content)
              } else if (parsed.type === 'table') {
                callbacks.onTable?.(parsed.table)
              } else if (parsed.type === 'chart') {
                callbacks.onChart?.(parsed.chart)
              } else if (parsed.type === 'error') {
                callbacks.onError?.(parsed.message)
              } else if (parsed.content) {
                callbacks.onContent?.(parsed.content)
              }
            } catch (e) {
              logger.error('APIClient', '解析 SSE 数据失败', e)
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
      } else {
        callbacks.onError?.(error instanceof Error ? error.message : '未知错误')
      }
    }

    return controller
  }

  /**
   * V2 流式查询（带回调）
   */
  async streamV2Query(
    request: ChatQueryRequest,
    callbacks: V2StreamCallbacks,
    abortSignal?: AbortSignal
  ): Promise<AbortController> {
    // 使用 V2 专用客户端，确保请求发送到正确的 URL
    const v2Client = APIClient.getV2Client()
    const supportsV2Stream = await APIClient.probeV2StreamSupport()
    if (!supportsV2Stream) {
      return v2Client.fallbackToNonStreamQuery(request, callbacks, abortSignal)
    }
    return v2Client.streamQuery('/query/stream', request, callbacks, abortSignal)
  }
}

// ============================================
// 导出单例
// ============================================

export const apiClient = new APIClient()

// 向后兼容的导出
export const api = {
  chat: {
    completion: (request: ChatCompletionRequest) => apiClient.chatCompletion(request),
  },
  v2: {
    query: (request: ChatQueryRequest) => apiClient.query(request),
    stream: (
      request: ChatQueryRequest,
      callbacks: V2StreamCallbacks,
      signal?: AbortSignal
    ) => apiClient.streamV2Query(request, callbacks, signal),
  },
}

export default apiClient
