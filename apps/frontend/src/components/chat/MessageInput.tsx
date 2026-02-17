/**
 * # [MESSAGE_INPUT] 聊天消息输入组件
 *
 * ## [MODULE]
 * **文件名**: MessageInput.tsx
 * **职责**: 提供聊天消息输入界面 - 文本输入、文件上传、拖拽支持、发送控制
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * Props:
 * - **placeholder?: string** - 输入框占位符文本（默认'输入您的问题...'）
 * - **maxLength?: number** - 最大字符长度（默认2000）
 * - **disabled?: boolean** - 是否禁用输入
 * - **onFileAttach?: (files: File[]) => void** - 文件附加回调
 * - **onDocumentUploaded?: (document: any) => void** - 文档上传完成回调
 *
 * ## [OUTPUT]
 * UI组件:
 * - **文本输入框**: 自动调整高度的多行文本输入（最大120px）
 * - **文件上传区**: 支持点击和拖拽上传
 * - **已上传文件列表**: 显示上传进度和状态
 * - **发送/停止按钮**: 根据状态切换发送或停止生成
 * - **快捷键**: Enter发送，Shift+Enter换行，Escape清空
 *
 * ## [LINK]
 * **上游依赖**:
 * - [../../store/chatStore.ts](../../store/chatStore.ts) - 聊天状态管理
 * - [../../services/fileUploadService.ts](../../services/fileUploadService.ts) - 文件上传服务
 * - [../ui/button.tsx](../ui/button.tsx) - 按钮组件
 * - [../ui/textarea.tsx](../ui/textarea.tsx) - 文本域组件
 * - lucide-react - 图标库
 *
 * **下游依赖**:
 * - [./ChatInterface.tsx](./ChatInterface.tsx) - 父组件调用
 *
 * **调用方**:
 * - ChatInterface聊天界面
 *
 * ## [STATE]
 * - **input: string** - 输入的文本内容
 * - **uploadProgress: UploadProgress | null** - 文件上传进度
 * - **uploadedFiles: UploadedFile[]** - 已上传的文件列表
 * - **isDragOver: boolean** - 拖拽悬停状态
 *
 * ## [SIDE-EFFECTS]
 * - **副作用1**: 调用chatStore.sendMessage发送消息
 * - **副作用2**: 调用fileUploadService上传文件
 * - **副作用3**: 触发onFileAttach和onDocumentUploaded回调
 * - **副作用4**: 自动调整文本域高度
 * - **副作用5**: 聚焦和清空输入框
 */

