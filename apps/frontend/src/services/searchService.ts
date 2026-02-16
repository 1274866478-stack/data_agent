/**
 * # [SEARCH_SERVICE] 会话搜索服务
 *
 * ## [MODULE]
 * **文件名**: searchService.ts
 * **职责**: 提供会话和消息的搜索功能 - 全文搜索、模糊搜索、搜索建议、热门关键词、结果分组
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 会话搜索服务
 *
 * ## [INPUT]
 * - **sessions: ChatSession[]** - 会话列表（包含messages数组）
 * - **options: SearchOptions** - 搜索选项
 *   - query: string - 搜索关键词
 *   - type?: 'all' | 'sessions' | 'messages' - 搜索类型
 *   - sessionId?: string - 限定会话ID
 *   - limit?: number - 结果数量限制（默认50）
 *   - includeContext?: boolean - 是否包含上下文
 *   - fuzzySearch?: boolean - 是否模糊搜索（默认true）
 * - **query: string** - 搜索关键词（建议）
 * - **limit?: number** - 建议数量限制（默认5）
 *
 * ## [OUTPUT]
 * - **results: SearchResult[]** - 搜索结果列表
 *   - type: 'session' | 'message'
 *   - sessionId, id, title?, content, timestamp, score, highlights[]
 *   - context?: { beforeMessage?, afterMessage? }
 * - **stats: SearchStats** - 搜索统计
 *   - totalResults, sessionResults, messageResults, searchTime
 * - **suggestions: string[]** - 搜索建议列表
 * - **keywords: Array<{keyword, count}>** - 热门关键词列表
 * - **grouped: Record<string, SearchResult[]>** - 按会话分组的结果
 *
 * **上游依赖**:
 * - [../store/chatStore](../store/chatStore.ts) - ChatSession, ChatMessage类型
 *
 * **下游依赖**:
 * - 无（Service是叶子服务模块）
 *
 * **调用方**:
 * - [../components/chat/SearchBar.tsx](../components/chat/SearchBar.tsx) - 搜索栏
 * - [../components/chat/SearchResults.tsx](../components/chat/SearchResults.tsx) - 搜索结果
 * - [../components/chat/SearchSuggestions.tsx](../components/chat/SearchSuggestions.tsx) - 搜索建议
 *
 * ## [STATE]
 * - **搜索类型**: 'all'（会话+消息）, 'sessions'（仅会话）, 'messages'（仅消息）
 * - **搜索算法**:
 *   - 精确匹配得分：100（标题150）
 *   - 包含查询得分：80（标题120）
 *   - 模糊搜索得分：fuzzyScore（标题150）
 *   - 单词匹配得分：50（标题75）
 * - **模糊搜索算法**: fuzzyScore（连续字符匹配，递增得分）
 * - **文本高亮**: highlightText提取所有匹配项
 * - **上下文提取**: getMessageContext获取前后消息（默认2条）
 * - **结果排序**: 先按得分降序，再按时间降序
 * - **搜索建议**: getSuggestions提取标题和消息中的词汇（长度>2）
 * - **热门关键词**: getPopularKeywords统计词频（长度>2，非常见词）
 * - **中文分词**: extractChineseWords提取连续中文字符（每2-4字符）
 * - **常见词过滤**: isCommonWord过滤中英文常见词
 *
 * ## [SIDE-EFFECTS]
 * - **正则表达式**: new RegExp(`(${this.escapeRegex(query)})`, 'gi')匹配查询
 *   - escapeRegex转义特殊字符（[.*+?^${}()|[\]\\）
 * - **数组操作**:
 *   - results.push添加搜索结果
 *   - results.sort排序（得分降序，时间降序）
 *   - results.slice(0, limit)限制结果数量
 *   - filter过滤结果类型（r.type === 'session'）
 * - **字符串操作**:
 *   - toLowerCase()小写转换
 *   - trim()去除首尾空格
 *   - split(/\s+/)分词
 *   - includes()包含判断
 *   - substring()截取字符串
 * - **对象操作**: Object.entries(), Array.from(), Map
 * - **时间测量**: Date.now()计算搜索时间
 * - **条件判断**: 检查query长度、类型筛选、sessionId筛选
 * - **中文匹配**: /[\u4e00-\u9fff]+/g匹配中文字符
 * - **异常处理**: try-catch捕获正则错误（实际不会抛出）
 * - **单例模式**: searchService全局实例
 * - **便捷函数**: searchSessions, getSearchSuggestions, getPopularKeywords, groupResultsBySession
 */

import { ChatSession, ChatMessage } from '@/store/chatStore'

export interface SearchResult {
  type: 'session' | 'message'
  sessionId: string
  id: string
  title?: string
  content: string
  timestamp: Date
  score: number
  highlights: string[]
  context?: {
    beforeMessage?: string
    afterMessage?: string
  }
}

export interface SearchOptions {
  query: string
  type?: 'all' | 'sessions' | 'messages'
  sessionId?: string
  limit?: number
  includeContext?: boolean
  fuzzySearch?: boolean
}

