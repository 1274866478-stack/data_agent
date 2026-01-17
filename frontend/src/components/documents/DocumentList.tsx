/**
 * # DocumentList 文档列表组件
 *
 * ## [MODULE]
 * **文件名**: DocumentList.tsx
 * **职责**: 显示文档列表，提供搜索、过滤、分页、批量操作和统计功能
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - **showSelection**: boolean (可选) - 是否显示选择框，默认false
 * - **onSelectionChange**: (selectedIds: string[]) => void (可选) - 选中状态变化回调
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 完整的文档列表界面（工具栏+统计+卡片列表+分页）
 * - **副作用**: 调用documentStore的各种方法和修改状态
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [@/store/documentStore.ts](../../store/documentStore.ts) - 文档状态管理
 * - [@/components/ui/*](../ui/) - UI基础组件（Button, Alert）
 * - [./DocumentCard.tsx](./DocumentCard.tsx) - 文档卡片
 *
 * **下游依赖**:
 * - 无直接下游组件
 *
 * **调用方**:
 * - [../../app/(app)/documents/page.tsx](../../app/(app)/documents/page.tsx) - 文档页面
 *
 * ## [STATE]
 * - **localSearchQuery**: string - 本地搜索查询文本（防抖）
 * - 从documentStore获取：documents, isLoading, error, selectedDocuments, total, currentPage, pageSize, statusFilter, fileTypeFilter, searchQuery, stats
 *
 * ## [SIDE-EFFECTS]
 * - 初始化时调用fetchDocuments()
 * - 搜索防抖300ms后调用setFilter()
 * - 状态过滤时调用setFilter()
 * - 分页时调用setPage()
 * - 批量删除时调用deleteSelectedDocuments()
 * - 刷新时调用refreshDocuments()
 * - 通知父组件选中变化（onSelectionChange回调）
 * - 删除确认弹窗（window.confirm）
 */
/**
 * 文档列表组件 - Story 2.4规范实现
 * 文档列表显示、搜索过滤、批量操作、状态显示
 */

import React, { useEffect, useState } from 'react'
import { useDocumentStore, DocumentStatus } from '@/store/documentStore'
import DocumentCard from './DocumentCard'
import { Button } from '@/components/ui/button'
import { Alert } from '@/components/ui/alert'

interface DocumentListProps {
  showSelection?: boolean
  onSelectionChange?: (selectedIds: string[]) => void
}

