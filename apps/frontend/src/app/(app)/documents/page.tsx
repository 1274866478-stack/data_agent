/**
 * # DocumentsPage 文档管理页面 - UI 一比一复刻版
 *
 * ## [MODULE]
 * **文件名**: app/(app)/documents/page.tsx
 * **职责**: 提供文档的完整管理界面，采用新设计风格
 * **作者**: Data Agent Team
 * **版本**: 3.0.0 (UI 一比一复刻)
 *
 * ## [INPUT]
 * - 无直接 Props（页面组件）
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 文档管理页面，包含搜索栏、筛选按钮、空状态和文档列表
 *
 * ## [LINK]
 * **上游依赖**:
 * - [@/store/documentStore](../../../store/documentStore.ts) - 提供文档状态管理
 * - [DocumentList](../../components/documents/DocumentList.tsx) - 文档列表组件
 * - [DocumentPreview](../../components/documents/DocumentPreview.tsx) - 文档预览组件
 * - [DocumentUpload](../../components/documents/DocumentUpload.tsx) - 文档上传组件
 * - [Alert](../../components/ui/alert.tsx) - 提示组件
 */

'use client'

import DocumentPreview from '@/components/documents/DocumentPreview'
import DocumentUpload from '@/components/documents/DocumentUpload'
import { Alert } from '@/components/ui/alert'
import { useDocumentStore } from '@/store/documentStore'
import { useEffect, useState } from 'react'

export default function DocumentsPage() {
  const {
    documents,
    stats,
    isLoading,
    error,
    showUploadModal,
    showPreviewModal,
    previewDocument,
    fetchDocuments,
    openUploadModal,
    closeUploadModal,
    closePreviewModal,
    clearError
  } = useDocumentStore()

  // 搜索和筛选状态
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  const handleUploadSuccess = (files: File[]) => {
    fetchDocuments()
  }

  const handleUploadError = (errorMessage: string) => {
    console.error('Upload error:', errorMessage)
  }

  const handleRefresh = () => {
    fetchDocuments()
  }

  return (
    <div className="doc-page-bg min-h-screen">
      <div className="container mx-auto px-4 py-6 max-w-[1200px]">

        {/* 1. 顶部工具栏 - 标题 + 统计卡片 + 上传按钮 */}
        <header className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-[#1f2937] dark:text-slate-200">文档管理</h1>
          <div className="flex items-center gap-3">
            {/* 统计卡片 - 总计 */}
            <div className="doc-header-stat">
              <span className="doc-header-stat-label">总计</span>
              <span className="doc-header-stat-value">{stats?.total_documents ?? documents.length ?? 0}</span>
            </div>
            {/* 统计卡片 - 已处理 */}
            <div className="doc-header-stat">
              <span className="doc-header-stat-label">已处理</span>
              <span className="doc-header-stat-value">{stats?.by_status?.ready ?? 0}</span>
            </div>
            {/* 统计卡片 - 存储 */}
            <div className="doc-header-stat">
              <span className="doc-header-stat-label">存储</span>
              <span className="doc-header-stat-value">{stats?.total_size_mb?.toFixed(1) ?? '0.0'} MB</span>
            </div>
            {/* 上传按钮 */}
            <button
              className="doc-primary-btn"
              onClick={openUploadModal}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" className="inline-block">
                <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
              </svg>
              上传文件
            </button>
          </div>
        </header>

        {/* 2. 搜索筛选区域 */}
        <div className="doc-search-bar mb-6">
          {/* 搜索图标 */}
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#64748b" className="flex-shrink-0">
            <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
          </svg>
          {/* 搜索输入框 */}
          <input
            type="text"
            placeholder="搜索文档（按名称或内容）..."
            className="doc-search-input-new"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {/* 状态筛选按钮 */}
          <button className="doc-filter-btn">
            所有状态
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="inline-block">
              <path d="M7 10l5 5 5-5z"/>
            </svg>
          </button>
          {/* 类型筛选按钮 */}
          <button className="doc-filter-btn">
            所有类型
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="inline-block">
              <path d="M7 10l5 5 5-5z"/>
            </svg>
          </button>
          {/* 刷新按钮 */}
          <button
            className="p-2 text-[#64748b] dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            onClick={handleRefresh}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" className="inline-block">
              <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
            </svg>
          </button>
        </div>

        {/* 3. 空状态区域 - 初始化数据源 */}
        {documents.length === 0 && !isLoading && (
          <div className="doc-empty-init mb-6">
            {/* 图标容器 */}
            <div className="w-16 h-16 bg-gradient-to-br from-[#00BFB3]/10 to-[#00E5D5]/10 rounded-2xl flex items-center justify-center mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="#00BFB3" className="inline-block">
                <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
              </svg>
            </div>
            {/* 标题 */}
            <h2 className="text-lg font-bold text-[#374151] dark:text-slate-200 mb-2">初始化数据源</h2>
            {/* 描述 */}
            <p className="text-sm text-[#6b7280] dark:text-slate-400 mb-6 max-w-md">
              拖拽您的 PDF、Word 或 Excel 文档到此处，开始智能数据处理。单个文件最大 50MB。
            </p>
            {/* 操作按钮 */}
            <div className="flex items-center gap-3">
              <button
                className="doc-primary-btn"
                onClick={openUploadModal}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" className="inline-block">
                  <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                </svg>
                选择文档
              </button>
              <span className="text-[#6b7280] dark:text-slate-400">或</span>
              <button className="doc-secondary-btn">
                从云端导入
              </button>
            </div>
          </div>
        )}

        {/* 3. 空状态区域 - 等待智能分析 */}
        {documents.length === 0 && !isLoading && (
          <div className="doc-empty-analyzing mb-6">
            {/* 图标容器 */}
            <div className="w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-slate-700 dark:to-slate-600 rounded-2xl flex items-center justify-center mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="#6b7280" className="inline-block dark:fill-slate-400">
                <path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7zm2.85 11.1l-.85.6V16h-4v-2.3l-.85-.6C7.8 12.16 7 10.63 7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.63-.8 3.16-2.15 4.1z"/>
              </svg>
            </div>
            {/* 标题 */}
            <h2 className="text-lg font-bold text-[#374151] dark:text-slate-200 mb-2">等待智能分析</h2>
            {/* 描述 */}
            <p className="text-sm text-[#6b7280] dark:text-slate-400 mb-6 max-w-md">
              未检测到文档。请向系统输入数据以开始实时分析和洞察提取。
            </p>
            {/* 标签 */}
            <div className="flex gap-2">
              <span className="doc-tag-accent">
                <span className="w-2 h-2 rounded-full inline-block"></span>
                支持多格式
              </span>
              <span className="doc-tag-accent">
                <span className="w-2 h-2 rounded-full inline-block"></span>
                安全存储
              </span>
            </div>
          </div>
        )}

        {/* 错误提示 */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            {error}
          </Alert>
        )}
      </div>

      {/* 模态框 */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-auto shadow-2xl">
            <DocumentUpload
              onClose={closeUploadModal}
              onSuccess={handleUploadSuccess}
              onError={handleUploadError}
            />
          </div>
        </div>
      )}

      {showPreviewModal && previewDocument && (
        <DocumentPreview
          document={previewDocument}
          onClose={closePreviewModal}
        />
      )}
    </div>
  )
}
