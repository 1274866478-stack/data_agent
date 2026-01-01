/**
 * # SearchPanel 对话搜索面板组件
 *
 * ## [MODULE]
 * **文件名**: SearchPanel.tsx
 * **职责**: 提供全文搜索功能，支持会话和消息搜索、模糊匹配、搜索建议和热门关键词
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - **isOpen**: boolean - 面板打开状态
 * - **onClose**: () => void - 关闭回调
 * - **onResultClick**: (sessionId: string, messageId?: string) => void (可选) - 结果点击回调
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 侧边搜索面板或null
 * - **副作用**: 调用onResultClick跳转到指定消息，调用onClose关闭面板
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [lucide-react](https://lucide.dev) - 图标库
 * - [@/components/ui/*](../ui/) - UI基础组件（Button, Input, Card, Badge, ScrollArea, Popover）
 * - [@/store/chatStore.ts](../../store/chatStore.ts) - 聊会话和消息状态
 * - [@/services/searchService.ts](../../services/searchService.ts) - 搜索核心逻辑
 * - [@/lib/utils.ts](../../lib/utils.ts) - 工具函数
 *
 * **下游依赖**:
 * - 无直接下游组件
 *
 * **调用方**:
 * - [./ChatInterface.tsx](./ChatInterface.tsx) - 聊天界面中的搜索侧边栏
 *
 * ## [STATE]
 * - **query**: string - 搜索查询文本
 * - **searchOptions**: SearchOptions - 搜索配置（类型、模糊搜索、上下文等）
 * - **searchResults**: 搜索结果对象（包含结果列表和统计）
 * - **suggestions**: string[] - 搜索建议列表
 * - **popularKeywords**: Array<{keyword: string; count: number}> - 热门关键词
 * - **showSuggestions**: boolean - 是否显示搜索建议
 *
 * ## [SIDE-EFFECTS]
 * - 300ms防抖自动搜索
 * - 实时更新搜索建议和热门关键词
 * - 点击搜索结果触发页面跳转
 * - 支持会话分组和上下文显示
 * - 显示搜索耗时统计
 */
