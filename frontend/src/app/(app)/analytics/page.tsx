/**
 * [HEADER]
 * 数据分析页面 - Data Agent V4 Analytics Dashboard
 * 提供数据资产概览、统计图表和使用情况分析
 *
 * [MODULE]
 * 模块类型: Next.js 14 App Router Page Component
 * 所属功能: 数据可视化与分析
 * 技术栈: React, TypeScript, Recharts, Zustand
 *
 * [INPUT]
 * - 无路由参数
 * - 依赖的全局状态:
 *   - tenantId (useTenantId): 当前租户ID
 *   - overview (useDashboardStore): 概览数据
 *   - dataSources (useDataSourceStore): 数据源列表
 *   - documents (useDocumentStore): 文档列表
 *
 * [OUTPUT]
 * - 渲染内容:
 *   - 关键指标卡片 (数据源、文档、存储、资产总数)
 *   - 数据源类型分布饼图
 *   - 文档状态分布饼图
 *   - 存储使用情况进度条
 *   - 最近活动列表
 * - 用户交互:
 *   - 刷新数据按钮 (handleRefresh)
 *   - 实时数据加载状态
 *
 * [LINK]
 * - 依赖组件:
 *   - @/components/ui/button - Button组件
 *   - @/components/ui/card - Card组件族
 *   - @/components/ui/loading-spinner - LoadingSpinner
 *   - @/components/ui/error-message - ErrorMessage
 * - 依赖状态管理:
 *   - @/store/authStore - useTenantId
 *   - @/store/dashboardStore - fetchOverview
 *   - @/store/dataSourceStore - fetchDataSources
 *   - @/store/documentStore - fetchDocuments
 * - 图表库:
 *   - recharts - PieChart, ResponsiveContainer
 * - 路由:
 *   - /analytics - 当前页面路由
 *
 * [POS]
 * - 文件路径: frontend/src/app/(app)/analytics/page.tsx
 * - 访问URL: http://localhost:3000/analytics
 * - 布局位置: (app) 路由组, 继承主应用布局
 *
 * [STATE]
 * - 局部状态:
 *   - isRefreshing: boolean - 刷新状态标记
 * - 衍生状态 (useMemo):
 *   - dataSourceStats - 数据源统计对象
 *   - docStats - 文档统计对象
 *   - dataSourceTypeData - 饼图数据格式
 *   - documentStatusData - 饼图数据格式
 *   - storageData - 存储使用情况
 * - 副作用:
 *   - useEffect: 加载初始数据 (tenantId变化时)
 *   - handleRefresh: 手动刷新所有数据
 *
 * [PROTOCOL]
 * - 初始化流程:
 *   1. 从 authStore 获取 tenantId
 *   2. 并行调用 fetchOverview, fetchDataSources, fetchDocuments
 *   3. 计算统计指标和图表数据
 * - 数据刷新机制:
 *   - 自动刷新: tenantId 变化时触发
 *   - 手动刷新: 点击刷新按钮, 防抖处理
 * - 错误处理:
 *   - 租户未认证: 显示认证错误提示
 *   - 数据加载失败: 显示 ErrorMessage 组件
 * - 性能优化:
 *   - useMemo 缓存统计计算结果
 *   - Promise.all 并行数据请求
 * - 空状态处理:
 *   - 无数据源: 显示空状态提示图标
 *   - 无文档: 显示空状态提示图标
 */

