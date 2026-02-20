export interface CreateDataSourceRequest {
  name: string
  connection_string: string
  db_type?: string
  file?: File
  create_db_if_not_exists?: boolean
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

export interface DataSourceListParams {
  tenant_id: string
  db_type?: string
  active_only?: boolean
  skip?: number
  limit?: number
}
