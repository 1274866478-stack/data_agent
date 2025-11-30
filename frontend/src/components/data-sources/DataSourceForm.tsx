'use client'

import { useState, useRef } from 'react'
import { useForm } from 'react-hook-form'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { ErrorMessage } from '@/components/ui/error-message'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useDataSourceStore, CreateDataSourceRequest } from '@/store/dataSourceStore'
import { Database, FileUp } from 'lucide-react'

// 支持的文件类型配置
const SUPPORTED_FILE_TYPES = {
  'csv': {
    mimeTypes: ['text/csv', 'application/vnd.ms-excel'],
    extensions: ['.csv'],
    maxSize: 100 * 1024 * 1024, // 100MB
    icon: '📊',
    description: 'CSV 表格文件'
  },
  'xlsx': {
    mimeTypes: ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
    extensions: ['.xlsx'],
    maxSize: 100 * 1024 * 1024, // 100MB
    icon: '📗',
    description: 'Excel 表格文件'
  },
  'xls': {
    mimeTypes: ['application/vnd.ms-excel'],
    extensions: ['.xls'],
    maxSize: 100 * 1024 * 1024, // 100MB
    icon: '📗',
    description: 'Excel 表格文件 (旧版)'
  },
  'db': {
    mimeTypes: ['application/x-sqlite3', 'application/octet-stream'],
    extensions: ['.db', '.sqlite', '.sqlite3'],
    maxSize: 500 * 1024 * 1024, // 500MB
    icon: '🗄️',
    description: 'SQLite 数据库文件'
  }
}

interface DataSourceFormProps {
  tenantId: string
  initialData?: Partial<CreateDataSourceRequest>
  onSubmit?: (data: CreateDataSourceRequest) => void
  onCancel?: () => void
  isLoading?: boolean
}

interface FileDataSourceForm {
  name: string
  file: File | null
  file_type: string
}

interface DatabaseConnectionForm {
  name: string
  connection_string: string
  db_type: string
}

export function DataSourceForm({
  tenantId,
  initialData,
  onSubmit,
  onCancel,
  isLoading: externalLoading = false,
}: DataSourceFormProps) {
  const [activeTab, setActiveTab] = useState<'database' | 'file'>('database')
  const { createDataSource, isLoading, error } = useDataSourceStore()

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>{initialData ? '编辑数据源' : '添加数据源'}</CardTitle>
        <CardDescription>
          选择数据库连接或上传数据文件
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'database' | 'file')}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="database" className="flex items-center gap-2">
              <Database className="h-4 w-4" />
              数据库连接
            </TabsTrigger>
            <TabsTrigger value="file" className="flex items-center gap-2">
              <FileUp className="h-4 w-4" />
              文件上传
            </TabsTrigger>
          </TabsList>

          <TabsContent value="database" className="space-y-4 mt-6">
            <DatabaseConnectionFormContent
              tenantId={tenantId}
              initialData={initialData}
              onSubmit={onSubmit}
              onCancel={onCancel}
              isLoading={externalLoading || isLoading}
              error={error}
            />
          </TabsContent>

          <TabsContent value="file" className="space-y-4 mt-6">
            <FileUploadFormContent
              tenantId={tenantId}
              initialData={initialData}
              onSubmit={onSubmit}
              onCancel={onCancel}
              isLoading={externalLoading || isLoading}
              error={error}
            />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

