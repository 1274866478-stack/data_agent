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
import { useDataSourceStore, CreateDataSourceRequest } from '@/store/dataSourceStore'
import { FileUp, Database, Server } from 'lucide-react'

// 支持的数据库类型配置
const SUPPORTED_DATABASE_TYPES = {
  'postgresql': {
    name: 'PostgreSQL',
    icon: '🐘',
    placeholder: 'postgresql://username:password@localhost:5432/database_name',
    description: '流行的开源关系型数据库'
  },
  'mysql': {
    name: 'MySQL',
    icon: '🐬',
    placeholder: 'mysql://username:password@localhost:3306/database_name',
    description: '广泛使用的关系型数据库'
  },
}

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

type SourceMode = 'file' | 'database'

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

interface DatabaseDataSourceForm {
  name: string
  db_type: string
  connection_string: string
  create_db_if_not_exists: boolean
}

export function DataSourceForm({
  tenantId,
  initialData,
  onSubmit,
  onCancel,
  isLoading: externalLoading = false,
}: DataSourceFormProps) {
  const { createDataSource, isLoading, error } = useDataSourceStore()
  const [mode, setMode] = useState<SourceMode>('file')

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {mode === 'file' ? <FileUp className="h-5 w-5" /> : <Database className="h-5 w-5" />}
          {initialData ? '编辑数据源' : '添加数据源'}
        </CardTitle>
        <CardDescription>
          {mode === 'file' 
            ? '上传 CSV、Excel 或 SQLite 数据库文件'
            : '连接 PostgreSQL、MySQL 等数据库'
          }
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 模式切换 */}
        <div className="flex gap-2 p-1 bg-muted rounded-lg">
          <button
            type="button"
            onClick={() => setMode('file')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              mode === 'file'
                ? 'bg-background shadow-sm text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <FileUp className="h-4 w-4" />
            上传文件
          </button>
          <button
            type="button"
            onClick={() => setMode('database')}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              mode === 'database'
                ? 'bg-background shadow-sm text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <Server className="h-4 w-4" />
            连接数据库
          </button>
        </div>

        {mode === 'file' ? (
          <FileUploadFormContent
            tenantId={tenantId}
            initialData={initialData}
            onSubmit={onSubmit}
            onCancel={onCancel}
            isLoading={externalLoading || isLoading}
            error={error}
          />
        ) : (
          <DatabaseConnectionFormContent
            tenantId={tenantId}
            initialData={initialData}
            onSubmit={onSubmit}
            onCancel={onCancel}
            isLoading={externalLoading || isLoading}
            error={error}
          />
        )}
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
    setValue,
  } = useForm<DatabaseDataSourceForm>({
    defaultValues: {
      name: initialData?.name || '',
      db_type: initialData?.db_type || 'postgresql',
      connection_string: initialData?.connection_string || '',
      create_db_if_not_exists: true,  // 默认启用自动创建
    },
  })

  const watchedDbType = watch('db_type')
  const watchedName = watch('name')
  const watchedConnectionString = watch('connection_string')
  const watchedCreateDb = watch('create_db_if_not_exists')

  const currentDbConfig = SUPPORTED_DATABASE_TYPES[watchedDbType as keyof typeof SUPPORTED_DATABASE_TYPES]

  const [localError, setLocalError] = useState<string | null>(null)
  const [isLocalLoading, setIsLocalLoading] = useState(false)

  // 提交表单
  const handleFormSubmit = async (data: DatabaseDataSourceForm) => {
    console.log('=== 表单提交开始 ===')
    console.log('表单数据:', data)
    console.log('tenantId:', tenantId)

    setLocalError(null)

    if (!data.name.trim()) {
      setLocalError('请输入数据源名称')
      return
    }
    
    if (!data.connection_string.trim()) {
      setLocalError('请输入连接字符串')
      return
    }

    setIsLocalLoading(true)

    try {
      const createData: CreateDataSourceRequest = {
        name: data.name,
        connection_string: data.connection_string,
        db_type: data.db_type,
        create_db_if_not_exists: data.create_db_if_not_exists,
      }

      console.log('调用 createDataSource，数据:', createData)
      const result = await createDataSource(tenantId, createData)
      console.log('创建成功:', result)
      onSubmit?.(createData)
    } catch (err) {
      console.error('创建数据源失败:', err)
      setLocalError(err instanceof Error ? err.message : '创建数据源失败')
    } finally {
      setIsLocalLoading(false)
    }
  }

  const displayError = localError || error
  const isFormLoading = isLocalLoading || isLoading || isSubmitting

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      {displayError && <ErrorMessage message={displayError} />}

      {/* 数据源名称 */}
      <div className="space-y-2">
        <Label htmlFor="db-name">数据源名称 *</Label>
        <Input
          id="db-name"
          placeholder="例如：生产数据库、测试环境"
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
          {...register('db_type', { required: '请选择数据库类型' })}
          className="w-full px-3 py-2 border rounded-md bg-background"
        >
          {Object.entries(SUPPORTED_DATABASE_TYPES).map(([key, config]) => (
            <option key={key} value={key}>
              {config.icon} {config.name}
            </option>
          ))}
        </select>
        {currentDbConfig && (
          <p className="text-sm text-muted-foreground">{currentDbConfig.description}</p>
        )}
      </div>

      {/* 连接字符串 */}
      <div className="space-y-2">
        <Label htmlFor="connection-string">连接字符串 *</Label>
        <Input
          id="connection-string"
          placeholder={currentDbConfig?.placeholder || ''}
          className="font-mono text-sm"
          {...register('connection_string', {
            required: '请输入连接字符串',
            minLength: { value: 10, message: '连接字符串格式不正确' },
          })}
        />
        {errors.connection_string && (
          <p className="text-sm text-destructive">{errors.connection_string.message}</p>
        )}
        {currentDbConfig && (
          <p className="text-xs text-muted-foreground">
            格式示例：{currentDbConfig.placeholder}
          </p>
        )}
      </div>

      {/* 自动创建数据库选项 - 仅 PostgreSQL */}
      {watchedDbType === 'postgresql' && (
        <div className="flex items-center space-x-3 p-4 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800">
          <input
            type="checkbox"
            id="create-db"
            {...register('create_db_if_not_exists')}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <div className="flex-1">
            <Label htmlFor="create-db" className="text-sm font-medium cursor-pointer">
              如果数据库不存在则自动创建
            </Label>
            <p className="text-xs text-muted-foreground mt-0.5">
              勾选后，如果指定的数据库不存在，系统将自动在 PostgreSQL 服务器上创建该数据库
            </p>
          </div>
        </div>
      )}

      {/* 支持的数据库类型 */}
      <div className="bg-muted/50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-foreground mb-2">支持的数据库类型</h4>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(SUPPORTED_DATABASE_TYPES).map(([key, config]) => (
            <div key={key} className="flex items-center gap-2 text-sm">
              <span className="text-lg">{config.icon}</span>
              <div>
                <span className="font-medium">{config.name}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 表单按钮 */}
      <div className="flex gap-3 pt-4">
        <Button
          type="submit"
          disabled={isFormLoading || !watchedName || !watchedConnectionString}
          className="flex-1"
        >
          {isFormLoading ? (
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

