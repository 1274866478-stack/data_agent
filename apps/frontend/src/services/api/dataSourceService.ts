import { API_BASE_URL } from '@/lib/api-client'
import type {
  ConnectionTestRequest,
  CreateDataSourceRequest,
  DataSourceListParams,
  UpdateDataSourceRequest,
} from '@/types/api/dataSource'
import type { BulkOperationResult, DataSourceConnection, TestResult } from '@/types/store/dataSource'

const getAuthToken = (): string | null => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('auth_token')
  }
  return null
}

const requestJson = async <T>(endpoint: string, options: RequestInit = {}): Promise<T> => {
  const token = getAuthToken()
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
  }

  return response.json()
}

export const dataSourceService = {
  list: async (params: DataSourceListParams): Promise<DataSourceConnection[]> => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value))
      }
    })
    return requestJson<DataSourceConnection[]>(`/data-sources?${searchParams}`)
  },
  get: async (id: string, tenantId: string): Promise<DataSourceConnection> => {
    return requestJson<DataSourceConnection>(`/data-sources/${id}?tenant_id=${tenantId}`)
  },
  create: async (tenantId: string, data: CreateDataSourceRequest): Promise<DataSourceConnection> => {
    if (data.file) {
      const formData = new FormData()
      formData.append('file', data.file)
      formData.append('name', data.name)
      if (data.db_type) {
        formData.append('db_type', data.db_type)
      }

      const token = getAuthToken()
      const response = await fetch(`${API_BASE_URL}/data-sources/upload?tenant_id=${tenantId}`, {
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

      return response.json()
    }

    const cleanData = {
      name: data.name,
      connection_string: data.connection_string,
      db_type: data.db_type || 'postgresql',
      create_db_if_not_exists: data.create_db_if_not_exists || false,
    }

    return requestJson<DataSourceConnection>(`/data-sources?tenant_id=${tenantId}`, {
      method: 'POST',
      body: JSON.stringify(cleanData),
    })
  },
  update: async (id: string, tenantId: string, data: UpdateDataSourceRequest): Promise<DataSourceConnection> => {
    return requestJson<DataSourceConnection>(`/data-sources/${id}?tenant_id=${tenantId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  },
  remove: async (id: string, tenantId: string): Promise<void> => {
    await requestJson(`/data-sources/${id}?tenant_id=${tenantId}`, {
      method: 'DELETE',
    })
  },
  bulkDelete: async (
    tenantId: string,
    userId: string | undefined,
    ids: string[]
  ): Promise<BulkOperationResult> => {
    const params = new URLSearchParams()
    params.append('tenant_id', tenantId)
    if (userId) {
      params.append('user_id', userId)
    }

    return requestJson<BulkOperationResult>(`/data-sources/bulk-delete?${params}`, {
      method: 'POST',
      body: JSON.stringify({
        item_ids: ids,
        item_type: 'database',
      }),
    })
  },
  testConnection: async (data: ConnectionTestRequest): Promise<TestResult> => {
    return requestJson<TestResult>('/data-sources/test', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
  testExisting: async (id: string, tenantId: string): Promise<TestResult> => {
    return requestJson<TestResult>(`/data-sources/${id}/test?tenant_id=${tenantId}`, {
      method: 'POST',
    })
  },
  supportedTypes: async (): Promise<unknown> => {
    return requestJson('/data-sources/types/supported')
  },
}

export default dataSourceService
