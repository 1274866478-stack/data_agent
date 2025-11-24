/**
 * ChatStore状态管理测试
 */

import { act, renderHook } from '@testing-library/react'
import { useChatStore, ChatMessage, ChatSession } from '../chatStore'
import { api } from '@/lib/api-client'

// Mock API客户端
jest.mock('@/lib/api-client', () => ({
  api: {
    chat: {
      sendQuery: jest.fn(),
    },
  },
}))

const mockApi = api as jest.Mocked<typeof api>

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

describe('chatStore', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    localStorageMock.getItem.mockReturnValue(null)

    // 重置store状态
    useChatStore.getState().sessions = []
    useChatStore.getState().currentSession = null
    useChatStore.getState().isLoading = false
    useChatStore.getState().isTyping = false
    useChatStore.getState().error = null
    useChatStore.getState().stats = {
      totalMessages: 0,
      totalSessions: 0,
      averageResponseTime: 0,
    }
  })

  describe('会话管理', () => {
    it('应该创建新会话', async () => {
      const { result } = renderHook(() => useChatStore())

      await act(async () => {
        const sessionId = await result.current.createSession('测试会话')
        expect(sessionId).toBeDefined()
        expect(typeof sessionId).toBe('string')
      })

      expect(result.current.sessions).toHaveLength(1)
      expect(result.current.sessions[0].title).toBe('测试会话')
      expect(result.current.currentSession).not.toBeNull()
      expect(result.current.currentSession?.title).toBe('测试会话')
      expect(result.current.stats.totalSessions).toBe(1)
    })

    it('应该使用默认标题创建会话', async () => {
      const { result } = renderHook(() => useChatStore())

      await act(async () => {
        await result.current.createSession()
      })

      expect(result.current.sessions[0].title).toBe('新会话')
    })

    it('应该切换会话', () => {
      const { result } = renderHook(() => useChatStore())

      // 先创建两个会话
      act(() => {
        result.current.createSession('会话1')
        result.current.createSession('会话2')
      })

      expect(result.current.currentSession?.title).toBe('会话2')

      // 切换到第一个会话
      act(() => {
        result.current.switchSession(result.current.sessions[0].id)
      })

      expect(result.current.currentSession?.title).toBe('会话1')
      expect(result.current.sessions[0].isActive).toBe(true)
      expect(result.current.sessions[1].isActive).toBe(false)
    })

    it('应该删除会话', () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话
      act(() => {
        result.current.createSession('会话1')
        result.current.createSession('会话2')
      })

      expect(result.current.sessions).toHaveLength(2)

      // 删除第一个会话
      act(() => {
        result.current.deleteSession(result.current.sessions[0].id)
      })

      expect(result.current.sessions).toHaveLength(1)
      expect(result.current.sessions[0].title).toBe('会话2')
      expect(result.current.stats.totalSessions).toBe(1)
    })

    it('应该更新会话标题', () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话
      act(() => {
        result.current.createSession('原标题')
      })

      // 更新标题
      act(() => {
        result.current.updateSessionTitle(
          result.current.sessions[0].id,
          '新标题'
        )
      })

      expect(result.current.sessions[0].title).toBe('新标题')
      expect(result.current.currentSession?.title).toBe('新标题')
    })

    it('删除最后一个会话时应该设置currentSession为null', () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话
      act(() => {
        result.current.createSession('唯一会话')
      })

      expect(result.current.currentSession).not.toBeNull()

      // 删除会话
      act(() => {
        result.current.deleteSession(result.current.sessions[0].id)
      })

      expect(result.current.sessions).toHaveLength(0)
      expect(result.current.currentSession).toBeNull()
    })
  })

  describe('消息管理', () => {
    it('应该添加消息到当前会话', () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话
      act(() => {
        result.current.createSession('测试会话')
      })

      const message: Omit<ChatMessage, 'id'> = {
        role: 'user',
        content: '测试消息',
        timestamp: new Date(),
        status: 'sent',
      }

      // 添加消息
      act(() => {
        result.current.addMessage(message)
      })

      expect(result.current.currentSession?.messages).toHaveLength(1)
      expect(result.current.currentSession?.messages[0].content).toBe('测试消息')
      expect(result.current.stats.totalMessages).toBe(1)
    })

    it('应该自动生成会话标题（使用第一条用户消息）', () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话
      act(() => {
        result.current.createSession()
      })

      const longMessage = '这是一个非常长的用户消息，应该被截断作为会话标题使用'
      const message: Omit<ChatMessage, 'id'> = {
        role: 'user',
        content: longMessage,
        timestamp: new Date(),
        status: 'sent',
      }

      // 添加消息
      act(() => {
        result.current.addMessage(message)
      })

      expect(result.current.currentSession?.title).toBe(longMessage.substring(0, 30) + '...')
    })

    it('应该更新消息', () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话并添加消息
      act(() => {
        result.current.createSession('测试会话')
        result.current.addMessage({
          role: 'user',
          content: '原消息',
          timestamp: new Date(),
          status: 'sending',
        })
      })

      const messageId = result.current.currentSession!.messages[0].id

      // 更新消息状态
      act(() => {
        result.current.updateMessage(messageId, {
          status: 'sent',
          content: '更新后的消息',
        })
      })

      expect(result.current.currentSession?.messages[0].status).toBe('sent')
      expect(result.current.currentSession?.messages[0].content).toBe('更新后的消息')
    })

    it('应该删除消息', () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话并添加消息
      act(() => {
        result.current.createSession('测试会话')
        result.current.addMessage({
          role: 'user',
          content: '要删除的消息',
          timestamp: new Date(),
          status: 'sent',
        })
      })

      expect(result.current.currentSession?.messages).toHaveLength(1)
      expect(result.current.stats.totalMessages).toBe(1)

      const messageId = result.current.currentSession!.messages[0].id

      // 删除消息
      act(() => {
        result.current.deleteMessage(messageId)
      })

      expect(result.current.currentSession?.messages).toHaveLength(0)
      expect(result.current.stats.totalMessages).toBe(0)
    })

    it('应该清空会话历史', () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话并添加多条消息
      act(() => {
        result.current.createSession('测试会话')
        result.current.addMessage({
          role: 'user',
          content: '消息1',
          timestamp: new Date(),
          status: 'sent',
        })
        result.current.addMessage({
          role: 'assistant',
          content: '消息2',
          timestamp: new Date(),
          status: 'sent',
        })
      })

      expect(result.current.currentSession?.messages).toHaveLength(2)

      // 清空历史
      act(() => {
        result.current.clearHistory(result.current.sessions[0].id)
      })

      expect(result.current.currentSession?.messages).toHaveLength(0)
    })
  })

  describe('发送消息', () => {
    it('应该成功发送消息并接收响应', async () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话
      await act(async () => {
        await result.current.createSession('测试会话')
      })

      // Mock API响应
      const mockResponse = {
        status: 'success' as const,
        data: {
          answer: '这是AI的回答',
          sources: ['数据源1', '数据源2'],
          reasoning: '推理过程',
          confidence: 0.9,
        },
      }
      mockApi.chat.sendQuery.mockResolvedValue(mockResponse)

      // 发送消息
      await act(async () => {
        await result.current.sendMessage('用户问题')
      })

      expect(result.current.currentSession?.messages).toHaveLength(2)
      expect(result.current.currentSession?.messages[0].role).toBe('user')
      expect(result.current.currentSession?.messages[0].content).toBe('用户问题')
      expect(result.current.currentSession?.messages[1].role).toBe('assistant')
      expect(result.current.currentSession?.messages[1].content).toBe('这是AI的回答')
      expect(result.current.currentSession?.messages[1].metadata?.sources).toEqual(['数据源1', '数据源2'])
      expect(result.current.stats.totalMessages).toBe(2)
    })

    it('应该处理发送消息错误', async () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话
      await act(async () => {
        await result.current.createSession('测试会话')
      })

      // Mock API错误
      mockApi.chat.sendQuery.mockResolvedValue({
        status: 'error' as const,
        error: '网络错误',
      })

      // 发送消息
      await act(async () => {
        await result.current.sendMessage('用户问题')
      })

      expect(result.current.currentSession?.messages).toHaveLength(2)
      expect(result.current.currentSession?.messages[0].role).toBe('user')
      expect(result.current.currentSession?.messages[1].role).toBe('system')
      expect(result.current.currentSession?.messages[1].content).toContain('发送消息失败')
      expect(result.current.error).toBe('发送消息失败')
    })

    it('应该在没有当前会话时不发送消息', async () => {
      const { result } = renderHook(() => useChatStore())

      // Mock API
      mockApi.chat.sendQuery.mockResolvedValue({
        status: 'success' as const,
        data: { answer: '回答' },
      })

      // 发送消息（没有会话）
      await act(async () => {
        await result.current.sendMessage('用户问题')
      })

      expect(mockApi.chat.sendQuery).not.toHaveBeenCalled()
      expect(result.current.currentSession).toBeNull()
    })

    it('应该在加载中时不发送消息', async () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话
      await act(async () => {
        await result.current.createSession('测试会话')
      })

      // 设置加载状态
      act(() => {
        result.current.setLoading(true)
      })

      // Mock API
      mockApi.chat.sendQuery.mockResolvedValue({
        status: 'success' as const,
        data: { answer: '回答' },
      })

      // 发送消息
      await act(async () => {
        await result.current.sendMessage('用户问题')
      })

      expect(mockApi.chat.sendQuery).not.toHaveBeenCalled()
    })
  })

  describe('状态管理', () => {
    it('应该设置加载状态', () => {
      const { result } = renderHook(() => useChatStore())

      expect(result.current.isLoading).toBe(false)

      act(() => {
        result.current.setLoading(true)
      })

      expect(result.current.isLoading).toBe(true)

      act(() => {
        result.current.setLoading(false)
      })

      expect(result.current.isLoading).toBe(false)
    })

    it('应该设置输入状态', () => {
      const { result } = renderHook(() => useChatStore())

      expect(result.current.isTyping).toBe(false)

      act(() => {
        result.current.setTyping(true)
      })

      expect(result.current.isTyping).toBe(true)

      act(() => {
        result.current.setTyping(false)
      })

      expect(result.current.isTyping).toBe(false)
    })

    it('应该设置错误状态', () => {
      const { result } = renderHook(() => useChatStore())

      expect(result.current.error).toBeNull()

      act(() => {
        result.current.setError('测试错误')
      })

      expect(result.current.error).toBe('测试错误')

      act(() => {
        result.current.setError(null)
      })

      expect(result.current.error).toBeNull()
    })
  })

  describe('本地存储', () => {
    it('应该保存数据到本地存储', () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话和消息
      act(() => {
        result.current.createSession('测试会话')
        result.current.addMessage({
          role: 'user',
          content: '测试消息',
          timestamp: new Date(),
          status: 'sent',
        })
      })

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'data-agent-chat-store',
        expect.stringContaining('测试会话')
      )
    })

    it('应该从本地存储加载数据', () => {
      const mockStoredData = {
        sessions: [
          {
            id: 'session-1',
            title: '存储的会话',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            messages: [
              {
                id: 'msg-1',
                role: 'user',
                content: '存储的消息',
                timestamp: new Date().toISOString(),
                status: 'sent',
              },
            ],
            isActive: true,
          },
        ],
        currentSession: {
          id: 'session-1',
          title: '存储的会话',
        },
        stats: {
          totalMessages: 1,
          totalSessions: 1,
          averageResponseTime: 0,
        },
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify(mockStoredData))

      // 重新创建hook以触发加载
      const { result } = renderHook(() => useChatStore())

      expect(result.current.sessions).toHaveLength(1)
      expect(result.current.sessions[0].title).toBe('存储的会话')
      expect(result.current.currentSession?.title).toBe('存储的会话')
      expect(result.current.stats.totalMessages).toBe(1)
    })

    it('应该处理本地存储加载错误', () => {
      localStorageMock.getItem.mockImplementation(() => {
        throw new Error('Storage error')
      })

      // 应该不抛出错误
      expect(() => {
        renderHook(() => useChatStore())
      }).not.toThrow()
    })

    it('应该处理本地存储保存错误', () => {
      localStorageMock.setItem.mockImplementation(() => {
        throw new Error('Storage error')
      })

      const { result } = renderHook(() => useChatStore())

      // 应该不抛出错误
      expect(() => {
        act(() => {
          result.current.createSession('测试会话')
        })
      }).not.toThrow()
    })
  })

  describe('统计信息', () => {
    it('应该正确更新消息统计', () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话
      act(() => {
        result.current.createSession('测试会话')
      })

      expect(result.current.stats.totalMessages).toBe(0)

      // 添加消息
      act(() => {
        result.current.addMessage({
          role: 'user',
          content: '消息1',
          timestamp: new Date(),
          status: 'sent',
        })
      })

      expect(result.current.stats.totalMessages).toBe(1)

      // 添加更多消息
      act(() => {
        result.current.addMessage({
          role: 'assistant',
          content: '消息2',
          timestamp: new Date(),
          status: 'sent',
        })
      })

      expect(result.current.stats.totalMessages).toBe(2)

      // 删除消息
      const messageId = result.current.currentSession!.messages[0].id
      act(() => {
        result.current.deleteMessage(messageId)
      })

      expect(result.current.stats.totalMessages).toBe(1)
    })

    it('应该正确更新会话统计', () => {
      const { result } = renderHook(() => useChatStore())

      expect(result.current.stats.totalSessions).toBe(0)

      // 创建会话
      act(() => {
        result.current.createSession('会话1')
      })

      expect(result.current.stats.totalSessions).toBe(1)

      // 创建更多会话
      act(() => {
        result.current.createSession('会话2')
      })

      expect(result.current.stats.totalSessions).toBe(2)

      // 删除会话
      act(() => {
        result.current.deleteSession(result.current.sessions[0].id)
      })

      expect(result.current.stats.totalSessions).toBe(1)
    })
  })
})