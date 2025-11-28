/**
 * 消息缓存服务
 * 提供离线消息缓存和同步功能
 * 支持 IndexedDB 和 localStorage 双重存储策略
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
  version?: number // 添加版本号用于冲突检测
  clientId?: string // 添加客户端ID用于多设备同步
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
  version?: number // 添加版本号用于冲突检测
}

export interface SyncResult {
  success: boolean
  syncedMessages: string[]
  failedMessages: string[]
  errorMessage?: string
  conflictMessages?: string[] // 添加冲突消息列表
}

// 同步状态事件类型
export type SyncEventType = 'start' | 'progress' | 'complete' | 'error' | 'conflict'

export interface SyncEvent {
  type: SyncEventType
  progress?: number // 0-100
  totalMessages?: number
  syncedCount?: number
  failedCount?: number
  conflictCount?: number
  message?: string
}

// 同步事件监听器
export type SyncEventListener = (event: SyncEvent) => void

// IndexedDB 数据库配置
const DB_NAME = 'data-agent-offline-cache'
const DB_VERSION = 1
const SESSIONS_STORE = 'sessions'
const MESSAGES_STORE = 'messages'
const SYNC_QUEUE_STORE = 'syncQueue'

/**
 * IndexedDB 工具类
 */
class IndexedDBHelper {
  private db: IDBDatabase | null = null
  private dbReady: Promise<IDBDatabase> | null = null

  /**
   * 打开或创建数据库
   */
  async openDatabase(): Promise<IDBDatabase> {
    if (this.db) return this.db

    if (this.dbReady) return this.dbReady

    this.dbReady = new Promise((resolve, reject) => {
      if (typeof window === 'undefined' || !window.indexedDB) {
        reject(new Error('IndexedDB not supported'))
        return
      }

      const request = indexedDB.open(DB_NAME, DB_VERSION)

      request.onerror = () => {
        console.error('IndexedDB open error:', request.error)
        reject(request.error)
      }

      request.onsuccess = () => {
        this.db = request.result
        resolve(this.db)
      }

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result

        // 创建会话存储
        if (!db.objectStoreNames.contains(SESSIONS_STORE)) {
          const sessionsStore = db.createObjectStore(SESSIONS_STORE, { keyPath: 'id' })
          sessionsStore.createIndex('updatedAt', 'updatedAt', { unique: false })
          sessionsStore.createIndex('isActive', 'isActive', { unique: false })
        }

        // 创建消息存储
        if (!db.objectStoreNames.contains(MESSAGES_STORE)) {
          const messagesStore = db.createObjectStore(MESSAGES_STORE, { keyPath: 'id' })
          messagesStore.createIndex('sessionId', 'sessionId', { unique: false })
          messagesStore.createIndex('status', 'status', { unique: false })
          messagesStore.createIndex('timestamp', 'timestamp', { unique: false })
        }

        // 创建同步队列存储
        if (!db.objectStoreNames.contains(SYNC_QUEUE_STORE)) {
          db.createObjectStore(SYNC_QUEUE_STORE, { keyPath: 'messageId' })
        }
      }
    })

