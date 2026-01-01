/**
 * # [CHAT_INTERFACE] 聊天界面组件
 *
 * ## [MODULE]
 * **文件名**: ChatInterface.tsx
 * **职责**: 提供完整的聊天用户界面，包括会话列表、消息显示、消息输入、搜索和离线状态指示
 *
 * ## [INPUT]
 * Props:
 * - **className?: string** - 可选的CSS类名
 *
 * ## [OUTPUT]
 * UI组件:
 * - **会话列表侧边栏**: 显示所有会话，支持搜索、创建、删除、切换会话
 * - **消息列表区域**: 显示当前会话的所有消息
 * - **消息输入区域**: 提供消息输入和文件上传功能
 * - **搜索面板**: 支持跨会话搜索消息
 * - **响应式布局**: 移动端使用Sheet侧滑，桌面端固定侧边栏
 *
 * **上游依赖**:
 * - [../../store/chatStore.ts](../../store/chatStore.ts) - 聊天状态管理Store
 * - [./MessageList.tsx](./MessageList.tsx) - 消息列表组件
 * - [./MessageInput.tsx](./MessageInput.tsx) - 消息输入组件
 * - [./SearchPanel.tsx](./SearchPanel.tsx) - 搜索面板组件
 * - [./OfflineStatusIndicator.tsx](./OfflineStatusIndicator.tsx) - 离线状态指示器
 * - [../ui/button.tsx](../ui/button.tsx) - 按钮组件
 * - [../ui/card.tsx](../ui/card.tsx) - 卡片组件
 * - [../ui/sheet.tsx](../ui/sheet.tsx) - 侧滑面板组件
 * - lucide-react - 图标库 (Plus, Menu, X, Settings, History, Database, Search)
 *
 * **下游依赖**:
 * - [../layout/Layout.tsx](../layout/Layout.tsx) - 主布局组件 (调用此组件)
 *
 * **调用方**:
 * - [../../app/(app)/chat/page.tsx](../../app/(app)/chat/page.tsx) - 聊天页面
 * - [../../app/page.tsx](../../app/page.tsx) - 首页
 *
 * ## [STATE]
 * - **侧边栏状态**: sidebarOpen (控制移动端侧边栏显示)
 * - **搜索状态**: sessionTitleFilter (会话标题过滤), searchPanelOpen (搜索面板显示)
 * - **高亮状态**: highlightedMessageId (搜索结果高亮显示)
 * - **会话管理**: 从chatStore读取sessions和currentSession
 *
 * ## [SIDE-EFFECTS]
 * - 调用chatStore actions (createSession, switchSession, deleteSession, updateSessionTitle, clearHistory)
 * - 操作MessageList ref (scrollToMessage方法)
 * - 浏览器confirm对话框 (删除会话和清空历史确认)
 * - 定时器 (消息高亮显示3秒后自动清除)
 */

'use client'

