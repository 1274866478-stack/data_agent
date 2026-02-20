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

export interface BulkOperationResult {
  success_count: number
  error_count: number
  errors: Array<{
    item_id: string
    error: string
  }>
}
