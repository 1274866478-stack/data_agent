/**
 * # [DOCUMENT_STORE] 文档状态管理Store
 *
 * ## [MODULE]
 * **文件名**: documentStore.ts
 * **职责**: Story 2.4文档管理 - 文档列表、上传、删除、预览、分页、筛选、批量操作
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 文档状态管理Store
 *
 * ## [INPUT]
 * Props (无 - Zustand Store):
 * - refresh?: boolean - 是否强制刷新
 * - file: File - 上传的文件
 * - files: File[] - 批量上传的文件列表
 * - id: string - 文档ID
 * - expiresHours: number - 预览URL有效期（小时）
 * - status: DocumentStatus | null - 状态筛选
 * - fileType: string | null - 文件类型筛选
 * - search: string - 搜索关键词
 * - page: number - 页码
 * - ids: string[] - 文档ID列表
 *
 * ## [OUTPUT]
 * Store:
 * - **documents: KnowledgeDocument[]** - 文档列表
 * - **uploadProgress: UploadProgress** - 上传进度跟踪
 * - **isLoading: boolean** - 加载状态
 * - **error: string | null** - 错误信息
 * - **selectedDocuments: string[]** - 选中的文档ID列表
 * - **currentPage: number** - 当前页码
 * - **pageSize: number** - 每页数量
 * - **total: number** - 总文档数
 * - **statusFilter: DocumentStatus | null** - 状态筛选
 * - **fileTypeFilter: string | null** - 文件类型筛选
 * - **searchQuery: string** - 搜索关键词
 * - **stats: DocumentStats | null** - 文档统计信息
 * - **showUploadModal: boolean** - 上传模态框显示状态
 * - **showPreviewModal: boolean** - 预览模态框显示状态
 * - **previewDocument: KnowledgeDocument | null** - 预览的文档
 * Actions:
 * - fetchDocuments(refresh?) - 获取文档列表
 * - uploadDocument(file) - 上传单个文档
 * - uploadMultipleDocuments(files) - 批量上传文档
 * - deleteDocument(id) - 删除文档
 * - deleteSelectedDocuments() - 删除选中文档
 * - getDocumentPreviewUrl(id, expiresHours?) - 获取预览URL
 * - getDocumentDownloadUrl(id) - 获取下载URL
 * - processDocument(id) - 手动触发文档处理
 * - setSelectedDocuments(ids) - 设置选中文档
 * - toggleDocumentSelection(id) - 切换文档选中状态
 * - clearSelection() - 清除选择
 * - setFilter(status, fileType, search) - 设置筛选器
 * - setPage(page) - 设置页码
 * - clearError() - 清除错误
 * - openUploadModal() / closeUploadModal() - 上传模态框控制
 * - openPreviewModal(document) / closePreviewModal() - 预览模态框控制
 * - refreshDocuments() - 刷新文档列表
 *
 * **上游依赖**:
 * - [zustand](https://github.com/pmndrs/zustand) - 状态管理库
 * - [zustand/middleware](https://github.com/pmndrs/zustand#persist) - persist中间件
 * - [zustand/middleware/immer](https://github.com/pmndrs/zustand#immer) - immer中间件
 *
 * **下游依赖**:
 * - 无（Store是叶子状态管理模块）
 *
 * **调用方**:
 * - [../components/documents/DocumentList.tsx](../components/documents/DocumentList.tsx) - 文档列表
 * - [../components/documents/DocumentCard.tsx](../components/documents/DocumentCard.tsx) - 文档卡片
 * - [../components/documents/DocumentPreview.tsx](../components/documents/DocumentPreview.tsx) - 文档预览
 * - [../app/(app)/documents/page.tsx](../app/(app)/documents/page.tsx) - 文档管理页面
 *
 * ## [STATE]
 * - **文档状态枚举**: DocumentStatus（PENDING, INDEXING, READY, ERROR）
 * - **文档类型**: KnowledgeDocument（id, tenant_id, file_name, storage_path等）
 * - **统计信息**: DocumentStats（by_status, by_file_type, total_documents等）
 * - **上传进度**: UploadProgress字典（文档ID → 进度信息）
 * - **分页**: currentPage, pageSize, total
 * - **筛选**: statusFilter, fileTypeFilter, searchQuery
 * - **选择**: selectedDocuments数组
 * - **UI状态**: showUploadModal, showPreviewModal, previewDocument
 * - **持久化策略**: 只持久化UI状态（currentPage, pageSize, filters），不持久化数据
 * - **immer中间件**: 简化不可变状态更新
 *
 * ## [SIDE-EFFECTS]
 * - **HTTP请求**: fetch调用Backend API
 *   - GET /documents - 获取文档列表
 *   - POST /documents/upload - 上传文档
 *   - DELETE /documents/{id} - 删除文档
 *   - GET /documents/{id}/preview - 获取预览URL
 *   - GET /documents/{id}/download - 获取下载URL
 *   - POST /documents/{id}/process - 触发文档处理
 * - **FormData**: new FormData()上传文件
 * - **URLSearchParams**: 构建查询参数（skip, limit, status, file_type）
 * - **状态更新**: set(state => {}) immer不可变更新
 * - **进度跟踪**: uploadProgress字典更新进度
 * - **数组操作**: unshift添加到开头，filter过滤删除，splice删除选中项
 * - **分页计算**: (currentPage - 1) * pageSize计算offset
 * - **Promise.allSettled**: 批量操作并行执行
 * - **setTimeout**: 延迟清理进度信息（3秒）
 * - **localStorage**: persist中间件持久化UI状态
 * - **异常处理**: try-catch捕获网络和API错误
 * - **条件判断**: response.ok检查HTTP状态
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'

// 文档状态枚举 - 与后端一致（小写值）
export enum DocumentStatus {
  PENDING = 'pending',
  INDEXING = 'indexing',
  READY = 'ready',
  ERROR = 'error'
}

// 文档类型定义 - Story 2.4规范
export interface KnowledgeDocument {
  id: string
  tenant_id: string
  file_name: string
  storage_path: string
  file_type: 'pdf' | 'docx' | 'unknown'
  file_size: number
  mime_type: string
  status: DocumentStatus
  processing_error?: string
  indexed_at?: string
  created_at: string
  updated_at: string
}

// 文档统计信息
export interface DocumentStats {
  by_status: Record<string, number>
  by_file_type: Record<string, number>
  total_documents: number
  total_size_bytes: number
  total_size_mb: number
}

// 上传进度信息
export interface UploadProgress {
  [key: string]: {
    progress: number
    status: 'uploading' | 'processing' | 'completed' | 'error'
    error?: string
  }
}

// 文档状态接口
interface DocumentState {
  // 状态数据
  documents: KnowledgeDocument[]
  uploadProgress: UploadProgress
  isLoading: boolean
  error: string | null
  selectedDocuments: string[]

  // 分页和过滤
  currentPage: number
  pageSize: number
  total: number
  statusFilter: DocumentStatus | null
  fileTypeFilter: string | null
  searchQuery: string

  // 统计信息
  stats: DocumentStats | null

  // UI状态
  showUploadModal: boolean
  showPreviewModal: boolean
  previewDocument: KnowledgeDocument | null

  // 操作方法
  fetchDocuments: (refresh?: boolean) => Promise<void>
  uploadDocument: (file: File) => Promise<void>
  uploadMultipleDocuments: (files: File[]) => Promise<void>
  deleteDocument: (id: string) => Promise<void>
  deleteSelectedDocuments: () => Promise<void>
  getDocumentPreviewUrl: (id: string, expiresHours?: number) => Promise<string>
  getDocumentDownloadUrl: (id: string) => Promise<string>
  processDocument: (id: string) => Promise<void>

  // 状态管理方法
  setSelectedDocuments: (ids: string[]) => void
  toggleDocumentSelection: (id: string) => void
  clearSelection: () => void
  setFilter: (status: DocumentStatus | null, fileType: string | null, search: string) => void
  setPage: (page: number) => void
  clearError: () => void

  // UI状态方法
  openUploadModal: () => void
  closeUploadModal: () => void
  openPreviewModal: (document: KnowledgeDocument) => void
  closePreviewModal: () => void
  refreshDocuments: () => Promise<void>
}

// API基础URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'

// 创建文档状态管理器
export const useDocumentStore = create<DocumentState>()(
  persist(
    immer((set, get) => ({
      // 初始状态
      documents: [],
      uploadProgress: {},
      isLoading: false,
      error: null,
      selectedDocuments: [],
      currentPage: 1,
      pageSize: 20,
      total: 0,
      statusFilter: null,
      fileTypeFilter: null,
      searchQuery: '',
      stats: null,
      showUploadModal: false,
      showPreviewModal: false,
      previewDocument: null,

      // 获取文档列表
      fetchDocuments: async (refresh = false) => {
        try {
          set((state) => {
            state.isLoading = true
            state.error = null
          })

          const { currentPage, pageSize, statusFilter, fileTypeFilter, searchQuery } = get()

          // 构建查询参数
          const params = new URLSearchParams({
            skip: ((currentPage - 1) * pageSize).toString(),
            limit: pageSize.toString(),
          })

          if (statusFilter) {
            params.append('status', statusFilter)
          }

          if (fileTypeFilter) {
            params.append('file_type', fileTypeFilter)
          }

          const response = await fetch(`${API_BASE_URL}/documents?${params}`)

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
          }

          const data = await response.json()

          set((state) => {
            state.documents = data.documents || []
            state.total = data.total || 0
            state.stats = data.stats || null
            state.isLoading = false
          })

        } catch (error) {
          console.error('Failed to fetch documents:', error)
          set((state) => {
            state.error = error instanceof Error ? error.message : '获取文档列表失败'
            state.isLoading = false
          })
        }
      },

      // 上传单个文档
      uploadDocument: async (file: File) => {
        try {
          const formData = new FormData()
          formData.append('file', file)

          // 创建进度跟踪
          const uploadId = `${file.name}_${Date.now()}`

          set((state) => {
            state.uploadProgress[uploadId] = {
              progress: 0,
              status: 'uploading'
            }
          })

          const response = await fetch(`${API_BASE_URL}/documents/upload`, {
            method: 'POST',
            body: formData,
          })

          if (!response.ok) {
            const errorData = await response.json()
            throw new Error(errorData.detail || '上传失败')
          }

          const document = await response.json()

          // 更新进度
          set((state) => {
            state.uploadProgress[uploadId] = {
              progress: 100,
              status: 'completed'
            }
            // 添加到文档列表
            state.documents.unshift(document)
            state.total += 1
          })

          // 刷新统计信息
          await get().fetchDocuments()

          // 清理进度信息（延迟清理）
          setTimeout(() => {
            set((state) => {
              delete state.uploadProgress[uploadId]
            })
          }, 3000)

        } catch (error) {
          console.error('Upload failed:', error)
          set((state) => {
            state.error = error instanceof Error ? error.message : '文档上传失败'
            // 标记上传失败
            const uploadId = `${file.name}_${Date.now()}`
            state.uploadProgress[uploadId] = {
              progress: 0,
              status: 'error',
              error: error instanceof Error ? error.message : '上传失败'
            }
          })
          throw error
        }
      },

      // 批量上传文档
      uploadMultipleDocuments: async (files: File[]) => {
        const uploadPromises = files.map(file => get().uploadDocument(file))

        try {
          await Promise.allSettled(uploadPromises)

          // 检查是否有失败的上传
          const failedUploads = uploadPromises.filter(
            result => result.status === 'rejected'
          ).length

          if (failedUploads > 0) {
            throw new Error(`${failedUploads} 个文件上传失败`)
          }

        } catch (error) {
          console.error('Batch upload failed:', error)
          throw error
        }
      },

      // 删除文档
      deleteDocument: async (id: string) => {
        try {
          const response = await fetch(`${API_BASE_URL}/documents/${id}`, {
            method: 'DELETE',
          })

          if (!response.ok) {
            const errorData = await response.json()
            throw new Error(errorData.detail || '删除失败')
          }

          set((state) => {
            state.documents = state.documents.filter(doc => doc.id !== id)
            state.selectedDocuments = state.selectedDocuments.filter(selectedId => selectedId !== id)
            state.total = Math.max(0, state.total - 1)
          })

          // 刷新统计信息
          await get().fetchDocuments()

        } catch (error) {
          console.error('Delete failed:', error)
          set((state) => {
            state.error = error instanceof Error ? error.message : '删除文档失败'
          })
          throw error
        }
      },

      // 删除选中的文档
      deleteSelectedDocuments: async () => {
        const { selectedDocuments } = get()

        if (selectedDocuments.length === 0) {
          return
        }

        try {
          const deletePromises = selectedDocuments.map(id => get().deleteDocument(id))
          await Promise.allSettled(deletePromises)

          set((state) => {
            state.selectedDocuments = []
          })

        } catch (error) {
          console.error('Batch delete failed:', error)
          throw error
        }
      },

      // 获取文档预览URL
      getDocumentPreviewUrl: async (id: string, expiresHours = 1) => {
        try {
          const response = await fetch(
            `${API_BASE_URL}/documents/${id}/preview?expires_in_hours=${expiresHours}`
          )

          if (!response.ok) {
            const errorData = await response.json()
            throw new Error(errorData.detail || '获取预览链接失败')
          }

          const data = await response.json()
          return data.preview_url

        } catch (error) {
          console.error('Get preview URL failed:', error)
          throw error
        }
      },

      // 获取文档下载URL
      getDocumentDownloadUrl: async (id: string) => {
        try {
          const response = await fetch(`${API_BASE_URL}/documents/${id}/download`)

          if (!response.ok) {
            throw new Error('获取下载链接失败')
          }

          return URL.createObjectURL(await response.blob())

        } catch (error) {
          console.error('Get download URL failed:', error)
          throw error
        }
      },

      // 手动触发文档处理
      processDocument: async (id: string) => {
        try {
          const response = await fetch(`${API_BASE_URL}/documents/${id}/process`, {
            method: 'POST',
          })

          if (!response.ok) {
            const errorData = await response.json()
            throw new Error(errorData.detail || '触发处理失败')
          }

          // 刷新文档列表以获取最新状态
          await get().fetchDocuments()

        } catch (error) {
          console.error('Process document failed:', error)
          set((state) => {
            state.error = error instanceof Error ? error.message : '文档处理失败'
          })
          throw error
        }
      },

      // 设置选中的文档
      setSelectedDocuments: (ids: string[]) => {
        set((state) => {
          state.selectedDocuments = ids
        })
      },

      // 切换文档选中状态
      toggleDocumentSelection: (id: string) => {
        set((state) => {
          const index = state.selectedDocuments.indexOf(id)
          if (index > -1) {
            state.selectedDocuments.splice(index, 1)
          } else {
            state.selectedDocuments.push(id)
          }
        })
      },

      // 清除选择
      clearSelection: () => {
        set((state) => {
          state.selectedDocuments = []
        })
      },

      // 设置过滤器
      setFilter: (status: DocumentStatus | null, fileType: string | null, search: string) => {
        set((state) => {
          state.statusFilter = status
          state.fileTypeFilter = fileType
          state.searchQuery = search
          state.currentPage = 1 // 重置到第一页
        })
      },

      // 设置页码
      setPage: (page: number) => {
        set((state) => {
          state.currentPage = page
        })
      },

      // 清除错误
      clearError: () => {
        set((state) => {
          state.error = null
        })
      },

      // 打开上传模态框
      openUploadModal: () => {
        set((state) => {
          state.showUploadModal = true
        })
      },

      // 关闭上传模态框
      closeUploadModal: () => {
        set((state) => {
          state.showUploadModal = false
        })
      },

      // 打开预览模态框
      openPreviewModal: (document: KnowledgeDocument) => {
        set((state) => {
          state.showPreviewModal = true
          state.previewDocument = document
        })
      },

      // 关闭预览模态框
      closePreviewModal: () => {
        set((state) => {
          state.showPreviewModal = false
          state.previewDocument = null
        })
      },

      // 刷新文档列表
      refreshDocuments: async () => {
        await get().fetchDocuments(true)
      },
    })),
    {
      name: 'document-store',
      partialize: (state) => ({
        // 只持久化UI状态，不持久化数据
        currentPage: state.currentPage,
        pageSize: state.pageSize,
        statusFilter: state.statusFilter,
        fileTypeFilter: state.fileTypeFilter,
        searchQuery: state.searchQuery,
      }),
    }
  )
)