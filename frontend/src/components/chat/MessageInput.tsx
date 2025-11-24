'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Square, Paperclip, Upload, X, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useChatStore } from '@/store/chatStore'
import { uploadFile, UploadProgress } from '@/services/fileUploadService'

interface MessageInputProps {
  placeholder?: string
  maxLength?: number
  disabled?: boolean
  onFileAttach?: (files: File[]) => void
  onDocumentUploaded?: (document: any) => void
}

export function MessageInput({
  placeholder = '输入您的问题...',
  maxLength = 2000,
  disabled = false,
  onFileAttach,
  onDocumentUploaded
}: MessageInputProps) {
  const [input, setInput] = useState('')
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const textareaRef = useRef<HTMLTextAreaElement>(null)

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
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()

    const files = Array.from(e.dataTransfer.files)
    handleFileUpload(files)
  }

  // 处理文件上传
  const handleFileUpload = async (files: File[]) => {
    if (files.length === 0) return

    const file = files[0] // 目前只支持单个文件上传

    // 设置上传进度
    setUploadProgress({
      loaded: 0,
      total: file.size,
      percentage: 0,
      status: 'pending',
      message: '准备上传...',
    })

    try {
      const result = await uploadFile(file, (progress) => {
        setUploadProgress(progress)
      })

      if (result.success && result.document) {
        // 添加到已上传文件列表
        setUploadedFiles(prev => [...prev, file])

        // 通知父组件
        onFileAttach?.([file])
        onDocumentUploaded?.(result.document)

        // 清除上传进度（延迟一下让用户看到完成状态）
        setTimeout(() => {
          setUploadProgress(null)
        }, 2000)
      } else {
        // 上传失败，显示错误信息
        setUploadProgress(prev => prev ? {
          ...prev,
          status: 'error',
          message: result.error || '上传失败',
        } : null)

        // 延迟清除错误状态
        setTimeout(() => {
          setUploadProgress(null)
        }, 5000)
      }
    } catch (error) {
      setUploadProgress({
        loaded: 0,
        total: file.size,
        percentage: 0,
        status: 'error',
        message: error instanceof Error ? error.message : '上传过程中发生错误',
      })

      setTimeout(() => {
        setUploadProgress(null)
      }, 5000)
    }
  }

  // 移除已上传的文件
  const removeUploadedFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index))
  }

  // 通过文件选择器上传文件
  const handleFileSelect = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.multiple = false
    input.accept = '.pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document'

    input.onchange = (e) => {
      const files = Array.from((e.target as HTMLInputElement).files || [])
      handleFileUpload(files)
    }

    input.click()
  }

  const isSendDisabled = !input.trim() || isLoading || disabled || uploadProgress?.status === 'uploading'

  // 调试信息
  useEffect(() => {
    const debugInfo = {
      input,
      inputLength: input.length,
      inputTrimmed: input.trim(),
      inputTrimmedLength: input.trim().length,
      isLoading,
      disabled,
      uploadProgress,
      isSendDisabled,
      currentSession: currentSession?.id,
      hasCurrentSession: !!currentSession,
      disabledReasons: {
        emptyInput: !input.trim(),
        loading: isLoading,
        componentDisabled: disabled,
        uploading: uploadProgress?.status === 'uploading'
      }
    }
    console.log('MessageInput 状态:', debugInfo)

    // 如果按钮被禁用但输入不为空，记录警告
    if (isSendDisabled && input.trim().length > 0) {
      console.warn('⚠️ 按钮被禁用但输入不为空！', debugInfo)
    }
  }, [input, isLoading, disabled, uploadProgress, isSendDisabled, currentSession])

  return (
    <div className="border-t bg-background p-4">
      {/* 开发环境调试面板 - 始终显示 */}
      <div className="max-w-4xl mx-auto mb-2 p-3 bg-yellow-50 border-2 border-yellow-400 rounded-lg text-xs space-y-1 shadow-lg">
        <div className="font-bold text-base mb-2">🔍 调试信息面板</div>
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-white p-2 rounded">
            <strong>输入内容:</strong> "{input}"
          </div>
          <div className="bg-white p-2 rounded">
            <strong>输入长度:</strong> {input.length}
          </div>
          <div className="bg-white p-2 rounded">
            <strong>Trim后:</strong> "{input.trim()}"
          </div>
          <div className="bg-white p-2 rounded">
            <strong>Trim长度:</strong> {input.trim().length}
          </div>
          <div className="bg-white p-2 rounded">
            <strong>isLoading:</strong> {isLoading ? '✅ 是' : '❌ 否'}
          </div>
          <div className="bg-white p-2 rounded">
            <strong>disabled:</strong> {disabled ? '✅ 是' : '❌ 否'}
          </div>
          <div className="bg-white p-2 rounded">
            <strong>currentSession:</strong> {currentSession?.id || '❌ 无'}
          </div>
          <div className="bg-white p-2 rounded">
            <strong>uploadProgress:</strong> {uploadProgress?.status || '无'}
          </div>
        </div>
        <div className={`mt-2 p-2 rounded text-center font-bold text-base ${isSendDisabled ? 'bg-red-200 text-red-800' : 'bg-green-200 text-green-800'}`}>
          按钮状态: {isSendDisabled ? '🔒 禁用' : '✅ 可用'}
        </div>
        {isSendDisabled && (
          <div className="mt-2 p-2 bg-red-100 rounded">
            <strong>禁用原因:</strong>
            <ul className="list-disc list-inside mt-1">
              {!input.trim() && <li>输入为空</li>}
              {isLoading && <li>正在加载</li>}
              {disabled && <li>组件被禁用</li>}
              {uploadProgress?.status === 'uploading' && <li>正在上传文件</li>}
            </ul>
          </div>
        )}
      </div>

      <div className="max-w-4xl mx-auto">
        <div className="flex gap-3">
          {/* 文件上传按钮 */}
          <div className="flex-shrink-0">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleFileSelect}
              disabled={isLoading || disabled || uploadProgress?.status === 'uploading'}
              className="h-10 w-10 p-0"
              title="上传文档 (PDF, Word)"
            >
              {uploadProgress?.status === 'uploading' ? (
                <div className="animate-spin">
                  <Upload className="h-4 w-4" />
                </div>
              ) : (
                <Paperclip className="h-4 w-4" />
              )}
            </Button>
          </div>

          {/* 输入区域 */}
          <div className="flex-1 relative">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => {
                console.log('Textarea onChange 触发:', e.target.value)
                setInput(e.target.value)
              }}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              maxLength={maxLength}
              disabled={disabled || isLoading}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              className="min-h-[40px] max-h-[120px] resize-none pr-12 py-3"
              rows={1}
            />

            {/* 字符计数 */}
            {maxLength && (
              <div className="absolute bottom-2 right-14 text-xs text-muted-foreground">
                {input.length}/{maxLength}
              </div>
            )}
          </div>

          {/* 发送/停止按钮 */}
          <div className="flex-shrink-0 flex flex-col items-center gap-1">
            {isLoading ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  // 这里可以添加停止API调用的逻辑
                }}
                disabled={false}
                className="h-10 px-3"
              >
                <Square className="h-4 w-4" />
                <span className="sr-only">停止生成</span>
              </Button>
            ) : (
              <>
                <Button
                  size="sm"
                  onClick={() => {
                    console.log('发送按钮被点击')
                    handleSend()
                  }}
                  disabled={isSendDisabled}
                  className="h-10 px-3"
                  title={isSendDisabled ? `按钮禁用原因: ${!input.trim() ? '输入为空' : isLoading ? '正在加载' : disabled ? '组件禁用' : '上传中'}` : '发送消息'}
                >
                  <Send className="h-4 w-4" />
                  <span className="sr-only">发送消息</span>
                </Button>
                {/* 调试信息 - 开发环境显示 */}
                {process.env.NODE_ENV === 'development' && (
                  <div className="text-[10px] text-gray-500">
                    {isSendDisabled ? '🔒' : '✅'}
                  </div>
                )}
              </>
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
          <div className="mt-2 space-y-1">
            <div className="text-xs text-muted-foreground mb-1">已上传文件：</div>
            {uploadedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center gap-2 p-2 bg-muted/30 rounded text-xs"
              >
                <FileText className="h-3 w-3 text-muted-foreground" />
                <span className="flex-1 truncate">{file.name}</span>
                <span className="text-muted-foreground">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeUploadedFile(index)}
                  className="h-auto p-0 text-xs text-muted-foreground hover:text-destructive"
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        )}

        {/* 提示信息 */}
        <div className="mt-2 text-xs text-muted-foreground">
          按 <kbd className="px-1 py-0.5 text-xs bg-muted rounded">Enter</kbd> 发送，
          <kbd className="px-1 py-0.5 text-xs bg-muted rounded mx-1">Shift + Enter</kbd> 换行，
          <kbd className="px-1 py-0.5 text-xs bg-muted rounded mx-1">Escape</kbd> 清空
          {uploadedFiles.length > 0 && (
            <span className="ml-2">
              • 支持 PDF、Word 文档拖拽上传
            </span>
          )}
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