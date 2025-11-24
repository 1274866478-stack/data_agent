/**
 * 消息缓存服务
 * 提供离线消息缓存和同步功能
 */

export interface CachedMessage {
  id: string
  sessionId: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  status: 'pending' | 'sent' | 'error' | 'synced'
  metadata?: {
    sources?: string[]
    reasoning?: string
    confidence?: number
  }
  syncAttempted?: number
  lastSyncAttempt?: Date
}

export interface CachedSession {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  messages: CachedMessage[]
  isActive: boolean
  isDirty: boolean
  lastSyncAt?: Date
}

export interface SyncResult {
  success: boolean
  syncedMessages: string[]
  failedMessages: string[]
  errorMessage?: string
}

class MessageCacheService {
  private cacheKey = 'data-agent-message-cache'
  private syncQueueKey = 'data-agent-sync-queue'
  private maxRetries = 3
  private syncRetryDelay = 5000 // 5 seconds

  /**
   * 获取缓存的消息数据
   */
  private getCachedData(): { sessions: CachedSession[], syncQueue: string[] } {
    if (typeof window === 'undefined') {
      return { sessions: [], syncQueue: [] }
    }

    try {
      const cachedData = localStorage.getItem(this.cacheKey)
      const syncQueueData = localStorage.getItem(this.syncQueueKey)

      const sessions = cachedData ? JSON.parse(cachedData) : []
      const syncQueue = syncQueueData ? JSON.parse(syncQueueData) : []

      // 转换日期字符串回Date对象
      const processedSessions = sessions.map((session: any) => ({
        ...session,
        createdAt: new Date(session.createdAt),
        updatedAt: new Date(session.updatedAt),
        lastSyncAt: session.lastSyncAt ? new Date(session.lastSyncAt) : undefined,
        messages: session.messages.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
          lastSyncAttempt: msg.lastSyncAttempt ? new Date(msg.lastSyncAttempt) : undefined,
        }))
      }))

      return { sessions: processedSessions, syncQueue }
    } catch (error) {
      console.error('Failed to load cached data:', error)
      return { sessions: [], syncQueue: [] }
    }
  }

  /**
   * 保存缓存数据
   */
  private saveCachedData(sessions: CachedSession[], syncQueue: string[]): void {
    if (typeof window === 'undefined') {
      return
    }

    try {
      localStorage.setItem(this.cacheKey, JSON.stringify(sessions))
      localStorage.setItem(this.syncQueueKey, JSON.stringify(syncQueue))
    } catch (error) {
      console.error('Failed to save cached data:', error)
    }
  }

  /**
   * 缓存会话
   */
  cacheSession(session: CachedSession): void {
    const { sessions, syncQueue } = this.getCachedData()
    const existingIndex = sessions.findIndex(s => s.id === session.id)

    if (existingIndex >= 0) {
      sessions[existingIndex] = { ...session, isDirty: true }
    } else {
      sessions.push({ ...session, isDirty: true })
    }

    this.saveCachedData(sessions, syncQueue)
  }

  /**
   * 缓存消息
   */
  cacheMessage(sessionId: string, message: Omit<CachedMessage, 'syncAttempted' | 'lastSyncAttempt'>): void {
    const { sessions, syncQueue } = this.getCachedData()
    const sessionIndex = sessions.findIndex(s => s.id === sessionId)

    if (sessionIndex < 0) {
      console.warn('Session not found for caching message:', sessionId)
      return
    }

    const fullMessage: CachedMessage = {
      ...message,
      syncAttempted: 0,
    }

    const session = sessions[sessionIndex]
    const existingMessageIndex = session.messages.findIndex(m => m.id === message.id)

    if (existingMessageIndex >= 0) {
      session.messages[existingMessageIndex] = fullMessage
    } else {
      session.messages.push(fullMessage)
    }

    session.updatedAt = new Date()
    session.isDirty = true

    // 如果是待发送的消息，加入同步队列
    if (message.status === 'pending' && !syncQueue.includes(fullMessage.id)) {
      syncQueue.push(fullMessage.id)
    }

    this.saveCachedData(sessions, syncQueue)
  }

  /**
   * 获取缓存的所有会话
   */
  getCachedSessions(): CachedSession[] {
    const { sessions } = this.getCachedData()
    return sessions
  }

  /**
   * 获取缓存的单个会话
   */
  getCachedSession(sessionId: string): CachedSession | null {
    const { sessions } = this.getCachedData()
    return sessions.find(s => s.id === sessionId) || null
  }

  /**
   * 获取缓存的消息
   */
  getCachedMessages(sessionId: string): CachedMessage[] {
    const session = this.getCachedSession(sessionId)
    return session ? session.messages : []
  }

  /**
   * 更新消息状态
   */
  updateMessageStatus(sessionId: string, messageId: string, status: CachedMessage['status']): void {
    const { sessions, syncQueue } = this.getCachedData()
    const sessionIndex = sessions.findIndex(s => s.id === sessionId)

    if (sessionIndex < 0) {
      return
    }

    const session = sessions[sessionIndex]
    const messageIndex = session.messages.findIndex(m => m.id === messageId)

    if (messageIndex < 0) {
      return
    }

    session.messages[messageIndex].status = status
    session.updatedAt = new Date()
    session.isDirty = true

    // 如果消息已同步，从同步队列中移除
    if (status === 'synced' || status === 'sent') {
      const queueIndex = syncQueue.indexOf(messageId)
      if (queueIndex >= 0) {
        syncQueue.splice(queueIndex, 1)
      }
    }

    this.saveCachedData(sessions, syncQueue)
  }

  /**
   * 删除缓存的消息
   */
  deleteCachedMessage(sessionId: string, messageId: string): void {
    const { sessions, syncQueue } = this.getCachedData()
    const sessionIndex = sessions.findIndex(s => s.id === sessionId)

    if (sessionIndex < 0) {
      return
    }

    const session = sessions[sessionIndex]
    session.messages = session.messages.filter(m => m.id !== messageId)
    session.updatedAt = new Date()
    session.isDirty = true

    // 从同步队列中移除
    const queueIndex = syncQueue.indexOf(messageId)
    if (queueIndex >= 0) {
      syncQueue.splice(queueIndex, 1)
    }

    this.saveCachedData(sessions, syncQueue)
  }

  /**
   * 删除缓存的会话
   */
  deleteCachedSession(sessionId: string): void {
    const { sessions, syncQueue } = this.getCachedData()
    const sessionIndex = sessions.findIndex(s => s.id === sessionId)

    if (sessionIndex < 0) {
      return
    }

    const session = sessions[sessionIndex]

    // 从同步队列中移除该会话的所有消息
    const messageIds = session.messages.map(m => m.id)
    const updatedSyncQueue = syncQueue.filter(id => !messageIds.includes(id))

    // 删除会话
    sessions.splice(sessionIndex, 1)

    this.saveCachedData(sessions, updatedSyncQueue)
  }

  /**
   * 获取待同步的消息队列
   */
  getSyncQueue(): string[] {
    const { syncQueue } = this.getCachedData()
    return [...syncQueue]
  }

  /**
   * 获取待同步的消息详情
   */
  getPendingMessages(): { sessionId: string, message: CachedMessage }[] {
    const { sessions, syncQueue } = this.getCachedData()
    const pendingMessages: { sessionId: string, message: CachedMessage }[] = []

    for (const messageId of syncQueue) {
      for (const session of sessions) {
        const message = session.messages.find(m => m.id === messageId)
        if (message && message.status === 'pending') {
          pendingMessages.push({ sessionId: session.id, message })
          break
        }
      }
    }

    return pendingMessages
  }

  /**
   * 同步消息到服务器
   */
  async syncMessages(
    sendMessage: (content: string, sessionId?: string) => Promise<void>
  ): Promise<SyncResult> {
    const { sessions, syncQueue } = this.getCachedData()
    const pendingMessages = this.getPendingMessages()

    if (pendingMessages.length === 0) {
      return {
        success: true,
        syncedMessages: [],
        failedMessages: [],
      }
    }

    const syncedMessages: string[] = []
    const failedMessages: string[] = []
    let updatedSessions = [...sessions]
    let updatedSyncQueue = [...syncQueue]

    // 按时间戳排序，先同步旧消息
    pendingMessages.sort((a, b) => a.message.timestamp.getTime() - b.message.timestamp.getTime())

    for (const { sessionId, message } of pendingMessages) {
      try {
        // 尝试发送消息
        await sendMessage(message.content, sessionId)

        // 更新消息状态
        const sessionIndex = updatedSessions.findIndex(s => s.id === sessionId)
        if (sessionIndex >= 0) {
          const messageIndex = updatedSessions[sessionIndex].messages.findIndex(m => m.id === message.id)
          if (messageIndex >= 0) {
            updatedSessions[sessionIndex].messages[messageIndex].status = 'synced'
            updatedSessions[sessionIndex].messages[messageIndex].lastSyncAttempt = new Date()
            updatedSessions[sessionIndex].lastSyncAt = new Date()
          }
        }

        syncedMessages.push(message.id)

        // 从同步队列中移除
        const queueIndex = updatedSyncQueue.indexOf(message.id)
        if (queueIndex >= 0) {
          updatedSyncQueue.splice(queueIndex, 1)
        }

      } catch (error) {
        console.error(`Failed to sync message ${message.id}:`, error)

        // 更新重试次数
        const sessionIndex = updatedSessions.findIndex(s => s.id === sessionId)
        if (sessionIndex >= 0) {
          const messageIndex = updatedSessions[sessionIndex].messages.findIndex(m => m.id === message.id)
          if (messageIndex >= 0) {
            updatedSessions[sessionIndex].messages[messageIndex].syncAttempted += 1
            updatedSessions[sessionIndex].messages[messageIndex].lastSyncAttempt = new Date()

            // 如果超过最大重试次数，标记为失败
            if (updatedSessions[sessionIndex].messages[messageIndex].syncAttempted >= this.maxRetries) {
              updatedSessions[sessionIndex].messages[messageIndex].status = 'error'
              const queueIndex = updatedSyncQueue.indexOf(message.id)
              if (queueIndex >= 0) {
                updatedSyncQueue.splice(queueIndex, 1)
              }
              failedMessages.push(message.id)
            }
          }
        }
      }
    }

    // 保存更新的缓存数据
    this.saveCachedData(updatedSessions, updatedSyncQueue)

    return {
      success: failedMessages.length === 0,
      syncedMessages,
      failedMessages,
      errorMessage: failedMessages.length > 0 ? `Failed to sync ${failedMessages.length} messages` : undefined,
    }
  }

  /**
   * 清理过期的缓存数据
   */
  cleanupExpiredCache(maxAge: number = 7 * 24 * 60 * 60 * 1000): void { // 默认7天
    const { sessions, syncQueue } = this.getCachedData()
    const now = new Date()
    const cutoffTime = new Date(now.getTime() - maxAge)

    const filteredSessions = sessions.filter(session => {
      return session.updatedAt > cutoffTime
    })

    const activeMessageIds = new Set<string>()
    filteredSessions.forEach(session => {
      session.messages.forEach(message => {
        activeMessageIds.add(message.id)
      })
    })

    const filteredSyncQueue = syncQueue.filter(messageId => activeMessageIds.has(messageId))

    this.saveCachedData(filteredSessions, filteredSyncQueue)
  }

  /**
   * 清空所有缓存
   */
  clearCache(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(this.cacheKey)
      localStorage.removeItem(this.syncQueueKey)
    }
  }

  /**
   * 获取缓存统计信息
   */
  getCacheStats(): {
    totalSessions: number
    totalMessages: number
    pendingMessages: number
    failedMessages: number
    cacheSize: number
  } {
    const { sessions } = this.getCachedData()
    let totalMessages = 0
    let pendingMessages = 0
    let failedMessages = 0

    sessions.forEach(session => {
      totalMessages += session.messages.length
      session.messages.forEach(message => {
        if (message.status === 'pending') {
          pendingMessages++
        } else if (message.status === 'error') {
          failedMessages++
        }
      })
    })

    let cacheSize = 0
    if (typeof window !== 'undefined') {
      try {
        const cacheData = localStorage.getItem(this.cacheKey)
        const syncQueueData = localStorage.getItem(this.syncQueueKey)
        cacheSize = (cacheData?.length || 0) + (syncQueueData?.length || 0)
      } catch (error) {
        console.error('Failed to calculate cache size:', error)
      }
    }

    return {
      totalSessions: sessions.length,
      totalMessages,
      pendingMessages,
      failedMessages,
      cacheSize,
    }
  }
}

// 创建单例实例
export const messageCacheService = new MessageCacheService()

// 便捷函数导出
export const cacheSession = (session: CachedSession): void => {
  messageCacheService.cacheSession(session)
}

export const cacheMessage = (sessionId: string, message: Omit<CachedMessage, 'syncAttempted' | 'lastSyncAttempt'>): void => {
  messageCacheService.cacheMessage(sessionId, message)
}

export const getCachedSessions = (): CachedSession[] => {
  return messageCacheService.getCachedSessions()
}

export const getCachedSession = (sessionId: string): CachedSession | null => {
  return messageCacheService.getCachedSession(sessionId)
}

export const getCachedMessages = (sessionId: string): CachedMessage[] => {
  return messageCacheService.getCachedMessages(sessionId)
}

export const syncMessages = async (sendMessage: (content: string, sessionId?: string) => Promise<void>): Promise<SyncResult> => {
  return messageCacheService.syncMessages(sendMessage)
}

export const clearCache = (): void => {
  messageCacheService.clearCache()
}

export const getCacheStats = () => {
  return messageCacheService.getCacheStats()
}