import { create } from 'zustand'
import { devtools, subscribeWithSelector } from 'zustand/middleware'
import { api, ChatQueryRequest, ChatCompletionRequest, StreamEvent } from '@/lib/api-client'
import { apiClient } from '@/lib/api-client'
import { StreamCallbacks, ProcessingStep } from '@/types/chat'
import { messageCacheService, cacheSession, cacheMessage, getCachedSessions, getCachedSession, getCachedMessages, syncMessages } from '@/services/messageCacheService'

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
type StreamingStatus = 'idle' | 'streaming' | 'analyzing_sql' | 'generating_chart' | 'error' | 'done'

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
  
  // 流式响应状态
  streamingStatus: StreamingStatus
  currentAbortController: AbortController | null
  streamingMessageId: string | null  // 当前正在流式更新的消息ID

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

  // 状态管理
  setLoading: (loading: boolean) => void
  setTyping: (typing: boolean) => void
  setError: (error: string | null) => void
  setOnline: (online: boolean) => void
  setSyncing: (syncing: boolean) => void

  // 缓存和同步操作
  loadFromCache: () => void
  syncPendingMessages: () => Promise<void>
  clearCache: () => void

  // 本地存储操作
  loadFromStorage: () => void
  saveToStorage: () => void

  // 内部方法
  _sendOnlineMessage: (content: string, sessionId: string, dataSourceIds?: string | string[]) => Promise<void>
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
      streamingStatus: 'idle',
      currentAbortController: null,
      streamingMessageId: null,
      stats: {
        totalMessages: 0,
        totalSessions: 0,
        averageResponseTime: 0,
        pendingMessages: 0,
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
              totalSessions: state.stats.totalSessions + 1,
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
              totalSessions: Math.max(0, state.stats.totalSessions - 1),
              totalMessages: Math.max(0, state.stats.totalMessages -
                state.sessions.find(s => s.id === sessionId)?.messages.length || 0),
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
              totalSessions: Math.max(0, state.stats.totalSessions - sessionIds.length),
              totalMessages: Math.max(0, state.stats.totalMessages - deletedMessages),
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
        console.log('[ChatStore] sendMessage 调用, currentSession:', state.currentSession?.id, 'isLoading:', state.isLoading, 'isOnline:', state.isOnline, 'dataSourceIds:', dataSourceIds)

        if (!state.currentSession || state.isLoading) {
          console.warn('[ChatStore] 无法发送消息: currentSession 或 isLoading 状态不正确')
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
        const state = get()
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
          const historyMessages = currentMessages
            .filter(m => m.role !== 'system' && m.status !== 'error')  // 排除系统消息和错误消息
            .slice(0, -1)  // 排除刚刚添加的当前消息（避免重复）
            .map(m => ({
              role: m.role as 'user' | 'assistant' | 'system',
              content: m.content
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
              const activeSources = await dataSourceStore.fetchDataSources(tenantId, { active_only: true })
              if (activeSources && activeSources.length > 0) {
                finalConnectionId = activeSources[0].id
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
              const allSources = await dataSourceStore.fetchDataSources(tenantId, { active_only: true })
              const selectedSources = (allSources || []).filter(ds => normalizedDataSourceIds.includes(ds.id))
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

            // 流式内容累积
            let accumulatedContent = ''
            let accumulatedThinking = ''
            let toolInput = ''
            let toolOutput: any = null
            let echartsOption: any = null
            let processingSteps: ProcessingStep[] = []

            // 定义回调函数
            const callbacks: StreamCallbacks = {
              onContent: (delta: string) => {
                accumulatedContent += delta
                // 🔧 修复：如果当前状态是 analyzing_sql 或 generating_chart，收到 content 事件时切换回 streaming
                const currentStatus = get().streamingStatus
                if (currentStatus === 'analyzing_sql' || currentStatus === 'generating_chart') {
                  set({ streamingStatus: 'streaming' })
                }
                // 增量更新消息内容
                state.updateMessage(assistantMessageId, {
                  content: accumulatedContent,
                })
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
                // 🔧 恢复图表功能：处理后端发送的 ECharts 配置
                console.log('[ChatStore] 📊 收到图表配置:', chartOption)
                echartsOption = chartOption
                set({ streamingStatus: 'generating_chart' })
                
                // 立即更新消息的 metadata，以便前端可以渲染图表
                state.updateMessage(assistantMessageId, {
                  metadata: {
                    echarts_option: chartOption,
                  },
                })
              },
              onProcessingStep: (step: ProcessingStep) => {
                // 处理AI推理步骤事件
                console.log('[ChatStore] 🔄 收到处理步骤:', step)
                
                // 查找是否已存在相同步骤号的步骤
                const existingIndex = processingSteps.findIndex(s => s.step === step.step)
                if (existingIndex >= 0) {
                  // 更新已有步骤（例如从running变为completed）
                  processingSteps[existingIndex] = step
                } else {
                  // 添加新步骤
                  processingSteps.push(step)
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
                set({ streamingStatus: 'error' })
                state.updateMessage(assistantMessageId, {
                  status: 'error',
                  content: accumulatedContent || error || '生成失败',
                })
                state.setError(error || '流式响应错误')
              },
              onDone: () => {
                set({ streamingStatus: 'done' })
                // 流结束，更新最终消息状态（合并所有累积的内容）
                const finalContent = accumulatedContent || '抱歉，我现在无法回答这个问题。'
                
                // 如果 toolInput 有内容但还没添加到 content 中，添加它
                if (toolInput && !finalContent.includes('```sql')) {
                  accumulatedContent += `\n\`\`\`sql\n${toolInput}\n\`\`\`\n`
                }
                
                state.updateMessage(assistantMessageId, {
                  status: 'sent',
                  content: accumulatedContent || finalContent,
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
          } else {
            // 非流式模式（原有逻辑）
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
          state.setLoading(false)
          state.setTyping(false)
          console.log('[ChatStore] _sendOnlineMessage 完成')
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
              totalMessages: state.stats.totalMessages + 1,
            }
          }
        })

        get().saveToStorage()
      },

      // 更新消息（支持深度合并 metadata）
      updateMessage: (messageId: string, updates: Partial<ChatMessage>) => {
        set((state) => {
          if (!state.currentSession) return state

          // 辅助函数：深度合并消息更新
          const mergeMessage = (m: ChatMessage): ChatMessage => {
            if (m.id !== messageId) return m
            
            // 如果更新包含 metadata，需要深度合并
            if (updates.metadata && m.metadata) {
              return {
                ...m,
                ...updates,
                metadata: {
                  ...m.metadata,
                  ...updates.metadata,
                }
              }
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
              totalMessages: Math.max(0, state.stats.totalMessages - 1),
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
              totalMessages: Math.max(0, state.stats.totalMessages - sessionMessageCount),
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

          // 不自动恢复 currentSession，每次打开都是新对话（类似ChatGPT行为）
          // 历史会话仍然保存在 sessions 列表中，用户可以从历史对话中选择恢复
          set({
            sessions,
            currentSession: null,  // 每次打开都是空白新对话
            stats: parsedData.stats || {
              totalMessages: 0,
              totalSessions: 0,
              averageResponseTime: 0,
            }
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