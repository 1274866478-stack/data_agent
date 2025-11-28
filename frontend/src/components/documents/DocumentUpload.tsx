/**
 * 文档上传组件 - Story 2.4规范实现
 * 支持拖拽上传、文件验证、进度显示、批量上传
 */

import React, { useState, useRef, useCallback } from 'react'
import { useDocumentStore } from '@/store/documentStore'
import { Button } from '@/components/ui/button'
import { Alert } from '@/components/ui/alert'
import { DocumentStatus } from '@/store/documentStore'

// 支持的文件类型
const SUPPORTED_FILE_TYPES = {
  'pdf': {
    mimeTypes: ['application/pdf'],
    extensions: ['.pdf'],
    maxSize: 50 * 1024 * 1024, // 50MB
    icon: '📄'
  },
  'docx': {
    mimeTypes: ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    extensions: ['.docx'],
    maxSize: 25 * 1024 * 1024, // 25MB
    icon: '📝'
  }
}

interface DocumentUploadProps {
  onClose?: () => void
  onSuccess?: (files: File[]) => void
  onError?: (error: string) => void
  multiple?: boolean
  maxFiles?: number
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onClose,
  onSuccess,
  onError,
  multiple = true,
  maxFiles = 10
}) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [dragActive, setDragActive] = useState(false)
  const [validationErrors, setValidationErrors] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { uploadMultipleDocuments, uploadProgress } = useDocumentStore()

  // 验证文件
  const validateFiles = useCallback((files: File[]): { valid: File[], errors: string[] } => {
    const valid: File[] = []
    const errors: string[] = []

    files.forEach((file, index) => {
      // 检查文件数量限制
      if (selectedFiles.length + valid.length + 1 > maxFiles) {
        errors.push(`最多只能上传 ${maxFiles} 个文件`)
        return
      }

      // 获取文件扩展名
      const extension = '.' + file.name.split('.').pop()?.toLowerCase()

      // 检查文件类型
      const fileType = Object.entries(SUPPORTED_FILE_TYPES).find(([_, config]) =>
        config.extensions.includes(extension)
      )

      if (!fileType) {
        errors.push(`文件 "${file.name}" 格式不支持，仅支持 PDF 和 Word 文档`)
        return
      }

      const config = SUPPORTED_FILE_TYPES[fileType[0] as keyof typeof SUPPORTED_FILE_TYPES]

      // 检查MIME类型
      if (!config.mimeTypes.includes(file.type)) {
        errors.push(`文件 "${file.name}" 的MIME类型不匹配`)
        return
      }

      // 检查文件大小
      if (file.size > config.maxSize) {
        errors.push(`文件 "${file.name}" 大小超过限制 (${config.maxSize / 1024 / 1024}MB)`)
        return
      }

      valid.push(file)
    })

    return { valid, errors }
  }, [selectedFiles.length, maxFiles])

  // 处理文件选择
  const handleFiles = useCallback((files: FileList) => {
    const fileArray = Array.from(files)
    const { valid, errors } = validateFiles(fileArray)

    setValidationErrors(errors)

    if (valid.length > 0) {
      setSelectedFiles(prev => [...prev, ...valid])
    }
  }, [validateFiles])

  // 拖拽处理
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files)
    }
  }, [handleFiles])

  // 文件选择处理
  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files)
    }
  }

  // 移除文件
  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index))
  }

  // 上传文件
  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      onError?.('请选择要上传的文件')
      return
    }

    try {
      if (selectedFiles.length === 1) {
        await useDocumentStore.getState().uploadDocument(selectedFiles[0])
      } else {
        await uploadMultipleDocuments(selectedFiles)
      }

      onSuccess?.(selectedFiles)
      setSelectedFiles([])
      setValidationErrors([])

      // 如果有 onClose 回调，延迟关闭以显示上传成功状态
      setTimeout(() => {
        onClose?.()
      }, 1000)

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '上传失败'
      onError?.(errorMessage)
    }
  }

  // 获取文件图标
  const getFileIcon = (file: File) => {
    const extension = '.' + file.name.split('.').pop()?.toLowerCase()
    const fileType = Object.entries(SUPPORTED_FILE_TYPES).find(([_, config]) =>
      config.extensions.includes(extension)
    )
    return fileType ? SUPPORTED_FILE_TYPES[fileType[0] as keyof typeof SUPPORTED_FILE_TYPES].icon : '📄'
  }

  // 获取上传进度
  const getUploadProgress = (file: File) => {
    const uploadId = `${file.name}_${Date.now()}`
    // 简化实现，实际应该有更精确的进度跟踪
    return Object.values(uploadProgress).find(progress =>
      progress.status !== 'completed' && progress.status !== 'error'
    )?.progress || 0
  }

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      {/* 标题 */}
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xl font-semibold text-gray-900">上传文档</h3>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-500 transition-colors"
          >
            ✕
          </button>
        )}
      </div>

      {/* 拖拽上传区域 */}
      <div
        className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive
            ? 'border-blue-400 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple={multiple}
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={handleFileInput}
          className="hidden"
        />

        <div className="space-y-4">
          <div className="text-6xl">📁</div>
          <div>
            <p className="text-lg font-medium text-gray-900">
              拖拽文件到这里，或者点击选择文件
            </p>
            <p className="text-sm text-gray-500 mt-1">
              支持 PDF 和 Word 文档，最大 50MB
            </p>
          </div>
          <Button
            onClick={() => fileInputRef.current?.click()}
            variant="outline"
          >
            选择文件
          </Button>
        </div>
      </div>

      {/* 验证错误 */}
      {validationErrors.length > 0 && (
        <div className="mt-4">
          {validationErrors.map((error, index) => (
            <Alert key={index} variant="destructive" className="mb-2">
              {error}
            </Alert>
          ))}
        </div>
      )}

      {/* 已选择的文件列表 */}
      {selectedFiles.length > 0 && (
        <div className="mt-6">
          <h4 className="text-lg font-medium text-gray-900 mb-4">
            已选择文件 ({selectedFiles.length})
          </h4>
          <div className="space-y-2">
            {selectedFiles.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center space-x-3 flex-1">
                  <span className="text-2xl">{getFileIcon(file)}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  {getUploadProgress(file) > 0 && (
                    <div className="flex-1 max-w-xs">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${getUploadProgress(file)}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {getUploadProgress(file)}% 完成
                      </p>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => removeFile(index)}
                  className="ml-3 text-red-500 hover:text-red-700 transition-colors"
                  disabled={getUploadProgress(file) > 0 && getUploadProgress(file) < 100}
                >
                  删除
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 上传限制提示 */}
      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <h5 className="text-sm font-medium text-blue-900 mb-1">上传限制</h5>
        <ul className="text-xs text-blue-700 space-y-1">
          <li>• 支持格式：PDF (.pdf)、Word 文档 (.docx)</li>
          <li>• 文件大小：PDF 最大 50MB，Word 最大 25MB</li>
          <li>• 最多上传 {maxFiles} 个文件</li>
          <li>• 文件将安全存储并自动进行处理</li>
        </ul>
      </div>

      {/* 操作按钮 */}
      <div className="flex justify-end space-x-3 mt-6">
        {onClose && (
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
        )}
        <Button
          onClick={handleUpload}
          disabled={selectedFiles.length === 0}
        >
          上传文件 ({selectedFiles.length})
        </Button>
      </div>
    </div>
  )
}

export default DocumentUpload