'use client'

import { useState, useRef, useCallback, useMemo, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { Send, Bot, User, Sparkles, Paperclip, X, FileText, CheckCircle, AlertCircle, Loader2, Plus, History, Search, MessageSquare, Trash2, ChevronLeft, CheckSquare, Database, ChevronDown, AlertTriangle, Square } from 'lucide-react'
import { Markdown } from '@/components/ui/markdown'
import { useChatStore } from '@/store/chatStore'
import { useDataSourceStore, DataSourceConnection } from '@/store/dataSourceStore'
import { uploadFile, UploadProgress, fileUploadService } from '@/services/fileUploadService'
import { cn } from '@/lib/utils'
import { ChatQueryResultView } from '@/components/chat/ChatQueryResultView'
import { EChartsRenderer } from '@/components/chat/EChartsRenderer'
import { ProcessingSteps } from '@/components/chat/ProcessingSteps'
import { extractEChartsOption, removeChartMarkers } from '@/utils/chartParser'

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
  const [pendingDataSourceIds, setPendingDataSourceIds] = useState<string[]>([])
  const [dataSourceMenuOpen, setDataSourceMenuOpen] = useState(false)
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
    streamingStatus
  } = useChatStore()

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
    <div className="h-[calc(100vh-8rem)] flex bg-gradient-to-br from-blue-50 to-indigo-50 -m-6">
      {/* 历史对话侧边栏 */}
      <div className={cn(
        "h-full bg-white border-r shadow-lg transition-all duration-300 flex flex-col",
        showHistory ? "w-80" : "w-0 overflow-hidden"
      )}>
        {showHistory && (
          <>
            {/* 侧边栏头部 */}
            <div className="p-4 border-b flex-shrink-0">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-gray-800 flex items-center gap-2">
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
                <div className="flex items-center justify-between mb-3 p-2 bg-blue-50 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={filteredSessions.length > 0 && selectedSessions.size === filteredSessions.length}
                      onCheckedChange={toggleSelectAll}
                    />
                    <span className="text-sm text-gray-600">
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
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
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
                  <div className="text-center py-8 text-gray-500">
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
                          ? "bg-blue-100 border border-blue-300"
                          : session.id === currentSession?.id
                            ? "bg-blue-50 border border-blue-200"
                            : "hover:bg-gray-100"
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
                          <p className="text-xs text-gray-500 mt-1">
                            {session.messages.length} 条消息
                          </p>
                          <p className="text-xs text-gray-400">
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
                            className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-red-500"
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

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col p-6 min-h-0">
        <div className="flex-1 max-w-6xl mx-auto w-full flex flex-col min-h-0 overflow-hidden">
          {/* Header */}
          <Card className="mb-6 border-2 border-blue-200 shadow-lg flex-shrink-0">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-3 text-2xl">
                  <div className="p-2 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg">
                    <Sparkles className="w-6 h-6 text-white" />
                  </div>
                  AI 智能助手
                </CardTitle>
                <div className="flex items-center gap-2">
                  {/* 历史对话按钮 */}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowHistory(!showHistory)}
                    className="gap-2"
                  >
                    <History className="w-4 h-4" />
                    历史对话
                    {sessions.length > 0 && (
                      <span className="bg-blue-100 text-blue-700 text-xs px-1.5 py-0.5 rounded-full">
                        {sessions.length}
                      </span>
                    )}
                  </Button>
                  {/* 新建对话按钮 */}
                  <Button
                    onClick={handleStartNewConversation}
                    size="sm"
                    className="gap-2 bg-gradient-to-br from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700"
                  >
                    <Plus className="w-4 h-4" />
                    新建对话
                  </Button>
                </div>
              </div>
              <div className="flex items-center justify-between mt-3">
                <p className="text-sm text-muted-foreground">
                  基于 DeepSeek 的智能数据分析助手，支持多轮对话和上下文理解
                </p>
                {/* 数据源选择器 */}
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-muted-foreground" />
                  <DropdownMenu
                    open={dataSourceMenuOpen}
                    onOpenChange={(open) => {
                      setDataSourceMenuOpen(open)
                      if (open) {
                        setPendingDataSourceIds(selectedDataSourceIds)
                      } else {
                        setPendingDataSourceIds(selectedDataSourceIds)
                      }
                    }}
                  >
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 min-w-[240px] justify-between"
                      >
                        <div className="flex items-center gap-2 overflow-hidden">
                          <span className="truncate">{selectedDataSourceLabel}</span>
                          {selectedDataSources.length > 0 && (
                            <div className="flex items-center gap-1">
                              {selectedDataSources.slice(0, 2).map(ds => (
                                <Badge key={ds.id} variant="outline" className="text-[10px] px-1 py-0">
                                  {ds.db_type.toUpperCase()}
                                </Badge>
                              ))}
                              {selectedDataSources.length > 2 && (
                                <Badge variant="outline" className="text-[10px] px-1 py-0">
                                  +{selectedDataSources.length - 2}
                                </Badge>
                              )}
                            </div>
                          )}
                        </div>
                        <ChevronDown className="w-4 h-4 shrink-0" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      className="w-72"
                      sideOffset={6}
                      align="end"
                    >
                      <DropdownMenuLabel>选择数据源</DropdownMenuLabel>
                      <DropdownMenuCheckboxItem
                        checked={pendingDataSourceIds.length === 0}
                        onCheckedChange={() => setPendingDataSourceIds([])}
                        className="pl-2"
                        onSelect={(e) => e.preventDefault()}
                      >
                        <div className="flex items-center gap-2">
                          <Checkbox
                            checked={pendingDataSourceIds.length === 0}
                            className="pointer-events-none h-3.5 w-3.5"
                          />
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
                            checked={pendingDataSourceIds.includes(ds.id)}
                            onCheckedChange={(checked) => {
                              const isChecked = Boolean(checked)
                              setPendingDataSourceIds((prev) => {
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
                                <Checkbox
                                  checked={pendingDataSourceIds.includes(ds.id)}
                                  className="pointer-events-none h-3.5 w-3.5"
                                />
                                <span className="truncate">{ds.name}</span>
                              </div>
                              <Badge variant="outline" className="text-[10px] px-1 py-0">
                                {ds.db_type.toUpperCase()}
                              </Badge>
                            </div>
                          </DropdownMenuCheckboxItem>
                        ))
                      )}
                      <DropdownMenuSeparator />
                      <div className="flex items-center justify-end gap-2 px-2 pb-2 pt-1">
                        <Button
                          size="sm"
                          variant="secondary"
                          className="h-8"
                          onClick={() => {
                            setPendingDataSourceIds(selectedDataSourceIds)
                            setDataSourceMenuOpen(false)
                          }}
                        >
                          取消
                        </Button>
                        <Button
                          size="sm"
                          className="h-8"
                          onClick={() => {
                            setSelectedDataSourceIds(pendingDataSourceIds)
                            setDataSourceMenuOpen(false)
                          }}
                        >
                          确认
                        </Button>
                      </div>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            </CardHeader>
          </Card>

          {/* Chat Area */}
          <Card className="flex-1 flex flex-col shadow-lg min-h-0 overflow-hidden">
            <CardContent className="flex-1 flex flex-col p-6 min-h-0">
              {/* Messages */}
              <div className="flex-1 overflow-y-auto mb-4 space-y-4 min-h-0">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center">
                  <div className="p-4 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-full mb-4">
                    <Bot className="w-16 h-16 text-blue-600" />
                  </div>
                  <h3 className="text-xl font-semibold mb-2">欢迎使用 AI 智能助手</h3>
                  <p className="text-gray-600 mb-6 max-w-md">
                    我可以帮助您分析数据、回答问题、生成报告。请输入您的问题开始对话。
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl">
                    {[
                      '介绍一下你的功能',
                      '分析我的数据源',
                      '生成数据报告',
                      '查看数据洞察'
                    ].map((question, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        size="sm"
                        onClick={() => setInput(question)}
                        className="text-left justify-start"
                      >
                        <Sparkles className="w-4 h-4 mr-2" />
                        {question}
                      </Button>
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
                          ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white'
                          : 'bg-gradient-to-br from-gray-100 to-gray-200'
                      }`}>
                        {message.role === 'user' ? (
                          <User className="w-5 h-5" />
                        ) : (
                          <Bot className="w-5 h-5 text-gray-700" />
                        )}
                      </div>
                      <div className={`flex-1 max-w-[75%] ${
                        message.role === 'user' ? 'text-right' : ''
                      }`}>
                        <div className={`inline-block p-4 rounded-2xl ${
                          message.role === 'user'
                            ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white'
                            : 'bg-white border border-gray-200 shadow-sm'
                        }`}>
                          {message.role === 'user' ? (
                            <p className="text-base whitespace-pre-wrap">{message.content}</p>
                          ) : (
                            <div className="text-gray-800">
                              {/* 🔴 第三道防线：检测工具调用失败并显示警告 */}
                              {(() => {
                                const hasSystemError = message.content.includes('SYSTEM ERROR') || 
                                                       message.content.includes('无法获取数据') ||
                                                       message.content.includes('工具调用失败') ||
                                                       (message.metadata as any)?.tool_error === true ||
                                                       (message.metadata as any)?.tool_status === 'error'
                                if (hasSystemError) {
                                  return (
                                    <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
                                      <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                                      <div className="flex-1">
                                        <p className="text-sm font-medium text-red-800">数据源连接失败</p>
                                        <p className="text-xs text-red-600 mt-1">以下回答可能不准确，请检查数据源连接状态</p>
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
                                    <div className="text-xs bg-blue-50 border border-blue-200 rounded p-2">
                                      <div className="font-medium text-blue-800 mb-1">工具调用:</div>
                                      <div className="space-y-1">
                                        {(message.metadata as any).tool_calls.map((tc: any, idx: number) => (
                                          <div key={idx} className="flex items-center gap-2">
                                            <span className="text-blue-600">• {tc.name || 'unknown'}</span>
                                            {tc.status === 'error' && (
                                              <AlertTriangle className="w-3 h-3 text-red-500" />
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                  
                                  {/* 推理过程（默认展开） */}
                                  {message.metadata.reasoning && (
                                    <details open className="text-xs bg-gray-50 border border-gray-200 rounded p-2">
                                      <summary className="font-medium text-gray-700 cursor-pointer mb-1">推理过程</summary>
                                      <p className="text-gray-600 mt-1 whitespace-pre-wrap">{message.metadata.reasoning}</p>
                                    </details>
                                  )}
                                </div>
                              )}
                              
                              <Markdown content={removeChartMarkers(message.content)} className="prose-base" />
                              {/* 如果有结构化结果或图表，追加展示 */}
                              {message.metadata && (message.metadata.table || message.metadata.chart) && (
                                <ChatQueryResultView
                                  table={message.metadata.table}
                                  chart={message.metadata.chart}
                                />
                              )}
                              {/* 从消息文本中提取并渲染 ECharts 配置 */}
                              {(() => {
                                const echartsOption = extractEChartsOption(message.content)
                                if (echartsOption) {
                                  return (
                                    <EChartsRenderer
                                      echartsOption={echartsOption}
                                      title={echartsOption.title?.text || '数据可视化'}
                                    />
                                  )
                                }
                                // 如果 metadata 中有 echarts_option，也尝试渲染
                                if (message.metadata && (message.metadata as any).echarts_option) {
                                  return (
                                    <EChartsRenderer
                                      echartsOption={(message.metadata as any).echarts_option}
                                      title={(message.metadata as any).echarts_option?.title?.text || '数据可视化'}
                                    />
                                  )
                                }
                                return null
                              })()}
                              
                              {/* 显示AI推理步骤 */}
                              {message.metadata?.processing_steps && message.metadata.processing_steps.length > 0 && (
                                <ProcessingSteps
                                  steps={message.metadata.processing_steps}
                                  defaultExpanded={true}
                                />
                              )}
                            </div>
                          )}
                        </div>
                        <div className={`text-xs text-gray-500 mt-1 px-2 ${
                          message.role === 'user' ? 'text-right' : ''
                        }`}>
                          {message.timestamp.toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  ))}
                  {isLoading && (
                    <div className="flex gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
                        <Bot className="w-5 h-5 text-gray-700" />
                      </div>
                      <div className="flex-1">
                        <div className="inline-block p-4 rounded-2xl bg-white border border-gray-200 shadow-sm">
                          <div className="flex items-center gap-2">
                            <div className="flex gap-1">
                              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-75"></div>
                              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-150"></div>
                            </div>
                            <span className="text-sm text-gray-600">AI 正在思考...</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Input Area */}
            <div className="border-t pt-4">
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
                <div className="mb-3 p-2 bg-muted/50 rounded-lg">
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
                <div className="mb-3 space-y-1.5">
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
                        uploadedFile.status === 'completed' && "bg-green-50 dark:bg-green-950/20",
                        uploadedFile.status === 'error' && "bg-red-50 dark:bg-red-950/20",
                        uploadedFile.status === 'uploading' && "bg-blue-50 dark:bg-blue-950/20",
                        uploadedFile.status === 'pending' && "bg-muted/30"
                      )}
                    >
                      {uploadedFile.status === 'completed' && (
                        <CheckCircle className="h-3.5 w-3.5 text-green-600 flex-shrink-0" />
                      )}
                      {uploadedFile.status === 'error' && (
                        <AlertCircle className="h-3.5 w-3.5 text-red-600 flex-shrink-0" />
                      )}
                      {uploadedFile.status === 'uploading' && (
                        <Loader2 className="h-3.5 w-3.5 text-blue-600 animate-spin flex-shrink-0" />
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
                          className="h-auto px-1.5 py-0.5 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-100"
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

              <div className="flex gap-3 items-end">
                {/* 文件上传按钮 */}
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleFileSelect}
                  disabled={isLoading || uploadProgress?.status === 'uploading'}
                  className="h-12 w-12 flex-shrink-0"
                  title="上传文档 (PDF, Word)"
                >
                  {uploadProgress?.status === 'uploading' ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Paperclip className="h-5 w-5" />
                  )}
                </Button>

                <Textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSend()
                    }
                  }}
                  placeholder={completedUploads > 0 ? `已上传 ${completedUploads} 个文件，输入问题...` : "输入您的问题..."}
                  disabled={isLoading}
                  className="flex-1 min-h-[48px] max-h-[120px] resize-none text-base"
                  rows={1}
                />
                {isLoading ? (
                  <Button
                    onClick={stopStreaming}
                    size="lg"
                    className="h-12 bg-gradient-to-br from-red-500 to-red-600 hover:from-red-600 hover:to-red-700"
                    title="停止生成"
                  >
                    <Square className="w-5 h-5 fill-current" />
                  </Button>
                ) : (
                  <Button
                    onClick={handleSend}
                    disabled={!input.trim()}
                    size="lg"
                    className="h-12 bg-gradient-to-br from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700"
                  >
                    <Send className="w-5 h-5" />
                  </Button>
                )}
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                {isLoading ? (
                  <span className="text-orange-600">AI 正在生成中... 点击红色按钮可停止生成</span>
                ) : (
                  <span>按 Enter 发送，Shift+Enter 换行 • 支持上传 PDF、Word 文档</span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
        </div>
      </div>
    </div>
  )
}