'use client'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { fileUploadService, uploadFile, UploadProgress } from '@/services/fileUploadService'
import { useChatStore } from '@/store/chatStore'
import { AlertCircle, CheckCircle, FileText, Loader2, Mic, Paperclip, Send, Square, Upload, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

interface MessageInputProps {
  placeholder?: string
  maxLength?: number
  disabled?: boolean
  onFileAttach?: (files: File[]) => void
  onDocumentUploaded?: (document: any) => void
}

interface UploadedFile {
  file: File
  document?: any
  status: 'pending' | 'uploading' | 'completed' | 'error'
  error?: string
}

export function MessageInput({
  placeholder = 'Ask a follow-up question...',
  maxLength = 2000,
  disabled = false,
  onFileAttach,
  onDocumentUploaded
}: MessageInputProps) {
  const [input, setInput] = useState('')
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null)
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { sendMessage, isLoading, isTyping, currentSession } = useChatStore()

  // 自动调整文本域高度
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
    }
  }, [input])

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    } else if (e.key === 'Escape') {
      setInput('')
      textareaRef.current?.focus()
    }
  }

  // 发送消息
  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const messageContent = input.trim()
    setInput('')

    // 重置文本域高度
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    await sendMessage(messageContent)
  }

  // 处理文件拖拽
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)
  }, [])

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

    // 支持多文件上传
    for (const file of files) {
      // 验证文件
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

      // 创建上传文件记录
      const uploadedFile: UploadedFile = {
        file,
        status: 'uploading',
      }
      setUploadedFiles(prev => [...prev, uploadedFile])

      // 设置上传进度
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
          // 更新已上传文件状态
          setUploadedFiles(prev =>
            prev.map(f =>
              f.file === file
                ? { ...f, status: 'completed' as const, document: result.document }
                : f
            )
          )

          // 通知父组件
          onFileAttach?.([file])
          onDocumentUploaded?.(result.document)

          // 清除上传进度
          setTimeout(() => setUploadProgress(null), 1500)
        } else {
          // 更新失败状态
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

  // 处理拖拽放置
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)

    const files = Array.from(e.dataTransfer.files)
    handleFileUpload(files)
  }, [])

  // 移除已上传的文件
  const removeUploadedFile = useCallback((index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index))
  }, [])

  // 重试上传失败的文件
  const retryUpload = useCallback((index: number) => {
    const uploadedFile = uploadedFiles[index]
    if (uploadedFile && uploadedFile.status === 'error') {
      // 先移除失败的记录
      setUploadedFiles(prev => prev.filter((_, i) => i !== index))
      // 重新上传
      handleFileUpload([uploadedFile.file])
    }
  }, [uploadedFiles])

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
    // 重置 input 以允许选择相同的文件
    e.target.value = ''
  }, [])
  const isSendDisabled = !input.trim() || isLoading || disabled || uploadProgress?.status === 'uploading'

  // 获取已完成上传的文件数量
  const completedUploads = uploadedFiles.filter(f => f.status === 'completed').length

  return (
    <div className="absolute bottom-0 left-0 w-full p-6 bg-gradient-to-t from-background-light via-background-light to-transparent dark:from-background-dark dark:via-background-dark pointer-events-none">
      {/* 隐藏的文件输入 */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        multiple
        onChange={handleFileInputChange}
      />

      <div className="max-w-4xl mx-auto pointer-events-auto">
        {/* 拖拽区域指示器 */}
        {isDragOver && (
          <div className="mb-3 p-6 border-2 border-dashed border-primary rounded-2xl bg-primary/5 text-center">
            <Upload className="h-8 w-8 mx-auto mb-2 text-primary" />
            <p className="text-sm text-teal-700 dark:text-teal-300 font-medium">Drop files to upload</p>
            <p className="text-xs text-muted-foreground">Supports PDF, Word documents</p>
          </div>
        )}

        {/* 玻璃态输入容器 */}
        <div className="glass rounded-2xl shadow-glow p-2.5 flex items-end gap-2 ring-1 ring-primary-200/50 dark:ring-primary-500/30 backdrop-blur-xl">
          {/* 附件按钮 */}
          <button
            onClick={handleFileSelect}
            disabled={isLoading || disabled || uploadProgress?.status === 'uploading'}
            className="p-3 text-slate-400 hover:text-primary transition-colors rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800"
            title="上传文档 (PDF, Word)"
          >
            {uploadProgress?.status === 'uploading' ? (
              <Upload className="h-5 w-5 animate-spin" />
            ) : (
              <Paperclip className="h-5 w-5" />
            )}
          </button>

          {/* 输入区域 */}
          <div
            className={cn(
              "flex-1 relative",
              isDragOver && "ring-2 ring-primary ring-offset-2 rounded-xl"
            )}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={completedUploads > 0 ? `已上传 ${completedUploads} 个文件，输入问题...` : placeholder}
              maxLength={maxLength}
              disabled={disabled || isLoading}
              className="w-full bg-transparent border-0 focus:ring-0 text-slate-800 dark:text-slate-100 placeholder-slate-400/70 py-3 px-2 resize-none leading-relaxed outline-none font-body text-base"
              rows={1}
              style={{ minHeight: '48px' }}
            />
          </div>

          {/* 右侧按钮组 */}
          <div className="flex items-center gap-1">
            {/* 麦克风按钮 */}
            <button className="p-2 text-slate-400 hover:text-primary transition-colors rounded-lg">
              <Mic className="h-5 w-5" />
            </button>
            
            {/* 发送按钮 */}
            {isLoading ? (
              <button
                onClick={() => {
                  // 停止生成逻辑
                }}
                className="p-3 bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-opacity-90 transition-all flex items-center justify-center"
                title="停止生成"
              >
                <Square className="h-5 w-5" />
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={isSendDisabled}
                className={cn(
                  "p-3 rounded-xl transition-all duration-200 flex items-center justify-center",
                  isSendDisabled
                    ? "bg-slate-200 dark:bg-slate-700 text-slate-400 cursor-not-allowed"
                    : "btn-datalab hover:scale-105 active:scale-95 shadow-glow hover:shadow-glow-lg"
                )}
                title={isSendDisabled ? '输入消息后发送' : '发送消息'}
              >
                <Send className="h-5 w-5" />
              </button>
            )}
          </div>
        </div>

        {/* 文件上传进度 */}
        {uploadProgress && (
          <div className="mt-2 p-2 bg-muted/50 rounded-lg">
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
              <div className="text-xs text-green-600">
                ✓ {uploadProgress.message}
              </div>
            )}

            {uploadProgress.status === 'error' && (
              <div className="text-xs text-destructive">
                ✗ {uploadProgress.message}
              </div>
            )}
          </div>
        )}

        {/* 已上传文件列表 */}
        {uploadedFiles.length > 0 && (
          <div className="mt-3 space-y-1.5">
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
                {/* 状态图标 */}
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

                {/* 文件名 */}
                <span className="flex-1 truncate">{uploadedFile.file.name}</span>

                {/* 文件大小 */}
                <span className="text-muted-foreground flex-shrink-0">
                  {fileUploadService.formatFileSize(uploadedFile.file.size)}
                </span>

                {/* 操作按钮 */}
                {uploadedFile.status === 'error' ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => retryUpload(index)}
                    className="h-auto px-1.5 py-0.5 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-100"
                  >
                    重试
                  </Button>
                ) : null}

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

            {/* 上传失败提示 */}
            {uploadedFiles.some(f => f.status === 'error') && (
              <div className="text-xs text-red-600 flex items-center gap-1 mt-1">
                <AlertCircle className="h-3 w-3" />
                <span>部分文件上传失败，点击&quot;重试&quot;重新上传</span>
              </div>
            )}
          </div>
        )}

        {/* 提示信息 */}
        <div className="text-center mt-3">
          <p className="text-[10px] text-slate-400 dark:text-slate-500">
            按 <span className="font-mono bg-slate-200 dark:bg-slate-700 px-1 rounded">Enter</span> 发送，<span className="font-mono bg-slate-200 dark:bg-slate-700 px-1 rounded">Shift+Enter</span> 换行。AI 可能会出错。
          </p>
        </div>

        {/* 输入状态指示 */}
        {isTyping && (
          <div className="mt-2 text-xs text-muted-foreground flex items-center gap-1">
            <div className="flex gap-1">
              <div className="w-1 h-1 bg-current rounded-full animate-pulse"></div>
              <div className="w-1 h-1 bg-current rounded-full animate-pulse delay-75"></div>
              <div className="w-1 h-1 bg-current rounded-full animate-pulse delay-150"></div>
            </div>
            AI 正在输入...
          </div>
        )}
      </div>
    </div>
  )
}