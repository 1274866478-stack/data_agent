/**
 * # [TENANT_STORE] 租户状态管理Store
 *
 * ## [MODULE]
 * **文件名**: tenantStore.ts
 * **职责**: Story-2.2前端租户管理 - 租户信息获取、更新、统计信息、状态管理
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 租户状态管理Store
 *
 * ## [INPUT]
 * Props (无 - Zustand Store):
 * - 无直接Props输入
 * - 内部从API获取租户信息
 *
 * ## [OUTPUT]
 * Store:
 * - **currentTenant: Tenant | null** - 当前租户信息
 *   - id, email, status (active/suspended/deleted)
 *   - display_name, settings (timezone, language, preferences)
 *   - storage_quota_mb, created_at, updated_at
 * - **tenantStats: TenantStats | null** - 租户统计信息
 *   - total_documents, total_data_sources, storage_used_mb
 *   - processed_documents, pending_documents
 *   - storage_quota_mb, storage_usage_percent
 * - **isLoading: boolean** - 加载状态
 * - **error: string | null** - 错误信息
 * Actions:
 * - fetchTenantProfile() - 获取租户信息
 * - updateTenantProfile(updateData) - 更新租户信息
 * - fetchTenantStats() - 获取租户统计信息
 * - clearTenantData() - 清除租户数据
 * - setError(error) - 设置错误信息
 * Selectors:
 * - useCurrentTenant() - 获取当前租户
 * - useTenantStats() - 获取租户统计
 * - useTenantLoading() - 获取加载状态
 * - useTenantError() - 获取错误信息
 * - useTenantActions() - 获取所有操作方法
 * Utilities:
 * - getStorageUsageColor(usagePercent) - 存储使用率颜色
 * - getStorageUsageVariant(usagePercent) - 存储使用率样式变体
 * - formatFileSize(mb) - 格式化文件大小
 * - getStatusColor(status) - 状态颜色
 * - getStatusBadgeVariant(status) - 状态徽章样式
 *
 * **上游依赖**:
 * - [zustand](https://github.com/pmndrs/zustand) - 状态管理库
 * - [zustand/middleware](https://github.com/pmndrs/zustand#devtools) - devtools中间件
 *
 * **下游依赖**:
 * - 无（Store是叶子状态管理模块）
 *
 * **调用方**:
 * - [../components/tenant/TenantProfile.tsx](../components/tenant/TenantProfile.tsx) - 租户资料组件
 * - [../components/tenant/TenantStats.tsx](../components/tenant/TenantStats.tsx) - 租户统计组件
 * - [../components/tenant/TenantSettings.tsx](../components/tenant/TenantSettings.tsx) - 租户设置组件
 * - [../app/(app)/settings/page.tsx](../app/(app)/settings/page.tsx) - 设置页面
 *
 * ## [STATE]
 * - **租户信息**: currentTenant存储当前租户完整信息
 * - **统计信息**: tenantStats存储租户使用统计
 * - **API客户端**: TenantAPI类封装API调用
 *   - getCurrentTenant() - GET /tenants/me
 *   - updateCurrentTenant() - PUT /tenants/me
 *   - getTenantStats() - GET /tenants/me/stats
 * - **工具函数**: 存储颜色、状态颜色、文件大小格式化
 * - **选择器函数**: Zustand选择器优化订阅
 *
 * ## [SIDE-EFFECTS]
 * - **HTTP请求**: fetch调用Backend API（/tenants/me, /tenants/me/stats）
 * - **localStorage操作**: localStorage.getItem('auth_token')获取认证令牌
 * - **状态更新**: set()更新currentTenant, tenantStats, isLoading, error
 * - **异常处理**: try-catch捕获网络和API错误
 * - **Zustand devtools**: 集成Redux DevTools调试
 * - **条件判断**: status枚举值判断颜色和样式变体
 * - **文件大小格式化**: if (mb < 1024)判断单位
 */

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

// 租户状态类型定义
export interface Tenant {
  id: string
  email: string
  status: 'active' | 'suspended' | 'deleted'
  display_name?: string
  settings: {
    timezone: string
    language: string
    notification_preferences: {
      email_notifications: boolean
      system_alerts: boolean
    }
    ui_preferences: {
      theme: string
      dashboard_layout: string
    }
  }
  storage_quota_mb: number
  created_at?: string
  updated_at?: string
}

// 租户统计信息类型定义
export interface TenantStats {
  total_documents: number
  total_data_sources: number
  storage_used_mb: number
  processed_documents: number
  pending_documents: number
  storage_quota_mb: number
  storage_usage_percent: number
}

// 租户设置更新类型定义
export interface TenantUpdateData {
  display_name?: string
  settings?: Partial<Tenant['settings']>
  storage_quota_mb?: number
}

