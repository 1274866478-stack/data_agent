/**
 * # [DATA_SOURCE_STORE] 数据源状态管理Store
 *
 * ## [MODULE]
 * **文件名**: dataSourceStore.ts
 * **职责**: 管理数据源连接列表、CRUD操作、连接测试、批量删除和API客户端封装，集成Zustand状态管理和TypeScript类型安全
 *
 * ## [INPUT]
 * Props (无 - Zustand Store):
 * - 接收tenantId进行数据查询
 * - 接收数据源创建/更新请求数据
 * - 接收文件上传数据
 *
 * ## [OUTPUT]
 * Store:
 * - **dataSources: DataSourceConnection[]** - 数据源连接列表
 * - **currentDataSource: DataSourceConnection | null** - 当前选中数据源
 * - **isLoading: boolean** - 加载状态
 * - **error: string | null** - 错误信息
 * - **testResults: Record<string, TestResult>** - 连接测试结果缓存
 * Actions:
 * - fetchDataSources(tenantId, filters) - 获取数据源列表
 * - getDataSourceById(id, tenantId) - 获取单个数据源
 * - createDataSource(tenantId, data) - 创建数据源（支持文件上传和连接字符串）
 * - updateDataSource(id, tenantId, data) - 更新数据源
 * - deleteDataSource(id, tenantId) - 删除数据源
 * - bulkDeleteDataSources(ids, tenantId, userId) - 批量删除数据源
 * - testConnection(connectionString, dbType) - 测试连接字符串
 * - testDataSourceConnection(id, tenantId) - 测试现有数据源连接
 * - getSupportedDatabaseTypes() - 获取支持的数据库类型
 * - clearError() - 清除错误
 * - setCurrentDataSource(dataSource) - 设置当前数据源
 *
 * **上游依赖**:
 * - [zustand](https://github.com/pmndrs/zustand) - 状态管理库
 * - [zustand/middleware](https://github.com/pmndrs/zustand#devtools) - devtools中间件
 *
 * **下游依赖**:
 * - 无（Store是叶子状态管理模块）
 *
 * **调用方**:
 * - [../components/data-sources/DataSourceList.tsx](../components/data-sources/DataSourceList.tsx) - 数据源列表
 * - [../components/data-sources/DataSourceForm.tsx](../components/data-sources/DataSourceForm.tsx) - 数据源表单
 * - [../components/data-sources/DataSourceCard.tsx](../components/data-sources/DataSourceCard.tsx) - 数据源卡片
 * - [../app/data-sources/page.tsx](../app/data-sources/page.tsx) - 数据源管理页面
 *
 * ## [STATE]
 * - **数据源列表**: 维护tenant的所有数据源连接
 * - **当前选中**: 跟踪当前操作的数据源
 * - **测试结果**: 缓存连接测试结果
 * - **API客户端**: 内置ApiClient类封装API调用
 * - **文件上传**: 支持CSV/Excel/SQLite文件上传创建数据源
 *
 * ## [SIDE-EFFECTS]
 * - HTTP请求（调用Backend API）
 * - 文件上传（FormData multipart）
 * - localStorage操作（读取auth_token）
 * - 开发工具集成（Zustand devtools）
 */

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

// 类型定义
export interface DataSourceConnection {
  id: string
  tenant_id: string
  name: string
  db_type: string
  status: 'active' | 'inactive' | 'error' | 'testing'
  host?: string
  port?: number
  database_name?: string
  last_tested_at?: string
  test_result?: TestResult
  created_at: string
  updated_at: string
}

export interface TestResult {
  success: boolean
  message: string
  response_time_ms: number
  details?: {
    database_type?: string
    server_version?: string
    database_name?: string
    current_user?: string
    connection_info?: {
      host?: string
      port?: number
      database?: string
    }
  }
  error_code?: string
  timestamp: string
}

export interface CreateDataSourceRequest {
  name: string
  connection_string: string
  db_type?: string
  file?: File  // 用于文件上传
  create_db_if_not_exists?: boolean  // 如果数据库不存在则自动创建
}

export interface UpdateDataSourceRequest {
  name?: string
  connection_string?: string
  db_type?: string
  is_active?: boolean
}

export interface ConnectionTestRequest {
  connection_string: string
  db_type?: string
}

// API响应类型
export interface ApiResponse<T> {
  data?: T
  error?: string
  message?: string
}

export interface BulkOperationResult {
  success_count: number
  error_count: number
  errors: Array<{
    item_id: string
    error: string
  }>
}

// Store状态接口
interface DataSourceState {
  // 状态
  dataSources: DataSourceConnection[]
  currentDataSource: DataSourceConnection | null
  isLoading: boolean
  error: string | null
  testResults: Record<string, TestResult>

