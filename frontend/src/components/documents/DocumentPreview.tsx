/**
 * 文档预览组件 - Story 2.4规范实现
 * PDF和Word文档预览、缩放控制、下载功能
 */

import React, { useState, useEffect, useRef } from 'react'
import { useDocumentStore, KnowledgeDocument } from '@/store/documentStore'
import { Button } from '@/components/ui/button'
import { Alert } from '@/components/ui/alert'

interface DocumentPreviewProps {
  document: KnowledgeDocument
  onClose?: () => void
}

export const DocumentPreview: React.FC<DocumentPreviewProps> = ({
  document,
  onClose
}) => {
  const [previewUrl, setPreviewUrl] = useState<string>('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [zoom, setZoom] = useState(100)
  const [rotation, setRotation] = useState(0)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  const { getDocumentPreviewUrl, getDocumentDownloadUrl } = useDocumentStore()

  // 加载预览
  useEffect(() => {
    loadPreview()
  }, [])

  const loadPreview = async () => {
    setIsLoading(true)
    setError('')

    try {
      const url = await getDocumentPreviewUrl(document.id, 2) // 2小时有效期
      setPreviewUrl(url)
    } catch (error) {
      console.error('Preview load failed:', error)
      setError(error instanceof Error ? error.message : '加载预览失败')
    } finally {
      setIsLoading(false)
    }
  }

  // 处理缩放
  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 25, 200))
  }

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 25, 25))
  }

  const handleResetZoom = () => {
    setZoom(100)
  }

  // 处理旋转
  const handleRotate = () => {
    setRotation(prev => (prev + 90) % 360)
  }

  // 处理下载
  const handleDownload = async () => {
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
      setError('下载失败')
    }
  }

  // 获取文档类型图标
  const getDocumentIcon = () => {
    switch (document.file_type) {
      case 'pdf':
        return '📄'
      case 'docx':
        return '📝'
      default:
        return '📄'
    }
  }

  // PDF预览样式
  const getPreviewStyle = () => {
    return {
      transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
      transition: 'transform 0.3s ease-in-out',
      transformOrigin: 'center'
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] flex flex-col">
        {/* 头部工具栏 */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">{getDocumentIcon()}</span>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 truncate max-w-md">
                {document.file_name}
              </h3>
              <p className="text-sm text-gray-500">
                {(document.file_size / 1024 / 1024).toFixed(2)} MB • {document.file_type.toUpperCase()}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {/* 缩放控制 */}
            <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
              <Button
                size="sm"
                variant="ghost"
                onClick={handleZoomOut}
                disabled={zoom <= 25}
                title="缩小"
              >
                ➖
              </Button>
              <span className="px-2 text-sm font-medium min-w-[3rem] text-center">
                {zoom}%
              </span>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleZoomIn}
                disabled={zoom >= 200}
                title="放大"
              >
                ➕
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleResetZoom}
                title="重置缩放"
              >
                🔄
              </Button>
            </div>

            {/* 旋转控制 - 仅PDF支持 */}
            {document.file_type === 'pdf' && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleRotate}
                title="旋转"
              >
                🔄
              </Button>
            )}

            {/* 下载按钮 */}
            <Button
              size="sm"
              variant="outline"
              onClick={handleDownload}
              title="下载文档"
            >
              ⬇️ 下载
            </Button>

            {/* 关闭按钮 */}
            <Button
              size="sm"
              variant="ghost"
              onClick={onClose}
              title="关闭预览"
            >
              ✕
            </Button>
          </div>
        </div>

        {/* 预览内容区域 */}
        <div className="flex-1 overflow-auto p-4 bg-gray-50">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-96 space-y-4">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <p className="text-gray-600">正在加载预览...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-96 space-y-4">
              <div className="text-6xl">❌</div>
              <Alert variant="destructive">
                <p className="font-medium">预览加载失败</p>
                <p className="text-sm mt-1">{error}</p>
              </Alert>
              <Button onClick={loadPreview} variant="outline">
                重试
              </Button>
            </div>
          ) : (
            <div className="flex justify-center">
              {document.file_type === 'pdf' ? (
                // PDF预览
                <div className="relative">
                  <iframe
                    ref={iframeRef}
                    src={previewUrl}
                    className="border border-gray-300 rounded shadow-lg"
                    style={{
                      width: '800px',
                      height: '600px',
                      ...getPreviewStyle()
                    }}
                    title={`PDF预览: ${document.file_name}`}
                  />
                </div>
              ) : (
                // Word文档预览 - 由于浏览器限制，显示下载提示
                <div className="text-center space-y-6 py-12">
                  <div className="text-6xl">📝</div>
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                      Word 文档预览
                    </h3>
                    <p className="text-gray-600 mb-4">
                      浏览器不支持直接预览 Word 文档，请下载后查看
                    </p>
                  </div>
                  <div className="space-y-4">
                    <div className="bg-gray-100 p-4 rounded-lg max-w-md mx-auto">
                      <h4 className="font-medium text-gray-900 mb-2">文档信息</h4>
                      <div className="text-sm text-gray-600 space-y-1">
                        <p>文件名: {document.file_name}</p>
                        <p>文件大小: {(document.file_size / 1024 / 1024).toFixed(2)} MB</p>
                        <p>文件类型: Word 文档</p>
                        <p>上传时间: {new Date(document.created_at).toLocaleString()}</p>
                      </div>
                    </div>
                    <Button onClick={handleDownload} size="lg">
                      📥 下载文档查看
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 底部状态栏 */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200 bg-gray-50">
          <div className="text-sm text-gray-600">
            {zoom}% • {rotation}°
          </div>
          <div className="text-sm text-gray-600">
            按ESC键关闭预览
          </div>
        </div>
      </div>

      {/* ESC键关闭 */}
      {onClose && (
        <div
          className="sr-only"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              onClose()
            }
          }}
        >
          ESC关闭
        </div>
      )}
    </div>
  )
}

export default DocumentPreview