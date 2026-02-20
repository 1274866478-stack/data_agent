export interface DocumentApiItem {
  id: string
  tenant_id: string
  file_name: string
  storage_path: string
  file_type: string
  file_size: number
  mime_type: string
  status: string
  processing_error?: string
  indexed_at?: string
  created_at: string
  updated_at: string
}

export interface DocumentListResponse {
  documents: DocumentApiItem[]
  total: number
  stats?: Record<string, any>
}
