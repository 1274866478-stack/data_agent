'use client'

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { useAuthStore } from './authStore'

// 获取 API 基础 URL
const getApiBaseUrl = () => {
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'
}

// 获取当前用户的 tenant_id 和 user_id
const getAuthParams = () => {
  const user = useAuthStore.getState().user
  return {
    tenant_id: user?.tenant_id || 'default_tenant',
    user_id: user?.id || 'anonymous'
  }
}

// 数据源概览统计接口
export interface DashboardOverview {
  databases: {
    total: number
    active: number
    error: number
  }
  documents: {
    total: number
    ready: number
    processing: number
    error: number
  }
  storage: {
    used_mb: number
    quota_mb: number
    usage_percentage: number
  }
  recent_activity: ActivityItem[]
}

// 活动记录接口
export interface ActivityItem {
  id: string
  type: 'database' | 'document'
  action: 'created' | 'updated' | 'deleted' | 'tested'
  item_name: string
  timestamp: string
  status: 'success' | 'error'
}

// 数据源类型
export type DataSourceType = 'database' | 'document' | 'all'

// 数据源状态筛选
export interface DataSourceFilters {
  type: DataSourceType
  status: string[]
  dateRange: {
    from?: string
    to?: string
  }
}

// 搜索结果接口
export interface SearchResult {
  id: string
  type: 'database' | 'document'
  name: string
  status: string
  created_at: string
  updated_at: string
  // 数据库特有字段
  db_type?: string
  host?: string
  // 文档特有字段
  file_type?: string
  file_size_mb?: number
}

// 批量操作结果接口
export interface BulkOperationResult {
  success_count: number
  error_count: number
  errors: Array<{
    item_id: string
    error: string
  }>
}

// Dashboard Store 接口
interface DashboardState {
  // 状态
  overview: DashboardOverview | null
  activeTab: 'databases' | 'documents'
  searchQuery: string
  filters: DataSourceFilters
  selectedItems: string[]
  isLoading: boolean
  error: string | null

  // 搜索结果
  searchResults: SearchResult[]
  searchTotal: number
  searchPage: number
  searchTotalPages: number

  // Actions
  fetchOverview: () => Promise<void>
  setActiveTab: (tab: 'databases' | 'documents') => void
  setSearchQuery: (query: string) => void
  updateFilters: (filters: Partial<DataSourceFilters>) => void
  clearFilters: () => void
  toggleSelection: (id: string) => void
  selectAll: (ids: string[]) => void
  clearSelection: () => void
  searchDataSources: (page?: number) => Promise<void>
  bulkDelete: (itemIds: string[], itemType: 'database' | 'document') => Promise<BulkOperationResult>
  clearError: () => void
  setSelectedItems: (items: string[]) => void
}

// 初始筛选器
const initialFilters: DataSourceFilters = {
  type: 'all',
  status: [],
  dateRange: {}
}

