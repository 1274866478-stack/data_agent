/**
 * 搜索服务测试
 */

import { searchSessions, getSearchSuggestions, getPopularKeywords, groupResultsBySession, SearchResult, SearchOptions } from '../searchService'
import type { ChatSession, ChatMessage } from '@/types/store/chat'

// 模拟测试数据
const mockSessions: ChatSession[] = [
  {
    id: 'session-1',
    title: '数据分析讨论',
    createdAt: new Date('2024-01-01'),
    updatedAt: new Date('2024-01-02'),
    messages: [
      {
        id: 'msg-1',
        role: 'user',
        content: '请帮我分析销售数据的趋势',
        timestamp: new Date('2024-01-01T10:00:00'),
        status: 'sent'
      },
      {
        id: 'msg-2',
        role: 'assistant',
        content: '根据销售数据分析，我们发现了一些有趣的趋势',
        timestamp: new Date('2024-01-01T10:01:00'),
        status: 'sent'
      },
      {
        id: 'msg-3',
        role: 'user',
        content: '能详细说明一下第一季度的情况吗？',
        timestamp: new Date('2024-01-01T10:02:00'),
        status: 'sent'
      }
    ],
    isActive: true
  },
  {
    id: 'session-2',
    title: '技术方案讨论',
    createdAt: new Date('2024-01-03'),
    updatedAt: new Date('2024-01-04'),
    messages: [
      {
        id: 'msg-4',
        role: 'user',
        content: '我们需要选择合适的数据库技术栈',
        timestamp: new Date('2024-01-03T14:00:00'),
        status: 'sent'
      },
      {
        id: 'msg-5',
        role: 'assistant',
        content: 'PostgreSQL是一个很好的选择，因为它支持复杂的查询',
        timestamp: new Date('2024-01-03T14:01:00'),
        status: 'sent'
      }
    ],
    isActive: false
  },
  {
    id: 'session-3',
    title: '产品功能规划',
    createdAt: new Date('2024-01-05'),
    updatedAt: new Date('2024-01-06'),
    messages: [
      {
        id: 'msg-6',
        role: 'user',
        content: '下一版本应该增加哪些新功能？',
        timestamp: new Date('2024-01-05T09:00:00'),
        status: 'sent'
      },
      {
        id: 'msg-7',
        role: 'assistant',
        content: '建议增加数据导出功能和更丰富的图表展示',
        timestamp: new Date('2024-01-05T09:01:00'),
        status: 'sent'
      }
    ],
    isActive: false
  }
]

