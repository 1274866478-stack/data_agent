export enum DocumentStatus {
  PENDING = 'pending',
  INDEXING = 'indexing',
  READY = 'ready',
  ERROR = 'error'
}

export interface KnowledgeDocument {
  id: string
  tenant_id: string
  file_name: string
  storage_path: string
  file_type: 'pdf' | 'docx' | 'unknown'
  file_size: number
  mime_type: string
  status: DocumentStatus
  processing_error?: string
  indexed_at?: string
  created_at: string
  updated_at: string
}

export interface DocumentStats {
  by_status: Record<string, number>
  by_file_type: Record<string, number>
  total_documents: number
  total_size_bytes: number
  total_size_mb: number
}
