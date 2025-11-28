'use client'

import { useState, useRef, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Send, Bot, User, Sparkles, Paperclip, X, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import { uploadFile, UploadProgress, fileUploadService } from '@/services/fileUploadService'
import { cn } from '@/lib/utils'

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
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { sendMessage, currentSession, createSession, isLoading } = useChatStore()

  // 获取当前会话的消息，如果没有会话则为空数组
  const messages = currentSession?.messages || []

  const handleSend = async () => {
    // 如果没有会话，先创建一个
    if (!currentSession) {
      await createSession('新对话')
    }

    if (!input.trim() || isLoading) return
    const content = input.trim()
    setInput('')
    await sendMessage(content)
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
    <div className="h-full flex flex-col bg-gradient-to-br from-blue-50 to-indigo-50">
      <div className="flex-1 max-w-6xl mx-auto w-full p-6 flex flex-col">
        {/* Header */}
        <Card className="mb-6 border-2 border-blue-200 shadow-lg">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-3 text-2xl">
              <div className="p-2 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              AI 智能助手
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-2">
              基于智谱 GLM-4 的智能数据分析助手，支持多轮对话和上下文理解
            </p>
          </CardHeader>
        </Card>

        {/* Chat Area */}
        <Card className="flex-1 flex flex-col shadow-lg">
          <CardContent className="flex-1 flex flex-col p-6">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto mb-4 space-y-4">
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
                          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
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
                <Button
                  onClick={handleSend}
                  disabled={isLoading || !input.trim()}
                  size="lg"
                  className="h-12 bg-gradient-to-br from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700"
                >
                  <Send className="w-5 h-5" />
                </Button>
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                按 Enter 发送，Shift+Enter 换行 • 支持上传 PDF、Word 文档
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