export const useDashboardStore = create<DashboardState>()(
  devtools(
    (set, get) => ({
      // 初始状态
      overview: null,
      activeTab: 'databases',
      searchQuery: '',
      filters: initialFilters,
      selectedItems: [],
      isLoading: false,
      error: null,

      searchResults: [],
      searchTotal: 0,
      searchPage: 1,
      searchTotalPages: 1,

      // 获取概览数据
      fetchOverview: async () => {
        set({ isLoading: true, error: null })

        try {
          const apiBaseUrl = getApiBaseUrl()
          const { tenant_id, user_id } = getAuthParams()
          const params = new URLSearchParams({ tenant_id, user_id })

          const response = await fetch(`${apiBaseUrl}/data-sources/overview?${params}`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
              'Content-Type': 'application/json',
            },
          })

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
          }

          const overview: DashboardOverview = await response.json()
          set({ overview, isLoading: false })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '获取概览数据失败',
            isLoading: false
          })
        }
      },

      // 设置活跃标签页
      setActiveTab: (tab: 'databases' | 'documents') => {
        set({ activeTab: tab })
        // 切换标签页时重新搜索
        const { searchQuery, filters } = get()
        if (searchQuery || filters.status.length > 0) {
          get().searchDataSources(1)
        }
      },

      // 设置搜索查询
      setSearchQuery: (query: string) => {
        set({ searchQuery: query })
        // 防抖搜索
        const timeoutId = setTimeout(() => {
          get().searchDataSources(1)
        }, 300)

        return () => clearTimeout(timeoutId)
      },

      // 更新筛选器
      updateFilters: (newFilters: Partial<DataSourceFilters>) => {
        set({
          filters: { ...get().filters, ...newFilters }
        })
        // 筛选器变化时重新搜索
        get().searchDataSources(1)
      },

      // 清除筛选器
      clearFilters: () => {
        set({ filters: initialFilters })
        get().searchDataSources(1)
      },

      // 切换选择状态
      toggleSelection: (id: string) => {
        const { selectedItems } = get()
        const newSelection = selectedItems.includes(id)
          ? selectedItems.filter(item => item !== id)
          : [...selectedItems, id]
        set({ selectedItems: newSelection })
      },

      // 全选
      selectAll: (ids: string[]) => {
        set({ selectedItems: ids })
      },

      // 清除选择
      clearSelection: () => {
        set({ selectedItems: [] })
      },

      // 搜索数据源
      searchDataSources: async (page = 1) => {
        set({ isLoading: true, error: null })

        try {
          const { searchQuery, filters, activeTab } = get()
          const { tenant_id, user_id } = getAuthParams()

          // 将前端的 tab 名称映射到后端期望的类型
          const tabToType: Record<string, string> = {
            'databases': 'database',
            'documents': 'document'
          }
          const searchType = filters.type === 'all'
            ? (tabToType[activeTab] || activeTab)
            : filters.type

          // 构建查询参数
          const params = new URLSearchParams({
            tenant_id,
            user_id,
            q: searchQuery,
            type: searchType,
            page: page.toString(),
            limit: '20',
          })

          // 添加状态筛选
          if (filters.status.length > 0) {
            params.append('status', filters.status.join(','))
          }

          // 添加日期范围筛选
          if (filters.dateRange.from) {
            params.append('date_from', filters.dateRange.from)
          }
          if (filters.dateRange.to) {
            params.append('date_to', filters.dateRange.to)
          }

          const apiBaseUrl = getApiBaseUrl()
          const response = await fetch(`${apiBaseUrl}/data-sources/search?${params}`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
              'Content-Type': 'application/json',
            },
          })

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
          }

          const data = await response.json()
          set({
            searchResults: data.results,
            searchTotal: data.total,
            searchPage: data.page,
            searchTotalPages: data.total_pages,
            isLoading: false
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '搜索失败',
            isLoading: false
          })
        }
      },

      // 批量删除
      bulkDelete: async (itemIds: string[], itemType: 'database' | 'document') => {
        set({ isLoading: true, error: null })

        try {
          const apiBaseUrl = getApiBaseUrl()
          const { tenant_id, user_id } = getAuthParams()
          const params = new URLSearchParams({ tenant_id, user_id })

          const response = await fetch(`${apiBaseUrl}/data-sources/bulk-delete?${params}`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              item_ids: itemIds,
              item_type: itemType,
            }),
          })

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
          }

          const result: BulkOperationResult = await response.json()
          set({ isLoading: false })

          // 删除成功后重新获取数据
          get().fetchOverview()
          get().searchDataSources(get().searchPage)
          get().clearSelection()

          return result
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '批量删除失败',
            isLoading: false
          })
          throw error
        }
      },

      // 设置选中项
      setSelectedItems: (items: string[]) => {
        set({ selectedItems: items })
      },

      // 清除错误
      clearError: () => {
        set({ error: null })
      },
    }),
    {
      name: 'dashboard-store',
    }
  )
)