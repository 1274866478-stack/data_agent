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
import { uploadFile } from '@/services/fileUploadService'
import { documentService } from '@/services/api'
import type { DocumentStats, KnowledgeDocument } from '@/types/store/document'
import { DocumentStatus } from '@/types/store/document'
import { getDocumentUploadKey } from '@/utils/documentKeys'
import logger from '@/lib/logger'

// 上传进度信息
export interface UploadProgress {
  [key: string]: {
    progress: number
    status: 'uploading' | 'processing' | 'completed' | 'error'
    error?: string
  }
}

interface UploadDocumentOptions {
  refreshAfterUpload?: boolean
}

interface DeleteDocumentOptions {
  refreshAfterDelete?: boolean
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
  uploadDocument: (file: File, options?: UploadDocumentOptions) => Promise<void>
  uploadMultipleDocuments: (files: File[]) => Promise<void>
  deleteDocument: (id: string, options?: DeleteDocumentOptions) => Promise<void>
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

          // 保留 refresh 参数用于向后兼容（当前实现不区分 refresh 逻辑）
          void refresh

          const { currentPage, pageSize, statusFilter, fileTypeFilter } = get()

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

          const data = await documentService.list(params)

          set((state) => {
            state.documents = data.documents || []
            state.total = data.total || 0
            state.stats = data.stats || null
            state.isLoading = false
          })

        } catch (error) {
          logger.error('DocumentStore', 'fetchDocuments failed', error)
          set((state) => {
            state.error = error instanceof Error ? error.message : '获取文档列表失败'
            state.isLoading = false
          })
        }
      },

      // 上传单个文档
      uploadDocument: async (file: File, options: UploadDocumentOptions = {}) => {
        try {
          // 生成稳定 uploadId，确保进度条按文件粒度更新
          const uploadId = getDocumentUploadKey(file)

          set((state) => {
            state.uploadProgress[uploadId] = {
              progress: 0,
              status: 'uploading'
            }
          })

          const result = await uploadFile(
            file,
            (progress) => {
              set((state) => {
                const mappedStatus = progress.status === 'processing'
                  ? 'processing'
                  : progress.status === 'completed'
                    ? 'completed'
                    : progress.status === 'error'
                      ? 'error'
                      : 'uploading'

                state.uploadProgress[uploadId] = {
                  progress: progress.percentage,
                  status: mappedStatus
                }
              })
            }
          )

          if (!result.success || !result.document) {
            throw new Error(result.error || '上传失败')
          }

          // 更新本地列表和进度
          set((state) => {
            state.uploadProgress[uploadId] = {
              progress: 100,
              status: 'completed'
            }
            // 乐观更新：优先把新文档展示到列表顶部
            state.documents.unshift(result.document)
            state.total += 1
          })

          if (options.refreshAfterUpload !== false) {
            void get().fetchDocuments().catch((error) => {
              logger.error('DocumentStore', 'background refresh after upload failed', error)
            })
          }

          // 延迟清理上传进度，方便用户看到完成状态
          setTimeout(() => {
            set((state) => {
              delete state.uploadProgress[uploadId]
            })
          }, 3000)

        } catch (error) {
          logger.error('DocumentStore', 'uploadDocument failed', error)
          const errorMessage = error instanceof Error ? error.message : '上传失败'
          set((state) => {
            state.error = errorMessage
            const uploadId = getDocumentUploadKey(file)
            state.uploadProgress[uploadId] = {
              progress: 0,
              status: 'error',
              error: errorMessage
            }
          })
          throw error
        }
      },

      // 批量上传文档
      uploadMultipleDocuments: async (files: File[]) => {
        const uploadPromises = files.map((file) =>
          get().uploadDocument(file, { refreshAfterUpload: false })
        )

        try {
          const results = await Promise.allSettled(uploadPromises)
          const successUploads = results.filter((result) => result.status === 'fulfilled').length

          // 检查是否有失败的上传
          const failedUploads = results.filter(
            result => result.status === 'rejected'
          ).length

          if (successUploads > 0) {
            void get().fetchDocuments().catch((error) => {
              logger.error('DocumentStore', 'background refresh after batch upload failed', error)
            })
          }

          if (failedUploads > 0) {
            throw new Error(`${failedUploads} 个文件上传失败`)
          }

        } catch (error) {
          logger.error('DocumentStore', 'uploadMultipleDocuments failed', error)
          throw error
        }
      },

      // 删除文档
      deleteDocument: async (id: string, options: DeleteDocumentOptions = {}) => {
        try {
          await documentService.remove(id)

          set((state) => {
            state.documents = state.documents.filter(doc => doc.id !== id)
            state.selectedDocuments = state.selectedDocuments.filter(selectedId => selectedId !== id)
            state.total = Math.max(0, state.total - 1)
          })

          if (options.refreshAfterDelete !== false) {
            void get().fetchDocuments().catch((error) => {
              logger.error('DocumentStore', 'background refresh after delete failed', error)
            })
          }

        } catch (error) {
          logger.error('DocumentStore', 'deleteDocument failed', error)
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
          const deletePromises = selectedDocuments.map((id) =>
            get().deleteDocument(id, { refreshAfterDelete: false })
          )
          const results = await Promise.allSettled(deletePromises)
          const successDeletes = results.filter((result) => result.status === 'fulfilled').length

          set((state) => {
            state.selectedDocuments = []
          })

          if (successDeletes > 0) {
            void get().fetchDocuments().catch((error) => {
              logger.error('DocumentStore', 'background refresh after batch delete failed', error)
            })
          }

        } catch (error) {
          logger.error('DocumentStore', 'deleteSelectedDocuments failed', error)
          throw error
        }
      },

      // 获取文档预览URL
      getDocumentPreviewUrl: async (id: string, expiresHours = 1) => {
        try {
          return await documentService.previewUrl(id, expiresHours)

        } catch (error) {
          logger.error('DocumentStore', 'getDocumentPreviewUrl failed', error)
          throw error
        }
      },

      // 获取文档下载URL
      getDocumentDownloadUrl: async (id: string) => {
        try {
          return await documentService.downloadUrl(id)

        } catch (error) {
          logger.error('DocumentStore', 'getDocumentDownloadUrl failed', error)
          throw error
        }
      },

      // 手动触发文档处理
      processDocument: async (id: string) => {
        try {
          await documentService.process(id)

          // 刷新文档列表以获取最新状态
          await get().fetchDocuments()

        } catch (error) {
          logger.error('DocumentStore', 'processDocument failed', error)
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
        await get().fetchDocuments()
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
