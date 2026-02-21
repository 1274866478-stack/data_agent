import { API_BASE_URL } from '@/lib/api-client'
import { responseErrorMessage } from '@/lib/api-error'
import { getStoredAuthToken } from '@/lib/auth-token'
import type { DocumentApiItem, DocumentListResponse } from '@/types/api/document'

const buildAuthHeaders = (extraHeaders: HeadersInit = {}): HeadersInit => {
  const token = getStoredAuthToken()
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extraHeaders,
  }
}

export const documentService = {
  list: async (params: URLSearchParams): Promise<DocumentListResponse> => {
    const response = await fetch(`${API_BASE_URL}/documents?${params}`, {
      headers: buildAuthHeaders(),
    })
    if (!response.ok) {
      throw new Error(await responseErrorMessage(response, `HTTP error! status: ${response.status}`))
    }
    return response.json()
  },
  upload: async (file: File): Promise<DocumentApiItem> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: 'POST',
      headers: buildAuthHeaders(),
      body: formData,
    })
    if (!response.ok) {
      throw new Error(await responseErrorMessage(response, '上传失败'))
    }
    return response.json()
  },
  remove: async (id: string): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/documents/${id}`, {
      method: 'DELETE',
      headers: buildAuthHeaders(),
    })
    if (!response.ok) {
      throw new Error(await responseErrorMessage(response, '删除失败'))
    }
  },
  previewUrl: async (id: string, expiresHours: number): Promise<string> => {
    const response = await fetch(
      `${API_BASE_URL}/documents/${id}/preview?expires_in_hours=${expiresHours}`,
      {
        headers: buildAuthHeaders(),
      }
    )
    if (!response.ok) {
      throw new Error(await responseErrorMessage(response, '获取预览链接失败'))
    }
    const data = await response.json()
    return data.preview_url
  },
  downloadUrl: async (id: string): Promise<string> => {
    const response = await fetch(`${API_BASE_URL}/documents/${id}/download`, {
      headers: buildAuthHeaders(),
    })
    if (!response.ok) {
      throw new Error(await responseErrorMessage(response, '获取下载链接失败'))
    }
    return URL.createObjectURL(await response.blob())
  },
  process: async (id: string): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/documents/${id}/process`, {
      method: 'POST',
      headers: buildAuthHeaders(),
    })
    if (!response.ok) {
      throw new Error(await responseErrorMessage(response, '触发处理失败'))
    }
  },
}

export default documentService
