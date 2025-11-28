/**
 * 文档卡片组件 - Story 2.4规范实现
 * 显示文档信息、状态指示器、快速操作按钮、预览功能
 */

import React, { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { useDocumentStore, DocumentStatus, KnowledgeDocument } from '@/store/documentStore'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface DocumentCardProps {
  document: KnowledgeDocument
  isSelected?: boolean
  onSelectionChange?: (selected: boolean) => void
  showSelection?: boolean
}

export const DocumentCard: React.FC<DocumentCardProps> = ({
  document,
  isSelected = false,
  onSelectionChange,
  showSelection = false
}) => {
  const [isLoading, setIsLoading] = useState(false)
  const [showActions, setShowActions] = useState(false)

  const {
    deleteDocument,
    getDocumentPreviewUrl,
    getDocumentDownloadUrl,
    processDocument,
    openPreviewModal
  } = useDocumentStore()

  // 获取文件图标和颜色
  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'pdf':
        return { icon: '📄', color: 'text-red-500' }
      case 'docx':
        return { icon: '📝', color: 'text-blue-500' }
      default:
        return { icon: '📄', color: 'text-gray-500' }
    }
  }

  // 获取状态信息
  const getStatusInfo = (status: DocumentStatus) => {
    switch (status) {
      case DocumentStatus.PENDING:
        return {
          text: '等待处理',
          color: 'bg-yellow-100 text-yellow-800',
          icon: '⏳'
        }
      case DocumentStatus.INDEXING:
        return {
          text: '正在处理',
          color: 'bg-blue-100 text-blue-800',
          icon: '🔄'
        }
      case DocumentStatus.READY:
        return {
          text: '处理完成',
          color: 'bg-green-100 text-green-800',
          icon: '✅'
        }
      case DocumentStatus.ERROR:
        return {
          text: '处理失败',
          color: 'bg-red-100 text-red-800',
          icon: '❌'
        }
      default:
        return {
          text: '未知状态',
          color: 'bg-gray-100 text-gray-800',
          icon: '❓'
        }
    }
  }

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // 处理预览
  const handlePreview = async () => {
    if (document.status !== DocumentStatus.READY) {
      return
    }

    setIsLoading(true)
    try {
      openPreviewModal(document)
    } catch (error) {
      console.error('Preview failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // 处理下载
  const handleDownload = async () => {
    setIsLoading(true)
    try {
      const downloadUrl = await getDocumentDownloadUrl(document.id)
      const link = window.document.createElement('a')
      link.href = downloadUrl
      link.download = document.file_name
      window.document.body.appendChild(link)
      link.click()
      window.document.body.removeChild(link)
    } catch (error) {
      console.error('Download failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // 处理删除
  const handleDelete = async () => {
    if (!window.confirm(`确定要删除文档 "${document.file_name}" 吗？`)) {
      return
    }

    setIsLoading(true)
    try {
      await deleteDocument(document.id)
    } catch (error) {
      console.error('Delete failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // 手动处理文档
  const handleProcess = async () => {
    setIsLoading(true)
    try {
      await processDocument(document.id)
    } catch (error) {
      console.error('Process failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const fileIcon = getFileIcon(document.file_type)
  const statusInfo = getStatusInfo(document.status)
  const canPreview = document.status === DocumentStatus.READY
  const canProcess = document.status === DocumentStatus.PENDING

  return (
    <div
      className={`
        relative bg-white border rounded-lg p-4 hover:shadow-md transition-all duration-200
        ${isSelected ? 'border-blue-500 shadow-md' : 'border-gray-200'}
        ${showActions ? 'ring-2 ring-blue-200' : ''}
      `}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* 选择框 */}
      {showSelection && onSelectionChange && (
        <div className="absolute top-3 left-3 z-10">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={(e) => onSelectionChange(e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
        </div>
      )}

      {/* 文档信息 */}
      <div className="flex items-start space-x-3">
        <div className={`text-3xl ${fileIcon.color}`}>
          {fileIcon.icon}
        </div>

        <div className="flex-1 min-w-0">
          {/* 文件名 */}
          <h3 className="text-lg font-medium text-gray-900 truncate" title={document.file_name}>
            {document.file_name}
          </h3>

          {/* 状态标签 */}
          <div className="mt-1 flex items-center space-x-2">
            <Badge className={statusInfo.color}>
              <span className="mr-1">{statusInfo.icon}</span>
              {statusInfo.text}
            </Badge>
            <span className="text-xs text-gray-500">
              {document.file_type.toUpperCase()}
            </span>
          </div>

          {/* 文件信息 */}
          <div className="mt-2 text-xs text-gray-500 space-y-1">
            <div>大小: {formatFileSize(document.file_size)}</div>
            <div>
              上传时间: {formatDistanceToNow(new Date(document.created_at), {
                addSuffix: true,
                locale: zhCN
              })}
            </div>
            {document.indexed_at && (
              <div>
                完成时间: {formatDistanceToNow(new Date(document.indexed_at), {
                  addSuffix: true,
                  locale: zhCN
                })}
              </div>
            )}
          </div>

          {/* 处理错误信息 */}
          {document.processing_error && (
            <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
              错误: {document.processing_error}
            </div>
          )}
        </div>

        {/* 快速操作按钮 */}
        <div className={`
          flex flex-col space-y-2 transition-opacity duration-200
          ${showActions ? 'opacity-100' : 'opacity-0'}
        `}>
          {canPreview && (
            <Button
              size="sm"
              variant="outline"
              onClick={handlePreview}
              disabled={isLoading}
              title="预览文档"
            >
              👁️
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={handleDownload}
            disabled={isLoading}
            title="下载文档"
          >
              ⬇️
            </Button>
          {canProcess && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleProcess}
              disabled={isLoading}
              title="处理文档"
            >
              🔄
            </Button>
          )}
        </div>
      </div>

      {/* 底部操作栏 */}
      <div className="mt-4 pt-4 border-t border-gray-100 flex justify-between items-center">
        <div className="text-xs text-gray-400">
          ID: {document.id.slice(0, 8)}...
        </div>

        {/* 详细操作菜单 */}
        <div className="flex space-x-2">
          {canPreview && (
            <Button
              size="sm"
              variant="ghost"
              onClick={handlePreview}
              disabled={isLoading}
              className="text-blue-600 hover:text-blue-700"
            >
              预览
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={handleDownload}
            disabled={isLoading}
            className="text-green-600 hover:text-green-700"
          >
            下载
          </Button>
          {canProcess && (
            <Button
              size="sm"
              variant="ghost"
              onClick={handleProcess}
              disabled={isLoading}
              className="text-blue-600 hover:text-blue-700"
            >
              处理
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={handleDelete}
            disabled={isLoading}
            className="text-red-600 hover:text-red-700"
          >
            删除
          </Button>
        </div>
      </div>

      {/* 加载状态覆盖 */}
      {isLoading && (
        <div className="absolute inset-0 bg-white bg-opacity-50 flex items-center justify-center rounded-lg">
          <div className="text-blue-600">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DocumentCard