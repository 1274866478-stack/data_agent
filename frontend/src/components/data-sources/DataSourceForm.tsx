'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { ErrorMessage } from '@/components/ui/error-message'
import { useDataSourceStore, CreateDataSourceRequest, TestResult } from '@/store/dataSourceStore'

interface DataSourceFormProps {
  tenantId: string
  initialData?: Partial<CreateDataSourceRequest>
  onSubmit?: (data: CreateDataSourceRequest) => void
  onCancel?: () => void
  isLoading?: boolean
}

export function DataSourceForm({
  tenantId,
  initialData,
  onSubmit,
  onCancel,
  isLoading: externalLoading = false,
}: DataSourceFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
    setError,
    setValue,
  } = useForm<CreateDataSourceRequest>({
    defaultValues: {
      name: '',
      connection_string: '',
      db_type: 'postgresql',
      ...initialData,
    },
  })

  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [isTesting, setIsTesting] = useState(false)

  const { testConnection, createDataSource } = useDataSourceStore()

  const watchedConnectionString = watch('connection_string')
  const watchedDbType = watch('db_type')

  // 连接字符串格式验证
  const validateConnectionString = (connectionString: string, dbType: string): boolean => {
    if (!connectionString) return false

    try {
      const url = new URL(connectionString)

      switch (dbType) {
        case 'postgresql':
          return url.protocol === 'postgresql:' && url.hostname && url.pathname
        case 'mysql':
          return url.protocol === 'mysql:' && url.hostname && url.pathname
        default:
          return false
      }
    } catch {
      return false
    }
  }

  // 获取连接字符串示例
  const getConnectionStringExample = (dbType: string): string => {
    switch (dbType) {
      case 'postgresql':
        return 'postgresql://username:password@localhost:5432/database_name'
      case 'mysql':
        return 'mysql://username:password@localhost:3306/database_name'
      default:
        return ''
    }
  }

  // 测试连接
  const handleTestConnection = async () => {
    const connectionString = watchedConnectionString
    const dbType = watchedDbType

    if (!connectionString) {
      setError('connection_string', { message: '请输入连接字符串' })
      return
    }

    if (!validateConnectionString(connectionString, dbType)) {
      setError('connection_string', { message: '连接字符串格式不正确' })
      return
    }

    setIsTesting(true)
    setTestResult(null)

    try {
      const result = await testConnection(connectionString, dbType)
      setTestResult(result)

      if (!result.success) {
        setError('connection_string', { message: `连接测试失败: ${result.message}` })
      }
    } catch (error) {
      const errorResult: TestResult = {
        success: false,
        message: error instanceof Error ? error.message : '连接测试失败',
        response_time_ms: 0,
        error_code: 'TEST_ERROR',
        timestamp: new Date().toISOString(),
      }
      setTestResult(errorResult)
      setError('connection_string', { message: errorResult.message })
    } finally {
      setIsTesting(false)
    }
  }

  // 提交表单
  const handleFormSubmit = async (data: CreateDataSourceRequest) => {
    if (!validateConnectionString(data.connection_string, data.db_type)) {
      setError('connection_string', { message: '连接字符串格式不正确，请先测试连接' })
      return
    }

    try {
      await createDataSource(tenantId, data)
      onSubmit?.(data)
    } catch (error) {
      // 错误已由store处理
    }
  }

  const getStatusColor = (success?: boolean) => {
    if (success === undefined) return 'secondary'
    return success ? 'default' : 'destructive'
  }

  const getStatusText = (success?: boolean) => {
    if (success === undefined) return '未测试'
    return success ? '连接成功' : '连接失败'
  }

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>{initialData ? '编辑数据源' : '添加数据源'}</CardTitle>
        <CardDescription>
          配置外部数据库连接，支持 PostgreSQL 和 MySQL
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
          {/* 数据源名称 */}
          <div className="space-y-2">
            <Label htmlFor="name">数据源名称 *</Label>
            <Input
              id="name"
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
            <Label htmlFor="db_type">数据库类型 *</Label>
            <select
              id="db_type"
              className="w-full p-2 border rounded-md bg-background"
              {...register('db_type', { required: '请选择数据库类型' })}
            >
              <option value="postgresql">PostgreSQL</option>
              <option value="mysql">MySQL</option>
            </select>
            {errors.db_type && (
              <p className="text-sm text-destructive">{errors.db_type.message}</p>
            )}
          </div>

          {/* 连接字符串 */}
          <div className="space-y-2">
            <Label htmlFor="connection_string">连接字符串 *</Label>
            <Input
              id="connection_string"
              placeholder={getConnectionStringExample(watchedDbType)}
              className="font-mono text-sm"
              {...register('connection_string', {
                required: '请输入连接字符串',
                validate: (value) => {
                  if (!value) return '请输入连接字符串'
                  if (!validateConnectionString(value, watchedDbType)) {
                    return '连接字符串格式不正确'
                  }
                  return true
                },
              })}
            />
            {errors.connection_string && (
              <p className="text-sm text-destructive">{errors.connection_string.message}</p>
            )}

            {/* 连接字符串格式说明 */}
            <div className="text-xs text-muted-foreground">
              格式示例：{getConnectionStringExample(watchedDbType)}
            </div>

            {/* 测试连接按钮 */}
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleTestConnection}
                disabled={isTesting || !watchedConnectionString}
              >
                {isTesting ? (
                  <>
                    <LoadingSpinner className="mr-2 h-4 w-4" />
                    测试中...
                  </>
                ) : (
                  '测试连接'
                )}
              </Button>

              {/* 测试结果 */}
              {testResult && (
                <Badge variant={getStatusColor(testResult.success)}>
                  {getStatusText(testResult.success)}
                </Badge>
              )}
            </div>
          </div>

          {/* 测试结果详情 */}
          {testResult && (
            <div className="p-4 border rounded-md bg-muted/50">
              <h4 className="font-medium mb-2">连接测试结果</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span>状态：</span>
                  <Badge variant={getStatusColor(testResult.success)}>
                    {getStatusText(testResult.success)}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>响应时间：</span>
                  <span>{testResult.response_time_ms}ms</span>
                </div>
                <div className="flex justify-between">
                  <span>消息：</span>
                  <span className={testResult.success ? 'text-green-600' : 'text-red-600'}>
                    {testResult.message}
                  </span>
                </div>

                {testResult.details && (
                  <div className="mt-3 space-y-1">
                    <div className="font-medium">连接详情：</div>
                    {testResult.details.database_type && (
                      <div>数据库类型：{testResult.details.database_type}</div>
                    )}
                    {testResult.details.server_version && (
                      <div>服务器版本：{testResult.details.server_version}</div>
                    )}
                    {testResult.details.database_name && (
                      <div>数据库名称：{testResult.details.database_name}</div>
                    )}
                    {testResult.details.connection_info?.host && (
                      <div>主机：{testResult.details.connection_info.host}</div>
                    )}
                    {testResult.details.connection_info?.port && (
                      <div>端口：{testResult.details.connection_info.port}</div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 错误信息 */}
          <ErrorMessage message={useDataSourceStore.getState().error} />

          {/* 表单按钮 */}
          <div className="flex gap-3 pt-4">
            <Button
              type="submit"
              disabled={isSubmitting || externalLoading || !testResult?.success}
              className="flex-1"
            >
              {(isSubmitting || externalLoading) ? (
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
      </CardContent>
    </Card>
  )
}