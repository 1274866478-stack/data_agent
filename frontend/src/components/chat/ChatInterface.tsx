'use client'

import { useEffect, useState } from 'react'
import { Plus, Menu, X, Settings, History, Database } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import { useChatStore } from '@/store/chatStore'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { cn } from '@/lib/utils'

interface ChatInterfaceProps {
  className?: string
}

export function ChatInterface({ className }: ChatInterfaceProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sessionTitleFilter, setSessionTitleFilter] = useState('')

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

  return (
    <div className={cn('flex h-full bg-background', className)}>
      {/* 侧边栏 */}
      <aside className="hidden md:flex w-80 flex-col border-r">
        <div className="p-4">
          <Button
            onClick={() => createSession()}
            className="w-full justify-start"
          >
            <Plus className="w-4 h-4 mr-2" />
            新建会话
          </Button>

          {/* 搜索框 */}
          <div className="mt-4">
            <Input
              placeholder="搜索会话..."
              value={sessionTitleFilter}
              onChange={(e) => setSessionTitleFilter(e.target.value)}
              className="text-sm"
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
                    <div className="p-4">
                      <Button
                        onClick={() => {
                          createSession()
                          setSidebarOpen(false)
                        }}
                        className="w-full justify-start"
                      >
                        <Plus className="w-4 h-4 mr-2" />
                        新建会话
                      </Button>
                    </div>

                    <Separator />

                    <ScrollArea className="flex-1 px-4">
                      <div className="space-y-2 py-4">
                        {sessions.map((session) => (
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
        <MessageList className="flex-1" />

        {/* 消息输入 */}
        <MessageInput onFileAttach={(files) => {
          console.log('Files attached:', files)
          // 这里可以添加文件上传逻辑
        }} />
      </main>
    </div>
  )
}