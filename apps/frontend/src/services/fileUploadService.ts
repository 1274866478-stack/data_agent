/**
 * 文件上传服务（文档域）
 *
 * 设计点：
 * - 自动选择普通上传 / 分块上传
 * - 统一认证头（兼容 auth_token / token）
 * - 统一 API 错误解析
 * - 统一上传进度回调
 */

import { API_BASE_URL } from '@/lib/api-client'
import { responseErrorMessage, extractApiErrorMessage } from '@/lib/api-error'
import { getStoredAuthToken } from '@/lib/auth-token'

export interface UploadProgress {
  loaded: number
  total: number
  percentage: number
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error'
  message?: string
}

export interface UploadSession {
  sessionId: string
  fileName: string
  fileSize: number
  mimeType: string
  totalChunks: number
  chunkSize: number
  fileChecksum: string
}

export interface UploadResult {
  success: boolean
  document?: any
  message?: string
  error?: string
}

class FileUploadService {
  private apiBase: string

  constructor() {
    this.apiBase = API_BASE_URL
  }

  /**
   * 获取认证头信息
   */
  private getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {}

    const token = getStoredAuthToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    return headers
  }

  /**
   * 检查文件类型是否支持
   */
  isFileTypeSupported(file: File): boolean {
    const supportedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]

    const supportedExtensions = ['.pdf', '.docx']
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))

    return supportedTypes.includes(file.type) || supportedExtensions.includes(fileExtension)
  }

  /**
   * 检查文件大小是否在限制范围内
   */
  private getFileTypeMaxSize(file: File): number {
    const extension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
    return extension === '.docx' ? 25 * 1024 * 1024 : 50 * 1024 * 1024
  }

  isFileSizeValid(file: File): boolean {
    return file.size <= this.getFileTypeMaxSize(file)
  }

  /**
   * 初始化分块上传会话
   */
  private async initializeChunkedUpload(file: File): Promise<UploadSession> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(`${this.apiBase}/upload/initialize`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: formData,
    })

    if (!response.ok) {
      throw new Error(await responseErrorMessage(response, '初始化上传失败'))
    }

    const data = await response.json()
    return {
      sessionId: data.session_id,
      fileName: data.file_name,
      fileSize: data.file_size,
      mimeType: data.mime_type,
      totalChunks: data.total_chunks,
      chunkSize: data.chunk_size,
      fileChecksum: data.file_checksum,
    }
  }

  /**
   * 上传单个分块
   */
  private async uploadChunk(
    sessionId: string,
    chunkNumber: number,
    chunkData: Blob
  ): Promise<void> {
    const formData = new FormData()
    formData.append('chunk_data', chunkData)

    const response = await fetch(
      `${this.apiBase}/upload/chunk/${sessionId}/${chunkNumber}`,
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: formData,
      }
    )

    if (!response.ok) {
      throw new Error(await responseErrorMessage(response, `分块 ${chunkNumber} 上传失败`))
    }
  }

  /**
   * 完成分块上传
   */
  private async completeChunkedUpload(sessionId: string): Promise<UploadResult> {
    const response = await fetch(`${this.apiBase}/upload/complete/${sessionId}`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      return {
        success: false,
        error: await responseErrorMessage(response, '完成上传失败'),
      }
    }

    const data = await response.json()
    return {
      success: data.success,
      document: data.document,
      message: data.message,
    }
  }

  /**
   * 执行分块上传
   */
  private async performChunkedUpload(
    file: File,
    onProgress?: (progress: UploadProgress) => void
  ): Promise<UploadResult> {
    try {
      // 初始化上传会话
      onProgress?.({
        loaded: 0,
        total: file.size,
        percentage: 0,
        status: 'pending',
        message: '初始化上传...',
      })

      const session = await this.initializeChunkedUpload(file)
      const chunkSize = session.chunkSize
      const totalChunks = session.totalChunks

      onProgress?.({
        loaded: 0,
        total: file.size,
        percentage: 0,
        status: 'uploading',
        message: '开始上传...',
      })

      // 流式切片上传，避免一次性持有全部分块
      for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
        const offset = chunkIndex * chunkSize
        const end = Math.min(offset + chunkSize, file.size)
        const chunk = file.slice(offset, end)
        await this.uploadChunk(session.sessionId, chunkIndex + 1, chunk)

        const loaded = Math.min((chunkIndex + 1) * chunkSize, file.size)
        const percentage = Math.round((loaded / file.size) * 100)

        onProgress?.({
          loaded,
          total: file.size,
          percentage,
          status: 'uploading',
          message: `上传中... ${percentage}%`,
        })
      }

      // 完成上传
      onProgress?.({
        loaded: file.size,
        total: file.size,
        percentage: 100,
        status: 'processing',
        message: '处理文件...',
      })

      const result = await this.completeChunkedUpload(session.sessionId)

      onProgress?.({
        loaded: file.size,
        total: file.size,
        percentage: 100,
        status: result.success ? 'completed' : 'error',
        message: result.message || (result.success ? '上传完成' : '上传失败'),
      })

      return result

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '上传过程中发生错误'

      onProgress?.({
        loaded: 0,
        total: file.size,
        percentage: 0,
        status: 'error',
        message: errorMessage,
      })

      return {
        success: false,
        error: errorMessage,
      }
    }
  }

  /**
   * 执行常规上传
   */
  private async performSimpleUpload(
    file: File,
    onProgress?: (progress: UploadProgress) => void
  ): Promise<UploadResult> {
    return new Promise((resolve) => {
      const formData = new FormData()
      formData.append('file', file)

      const xhr = new XMLHttpRequest()

      // 监听上传进度
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const percentage = Math.round((event.loaded / event.total) * 100)
          onProgress?.({
            loaded: event.loaded,
            total: event.total,
            percentage,
            status: 'uploading',
            message: `上传中... ${percentage}%`,
          })
        }
      })

      // 监听完成事件
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText)
            onProgress?.({
              loaded: file.size,
              total: file.size,
              percentage: 100,
              status: 'processing',
              message: '处理文件...',
            })

            setTimeout(() => {
              onProgress?.({
                loaded: file.size,
                total: file.size,
                percentage: 100,
                status: 'completed',
                message: '上传完成',
              })
            }, 1000)

            resolve({
              success: true,
              document: data,
            })
          } catch (error) {
            onProgress?.({
              loaded: 0,
              total: file.size,
              percentage: 0,
              status: 'error',
              message: '响应解析失败',
            })

            resolve({
              success: false,
              error: '响应解析失败',
            })
          }
        } else {
          try {
            const errorData = JSON.parse(xhr.responseText)
            const message = extractApiErrorMessage(errorData, '上传失败')
            onProgress?.({
              loaded: 0,
              total: file.size,
              percentage: 0,
              status: 'error',
              message,
            })

            resolve({
              success: false,
              error: message,
            })
          } catch {
            onProgress?.({
              loaded: 0,
              total: file.size,
              percentage: 0,
              status: 'error',
              message: `上传失败 (${xhr.status})`,
            })

            resolve({
              success: false,
              error: `上传失败 (${xhr.status})`,
            })
          }
        }
      })

      // 监听错误事件
      xhr.addEventListener('error', () => {
        onProgress?.({
          loaded: 0,
          total: file.size,
          percentage: 0,
          status: 'error',
          message: '网络错误',
        })

        resolve({
          success: false,
          error: '网络错误',
        })
      })

      // 监听取消事件
      xhr.addEventListener('abort', () => {
        onProgress?.({
          loaded: 0,
          total: file.size,
          percentage: 0,
          status: 'error',
          message: '上传已取消',
        })

        resolve({
          success: false,
          error: '上传已取消',
        })
      })

      // 开始上传
      onProgress?.({
        loaded: 0,
        total: file.size,
        percentage: 0,
        status: 'pending',
        message: '准备上传...',
      })

      xhr.open('POST', `${this.apiBase}/documents/upload`)

      // 添加认证头
      const authHeaders = this.getAuthHeaders()
      Object.entries(authHeaders).forEach(([key, value]) => {
        xhr.setRequestHeader(key, value)
      })

      xhr.send(formData)
    })
  }

  /**
   * 上传文件（自动选择上传方式）
   */
  async uploadFile(
    file: File,
    onProgress?: (progress: UploadProgress) => void,
    preferChunked: boolean = false
  ): Promise<UploadResult> {
    // 验证文件
    if (!this.isFileTypeSupported(file)) {
      return {
        success: false,
        error: '不支持的文件类型，仅支持 PDF、Word 文档',
      }
    }

    if (!this.isFileSizeValid(file)) {
      const maxSizeMb = Math.floor(this.getFileTypeMaxSize(file) / (1024 * 1024))
      return {
        success: false,
        error: `文件大小超出限制，最大允许 ${maxSizeMb}MB`,
      }
    }

    // 选择上传方式
    const shouldUseChunked = preferChunked || file.size > 10 * 1024 * 1024 // 10MB以上使用分块上传

    if (shouldUseChunked) {
      return this.performChunkedUpload(file, onProgress)
    } else {
      return this.performSimpleUpload(file, onProgress)
    }
  }

  /**
   * 获取上传状态
   */
  async getUploadStatus(sessionId: string): Promise<any> {
    const response = await fetch(`${this.apiBase}/upload/status/${sessionId}`, {
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error('获取上传状态失败')
    }

    return response.json()
  }

  /**
   * 取消上传会话
   */
  async abortUpload(sessionId: string): Promise<void> {
    const response = await fetch(`${this.apiBase}/upload/abort/${sessionId}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
    })

    if (!response.ok) {
      throw new Error('取消上传失败')
    }
  }

  /**
   * 获取支持的文件类型列表
   */
  getSupportedFileTypes(): string[] {
    return ['.pdf', '.docx']
  }

  /**
   * 获取最大文件大小(字节)
   */
  getMaxFileSize(): number {
    return 50 * 1024 * 1024 // PDF 50MB (DOCX 25MB)
  }

  /**
   * 格式化文件大小
   */
  formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }
}

// 创建单例实例
export const fileUploadService = new FileUploadService()

// 便捷函数导出
export const uploadFile = (
  file: File,
  onProgress?: (progress: UploadProgress) => void,
  preferChunked?: boolean
): Promise<UploadResult> => {
  return fileUploadService.uploadFile(file, onProgress, preferChunked)
}

export const getUploadStatus = (sessionId: string): Promise<any> => {
  return fileUploadService.getUploadStatus(sessionId)
}

export const abortUpload = (sessionId: string): Promise<void> => {
  return fileUploadService.abortUpload(sessionId)
}