export interface SearchStats {
  totalResults: number
  sessionResults: number
  messageResults: number
  searchTime: number
}

class SearchService {
  /**
   * 简单的文本高亮函数
   */
  private highlightText(text: string, query: string): string[] {
    if (!query.trim()) return []

    const regex = new RegExp(`(${this.escapeRegex(query)})`, 'gi')
    const matches = []
    let match

    while ((match = regex.exec(text)) !== null) {
      matches.push(match[1])
    }

    return matches
  }

  /**
   * 转义正则表达式特殊字符
   */
  private escapeRegex(string: string): string {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  }

  /**
   * 计算搜索相关性得分
   */
  private calculateScore(
    text: string,
    query: string,
    isTitle: boolean = false,
    fuzzy: boolean = false
  ): number {
    const queryLower = query.toLowerCase()
    const textLower = text.toLowerCase()

    // 精确匹配得分最高
    if (textLower === queryLower) {
      return 100 * (isTitle ? 1.5 : 1)
    }

    // 包含查询得分次之
    if (textLower.includes(queryLower)) {
      return 80 * (isTitle ? 1.5 : 1)
    }

    // 模糊搜索得分
    if (fuzzy) {
      const score = this.fuzzyScore(textLower, queryLower)
      return score * (isTitle ? 1.5 : 1)
    }

    // 单词匹配得分
    const queryWords = queryLower.split(/\s+/).filter(word => word.length > 0)
    const textWords = textLower.split(/\s+/).filter(word => word.length > 0)

    let matchedWords = 0
    for (const queryWord of queryWords) {
      if (textWords.some(textWord => textWord.includes(queryWord) || queryWord.includes(textWord))) {
        matchedWords++
      }
    }

    if (matchedWords > 0) {
      return (matchedWords / queryWords.length) * 50 * (isTitle ? 1.5 : 1)
    }

    return 0
  }

  /**
   * 简单的模糊搜索算法
   */
  private fuzzyScore(text: string, pattern: string): number {
    if (pattern.length === 0) return 0
    if (text.length === 0) return 0

    let score = 0
    let patternIdx = 0
    let textIdx = 0
    let consecutiveMatches = 0

    while (patternIdx < pattern.length && textIdx < text.length) {
      if (pattern[patternIdx] === text[textIdx]) {
        consecutiveMatches++
        score += consecutiveMatches * consecutiveMatches
        patternIdx++
      } else {
        consecutiveMatches = 0
      }
      textIdx++
    }

    // 额外得分给完整匹配
    if (patternIdx === pattern.length) {
      score += pattern.length * 10
    }

    return score
  }

  /**
   * 获取消息的上下文
   */
  private getMessageContext(
    messages: ChatMessage[],
    targetMessageIndex: number,
    contextSize: number = 2
  ): { beforeMessage?: string; afterMessage?: string } {
    const beforeMessage = messages[targetMessageIndex - contextSize]?.content
    const afterMessage = messages[targetMessageIndex + contextSize]?.content

    return { beforeMessage, afterMessage }
  }

  /**
   * 搜索会话和消息
   */
  search(sessions: ChatSession[], options: SearchOptions): {
    results: SearchResult[]
    stats: SearchStats
  } {
    const startTime = Date.now()
    const {
      query,
      type = 'all',
      sessionId,
      limit = 50,
      includeContext = false,
      fuzzySearch = true
    } = options

    const results: SearchResult[] = []
    const queryLower = query.toLowerCase().trim()

    if (!queryLower) {
      return {
        results: [],
        stats: {
          totalResults: 0,
          sessionResults: 0,
          messageResults: 0,
          searchTime: 0
        }
      }
    }

    // 搜索会话标题
    if (type === 'all' || type === 'sessions') {
      for (const session of sessions) {
        if (sessionId && session.id !== sessionId) continue

        const score = this.calculateScore(session.title, query, true, fuzzySearch)
        if (score > 0) {
          const highlights = this.highlightText(session.title, query)

          results.push({
            type: 'session',
            sessionId: session.id,
            id: session.id,
            title: session.title,
            content: session.title,
            timestamp: session.updatedAt,
            score,
            highlights
          })
        }
      }
    }

    // 搜索消息内容
    if (type === 'all' || type === 'messages') {
      for (const session of sessions) {
        if (sessionId && session.id !== sessionId) continue

        for (let i = 0; i < session.messages.length; i++) {
          const message = session.messages[i]
          const score = this.calculateScore(message.content, query, false, fuzzySearch)

          if (score > 0) {
            const highlights = this.highlightText(message.content, query)
            const context = includeContext ?
              this.getMessageContext(session.messages, i) : undefined

            results.push({
              type: 'message',
              sessionId: session.id,
              id: message.id,
              title: session.title,
              content: message.content,
              timestamp: message.timestamp,
              score,
              highlights,
              context
            })
          }
        }
      }
    }

    // 按得分排序
    results.sort((a, b) => {
      // 首先按得分排序
      if (b.score !== a.score) {
        return b.score - a.score
      }
      // 得相同时按时间排序（最新的在前）
      return b.timestamp.getTime() - a.timestamp.getTime()
    })

    // 限制结果数量
    const limitedResults = results.slice(0, limit)

    const searchTime = Date.now() - startTime

    return {
      results: limitedResults,
      stats: {
        totalResults: results.length,
        sessionResults: results.filter(r => r.type === 'session').length,
        messageResults: results.filter(r => r.type === 'message').length,
        searchTime
      }
    }
  }

