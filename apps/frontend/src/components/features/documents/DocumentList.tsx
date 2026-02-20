/**
 * # DocumentList 文档列表组件 - 简化版
 *
 * ## [MODULE]
 * **文件名**: DocumentList.tsx
 * **职责**: 显示文档列表，提供分页和批量操作功能（工具栏已移至页面级）
 * **作者**: Data Agent Team
 * **版本**: 2.0.0 (UI 一比一复刻)
 *
 * ## [INPUT]
 * - **showSelection**: boolean (可选) - 是否显示选择框，默认false
 * - **onSelectionChange**: (selectedIds: string[]) => void (可选) - 选中状态变化回调
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 文档列表界面（批量操作+卡片列表+分页）
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
 */

import React, { useEffect, useState } from 'react'
import { useDocuments } from '@/hooks/useDocuments'
import { DocumentStatus } from '@/types/store/document'
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
    fetchDocuments,
    setSelectedDocuments,
    toggleDocumentSelection,
    clearSelection,
    setFilter,
    setPage,
    deleteSelectedDocuments,
    clearError,
    refreshDocuments
  } = useDocuments()

  const [localSearchQuery, setLocalSearchQuery] = useState(searchQuery)

  // 初始化数据
  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  // 处理搜索（从页面级传递过来的搜索）
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

  // 计算分页信息
  const totalPages = Math.ceil(total / pageSize)
  const hasNextPage = currentPage < totalPages
  const hasPrevPage = currentPage > 1

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

      {/* 批量操作 */}
      {showSelection && selectedDocuments.length > 0 && (
        <div className="flex items-center justify-between p-4 bg-white dark:bg-slate-800 rounded-xl border border-[#E0E0E0] dark:border-slate-700">
          <span className="text-sm text-[#212121] dark:text-slate-200">
            已选择 {selectedDocuments.length} 个文档
          </span>
          <div className="flex space-x-2">
            <Button
              size="sm"
              variant="outline"
              onClick={clearSelection}
              className="border-[#E0E0E0] dark:border-slate-600"
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

      {/* 文档列表 */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#2196F3] dark:border-sky-400"></div>
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12 bg-white dark:bg-slate-800 rounded-xl border border-[#E0E0E0] dark:border-slate-700">
            <div className="text-6xl mb-4">📂</div>
            <h3 className="text-lg font-medium text-[#212121] dark:text-slate-200 mb-2">暂无文档</h3>
            <p className="text-[#757575] dark:text-slate-400">
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
                  className="border-[#E0E0E0] dark:border-slate-600"
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
                        className={pageNum === currentPage
                          ? "bg-[#2196F3] text-white hover:bg-[#1976D2]"
                          : "border-[#E0E0E0] dark:border-slate-600"
                        }
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
                  className="border-[#E0E0E0] dark:border-slate-600"
                >
                  下一页
                </Button>
              </div>
            )}

            {/* 页面信息 */}
            <div className="text-center text-sm text-[#757575] dark:text-slate-400">
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