    return this.dbReady
  }

  /**
   * 获取所有会话
   */
  async getAllSessions(): Promise<CachedSession[]> {
    try {
      const db = await this.openDatabase()
      return new Promise((resolve, reject) => {
        const transaction = db.transaction([SESSIONS_STORE], 'readonly')
        const store = transaction.objectStore(SESSIONS_STORE)
        const request = store.getAll()

        request.onsuccess = () => {
          const sessions = request.result.map((s: any) => ({
            ...s,
            createdAt: new Date(s.createdAt),
            updatedAt: new Date(s.updatedAt),
            lastSyncAt: s.lastSyncAt ? new Date(s.lastSyncAt) : undefined,
          }))
          resolve(sessions)
        }

        request.onerror = () => reject(request.error)
      })
    } catch (error) {
      console.error('IndexedDB getAllSessions error:', error)
      return []
    }
  }

  /**
   * 保存会话
   */
  async saveSession(session: CachedSession): Promise<void> {
    try {
      const db = await this.openDatabase()
      return new Promise((resolve, reject) => {
        const transaction = db.transaction([SESSIONS_STORE], 'readwrite')
        const store = transaction.objectStore(SESSIONS_STORE)

        const sessionData = {
          ...session,
          createdAt: session.createdAt.toISOString(),
          updatedAt: session.updatedAt.toISOString(),
          lastSyncAt: session.lastSyncAt?.toISOString(),
          messages: [], // 消息单独存储
        }

        const request = store.put(sessionData)
        request.onsuccess = () => resolve()
        request.onerror = () => reject(request.error)
      })
    } catch (error) {
      console.error('IndexedDB saveSession error:', error)
    }
  }

  /**
   * 获取会话的所有消息
   */
  async getMessagesBySession(sessionId: string): Promise<CachedMessage[]> {
    try {
      const db = await this.openDatabase()
      return new Promise((resolve, reject) => {
        const transaction = db.transaction([MESSAGES_STORE], 'readonly')
        const store = transaction.objectStore(MESSAGES_STORE)
        const index = store.index('sessionId')
        const request = index.getAll(sessionId)

        request.onsuccess = () => {
          const messages = request.result.map((m: any) => ({
            ...m,
            timestamp: new Date(m.timestamp),
            lastSyncAttempt: m.lastSyncAttempt ? new Date(m.lastSyncAttempt) : undefined,
          }))
          // 按时间排序
          messages.sort((a: CachedMessage, b: CachedMessage) =>
            a.timestamp.getTime() - b.timestamp.getTime()
          )
          resolve(messages)
        }

        request.onerror = () => reject(request.error)
      })
    } catch (error) {
      console.error('IndexedDB getMessagesBySession error:', error)
      return []
    }
  }

  /**
   * 保存消息
   */
  async saveMessage(message: CachedMessage): Promise<void> {
    try {
      const db = await this.openDatabase()
      return new Promise((resolve, reject) => {
        const transaction = db.transaction([MESSAGES_STORE], 'readwrite')
        const store = transaction.objectStore(MESSAGES_STORE)

        const messageData = {
          ...message,
          timestamp: message.timestamp.toISOString(),
          lastSyncAttempt: message.lastSyncAttempt?.toISOString(),
        }

        const request = store.put(messageData)
        request.onsuccess = () => resolve()
        request.onerror = () => reject(request.error)
      })
    } catch (error) {
      console.error('IndexedDB saveMessage error:', error)
    }
  }

  /**
   * 获取待同步消息
   */
  async getPendingMessages(): Promise<CachedMessage[]> {
    try {
      const db = await this.openDatabase()
      return new Promise((resolve, reject) => {
        const transaction = db.transaction([MESSAGES_STORE], 'readonly')
        const store = transaction.objectStore(MESSAGES_STORE)
        const index = store.index('status')
        const request = index.getAll('pending')

        request.onsuccess = () => {
          const messages = request.result.map((m: any) => ({
            ...m,
            timestamp: new Date(m.timestamp),
            lastSyncAttempt: m.lastSyncAttempt ? new Date(m.lastSyncAttempt) : undefined,
          }))
          resolve(messages)
        }

        request.onerror = () => reject(request.error)
      })
    } catch (error) {
      console.error('IndexedDB getPendingMessages error:', error)
      return []
    }
  }

  /**
   * 添加到同步队列
   */
  async addToSyncQueue(messageId: string): Promise<void> {
    try {
      const db = await this.openDatabase()
      return new Promise((resolve, reject) => {
        const transaction = db.transaction([SYNC_QUEUE_STORE], 'readwrite')
        const store = transaction.objectStore(SYNC_QUEUE_STORE)
        const request = store.put({ messageId, addedAt: new Date().toISOString() })

        request.onsuccess = () => resolve()
        request.onerror = () => reject(request.error)
      })
    } catch (error) {
      console.error('IndexedDB addToSyncQueue error:', error)
    }
  }

  /**
   * 从同步队列移除
   */
  async removeFromSyncQueue(messageId: string): Promise<void> {
    try {
      const db = await this.openDatabase()
      return new Promise((resolve, reject) => {
        const transaction = db.transaction([SYNC_QUEUE_STORE], 'readwrite')
        const store = transaction.objectStore(SYNC_QUEUE_STORE)
        const request = store.delete(messageId)

        request.onsuccess = () => resolve()
        request.onerror = () => reject(request.error)
      })
    } catch (error) {
      console.error('IndexedDB removeFromSyncQueue error:', error)
    }
  }

  /**
   * 获取同步队列
   */
  async getSyncQueue(): Promise<string[]> {
    try {
      const db = await this.openDatabase()
      return new Promise((resolve, reject) => {
        const transaction = db.transaction([SYNC_QUEUE_STORE], 'readonly')
        const store = transaction.objectStore(SYNC_QUEUE_STORE)
        const request = store.getAll()

        request.onsuccess = () => {
          resolve(request.result.map((item: any) => item.messageId))
        }

        request.onerror = () => reject(request.error)
      })
    } catch (error) {
      console.error('IndexedDB getSyncQueue error:', error)
      return []
    }
  }

  /**
   * 删除会话及其消息
   */
  async deleteSession(sessionId: string): Promise<void> {
    try {
      const db = await this.openDatabase()

      // 先删除该会话的所有消息
      const messages = await this.getMessagesBySession(sessionId)
      const messageIds = messages.map(m => m.id)

      return new Promise((resolve, reject) => {
        const transaction = db.transaction(
          [SESSIONS_STORE, MESSAGES_STORE, SYNC_QUEUE_STORE],
          'readwrite'
        )

        // 删除会话
        transaction.objectStore(SESSIONS_STORE).delete(sessionId)

        // 删除消息和同步队列项
        const messagesStore = transaction.objectStore(MESSAGES_STORE)
        const syncQueueStore = transaction.objectStore(SYNC_QUEUE_STORE)

        messageIds.forEach(id => {
          messagesStore.delete(id)
          syncQueueStore.delete(id)
        })

        transaction.oncomplete = () => resolve()
        transaction.onerror = () => reject(transaction.error)
      })
    } catch (error) {
      console.error('IndexedDB deleteSession error:', error)
    }
  }

  /**
   * 清空所有数据
   */
  async clearAll(): Promise<void> {
    try {
      const db = await this.openDatabase()
      return new Promise((resolve, reject) => {
        const transaction = db.transaction(
          [SESSIONS_STORE, MESSAGES_STORE, SYNC_QUEUE_STORE],
          'readwrite'
        )

        transaction.objectStore(SESSIONS_STORE).clear()
        transaction.objectStore(MESSAGES_STORE).clear()
        transaction.objectStore(SYNC_QUEUE_STORE).clear()

        transaction.oncomplete = () => resolve()
        transaction.onerror = () => reject(transaction.error)
      })
    } catch (error) {
      console.error('IndexedDB clearAll error:', error)
    }
  }

  /**
   * 检查 IndexedDB 是否可用
   */
  isSupported(): boolean {
    return typeof window !== 'undefined' && !!window.indexedDB
  }
}

