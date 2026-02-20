/**
 * API Client - Data Agent Backend API
 *
 * 提供与后端 FastAPI 的通信接口
 */

import type { ChatCompletionRequest, ChatQueryRequest, ChatQueryResponse, V2StreamCallbacks } from '@/types/api/chat'
import type { StreamCallbacks } from '@/types/chat'

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

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
  }

  /**
   * V2 API 专用客户端（使用 V2 base URL）
   */
  static getV2Client(): APIClient {
    return new APIClient(API_V2_BASE_URL)
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
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(error.detail || '请求失败')
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
  async query(request: ChatQueryRequest): Promise<ChatQueryResponse> {
    // 使用 V2 专用客户端，确保请求发送到正确的 URL
    const v2Client = APIClient.getV2Client()
    return v2Client.request<ChatQueryResponse>('/query', {
      method: 'POST',
      body: JSON.stringify(request),
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
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ...request, stream: true }),
        signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
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
              console.error('解析 SSE 数据失败:', e)
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
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
        signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
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
              console.error('解析 SSE 数据失败:', e)
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