import { useEffect, useState, useRef } from 'react'
import { Plus, Menu, X, Settings, History, Database, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import { useChatStore } from '@/store/chatStore'
import { MessageList, MessageListRef } from './MessageList'
import { MessageInput } from './MessageInput'
import { SearchPanel } from './SearchPanel'
import { OfflineStatusIndicator } from './OfflineStatusIndicator'
import { cn } from '@/lib/utils'

interface ChatInterfaceProps {
  className?: string
}

export function ChatInterface({ className }: ChatInterfaceProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sessionTitleFilter, setSessionTitleFilter] = useState('')
  const [searchPanelOpen, setSearchPanelOpen] = useState(false)
  const [highlightedMessageId, setHighlightedMessageId] = useState<string | null>(null)
  const messageListRef = useRef<MessageListRef>(null)

  const {
    sessions,
    currentSession,
    createSession,
    switchSession,
    deleteSession,
    updateSessionTitle,
    clearHistory,
    error,
    setError
  } = useChatStore()

  // 过滤后的会话列表
  const filteredSessions = sessions.filter(session =>
    session.title.toLowerCase().includes(sessionTitleFilter.toLowerCase())
  )

  // 初始化时创建第一个会话
  useEffect(() => {
    if (sessions.length === 0) {
      createSession('新会话')
    }
  }, [sessions.length, createSession])

  // 处理会话标题编辑
  const handleSessionTitleEdit = (sessionId: string, newTitle: string) => {
    if (newTitle.trim()) {
      updateSessionTitle(sessionId, newTitle.trim())
    }
  }

  // 处理会话删除
  const handleDeleteSession = (sessionId: string) => {
    if (sessions.length <= 1) {
      setError('不能删除最后一个会话')
      return
    }

    if (confirm('确定要删除这个会话吗？所有消息将被永久删除。')) {
      deleteSession(sessionId)
    }
  }

  // 处理清空历史
  const handleClearHistory = (sessionId: string) => {
    if (confirm('确定要清空这个会话的所有消息吗？')) {
      clearHistory(sessionId)
    }
  }

  // 处理搜索结果点击
  const handleSearchResultClick = (sessionId: string, messageId?: string) => {
    // 先切换到目标会话
    if (currentSession?.id !== sessionId) {
      switchSession(sessionId)
    }

    // 如果有消息ID，延迟设置高亮（等待会话切换完成）
    if (messageId) {
      setTimeout(() => {
        setHighlightedMessageId(messageId)
        messageListRef.current?.scrollToMessage(messageId)
        // 3秒后清除高亮
        setTimeout(() => setHighlightedMessageId(null), 3000)
      }, 100)
    }
  }

  return (
    <div className={cn('flex h-full bg-background', className)}>
      {/* 侧边栏 */}
      <aside className="hidden md:flex w-80 flex-col border-r">
        <div className="p-4">
          <div className="flex gap-2">
            <Button
              onClick={() => createSession()}
              className="flex-1 justify-start"
            >
              <Plus className="w-4 h-4 mr-2" />
              新建会话
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setSearchPanelOpen(true)}
              title="搜索对话"
            >
              <Search className="w-4 h-4" />
            </Button>
          </div>

          {/* 搜索框 */}
          <div className="mt-4">
            <Input
              placeholder="搜索会话..."
              value={sessionTitleFilter}
              onChange={(e) => setSessionTitleFilter(e.target.value)}
              className="text-sm"
              aria-label="搜索会话"
            />
          </div>
        </div>

        <Separator />

        {/* 会话列表 */}
        <ScrollArea className="flex-1 px-4">
          <div className="space-y-2 py-4">
            {filteredSessions.length === 0 ? (
              <div className="text-center text-muted-foreground text-sm py-8">
                {sessionTitleFilter ? '没有找到匹配的会话' : '暂无会话'}
              </div>
            ) : (
              filteredSessions.map((session) => (
                <Card
                  key={session.id}
                  className={cn(
                    'cursor-pointer transition-colors hover:bg-muted/50',
                    currentSession?.id === session.id && 'border-primary bg-primary/5'
                  )}
                  onClick={() => switchSession(session.id)}
                >
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium text-sm truncate">
                          {session.title}
                        </h4>
                        <p className="text-xs text-muted-foreground">
                          {session.updatedAt.toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-1 ml-2">
                        {session.messages.length > 0 && (
                          <span className="text-xs bg-muted px-2 py-1 rounded-full">
                            {session.messages.length}
                          </span>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </ScrollArea>

        <Separator />

        {/* 底部操作 */}
        <div className="p-4 space-y-2">
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start"
            onClick={() => {
              // 这里可以添加历史记录功能
            }}
          >
            <History className="w-4 h-4 mr-2" />
            历史记录
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start"
            onClick={() => {
              // 这里可以添加数据源管理功能
            }}
          >
            <Database className="w-4 h-4 mr-2" />
            数据源管理
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start"
            onClick={() => {
              // 这里可以添加设置功能
            }}
          >
            <Settings className="w-4 h-4 mr-2" />
            设置
          </Button>
        </div>
      </aside>

      {/* 主聊天区域 */}
      <main className="flex-1 flex flex-col">
        {/* 顶部标题栏 */}
        <header className="border-b px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* 移动端菜单按钮 */}
              <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="sm" className="md:hidden">
                    <Menu className="w-4 h-4" />
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="w-80 p-0">
                  <div className="h-full flex flex-col">
                    <div className="p-4 space-y-3">
                      <div className="flex gap-2">
                        <Button
                          onClick={() => {
                            createSession()
                            setSidebarOpen(false)
                          }}
                          className="flex-1 justify-start"
                        >
                          <Plus className="w-4 h-4 mr-2" />
                          新建会话
                        </Button>
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => {
                            setSidebarOpen(false)
                            setSearchPanelOpen(true)
                          }}
                          title="搜索对话"
                        >
                          <Search className="w-4 h-4" />
                        </Button>
                      </div>

                      {/* 移动端会话过滤 */}
                      <Input
                        placeholder="搜索会话..."
                        value={sessionTitleFilter}
                        onChange={(e) => setSessionTitleFilter(e.target.value)}
                        className="text-sm"
                      />
                    </div>

                    <Separator />

                    <ScrollArea className="flex-1 px-4">
                      <div className="space-y-2 py-4">
                        {filteredSessions.map((session) => (
                          <Card
                            key={session.id}
                            className={cn(
                              'cursor-pointer transition-colors hover:bg-muted/50',
                              currentSession?.id === session.id && 'border-primary bg-primary/5'
                            )}
                            onClick={() => {
                              switchSession(session.id)
                              setSidebarOpen(false)
                            }}
                          >
                            <CardContent className="p-3">
                              <div className="flex items-center justify-between">
                                <div className="flex-1 min-w-0">
                                  <h4 className="font-medium text-sm truncate">
                                    {session.title}
                                  </h4>
                                  <p className="text-xs text-muted-foreground">
                                    {session.updatedAt.toLocaleDateString()}
                                  </p>
                                </div>
                                {session.messages.length > 0 && (
                                  <span className="text-xs bg-muted px-2 py-1 rounded-full">
                                    {session.messages.length}
                                  </span>
                                )}
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                        {filteredSessions.length === 0 && (
                          <div className="text-center text-muted-foreground text-sm py-8">
                            {sessionTitleFilter ? '没有找到匹配的会话' : '暂无会话'}
                          </div>
                        )}
                      </div>
                    </ScrollArea>
                  </div>
                </SheetContent>
              </Sheet>

              {/* 会话标题 */}
              <div>
                <h1 className="text-lg font-semibold">
                  {currentSession?.title || '聊天'}
                </h1>
                <p className="text-sm text-muted-foreground">
                  {currentSession?.messages.length || 0} 条消息
                </p>
              </div>
            </div>

            {/* 右侧操作按钮 */}
            <div className="flex items-center gap-2">
              {/* 离线状态指示器 */}
              <OfflineStatusIndicator />

              {currentSession && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleClearHistory(currentSession.id)}
                >
                  清空历史
                </Button>
              )}
            </div>
          </div>
        </header>

        {/* 错误提示 */}
        {error && (
          <div className="mx-6 mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
            <div className="flex items-center justify-between">
              <p className="text-sm text-destructive">{error}</p>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setError(null)}
                className="h-auto p-1 text-destructive hover:text-destructive"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}

        {/* 消息列表 */}
        <MessageList
          ref={messageListRef}
          className="flex-1"
          messages={currentSession?.messages || []}
          highlightedMessageId={highlightedMessageId}
        />

        {/* 消息输入 */}
        <MessageInput onFileAttach={(files) => {
          console.log('Files attached:', files)
          // 这里可以添加文件上传逻辑
        }} />
      </main>

      {/* 搜索面板 - 桌面端 */}
      {searchPanelOpen && (
        <aside className="hidden md:block w-96 border-l">
          <SearchPanel
            isOpen={searchPanelOpen}
            onClose={() => setSearchPanelOpen(false)}
            onResultClick={handleSearchResultClick}
          />
        </aside>
      )}

      {/* 搜索面板 - 移动端 */}
      <Sheet open={searchPanelOpen} onOpenChange={setSearchPanelOpen}>
        <SheetContent side="right" className="w-full sm:w-96 p-0 md:hidden">
          <SearchPanel
            isOpen={searchPanelOpen}
            onClose={() => setSearchPanelOpen(false)}
            onResultClick={(sessionId, messageId) => {
              handleSearchResultClick(sessionId, messageId)
              setSearchPanelOpen(false)
            }}
          />
        </SheetContent>
      </Sheet>
    </div>
  )
}