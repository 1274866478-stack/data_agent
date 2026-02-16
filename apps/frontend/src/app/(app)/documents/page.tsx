/**
 * # DocumentsPage 文档管理页面
 *
 * ## [MODULE]
 * **文件名**: app/(app)/documents/page.tsx
 * **职责**: 提供文档的完整管理界面，包括文档列表、上传、预览和统计信息
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **备注**: Story 2.4规范实现
 *
 * ## [INPUT]
 * - 无直接 Props（页面组件）
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 文档管理页面，包含统计卡片、文档列表、上传和预览功能
 *
 * ## [LINK]
 * **上游依赖**:
 * - [@/store/documentStore](../../../store/documentStore.ts) - 提供文档状态管理
 * - [DocumentList](../../components/documents/DocumentList.tsx) - 文档列表组件
 * - [DocumentUpload](../../components/documents/DocumentUpload.tsx) - 文档上传组件
 * - [DocumentPreview](../../components/documents/DocumentPreview.tsx) - 文档预览组件
 * - [@/components/ui/button](../../components/ui/button.tsx) - 按钮组件
 * - [@/components/ui/alert](../../components/ui/alert.tsx) - 提示组件
 *
 * **下游依赖**:
 * - 无（页面是用户交互入口点）
 *
 * ## [STATE]
 * - **documents: Document[]** - 文档列表（从 documentStore 获取）
 * - **isLoading: boolean** - 加载状态
 * - **error: string | null** - 错误信息
 * - **showUploadModal: boolean** - 是否显示上传模态框
 * - **showPreviewModal: boolean** - 是否显示预览模态框
 * - **previewDocument: Document | null** - 预览的文档对象
 * - **selectedDocuments: string[]** - 已选中的文档ID列表
 * - **stats: DocumentStats | null** - 文档统计信息
 *
 * ## [SIDE-EFFECTS]
 * - **数据获取**: 组件挂载时自动调用 fetchDocuments() 获取文档列表
 * - **统计展示**: 计算并展示文档统计信息（总数、已完成、处理中、存储使用）
 * - **上传处理**: 处理文档上传成功和错误回调，成功后刷新列表
 * - **模态框管理**: 控制上传和预览模态框的显示/隐藏
 * - **错误处理**: 显示和清除错误信息
 */
/**
 * 文档管理页面 - Story 2.4规范实现
 * 整合所有文档管理组件，提供完整的用户界面
 */

'use client'

import DocumentList from '@/components/documents/DocumentList'
import DocumentPreview from '@/components/documents/DocumentPreview'
import DocumentUpload from '@/components/documents/DocumentUpload'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useDocumentStore } from '@/store/documentStore'
import { useEffect } from 'react'

export default function DocumentsPage() {
  const {
    documents,
    isLoading,
    error,
    showUploadModal,
    showPreviewModal,
    previewDocument,
    fetchDocuments,
    openUploadModal,
    closeUploadModal,
    closePreviewModal,
    clearError,
    selectedDocuments,
    stats
  } = useDocumentStore()

  // 初始化数据
  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  // 处理上传成功
  const handleUploadSuccess = (files: File[]) => {
    // 成功后刷新列表
    fetchDocuments()
  }

  // 处理上传错误
  const handleUploadError = (errorMessage: string) => {
    console.error('Upload error:', errorMessage)
  }

  // 获取统计信息
  const getQuickStats = () => {
    if (!stats) return null

    const readyCount = stats.by_status?.READY || 0
    const processingCount = stats.by_status?.INDEXING || 0
    const errorCount = stats.by_status?.ERROR || 0

    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-gray-200 dark:border-slate-700 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">总文档</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-slate-100">{stats.total_documents}</p>
            </div>
            <div className="text-3xl">📁</div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-gray-200 dark:border-slate-700 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">已完成</p>
              <p className="text-2xl font-bold text-green-600">{readyCount}</p>
            </div>
            <div className="text-3xl">✅</div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-gray-200 dark:border-slate-700 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">处理中</p>
              <p className="text-2xl font-bold text-blue-600">{processingCount}</p>
            </div>
            <div className="text-3xl">🔄</div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-gray-200 dark:border-slate-700 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">存储使用</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-slate-100">{stats.total_size_mb.toFixed(1)} MB</p>
            </div>
            <div className="text-3xl">💾</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-800">
      <div className="container mx-auto px-4 py-8">
        {/* 页面标题 */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-slate-100">文档管理</h1>
            <p className="text-gray-600 mt-1">上传、管理和预览您的文档</p>
          </div>
          <div className="flex space-x-3">
            {selectedDocuments.length > 0 && (
              <div className="flex items-center space-x-2 bg-blue-50 dark:bg-blue-900/20 px-3 py-2 rounded-lg">
                <span className="text-sm text-blue-700">
                  已选择 {selectedDocuments.length} 个文档
                </span>
              </div>
            )}
            <Button onClick={openUploadModal} className="bg-gradient-modern-primary hover:opacity-90 transition-opacity">
              📤 上传文档
            </Button>
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <Alert variant="destructive" className="mb-6 flex justify-between items-center">
            <span>{error}</span>
            <Button size="sm" variant="ghost" onClick={clearError}>
              ✕
            </Button>
          </Alert>
        )}

        {/* 统计信息 */}
        {getQuickStats()}

        {/* 使用说明 */}
        {documents.length === 0 && !isLoading && (
          <div className="bg-white p-8 rounded-lg border border-gray-200 text-center mb-8">
            <div className="text-6xl mb-4">📂</div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-slate-100 mb-2">开始使用文档管理</h2>
            <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
              上传您的 PDF 和 Word 文档，系统将自动处理并为您提供预览、搜索和管理功能。
              所有文档都安全存储在您的专属空间中。
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto text-left">
              <div className="p-4 bg-gray-50 dark:bg-slate-800 rounded-lg">
                <div className="text-2xl mb-2">📄</div>
                <h3 className="font-medium text-gray-900 dark:text-slate-100 mb-1">支持多种格式</h3>
                <p className="text-sm text-gray-600">PDF 和 Word 文档，最大 50MB</p>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-slate-800 rounded-lg">
                <div className="text-2xl mb-2">🔍</div>
                <h3 className="font-medium text-gray-900 dark:text-slate-100 mb-1">智能处理</h3>
                <p className="text-sm text-gray-600">自动提取内容和元数据</p>
              </div>
              <div className="p-4 bg-gray-50 dark:bg-slate-800 rounded-lg">
                <div className="text-2xl mb-2">👁️</div>
                <h3 className="font-medium text-gray-900 dark:text-slate-100 mb-1">在线预览</h3>
                <p className="text-sm text-gray-600">无需下载即可查看文档</p>
              </div>
            </div>
          </div>
        )}

        {/* 文档列表 */}
        <DocumentList />
      </div>

      {/* 上传模态框 */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-40 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-auto">
            <DocumentUpload
              onClose={closeUploadModal}
              onSuccess={handleUploadSuccess}
              onError={handleUploadError}
            />
          </div>
        </div>
      )}

      {/* 预览模态框 */}
      {showPreviewModal && previewDocument && (
        <DocumentPreview
          document={previewDocument}
          onClose={closePreviewModal}
        />
      )}
    </div>
  )
}