/**
 * 搜索面板组件
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import { Search, Clock, TrendingUp, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useChatStore } from '@/store/chatStore'
import { searchSessions, getSearchSuggestions, getPopularKeywords, SearchResult, SearchOptions, groupResultsBySession } from '@/services/searchService'
import { cn } from '@/lib/utils'

interface SearchPanelProps {
  isOpen: boolean
  onClose: () => void
  onResultClick?: (sessionId: string, messageId?: string) => void
}

export function SearchPanel({ isOpen, onClose, onResultClick }: SearchPanelProps) {
  const [query, setQuery] = useState('')
  const [searchOptions, setSearchOptions] = useState<SearchOptions>({
    query: '',
    type: 'all',
    fuzzySearch: true,
    includeContext: false,
    limit: 20
  })
  const [searchResults, setSearchResults] = useState<{
    results: SearchResult[]
    stats: {
      totalResults: number
      sessionResults: number
      messageResults: number
      searchTime: number
    }
  } | null>(null)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [popularKeywords, setPopularKeywords] = useState<Array<{ keyword: string; count: number }>>([])
  const [showSuggestions, setShowSuggestions] = useState(false)

  const { sessions } = useChatStore()

  // 获取热门关键词
  useEffect(() => {
    if (sessions.length > 0) {
      const keywords = getPopularKeywords(sessions, 8)
      setPopularKeywords(keywords)
    }
  }, [sessions])

  // 执行搜索
  const performSearch = useMemo(() => {
    return (searchQuery: string, options: Partial<SearchOptions> = {}) => {
      if (!searchQuery.trim()) {
        setSearchResults(null)
        setSuggestions([])
        return
      }

      const finalOptions: SearchOptions = {
        ...searchOptions,
        query: searchQuery,
        ...options,
      }

      const startTime = Date.now()
      const result = searchSessions(sessions, finalOptions)

      setSearchResults(result)
      setSuggestions(getSearchSuggestions(sessions, searchQuery, 5))

      console.log(`Search completed in ${Date.now() - startTime}ms`)
    }
  }, [sessions, searchOptions])

  // 搜索防抖
  useEffect(() => {
    const timer = setTimeout(() => {
      performSearch(query)
    }, 300)

    return () => clearTimeout(timer)
  }, [query, performSearch])

  // 处理搜索选项变化
  const handleOptionChange = (key: keyof SearchOptions, value: any) => {
    const newOptions = { ...searchOptions, [key]: value }
    setSearchOptions(newOptions)
    if (query.trim()) {
      performSearch(query, { [key]: value })
    }
  }

  // 处理搜索建议点击
  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion)
    setShowSuggestions(false)
  }

  // 处理热门关键词点击
  const handleKeywordClick = (keyword: string) => {
    setQuery(keyword)
    setShowSuggestions(false)
  }

  // 处理结果点击
  const handleResultClick = (result: SearchResult) => {
    onResultClick?.(result.sessionId, result.type === 'message' ? result.id : undefined)
    onClose()
  }

  // 清空搜索
  const clearSearch = () => {
    setQuery('')
    setSearchResults(null)
    setSuggestions([])
    setShowSuggestions(false)
  }

  // 按会话分组结果
  const groupedResults = useMemo(() => {
    return searchResults ? groupResultsBySession(searchResults.results) : {}
  }, [searchResults])

  if (!isOpen) return null

  return (
    <div className="w-full h-full bg-background border-l">
      <Card className="h-full rounded-none border-0">
        {/* 搜索头部 */}
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Search className="h-4 w-4" />
              搜索对话
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-8 w-8 p-0"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* 搜索输入框 */}
          <div className="relative">
            <Input
              placeholder="搜索对话内容..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value)
                setShowSuggestions(true)
              }}
              onFocus={() => setShowSuggestions(true)}
              className="pr-8"
            />
            {query && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearSearch}
                className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 p-0"
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>

          {/* 搜索选项 */}
          <div className="flex flex-wrap gap-2 mt-2">
            <select
              value={searchOptions.type}
              onChange={(e) => handleOptionChange('type', e.target.value)}
              className="text-xs px-2 py-1 border rounded bg-background"
            >
              <option value="all">全部</option>
              <option value="sessions">会话</option>
              <option value="messages">消息</option>
            </select>

            <label className="flex items-center gap-1 text-xs">
              <input
                type="checkbox"
                checked={searchOptions.fuzzySearch}
                onChange={(e) => handleOptionChange('fuzzySearch', e.target.checked)}
                className="rounded"
              />
              模糊搜索
            </label>

            <label className="flex items-center gap-1 text-xs">
              <input
                type="checkbox"
                checked={searchOptions.includeContext}
                onChange={(e) => handleOptionChange('includeContext', e.target.checked)}
                className="rounded"
              />
              显示上下文
            </label>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <ScrollArea className="h-[calc(100vh-12rem)]">
            {/* 搜索建议 */}
            {showSuggestions && suggestions.length > 0 && (
              <div className="p-3 border-b">
                <div className="text-xs font-medium text-muted-foreground mb-2">搜索建议</div>
                <div className="flex flex-wrap gap-1">
                  {suggestions.map((suggestion, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="text-xs h-6"
                    >
                      {suggestion}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {/* 搜索结果 */}
            {searchResults && (
              <div className="p-3">
                {/* 搜索统计 */}
                <div className="flex items-center justify-between mb-3 text-xs text-muted-foreground">
                  <span>
                    找到 {searchResults.stats.totalResults} 个结果
                    ({searchResults.stats.sessionResults} 个会话, {searchResults.stats.messageResults} 条消息)
                  </span>
                  <span>
                    {searchResults.stats.searchTime}ms
                  </span>
                </div>

                {searchResults.results.length === 0 ? (
                  /* 无结果状态 */
                  <div className="text-center py-8">
                    <Search className="h-8 w-8 mx-auto text-muted-foreground mb-3" />
                    <p className="text-sm text-muted-foreground">
                      没有找到匹配的内容
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      尝试使用不同的关键词或调整搜索选项
                    </p>
                  </div>
                ) : (
                  /* 搜索结果列表 */
                  <div className="space-y-3">
                    {Object.entries(groupedResults).map(([sessionId, sessionResults]) => {
                      const session = sessions.find(s => s.id === sessionId)
                      const sessionTitle = session?.title || '未知会话'

                      return (
                        <div key={sessionId} className="border rounded-lg p-3">
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="font-medium text-sm truncate">
                              {sessionTitle}
                            </h4>
                            <Badge variant="secondary" className="text-xs">
                              {sessionResults.length} 个结果
                            </Badge>
                          </div>

                          <div className="space-y-2">
                            {sessionResults.map((result) => (
                              <div
                                key={result.id}
                                className={cn(
                                  "p-2 rounded border cursor-pointer transition-colors hover:bg-muted/50",
                                  result.type === 'message' && "ml-4 border-l-2 border-l-primary"
                                )}
                                onClick={() => handleResultClick(result)}
                              >
                                <div className="flex items-start justify-between gap-2">
                                  <div className="flex-1 min-w-0">
                                    {/* 结果标题或内容预览 */}
                                    {result.type === 'session' ? (
                                      <p className="text-sm font-medium">
                                        {result.content}
                                      </p>
                                    ) : (
                                      <div>
                                        <p className="text-sm line-clamp-2">
                                          {result.content}
                                        </p>
                                        {result.context?.beforeMessage && (
                                          <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                                            ...{result.context.beforeMessage}
                                          </p>
                                        )}
                                        {result.context?.afterMessage && (
                                          <p className="text-xs text-muted-foreground line-clamp-1">
                                            {result.context.afterMessage}...
                                          </p>
                                        )}
                                      </div>
                                    )}

                                    {/* 搜索高亮 */}
                                    {result.highlights.length > 0 && (
                                      <div className="flex flex-wrap gap-1 mt-1">
                                        {result.highlights.slice(0, 3).map((highlight, index) => (
                                          <Badge
                                            key={index}
                                            variant="secondary"
                                            className="text-xs bg-yellow-100 text-yellow-800"
                                          >
                                            {highlight}
                                          </Badge>
                                        ))}
                                      </div>
                                    )}
                                  </div>

                                  <div className="text-xs text-muted-foreground whitespace-nowrap">
                                    {result.timestamp.toLocaleString()}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )}

            {/* 热门关键词 */}
            {!query && popularKeywords.length > 0 && (
              <div className="p-3 border-t">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="h-3 w-3 text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground">
                    热门搜索
                  </span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {popularKeywords.map((item, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      onClick={() => handleKeywordClick(item.keyword)}
                      className="text-xs h-6"
                    >
                      {item.keyword}
                      <Badge variant="secondary" className="ml-1 text-xs">
                        {item.count}
                      </Badge>
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}