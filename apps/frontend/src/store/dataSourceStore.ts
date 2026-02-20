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
import { dataSourceService } from '@/services/api'
import type { CreateDataSourceRequest, DataSourceListParams, UpdateDataSourceRequest } from '@/types/api/dataSource'
import type { BulkOperationResult, DataSourceConnection, TestResult } from '@/types/store/dataSource'
// Store状态接口
interface DataSourceState {
  // 状态
  dataSources: DataSourceConnection[]
  currentDataSource: DataSourceConnection | null
  isLoading: boolean
  error: string | null
  testResults: Record<string, TestResult>

  // Actions
  fetchDataSources: (tenantId: string, filters?: Omit<DataSourceListParams, 'tenant_id'>) => Promise<void>

  getDataSourceById: (id: string, tenantId: string) => Promise<DataSourceConnection | null>

  createDataSource: (tenantId: string, data: CreateDataSourceRequest) => Promise<DataSourceConnection>

  updateDataSource: (id: string, tenantId: string, data: UpdateDataSourceRequest) => Promise<DataSourceConnection>

  deleteDataSource: (id: string, tenantId: string) => Promise<void>

  bulkDeleteDataSources: (ids: string[], tenantId: string, userId?: string) => Promise<BulkOperationResult>

  testConnection: (connectionString: string, dbType?: string) => Promise<TestResult>

  testDataSourceConnection: (id: string, tenantId: string) => Promise<TestResult>

  getSupportedDatabaseTypes: () => Promise<unknown>

  clearError: () => void
  setCurrentDataSource: (dataSource: DataSourceConnection | null) => void
}


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
          const dataSources = await dataSourceService.list({
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
          const dataSource = await dataSourceService.get(id, tenantId)
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
          const newDataSource = await dataSourceService.create(tenantId, data)

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
          const updatedDataSource = await dataSourceService.update(id, tenantId, data)

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
          await dataSourceService.remove(id, tenantId)

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
          const result = await dataSourceService.bulkDelete(tenantId, userId, ids)

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
          const testResult = await dataSourceService.testConnection({
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
          const testResult = await dataSourceService.testExisting(id, tenantId)

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
          return await dataSourceService.supportedTypes()
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
