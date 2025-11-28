'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { ErrorMessage } from '@/components/ui/error-message'
import { DataSourceForm } from './DataSourceForm'
import { ConnectionTest } from './ConnectionTest'
import { useDataSourceStore, DataSourceConnection } from '@/store/dataSourceStore'

interface DataSourceListProps {
  tenantId: string
  onDataSourceSelect?: (dataSource: DataSourceConnection) => void
}

export function DataSourceList({ tenantId, onDataSourceSelect }: DataSourceListProps) {
  const {
    dataSources,
    isLoading,
    error,
    fetchDataSources,
    deleteDataSource,
    testDataSourceConnection,
    clearError,
  } = useDataSourceStore()

  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingDataSource, setEditingDataSource] = useState<DataSourceConnection | null>(null)
  const [testingDataSource, setTestingDataSource] = useState<string | null>(null)

  useEffect(() => {
    fetchDataSources(tenantId, {
      active_only: filterStatus !== 'all',
    })
  }, [tenantId, filterStatus, fetchDataSources])

  // 过滤数据源
  const filteredDataSources = dataSources.filter((source) => {
    const matchesSearch = source.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         source.db_type.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesStatus = filterStatus === 'all' ||
                         (filterStatus === 'active' && source.status === 'active') ||
                         (filterStatus === 'inactive' && source.status === 'inactive') ||
                         (filterStatus === 'error' && source.status === 'error')

    return matchesSearch && matchesStatus
  })

  // 获取状态颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'default'
      case 'inactive':
        return 'secondary'
      case 'error':
        return 'destructive'
      case 'testing':
        return 'outline'
      default:
        return 'secondary'
    }
  }

  // 获取状态文本
  const getStatusText = (status: string) => {
    switch (status) {
      case 'active':
        return '已连接'
      case 'inactive':
        return '未激活'
      case 'error':
        return '连接错误'
      case 'testing':
        return '测试中'
      default:
        return '未知'
    }
  }

  // 获取数据库类型显示名称
  const getDatabaseTypeDisplay = (dbType: string) => {
    switch (dbType) {
      case 'postgresql':
        return 'PostgreSQL'
      case 'mysql':
        return 'MySQL'
      case 'sqlite':
        return 'SQLite'
      default:
        return dbType.toUpperCase()
    }
  }

  // 处理删除
  const handleDelete = async (dataSource: DataSourceConnection) => {
    if (window.confirm(`确定要删除数据源 "${dataSource.name}" 吗？此操作不可恢复。`)) {
      try {
        await deleteDataSource(dataSource.id, tenantId)
      } catch (error) {
        // 错误已由store处理
      }
    }
  }

  // 处理测试连接
  const handleTestConnection = async (dataSource: DataSourceConnection) => {
    setTestingDataSource(dataSource.id)
    try {
      await testDataSourceConnection(dataSource.id, tenantId)
    } catch (error) {
      // 错误已由store处理
    } finally {
      setTestingDataSource(null)
    }
  }

  // 处理编辑
  const handleEdit = (dataSource: DataSourceConnection) => {
    setEditingDataSource(dataSource)
    setShowCreateForm(false)
  }

  // 处理创建成功
  const handleCreateSuccess = () => {
    setShowCreateForm(false)
    clearError()
    fetchDataSources(tenantId)
  }

  // 处理编辑成功
  const handleEditSuccess = () => {
    setEditingDataSource(null)
    clearError()
    fetchDataSources(tenantId)
  }

  // 处理取消
  const handleCancel = () => {
    setShowCreateForm(false)
    setEditingDataSource(null)
    clearError()
  }

  if (showCreateForm || editingDataSource) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">
            {editingDataSource ? '编辑数据源' : '添加数据源'}
          </h2>
          <Button variant="outline" onClick={handleCancel}>
            返回列表
          </Button>
        </div>

        <DataSourceForm
          tenantId={tenantId}
          initialData={editingDataSource ? {
            name: editingDataSource.name,
            db_type: editingDataSource.db_type,
          } : undefined}
          onSubmit={handleCreateSuccess}
          onCancel={handleCancel}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页面标题和操作 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">数据源管理</h1>
          <p className="text-muted-foreground">
            管理和监控您的数据库连接
          </p>
        </div>
        <Button onClick={() => setShowCreateForm(true)}>
          添加数据源
        </Button>
      </div>

      {/* 搜索和筛选 */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <Label htmlFor="search" className="sr-only">搜索</Label>
          <Input
            id="search"
            placeholder="搜索数据源名称或类型..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-3 py-2 border rounded-md bg-background"
        >
          <option value="all">所有状态</option>
          <option value="active">已连接</option>
          <option value="inactive">未激活</option>
          <option value="error">连接错误</option>
        </select>
      </div>

      {/* 错误信息 */}
      {error && <ErrorMessage message={error} />}

      {/* 加载状态 */}
      {isLoading && (
        <div className="flex justify-center py-8">
          <LoadingSpinner className="h-8 w-8" />
        </div>
      )}

      {/* 数据源列表 */}
      {!isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDataSources.map((dataSource) => (
            <Card key={dataSource.id} className="relative">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg truncate" title={dataSource.name}>
                    {dataSource.name}
                  </CardTitle>
                  <div className={`w-3 h-3 rounded-full ${
                    dataSource.status === 'active' ? 'bg-green-500' :
                    dataSource.status === 'error' ? 'bg-red-500' :
                    dataSource.status === 'testing' ? 'bg-yellow-500' :
                    'bg-gray-400'
                  }`} />
                </div>
                <CardDescription className="flex items-center gap-2">
                  <Badge variant="outline">
                    {getDatabaseTypeDisplay(dataSource.db_type)}
                  </Badge>
                  <Badge variant={getStatusColor(dataSource.status)}>
                    {getStatusText(dataSource.status)}
                  </Badge>
                </CardDescription>
              </CardHeader>
              <CardContent>
                {/* 连接信息 */}
                <div className="space-y-2 text-sm text-muted-foreground mb-4">
                  {dataSource.host && (
                    <div>主机：{dataSource.host}</div>
                  )}
                  {dataSource.port && (
                    <div>端口：{dataSource.port}</div>
                  )}
                  {dataSource.database_name && (
                    <div>数据库：{dataSource.database_name}</div>
                  )}
                  {dataSource.last_tested_at && (
                    <div>最后测试：{new Date(dataSource.last_tested_at).toLocaleString()}</div>
                  )}
                </div>

                {/* 测试结果预览 */}
                {dataSource.test_result && (
                  <div className="mb-4 p-2 bg-muted rounded text-xs">
                    <div className="flex items-center gap-2">
                      <span>最后测试：</span>
                      <Badge variant={dataSource.test_result.success ? 'default' : 'destructive'}>
                        {dataSource.test_result.success ? '成功' : '失败'}
                      </Badge>
                      <span>({dataSource.test_result.response_time_ms}ms)</span>
                    </div>
                    {!dataSource.test_result.success && (
                      <div className="text-red-600 mt-1 truncate">
                        {dataSource.test_result.message}
                      </div>
                    )}
                  </div>
                )}

                {/* 操作按钮 */}
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => handleTestConnection(dataSource)}
                    disabled={testingDataSource === dataSource.id}
                  >
                    {testingDataSource === dataSource.id ? (
                      <>
                        <LoadingSpinner className="mr-1 h-3 w-3" />
                        测试中
                      </>
                    ) : (
                      '测试连接'
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleEdit(dataSource)}
                  >
                    编辑
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onDataSourceSelect?.(dataSource)}
                  >
                    选择
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(dataSource)}
                    className="text-red-600 hover:text-red-700"
                  >
                    删除
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 空状态 */}
      {!isLoading && filteredDataSources.length === 0 && (
        <div className="text-center py-12">
          <div className="text-muted-foreground mb-4">
            {searchQuery || filterStatus !== 'all'
              ? '没有找到匹配的数据源'
              : '还没有任何数据源'
            }
          </div>
          {!searchQuery && filterStatus === 'all' && (
            <Button onClick={() => setShowCreateForm(true)}>
              添加第一个数据源
            </Button>
          )}
        </div>
      )}
    </div>
  )
}