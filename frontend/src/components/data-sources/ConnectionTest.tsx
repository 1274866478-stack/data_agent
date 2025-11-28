'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { useDataSourceStore, TestResult } from '@/store/dataSourceStore'

interface ConnectionTestProps {
  connectionString?: string
  dbType?: string
  onTestComplete?: (result: TestResult) => void
  showAdvanced?: boolean
  compact?: boolean
}

export function ConnectionTest({
  connectionString: initialConnectionString,
  dbType = 'postgresql',
  onTestComplete,
  showAdvanced = true,
  compact = false,
}: ConnectionTestProps) {
  const { testConnection } = useDataSourceStore()

  const [connectionString, setConnectionString] = useState(initialConnectionString || '')
  const [selectedDbType, setSelectedDbType] = useState(dbType)
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [isTesting, setIsTesting] = useState(false)
  const [showDetails, setShowDetails] = useState(false)

  // 执行连接测试
  const handleTestConnection = async () => {
    if (!connectionString.trim()) {
      return
    }

    setIsTesting(true)
    setTestResult(null)

    try {
      const result = await testConnection(connectionString, selectedDbType)
      setTestResult(result)
      onTestComplete?.(result)
    } catch (error) {
      // 错误已由store处理，testConnection会返回错误结果
    } finally {
      setIsTesting(false)
    }
  }

  // 获取连接字符串示例
  const getConnectionStringExample = (type: string): string => {
    switch (type) {
      case 'postgresql':
        return 'postgresql://username:password@localhost:5432/database_name'
      case 'mysql':
        return 'mysql://username:password@localhost:3306/database_name'
      case 'sqlite':
        return 'sqlite:///path/to/database.db'
      default:
        return ''
    }
  }

  // 获取状态颜色
  const getStatusColor = (success?: boolean) => {
    if (success === undefined) return 'secondary'
    return success ? 'default' : 'destructive'
  }

  // 获取状态文本
  const getStatusText = (success?: boolean) => {
    if (success === undefined) return '未测试'
    return success ? '连接成功' : '连接失败'
  }

  // 获取响应时间颜色
  const getResponseTimeColor = (responseTime: number) => {
    if (responseTime < 100) return 'text-green-600'
    if (responseTime < 500) return 'text-yellow-600'
    return 'text-red-600'
  }

  if (compact) {
    return (
      <div className="space-y-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={connectionString}
            onChange={(e) => setConnectionString(e.target.value)}
            placeholder={getConnectionStringExample(selectedDbType)}
            className="flex-1 px-3 py-2 border rounded-md text-sm font-mono bg-background"
          />
          <select
            value={selectedDbType}
            onChange={(e) => setSelectedDbType(e.target.value)}
            className="px-3 py-2 border rounded-md bg-background text-sm"
          >
            <option value="postgresql">PostgreSQL</option>
            <option value="mysql">MySQL</option>
            <option value="sqlite">SQLite</option>
          </select>
          <Button
            onClick={handleTestConnection}
            disabled={isTesting || !connectionString.trim()}
            size="sm"
          >
            {isTesting ? (
              <LoadingSpinner className="h-4 w-4" />
            ) : (
              '测试'
            )}
          </Button>
        </div>

        {testResult && (
          <div className="flex items-center gap-2 text-sm">
            <Badge variant={getStatusColor(testResult.success)}>
              {getStatusText(testResult.success)}
            </Badge>
            <span className={getResponseTimeColor(testResult.response_time_ms)}>
              {testResult.response_time_ms}ms
            </span>
          </div>
        )}
      </div>
    )
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          数据库连接测试
          {testResult && (
            <Badge variant={getStatusColor(testResult.success)}>
              {getStatusText(testResult.success)}
            </Badge>
          )}
        </CardTitle>
        <CardDescription>
          测试数据库连接字符串的有效性和性能
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 数据库类型选择 */}
        <div className="space-y-2">
          <label className="text-sm font-medium">数据库类型</label>
          <select
            value={selectedDbType}
            onChange={(e) => setSelectedDbType(e.target.value)}
            className="w-full p-2 border rounded-md bg-background"
          >
            <option value="postgresql">PostgreSQL</option>
            <option value="mysql">MySQL</option>
            <option value="sqlite">SQLite</option>
          </select>
        </div>

        {/* 连接字符串输入 */}
        <div className="space-y-2">
          <label className="text-sm font-medium">连接字符串</label>
          <input
            type="text"
            value={connectionString}
            onChange={(e) => setConnectionString(e.target.value)}
            placeholder={getConnectionStringExample(selectedDbType)}
            className="w-full p-2 border rounded-md font-mono text-sm bg-background"
          />
          <div className="text-xs text-muted-foreground">
            格式示例：{getConnectionStringExample(selectedDbType)}
          </div>
        </div>

        {/* 测试按钮 */}
        <Button
          onClick={handleTestConnection}
          disabled={isTesting || !connectionString.trim()}
          className="w-full"
        >
          {isTesting ? (
            <>
              <LoadingSpinner className="mr-2 h-4 w-4" />
              测试连接中...
            </>
          ) : (
            '开始测试'
          )}
        </Button>

        {/* 测试结果概览 */}
        {testResult && (
          <div className="border rounded-lg p-4 bg-muted/50">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-medium">测试结果</h4>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowDetails(!showDetails)}
              >
                {showDetails ? '隐藏详情' : '显示详情'}
              </Button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-muted-foreground">状态</div>
                <div className="font-medium">
                  <Badge variant={getStatusColor(testResult.success)}>
                    {getStatusText(testResult.success)}
                  </Badge>
                </div>
              </div>
              <div>
                <div className="text-muted-foreground">响应时间</div>
                <div className={`font-medium ${getResponseTimeColor(testResult.response_time_ms)}`}>
                  {testResult.response_time_ms}ms
                </div>
              </div>
              <div>
                <div className="text-muted-foreground">错误代码</div>
                <div className="font-medium">
                  {testResult.error_code || 'N/A'}
                </div>
              </div>
              <div>
                <div className="text-muted-foreground">测试时间</div>
                <div className="font-medium">
                  {new Date(testResult.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>

            <div className="mt-3">
              <div className="text-muted-foreground text-sm">消息</div>
              <div className={`text-sm ${testResult.success ? 'text-green-600' : 'text-red-600'}`}>
                {testResult.message}
              </div>
            </div>

            {/* 详细信息 */}
            {showDetails && showAdvanced && testResult.details && (
              <div className="mt-4 pt-4 border-t space-y-3">
                <h5 className="font-medium">连接详情</h5>

                {testResult.details.database_type && (
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-muted-foreground">数据库类型：</div>
                    <div>{testResult.details.database_type}</div>
                  </div>
                )}

                {testResult.details.server_version && (
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-muted-foreground">服务器版本：</div>
                    <div className="font-mono text-xs">{testResult.details.server_version}</div>
                  </div>
                )}

                {testResult.details.database_name && (
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-muted-foreground">数据库名称：</div>
                    <div>{testResult.details.database_name}</div>
                  </div>
                )}

                {testResult.details.current_user && (
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="text-muted-foreground">当前用户：</div>
                    <div>{testResult.details.current_user}</div>
                  </div>
                )}

                {testResult.details.connection_info && (
                  <div className="space-y-2">
                    <div className="text-sm font-medium">连接信息：</div>
                    <div className="bg-background p-2 rounded text-xs font-mono space-y-1">
                      {testResult.details.connection_info.host && (
                        <div>主机：{testResult.details.connection_info.host}</div>
                      )}
                      {testResult.details.connection_info.port && (
                        <div>端口：{testResult.details.connection_info.port}</div>
                      )}
                      {testResult.details.connection_info.database && (
                        <div>数据库：{testResult.details.connection_info.database}</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* 性能基准说明 */}
        {showAdvanced && (
          <div className="text-xs text-muted-foreground bg-muted/30 p-3 rounded">
            <div className="font-medium mb-1">性能基准：</div>
            <div className="space-y-1">
              <div>• 🟢 优秀：&lt; 100ms</div>
              <div>• 🟡 良好：100-500ms</div>
              <div>• 🔴 需要优化：&gt; 500ms</div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}