'use client'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ErrorMessage } from '@/components/ui/error-message'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { useTenantId } from '@/store/authStore'
import { useDashboardStore } from '@/store/dashboardStore'
import { useDataSourceStore } from '@/store/dataSourceStore'
import { useDocumentStore } from '@/store/documentStore'
import {
    AlertCircle,
    CheckCircle,
    Clock,
    Database,
    FileText,
    FolderOpen,
    HardDrive,
    RefreshCw
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import {
    Cell,
    Legend,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip
} from 'recharts'

// 颜色配置
const COLORS = {
  database: {
    active: '#10b981',  // 绿色 - 活跃
    inactive: '#6b7280', // 灰色 - 非活跃
    error: '#ef4444',    // 红色 - 错误
  },
  document: {
    ready: '#10b981',     // 绿色 - 就绪
    processing: '#f59e0b', // 黄色 - 处理中
    pending: '#3b82f6',   // 蓝色 - 待处理
    error: '#ef4444',     // 红色 - 错误
  },
  storage: {
    used: '#3b82f6',   // 蓝色
    free: '#e5e7eb',   // 灰色
  }
}

export default function AnalyticsPage() {
  const tenantId = useTenantId()
  const { overview, isLoading: dashboardLoading, error: dashboardError, fetchOverview } = useDashboardStore()
  const { dataSources, fetchDataSources, isLoading: dataSourceLoading } = useDataSourceStore()
  const { documents, stats: documentStats, fetchDocuments, isLoading: documentLoading } = useDocumentStore()

  const [isRefreshing, setIsRefreshing] = useState(false)

  // 加载数据
  useEffect(() => {
    if (tenantId) {
      fetchOverview()
      fetchDataSources(tenantId)
      fetchDocuments()
    }
  }, [tenantId, fetchOverview, fetchDataSources, fetchDocuments])

  // 计算数据源统计
  const dataSourceStats = useMemo(() => {
    const total = dataSources.length
    const active = dataSources.filter(ds => ds.status === 'active').length
    const inactive = dataSources.filter(ds => ds.status === 'inactive').length
    const error = dataSources.filter(ds => ds.status === 'error').length

    // 按类型分组
    const byType: Record<string, number> = {}
    dataSources.forEach(ds => {
      const type = ds.db_type || 'unknown'
      byType[type] = (byType[type] || 0) + 1
    })

    return { total, active, inactive, error, byType }
  }, [dataSources])

  // 计算文档统计
  const docStats = useMemo(() => {
    const total = documents.length
    const ready = documents.filter(d => d.status === 'READY').length
    const processing = documents.filter(d => d.status === 'INDEXING').length
    const pending = documents.filter(d => d.status === 'PENDING').length
    const error = documents.filter(d => d.status === 'ERROR').length

    // 按文件类型分组
    const byType: Record<string, number> = {}
    documents.forEach(doc => {
      const type = doc.file_type || 'unknown'
      byType[type] = (byType[type] || 0) + 1
    })

    // 计算总大小
    const totalSize = documents.reduce((sum, doc) => sum + (doc.file_size || 0), 0)

    return { total, ready, processing, pending, error, byType, totalSize }
  }, [documents])

  // 数据源类型分布图数据
  const dataSourceTypeData = useMemo(() => {
    const typeColors: Record<string, string> = {
      postgresql: '#336791',
      mysql: '#4479A1',
      sqlite: '#003B57',
      mongodb: '#47A248',
      unknown: '#6b7280',
    }

    return Object.entries(dataSourceStats.byType).map(([name, value]) => ({
      name: name.toUpperCase(),
      value,
      color: typeColors[name.toLowerCase()] || '#6b7280'
    }))
  }, [dataSourceStats.byType])

  // 文档状态分布图数据
  const documentStatusData = useMemo(() => {
    const data = []
    if (docStats.ready > 0) data.push({ name: '已就绪', value: docStats.ready, color: COLORS.document.ready })
    if (docStats.processing > 0) data.push({ name: '处理中', value: docStats.processing, color: COLORS.document.processing })
    if (docStats.pending > 0) data.push({ name: '待处理', value: docStats.pending, color: COLORS.document.pending })
    if (docStats.error > 0) data.push({ name: '错误', value: docStats.error, color: COLORS.document.error })
    return data
  }, [docStats])

  // 存储使用情况
  const storageData = useMemo(() => {
    const usedMB = overview?.storage?.used_mb || (docStats.totalSize / (1024 * 1024))
    const quotaMB = overview?.storage?.quota_mb || 1024
    const usedPercent = Math.min(100, (usedMB / quotaMB) * 100)
    return { usedMB, quotaMB, usedPercent }
  }, [overview, docStats.totalSize])

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const isLoading = dashboardLoading || dataSourceLoading || documentLoading
  const error = dashboardError

  // 如果租户ID不存在，说明用户未正确认证
  if (!tenantId) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">认证错误</h1>
          <p className="text-gray-600">无法获取租户信息，请重新登录。</p>
        </div>
      </div>
    )
  }

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await Promise.all([
        fetchOverview(),
        fetchDataSources(tenantId),
        fetchDocuments()
      ])
    } finally {
      setIsRefreshing(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      {/* 页面标题和操作 */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">数据分析</h1>
          <p className="text-gray-300">
            查看您的数据资产概览和使用情况
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading || isRefreshing}
          >
            {(isLoading || isRefreshing) ? (
              <LoadingSpinner className="h-4 w-4 mr-2" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            刷新
          </Button>
        </div>
      </div>

      {/* 错误信息 */}
      {error && <ErrorMessage message={error} />}

      {/* 加载状态 */}
      {isLoading && !isRefreshing && (
        <div className="flex justify-center items-center py-12">
          <LoadingSpinner className="h-8 w-8" />
          <span className="ml-2 text-muted-foreground">加载数据中...</span>
        </div>
      )}

      {/* 关键指标卡片 */}
      {!isLoading && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 数据源数量 */}
            <Card className="hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 border-blue-200/60 dark:border-blue-500/30">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">数据源总数</CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{dataSourceStats.total}</div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                  <span className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-green-500" />
                    {dataSourceStats.active} 活跃
                  </span>
                  {dataSourceStats.error > 0 && (
                    <span className="flex items-center gap-1">
                      <AlertCircle className="h-3 w-3 text-red-500" />
                      {dataSourceStats.error} 错误
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* 文档数量 */}
            <Card className="hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 border-green-200/60 dark:border-green-500/30">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">文档总数</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{docStats.total}</div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                  <span className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-green-500" />
                    {docStats.ready} 就绪
                  </span>
                  {docStats.processing > 0 && (
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3 text-yellow-500" />
                      {docStats.processing} 处理中
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* 存储使用情况 */}
            <Card className="hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 border-purple-200/60 dark:border-purple-500/30">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">存储使用</CardTitle>
                <HardDrive className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatFileSize(docStats.totalSize)}</div>
                <div className="mt-2">
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all"
                      style={{ width: `${storageData.usedPercent}%` }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    已使用 {storageData.usedPercent.toFixed(1)}% (配额 {storageData.quotaMB} MB)
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* 数据资产概览 */}
            <Card className="hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 border-orange-200/60 dark:border-orange-500/30">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">数据资产</CardTitle>
                <FolderOpen className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {dataSourceStats.total + docStats.total}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {dataSourceStats.total} 个数据库连接 + {docStats.total} 个文档
                </p>
              </CardContent>
            </Card>
          </div>

          {/* 图表区域 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 数据源类型分布 */}
            <Card className="hover:shadow-lg transition-all duration-200">
              <CardHeader>
                <CardTitle>数据源类型分布</CardTitle>
                <CardDescription>各类型数据库连接的数量分布</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  {dataSourceTypeData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={dataSourceTypeData}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={100}
                          paddingAngle={2}
                          dataKey="value"
                          label={({ name, value }) => `${name}: ${value}`}
                          labelLine={false}
                        >
                          {dataSourceTypeData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--background))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '6px'
                          }}
                          formatter={(value: number) => [`${value} 个`, '数量']}
                        />
                        <Legend
                          verticalAlign="bottom"
                          height={36}
                          formatter={(value) => <span className="text-sm">{value}</span>}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                      <div className="text-center">
                        <Database className="h-12 w-12 mx-auto mb-2 opacity-50" />
                        <p>暂无数据源</p>
                        <p className="text-sm">添加数据源后可查看统计</p>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* 文档状态分布 */}
            <Card className="hover:shadow-lg transition-all duration-200">
              <CardHeader>
                <CardTitle>文档状态分布</CardTitle>
                <CardDescription>知识库文档的处理状态</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  {documentStatusData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={documentStatusData}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={100}
                          paddingAngle={2}
                          dataKey="value"
                          label={({ name, value }) => `${name}: ${value}`}
                          labelLine={false}
                        >
                          {documentStatusData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--background))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '6px'
                          }}
                          formatter={(value: number) => [`${value} 个`, '数量']}
                        />
                        <Legend
                          verticalAlign="bottom"
                          height={36}
                          formatter={(value) => <span className="text-sm">{value}</span>}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                      <div className="text-center">
                        <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
                        <p>暂无文档</p>
                        <p className="text-sm">上传文档后可查看统计</p>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 最近活动 */}
          {overview?.recent_activity && overview.recent_activity.length > 0 && (
            <Card className="hover:shadow-lg transition-all duration-200">
              <CardHeader>
                <CardTitle>最近活动</CardTitle>
                <CardDescription>数据资产的最新操作记录</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {overview.recent_activity.slice(0, 5).map((activity) => (
                    <div key={activity.id} className="flex items-center justify-between py-2 border-b last:border-0">
                      <div className="flex items-center gap-3">
                        {activity.type === 'database' ? (
                          <Database className="h-4 w-4 text-blue-500" />
                        ) : (
                          <FileText className="h-4 w-4 text-green-500" />
                        )}
                        <div>
                          <p className="text-sm font-medium">{activity.item_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {activity.action === 'created' && '创建'}
                            {activity.action === 'updated' && '更新'}
                            {activity.action === 'deleted' && '删除'}
                            {activity.action === 'tested' && '测试'}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {activity.status === 'success' ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-red-500" />
                        )}
                        <span className="text-xs text-muted-foreground">
                          {new Date(activity.timestamp).toLocaleString('zh-CN')}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}