// 数据库连接表单组件
function DatabaseConnectionFormContent({
  tenantId,
  initialData,
  onSubmit,
  onCancel,
  isLoading,
  error,
}: {
  tenantId: string
  initialData?: Partial<CreateDataSourceRequest>
  onSubmit?: (data: CreateDataSourceRequest) => void
  onCancel?: () => void
  isLoading: boolean
  error: string | null
}) {
  const { createDataSource } = useDataSourceStore()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
  } = useForm<DatabaseConnectionForm>({
    defaultValues: {
      name: initialData?.name || '',
      connection_string: '',
      db_type: 'postgresql',
    },
  })

  // 监听表单值变化(用于调试)
  const formValues = watch()

  const handleFormSubmit = async (data: DatabaseConnectionForm) => {
    try {
      // 验证连接字符串不为空
      if (!data.connection_string || data.connection_string.trim().length === 0) {
        console.error('连接字符串为空:', data)
        return
      }

      console.log('提交数据库连接表单:', data)

      const createData: CreateDataSourceRequest = {
        name: data.name.trim(),
        connection_string: data.connection_string.trim(),
        db_type: data.db_type,
      }

      console.log('准备创建数据源:', createData)

      await createDataSource(tenantId, createData)
      onSubmit?.(createData)
    } catch (error) {
      console.error('创建数据源失败:', error)
      // 错误已由store处理
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      {error && <ErrorMessage message={error} />}

      {/* 调试信息 */}
      {process.env.NODE_ENV === 'development' && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-xs">
          <p className="font-bold mb-1">🐛 调试信息:</p>
          <p>名称: {formValues.name || '(空)'}</p>
          <p>连接字符串: {formValues.connection_string || '(空)'}</p>
          <p>数据库类型: {formValues.db_type || '(空)'}</p>
        </div>
      )}

      {/* 数据源名称 */}
      <div className="space-y-2">
        <Label htmlFor="db-name">数据源名称 *</Label>
        <Input
          id="db-name"
          placeholder="例如：生产数据库、ChatBI测试数据库"
          {...register('name', {
            required: '请输入数据源名称',
            minLength: { value: 1, message: '数据源名称不能为空' },
            maxLength: { value: 255, message: '数据源名称不能超过255个字符' },
          })}
        />
        {errors.name && (
          <p className="text-sm text-destructive">{errors.name.message}</p>
        )}
      </div>

      {/* 数据库类型 */}
      <div className="space-y-2">
        <Label htmlFor="db-type">数据库类型 *</Label>
        <select
          id="db-type"
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          {...register('db_type', { required: '请选择数据库类型' })}
        >
          <option value="postgresql">PostgreSQL</option>
          <option value="mysql">MySQL</option>
          <option value="sqlite">SQLite</option>
        </select>
        {errors.db_type && (
          <p className="text-sm text-destructive">{errors.db_type.message}</p>
        )}
      </div>

      {/* 连接字符串 */}
      <div className="space-y-2">
        <Label htmlFor="connection-string">连接字符串 *</Label>
        <Input
          id="connection-string"
          type="text"
          placeholder="postgresql://user:password@localhost:5432/database"
          {...register('connection_string', {
            required: '请输入连接字符串',
            minLength: { value: 1, message: '连接字符串不能为空' },
          })}
        />
        {errors.connection_string && (
          <p className="text-sm text-destructive">{errors.connection_string.message}</p>
        )}
        <p className="text-xs text-muted-foreground">
          示例: postgresql://username:password@host:port/database
        </p>
      </div>

      {/* 表单按钮 */}
      <div className="flex gap-3 pt-4">
        <Button
          type="submit"
          disabled={isSubmitting || isLoading}
          className="flex-1"
        >
          {(isSubmitting || isLoading) ? (
            <>
              <LoadingSpinner className="mr-2 h-4 w-4" />
              {initialData ? '更新中...' : '创建中...'}
            </>
          ) : (
            initialData ? '更新数据源' : '创建数据源'
          )}
        </Button>

        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            取消
          </Button>
        )}
      </div>
    </form>
  )
}

