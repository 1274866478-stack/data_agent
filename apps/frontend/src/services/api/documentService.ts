import { API_BASE_URL } from '@/lib/api-client'
import type { DocumentApiItem, DocumentListResponse } from '@/types/api/document'

export const documentService = {
  list: async (params: URLSearchParams): Promise<DocumentListResponse> => {
    const response = await fetch(`${API_BASE_URL}/documents?${params}`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return response.json()
  },
  upload: async (file: File): Promise<DocumentApiItem> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: 'POST',
      body: formData,
    })
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || '上传失败')
    }
    return response.json()
  },
  remove: async (id: string): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/documents/${id}`, {
      method: 'DELETE',
    })
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || '删除失败')
    }
  },
  previewUrl: async (id: string, expiresHours: number): Promise<string> => {
    const response = await fetch(
      `${API_BASE_URL}/documents/${id}/preview?expires_in_hours=${expiresHours}`
    )
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || '获取预览链接失败')
    }
    const data = await response.json()
    return data.preview_url
  },
  downloadUrl: async (id: string): Promise<string> => {
    const response = await fetch(`${API_BASE_URL}/documents/${id}/download`)
    if (!response.ok) {
      throw new Error('获取下载链接失败')
    }
    return URL.createObjectURL(await response.blob())
  },
  process: async (id: string): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/documents/${id}/process`, {
      method: 'POST',
    })
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || '触发处理失败')
    }
  },
}

export default documentService
