/**
 * API集成测试
 * 测试前后端API的实际集成
 */

import { renderHook, act } from '@testing-library/react'
import { useChatStore } from '@/store/chatStore'

// Mock实际的网络请求，但测试完整的数据流
jest.mock('@/lib/api-client', () => ({
  api: {
    chat: {
      sendQuery: jest.fn(),
      getSessions: jest.fn(),
      createSession: jest.fn(),
      deleteSession: jest.fn(),
      getSession: jest.fn(),
    },
  },
}))

import { api } from '@/lib/api-client'
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

describe('API集成测试', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    localStorageMock.getItem.mockReturnValue(null)
  })

  describe('聊天流程集成', () => {
    it('应该完成完整的聊天流程', async () => {
      const { result } = renderHook(() => useChatStore())

      // 1. 创建会话
      mockApi.chat.createSession.mockResolvedValue({
        status: 'success',
        data: {
          id: 'session-123',
          title: '新会话',
          created_at: '2024-01-01T00:00:00Z',
          message_count: 0,
        },
      })

      await act(async () => {
        const sessionId = await result.current.createSession('测试聊天')
        expect(sessionId).toBeDefined()
      })

      expect(mockApi.chat.createSession).toHaveBeenCalledWith('测试聊天')

      // 2. 发送消息
      const mockAiResponse = {
        status: 'success' as const,
        data: {
          answer: '这是AI的回答',
          sources: ['database1', 'table1'],
          reasoning: '基于用户查询，我分析了相关数据',
          confidence: 0.85,
          execution_time: 1.2,
        },
      }

      mockApi.chat.sendQuery.mockResolvedValue(mockAiResponse)

      await act(async () => {
        await result.current.sendMessage('分析最近的销售数据')
      })

      // 验证API调用
      expect(mockApi.chat.sendQuery).toHaveBeenCalledWith({
        query: '分析最近的销售数据',
        session_id: result.current.sessions[0].id,
      })

      // 验证状态更新
      expect(result.current.currentSession?.messages).toHaveLength(2)
      expect(result.current.currentSession?.messages[0].role).toBe('user')
      expect(result.current.currentSession?.messages[0].content).toBe('分析最近的销售数据')
      expect(result.current.currentSession?.messages[1].role).toBe('assistant')
      expect(result.current.currentSession?.messages[1].content).toBe('这是AI的回答')
      expect(result.current.currentSession?.messages[1].metadata?.sources).toEqual(['database1', 'table1'])
      expect(result.current.currentSession?.messages[1].metadata?.confidence).toBe(0.85)

      // 验证统计信息更新
      expect(result.current.stats.totalMessages).toBe(2)
    })

    it('应该处理API错误并显示系统消息', async () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话
      await act(async () => {
        await result.current.createSession('测试会话')
      })

      // Mock API错误
      mockApi.chat.sendQuery.mockResolvedValue({
        status: 'error',
        error: '数据库连接失败',
      })

      // 发送消息
      await act(async () => {
        await result.current.sendMessage('测试消息')
      })

      // 验证错误处理
      expect(result.current.currentSession?.messages).toHaveLength(2)
      expect(result.current.currentSession?.messages[0].role).toBe('user')
      expect(result.current.currentSession?.messages[1].role).toBe('system')
      expect(result.current.currentSession?.messages[1].content).toContain('发送消息失败')
      expect(result.current.error).toBe('发送消息失败')
    })

    it('应该处理网络错误', async () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话
      await act(async () => {
        await result.current.createSession('测试会话')
      })

      // Mock网络错误
      mockApi.chat.sendQuery.mockRejectedValue(new Error('Network error'))

      // 发送消息
      await act(async () => {
        await result.current.sendMessage('测试消息')
      })

      // 验证错误处理
      expect(result.current.currentSession?.messages).toHaveLength(2)
      expect(result.current.currentSession?.messages[1].role).toBe('system')
      expect(result.current.currentSession?.messages[1].content).toContain('发送消息失败')
      expect(result.current.error).toBe('发送消息失败')
    })
  })

  describe('会话管理集成', () => {
    it('应该加载和管理多个会话', async () => {
      const { result } = renderHook(() => useChatStore())

      // Mock获取会话列表
      const mockSessions = [
        {
          id: 'session-1',
          title: '数据分析',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T01:00:00Z',
          message_count: 5,
        },
        {
          id: 'session-2',
          title: '报告生成',
          created_at: '2024-01-02T00:00:00Z',
          updated_at: '2024-01-02T01:00:00Z',
          message_count: 3,
        },
      ]

      mockApi.chat.getSessions.mockResolvedValue({
        status: 'success',
        data: mockSessions,
      })

      // 创建多个本地会话
      await act(async () => {
        await result.current.createSession('本地会话1')
        await result.current.createSession('本地会话2')
      })

      expect(result.current.sessions).toHaveLength(2)
      expect(result.current.currentSession?.title).toBe('本地会话2')

      // 切换会话
      act(() => {
        result.current.switchSession(result.current.sessions[0].id)
      })

      expect(result.current.currentSession?.title).toBe('本地会话1')
      expect(result.current.sessions[0].isActive).toBe(true)
      expect(result.current.sessions[1].isActive).toBe(false)
    })

    it('应该删除会话并处理数据清理', async () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话并添加消息
      await act(async () => {
        await result.current.createSession('要删除的会话')
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

      expect(result.current.sessions).toHaveLength(1)
      expect(result.current.currentSession?.messages).toHaveLength(2)
      expect(result.current.stats.totalMessages).toBe(2)

      // Mock删除API
      mockApi.chat.deleteSession.mockResolvedValue({
        status: 'success',
      })

      const sessionId = result.current.sessions[0].id

      // 删除会话
      act(() => {
        result.current.deleteSession(sessionId)
      })

      expect(result.current.sessions).toHaveLength(0)
      expect(result.current.currentSession).toBeNull()
      expect(result.current.stats.totalMessages).toBe(0)
      expect(mockApi.chat.deleteSession).toHaveBeenCalledWith(sessionId)
    })
  })

  describe('状态持久化集成', () => {
    it('应该保存和恢复会话状态', async () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话和消息
      await act(async () => {
        await result.current.createSession('持久化测试')
        result.current.addMessage({
          role: 'user',
          content: '测试消息',
          timestamp: new Date(),
          status: 'sent',
        })
      })

      // 验证保存到localStorage
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'data-agent-chat-store',
        expect.stringContaining('持久化测试')
      )

      // Mock从localStorage加载数据
      const storedData = {
        sessions: result.current.sessions,
        currentSession: result.current.currentSession,
        stats: result.current.stats,
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify(storedData))

      // 创建新的hook实例来测试加载
      const { result: newResult } = renderHook(() => useChatStore())

      expect(newResult.current.sessions).toHaveLength(1)
      expect(newResult.current.currentSession?.title).toBe('持久化测试')
      expect(newResult.current.currentSession?.messages).toHaveLength(1)
      expect(newResult.current.stats.totalMessages).toBe(1)
    })

    it('应该处理localStorage加载错误', () => {
      localStorageMock.getItem.mockImplementation(() => {
        throw new Error('Storage access denied')
      })

      // 应该不抛出错误
      expect(() => {
        renderHook(() => useChatStore())
      }).not.toThrow()
    })
  })

  describe('并发操作集成', () => {
    it('应该处理并发的消息发送', async () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话
      await act(async () => {
        await result.current.createSession('并发测试')
      })

      // Mock API响应
      mockApi.chat.sendQuery.mockResolvedValue({
        status: 'success',
        data: {
          answer: '回复消息',
          sources: [],
          confidence: 0.9,
        },
      })

      // 尝试并发发送消息
      const promise1 = act(() => result.current.sendMessage('消息1'))
      const promise2 = act(() => result.current.sendMessage('消息2'))

      await Promise.all([promise1, promise2])

      // 验证只有一条消息被发送（因为加载状态阻止）
      expect(mockApi.chat.sendQuery).toHaveBeenCalledTimes(1)
      expect(result.current.currentSession?.messages).toHaveLength(2) // 用户消息 + AI回复
    })

    it('应该在加载时阻止新操作', async () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话
      await act(async () => {
        await result.current.createSession('加载测试')
      })

      // Mock延迟的API响应
      let resolveApi: (value: any) => void
      const apiPromise = new Promise(resolve => {
        resolveApi = resolve
      })
      mockApi.chat.sendQuery.mockReturnValue(apiPromise)

      // 开始发送消息
      const sendPromise = act(() => result.current.sendMessage('测试消息'))

      // 验证加载状态
      expect(result.current.isLoading).toBe(true)
      expect(result.current.isTyping).toBe(true)

      // 尝试发送另一条消息（应该被阻止）
      act(() => result.current.sendMessage('第二条消息'))

      // 完成API调用
      resolveApi({
        status: 'success',
        data: {
          answer: 'AI回复',
          sources: [],
          confidence: 0.9,
        },
      })

      await sendPromise

      // 验证状态
      expect(result.current.isLoading).toBe(false)
      expect(result.current.isTyping).toBe(false)
      expect(result.current.currentSession?.messages).toHaveLength(2) // 只有一组对话
    })
  })

  describe('错误恢复集成', () => {
    it('应该从API错误中恢复', async () => {
      const { result } = renderHook(() => useChatStore())

      // 创建会话
      await act(async () => {
        await result.current.createSession('错误恢复测试')
      })

      // 第一次API调用失败
      mockApi.chat.sendQuery.mockResolvedValueOnce({
        status: 'error',
        error: '临时网络错误',
      })

      await act(async () => {
        await result.current.sendMessage('第一次消息')
      })

      expect(result.current.currentSession?.messages).toHaveLength(2)
      expect(result.current.currentSession?.messages[1].role).toBe('system')
      expect(result.current.error).toBe('发送消息失败')

      // 清除错误状态
      act(() => {
        result.current.setError(null)
      })

      expect(result.current.error).toBeNull()

      // 第二次API调用成功
      mockApi.chat.sendQuery.mockResolvedValueOnce({
        status: 'success',
        data: {
          answer: '成功回复',
          sources: [],
          confidence: 0.9,
        },
      })

      await act(async () => {
        await result.current.sendMessage('第二次消息')
      })

      expect(result.current.currentSession?.messages).toHaveLength(4) // 2组对话
      expect(result.current.currentSession?.messages[3].role).toBe('assistant')
      expect(result.current.error).toBeNull()
    })
  })
})