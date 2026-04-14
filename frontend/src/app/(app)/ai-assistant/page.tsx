'use client'

import Link from 'next/link'
import { useChatStore } from '@/store/chatStore'
import { useDataSourceStore } from '@/store/dataSourceStore'
import { useAuthStore } from '@/store/authStore'
import { removeChartMarkers } from '@/utils/chartParser'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import { Markdown } from '@/components/ui/markdown'
import { PlainText } from '@/components/ui/plain-text'
import { ScrollArea } from '@/components/ui/scroll-area'
import { ProcessingSteps } from '@/components/chat/ProcessingSteps'
import { cn } from '@/lib/utils'
import { fileUploadService, uploadFile, UploadProgress } from '@/services/fileUploadService'
import { AlertCircle, AlertTriangle, CheckCircle, CheckSquare, ChevronDown, ChevronLeft, Database, FileText, History, Loader2, MessageSquare, Paperclip, Plus, Search, Send, Square, Trash2, User, X } from 'lucide-react'
import Image from 'next/image'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

interface UploadedFile {
  file: File
  document?: any
  status: 'pending' | 'uploading' | 'completed' | 'error'
  error?: string
}

export default function AIAssistantPage() {
  const [input, setInput] = useState('')
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null)
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [showHistory, setShowHistory] = useState(false)
  const [batchSelectMode, setBatchSelectMode] = useState(false)
  const [selectedSessions, setSelectedSessions] = useState<Set<string>>(new Set())
  const [selectedDataSourceIds, setSelectedDataSourceIds] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const {
    sendMessage,
    currentSession,
    createSession,
    isLoading,
    sessions,
    switchSession,
    deleteSession,
    deleteSessions,
    searchSessions,
    startNewConversation,
    stopStreaming,
    streamingStatus,
    outputFormat,
    setOutputFormat
  } = useChatStore()

  // 认证状态
  const { isAuthenticated, user } = useAuthStore()

  // 数据源相关
  const {
    dataSources,
    isLoading: isLoadingDataSources,
    fetchDataSources
  } = useDataSourceStore()

  // 加载数据源列表
  useEffect(() => {
    // TODO: 从认证上下文获取租户ID，现在使用默认值
    const tenantId = 'default_tenant'
    fetchDataSources(tenantId, { active_only: true })
  }, [fetchDataSources])

  // 获取活跃的数据源列表
  const activeDataSources = useMemo(() => {
    return dataSources.filter(ds => ds.status === 'active')
  }, [dataSources])

  // 获取选中的数据源对象（空表示使用所有数据源）
  const selectedDataSources = useMemo(() => {
    if (selectedDataSourceIds.length === 0) return []
    const selectedSet = new Set(selectedDataSourceIds)
    return activeDataSources.filter(ds => selectedSet.has(ds.id))
  }, [activeDataSources, selectedDataSourceIds])

  const selectedDataSourceLabel = useMemo(() => {
    if (selectedDataSources.length === 0) return '所有数据源（自动）'
    if (selectedDataSources.length === 1) return selectedDataSources[0].name
    if (selectedDataSources.length === 2) return `${selectedDataSources[0].name}、${selectedDataSources[1].name}`
    return `${selectedDataSources[0].name} 等 ${selectedDataSources.length} 个`
  }, [selectedDataSources])

  // 获取当前会话的消息，如果没有会话则为空数组
  const messages = currentSession?.messages || []

  // 搜索过滤后的历史会话
  const filteredSessions = useMemo(() => {
    return searchSessions(searchQuery).sort((a, b) =>
      new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    )
  }, [sessions, searchQuery, searchSessions])

  // 开始新对话
  const handleStartNewConversation = async () => {
    await startNewConversation()
    setShowHistory(false)
  }

  // 切换到某个历史会话
  const handleSwitchSession = (sessionId: string) => {
    switchSession(sessionId)
    setShowHistory(false)
  }

  // 删除某个会话
  const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation()
    if (confirm('确定要删除这个对话吗？')) {
      deleteSession(sessionId)
    }
  }

  // 切换批量选择模式
  const toggleBatchSelectMode = () => {
    setBatchSelectMode(!batchSelectMode)
    setSelectedSessions(new Set())
  }

  // 切换单个会话的选择状态
  const toggleSessionSelection = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation()
    const newSelected = new Set(selectedSessions)
    if (newSelected.has(sessionId)) {
      newSelected.delete(sessionId)
    } else {
      newSelected.add(sessionId)
    }
    setSelectedSessions(newSelected)
  }

  // 全选/取消全选
  const toggleSelectAll = () => {
    if (selectedSessions.size === filteredSessions.length) {
      setSelectedSessions(new Set())
    } else {
      setSelectedSessions(new Set(filteredSessions.map(s => s.id)))
    }
  }

  // 批量删除选中的会话
  const handleBatchDelete = () => {
    if (selectedSessions.size === 0) return
    if (confirm(`确定要删除选中的 ${selectedSessions.size} 个对话吗？`)) {
      deleteSessions(Array.from(selectedSessions))
      setSelectedSessions(new Set())
      setBatchSelectMode(false)
    }
  }

  const handleSend = async () => {
    // 如果没有会话，先创建一个
    if (!currentSession) {
      await createSession('新对话')
    }

    if (!input.trim() || isLoading) return
    const content = input.trim()
    setInput('')
    // 如果没有选择数据源，自动使用第一个活跃数据源（确保使用 Agent）
    let dataSourceIds = selectedDataSourceIds
    if (dataSourceIds.length === 0 && activeDataSources.length > 0) {
      dataSourceIds = [activeDataSources[0].id]
    }
    await sendMessage(content, dataSourceIds.length > 0 ? dataSourceIds : undefined)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 验证文件类型
  const validateFile = useCallback((file: File): { valid: boolean; error?: string } => {
    if (!fileUploadService.isFileTypeSupported(file)) {
      return {
        valid: false,
        error: `不支持的文件类型: ${file.name}。仅支持 PDF、Word 文档。`,
      }
    }

    if (!fileUploadService.isFileSizeValid(file)) {
      const maxSize = fileUploadService.formatFileSize(fileUploadService.getMaxFileSize())
      return {
        valid: false,
        error: `文件过大: ${fileUploadService.formatFileSize(file.size)}。最大支持 ${maxSize}。`,
      }
    }

    return { valid: true }
  }, [])

  // 处理文件上传
  const handleFileUpload = async (files: File[]) => {
    if (files.length === 0) return

    for (const file of files) {
      const validation = validateFile(file)
      if (!validation.valid) {
        setUploadProgress({
          loaded: 0,
          total: file.size,
          percentage: 0,
          status: 'error',
          message: validation.error,
        })
        setTimeout(() => setUploadProgress(null), 3000)
        continue
      }

      const uploadedFile: UploadedFile = { file, status: 'uploading' }
      setUploadedFiles(prev => [...prev, uploadedFile])

      setUploadProgress({
        loaded: 0,
        total: file.size,
        percentage: 0,
        status: 'pending',
        message: `准备上传: ${file.name}`,
      })

      try {
        const result = await uploadFile(file, (progress) => {
          setUploadProgress(progress)
        })

        if (result.success && result.document) {
          setUploadedFiles(prev =>
            prev.map(f =>
              f.file === file
                ? { ...f, status: 'completed' as const, document: result.document }
                : f
            )
          )
          setTimeout(() => setUploadProgress(null), 1500)
        } else {
          setUploadedFiles(prev =>
            prev.map(f =>
              f.file === file
                ? { ...f, status: 'error' as const, error: result.error }
                : f
            )
          )
          setUploadProgress({
            loaded: 0,
            total: file.size,
            percentage: 0,
            status: 'error',
            message: result.error || '上传失败',
          })
          setTimeout(() => setUploadProgress(null), 3000)
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : '上传过程中发生错误'
        setUploadedFiles(prev =>
          prev.map(f =>
            f.file === file
              ? { ...f, status: 'error' as const, error: errorMessage }
              : f
          )
        )
        setUploadProgress({
          loaded: 0,
          total: file.size,
          percentage: 0,
          status: 'error',
          message: errorMessage,
        })
        setTimeout(() => setUploadProgress(null), 3000)
      }
    }
  }

  // 通过文件选择器上传文件
  const handleFileSelect = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  // 处理文件选择器的 change 事件
  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length > 0) {
      handleFileUpload(files)
    }
    e.target.value = ''
  }, [])

  // 移除已上传的文件
  const removeUploadedFile = useCallback((index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index))
  }, [])

  // 重试上传失败的文件
  const retryUpload = useCallback((index: number) => {
    const uploadedFile = uploadedFiles[index]
    if (uploadedFile && uploadedFile.status === 'error') {
      setUploadedFiles(prev => prev.filter((_, i) => i !== index))
      handleFileUpload([uploadedFile.file])
    }
  }, [uploadedFiles])

  const completedUploads = uploadedFiles.filter(f => f.status === 'completed').length

  return (
    <div className="h-screen flex flex-col bg-gradient-to-b from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      {/* 极简顶部栏 - 参考 ChatGPT */}
      <header className="h-16 flex items-center justify-between px-6 border-b border-slate-200/50 dark:border-slate-700/50 bg-white/60 dark:bg-slate-900/60 backdrop-blur-sm flex-shrink-0">
        {/* 左侧：Logo + 历史记录（已登录时） */}
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl overflow-hidden flex items-center justify-center">
            <Image src="/logo-icon-only.svg" alt="Insight Agent" width={36} height={36} className="object-contain" />
          </div>
          <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
            Insight Agent
          </h1>
          {isAuthenticated && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowHistory(!showHistory)}
              className="gap-2 ml-2 text-slate-700 dark:text-slate-300"
            >
              <History className="w-4 h-4" />
              History
              {sessions.length > 0 && (
                <span className="bg-primary/20 text-primary text-xs px-1.5 py-0.5 rounded-full font-medium">
                  {sessions.length}
                </span>
              )}
            </Button>
          )}
        </div>

        {/* 右侧：登录/注册（未登录）或 New Chat（已登录） */}
        {isAuthenticated ? (
          <Button
            onClick={handleStartNewConversation}
            size="sm"
            className="gap-2 bg-primary text-slate-900 hover:opacity-90"
          >
            <Plus className="w-4 h-4" />
            New Chat
          </Button>
        ) : (
          <div className="flex items-center gap-3">
            <Link href="/sign-in">
              <Button variant="ghost" size="sm" className="text-slate-700 dark:text-slate-300">
                登录
              </Button>
            </Link>
            <Link href="/sign-up">
              <Button size="sm" className="bg-black dark:bg-white text-white dark:text-black hover:bg-slate-800 dark:hover:bg-slate-200">
                免费注册
              </Button>
            </Link>
          </div>
        )}
      </header>

      {/* 主内容区 */}
      <div className="flex-1 flex min-h-0">
        {/* 历史对话侧边栏 */}
        <div className={cn(
          "h-full bg-white/60 dark:bg-slate-900/60 backdrop-blur-sm border-r border-slate-200/60 dark:border-slate-700/60 shadow-lg transition-all duration-300 flex flex-col",
          showHistory ? "w-80" : "w-0 overflow-hidden"
        )}>
        {showHistory && (
          <>
            {/* 侧边栏头部 */}
            <div className="p-4 border-b flex-shrink-0">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-foreground flex items-center gap-2">
                  <History className="w-4 h-4" />
                  历史对话
                </h3>
                <div className="flex items-center gap-1">
                  {/* 批量选择按钮 */}
                  <Button
                    variant={batchSelectMode ? "default" : "ghost"}
                    size="icon"
                    onClick={toggleBatchSelectMode}
                    className="h-8 w-8"
                    title={batchSelectMode ? "取消批量选择" : "批量选择"}
                  >
                    <CheckSquare className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setShowHistory(false)}
                    className="h-8 w-8"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              {/* 批量操作栏 */}
              {batchSelectMode && (
                <div className="flex items-center justify-between mb-3 p-2 bg-primary/10 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={filteredSessions.length > 0 && selectedSessions.size === filteredSessions.length}
                      onCheckedChange={toggleSelectAll}
                    />
                    <span className="text-sm text-primary">
                      {selectedSessions.size > 0 ? `已选 ${selectedSessions.size} 项` : '全选'}
                    </span>
                  </div>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleBatchDelete}
                    disabled={selectedSessions.size === 0}
                    className="h-7 text-xs"
                  >
                    <Trash2 className="w-3 h-3 mr-1" />
                    删除
                  </Button>
                </div>
              )}

              {/* 搜索框 */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="搜索对话..."
                  className="pl-9 h-9"
                />
                {searchQuery && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setSearchQuery('')}
                    className="absolute right-1 top-1/2 transform -translate-y-1/2 h-7 w-7"
                  >
                    <X className="w-3 h-3" />
                  </Button>
                )}
              </div>
            </div>

            {/* 会话列表 */}
            <ScrollArea className="flex-1">
              <div className="p-2">
                {filteredSessions.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <MessageSquare className="w-10 h-10 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">
                      {searchQuery ? '没有找到匹配的对话' : '暂无历史对话'}
                    </p>
                  </div>
                ) : (
                  filteredSessions.map((session) => (
                    <div
                      key={session.id}
                      onClick={() => batchSelectMode ? null : handleSwitchSession(session.id)}
                      className={cn(
                        "p-3 rounded-lg cursor-pointer mb-1 group transition-colors",
                        selectedSessions.has(session.id)
                          ? "bg-primary/20 border border-primary/40"
                          : session.id === currentSession?.id
                            ? "bg-primary/10 border border-primary/30"
                            : "hover:bg-muted"
                      )}
                    >
                      <div className="flex items-start gap-2">
                        {/* 批量选择复选框 */}
                        {batchSelectMode && (
                          <div className="pt-0.5" onClick={(e) => toggleSessionSelection(e, session.id)}>
                            <Checkbox
                              checked={selectedSessions.has(session.id)}
                              onCheckedChange={() => {}}
                            />
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">{session.title}</p>
                          <p className="text-xs text-muted-foreground mt-1">
                            {session.messages.length} 条消息
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(session.updatedAt).toLocaleDateString('zh-CN', {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </p>
                        </div>
                        {/* 非批量模式显示删除按钮 */}
                        {!batchSelectMode && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={(e) => handleDeleteSession(e, session.id)}
                            className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </>
        )}
      </div>

        {/* 主内容区 - 居中布局 */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex-1 max-w-3xl mx-auto w-full flex flex-col min-h-0 overflow-hidden px-4">

          {/* 消息区域 */}
          <div className="flex-1 overflow-y-auto space-y-4 py-6">
          {messages.length === 0 ? (
            /* 极简欢迎界面 */
            <div className="h-full flex flex-col items-center justify-center text-center px-4">
              <h2 className="text-2xl font-semibold text-foreground mb-3">
                准备好了，随时开始
              </h2>
              <p className="text-muted-foreground mb-8 max-w-md">
                我可以帮助您分析数据、回答问题、生成报告。
              </p>
              <div className="flex flex-wrap justify-center gap-2 max-w-lg">
                {[
                  '介绍一下你的功能',
                  '分析我的数据源',
                  '生成数据报告',
                ].map((question) => (
                  <button
                    key={question}
                    onClick={() => setInput(question)}
                    className="text-sm px-4 py-2 rounded-full bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-foreground transition-colors"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
              ) : (
                <>
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex gap-3 ${
                        message.role === 'user' ? 'flex-row-reverse' : ''
                      }`}
                    >
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                        message.role === 'user'
                          ? 'bg-gradient-to-br from-primary to-primary/80 text-primary-foreground'
                          : 'bg-muted text-muted-foreground'
                      }`}>
                        {message.role === 'user' ? (
                          <User className="w-5 h-5" />
                        ) : (
                          <div className="w-5 h-5 flex items-center justify-center text-foreground">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
                              <path d="M12 8V4H8" />
                              <rect width="16" height="12" x="4" y="8" rx="2" />
                              <path d="M2 14h2" />
                              <path d="M20 14h2" />
                              <path d="M15 13v2" />
                              <path d="M9 13v2" />
                            </svg>
                          </div>
                        )}
                      </div>
                      <div className={`flex-1 max-w-[75%] ${
                        message.role === 'user' ? 'text-right' : ''
                      }`}>
                        <div className={cn(
                          "inline-block p-4 rounded-2xl",
                          message.role === 'user'
                            ? 'bg-gradient-to-br from-primary-400 to-primary-500 text-slate-900 font-medium shadow-glow message-user'
                            : 'bg-white/95 dark:bg-slate-800/95 border border-primary-200/50 dark:border-primary-500/30 shadow-sm backdrop-blur-sm message-ai'
                        )}>
                          {message.role === 'user' ? (
                            <p className="text-base whitespace-pre-wrap">{message.content}</p>
                          ) : (
                            <div className="text-foreground">
                              {/* 🔴 第三道防线：检测工具调用失败并显示警告 */}
                              {(() => {
                                const hasSystemError = message.content.includes('SYSTEM ERROR') || 
                                                       message.content.includes('无法获取数据') ||
                                                       message.content.includes('工具调用失败') ||
                                                       (message.metadata as any)?.tool_error === true ||
                                                       (message.metadata as any)?.tool_status === 'error'
                                if (hasSystemError) {
                                  return (
                                    <div className="mb-3 p-3 bg-destructive/10 border border-destructive/30 rounded-lg flex items-start gap-2">
                                      <AlertTriangle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
                                      <div className="flex-1">
                                        <p className="text-sm font-medium text-destructive">数据源连接失败</p>
                                        <p className="text-xs text-destructive/80 mt-1">以下回答可能不准确，请检查数据源连接状态</p>
                                      </div>
                                    </div>
                                  )
                                }
                                return null
                              })()}
                              
                              {/* 显示工具调用状态和推理过程（默认展开） */}
                              {message.metadata && (
                                <div className="mb-3 space-y-2">
                                  {/* 工具调用状态 */}
                                  {(message.metadata as any).tool_calls && (message.metadata as any).tool_calls.length > 0 && (
                                    <div className="text-xs bg-primary/10 border border-primary/30 rounded p-2">
                                      <div className="font-medium text-primary mb-1">工具调用:</div>
                                      <div className="space-y-1">
                                        {(message.metadata as any).tool_calls.map((tc: any, idx: number) => (
                                          <div key={idx} className="flex items-center gap-2">
                                            <span className="text-primary">• {tc.name || 'unknown'}</span>
                                            {tc.status === 'error' && (
                                              <AlertTriangle className="w-3 h-3 text-destructive" />
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                  
                                  {/* 推理过程（默认展开） */}
                                  {message.metadata.reasoning && (
                                    <details open className="text-xs bg-muted border border-border rounded p-2">
                                      <summary className="font-medium text-foreground cursor-pointer mb-1">推理过程</summary>
                                      <p className="text-muted-foreground mt-1 whitespace-pre-wrap">{message.metadata.reasoning}</p>
                                    </details>
                                  )}
                                </div>
                              )}
                              
                              {/* AI 正在思考提示（仅在加载中且该消息是最后一条AI消息时显示，置于推理过程上方） */}
                              {isLoading && message === messages.filter(m => m.role === 'assistant').pop() && (
                                <div className="mb-3 inline-flex items-center gap-2 px-3 py-2 rounded-full bg-primary/10 border border-primary/30">
                                  <div className="flex gap-1">
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce delay-75"></div>
                                    <div className="w-2 h-2 bg-primary rounded-full animate-bounce delay-150"></div>
                                  </div>
                                  <span className="text-sm text-muted-foreground">AI 正在思考...</span>
                                </div>
                              )}

                              {/* 显示AI推理步骤（包含SQL、表格、图表） */}
                              {message.metadata?.processing_steps && message.metadata.processing_steps.length > 0 && (
                                <ProcessingSteps
                                  steps={message.metadata.processing_steps}
                                  defaultExpanded={true}
                                  outputFormat={outputFormat}
                                />
                              )}

                              {outputFormat === 'plain' ? (
                                <PlainText content={removeChartMarkers(message.content, !!(message.metadata?.processing_steps && message.metadata.processing_steps.length > 0))} className="text-base leading-relaxed" />
                              ) : (
                                <Markdown content={removeChartMarkers(message.content, !!(message.metadata?.processing_steps && message.metadata.processing_steps.length > 0))} className="prose-base" />
                              )}
                            </div>
                          )}
                        </div>
                        <div className={`text-xs text-muted-foreground mt-1 px-2 ${
                          message.role === 'user' ? 'text-right' : ''
                        }`}>
                          {message.timestamp.toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  ))}

                </>
              )}
            </div>

            {/* 输入框区域 */}
          <div className="pb-6 pt-4 flex-shrink-0">
            {/* 隐藏的文件输入 */}
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              multiple
              onChange={handleFileInputChange}
            />

            {/* 文件上传进度 */}
            {uploadProgress && (
              <div className="mb-3 max-w-2xl mx-auto p-2 bg-muted rounded-lg">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium">{uploadProgress.message}</span>
                  {uploadProgress.status === 'error' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setUploadProgress(null)}
                      className="h-auto p-0 text-xs"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  )}
                </div>
                {uploadProgress.status === 'uploading' && (
                  <div className="w-full bg-background rounded-full h-1.5">
                    <div
                      className="bg-primary h-1.5 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress.percentage}%` }}
                    />
                  </div>
                )}
                {uploadProgress.status === 'completed' && (
                  <div className="text-xs text-green-600">✓ {uploadProgress.message}</div>
                )}
                {uploadProgress.status === 'error' && (
                  <div className="text-xs text-destructive">✗ {uploadProgress.message}</div>
                )}
              </div>
            )}

            {/* 已上传文件列表 */}
            {uploadedFiles.length > 0 && (
              <div className="mb-3 max-w-2xl mx-auto space-y-1.5">
                <div className="text-xs text-muted-foreground mb-1 flex items-center gap-2">
                  <span>已上传文件</span>
                  <span className="px-1.5 py-0.5 bg-muted rounded-full text-[10px]">
                    {completedUploads}/{uploadedFiles.length}
                  </span>
                </div>
                {uploadedFiles.map((uploadedFile, index) => (
                  <div
                    key={index}
                    className={cn(
                      "flex items-center gap-2 p-2 rounded text-xs transition-colors",
                      uploadedFile.status === 'completed' && "bg-green-500/10",
                      uploadedFile.status === 'error' && "bg-destructive/10",
                      uploadedFile.status === 'uploading' && "bg-primary/10",
                      uploadedFile.status === 'pending' && "bg-muted/30"
                    )}
                  >
                    {uploadedFile.status === 'completed' && (
                      <CheckCircle className="h-3.5 w-3.5 text-green-600 flex-shrink-0" />
                    )}
                    {uploadedFile.status === 'error' && (
                      <AlertCircle className="h-3.5 w-3.5 text-destructive flex-shrink-0" />
                    )}
                    {uploadedFile.status === 'uploading' && (
                      <Loader2 className="h-3.5 w-3.5 text-primary animate-spin flex-shrink-0" />
                    )}
                    {uploadedFile.status === 'pending' && (
                      <FileText className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                    )}
                    <span className="flex-1 truncate">{uploadedFile.file.name}</span>
                    <span className="text-muted-foreground flex-shrink-0">
                      {fileUploadService.formatFileSize(uploadedFile.file.size)}
                    </span>
                    {uploadedFile.status === 'error' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => retryUpload(index)}
                        className="h-auto px-1.5 py-0.5 text-xs text-primary hover:text-primary/80 hover:bg-primary/10"
                      >
                        重试
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeUploadedFile(index)}
                      className="h-auto p-0.5 text-muted-foreground hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            )}

            {/* 数据源选择器 - 紧凑版，居中 */}
            <div className="mb-3 flex items-center justify-center">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-7 text-xs gap-1 text-muted-foreground hover:text-foreground">
                    <Database className="w-3 h-3" />
                    <span>{selectedDataSourceLabel}</span>
                    <ChevronDown className="w-3 h-3" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="center" className="w-64">
                  <DropdownMenuLabel>选择数据源</DropdownMenuLabel>
                  <DropdownMenuCheckboxItem
                    checked={selectedDataSourceIds.length === 0}
                    onCheckedChange={() => setSelectedDataSourceIds([])}
                    className="pl-2"
                    onSelect={(e) => e.preventDefault()}
                  >
                    <div className="flex items-center gap-2">
                      <Checkbox checked={selectedDataSourceIds.length === 0} className="pointer-events-none h-3.5 w-3.5" />
                      <span>所有数据源（自动）</span>
                    </div>
                  </DropdownMenuCheckboxItem>
                  <DropdownMenuSeparator />
                  {isLoadingDataSources ? (
                    <DropdownMenuItem disabled className="flex items-center gap-2">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      加载中...
                    </DropdownMenuItem>
                  ) : activeDataSources.length === 0 ? (
                    <DropdownMenuItem disabled className="text-muted-foreground">
                      暂无可用数据源
                    </DropdownMenuItem>
                  ) : (
                    activeDataSources.map((ds) => (
                      <DropdownMenuCheckboxItem
                        key={ds.id}
                        checked={selectedDataSourceIds.includes(ds.id)}
                        onCheckedChange={(checked) => {
                          const isChecked = Boolean(checked)
                          setSelectedDataSourceIds((prev) => {
                            const next = new Set(prev)
                            if (isChecked) {
                              next.add(ds.id)
                            } else {
                              next.delete(ds.id)
                            }
                            return Array.from(next)
                          })
                        }}
                        onSelect={(e) => e.preventDefault()}
                      >
                        <div className="flex items-center justify-between gap-2 w-full">
                          <div className="flex items-center gap-2 min-w-0">
                            <Checkbox checked={selectedDataSourceIds.includes(ds.id)} className="pointer-events-none h-3.5 w-3.5" />
                            <span className="truncate">{ds.name}</span>
                          </div>
                          <Badge variant="outline" className="text-[10px] px-1 py-0">
                            {ds.db_type.toUpperCase()}
                          </Badge>
                        </div>
                      </DropdownMenuCheckboxItem>
                    ))
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* 居中输入框 */}
            <div className="relative max-w-2xl mx-auto">
              {/* 玻璃态输入容器 */}
              <div className="rounded-2xl border border-slate-200/60 dark:border-slate-700/60 bg-white/90 dark:bg-slate-800/90 backdrop-blur-sm shadow-lg ring-1 ring-slate-200/50 dark:ring-slate-700/50 p-2 flex items-end gap-2">
                {/* 文件上传按钮 */}
                <button
                  onClick={handleFileSelect}
                  disabled={isLoading || uploadProgress?.status === 'uploading'}
                  className="p-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 flex-shrink-0"
                  title="上传文档 (PDF, Word)"
                >
                  {uploadProgress?.status === 'uploading' ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Paperclip className="h-5 w-5" />
                  )}
                </button>

                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder={completedUploads > 0 ? `已上传 ${completedUploads} 个文件，输入问题...` : "输入您的问题..."}
                  disabled={isLoading}
                  className="flex-1 bg-transparent border-0 focus:ring-0 text-slate-800 dark:text-slate-100 placeholder-slate-400 py-2.5 px-2 resize-none leading-relaxed outline-none text-base"
                  rows={1}
                  style={{ minHeight: '48px', maxHeight: '120px' }}
                />

                {isLoading ? (
                  <button
                    onClick={stopStreaming}
                    className="p-2.5 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-all flex items-center justify-center flex-shrink-0"
                    title="停止生成"
                  >
                    <Square className="w-5 h-5 fill-current" />
                  </button>
                ) : (
                  <button
                    onClick={handleSend}
                    disabled={!input.trim()}
                    className={cn(
                      "p-2.5 rounded-xl transition-all flex items-center justify-center flex-shrink-0",
                      !input.trim()
                        ? "bg-slate-200 dark:bg-slate-700 text-slate-400 cursor-not-allowed"
                        : "bg-primary hover:bg-primary/90 text-slate-900 shadow-sm"
                    )}
                  >
                    <Send className="w-5 h-5" />
                  </button>
                )}
              </div>
            </div>

            <div className="mt-2 text-center">
              {isLoading ? (
                <p className="text-[10px] text-orange-600">AI 正在生成中... 点击红色按钮可停止生成</p>
              ) : (
                <p className="text-[10px] text-slate-400 dark:text-slate-500">
                  按 <span className="font-mono bg-slate-200 dark:bg-slate-700 px-1 rounded">Enter</span> 发送，<span className="font-mono bg-slate-200 dark:bg-slate-700 px-1 rounded">Shift+Enter</span> 换行。AI 可能会出错。
                </p>
              )}
            </div>
          </div>
          </div>
        </div>
      </div>
    </div>
  )
}