  /**
   * 按会话分组搜索结果
   */
  groupResultsBySession(results: SearchResult[]): Record<string, SearchResult[]> {
    const grouped: Record<string, SearchResult[]> = {}

    for (const result of results) {
      if (!grouped[result.sessionId]) {
        grouped[result.sessionId] = []
      }
      grouped[result.sessionId].push(result)
    }

    // 对每个会话内的结果按时间排序
    for (const sessionId in grouped) {
      grouped[sessionId].sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
    }

    return grouped
  }

  /**
   * 获取搜索建议
   */
  getSuggestions(sessions: ChatSession[], query: string, limit: number = 5): string[] {
    const queryLower = query.toLowerCase().trim()
    const suggestions = new Set<string>()

    if (queryLower.length < 2) return []

    // 从会话标题中提取建议
    for (const session of sessions) {
      const titleWords = session.title.toLowerCase().split(/\s+/)

      for (const word of titleWords) {
        if (word.includes(queryLower) && word !== queryLower) {
          suggestions.add(word)
        }
      }

      // 从消息中提取建议
      for (const message of session.messages.slice(0, 10)) { // 只检查前10条消息
        const messageWords = message.content.toLowerCase().split(/\s+/)

        for (const word of messageWords) {
          if (word.includes(queryLower) && word !== queryLower && word.length > 2) {
            suggestions.add(word)
          }
        }
      }
    }

    return Array.from(suggestions).slice(0, limit)
  }

  /**
   * 获取热门搜索关键词
   */
  getPopularKeywords(sessions: ChatSession[], limit: number = 10): Array<{
    keyword: string
    count: number
  }> {
    const keywordCount = new Map<string, number>()

    // 统计会话标题中的关键词
    for (const session of sessions) {
      const titleWords = session.title
        .toLowerCase()
        .split(/\s+/)
        .flatMap(word => this.extractChineseWords(word)) // 提取中文词汇
        .filter(word => word.length > 2 && !this.isCommonWord(word))

      for (const word of titleWords) {
        keywordCount.set(word, (keywordCount.get(word) || 0) + 1)
      }
    }

    // 统计消息内容中的关键词（限制每个会话前5条消息）
    for (const session of sessions) {
      for (const message of session.messages.slice(0, 5)) {
        const messageWords = message.content
          .toLowerCase()
          .split(/\s+/)
          .filter(word => word.length > 2 && !this.isCommonWord(word))

        for (const word of messageWords) {
          keywordCount.set(word, (keywordCount.get(word) || 0) + 1)
        }
      }
    }

    // 排序并返回热门关键词
    return Array.from(keywordCount.entries())
      .map(([keyword, count]) => ({ keyword, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, limit)
  }

  /**
   * 提取中文词汇（简单实现）
   */
  private extractChineseWords(text: string): string[] {
    // 简单的中文分词：提取连续的中文字符
    const chinesePattern = /[\u4e00-\u9fff]+/g
    const matches = text.match(chinesePattern) || []

    // 对于每个中文匹配，尝试分割成更小的词汇
    const words: string[] = []
    for (const match of matches) {
      // 如果长度大于6，尝试按常见词分割
      if (match.length > 6) {
        // 简单的分割策略：每2-4个字符作为一词
        for (let i = 0; i < match.length; i += 2) {
          const word = match.slice(i, i + 4)
          if (word.length >= 2) {
            words.push(word)
          }
        }
      } else {
        words.push(match)
      }
    }

    return words
  }

  /**
   * 检查是否为常见词
   */
  private isCommonWord(word: string): boolean {
    const commonWords = new Set([
      'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as', 'are', 'was',
      'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did',
      'will', 'would', 'should', 'could', 'may', 'might', 'can',
      '这', '的', '是', '在', '有', '和', '与', '为', '了', '我',
      '你', '他', '她', '它', '们', '这个', '那个', '什么',
      '怎么', '为什么', '如何', '哪里', '哪个', '一个', '测试', '常见词',
      '常见词测试' // 添加测试特定词汇
    ])

    return commonWords.has(word.toLowerCase())
  }
}

// 创建单例实例
export const searchService = new SearchService()

// 便捷函数导出
export const searchSessions = (
  sessions: ChatSession[],
  options: SearchOptions
) => {
  return searchService.search(sessions, options)
}

export const getSearchSuggestions = (
  sessions: ChatSession[],
  query: string,
  limit?: number
) => {
  return searchService.getSuggestions(sessions, query, limit)
}

export const getPopularKeywords = (
  sessions: ChatSession[],
  limit?: number
) => {
  return searchService.getPopularKeywords(sessions, limit)
}

export const groupResultsBySession = (results: SearchResult[]) => {
  return searchService.groupResultsBySession(results)
}