export const DocumentList: React.FC<DocumentListProps> = ({
  showSelection = false,
  onSelectionChange
}) => {
  const {
    documents,
    isLoading,
    error,
    selectedDocuments,
    total,
    currentPage,
    pageSize,
    statusFilter,
    fileTypeFilter,
    searchQuery,
    stats,
    fetchDocuments,
    setSelectedDocuments,
    toggleDocumentSelection,
    clearSelection,
    setFilter,
    setPage,
    deleteSelectedDocuments,
    clearError,
    refreshDocuments
  } = useDocumentStore()

  const [localSearchQuery, setLocalSearchQuery] = useState(searchQuery)

  // 初始化数据
  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  // 处理搜索
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setFilter(statusFilter, fileTypeFilter, localSearchQuery)
    }, 300)

    return () => clearTimeout(timeoutId)
  }, [localSearchQuery, statusFilter, fileTypeFilter, setFilter])

  // 通知父组件选择变化
  useEffect(() => {
    onSelectionChange?.(selectedDocuments)
  }, [selectedDocuments, onSelectionChange])

  // 处理状态过滤
  const handleStatusFilter = (status: DocumentStatus | null) => {
    setFilter(status, fileTypeFilter, localSearchQuery)
  }

  // 处理文件类型过滤
  const handleFileTypeFilter = (fileType: string | null) => {
    setFilter(statusFilter, fileType, localSearchQuery)
  }

  // 处理搜索
  const handleSearch = (query: string) => {
    setLocalSearchQuery(query)
  }

  // 处理分页
  const handlePageChange = (page: number) => {
    setPage(page)
  }

  // 处理批量删除
  const handleBatchDelete = async () => {
    if (selectedDocuments.length === 0) return

    if (window.confirm(`确定要删除选中的 ${selectedDocuments.length} 个文档吗？`)) {
      try {
        await deleteSelectedDocuments()
      } catch (error) {
        console.error('Batch delete failed:', error)
      }
    }
  }

  // 处理刷新
  const handleRefresh = async () => {
    await refreshDocuments()
  }

  // 计算分页信息
  const totalPages = Math.ceil(total / pageSize)
  const hasNextPage = currentPage < totalPages
  const hasPrevPage = currentPage > 1

  // 获取统计信息
  const getStatsDisplay = () => {
    if (!stats) return null

    return (
      <div className="flex space-x-6 text-sm">
        <div>
          <span className="text-gray-500">总计:</span>
          <span className="ml-1 font-medium">{stats.total_documents}</span>
        </div>
        <div>
          <span className="text-gray-500">已完成:</span>
          <span className="ml-1 font-medium text-green-600">
            {stats.by_status[DocumentStatus.READY] || 0}
          </span>
        </div>
        <div>
          <span className="text-gray-500">处理中:</span>
          <span className="ml-1 font-medium text-blue-600">
            {stats.by_status[DocumentStatus.INDEXING] || 0}
          </span>
        </div>
        <div>
          <span className="text-gray-500">存储:</span>
          <span className="ml-1 font-medium">{parseFloat(String(stats.total_size_mb)).toFixed(1)} MB</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 错误提示 */}
      {error && (
        <Alert variant="destructive" className="flex justify-between items-center">
          <span>{error}</span>
          <Button size="sm" variant="ghost" onClick={clearError}>
            ✕
          </Button>
        </Alert>
      )}

      {/* 工具栏 */}
      <div className="bg-white dark:bg-slate-800 p-4 rounded-lg border border-gray-200 dark:border-slate-700">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
          {/* 搜索框 */}
          <div className="flex-1 max-w-md">
            <input
              type="text"
              placeholder="搜索文档名称..."
              value={localSearchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* 过滤器 */}
          <div className="flex flex-wrap gap-2">
            {/* 状态过滤 */}
            <select
              value={statusFilter || ''}
              onChange={(e) => handleStatusFilter(e.target.value ? e.target.value as DocumentStatus : null)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">所有状态</option>
              <option value={DocumentStatus.PENDING}>等待处理</option>
              <option value={DocumentStatus.INDEXING}>正在处理</option>
              <option value={DocumentStatus.READY}>处理完成</option>
              <option value={DocumentStatus.ERROR}>处理失败</option>
            </select>

            {/* 文件类型过滤 */}
            <select
              value={fileTypeFilter || ''}
              onChange={(e) => handleFileTypeFilter(e.target.value || null)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">所有类型</option>
              <option value="pdf">PDF</option>
              <option value="docx">Word</option>
            </select>

            {/* 刷新按钮 */}
            <Button
              variant="outline"
              onClick={handleRefresh}
              disabled={isLoading}
            >
              🔄 刷新
            </Button>
          </div>
        </div>

        {/* 批量操作 */}
        {showSelection && selectedDocuments.length > 0 && (
          <div className="mt-4 flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <span className="text-sm text-blue-700">
              已选择 {selectedDocuments.length} 个文档
            </span>
            <div className="flex space-x-2">
              <Button
                size="sm"
                variant="outline"
                onClick={clearSelection}
              >
                取消选择
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={handleBatchDelete}
              >
                删除选中
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* 统计信息 */}
      {getStatsDisplay() && (
        <div className="bg-white dark:bg-slate-800 p-4 rounded-lg border border-gray-200 dark:border-slate-700">
          {getStatsDisplay()}
        </div>
      )}

      {/* 文档列表 */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12 bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700">
            <div className="text-6xl mb-4">📂</div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-slate-100 mb-2">暂无文档</h3>
            <p className="text-gray-500">
              {searchQuery || statusFilter || fileTypeFilter
                ? '没有找到符合条件的文档'
                : '还没有上传任何文档，点击上传按钮开始'
              }
            </p>
          </div>
        ) : (
          <>
            <div className="grid gap-4 lg:grid-cols-2">
              {documents.map((document) => (
                <DocumentCard
                  key={document.id}
                  document={document}
                  isSelected={selectedDocuments.includes(document.id)}
                  onSelectionChange={(selected) =>
                    toggleDocumentSelection(document.id)
                  }
                  showSelection={showSelection}
                />
              ))}
            </div>

            {/* 分页控件 */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center space-x-2 pt-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={!hasPrevPage || isLoading}
                >
                  上一页
                </Button>

                <div className="flex items-center space-x-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum
                    if (totalPages <= 5) {
                      pageNum = i + 1
                    } else if (currentPage <= 3) {
                      pageNum = i + 1
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i
                    } else {
                      pageNum = currentPage - 2 + i
                    }

                    return (
                      <Button
                        key={pageNum}
                        variant={pageNum === currentPage ? "default" : "outline"}
                        size="sm"
                        onClick={() => handlePageChange(pageNum)}
                        disabled={isLoading}
                      >
                        {pageNum}
                      </Button>
                    )
                  })}
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={!hasNextPage || isLoading}
                >
                  下一页
                </Button>
              </div>
            )}

            {/* 页面信息 */}
            <div className="text-center text-sm text-gray-500">
              显示第 {(currentPage - 1) * pageSize + 1} -{' '}
              {Math.min(currentPage * pageSize, total)} 条，共 {total} 条
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default DocumentList