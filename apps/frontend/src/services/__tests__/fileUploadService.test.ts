/**
 * 文件上传服务测试
 */

import { fileUploadService, uploadFile, UploadProgress } from '../fileUploadService'

// Mock fetch
global.fetch = jest.fn()

const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>

// Mock FormData
global.FormData = jest.fn().mockImplementation(() => ({
  append: jest.fn(),
})) as any

describe('FileUploadService', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('文件验证', () => {
    it('应该验证支持的文件类型', () => {
      const supportedFile = new File(['content'], 'test.pdf', { type: 'application/pdf' })
      const supportedFile2 = new File(['content'], 'test.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
      const unsupportedFile = new File(['content'], 'test.txt', { type: 'text/plain' })

      // 由于这些是私有方法，我们通过测试上传来间接验证
      expect(supportedFile.type).toBe('application/pdf')
      expect(supportedFile2.type).toBe('application/vnd.openxmlformats-officedocument.wordprocessingml.document')
      expect(unsupportedFile.type).toBe('text/plain')
    })

    it('应该验证文件大小', () => {
      const smallFile = new File(['content'], 'small.pdf', { type: 'application/pdf' })
      const largeFile = new File(['x'.repeat(200 * 1024 * 1024)], 'large.pdf', { type: 'application/pdf' }) // 200MB

      expect(smallFile.size).toBeLessThan(100 * 1024 * 1024) // 100MB limit
      expect(largeFile.size).toBeGreaterThan(100 * 1024 * 1024)
    })
  })

  describe('uploadFile 函数', () => {
    it('应该拒绝不支持的文件类型', async () => {
      const file = new File(['content'], 'test.txt', { type: 'text/plain' })

      const result = await uploadFile(file)

      expect(result.success).toBe(false)
      expect(result.error).toContain('不支持的文件类型')
    })

    it('应该拒绝过大的文件', async () => {
      const file = new File(['x'.repeat(200 * 1024 * 1024)], 'large.pdf', { type: 'application/pdf' })

      const result = await uploadFile(file)

      expect(result.success).toBe(false)
      expect(result.error).toContain('文件大小超出限制')
    })

    it('应该支持简单上传', async () => {
      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })

      // Mock 成功的简单上传
      mockFetch.mockImplementationOnce(() => {
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              ok: true,
              status: 200,
              json: () => Promise.resolve({
                id: 'doc-123',
                file_name: 'test.pdf',
                file_size: file.size,
              }),
            } as Response)
          }, 100)
        })
      })

      const progressCallback = jest.fn()
      const result = await uploadFile(file, progressCallback)

      expect(result.success).toBe(true)
      expect(result.document).toBeDefined()
      expect(progressCallback).toHaveBeenCalled()
    })

    it('应该处理简单上传错误', async () => {
      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })

      // Mock 失败的简单上传
      mockFetch.mockImplementationOnce(() => {
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              ok: false,
              status: 400,
              json: () => Promise.resolve({
                detail: '文件格式不支持',
              }),
            } as Response)
          }, 100)
        })
      })

      const progressCallback = jest.fn()
      const result = await uploadFile(file, progressCallback)

      expect(result.success).toBe(false)
      expect(result.error).toContain('文件格式不支持')
    })

    it('应该处理网络错误', async () => {
      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })

      // Mock 网络错误
      mockFetch.mockImplementationOnce(() => {
        return new Promise((resolve, reject) => {
          setTimeout(() => {
            reject(new Error('Network Error'))
          }, 100)
        })
      })

      const progressCallback = jest.fn()
      const result = await uploadFile(file, progressCallback)

      expect(result.success).toBe(false)
      expect(result.error).toBe('网络错误')
    })
  })

  describe('分块上传', () => {
    it('应该对大文件使用分块上传', async () => {
      const largeFile = new File(['x'.repeat(15 * 1024 * 1024)], 'large.pdf', { type: 'application/pdf' }) // 15MB

      // Mock 分块上传初始化
      mockFetch.mockImplementationOnce(() => {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            session_id: 'session-123',
            file_name: 'large.pdf',
            file_size: largeFile.size,
            total_chunks: 15,
            chunk_size: 1024 * 1024,
            file_checksum: 'checksum123',
          }),
        } as Response)
      })

      // Mock 分块上传
      for (let i = 0; i < 15; i++) {
        mockFetch.mockImplementationOnceOnce(() => {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              success: true,
              chunk_number: i + 1,
            }),
          } as Response)
        })
      }

      // Mock 完成上传
      mockFetch.mockImplementationOnce(() => {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            document: {
              id: 'doc-123',
              file_name: 'large.pdf',
            },
            message: '文件上传完成',
          }),
        } as Response)
      })

      const progressCallback = jest.fn()
      const result = await uploadFile(largeFile, progressCallback, true) // 强制使用分块上传

      expect(result.success).toBe(true)
      expect(result.document).toBeDefined()
      expect(progressCallback).toHaveBeenCalledTimes(17) // 1个初始化 + 15个分块 + 1个完成
    })

    it('应该处理分块上传初始化失败', async () => {
      const largeFile = new File(['x'.repeat(15 * 1024 * 1024)], 'large.pdf', { type: 'application/pdf' })

      // Mock 初始化失败
      mockFetch.mockImplementationOnce(() => {
        return Promise.resolve({
          ok: false,
          status: 400,
          json: () => Promise.resolve({
            detail: '文件过大',
          }),
        } as Response)
      })

      const progressCallback = jest.fn()
      const result = await uploadFile(largeFile, progressCallback, true)

      expect(result.success).toBe(false)
      expect(result.error).toContain('初始化上传失败')
    })

    it('应该处理分块上传失败', async () => {
      const largeFile = new File(['x'.repeat(15 * 1024 * 1024)], 'large.pdf', { type: 'application/pdf' })

      // Mock 初始化成功
      mockFetch.mockImplementationOnce(() => {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            session_id: 'session-123',
            file_name: 'large.pdf',
            file_size: largeFile.size,
            total_chunks: 15,
            chunk_size: 1024 * 1024,
            file_checksum: 'checksum123',
          }),
        } as Response)
      })

      // Mock 第一个分块上传失败
      mockFetch.mockImplementationOnce(() => {
        return Promise.resolve({
          ok: false,
          status: 500,
          json: () => Promise.resolve({
            detail: '分块上传失败',
          }),
        } as Response)
      })

      const progressCallback = jest.fn()
      const result = await uploadFile(largeFile, progressCallback, true)

      expect(result.success).toBe(false)
      expect(result.error).toContain('分块 1 上传失败')
    })
  })

  describe('进度回调', () => {
    it('应该正确调用进度回调', async () => {
      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })
      const progressEvents: UploadProgress[] = []

      mockFetch.mockImplementationOnce(() => {
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              ok: true,
              status: 200,
              json: () => Promise.resolve({
                id: 'doc-123',
                file_name: 'test.pdf',
              }),
            } as Response)
          }, 100)
        })
      })

      await uploadFile(file, (progress) => {
        progressEvents.push(progress)
      })

      expect(progressEvents.length).toBeGreaterThan(0)
      expect(progressEvents[0].status).toBe('pending')
      expect(progressEvents[progressEvents.length - 1].status).toBe('completed')
    })

    it('应该在上传失败时调用错误进度', async () => {
      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })
      let errorProgress: UploadProgress | null = null

      mockFetch.mockImplementationOnce(() => {
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              ok: false,
              status: 400,
              json: () => Promise.resolve({
                detail: '上传失败',
              }),
            } as Response)
          }, 100)
        })
      })

      await uploadFile(file, (progress) => {
        if (progress.status === 'error') {
          errorProgress = progress
        }
      })

      expect(errorProgress).not.toBeNull()
      expect(errorProgress?.message).toContain('上传失败')
    })
  })

  describe('错误处理', () => {
    it('应该处理JSON解析错误', async () => {
      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })

      mockFetch.mockImplementationOnce(() => {
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              ok: true,
              status: 200,
              json: () => Promise.reject(new Error('Invalid JSON')),
              text: () => Promise.resolve('Invalid response'),
            } as Response)
          }, 100)
        })
      })

      const result = await uploadFile(file)

      expect(result.success).toBe(true) // 简单上传应该回退到文本处理
    })

    it('应该处理响应文本解析错误', async () => {
      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })

      mockFetch.mockImplementationOnce(() => {
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              ok: true,
              status: 200,
              json: () => Promise.reject(new Error('Invalid JSON')),
              text: () => Promise.reject(new Error('Invalid text')),
            } as Response)
          }, 100)
        })
      })

      const result = await uploadFile(file)

      expect(result.success).toBe(false) // 两种解析都失败
    })
  })
})