/**
 * # [CHAT_STORE] 聊天状态管理Store
 *
 * ## [MODULE]
 * **文件名**: chatStore.ts
 * **职责**: 管理聊天会话、消息历史、流式响应控制、离线缓存和同步，集成Zustand、API客户端和消息缓存服务
 *
 * ## [INPUT]
 * Props (无 - Zustand Store):
 * - 从messageCacheService恢复缓存数据
 * - 从localStorage恢复持久化数据
 * - 接收用户输入和数据源选择
 *
 * ## [OUTPUT]
 * Store:
 * - **sessions: ChatSession[]** - 聊天会话列表
 * - **currentSession: ChatSession | null** - 当前活跃会话
 * - **isLoading: boolean** - 加载状态
 * - **isTyping: boolean** - AI输入状态
 * - **error: string | null** - 错误信息
 * - **isOnline: boolean** - 在线状态
 * - **isSyncing: boolean** - 同步状态
 * - **streamingStatus: StreamingStatus** - 流式响应状态
 * - **currentAbortController: AbortController | null** - 流式取消控制器
 * - **streamingMessageId: string | null** - 当前流式消息ID
 * - **stats: object** - 统计信息
 * Actions:
 * - createSession(title) - 创建新会话
 * - switchSession(sessionId) - 切换会话
 * - deleteSession(sessionId) - 删除会话
 * - deleteSessions(sessionIds) - 批量删除会话
 * - updateSessionTitle(sessionId, title) - 更新会话标题
 * - searchSessions(keyword) - 搜索会话
 * - sendMessage(content, dataSourceIds, useStream) - 发送消息
 * - addMessage(message) - 添加消息
 * - updateMessage(messageId, updates) - 更新消息
 * - deleteMessage(messageId) - 删除消息
 * - clearHistory(sessionId) - 清空历史
 * - stopStreaming() - 停止流式响应
 * - loadFromCache() - 从缓存加载
 * - syncPendingMessages() - 同步待发送消息
 * - clearCache() - 清空缓存
 * - loadFromStorage() - 从本地存储加载
 * - saveToStorage() - 保存到本地存储
 *
 * **上游依赖**:
 * - [zustand](https://github.com/pmndrs/zustand) - 状态管理库
 * - [zustand/middleware](https://github.com/pmndrs/zustand#devtools) - devtools中间件
 * - [../lib/api-client.ts](../lib/api-client.ts) - API客户端（api, apiClient, 类型定义）
 * - [../types/chat.ts](../types/chat.ts) - 聊天类型定义（ProcessingStep, StreamCallbacks）
 * - [../services/messageCacheService.ts](../services/messageCacheService.ts) - 消息缓存服务
 *
 * **下游依赖**:
 * - 无（Store是叶子状态管理模块）
 *
 * **调用方**:
 * - [../components/chat/ChatInterface.tsx](../components/chat/ChatInterface.tsx) - 聊天界面组件
 * - [../components/chat/MessageList.tsx](../components/chat/MessageList.tsx) - 消息列表组件
 * - [../components/chat/MessageInput.tsx](../components/chat/MessageInput.tsx) - 消息输入组件
 *
 * ## [STATE]
 * - **会话管理**: 多会话支持，会话切换，会话搜索
 * - **消息管理**: 消息增删改查，元数据扩展
 * - **流式控制**: 流式响应状态跟踪，取消机制，回调处理
 * - **离线支持**: 离线消息缓存，在线自动同步
 * - **持久化策略**: localStorage存储会话和消息
 *
 * ## [SIDE-EFFECTS]
 * - localStorage操作 (读写data-agent-chat-store)
 * - IndexedDB操作 (messageCacheService缓存)
 * - API调用 (发送消息，查询历史)
 * - 网络状态监听 (online/offline事件)
 * - 定时同步任务 (每30秒同步待发送消息)
 */

import { api, apiClient, ChatCompletionRequest, ChatQueryRequest } from '@/lib/api-client'
import logger from '@/lib/logger'
import { cacheMessage, cacheSession, getCachedSession, getCachedSessions, messageCacheService, syncMessages } from '@/services/messageCacheService'
import { ProcessingStep, StreamCallbacks, V2SessionState, V2StreamCallbacks } from '@/types/chat'
import { create } from 'zustand'
import { devtools, subscribeWithSelector } from 'zustand/middleware'

// 聊天消息类型定义
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
    table?: import('@/lib/api-client').ChatQueryResultTable
    chart?: import('@/lib/api-client').ChatQueryChart
    echarts_option?: Record<string, any>
    processing_steps?: ProcessingStep[]  // AI推理步骤
    progress?: number  // V2 流式进度 (0-100)
  }
}

// 聊天会话类型定义
export interface ChatSession {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  messages: ChatMessage[]
  isActive: boolean
}

// 流式状态类型
type StreamingStatus = 'idle' | 'streaming' | 'paused' | 'analyzing_sql' | 'generating_chart' | 'error' | 'done'

// V2 流式会话管理状态
interface V2SessionManager {
  currentSessionId: string | null
  sessionState: V2SessionState | null
  isPaused: boolean
}

// 聊天状态接口
interface ChatState {
  // 状态
  sessions: ChatSession[]
  currentSession: ChatSession | null
  isLoading: boolean
  isTyping: boolean
  error: string | null
  isOnline: boolean
  isSyncing: boolean

  // 输出格式配置
  outputFormat: 'markdown' | 'plain'

  // 流式响应状态
  streamingStatus: StreamingStatus
  currentAbortController: AbortController | null
  streamingMessageId: string | null  // 当前正在流式更新的消息ID

  // V2 流式会话管理
  v2Session: V2SessionManager

  // 图表合并状态
  selectedCharts: string[]  // 选中的图表消息ID列表
  isMergingCharts: boolean   // 是否正在合并图表

  // 统计信息
  stats: {
    totalMessages: number
    totalSessions: number
    averageResponseTime: number
    pendingMessages: number
  }

  // 操作函数
  // 会话管理
  createSession: (title?: string) => Promise<string>
  switchSession: (sessionId: string) => void
  deleteSession: (sessionId: string) => void
  deleteSessions: (sessionIds: string[]) => void
  updateSessionTitle: (sessionId: string, title: string) => void
  searchSessions: (keyword: string) => ChatSession[]
  startNewConversation: () => Promise<string>

  // 消息操作
  sendMessage: (content: string, dataSourceIds?: string | string[], useStream?: boolean) => Promise<void>
  addMessage: (message: Omit<ChatMessage, 'id'>) => void
  updateMessage: (messageId: string, updates: Partial<ChatMessage>) => void
  deleteMessage: (messageId: string) => void
  clearHistory: (sessionId: string) => void

  // 流式响应控制
  stopStreaming: () => void
  setStreamingStatus: (status: StreamingStatus) => void

  // V2 流式会话管理
  pauseV2Session: (sessionId: string) => Promise<void>
  resumeV2Session: (sessionId: string) => Promise<void>
  cancelV2Session: (sessionId: string) => Promise<void>
  getV2SessionState: (sessionId: string) => Promise<V2SessionState | null>

  // 图表合并操作
  toggleChartSelection: (messageId: string) => void
  clearChartSelection: () => void
  mergeCharts: (messageIds: string[]) => Promise<void>

  // 状态管理
  setLoading: (loading: boolean) => void
  setTyping: (typing: boolean) => void
  setError: (error: string | null) => void
  setOnline: (online: boolean) => void
  setSyncing: (syncing: boolean) => void
  setOutputFormat: (format: 'markdown' | 'plain') => void

  // 缓存和同步操作
  loadFromCache: () => void
  syncPendingMessages: () => Promise<void>
  clearCache: () => void

  // 本地存储操作
  loadFromStorage: () => void
  saveToStorage: () => void

  // 内部方法
  _sendOnlineMessage: (content: string, sessionId: string, dataSourceIds?: string | string[], useStream?: boolean) => Promise<void>
}

// 生成唯一ID
const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

