/**
 * 消息缓存服务测试
 */

import { messageCacheService, cacheSession, cacheMessage, getCachedSessions, getCachedSession, getCachedMessages, syncMessages } from '../messageCacheService'

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

// Mock fetch
global.fetch = jest.fn()

const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>

describe('MessageCacheService', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    localStorageMock.getItem.mockReturnValue(null)
  })

  describe('缓存会话', () => {
    it('应该缓存新会话', () => {
      const session = {
        id: 'session-1',
        title: '测试会话',
        createdAt: new Date(),
        updatedAt: new Date(),
        messages: [],
        isActive: true,
        isDirty: false,
      }

      cacheSession(session)

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'data-agent-message-cache',
        expect.stringContaining('session-1')
      )
    })

    it('应该更新现有会话', () => {
      const initialSession = {
        id: 'session-1',
        title: '初始标题',
        createdAt: new Date(),
        updatedAt: new Date(),
        messages: [],
        isActive: true,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([initialSession]))

      const updatedSession = {
        ...initialSession,
        title: '更新标题',
        updatedAt: new Date(),
      }

      cacheSession(updatedSession)

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'data-agent-message-cache',
        expect.stringContaining('更新标题')
      )
    })
  })

  describe('缓存消息', () => {
    it('应该缓存新消息', () => {
      const session = {
        id: 'session-1',
        title: '测试会话',
        createdAt: new Date(),
        updatedAt: new Date(),
        messages: [],
        isActive: true,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([session]))

      const message = {
        id: 'msg-1',
        sessionId: 'session-1',
        role: 'user' as const,
        content: '测试消息',
        timestamp: new Date(),
        status: 'pending' as const,
      }

      cacheMessage('session-1', message)

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'data-agent-message-cache',
        expect.stringContaining('测试消息')
      )
    })

    it('应该将待发送消息加入同步队列', () => {
      const session = {
        id: 'session-1',
        title: '测试会话',
        createdAt: new Date(),
        updatedAt: new Date(),
        messages: [],
        isActive: true,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([session]))
      localStorageMock.getItem.mockReturnValueOnce('[]') // 初始同步队列为空

      const message = {
        id: 'msg-1',
        sessionId: 'session-1',
        role: 'user' as const,
        content: '待发送消息',
        timestamp: new Date(),
        status: 'pending' as const,
      }

      cacheMessage('session-1', message)

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'data-agent-sync-queue',
        expect.stringContaining('msg-1')
      )
    })

    it('不应该将已发送消息加入同步队列', () => {
      const session = {
        id: 'session-1',
        title: '测试会话',
        createdAt: new Date(),
        updatedAt: new Date(),
        messages: [],
        isActive: true,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([session]))

      const message = {
        id: 'msg-1',
        sessionId: 'session-1',
        role: 'user' as const,
        content: '已发送消息',
        timestamp: new Date(),
        status: 'sent' as const,
      }

      cacheMessage('session-1', message)

      // 同步队列应该保持为空
      expect(localStorageMock.setItem).not.toHaveBeenCalledWith(
        'data-agent-sync-queue',
        expect.anything()
      )
    })
  })

  describe('获取缓存数据', () => {
    it('应该获取所有缓存会话', () => {
      const sessions = [
        {
          id: 'session-1',
          title: '会话1',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          messages: [],
          isActive: true,
          isDirty: false,
        },
        {
          id: 'session-2',
          title: '会话2',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          messages: [],
          isActive: false,
          isDirty: false,
        },
      ]

      localStorageMock.getItem.mockReturnValue(JSON.stringify(sessions))

      const cachedSessions = getCachedSessions()

      expect(cachedSessions).toHaveLength(2)
      expect(cachedSessions[0].id).toBe('session-1')
      expect(cachedSessions[1].id).toBe('session-2')
    })

    it('应该获取单个缓存会话', () => {
      const session = {
        id: 'session-1',
        title: '测试会话',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [],
        isActive: true,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([session]))

      const cachedSession = getCachedSession('session-1')

      expect(cachedSession).not.toBeNull()
      expect(cachedSession?.id).toBe('session-1')
      expect(cachedSession?.title).toBe('测试会话')
    })

    it('应该返回null当会话不存在', () => {
      localStorageMock.getItem.mockReturnValue(JSON.stringify([]))

      const cachedSession = getCachedSession('nonexistent')

      expect(cachedSession).toBeNull()
    })

    it('应该获取会话的消息', () => {
      const messages = [
        {
          id: 'msg-1',
          sessionId: 'session-1',
          role: 'user' as const,
          content: '消息1',
          timestamp: new Date().toISOString(),
          status: 'sent' as const,
        },
        {
          id: 'msg-2',
          sessionId: 'session-1',
          role: 'assistant' as const,
          content: '消息2',
          timestamp: new Date().toISOString(),
          status: 'sent' as const,
        },
      ]

      const session = {
        id: 'session-1',
        title: '测试会话',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages,
        isActive: true,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([session]))

      const cachedMessages = getCachedMessages('session-1')

      expect(cachedMessages).toHaveLength(2)
      expect(cachedMessages[0].content).toBe('消息1')
      expect(cachedMessages[1].content).toBe('消息2')
    })
  })

  describe('消息状态更新', () => {
    it('应该更新消息状态', () => {
      const message = {
        id: 'msg-1',
        sessionId: 'session-1',
        role: 'user' as const,
        content: '测试消息',
        timestamp: new Date().toISOString(),
        status: 'pending' as const,
      }

      const session = {
        id: 'session-1',
        title: '测试会话',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [message],
        isActive: true,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([session]))

      // 使用service实例更新消息状态
      messageCacheService.updateMessageStatus('session-1', 'msg-1', 'sent')

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'data-agent-message-cache',
        expect.stringContaining('"status":"sent"')
      )
    })

    it('应该将已同步消息从队列中移除', () => {
      const message = {
        id: 'msg-1',
        sessionId: 'session-1',
        role: 'user' as const,
        content: '测试消息',
        timestamp: new Date().toISOString(),
        status: 'pending' as const,
      }

      const session = {
        id: 'session-1',
        title: '测试会话',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [message],
        isActive: true,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([session]))
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(['msg-1'])) // 同步队列

      messageCacheService.updateMessageStatus('session-1', 'msg-1', 'synced')

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'data-agent-sync-queue',
        '[]'
      )
    })
  })

  describe('删除操作', () => {
    it('应该删除消息', () => {
      const message1 = {
        id: 'msg-1',
        sessionId: 'session-1',
        role: 'user' as const,
        content: '消息1',
        timestamp: new Date().toISOString(),
        status: 'sent' as const,
      }

      const message2 = {
        id: 'msg-2',
        sessionId: 'session-1',
        role: 'assistant' as const,
        content: '消息2',
        timestamp: new Date().toISOString(),
        status: 'sent' as const,
      }

      const session = {
        id: 'session-1',
        title: '测试会话',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [message1, message2],
        isActive: true,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([session]))

      messageCacheService.deleteCachedMessage('session-1', 'msg-1')

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'data-agent-message-cache',
        expect.stringContaining('消息2')
      )
      expect(localStorageMock.setItem).not.toHaveBeenCalledWith(
        'data-agent-message-cache',
        expect.stringContaining('消息1')
      )
    })

    it('应该删除会话', () => {
      const session1 = {
        id: 'session-1',
        title: '会话1',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [],
        isActive: true,
        isDirty: false,
      }

      const session2 = {
        id: 'session-2',
        title: '会话2',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [],
        isActive: false,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([session1, session2]))

      messageCacheService.deleteCachedSession('session-1')

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'data-agent-message-cache',
        expect.stringContaining('会话2')
      )
      expect(localStorageMock.setItem).not.toHaveBeenCalledWith(
        'data-agent-message-cache',
        expect.stringContaining('会话1')
      )
    })
  })

  describe('同步功能', () => {
    it('应该获取待同步消息', () => {
      const message = {
        id: 'msg-1',
        sessionId: 'session-1',
        role: 'user' as const,
        content: '待同步消息',
        timestamp: new Date().toISOString(),
        status: 'pending' as const,
      }

      const session = {
        id: 'session-1',
        title: '测试会话',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [message],
        isActive: true,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([session]))
      localStorageMock.getItem.mockReturnValue(JSON.stringify(['msg-1']))

      const pendingMessages = messageCacheService.getPendingMessages()

      expect(pendingMessages).toHaveLength(1)
      expect(pendingMessages[0].message.content).toBe('待同步消息')
      expect(pendingMessages[0].sessionId).toBe('session-1')
    })

    it('应该成功同步消息', async () => {
      const message = {
        id: 'msg-1',
        sessionId: 'session-1',
        role: 'user' as const,
        content: '待同步消息',
        timestamp: new Date().toISOString(),
        status: 'pending' as const,
      }

      const session = {
        id: 'session-1',
        title: '测试会话',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [message],
        isActive: true,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([session]))
      localStorageMock.getItem.mockReturnValue(JSON.stringify(['msg-1']))

      const mockSendMessage = jest.fn().mockResolvedValue(undefined)

      const result = await syncMessages(mockSendMessage)

      expect(result.success).toBe(true)
      expect(result.syncedMessages).toContain('msg-1')
      expect(result.failedMessages).toHaveLength(0)
    })

    it('应该处理同步失败', async () => {
      const message = {
        id: 'msg-1',
        sessionId: 'session-1',
        role: 'user' as const,
        content: '待同步消息',
        timestamp: new Date().toISOString(),
        status: 'pending' as const,
      }

      const session = {
        id: 'session-1',
        title: '测试会话',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [message],
        isActive: true,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([session]))
      localStorageMock.getItem.mockReturnValue(JSON.stringify(['msg-1']))

      const mockSendMessage = jest.fn().mockRejectedValue(new Error('Network error'))

      const result = await syncMessages(mockSendMessage)

      expect(result.success).toBe(false)
      expect(result.syncedMessages).toHaveLength(0)
      expect(result.failedMessages).toContain('msg-1')
      expect(result.errorMessage).toBeDefined()
    })
  })

  describe('缓存统计', () => {
    it('应该返回正确的统计信息', () => {
      const session1 = {
        id: 'session-1',
        title: '会话1',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [
          {
            id: 'msg-1',
            sessionId: 'session-1',
            role: 'user' as const,
            content: '消息1',
            timestamp: new Date().toISOString(),
            status: 'sent' as const,
          },
          {
            id: 'msg-2',
            sessionId: 'session-1',
            role: 'user' as const,
            content: '消息2',
            timestamp: new Date().toISOString(),
            status: 'pending' as const,
          },
        ],
        isActive: true,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([session1]))
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(['msg-2']))
      localStorageMock.getItem.mockReturnValueOnce('500')

      const stats = messageCacheService.getCacheStats()

      expect(stats.totalSessions).toBe(1)
      expect(stats.totalMessages).toBe(2)
      expect(stats.pendingMessages).toBe(1)
      expect(stats.failedMessages).toBe(0)
      expect(stats.cacheSize).toBe(503) // 500 + 3
    })
  })

  describe('错误处理', () => {
    it('应该处理localStorage错误', () => {
      localStorageMock.getItem.mockImplementation(() => {
        throw new Error('Storage error')
      })

      expect(() => {
        getCachedSessions()
      }).not.toThrow()

      expect(() => {
        getCachedSession('test')
      }).not.toThrow()

      expect(() => {
        cacheSession({} as any)
      }).not.toThrow()
    })

    it('应该处理无效的缓存数据', () => {
      localStorageMock.getItem.mockReturnValue('invalid json')

      expect(() => {
        getCachedSessions()
      }).not.toThrow()

      expect(getCachedSessions()).toEqual([])
    })
  })

  describe('清理功能', () => {
    it('应该清空所有缓存', () => {
      const session = {
        id: 'session-1',
        title: '测试会话',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messages: [],
        isActive: true,
        isDirty: false,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify([session]))

      messageCacheService.clearCache()

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('data-agent-message-cache')
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('data-agent-sync-queue')
    })
  })
})