  // Actions
  fetchDataSources: (tenantId: string, filters?: {
    db_type?: string
    active_only?: boolean
    skip?: number
    limit?: number
  }) => Promise<void>

  getDataSourceById: (id: string, tenantId: string) => Promise<DataSourceConnection | null>

  createDataSource: (tenantId: string, data: CreateDataSourceRequest) => Promise<DataSourceConnection>

  updateDataSource: (id: string, tenantId: string, data: UpdateDataSourceRequest) => Promise<DataSourceConnection>

  deleteDataSource: (id: string, tenantId: string) => Promise<void>

  bulkDeleteDataSources: (ids: string[], tenantId: string, userId?: string) => Promise<BulkOperationResult>

  testConnection: (connectionString: string, dbType?: string) => Promise<TestResult>

  testDataSourceConnection: (id: string, tenantId: string) => Promise<TestResult>

  getSupportedDatabaseTypes: () => Promise<any>

  clearError: () => void
  setCurrentDataSource: (dataSource: DataSourceConnection | null) => void
}

// API客户端
class ApiClient {
  private baseURL: string

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const token = this.getAuthToken()

    const headers = {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
      }

      return await response.json()
    } catch (error) {
      if (error instanceof Error) {
        throw error
      }
      throw new Error('Network error occurred')
    }
  }

  private getAuthToken(): string | null {
    // TODO: 从Clerk或认证store获取token
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth_token')
    }
    return null
  }

  // 数据源相关API
  async getDataSources(params: {
    tenant_id: string
    db_type?: string
    active_only?: boolean
    skip?: number
    limit?: number
  }): Promise<DataSourceConnection[]> {
    const searchParams = new URLSearchParams()

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value))
      }
    })

    return this.request<DataSourceConnection[]>(`/data-sources?${searchParams}`)
  }

  async getDataSource(id: string, tenantId: string): Promise<DataSourceConnection> {
    return this.request<DataSourceConnection>(`/data-sources/${id}?tenant_id=${tenantId}`)
  }

  async createDataSource(tenantId: string, data: CreateDataSourceRequest): Promise<DataSourceConnection> {
    console.log('ApiClient.createDataSource 调用:', { tenantId, data })

    // 如果包含文件，使用 FormData 进行上传
    if (data.file) {
      console.log('使用文件上传模式')
      const formData = new FormData()
      formData.append('file', data.file)
      formData.append('name', data.name)
      if (data.db_type) {
        formData.append('db_type', data.db_type)
      }

      const url = `${this.baseURL}/data-sources/upload?tenant_id=${tenantId}`
      const token = this.getAuthToken()

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
      }

      return await response.json()
    }

    // 传统的连接字符串方式
    console.log('使用连接字符串模式')

    // 清理数据,移除file字段
    const cleanData = {
      name: data.name,
      connection_string: data.connection_string,
      db_type: data.db_type || 'postgresql',
      create_db_if_not_exists: data.create_db_if_not_exists || false,
    }

    console.log('发送到API的数据:', cleanData)

    return this.request<DataSourceConnection>(`/data-sources?tenant_id=${tenantId}`, {
      method: 'POST',
      body: JSON.stringify(cleanData),
    })
  }

  async updateDataSource(id: string, tenantId: string, data: UpdateDataSourceRequest): Promise<DataSourceConnection> {
    return this.request<DataSourceConnection>(`/data-sources/${id}?tenant_id=${tenantId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteDataSource(id: string, tenantId: string): Promise<void> {
    await this.request(`/data-sources/${id}?tenant_id=${tenantId}`, {
      method: 'DELETE',
    })
  }

  async bulkDeleteDataSources(tenantId: string, userId: string | undefined, ids: string[]): Promise<BulkOperationResult> {
    const params = new URLSearchParams()
    params.append('tenant_id', tenantId)
    if (userId) {
      params.append('user_id', userId)
    }

    const token = this.getAuthToken()
    return this.request<BulkOperationResult>(`/data-sources/bulk-delete?${params}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: JSON.stringify({
        item_ids: ids,
        item_type: 'database',
      }),
    })
  }

  async testConnection(data: ConnectionTestRequest): Promise<TestResult> {
    return this.request<TestResult>('/data-sources/test', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async testDataSourceConnection(id: string, tenantId: string): Promise<TestResult> {
    return this.request<TestResult>(`/data-sources/${id}/test?tenant_id=${tenantId}`, {
      method: 'POST',
    })
  }

  async getSupportedDatabaseTypes(): Promise<any> {
    return this.request<any>('/data-sources/types/supported')
  }
}

// 创建API客户端实例
const apiClient = new ApiClient()

// 创建store
export const useDataSourceStore = create<DataSourceState>()(
  devtools(
    (set, get) => ({
      // 初始状态
      dataSources: [],
      currentDataSource: null,
      isLoading: false,
      error: null,
      testResults: {},

      // Actions
      fetchDataSources: async (tenantId, filters = {}) => {
        set({ isLoading: true, error: null })

        try {
          const dataSources = await apiClient.getDataSources({
            tenant_id: tenantId,
            ...filters,
          })

          set({
            dataSources,
            isLoading: false
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to fetch data sources',
            isLoading: false
          })
        }
      },

      getDataSourceById: async (id, tenantId) => {
        try {
          const dataSource = await apiClient.getDataSource(id, tenantId)
          set({ currentDataSource: dataSource })
          return dataSource
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to fetch data source'
          })
          return null
        }
      },

      createDataSource: async (tenantId, data) => {
        set({ isLoading: true, error: null })

        try {
          const newDataSource = await apiClient.createDataSource(tenantId, data)

          set(state => ({
            dataSources: [newDataSource, ...state.dataSources],
            isLoading: false
          }))

          return newDataSource
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to create data source',
            isLoading: false
          })
          throw error
        }
      },

      updateDataSource: async (id, tenantId, data) => {
        set({ isLoading: true, error: null })

        try {
          const updatedDataSource = await apiClient.updateDataSource(id, tenantId, data)

          set(state => ({
            dataSources: state.dataSources.map(ds =>
              ds.id === id ? updatedDataSource : ds
            ),
            currentDataSource: state.currentDataSource?.id === id
              ? updatedDataSource
              : state.currentDataSource,
            isLoading: false
          }))

          return updatedDataSource
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to update data source',
            isLoading: false
          })
          throw error
        }
      },

      deleteDataSource: async (id, tenantId) => {
        set({ isLoading: true, error: null })

        try {
          await apiClient.deleteDataSource(id, tenantId)

          set(state => ({
            dataSources: state.dataSources.filter(ds => ds.id !== id),
            currentDataSource: state.currentDataSource?.id === id
              ? null
              : state.currentDataSource,
            isLoading: false
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to delete data source',
            isLoading: false
          })
          throw error
        }
      },

      bulkDeleteDataSources: async (ids, tenantId, userId) => {
        if (ids.length === 0) {
          return { success_count: 0, error_count: 0, errors: [] }
        }

        set({ isLoading: true, error: null })

        try {
          const result = await apiClient.bulkDeleteDataSources(tenantId, userId, ids)

          set(state => ({
            dataSources: state.dataSources.filter(ds => !ids.includes(ds.id)),
            currentDataSource: state.currentDataSource && ids.includes(state.currentDataSource.id)
              ? null
              : state.currentDataSource,
            isLoading: false
          }))

          return result
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to bulk delete data sources',
            isLoading: false
          })
          throw error
        }
      },

      testConnection: async (connectionString, dbType = 'postgresql') => {
        try {
          const testResult = await apiClient.testConnection({
            connection_string: connectionString,
            db_type: dbType,
          })

          // 存储测试结果
          const testKey = `${connectionString.substring(0, 20)}_${Date.now()}`
          set(state => ({
            testResults: {
              ...state.testResults,
              [testKey]: testResult
            }
          }))

          return testResult
        } catch (error) {
          const errorResult: TestResult = {
            success: false,
            message: error instanceof Error ? error.message : 'Connection test failed',
            response_time_ms: 0,
            error_code: 'TEST_ERROR',
            timestamp: new Date().toISOString(),
          }

          return errorResult
        }
      },

      testDataSourceConnection: async (id, tenantId) => {
        try {
          const testResult = await apiClient.testDataSourceConnection(id, tenantId)

          // 更新对应数据源的测试结果
          set(state => ({
            dataSources: state.dataSources.map(ds =>
              ds.id === id
                ? { ...ds, test_result: testResult, last_tested_at: testResult.timestamp }
                : ds
            ),
            currentDataSource: state.currentDataSource?.id === id
              ? { ...state.currentDataSource, test_result: testResult, last_tested_at: testResult.timestamp }
              : state.currentDataSource,
          }))

          return testResult
        } catch (error) {
          const errorResult: TestResult = {
            success: false,
            message: error instanceof Error ? error.message : 'Connection test failed',
            response_time_ms: 0,
            error_code: 'TEST_ERROR',
            timestamp: new Date().toISOString(),
          }

          return errorResult
        }
      },

      getSupportedDatabaseTypes: async () => {
        try {
          return await apiClient.getSupportedDatabaseTypes()
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to fetch supported database types'
          })
          return null
        }
      },

      clearError: () => set({ error: null }),

      setCurrentDataSource: (dataSource) => set({ currentDataSource: dataSource }),
    }),
    {
      name: 'data-source-store',
    }
  )
)