// 文件上传表单组件
function FileUploadFormContent({
  tenantId,
  initialData,
  onSubmit,
  onCancel,
  isLoading,
  error,
}: {
  tenantId: string
  initialData?: Partial<CreateDataSourceRequest>
  onSubmit?: (data: CreateDataSourceRequest) => void
  onCancel?: () => void
  isLoading: boolean
  error: string | null
}) {
  const { createDataSource } = useDataSourceStore()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    setValue,
    watch,
  } = useForm<FileDataSourceForm>({
    defaultValues: {
      name: initialData?.name || '',
      file: null,
      file_type: '',
    },
  })

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)

  const watchedName = watch('name')

  // 获取支持的文件扩展名
  const getSupportedExtensions = (): string => {
    return Object.values(SUPPORTED_FILE_TYPES)
      .flatMap(type => type.extensions)
      .join(',')
  }

  // 验证文件类型
  const validateFileType = (file: File): { valid: boolean; fileType?: string; error?: string } => {
    const fileName = file.name.toLowerCase()
    const extension = '.' + fileName.split('.').pop()

    for (const [key, config] of Object.entries(SUPPORTED_FILE_TYPES)) {
      if (config.extensions.includes(extension)) {
        if (file.size > config.maxSize) {
          return {
            valid: false,
            error: `文件大小超出限制，${config.description}最大允许 ${config.maxSize / (1024 * 1024)}MB`
          }
        }
        return { valid: true, fileType: key }
      }
    }

    return {
      valid: false,
      error: '不支持的文件类型，请上传 CSV、Excel (.xls/.xlsx) 或 SQLite 数据库 (.db) 文件'
    }
  }

  // 获取文件类型图标
  const getFileTypeIcon = (fileType: string): string => {
    return SUPPORTED_FILE_TYPES[fileType as keyof typeof SUPPORTED_FILE_TYPES]?.icon || '📁'
  }

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  // 处理文件选择
  const handleFileSelect = (file: File) => {
    const validation = validateFileType(file)

    if (!validation.valid) {
      setFileError(validation.error || '文件验证失败')
      setSelectedFile(null)
      return
    }

    setFileError(null)
    setSelectedFile(file)
    setValue('file_type', validation.fileType || '')

    if (!watchedName) {
      const defaultName = file.name.replace(/\.[^/.]+$/, '')
      setValue('name', defaultName)
    }
  }

  // 处理文件输入变化
  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (files && files.length > 0) {
      handleFileSelect(files[0])
    }
  }

  // 处理拖拽事件
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  // 处理文件放置
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  // 移除已选文件
  const handleRemoveFile = () => {
    setSelectedFile(null)
    setFileError(null)
    setValue('file_type', '')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // 提交表单
  const handleFormSubmit = async (data: FileDataSourceForm) => {
    if (!selectedFile) {
      setFileError('请选择一个文件')
      return
    }

    if (!data.name.trim()) {
      return
    }

    try {
      const createData: CreateDataSourceRequest = {
        name: data.name,
        connection_string: `file://${selectedFile.name}`,
        db_type: data.file_type,
        file: selectedFile,
      }

      await createDataSource(tenantId, createData)
      onSubmit?.(createData)
    } catch (error) {
      // 错误已由store处理
    }
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      {error && <ErrorMessage message={error} />}

      {/* 数据源名称 */}
      <div className="space-y-2">
        <Label htmlFor="file-name">数据源名称 *</Label>
        <Input
          id="file-name"
          placeholder="例如：销售数据、用户信息"
          {...register('name', {
            required: '请输入数据源名称',
            minLength: { value: 1, message: '数据源名称不能为空' },
            maxLength: { value: 255, message: '数据源名称不能超过255个字符' },
          })}
        />
        {errors.name && (
          <p className="text-sm text-destructive">{errors.name.message}</p>
        )}
      </div>

      {/* 文件上传区域 */}
      <div className="space-y-2">
        <Label>上传文件 *</Label>
        <div
          className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragActive
              ? 'border-blue-400 bg-blue-50'
              : fileError
              ? 'border-red-300 bg-red-50'
              : selectedFile
              ? 'border-green-300 bg-green-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          {selectedFile ? (
            <div className="space-y-3">
              <div className="text-4xl">{getFileTypeIcon(watch('file_type'))}</div>
              <div>
                <p className="text-lg font-medium text-gray-900">{selectedFile.name}</p>
                <p className="text-sm text-gray-500">
                  {formatFileSize(selectedFile.size)} · {watch('file_type').toUpperCase()}
                </p>
              </div>
              <div className="flex justify-center gap-2">
                <label className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground h-8 px-3 cursor-pointer">
                  更换文件
                  <input
                    type="file"
                    accept={getSupportedExtensions()}
                    onChange={handleFileInputChange}
                    className="sr-only"
                  />
                </label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleRemoveFile}
                  className="text-red-600 hover:text-red-700"
                >
                  移除
                </Button>
              </div>
            </div>
          ) : (
            <label className="block space-y-4 cursor-pointer">
              <input
                type="file"
                accept={getSupportedExtensions()}
                onChange={handleFileInputChange}
                className="sr-only"
              />
              <div className="text-4xl">📁</div>
              <div>
                <p className="text-base font-medium text-gray-900">
                  拖拽文件到这里，或者点击选择文件
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  支持 CSV、Excel (.xls/.xlsx) 和 SQLite 数据库 (.db) 文件
                </p>
              </div>
              <p className="text-xs text-gray-400">
                文件大小限制：表格文件 100MB，数据库文件 500MB
              </p>
            </label>
          )}
        </div>
        {fileError && (
          <p className="text-sm text-destructive">{fileError}</p>
        )}
      </div>

      {/* 支持的文件类型 */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-700 mb-2">支持的文件类型</h4>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(SUPPORTED_FILE_TYPES).map(([key, config]) => (
            <div key={key} className="flex items-center gap-2 text-sm">
              <span className="text-lg">{config.icon}</span>
              <div>
                <span className="font-medium">{config.extensions.join(', ')}</span>
                <span className="text-gray-500 ml-2">{config.maxSize / (1024 * 1024)}MB</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 表单按钮 */}
      <div className="flex gap-3 pt-4">
        <Button
          type="submit"
          disabled={isSubmitting || isLoading || !selectedFile || !watchedName}
          className="flex-1"
        >
          {(isSubmitting || isLoading) ? (
            <>
              <LoadingSpinner className="mr-2 h-4 w-4" />
              {initialData ? '更新中...' : '创建中...'}
            </>
          ) : (
            initialData ? '更新数据源' : '创建数据源'
          )}
        </Button>

        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>
            取消
          </Button>
        )}
      </div>
    </form>
  )
}

