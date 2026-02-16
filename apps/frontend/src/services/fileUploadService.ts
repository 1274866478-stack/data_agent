/**
 * # [FILE_UPLOAD_SERVICE] 文件上传服务
 *
 * ## [MODULE]
 * **文件名**: fileUploadService.ts
 * **职责**: Story 2.4性能优化 - 支持分块上传和常规上传，与后端API集成，进度跟踪
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 文件上传服务
 *
 * ## [INPUT]
 * - **file: File** - 要上传的文件
 * - **onProgress?: (progress: UploadProgress) => void** - 进度回调函数
 * - **preferChunked?: boolean** - 是否优先使用分块上传（默认false）
 * - **sessionId: string** - 上传会话ID
 *
 * ## [OUTPUT]
 * - **UploadResult**: 上传结果
 *   - success: boolean - 是否成功
 *   - document?: any - 文档信息
 *   - message?: string - 成功消息
 *   - error?: string - 错误信息
 * - **UploadProgress**: 上传进度
 *   - loaded: number - 已上传字节数
 *   - total: number - 总字节数
 *   - percentage: number - 百分比（0-100）
 *   - status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error'
 *   - message?: string - 状态消息
 *
 * **上游依赖**:
 * - 无（独立服务）
 *
 * **下游依赖**:
 * - 无（Service是叶子服务模块）
 *
 * **调用方**:
 * - [../components/documents/DocumentUpload.tsx](../components/documents/DocumentUpload.tsx) - 文档上传组件
 * - [../store/documentStore](../store/documentStore.ts) - 文档Store调用uploadFile
 *
 * ## [STATE]
 * - **上传方式选择**:
 *   - 常规上传（XMLHttpRequest）: 文件≤10MB或preferChunked=false
 *   - 分块上传（fetch + FormData）: 文件>10MB或preferChunked=true
 * - **支持的文件类型**:
 *   - MIME类型: application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, application/msword
 *   - 扩展名: .pdf, .docx, .doc
 * - **文件大小限制**: 最大100MB
 * - **分块上传流程**:
 *   1. initializeChunkedUpload() - 初始化上传会话（POST /upload/initialize）
 *   2. uploadChunk() - 上传单个分块（POST /upload/chunk/{sessionId}/{chunkNumber}）
 *   3. completeChunkedUpload() - 完成上传（POST /upload/complete/{sessionId}）
 * - **常规上传流程**:
 *   - XMLHttpRequest上传（POST /documents/upload）
 *   - progress事件监听上传进度
 *   - load事件处理响应
 * - **进度回调**:
 *   - pending: 初始化阶段
 *   - uploading: 上传中（更新percentage）
 *   - processing: 处理中
 *   - completed: 上传完成
 *   - error: 上传失败
 * - **认证**: localStorage.getItem('token')获取Bearer token
 * - **校验和**: calculateFileChecksum()简化实现（32位hex）
 * - **分块计算**: file.slice(offset, end)切片
 *
 * ## [SIDE-EFFECTS]
 * - **HTTP请求**:
 *   - fetch()调用分块上传API
 *   - XMLHttpRequest调用常规上传API
 * - **FormData**: new FormData()包装文件和分块数据
 *   - **fetch**:
 *     - POST /upload/initialize（初始化）
 *     - POST /upload/chunk/{sessionId}/{chunkNumber}（上传分块）
 *     - POST /upload/complete/{sessionId}（完成上传）
 *     - GET /upload/status/{sessionId}（获取状态）
 *     - DELETE /upload/abort/{sessionId}（取消上传）
 *   - **XMLHttpRequest**:
 *     - POST /documents/upload（常规上传）
 *     - upload.progress事件监听进度
 *     - load/error/abort事件处理结果
 * - **localStorage**: localStorage.getItem('token')获取认证令牌
 * - **文件操作**:
 *   - file.name.lastIndexOf('.')提取扩展名
 *   - file.name.toLowerCase()转换小写
 *   - file.size检查文件大小
 *   - file.slice(offset, end)切片
 *   - file.arrayBuffer()读取文件内容
 * - **回调函数**: onProgress({loaded, total, percentage, status, message})更新进度
 * - **分块逻辑**:
 *   - for循环遍历分块（offset += chunkSize）
 *   - Math.min(offset + chunkSize, file.size)计算结束位置
 *   - chunks数组存储所有分块
 * - **进度计算**:
 *   - Math.round((loaded / file.size) * 100)计算百分比
 *   - Math.min((i + 1) * chunkSize, file.size)计算已上传字节数
 * - **try-catch**: 捕获网络错误和JSON解析错误
 * - **response.ok**: 检查HTTP状态码
 * - **异常处理**: try-catch捕获fetch和XMLHttpRequest错误，返回UploadResult（success=false）
 * - **单例模式**: fileUploadService全局实例
 * - **便捷函数**: uploadFile, getUploadStatus, abortUpload
 */

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
    this.apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'
  }

  /**
   * 获取认证头信息
   */
  private getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {}

    // 从 localStorage 获取 token
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token')
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
    }

    return headers
  }

  /**
   * 检查文件类型是否支持
   */
  isFileTypeSupported(file: File): boolean {
    const supportedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword'
    ]

    const supportedExtensions = ['.pdf', '.docx', '.doc']
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))

    return supportedTypes.includes(file.type) || supportedExtensions.includes(fileExtension)
  }

  /**
   * 检查文件大小是否在限制范围内
   */
  isFileSizeValid(file: File): boolean {
    const maxSize = 100 * 1024 * 1024 // 100MB
    return file.size <= maxSize
  }

  /**
   * 计算文件校验和
   */
  private async calculateFileChecksum(file: File): Promise<string> {
    // 简化实现，实际应用中应该使用更强的哈希算法
    const buffer = await file.arrayBuffer()
    const hashArray = Array.from(new Uint8Array(buffer))
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
    return hashHex.substring(0, 32) // 简化为32位
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
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || '初始化上传失败')
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
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `分块 ${chunkNumber} 上传失败`)
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
      const errorData = await response.json().catch(() => ({}))
      return {
        success: false,
        error: errorData.detail || '完成上传失败',
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

      // 分块上传
      const chunks: Blob[] = []
      const chunkSize = session.chunkSize

      for (let offset = 0; offset < file.size; offset += chunkSize) {
        const end = Math.min(offset + chunkSize, file.size)
        const chunk = file.slice(offset, end)
        chunks.push(chunk)
      }

      onProgress?.({
        loaded: 0,
        total: file.size,
        percentage: 0,
        status: 'uploading',
        message: '开始上传...',
      })

      // 上传所有分块
      for (let i = 0; i < chunks.length; i++) {
        await this.uploadChunk(session.sessionId, i + 1, chunks[i])

        const loaded = Math.min((i + 1) * chunkSize, file.size)
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
            onProgress?.({
              loaded: 0,
              total: file.size,
              percentage: 0,
              status: 'error',
              message: errorData.detail || '上传失败',
            })

            resolve({
              success: false,
              error: errorData.detail || '上传失败',
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
      return {
        success: false,
        error: '文件大小超出限制，最大允许 100MB',
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
    return ['.pdf', '.doc', '.docx']
  }

  /**
   * 获取最大文件大小(字节)
   */
  getMaxFileSize(): number {
    return 100 * 1024 * 1024 // 100MB
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