// Store状态接口
interface TenantStoreState {
  // 状态
  currentTenant: Tenant | null
  tenantStats: TenantStats | null
  isLoading: boolean
  error: string | null

  // 操作
  fetchTenantProfile: () => Promise<void>
  updateTenantProfile: (updateData: TenantUpdateData) => Promise<void>
  fetchTenantStats: () => Promise<void>
  clearTenantData: () => void
  setError: (error: string | null) => void
}

// API客户端
class TenantAPI {
  private baseURL: string

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = localStorage.getItem('auth_token')
    const url = `${this.baseURL}${endpoint}`

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || `HTTP error! status: ${response.status}`)
    }

    return response.json()
  }

  async getCurrentTenant(): Promise<Tenant> {
    return this.request<Tenant>('/tenants/me')
  }

  async updateCurrentTenant(updateData: TenantUpdateData): Promise<Tenant> {
    return this.request<Tenant>('/tenants/me', {
      method: 'PUT',
      body: JSON.stringify(updateData),
    })
  }

  async getTenantStats(): Promise<{ tenant_id: string; statistics: TenantStats; last_updated: string }> {
    return this.request<{ tenant_id: string; statistics: TenantStats; last_updated: string }>('/tenants/me/stats')
  }
}

// 创建API实例
const tenantAPI = new TenantAPI()

// 创建租户store
export const useTenantStore = create<TenantStoreState>()(
  devtools(
    (set, get) => ({
      // 初始状态
      currentTenant: null,
      tenantStats: null,
      isLoading: false,
      error: null,

      // 获取租户信息
      fetchTenantProfile: async () => {
        set({ isLoading: true, error: null })

        try {
          const tenant = await tenantAPI.getCurrentTenant()
          set({
            currentTenant: tenant,
            isLoading: false
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to fetch tenant profile',
            isLoading: false
          })
        }
      },

      // 更新租户信息
      updateTenantProfile: async (updateData: TenantUpdateData) => {
        set({ isLoading: true, error: null })

        try {
          const updatedTenant = await tenantAPI.updateCurrentTenant(updateData)
          set({
            currentTenant: updatedTenant,
            isLoading: false
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to update tenant profile',
            isLoading: false
          })
          throw error
        }
      },

      // 获取租户统计信息
      fetchTenantStats: async () => {
        set({ isLoading: true, error: null })

        try {
          const response = await tenantAPI.getTenantStats()
          set({
            tenantStats: response.statistics,
            isLoading: false
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to fetch tenant stats',
            isLoading: false
          })
        }
      },

      // 清除租户数据
      clearTenantData: () => {
        set({
          currentTenant: null,
          tenantStats: null,
          error: null,
          isLoading: false,
        })
      },

      // 设置错误
      setError: (error: string | null) => {
        set({ error })
      },
    }),
    {
      name: 'tenant-store',
    }
  )
)

// 选择器函数，用于组件中选择特定状态
export const useCurrentTenant = () => useTenantStore((state) => state.currentTenant)
export const useTenantStats = () => useTenantStore((state) => state.tenantStats)
export const useTenantLoading = () => useTenantStore((state) => state.isLoading)
export const useTenantError = () => useTenantStore((state) => state.error)

// Action hooks
export const useTenantActions = () => useTenantStore((state) => ({
  fetchTenantProfile: state.fetchTenantProfile,
  updateTenantProfile: state.updateTenantProfile,
  fetchTenantStats: state.fetchTenantStats,
  clearTenantData: state.clearTenantData,
  setError: state.setError,
}))

// Utility functions
export const getStorageUsageColor = (usagePercent: number): string => {
  if (usagePercent >= 90) return 'text-red-600'
  if (usagePercent >= 75) return 'text-yellow-600'
  return 'text-green-600'
}

export const getStorageUsageVariant = (usagePercent: number): 'default' | 'destructive' => {
  return usagePercent >= 90 ? 'destructive' : 'default'
}

export const formatFileSize = (mb: number): string => {
  if (mb < 1024) return `${mb} MB`
  return `${(mb / 1024).toFixed(1)} GB`
}

// 租户状态颜色映射
export const getStatusColor = (status: string): string => {
  switch (status) {
    case 'active':
      return 'text-green-600'
    case 'suspended':
      return 'text-yellow-600'
    case 'deleted':
      return 'text-red-600'
    default:
      return 'text-gray-600'
  }
}

export const getStatusBadgeVariant = (status: string): 'default' | 'secondary' | 'destructive' => {
  switch (status) {
    case 'active':
      return 'default'
    case 'suspended':
      return 'secondary'
    case 'deleted':
      return 'destructive'
    default:
      return 'secondary'
  }
}