// 创建聊天状态store
export const useChatStore = create<ChatState>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      // 初始状态
      sessions: [],
      currentSession: null,
      isLoading: false,
      isTyping: false,
      error: null,
      isOnline: typeof window !== 'undefined' ? navigator.onLine : true,
      isSyncing: false,
      outputFormat: 'markdown',
      streamingStatus: 'idle',
      currentAbortController: null,
      streamingMessageId: null,
      selectedCharts: [],
      isMergingCharts: false,
      stats: {
        totalMessages: 0,
        totalSessions: 0,
        averageResponseTime: 0,
        pendingMessages: 0,
      },
      // V2 流式会话管理初始状态
      v2Session: {
        currentSessionId: null,
        sessionState: null,
        isPaused: false,
      },

      // 创建新会话
      createSession: async (title = '新会话') => {
        const sessionId = generateId()
        const newSession: ChatSession = {
          id: sessionId,
          title,
          createdAt: new Date(),
          updatedAt: new Date(),
          messages: [],
          isActive: true,
        }

        set((state) => {
          // 将其他会话设为非活跃
          const updatedSessions = state.sessions.map(s => ({ ...s, isActive: false }))
          return {
            sessions: [...updatedSessions, newSession],
            currentSession: newSession,
            stats: {
              ...state.stats,
              totalSessions: (state?.stats?.totalSessions ?? 0) + 1,
            }
          }
        })

        // 同步会话到缓存服务
        messageCacheService.cacheSession({
          id: newSession.id,
          title: newSession.title,
          createdAt: newSession.createdAt,
          updatedAt: newSession.updatedAt,
          messages: [],
          isActive: newSession.isActive,
          isDirty: false,
        })

        // 保存到本地存储
        get().saveToStorage()

        return sessionId
      },

      // 切换会话
      switchSession: (sessionId: string) => {
        set((state) => {
          const session = state.sessions.find(s => s.id === sessionId)
          if (!session) return state

          // 更新会话活跃状态
          const updatedSessions = state.sessions.map(s => ({
            ...s,
            isActive: s.id === sessionId
          }))

          return {
            sessions: updatedSessions,
            currentSession: session,
            error: null
          }
        })
      },

      // 删除会话
      deleteSession: (sessionId: string) => {
        set((state) => {
          const updatedSessions = state.sessions.filter(s => s.id !== sessionId)
          const currentSession = state.currentSession?.id === sessionId
            ? (updatedSessions.length > 0 ? updatedSessions[0] : null)
            : state.currentSession

          return {
            sessions: updatedSessions,
            currentSession,
            stats: {
              ...state.stats,
              totalSessions: Math.max(0, (state?.stats?.totalSessions ?? 0) - 1),
              totalMessages: Math.max(0, (state?.stats?.totalMessages ?? 0) -
                (state?.sessions?.find(s => s.id === sessionId)?.messages.length ?? 0)),
            }
          }
        })

        get().saveToStorage()
      },

      // 批量删除会话
      deleteSessions: (sessionIds: string[]) => {
        if (sessionIds.length === 0) return

        set((state) => {
          const sessionIdsSet = new Set(sessionIds)
          const deletedMessages = state.sessions
            .filter(s => sessionIdsSet.has(s.id))
            .reduce((total, s) => total + s.messages.length, 0)

          const updatedSessions = state.sessions.filter(s => !sessionIdsSet.has(s.id))
          const currentSession = state.currentSession && sessionIdsSet.has(state.currentSession.id)
            ? (updatedSessions.length > 0 ? updatedSessions[0] : null)
            : state.currentSession

          return {
            sessions: updatedSessions,
            currentSession,
            stats: {
              ...state.stats,
              totalSessions: Math.max(0, (state?.stats?.totalSessions ?? 0) - sessionIds.length),
              totalMessages: Math.max(0, (state?.stats?.totalMessages ?? 0) - deletedMessages),
            }
          }
        })

        get().saveToStorage()
      },

      // 更新会话标题
      updateSessionTitle: (sessionId: string, title: string) => {
        set((state) => {
          const updatedSessions = state.sessions.map(s =>
            s.id === sessionId ? { ...s, title, updatedAt: new Date() } : s
          )

          return {
            sessions: updatedSessions,
            currentSession: state.currentSession?.id === sessionId
              ? { ...state.currentSession, title, updatedAt: new Date() }
              : state.currentSession
          }
        })

        get().saveToStorage()
      },

      // 搜索会话 - 按关键字搜索会话标题和消息内容
      searchSessions: (keyword: string): ChatSession[] => {
        const state = get()
        if (!keyword.trim()) {
          return state.sessions
        }

        const lowerKeyword = keyword.toLowerCase().trim()
        return state.sessions.filter(session => {
          // 搜索会话标题
          if (session.title.toLowerCase().includes(lowerKeyword)) {
            return true
          }
          // 搜索会话消息内容
          return session.messages.some(msg =>
            msg.content.toLowerCase().includes(lowerKeyword)
          )
        })
      },

      // 开始新对话 - 创建新会话并清空当前状态
      startNewConversation: async (): Promise<string> => {
        // 直接创建新会话
        const sessionId = await get().createSession('新对话')
        return sessionId
      },

      // 发送消息
      sendMessage: async (content: string, dataSourceIds?: string | string[], useStream: boolean = true) => {
        const state = get()
        logger.info('ChatStore', 'sendMessage called', {
          sessionId: state.currentSession?.id,
          isLoading: state.isLoading,
          isOnline: state.isOnline,
          dataSourceIds,
          contentLength: content.length,
        })

        if (!state.currentSession || state.isLoading) {
          logger.warn('ChatStore', 'Cannot send message: invalid state', {
            hasSession: !!state.currentSession,
            isLoading: state.isLoading,
          })
          return
        }

        // 添加用户消息
        const userMessage: Omit<ChatMessage, 'id'> = {
          role: 'user',
          content,
          timestamp: new Date(),
          status: state.isOnline ? 'sent' : 'sending'
        }

        state.addMessage(userMessage)
        console.log('[ChatStore] 用户消息已添加到会话')

        // 如果离线，将消息加入缓存队列
        if (!state.isOnline) {
          console.log('[ChatStore] 离线模式，将消息加入缓存队列')

          // 确保 session 已经被缓存（如果没有则先缓存）
          const cachedSession = getCachedSession(state.currentSession.id)
          if (!cachedSession) {
            console.log('[ChatStore] Session 未缓存，先缓存 session')
            cacheSession({
              id: state.currentSession.id,
              title: state.currentSession.title,
              createdAt: state.currentSession.createdAt,
              updatedAt: state.currentSession.updatedAt,
              messages: state.currentSession.messages.map(m => ({
                id: m.id,
                sessionId: state.currentSession!.id,
                role: m.role,
                content: m.content,
                timestamp: m.timestamp,
                status: (m.status === 'sending' ? 'pending' : m.status || 'sent') as 'pending' | 'sent' | 'error' | 'synced',
              })),
              isActive: state.currentSession.isActive,
              isDirty: false,
            })
          }

          const pendingMessage = {
            id: generateId(),
            sessionId: state.currentSession.id,
            role: 'user' as const,
            content,
            timestamp: new Date(),
            status: 'pending' as const,
          }

          cacheMessage(state.currentSession.id, pendingMessage)

          // 更新统计
          const cacheStats = messageCacheService.getCacheStats()
          set((currentState) => ({
            stats: {
              ...currentState.stats,
              pendingMessages: cacheStats.pendingMessages,
            }
          }))

          state.setError('网络连接已断开，消息将在恢复后自动发送')
          return
        }

        // 在线时直接发送消息
        console.log('[ChatStore] 在线模式，调用 _sendOnlineMessage, useStream:', useStream)
        await state._sendOnlineMessage(content, state.currentSession.id, dataSourceIds, useStream)
      },

      // 内部方法：在线发送消息
      _sendOnlineMessage: async (content: string, sessionId: string, dataSourceIds?: string | string[], useStream: boolean = true) => {
        const endTimer = logger.startTimer('_sendOnlineMessage')
        const state = get()

        logger.info('ChatStore', '_sendOnlineMessage started', {
          sessionId,
          dataSourceIds,
          useStream,
        })

        console.log('[ChatStore] _sendOnlineMessage 开始, sessionId:', sessionId)

        const normalizedDataSourceIds = dataSourceIds
          ? Array.isArray(dataSourceIds)
            ? dataSourceIds.filter(Boolean)
            : [dataSourceIds]
          : undefined

        // 设置加载状态
        state.setLoading(true)
        state.setTyping(true)

        try {
          // 获取当前会话的历史消息（不包含刚添加的用户消息，因为它已经被添加了）
          const currentSession = state.sessions.find(s => s.id === sessionId)
          // 安全获取消息列表，防止 undefined 错误
          const currentMessages = currentSession?.messages || []
          // 🔧 [修复] 清理历史消息中的错误信息，避免AI重复提及历史错误
          const cleanErrorContent = (content: string): string => {
            // 移除SQL执行失败的错误块
            let cleaned = content
              // 移除 "⚠️ 原始SQL有误，尝试修复后仍然失败" 错误块
              .replace(/\*\*⚠️ 原始SQL有误，尝试修复后仍然失败：\*\*[\s\S]*?(?=\n\n|$)/g, '')
              // 移除 "❌ 查询执行失败" 错误信息
              .replace(/\n\n❌ \*\*查询执行失败\*\*:[\s\S]*?(?=\n\n[^*]|$)/g, '')
              // 移除重试提示
              .replace(/\n\*已尝试自动修复 \d+ 次，但仍然失败\*\n/g, '')
              // 移除多余的空行
              .replace(/\n{3,}/g, '\n\n')
              .trim()
            return cleaned
          }

          const historyMessages = currentMessages
            .filter(m => m.role !== 'system' && m.status !== 'error')  // 排除系统消息和错误消息
            .slice(0, -1)  // 排除刚刚添加的当前消息（避免重复）
            .map(m => ({
              role: m.role as 'user' | 'assistant' | 'system',
              // 清理assistant消息中的错误内容，避免AI重复历史错误
              content: m.role === 'assistant' ? cleanErrorContent(m.content) : m.content
            }))

          console.log('[ChatStore] 历史消息数量:', historyMessages.length, '数据源ID:', normalizedDataSourceIds)

          // 调用API发送消息，包含历史上下文和数据源选择
          // 如果没有选择数据源，尝试从 API 获取第一个活跃数据源
          let finalConnectionId: string | undefined = undefined
          if (normalizedDataSourceIds && normalizedDataSourceIds.length === 1) {
            // 单选时使用选中的数据源
            finalConnectionId = normalizedDataSourceIds[0]
          } else if (!normalizedDataSourceIds || normalizedDataSourceIds.length === 0) {
            // 没有选择数据源时，尝试获取第一个活跃数据源
            try {
              const { useDataSourceStore } = await import('@/store/dataSourceStore')
              const dataSourceStore = useDataSourceStore.getState()
              const tenantId = 'default_tenant' // TODO: 从认证上下文获取
              await dataSourceStore.fetchDataSources(tenantId, { active_only: true })
              const sources = dataSourceStore.dataSources || []
              if (sources.length > 0 && sources[0]?.id) {
                finalConnectionId = sources[0].id
                console.log('[ChatStore] 自动使用第一个活跃数据源:', finalConnectionId)
              }
            } catch (error) {
              console.warn('[ChatStore] 无法获取活跃数据源，将使用后端默认选择:', error)
            }
          }
          // 多选时不设置 connection_id，避免单连接限制

          const queryRequest: ChatQueryRequest = {
            query: content,
            session_id: sessionId,
            history: historyMessages,  // 添加历史消息
            context: normalizedDataSourceIds && normalizedDataSourceIds.length > 0
              ? { data_sources: normalizedDataSourceIds }
              : undefined,  // 添加数据源选择
            // 设置 connection_id 以启用 Agent
            connection_id: finalConnectionId,
          }

          // 🔍 诊断：记录数据源选择信息
          console.log('🔍 [数据源诊断] 前端发送请求时的数据源信息:')
          console.log('  - 用户选择的数据源IDs:', normalizedDataSourceIds)
          console.log('  - 最终使用的 connection_id:', finalConnectionId)
          console.log('  - context.data_sources:', queryRequest.context?.data_sources)
          if (normalizedDataSourceIds && normalizedDataSourceIds.length > 0) {
            try {
              const { useDataSourceStore } = await import('@/store/dataSourceStore')
              const dataSourceStore = useDataSourceStore.getState()
              const tenantId = 'default_tenant'
              await dataSourceStore.fetchDataSources(tenantId, { active_only: true })
              const allSources = dataSourceStore.dataSources || []
              const selectedSources = allSources.filter(ds => normalizedDataSourceIds.includes(ds.id))
              console.log('  - 选中的数据源详情:')
              selectedSources.forEach((ds, idx) => {
                console.log(`    [${idx+1}] ID: ${ds.id}, 名称: ${ds.name}, 类型: ${ds.db_type}, 状态: ${ds.status}`)
              })
            } catch (error) {
              console.warn('  - 无法获取数据源详情:', error)
            }
          }
          // 如果使用流式模式，使用流式API
          if (useStream) {
            // 创建 AbortController
            const abortController = new AbortController()
            set({ currentAbortController: abortController, streamingStatus: 'streaming' })

            // 创建初始的 assistant 消息
            const assistantMessageId = generateId()
            const initialMessage: Omit<ChatMessage, 'id'> = {
              role: 'assistant',
              content: '',
              timestamp: new Date(),
              status: 'sending',
            }

            // 添加初始消息
            set((currentState) => {
              const session = currentState.sessions.find(s => s.id === sessionId)
              if (!session) return currentState

              const newMessage: ChatMessage = {
                ...initialMessage,
                id: assistantMessageId,
              }

              return {
                ...currentState,
                streamingMessageId: assistantMessageId,
                sessions: currentState.sessions.map(s =>
                  s.id === sessionId
                    ? {
                        ...s,
                        messages: [...s.messages, newMessage],
                        updatedAt: new Date(),
                      }
                    : s
                ),
                currentSession: currentState.currentSession?.id === sessionId
                  ? {
                      ...currentState.currentSession,
                      messages: [...currentState.currentSession.messages, newMessage],
                      updatedAt: new Date(),
                    }
                  : currentState.currentSession,
              }
            })

            // 检查是否使用 V2 流式 (默认使用 V2)
            const useV2Stream = queryRequest.use_v2 !== false

            if (useV2Stream) {
              // ============================================================
              // V2 流式模式 (使用 AgentV2 + SSE)
              // ============================================================
              console.log('[ChatStore] 使用 V2 流式模式')

              let accumulatedAnswer = ''
              let processingSteps: ProcessingStep[] = []
              let currentProgress = 0

              // 🔧 流式更新节流控制
              let lastUpdateTime = 0
              const UPDATE_THROTTLE_MS = 100  // 每 100ms 最多更新一次 UI（优化流式输出）
              let pendingUpdate = false
              let rafId: number | null = null

              // V2 流式回调
              const v2Callbacks: V2StreamCallbacks = {
                onStart: (data) => {
                  console.log('[ChatStore V2] 开始:', data)
                  // 保存 V2 会话信息到状态
                  set({
                    v2Session: {
                      currentSessionId: data.session_id,
                      sessionState: null,
                      isPaused: false,
                    }
                  })
                  processingSteps = []
                  currentProgress = 0
                },
                onStep: (data) => {
                  // 🔧 修复：添加详细的状态调试日志
                  console.log('[ChatStore V2] 步骤事件:', {
                    step: data.step,
                    step_id: data.step_id,
                    message: data.message,
                    status: data.status,
                    hasStatusField: "status" in data,
                    statusValue: data.status,
                    statusType: typeof data.status
                  })

                  // 🔧 扩展：转换为 ProcessingStep 格式（支持 V1 兼容字段）
                  const step: ProcessingStep = {
                    step: data.step,
                    title: data.message,
                    description: data.detail || data.message,
                    status: data.status || 'running',  // 🔧 使用后端返回的状态，默认为 running
                    content_type: data.content_type,    // 🔧 新增
                    content_data: data.content_data,    // 🔧 新增
                    duration: data.duration,            // 🔧 新增
                    streaming: data.streaming,          // 🔧 新增
                    content_preview: data.content_preview,  // 🔧 新增
                  }

                  // 🔧 优先使用 step_id 合并，回退到 step 数字
                  const existingIndex = processingSteps.findIndex(s =>
                    data.step_id ? s.step_id === data.step_id : s.step === data.step
                  )
                  if (existingIndex >= 0) {
                    // 🔧 如果步骤已存在，合并更新（保留已有的 timestamp 等字段）
                    processingSteps[existingIndex] = {
                      ...processingSteps[existingIndex],
                      ...step,
                      // 🔧 修复：明确检查 status 是否为有效的非空字符串
                      // 空字符串 "" 不是 undefined，但也不应该作为有效状态
                      status: (typeof data.status === 'string' && data.status.length > 0)
                          ? data.status
                          : processingSteps[existingIndex].status,
                    }
                  } else {
                    processingSteps.push(step)
                  }

                  // 按步骤号排序
                  processingSteps.sort((a, b) => a.step - b.step)

                  // 更新消息 metadata
                  state.updateMessage(assistantMessageId, {
                    metadata: {
                      processing_steps: [...processingSteps],
                      progress: currentProgress,
                    },
                  })
                },
                onProgress: (data) => {
                  console.log('[ChatStore V2] 进度:', data.value)
                  currentProgress = data.value

                  // 更新进度
                  state.updateMessage(assistantMessageId, {
                    metadata: {
                      processing_steps: [...processingSteps],
                      progress: currentProgress,
                    },
                  })
                },
                onData: (data) => {
                  // 🔧 优化：减少日志输出频率
                  accumulatedAnswer += data.chunk
                  currentProgress = data.progress || currentProgress

                  // 🔧 优化：将流式内容显示在当前正在运行的步骤中
                  // 优先找正在运行的步骤，如果没有则用最后一个步骤
                  let targetStep = processingSteps.find(s => s.status === 'running')
                  if (!targetStep && processingSteps.length > 0) {
                    targetStep = processingSteps[processingSteps.length - 1]
                  }
                  
                  if (targetStep) {
                    // 在当前步骤中显示流式内容
                    targetStep.content_preview = accumulatedAnswer
                    targetStep.streaming = true  // 启用打字机光标
                  } else {
                    // 如果还没有任何步骤，创建一个初始的"AI 思考中"步骤
                    const thinkingStep: ProcessingStep = {
                      step: 0,
                      title: 'AI 思考中',
                      description: '正在分析问题...',
                      status: 'running' as const,
                      streaming: true,
                      content_preview: accumulatedAnswer,
                    }
                    processingSteps.push(thinkingStep)
                  }

                  // 🔧 节流更新：使用 requestAnimationFrame 批量更新
                  const now = Date.now()
                  if (!pendingUpdate && (now - lastUpdateTime >= UPDATE_THROTTLE_MS)) {
                    pendingUpdate = true
                    rafId = requestAnimationFrame(() => {
                      state.updateMessage(assistantMessageId, {
                        content: accumulatedAnswer,
                        metadata: {
                          processing_steps: [...processingSteps],
                        },
                      })
                      lastUpdateTime = Date.now()
                      pendingUpdate = false
                    })
                  }
                },
                onDone: (data) => {
                  console.log('[ChatStore V2] 完成:', data)
                  console.log('[ChatStore V2] chart_config:', data.chart_config)
                  console.log('[ChatStore V2] 当前 processingSteps 数量:', processingSteps.length)

                  // 🔧 第六次修复：记录初始状态
                  console.log('[ChatStore V2] 🔍 onDone 开始时 processingSteps:', processingSteps.map(s => ({
                    step: s.step,
                    title: s.title,
                    status: s.status,
                    statusType: typeof s.status
                  })))

                  // 🔧 兜底逻辑：如果没有步骤1，先添加一个running状态的步骤1
                  if (processingSteps.length === 0 || !processingSteps.some(s => s.step === 1)) {
                    console.warn('[ChatStore V2] ⚠️ processingSteps中没有步骤1，添加步骤1')
                    processingSteps.push({
                      step: 1,
                      title: '理解问题',
                      description: '正在分析问题...',
                      status: 'running' as const,
                    })
                  }

                  // 🔧 第六次修复：合并所有 map 操作为一次，确保不可变性
                  // 1. 强制完成所有 running 步骤
                  // 2. 清理 streaming 和 content_preview
                  // 3. 确保步骤 0 的 content_preview 被清除（防止文案重复）
                  processingSteps = processingSteps.map((step) => {
                    const baseUpdate = {
                      ...step,
                      streaming: false,
                      content_preview: undefined,
                    }
                    // 如果步骤是 running 状态，强制改为 completed
                    if (step.status === 'running') {
                      console.log(`[ChatStore V2] 🔧 强制步骤 ${step.step} 从 running 更新为 completed`)
                      return {
                        ...baseUpdate,
                        status: 'completed',
                      }
                    }
                    return baseUpdate
                  })

                  console.log('[ChatStore V2] ✅ 已更新所有步骤（completed + 清理字段）')
                  console.log('[ChatStore V2] 🔍 更新后 processingSteps:', processingSteps.map(s => ({
                    step: s.step,
                    status: s.status
                  })))

                  // 🔧 第六次修复：如果没有任何步骤，添加默认步骤
                  if (processingSteps.length === 0) {
                    console.warn('[ChatStore V2] ⚠️ processingSteps 为空，添加默认步骤')
                    const defaultStep: ProcessingStep = {
                      step: 1,
                      title: '查询完成',
                      description: '查询已处理完成',
                      status: 'completed',
                      duration: 100
                    }
                    processingSteps.push(defaultStep)
                  }

                  // 🔧 第六次修复：检查 answer 是否为空
                  if (!data.answer || !data.answer.trim()) {
                    console.warn('[ChatStore V2] ⚠️ 收到的 answer 为空，data:', data)

                    // 生成友好的错误消息
                    const emptyAnswerMessage = data.success
                      ? "查询已处理完成，但 AI 未生成文字回复。请查看上方的 Reasoning Process 了解详情。"
                      : "查询处理失败，请重试。"

                    // 更新消息内容
                    state.updateMessage(assistantMessageId, {
                      status: 'sent',
                      content: emptyAnswerMessage,
                      metadata: {
                        processing_steps: [...processingSteps],
                        progress: 100,
                      }
                    })

                    state.setError(emptyAnswerMessage)
                    return
                  }

                  // 🔧 取消挂起的节流更新，执行最终同步更新
                  if (rafId !== null) {
                    cancelAnimationFrame(rafId)
                    rafId = null
                  }
                  pendingUpdate = false

                  // 🔧 解析图表配置
                  let chartConfig = null
                  console.log('[ChatStore V2] 🔍 done 事件 data.chart_config:', data.chart_config)
                  console.log('[ChatStore V2] 🔍 chart_config 类型:', typeof data.chart_config)
                  console.log('[ChatStore V2] 🔍 chart_config 长度:', data.chart_config?.length || 'N/A')
                  if (data.chart_config) {
                    try {
                      chartConfig = typeof data.chart_config === 'string'
                        ? JSON.parse(data.chart_config)
                        : data.chart_config
                      console.log('[ChatStore V2] ✅ 成功解析图表配置:', chartConfig)
                      console.log('[ChatStore V2] 🔍 chartConfig.series:', chartConfig?.series)
                      console.log('[ChatStore V2] 🔍 chartConfig.xAxis:', chartConfig?.xAxis)
                    } catch (e) {
                      console.warn('[ChatStore V2] ❌ 图表配置解析失败:', e)
                    }
                  } else {
                    console.warn('[ChatStore V2] ⚠️ done 事件中没有 chart_config 字段')
                  }

                  // 🔧 步骤优化：移除前端重复添加的3个步骤（数据展示、图表、AI回答）
                  // 后端已经发送了相应的步骤，前端不需要再添加
                  // 1. 数据展示步骤：后端的 on_tool_end 已包含表格数据
                  // 2. 图表步骤：后端的 done 事件已包含图表配置
                  // 3. AI回答步骤：使用 data.answer 而非额外添加步骤
                  console.log('[ChatStore V2] 🔍 步骤优化：跳过前端重复步骤添加')

                  // 🔧 检查是否有表格数据（仅用于日志记录）
                  const hasTableData = processingSteps.some(step =>
                    step.content_type === 'table' && step.content_data?.table
                  )
                  console.log('[ChatStore V2] 🔍 是否有表格数据:', hasTableData)
                  console.log('[ChatStore V2] 🔍 是否有图表配置:', !!chartConfig)

                  // 🔧 修复4：如果有图表配置，添加图表步骤到 processing_steps
                  // 这样 ProcessingSteps 组件就能正确显示图表
                  if (chartConfig && !processingSteps.some(s => s.content_type === 'chart')) {
                    console.log('[ChatStore V2] 📊 添加图表步骤到 processing_steps')
                    const maxStep = Math.max(0, ...processingSteps.map(s => s.step || 0))
                    processingSteps.push({
                      step: maxStep + 1,
                      step_id: `chart-${Date.now()}`,
                      title: '生成数据可视化',
                      description: '创建图表展示分析结果',
                      status: 'completed' as const,
                      duration: 200,
                      content_type: 'chart' as const,
                      content_data: {
                        chart: {
                          echarts_option: chartConfig,
                          chart_type: chartConfig.chart_type || 'line',
                          title: chartConfig.title?.text || '数据图表',
                        }
                      }
                    })
                    console.log('[ChatStore V2] ✅ 图表步骤已添加')
                  }

                  // 🔧 步骤优化：在最终更新前，再次检查是否有 running 步骤
                  const hasRunningBeforeFinal = processingSteps.some(s => s.status === 'running')
                  if (hasRunningBeforeFinal) {
                    console.warn('[ChatStore V2] ⚠️ 最终更新前仍有 running 步骤，强制完成所有步骤')
                    processingSteps = processingSteps.map(s => ({
                      ...s,
                      status: 'completed',
                    }))
                  }

                  console.log('[ChatStore V2] 🔍 最终 processingSteps 状态:', processingSteps.map(s => ({
                    step: s.step,
                    status: s.status
                  })))

                  // 🔧 第六次修复：只调用一次 updateMessage，使用最新的 processingSteps
                  state.updateMessage(assistantMessageId, {
                    status: 'sent',
                    content: data.answer,
                    metadata: {
                      processing_steps: [...processingSteps],
                      progress: 100,
                      processing_time_ms: data.processing_time_ms,
                      // 🔧 同时保存到 metadata.echarts_option 以便其他组件使用
                      ...(chartConfig && { echarts_option: chartConfig }),
                    },
                    // 🔧 添加图表配置（向后兼容）
                    ...(chartConfig && {
                      chart: {
                        chart_type: chartConfig.chart_type || 'line',
                        title: chartConfig.title || '数据图表',
                        chart_config: JSON.stringify(chartConfig),
                      }
                    })
                  })
                },
                onError: (data) => {
                  console.error('[ChatStore V2] 错误:', data)

                  // 🔧 兜底逻辑：确保步骤1被标记为完成
                  processingSteps = processingSteps.map(s => {
                    if (s.step === 1 && s.status === 'running') {
                      return { ...s, status: 'completed', streaming: false, content_preview: undefined }
                    }
                    // 清理所有步骤的 streaming 和 content_preview
                    return { ...s, streaming: false, content_preview: undefined, status: s.status === 'running' ? 'completed' : s.status }
                  })

                  // 如果没有任何步骤，添加默认步骤
                  if (processingSteps.length === 0) {
                    console.warn('[ChatStore V2] ⚠️ processingSteps 为空，添加默认步骤')
                    processingSteps = [{
                      step: 1,
                      title: '查询处理',
                      description: '查询处理完成',
                      status: 'completed',
                      duration: 100
                    }]
                  }

                  console.log('[ChatStore V2] ✅ onError：已更新所有步骤')

                  set({
                    streamingStatus: 'error',
                    isLoading: false,
                    isTyping: false,
                  })
                  state.updateMessage(assistantMessageId, {
                    status: 'error',
                    content: data.error || '查询失败',
                    metadata: {
                      processing_steps: [...processingSteps],
                      progress: 100,
                    },
                  })
                  state.setError(data.detail || data.error || 'V2 流式响应错误')
                },
              }

              try {
                // 调用 V2 流式 API
                const returnedController = await apiClient.streamV2Query(
                  queryRequest,
                  v2Callbacks,
                  abortController.signal
                )

                if (returnedController !== abortController) {
                  set({ currentAbortController: returnedController })
                }
              } catch (error) {
                if (error instanceof Error && error.name === 'AbortError') {
                  console.log('[ChatStore V2] 流式响应已取消')
                  set({ streamingStatus: 'idle' })
                  state.updateMessage(assistantMessageId, {
                    status: 'error',
                    content: accumulatedAnswer || '响应已中断',
                  })
                  return
                }
                throw error
              } finally {
                set({
                  currentAbortController: null,
                  streamingMessageId: null,
                  streamingStatus: 'idle',
                  isLoading: false,
                  isTyping: false,
                })
              }

            } else {
              // ============================================================
              // V1 流式模式 (原有逻辑)
              // ============================================================
              console.log('[ChatStore] 使用 V1 流式模式')

              // 构建 ChatCompletionRequest
              const chatRequest: ChatCompletionRequest = {
                messages: historyMessages.concat([{
                  role: 'user',
                  content: content
                }]),
                stream: true,
                enable_thinking: false,
                data_source_ids: normalizedDataSourceIds,
              }

              // 流式内容累积
              let accumulatedContent = ''
              let accumulatedThinking = ''
              let toolInput = ''
              let toolOutput: any = null
              let echartsOption: any = null
              let processingSteps: ProcessingStep[] = []

            // 🔧 新增：标记是否已经收到了正式的处理步骤
            // 在收到正式步骤之前，所有 content 都视为"规划/思考"阶段
            let hasReceivedFormalStep = false
            let planningContent = ''  // 规划阶段的内容

            // 🔧 新增：创建初始的"理解问题"步骤（步骤 0）
            const initPlanningStep: ProcessingStep = {
              step: 0,
              title: '理解问题',
              description: '正在分析您的问题...',
              status: 'running',
            }
            processingSteps.push(initPlanningStep)
            state.updateMessage(assistantMessageId, {
              metadata: {
                processing_steps: [...processingSteps],
              },
            })

            // 定义回调函数
            const callbacks: StreamCallbacks = {
              onContent: (delta: string) => {
                // 🔧 修改：所有内容都存入步骤 0 的 content_preview（包括规划阶段和回答阶段）
                // 这样可以让临时内容在步骤0中显示，而不是在消息气泡中
                planningContent += delta

                // 确保 processingSteps 中有步骤 0
                let planningStep = processingSteps.find(s => s.step === 0)
                if (!planningStep) {
                  planningStep = {
                    step: 0,
                    title: '理解问题',
                    description: '正在分析您的问题...',
                    status: 'running' as const,
                  }
                  processingSteps.push(planningStep)
                }

                // 更新步骤 0 的 content_preview
                planningStep.content_preview = planningContent
                planningStep.description = planningContent.length > 100
                  ? planningContent.slice(0, 100) + '...'
                  : planningContent

                state.updateMessage(assistantMessageId, {
                  metadata: {
                    processing_steps: [...processingSteps],
                  },
                })

                // 同时累积到 accumulatedContent（用于其他用途，如错误恢复）
                accumulatedContent += delta

                // 🔧 修复：如果当前状态是 analyzing_sql 或 generating_chart，收到 content 事件时切换回 streaming
                const currentStatus = get().streamingStatus
                if (currentStatus === 'analyzing_sql' || currentStatus === 'generating_chart') {
                  set({ streamingStatus: 'streaming' })
                }
              },
              onThinking: (delta: string) => {
                accumulatedThinking += delta
                state.updateMessage(assistantMessageId, {
                  metadata: {
                    reasoning: accumulatedThinking,
                  },
                })
              },
              onToolInput: (toolName: string, args: string) => {
                toolInput += args
                set({ streamingStatus: 'analyzing_sql' })
                // 将 SQL 代码追加到消息内容中，以便显示
                const sqlBlock = `\n\`\`\`sql\n${toolInput}\n\`\`\`\n`
                // 只在第一次收到 tool_input 时添加，避免重复
                if (!accumulatedContent.includes('```sql')) {
                  accumulatedContent += sqlBlock
                } else {
                  // 如果已经有 SQL 块，更新它
                  const sqlMatch = accumulatedContent.match(/```sql\n([\s\S]*?)\n```/)
                  if (sqlMatch) {
                    accumulatedContent = accumulatedContent.replace(
                      /```sql\n[\s\S]*?\n```/,
                      sqlBlock.trim()
                    )
                  } else {
                    accumulatedContent += args
                  }
                }
                state.updateMessage(assistantMessageId, {
                  content: accumulatedContent,
                })
                console.log('[ChatStore] Tool input:', toolName, args.substring(0, 100))
              },
              onToolResult: (data: any) => {
                toolOutput = data
                set({ streamingStatus: 'generating_chart' })
                // 尝试提取 ECharts 配置
                if (typeof toolOutput === 'object' && toolOutput.echarts_option) {
                  echartsOption = toolOutput.echarts_option
                }
                console.log('[ChatStore] Tool result received:', data)
              },
              onChartConfig: (chartOption: any) => {
                // 图表已通过 ProcessingSteps 的步骤7显示，无需单独处理
                console.log('[ChatStore] 📊 收到图表配置（已由步骤7处理）:', chartOption)
                echartsOption = chartOption
                set({ streamingStatus: 'generating_chart' })
                // 图表配置已通过 onProcessingStep 的步骤7 添加到 processing_steps 中
                // 无需再单独添加到 metadata，避免重复显示
              },
              onProcessingStep: (step: ProcessingStep) => {
                // 处理AI推理步骤事件
                console.log('[ChatStore] 🔄 收到处理步骤:', step)

                // 🔧 新增：收到正式步骤时，标记规划阶段结束
                if (step.step >= 1 && !hasReceivedFormalStep) {
                  hasReceivedFormalStep = true
                  // 完成步骤 0（规划步骤）
                  const planningStep = processingSteps.find(s => s.step === 0)
                  if (planningStep) {
                    planningStep.status = 'completed'
                    // 🔧 修改：保留 content_preview，让步骤0继续显示后续的临时内容
                    // 同时也保存为 text 类型（用于最终展示）
                    if (planningContent.trim()) {
                      planningStep.content_type = 'text'
                      planningStep.content_data = {
                        text: planningContent
                      }
                      // 注意：不清除 content_preview，让步骤0继续显示临时内容
                    }
                  }
                }

                // 🔧 重构：支持多图表 - 用 step号 + chart_index 作为唯一标识
                // 获取 chart_index（如果存在）
                const chartIndex = step.content_data?.chart?.chart_index

                // 查找是否已存在相同步骤的步骤
                let existingIndex = processingSteps.findIndex(s => {
                  // 如果有 chart_index，需要同时匹配 step号 和 chart_index
                  if (chartIndex !== undefined) {
                    const existingChartIndex = s.content_data?.chart?.chart_index
                    return s.step === step.step && existingChartIndex === chartIndex
                  }
                  // 否则只匹配 step号（旧逻辑，用于非图表步骤）
                  return s.step === step.step && !s.content_data?.chart?.chart_index
                })

                // 🔧 修复：如果有 chart_index 但没找到精确匹配，尝试替换同步骤号的 running 状态步骤
                // 这解决了 step_update 创建的步骤没有 chart_index，导致后续 completed 事件无法匹配的问题
                if (existingIndex < 0 && chartIndex !== undefined) {
                  existingIndex = processingSteps.findIndex(s =>
                    s.step === step.step &&
                    s.status === 'running' &&
                    !s.content_data?.chart?.chart_index
                  )
                  if (existingIndex >= 0) {
                    console.log('[ChatStore] 🔧 找到同步骤号的 running 步骤，将替换:', processingSteps[existingIndex])
                  }
                }

                if (existingIndex >= 0) {
                  // 更新已有步骤（例如从running变为completed）
                  processingSteps[existingIndex] = step
                } else {
                  // 添加新步骤
                  processingSteps.push(step)
                }

                // 按步骤号排序（相同step号的按chart_index排序）
                processingSteps.sort((a, b) => {
                  if (a.step !== b.step) return a.step - b.step
                  // 相同step号，按chart_index排序
                  const aIdx = a.content_data?.chart?.chart_index || 0
                  const bIdx = b.content_data?.chart?.chart_index || 0
                  return aIdx - bIdx
                })

                // 更新消息的metadata
                state.updateMessage(assistantMessageId, {
                  metadata: {
                    processing_steps: [...processingSteps],
                  },
                })
              },
              // 🔧 处理步骤更新事件（用于更新正在进行的步骤，支持流式输出状态）
              onStepUpdate: (stepNum: number, description: string, contentPreview?: string, streaming?: boolean) => {
                console.log('[ChatStore] 🔄 收到步骤更新:', stepNum, description, contentPreview?.substring(0, 50), streaming ? '(流式)' : '')

                // 查找是否已存在相同步骤号的步骤
                const existingIndex = processingSteps.findIndex(s => s.step === stepNum)
                if (existingIndex >= 0) {
                  // 更新已有步骤的描述、内容预览和流式状态
                  processingSteps[existingIndex] = {
                    ...processingSteps[existingIndex],
                    description: description,
                    content_preview: contentPreview,
                    streaming: streaming,  // 🔧 新增：流式输出状态
                  }
                } else {
                  // 如果步骤不存在，创建一个新步骤
                  processingSteps.push({
                    step: stepNum,
                    title: `步骤 ${stepNum}`,
                    description: description,
                    status: 'running',
                    content_preview: contentPreview,
                    streaming: streaming,  // 🔧 新增：流式输出状态
                  })
                }

                // 按步骤号排序
                processingSteps.sort((a, b) => a.step - b.step)

                // 更新消息的metadata
                state.updateMessage(assistantMessageId, {
                  metadata: {
                    processing_steps: [...processingSteps],
                  },
                })
              },
              onError: (error: string) => {
                set({
                  streamingStatus: 'error',
                  isLoading: false,  // 🔧 确保重置加载状态
                  isTyping: false,   // 🔧 确保重置输入状态
                })
                state.updateMessage(assistantMessageId, {
                  status: 'error',
                  content: accumulatedContent || error || '生成失败',
                })
                state.setError(error || '流式响应错误')
              },
              onDone: () => {
                set({ streamingStatus: 'done' })

                // 🔧 修复：将所有 running 状态的步骤更新为 completed
                // 这确保了即使后端没有发送完成事件，前端也不会一直显示"正在生成..."
                processingSteps.forEach(step => {
                  if (step.status === 'running') {
                    step.status = 'completed'
                    // 清除流式标识
                    step.streaming = false
                    // 对于规划步骤（步骤0），保存累积的规划内容
                    if (step.step === 0 && planningContent.trim()) {
                      step.content_type = 'text'
                      step.content_data = {
                        text: planningContent
                      }
                      // 🔧 修改：保留 content_preview，让步骤0继续显示临时内容
                      // 注意：不清除 content_preview
                    }
                  }
                })

                // 流结束，更新最终消息状态（合并所有累积的内容）
                // 🔧 修复：如果有 processing_steps，说明内容已在 ProcessingSteps 中展示，不需要默认错误消息
                const hasProcessingSteps = processingSteps.length > 0
                // 🔧 重构：消息 content 保持为空，所有内容都在 ProcessingSteps 中展示
                const finalContent = hasProcessingSteps ? '' : (accumulatedContent || '抱歉，我现在无法回答这个问题。')

                // 如果 toolInput 有内容但还没添加到 content 中，添加它
                if (toolInput && !finalContent.includes('```sql')) {
                  accumulatedContent += `\n\`\`\`sql\n${toolInput}\n\`\`\`\n`
                }

                state.updateMessage(assistantMessageId, {
                  status: 'sent',
                  content: finalContent,  // 🔧 修改：有 processing_steps 时为空
                  metadata: {
                    reasoning: accumulatedThinking || undefined,
                    sources: [],
                    confidence: 0.9,
                    echarts_option: echartsOption,
                    processing_steps: processingSteps.length > 0 ? [...processingSteps] : undefined,
                  },
                })

                // 流结束后保存到存储和缓存（任务2.4）
                setTimeout(() => {
                  const finalState = get()
                  const finalSession = finalState.sessions.find(s => s.id === sessionId)
                  if (finalSession) {
                    const finalMessage = finalSession.messages.find(m => m.id === assistantMessageId)
                    if (finalMessage && finalMessage.status === 'sent') {
                      // 保存到缓存
                      cacheMessage(sessionId, {
                        id: finalMessage.id,
                        sessionId,
                        role: finalMessage.role,
                        content: finalMessage.content,
                        timestamp: finalMessage.timestamp,
                        status: 'sent',
                      })
                      // 保存到本地存储
                      finalState.saveToStorage()
                    }
                  }
                }, 100) // 延迟一点确保状态已更新
              },
            }

            try {
              // 使用新的回调方式调用流式API
              const returnedController = await apiClient.streamChatCompletionWithCallbacks(
                chatRequest,
                callbacks,
                abortController.signal
              )
              // 更新 AbortController（如果返回了新的）
              if (returnedController !== abortController) {
                set({ currentAbortController: returnedController })
              }
            } catch (error) {
              if (error instanceof Error && error.name === 'AbortError') {
                console.log('[ChatStore] 流式响应已取消')
                set({ streamingStatus: 'idle' })
                state.updateMessage(assistantMessageId, {
                  status: 'error',
                  content: accumulatedContent || '响应已中断',
                })
                return
              }
              throw error
            } finally {
              set({ 
                currentAbortController: null, 
                streamingMessageId: null, 
                streamingStatus: 'idle',
                isLoading: false,
                isTyping: false,
              })
            }
          }  // 关闭 V1 流式 else 分支
        }  // 关闭外层 if (useStream) 分支
        else {  // 非流式模式（原有逻辑）
            console.log('[ChatStore] 准备调用 API, request:', queryRequest)
            const response = await api.chat.sendQuery(queryRequest)
            console.log('[ChatStore] API 响应:', response)

            if (response.status === 'error' || !response.data) {
              console.error('[ChatStore] API 返回错误:', response.error)
              throw new Error(response.error || 'API Error: Unknown error')
            }

            const result = response.data
            console.log('[ChatStore] API 返回成功, result:', result)

            // 添加AI响应消息
            const assistantMessage: Omit<ChatMessage, 'id'> = {
              role: 'assistant',
              content: result.answer || '抱歉，我现在无法回答这个问题。',
              timestamp: new Date(),
              status: 'sent',
              metadata: {
                sources: result.sources,
                reasoning: result.reasoning,
                confidence: result.confidence,
                table: result.table,
                chart: result.chart,
                echarts_option: result.echarts_option,
              }
            }

            state.addMessage(assistantMessage)
            console.log('[ChatStore] AI 响应消息已添加')
          }

        } catch (error) {
          // 记录错误日志
          logger.error('ChatStore', 'sendMessage failed', error, {
            sessionId,
            dataSourceIds,
            useStream,
          })

          console.error('[ChatStore] 发送消息失败:', error)

          // 确保 session 已经被缓存（如果没有则先缓存）
          if (state.currentSession) {
            const cachedSession = getCachedSession(sessionId)
            if (!cachedSession) {
              console.log('[ChatStore] Session 未缓存，先缓存 session')
              cacheSession({
                id: state.currentSession.id,
                title: state.currentSession.title,
                createdAt: state.currentSession.createdAt,
                updatedAt: state.currentSession.updatedAt,
                messages: state.currentSession.messages.map(m => ({
                  id: m.id,
                  sessionId: state.currentSession!.id,
                  role: m.role,
                  content: m.content,
                  timestamp: m.timestamp,
                  status: (m.status === 'sending' ? 'pending' : m.status || 'sent') as 'pending' | 'sent' | 'error' | 'synced',
                })),
                isActive: state.currentSession.isActive,
                isDirty: false,
              })
            }
          }

          // 如果发送失败，将消息加入缓存队列
          const pendingMessage = {
            id: generateId(),
            sessionId,
            role: 'user' as const,
            content,
            timestamp: new Date(),
            status: 'pending' as const,
          }

          console.log('[ChatStore] 将消息加入缓存队列, sessionId:', sessionId)
          cacheMessage(sessionId, pendingMessage)

          // 更新消息状态为错误，但保留在缓存中
          state.updateMessage(
            state.currentSession?.messages[state.currentSession.messages.length - 1]?.id || '',
            { status: 'error' }
          )

          // 添加错误消息
          const errorMessage: Omit<ChatMessage, 'id'> = {
            role: 'system',
            content: `发送消息失败: ${error instanceof Error ? error.message : '未知错误'}。请检查网络连接或后端服务状态。`,
            timestamp: new Date(),
            status: 'error'
          }

          state.addMessage(errorMessage)
          state.setError(`发送消息失败: ${error instanceof Error ? error.message : '未知错误'}`)
        } finally {
          // 结束性能计时
          endTimer()

          state.setLoading(false)
          state.setTyping(false)
          console.log('[ChatStore] _sendOnlineMessage 完成')

          logger.info('ChatStore', '_sendOnlineMessage completed', {
            sessionId,
          })
        }
      },

      // 添加消息
      addMessage: (message: Omit<ChatMessage, 'id'>) => {
        const messageId = generateId()
        const fullMessage: ChatMessage = { ...message, id: messageId }

        set((state) => {
          if (!state.currentSession) return state

          // 更新当前会话的消息列表
          const updatedSessions = state.sessions.map(s =>
            s.id === state.currentSession?.id
              ? {
                  ...s,
                  messages: [...s.messages, fullMessage],
                  updatedAt: new Date()
                }
              : s
          )

          const updatedCurrentSession = {
            ...state.currentSession,
            messages: [...state.currentSession.messages, fullMessage],
            updatedAt: new Date()
          }

          // 自动生成会话标题（使用第一条用户消息）
          let sessionTitle = state.currentSession.title
          if (state.currentSession.messages.length === 0 && message.role === 'user') {
            sessionTitle = message.content.substring(0, 30) + (message.content.length > 30 ? '...' : '')
          }

          return {
            sessions: updatedSessions,
            currentSession: {
              ...updatedCurrentSession,
              title: sessionTitle
            },
            stats: {
              ...state.stats,
              totalMessages: (state?.stats?.totalMessages ?? 0) + 1,
            }
          }
        })

        get().saveToStorage()
      },

      // 更新消息（支持深度合并 metadata）
      updateMessage: (messageId: string, updates: Partial<ChatMessage>) => {
        // 🔧 第三次修复：添加调试日志
        console.log('[ChatStore] 🔧 updateMessage 调用:', {
          messageId,
          hasUpdates: !!updates,
          hasContent: !!updates.content,
          hasMetadata: !!updates.metadata,
          metadataKeys: updates.metadata ? Object.keys(updates.metadata) : [],
          processingSteps: updates.metadata?.processing_steps?.map((s: any) => ({ step: s.step, status: s.status })),
          progress: updates.metadata?.progress
        })

        set((state) => {
          if (!state.currentSession) return state

          // 辅助函数：深度合并消息更新
          const mergeMessage = (m: ChatMessage): ChatMessage => {
            if (m.id !== messageId) return m

            // 🔧 第五次修复：强制完成所有 running 状态的步骤
            let processingSteps = updates.metadata?.processing_steps || m.metadata?.processing_steps
            if (processingSteps && processingSteps.length > 0) {
              const hasRunning = processingSteps.some((s: any) => s.status === 'running')
              if (hasRunning) {
                console.log('[ChatStore] 🔧 第五次修复：强制完成所有 running 步骤')
                processingSteps = processingSteps.map((step: any) => ({
                  ...step,
                  status: step.status === 'running' ? 'completed' : step.status,
                  streaming: false
                }))
                // 🔧 更新 updates.metadata.processing_steps
                if (updates.metadata) {
                  updates.metadata = {
                    ...updates.metadata,
                    processing_steps: processingSteps
                  }
                } else {
                  updates.metadata = { processing_steps: processingSteps }
                }
              }
            }

            // 如果更新包含 metadata，需要深度合并
            if (updates.metadata && m.metadata) {
              const merged = {
                ...m,
                ...updates,
                metadata: {
                  ...m.metadata,
                  ...updates.metadata,
                }
              }
              // 🔧 第三次修复：记录合并后的 metadata
              if (merged.metadata?.processing_steps) {
                console.log('[ChatStore] 🔧 mergeMessage 合并后 metadata:', {
                  processingSteps: merged.metadata.processing_steps.map((s: any) => ({
                    step: s.step,
                    status: s.status,
                    title: s.title?.substring(0, 20)
                  })),
                  progress: merged.metadata.progress
                })
              }
              return merged
            }

            // 否则直接合并
            return { ...m, ...updates }
          }

          const updatedSessions = state.sessions.map(s =>
            s.id === state.currentSession?.id
              ? {
                  ...s,
                  messages: s.messages.map(mergeMessage),
                  updatedAt: new Date()
                }
              : s
          )

          const updatedCurrentSession = {
            ...state.currentSession,
            messages: state.currentSession.messages.map(mergeMessage),
            updatedAt: new Date()
          }

          return {
            sessions: updatedSessions,
            currentSession: updatedCurrentSession
          }
        })

        // 注意：流式更新时不立即保存，只在流结束时保存（在 onDone 回调中）
        // get().saveToStorage()
      },

      // 删除消息
      deleteMessage: (messageId: string) => {
        set((state) => {
          if (!state.currentSession) return state

          const updatedSessions = state.sessions.map(s =>
            s.id === state.currentSession?.id
              ? {
                  ...s,
                  messages: (s.messages || []).filter(m => m.id !== messageId),
                  updatedAt: new Date()
                }
              : s
          )

          const updatedCurrentSession = {
            ...state.currentSession,
            messages: (state.currentSession.messages || []).filter(m => m.id !== messageId),
            updatedAt: new Date()
          }

          return {
            sessions: updatedSessions,
            currentSession: updatedCurrentSession,
            stats: {
              ...state.stats,
              totalMessages: Math.max(0, (state?.stats?.totalMessages ?? 0) - 1),
            }
          }
        })

        get().saveToStorage()
      },

      // 清空历史
      clearHistory: (sessionId: string) => {
        set((state) => {
          const updatedSessions = state.sessions.map(s =>
            s.id === sessionId
              ? {
                  ...s,
                  messages: [],
                  updatedAt: new Date()
                }
              : s
          )

          const sessionMessageCount = state.sessions.find(s => s.id === sessionId)?.messages.length || 0

          return {
            sessions: updatedSessions,
            currentSession: state.currentSession?.id === sessionId
              ? { ...state.currentSession, messages: [] }
              : state.currentSession,
            stats: {
              ...state.stats,
              totalMessages: Math.max(0, (state?.stats?.totalMessages ?? 0) - sessionMessageCount),
            }
          }
        })

        get().saveToStorage()
      },

      // 设置加载状态
      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      },

      // 设置输入状态
      setTyping: (typing: boolean) => {
        set({ isTyping: typing })
      },

      // 设置错误状态
      setError: (error: string | null) => {
        set({ error })
      },

      // 设置输出格式
      setOutputFormat: (format: 'markdown' | 'plain') => {
        set({ outputFormat: format })
        // 保存到本地存储
        if (typeof window !== 'undefined') {
          localStorage.setItem('data-agent-output-format', format)
        }
      },

      // 停止流式响应
      stopStreaming: () => {
        const state = get()
        if (state.currentAbortController) {
          state.currentAbortController.abort()
          set({
            currentAbortController: null,
            streamingStatus: 'idle',
            streamingMessageId: null,
          })
        }
      },

      // 设置流式状态
      setStreamingStatus: (status: StreamingStatus) => {
        set({ streamingStatus: status })
      },

      // ========================================
      // V2 流式会话管理
      // ========================================

      // 暂停 V2 流式会话
      pauseV2Session: async (sessionId: string) => {
        console.log('[ChatStore] 暂停 V2 会话:', sessionId)
        try {
          const result = await apiClient.pauseV2Session(sessionId)
          console.log('[ChatStore] 暂停结果:', result)
          // 更新本地状态
          set({
            v2Session: {
              ...get().v2Session,
              isPaused: true,
            },
            streamingStatus: 'paused',
          })
        } catch (error) {
          console.error('[ChatStore] 暂停会话失败:', error)
          set({ error: `暂停会话失败: ${error instanceof Error ? error.message : '未知错误'}` })
        }
      },

      // 恢复 V2 流式会话
      resumeV2Session: async (sessionId: string) => {
        console.log('[ChatStore] 恢复 V2 会话:', sessionId)
        try {
          const result = await apiClient.resumeV2Session(sessionId)
          console.log('[ChatStore] 恢复结果:', result)
          // 更新本地状态
          set({
            v2Session: {
              ...get().v2Session,
              isPaused: false,
              sessionState: {
                session_id: sessionId,
                tenant_id: '',
                user_id: '',
                query: '',
                status: 'running',
                accumulated_answer: result.accumulated_answer,
                current_progress: result.current_progress,
                processing_steps: [],
                created_at: 0,
                updated_at: 0,
              },
            },
            streamingStatus: 'streaming',
          })
        } catch (error) {
          console.error('[ChatStore] 恢复会话失败:', error)
          set({ error: `恢复会话失败: ${error instanceof Error ? error.message : '未知错误'}` })
        }
      },

      // 取消 V2 流式会话
      cancelV2Session: async (sessionId: string) => {
        console.log('[ChatStore] 取消 V2 会话:', sessionId)
        try {
          const result = await apiClient.cancelV2Session(sessionId)
          console.log('[ChatStore] 取消结果:', result)
          // 清理会话状态
          set({
            v2Session: {
              currentSessionId: null,
              sessionState: null,
              isPaused: false,
            },
            streamingStatus: 'idle',
            currentAbortController: null,
            streamingMessageId: null,
          })
        } catch (error) {
          console.error('[ChatStore] 取消会话失败:', error)
          set({ error: `取消会话失败: ${error instanceof Error ? error.message : '未知错误'}` })
        }
      },

      // 获取 V2 会话状态
      getV2SessionState: async (sessionId: string): Promise<V2SessionState | null> => {
        console.log('[ChatStore] 获取 V2 会话状态:', sessionId)
        try {
          const sessionState = await apiClient.getV2SessionState(sessionId)
          // 更新本地状态
          set({
            v2Session: {
              currentSessionId: sessionId,
              sessionState,
              isPaused: sessionState.status === 'paused',
            },
          })
          return sessionState
        } catch (error) {
          console.error('[ChatStore] 获取会话状态失败:', error)
          return null
        }
      },

      // ========================================
      // 图表合并功能
      // ========================================

      // 切换图表选中状态
      toggleChartSelection: (messageId: string) => {
        const state = get()
        const isSelected = state.selectedCharts.includes(messageId)
        set({
          selectedCharts: isSelected
            ? state.selectedCharts.filter(id => id !== messageId)
            : [...state.selectedCharts, messageId]
        })
      },

      // 清空图表选择
      clearChartSelection: () => {
        set({ selectedCharts: [] })
      },

      // 合并选中的图表
      mergeCharts: async (messageIds: string[]) => {
        const state = get()
        const currentSession = state.currentSession
        if (!currentSession) {
          state.setError('没有活跃的会话')
          return
        }

        // 从消息中提取图表配置
        const messages = currentSession.messages
        const chartConfigs = messages
          .filter(m => messageIds.includes(m.id) && m.metadata?.echarts_option)
          .map(m => ({
            messageId: m.id,
            echarts_option: m.metadata?.echarts_option,
            title: m.metadata?.echarts_option?.title?.text || '图表'
          }))

        if (chartConfigs.length < 2) {
          state.setError('请至少选择两个图表进行合并')
          return
        }

        set({ isMergingCharts: true })

        try {
          // 构建合并提示
          const mergePrompt = `请将这些图表合并为一个双Y轴图表：

${chartConfigs.map((c, i) => `## 图表${i + 1}：${c.title}\n${JSON.stringify(c.echarts_option, null, 2)}`).join('\n\n')}

请分析这些图表的数据结构，生成一个合并的双Y轴图表配置。注意：
1. 提取并合并X轴数据（确保对齐）
2. 将不同指标分配到合适的Y轴（数值量级差异大的分配到不同轴）
3. 使用不同图表类型区分（折线图/柱状图）
4. 返回完整的 [CHART_START]...[CHART_END] 配置格式`

          // 发送合并请求
          await state.sendMessage(mergePrompt)

          // 清空选择
          set({ selectedCharts: [] })
        } catch (error) {
          console.error('[ChatStore] 合并图表失败:', error)
          state.setError(`合并图表失败: ${error instanceof Error ? error.message : '未知错误'}`)
        } finally {
          set({ isMergingCharts: false })
        }
      },

      // 从本地存储加载
      loadFromStorage: () => {
        if (typeof window === 'undefined') return

        try {
          const storedData = localStorage.getItem('data-agent-chat-store')
          if (!storedData) return

          const parsedData = JSON.parse(storedData)

          // 转换日期字符串回Date对象
          const sessions = parsedData.sessions?.map((s: any) => ({
            ...s,
            createdAt: new Date(s.createdAt),
            updatedAt: new Date(s.updatedAt),
            messages: s.messages?.map((m: any) => ({
              ...m,
              timestamp: new Date(m.timestamp)
            }))
          })) || []

          // 恢复输出格式配置
          const outputFormat = localStorage.getItem('data-agent-output-format') as 'markdown' | 'plain' || 'markdown'

          // 不自动恢复 currentSession，每次打开都是新对话（类似ChatGPT行为）
          // 历史会话仍然保存在 sessions 列表中，用户可以从历史对话中选择恢复
          set({
            sessions,
            currentSession: null,  // 每次打开都是空白新对话
            stats: parsedData.stats || {
              totalMessages: 0,
              totalSessions: 0,
              averageResponseTime: 0,
            },
            outputFormat,
          })
        } catch (error) {
          console.error('Failed to load chat store from storage:', error)
        }
      },

      // 保存到本地存储
      saveToStorage: () => {
        if (typeof window === 'undefined') return

        try {
          const state = get()
          const dataToStore = {
            sessions: state.sessions,
            currentSession: state.currentSession,
            stats: state.stats
          }

          localStorage.setItem('data-agent-chat-store', JSON.stringify(dataToStore))
        } catch (error) {
          console.error('Failed to save chat store to storage:', error)
        }
      },

      // 设置在线状态
      setOnline: (online: boolean) => {
        set({ isOnline: online })

        // 当重新上线时，尝试同步待发送的消息
        if (online) {
          get().syncPendingMessages()
        }
      },

      // 设置同步状态
      setSyncing: (syncing: boolean) => {
        set({ isSyncing: syncing })
      },

      // 从缓存加载数据
      loadFromCache: () => {
        try {
          const cachedSessions = getCachedSessions()

          if (cachedSessions.length > 0) {
            // 转换缓存数据为当前状态格式
            const sessions: ChatSession[] = cachedSessions.map(cachedSession => ({
              id: cachedSession.id,
              title: cachedSession.title,
              createdAt: cachedSession.createdAt,
              updatedAt: cachedSession.updatedAt,
              messages: cachedSession.messages.map(cachedMessage => ({
                id: cachedMessage.id,
                role: cachedMessage.role,
                content: cachedMessage.content,
                timestamp: cachedMessage.timestamp,
                status: (cachedMessage.status === 'pending' ? 'sending' :
                         cachedMessage.status === 'synced' ? 'sent' :
                         cachedMessage.status) as 'sending' | 'sent' | 'error',
                metadata: cachedMessage.metadata,
              })),
              isActive: cachedSession.isActive,
            }))

            // 更新状态
            set((state) => {
              const activeSession = sessions.find(s => s.isActive) || sessions[0] || null
              return {
                sessions,
                currentSession: activeSession,
                stats: {
                  ...state.stats,
                  totalSessions: sessions.length,
                  totalMessages: sessions.reduce((total, s) => total + s.messages.length, 0),
                }
              }
            })
          }
        } catch (error) {
          console.error('Failed to load from cache:', error)
        }
      },

      // 同步待发送的消息
      syncPendingMessages: async () => {
        const state = get()
        if (state.isSyncing || !state.isOnline) return

        set({ isSyncing: true })

        try {
          const result = await syncMessages(async (content, sessionId) => {
            // 使用store的sendMessage方法，但要避免无限循环
            if (!sessionId) {
              throw new Error('Session ID is required')
            }

            const currentState = get()
            if (currentState.currentSession?.id === sessionId) {
              // 获取历史消息用于上下文
              const currentSession = currentState.sessions.find(s => s.id === sessionId)
              // 安全获取消息列表，防止 undefined 错误
              const currentMessages = currentSession?.messages || []
              const historyMessages = currentMessages
                .filter(m => m.role !== 'system' && m.status !== 'error')
                .map(m => ({
                  role: m.role as 'user' | 'assistant' | 'system',
                  content: m.content
                }))

              // 直接调用API而不是通过store的sendMessage
              const queryRequest: ChatQueryRequest = {
                query: content,
                session_id: sessionId,
                history: historyMessages,  // 添加历史上下文
              }

              const response = await api.chat.sendQuery(queryRequest)

              if (response.status === 'error' || !response.data) {
                throw new Error(response.error || 'API Error: Unknown error')
              }

              const apiResult = response.data

              // 添加AI响应消息到缓存
              const assistantMessage = {
                id: generateId(),
                sessionId,
                role: 'assistant' as const,
                content: apiResult.answer || '抱歉，我现在无法回答这个问题。',
                timestamp: new Date(),
                status: 'sent' as const,
                metadata: {
                  sources: apiResult.sources,
                  reasoning: apiResult.reasoning,
                  confidence: apiResult.confidence,
                  table: apiResult.table,
                  chart: apiResult.chart,
                  echarts_option: apiResult.echarts_option,
                }
              }

              cacheMessage(sessionId, assistantMessage)
            }
          })

          // 更新统计信息
          const cacheStats = messageCacheService.getCacheStats()
          set((state) => ({
            stats: {
              ...state.stats,
              pendingMessages: cacheStats.pendingMessages,
            }
          }))

          if (!result.success) {
            set({
              error: result.errorMessage || '消息同步失败',
            })
          }
        } catch (error) {
          console.error('Failed to sync pending messages:', error)
          set({
            error: error instanceof Error ? error.message : '消息同步失败',
          })
        } finally {
          set({ isSyncing: false })
        }
      },

      // 清空缓存
      clearCache: () => {
        messageCacheService.clearCache()
      },
    })),
    {
      name: 'data-agent-chat-store',
    }
  )
)

// 初始化时从本地存储和缓存加载
if (typeof window !== 'undefined') {
  const store = useChatStore.getState()

  // 先从缓存加载（离线数据）
  store.loadFromCache()

  // 再从本地存储加载（在线数据）
  store.loadFromStorage()

  // 监听网络状态变化
  const handleOnline = () => {
    store.setOnline(true)
  }

  const handleOffline = () => {
    store.setOnline(false)
  }

  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)

  // 页面卸载时清理事件监听器
  window.addEventListener('beforeunload', () => {
    window.removeEventListener('online', handleOnline)
    window.removeEventListener('offline', handleOffline)
  })

  // 定期同步（每30秒）
  setInterval(() => {
    if (navigator.onLine && !store.isSyncing) {
      store.syncPendingMessages()
    }
  }, 30000)
}