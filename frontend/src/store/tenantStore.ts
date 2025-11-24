/**
 * 租户状态管理
 * 实现Story-2.2要求的前端租户管理
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