describe('SearchService', () => {
  describe('searchSessions', () => {
    it('应该返回空的搜索结果当查询为空时', () => {
      const result = searchSessions(mockSessions, { query: '' })

      expect(result.results).toEqual([])
      expect(result.stats.totalResults).toBe(0)
      expect(result.stats.sessionResults).toBe(0)
      expect(result.stats.messageResults).toBe(0)
      expect(result.stats.searchTime).toBeGreaterThanOrEqual(0)
    })

    it('应该搜索会话标题', () => {
      const result = searchSessions(mockSessions, { query: '数据分析讨论', type: 'sessions' })

      expect(result.results.length).toBeGreaterThanOrEqual(1)
      const sessionResult = result.results.find(r => r.type === 'session')
      expect(sessionResult).toBeDefined()
      expect(sessionResult?.sessionId).toBe('session-1')
      expect(sessionResult?.content).toBe('数据分析讨论')
      expect(result.stats.sessionResults).toBeGreaterThanOrEqual(1)
    })

    it('应该搜索消息内容', () => {
      const result = searchSessions(mockSessions, { query: '请帮我分析销售数据的趋势', type: 'messages' })

      expect(result.results.length).toBeGreaterThanOrEqual(1)
      const messageResult = result.results.find(r => r.content === '请帮我分析销售数据的趋势')
      expect(messageResult).toBeDefined()
      expect(messageResult?.type).toBe('message')
      expect(messageResult?.sessionId).toBe('session-1')
      expect(result.stats.messageResults).toBeGreaterThanOrEqual(1)
    })

    it('应该同时搜索会话和消息', () => {
      const result = searchSessions(mockSessions, { query: '数据' })

      expect(result.results.length).toBeGreaterThan(1)
      expect(result.results.some(r => r.type === 'session')).toBe(true)
      expect(result.results.some(r => r.type === 'message')).toBe(true)
    })

    it('应该支持模糊搜索', () => {
      const result = searchSessions(mockSessions, {
        query: 'shujuku', // 模拟"数据库"的拼音
        fuzzySearch: true
      })

      expect(result.results.length).toBeGreaterThan(0)
    })

    it('应该按相关性得分排序', () => {
      const result = searchSessions(mockSessions, { query: '数据库' })

      // 数据库技术栈讨论应该排在前面
      expect(result.results[0].sessionId).toBe('session-2')
      expect(result.results[0].score).toBeGreaterThan(result.results[1]?.score || 0)
    })

    it('应该支持按类型过滤', () => {
      const sessionResult = searchSessions(mockSessions, { query: '数据', type: 'sessions' })
      const messageResult = searchSessions(mockSessions, { query: '数据', type: 'messages' })

      expect(sessionResult.results.every(r => r.type === 'session')).toBe(true)
      expect(messageResult.results.every(r => r.type === 'message')).toBe(true)
    })

    it('应该支持按会话ID过滤', () => {
      const result = searchSessions(mockSessions, {
        query: '数据',
        sessionId: 'session-1'
      })

      expect(result.results.every(r => r.sessionId === 'session-1')).toBe(true)
    })

    it('应该限制结果数量', () => {
      const result = searchSessions(mockSessions, {
        query: '数据',
        limit: 2
      })

      expect(result.results.length).toBeLessThanOrEqual(2)
    })

    it('应该包含搜索高亮', () => {
      const result = searchSessions(mockSessions, { query: '数据' })

      result.results.forEach(result => {
        expect(result.highlights.length).toBeGreaterThan(0)
        result.highlights.forEach(highlight => {
          expect(typeof highlight).toBe('string')
          expect(highlight.length).toBeGreaterThan(0)
        })
      })
    })

    it('应该包含上下文信息', () => {
      const result = searchSessions(mockSessions, {
        query: '能详细说明',
        includeContext: true
      })

      const messageResult = result.results.find(r => r.type === 'message')
      expect(messageResult?.context).toBeDefined()
      expect(messageResult?.context?.beforeMessage).toBeTruthy()
      // afterMessage可能为undefined，因为这是最后一条消息
    })
  })

  describe('getSearchSuggestions', () => {
    it('应该返回空数组当查询太短时', () => {
      const suggestions = getSearchSuggestions(mockSessions, '数')
      expect(suggestions).toEqual([])
    })

    it('应该从会话标题中提取建议', () => {
      const suggestions = getSearchSuggestions(mockSessions, '数据')
      expect(suggestions.length).toBeGreaterThan(0)
      expect(suggestions.some(s => s.includes('数据'))).toBe(true)
    })

    it('应该从消息内容中提取建议', () => {
      const suggestions = getSearchSuggestions(mockSessions, '分析')
      expect(suggestions.length).toBeGreaterThan(0)
    })

    it('应该限制建议数量', () => {
      const suggestions = getSearchSuggestions(mockSessions, '数据', 2)
      expect(suggestions.length).toBeLessThanOrEqual(2)
    })

    it('应该去重建议', () => {
      const suggestions = getSearchSuggestions(mockSessions, '数据')
      const uniqueSuggestions = [...new Set(suggestions)]
      expect(suggestions).toEqual(uniqueSuggestions)
    })
  })

  describe('getPopularKeywords', () => {
    it('应该返回热门关键词', () => {
      const keywords = getPopularKeywords(mockSessions)

      expect(keywords.length).toBeGreaterThan(0)
      keywords.forEach(keyword => {
        expect(keyword).toHaveProperty('keyword')
        expect(keyword).toHaveProperty('count')
        expect(typeof keyword.keyword).toBe('string')
        expect(typeof keyword.count).toBe('number')
        expect(keyword.count).toBeGreaterThan(0)
      })
    })

    it('应该按频率排序关键词', () => {
      const keywords = getPopularKeywords(mockSessions)

      for (let i = 1; i < keywords.length; i++) {
        expect(keywords[i-1].count).toBeGreaterThanOrEqual(keywords[i].count)
      }
    })

    it('应该过滤常见词', () => {
      const sessionsWithCommonWords: ChatSession[] = [
        {
          id: 'test',
          title: '的',
          createdAt: new Date(),
          updatedAt: new Date(),
          messages: [
            {
              id: 'msg',
              role: 'user',
              content: '是 在 有 和 我 你 他 这个',
              timestamp: new Date(),
              status: 'sent'
            }
          ],
          isActive: true
        }
      ]

      const keywords = getPopularKeywords(sessionsWithCommonWords)
      expect(keywords.length).toBe(0)
    })

    it('应该限制关键词长度', () => {
      const keywords = getPopularKeywords(mockSessions)

      keywords.forEach(keyword => {
        expect(keyword.keyword.length).toBeGreaterThan(2)
      })
    })

    it('应该限制返回数量', () => {
      const keywords = getPopularKeywords(mockSessions, 3)
      expect(keywords.length).toBeLessThanOrEqual(3)
    })
  })

  describe('groupResultsBySession', () => {
    it('应该按会话分组结果', () => {
      const results: SearchResult[] = [
        {
          type: 'message',
          sessionId: 'session-1',
          id: 'msg-1',
          content: '消息1',
          timestamp: new Date(),
          score: 80,
          highlights: ['消息1']
        },
        {
          type: 'session',
          sessionId: 'session-2',
          id: 'session-2',
          content: '会话2',
          timestamp: new Date(),
          score: 90,
          highlights: ['会话2']
        },
        {
          type: 'message',
          sessionId: 'session-1',
          id: 'msg-2',
          content: '消息2',
          timestamp: new Date(),
          score: 70,
          highlights: ['消息2']
        }
      ]

      const grouped = groupResultsBySession(results)

      expect(Object.keys(grouped)).toHaveLength(2)
      expect(grouped['session-1']).toHaveLength(2)
      expect(grouped['session-2']).toHaveLength(1)
    })

    it('应该在每个会话内按时间排序', () => {
      const oldDate = new Date('2024-01-01')
      const newDate = new Date('2024-01-02')

      const results: SearchResult[] = [
        {
          type: 'message',
          sessionId: 'session-1',
          id: 'msg-1',
          content: '旧消息',
          timestamp: oldDate,
          score: 80,
          highlights: ['旧消息']
        },
        {
          type: 'message',
          sessionId: 'session-1',
          id: 'msg-2',
          content: '新消息',
          timestamp: newDate,
          score: 70,
          highlights: ['新消息']
        }
      ]

      const grouped = groupResultsBySession(results)
      const sessionResults = grouped['session-1']

      expect(sessionResults[0].timestamp.getTime()).toBeGreaterThan(sessionResults[1].timestamp.getTime())
    })

    it('应该处理空结果', () => {
      const grouped = groupResultsBySession([])
      expect(Object.keys(grouped)).toHaveLength(0)
    })
  })

  describe('性能测试', () => {
    it('应该在合理时间内完成搜索', () => {
      const startTime = Date.now()

      searchSessions(mockSessions, { query: '数据' })

      const endTime = Date.now()
      const duration = endTime - startTime

      expect(duration).toBeLessThan(100) // 应该在100ms内完成
    })

    it('应该处理大量数据', () => {
      // 生成大量测试数据
      const largeSessions: ChatSession[] = []
      for (let i = 0; i < 100; i++) {
        largeSessions.push({
          id: `session-${i}`,
          title: `会话 ${i}`,
          createdAt: new Date(),
          updatedAt: new Date(),
          messages: [
            {
              id: `msg-${i}`,
              role: 'user',
              content: `消息内容 ${i}`,
              timestamp: new Date(),
              status: 'sent'
            }
          ],
          isActive: i === 0
        })
      }

      const result = searchSessions(largeSessions, { query: '消息' })

      expect(result.results.length).toBeGreaterThan(0)
      expect(result.stats.searchTime).toBeLessThan(500) // 应该在500ms内完成
    })
  })

  describe('边界情况测试', () => {
    it('应该处理特殊字符搜索', () => {
      const result = searchSessions(mockSessions, { query: '!@#$%^&*()' })
      expect(result.results).toEqual([])
    })

    it('应该处理Unicode字符搜索', () => {
      const result = searchSessions(mockSessions, { query: '📊' })
      expect(result.results).toEqual([])
    })

    it('应该处理超长查询', () => {
      const longQuery = 'a'.repeat(1000)
      const result = searchSessions(mockSessions, { query: longQuery })
      expect(result.results).toEqual([])
    })

    it('应该处理空会话列表', () => {
      const result = searchSessions([], { query: '测试' })
      expect(result.results).toEqual([])
      expect(result.stats.totalResults).toBe(0)
    })

    it('应该处理没有消息的会话', () => {
      const emptySession: ChatSession = {
        id: 'empty',
        title: '空会话',
        createdAt: new Date(),
        updatedAt: new Date(),
        messages: [],
        isActive: false
      }

      const result = searchSessions([emptySession], { query: '测试' })
      expect(result.results).toEqual([])
    })
  })
})