// 创建 IndexedDB 帮助器实例
const indexedDBHelper = new IndexedDBHelper()

/**
 * 生成唯一客户端ID
 */
function getClientId(): string {
  if (typeof window === 'undefined') return 'server'

  let clientId = localStorage.getItem('data-agent-client-id')
  if (!clientId) {
    clientId = `client-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    localStorage.setItem('data-agent-client-id', clientId)
  }
  return clientId
}

class MessageCacheService {
  private cacheKey = 'data-agent-message-cache'
  private syncQueueKey = 'data-agent-sync-queue'
  private maxRetries = 3
  private syncRetryDelay = 5000 // 5 seconds
  private syncEventListeners: Set<SyncEventListener> = new Set()
  private useIndexedDB: boolean = false
  private clientId: string

  constructor() {
    this.clientId = getClientId()
    // 检查是否支持 IndexedDB
    this.useIndexedDB = indexedDBHelper.isSupported()
  }

  /**
   * 添加同步事件监听器
   */
  addSyncEventListener(listener: SyncEventListener): void {
    this.syncEventListeners.add(listener)
  }

  /**
   * 移除同步事件监听器
   */
  removeSyncEventListener(listener: SyncEventListener): void {
    this.syncEventListeners.delete(listener)
  }

  /**
   * 触发同步事件
   */
  private emitSyncEvent(event: SyncEvent): void {
    this.syncEventListeners.forEach(listener => {
      try {
        listener(event)
      } catch (error) {
        console.error('Sync event listener error:', error)
      }
    })
  }

  /**
   * 获取缓存的消息数据 (localStorage 回退方案)
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
   * 保存缓存数据 (localStorage 回退方案)
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
   * 缓存会话 (支持 IndexedDB)
   */
  cacheSession(session: CachedSession): void {
    // 添加版本号
    const sessionWithVersion = {
      ...session,
      version: (session.version || 0) + 1,
      isDirty: true,
    }

    // 使用 IndexedDB 存储
    if (this.useIndexedDB) {
      indexedDBHelper.saveSession(sessionWithVersion).catch(console.error)
    }

    // 同时保存到 localStorage 作为备份
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
   * 缓存消息 (支持 IndexedDB)
   */
  cacheMessage(sessionId: string, message: Omit<CachedMessage, 'syncAttempted' | 'lastSyncAttempt'>): void {
    const fullMessage: CachedMessage = {
      ...message,
      syncAttempted: 0,
      version: 1,
      clientId: this.clientId,
    }

    // 使用 IndexedDB 存储
    if (this.useIndexedDB) {
      indexedDBHelper.saveMessage(fullMessage).catch(console.error)

      // 如果是待发送消息，加入同步队列
      if (message.status === 'pending') {
        indexedDBHelper.addToSyncQueue(fullMessage.id).catch(console.error)
      }
    }

    // 同时保存到 localStorage 作为备份
    const { sessions, syncQueue } = this.getCachedData()
    const sessionIndex = sessions.findIndex(s => s.id === sessionId)

    if (sessionIndex < 0) {
      console.warn('Session not found for caching message:', sessionId)
      return
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
   * 同步消息到服务器 (增强版，支持事件通知)
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
        conflictMessages: [],
      }
    }

    // 触发同步开始事件
    this.emitSyncEvent({
      type: 'start',
      totalMessages: pendingMessages.length,
      progress: 0,
    })

    const syncedMessages: string[] = []
    const failedMessages: string[] = []
    const conflictMessages: string[] = []
    let updatedSessions = [...sessions]
    let updatedSyncQueue = [...syncQueue]

    // 按时间戳排序，先同步旧消息
    pendingMessages.sort((a, b) => a.message.timestamp.getTime() - b.message.timestamp.getTime())

    let processedCount = 0

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
            updatedSessions[sessionIndex].messages[messageIndex].version =
              (updatedSessions[sessionIndex].messages[messageIndex].version || 0) + 1
            updatedSessions[sessionIndex].lastSyncAt = new Date()
          }
        }

        syncedMessages.push(message.id)

        // 从同步队列中移除
        const queueIndex = updatedSyncQueue.indexOf(message.id)
        if (queueIndex >= 0) {
          updatedSyncQueue.splice(queueIndex, 1)
        }

        // 同时更新 IndexedDB
        if (this.useIndexedDB) {
          indexedDBHelper.removeFromSyncQueue(message.id).catch(console.error)
        }

      } catch (error) {
        console.error(`Failed to sync message ${message.id}:`, error)

        // 更新重试次数
        const sessionIndex = updatedSessions.findIndex(s => s.id === sessionId)
        if (sessionIndex >= 0) {
          const messageIndex = updatedSessions[sessionIndex].messages.findIndex(m => m.id === message.id)
          if (messageIndex >= 0) {
            updatedSessions[sessionIndex].messages[messageIndex].syncAttempted =
              (updatedSessions[sessionIndex].messages[messageIndex].syncAttempted || 0) + 1
            updatedSessions[sessionIndex].messages[messageIndex].lastSyncAttempt = new Date()

            // 如果超过最大重试次数，标记为失败
            if (updatedSessions[sessionIndex].messages[messageIndex].syncAttempted >= this.maxRetries) {
              updatedSessions[sessionIndex].messages[messageIndex].status = 'error'
              const queueIndex = updatedSyncQueue.indexOf(message.id)
              if (queueIndex >= 0) {
                updatedSyncQueue.splice(queueIndex, 1)
              }
              failedMessages.push(message.id)

              // 触发错误事件
              this.emitSyncEvent({
                type: 'error',
                message: `消息 ${message.id} 同步失败，已达到最大重试次数`,
              })
            }
          }
        }
      }

      // 更新进度
      processedCount++
      const progress = Math.round((processedCount / pendingMessages.length) * 100)
      this.emitSyncEvent({
        type: 'progress',
        progress,
        totalMessages: pendingMessages.length,
        syncedCount: syncedMessages.length,
        failedCount: failedMessages.length,
      })
    }

    // 保存更新的缓存数据
    this.saveCachedData(updatedSessions, updatedSyncQueue)

    const result: SyncResult = {
      success: failedMessages.length === 0,
      syncedMessages,
      failedMessages,
      conflictMessages,
      errorMessage: failedMessages.length > 0 ? `同步失败 ${failedMessages.length} 条消息` : undefined,
    }

    // 触发同步完成事件
    this.emitSyncEvent({
      type: 'complete',
      progress: 100,
      totalMessages: pendingMessages.length,
      syncedCount: syncedMessages.length,
      failedCount: failedMessages.length,
      conflictCount: conflictMessages.length,
      message: result.success ? '同步完成' : result.errorMessage,
    })

    return result
  }

  /**
   * 重试失败的消息
   */
  async retryFailedMessages(
    sendMessage: (content: string, sessionId?: string) => Promise<void>
  ): Promise<SyncResult> {
    const { sessions, syncQueue } = this.getCachedData()

    // 找出所有失败的消息
    const failedMessages: { sessionId: string, message: CachedMessage }[] = []

    sessions.forEach(session => {
      session.messages.forEach(message => {
        if (message.status === 'error') {
          failedMessages.push({ sessionId: session.id, message })
        }
      })
    })

    if (failedMessages.length === 0) {
      return {
        success: true,
        syncedMessages: [],
        failedMessages: [],
        conflictMessages: [],
      }
    }

    // 重置重试次数并重新加入同步队列
    let updatedSessions = [...sessions]
    let updatedSyncQueue = [...syncQueue]

    failedMessages.forEach(({ sessionId, message }) => {
      const sessionIndex = updatedSessions.findIndex(s => s.id === sessionId)
      if (sessionIndex >= 0) {
        const messageIndex = updatedSessions[sessionIndex].messages.findIndex(m => m.id === message.id)
        if (messageIndex >= 0) {
          updatedSessions[sessionIndex].messages[messageIndex].status = 'pending'
          updatedSessions[sessionIndex].messages[messageIndex].syncAttempted = 0

          if (!updatedSyncQueue.includes(message.id)) {
            updatedSyncQueue.push(message.id)
          }
        }
      }
    })

    this.saveCachedData(updatedSessions, updatedSyncQueue)

    // 重新同步
    return this.syncMessages(sendMessage)
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

    // 同时清空 IndexedDB
    if (this.useIndexedDB) {
      indexedDBHelper.clearAll().catch(console.error)
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

// 新增导出：同步事件监听器
export const addSyncEventListener = (listener: SyncEventListener): void => {
  messageCacheService.addSyncEventListener(listener)
}

export const removeSyncEventListener = (listener: SyncEventListener): void => {
  messageCacheService.removeSyncEventListener(listener)
}

// 新增导出：重试失败消息
export const retryFailedMessages = async (
  sendMessage: (content: string, sessionId?: string) => Promise<void>
): Promise<SyncResult> => {
  return messageCacheService.retryFailedMessages(sendMessage)
}