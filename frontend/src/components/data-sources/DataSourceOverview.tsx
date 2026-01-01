/**
 * # DataSourceOverview 数据源概览组件
 *
 * ## [MODULE]
 * **文件名**: DataSourceOverview.tsx
 * **职责**: 展示数据源和文档的统计概览，包括连接状态、存储使用、健康指标和最近活动
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - 无直接 Props（通过 store 获取数据）
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 数据源概览仪表板，包含统计卡片、健康状态、存储使用和活动记录
 *
 * ## [LINK]
 * **上游依赖**:
 * - [@/store/dashboardStore](../../store/dashboardStore.ts) - 提供概览数据和状态管理
 * - [@/components/ui/card](../ui/card.tsx) - 卡片容器组件
 * - [@/components/ui/badge](../ui/badge.tsx) - 状态徽章组件
 * - [@/components/ui/progress](../ui/progress.tsx) - 进度条组件
 * - [lucide-react](https://lucide.dev) - 图标库
 *
 * **下游依赖**:
 * - [../../app/(app)/page.tsx](../../app/(app)/page.tsx) - 在仪表板页面中使用
 * - [DataSourceTabs.tsx](./DataSourceTabs.tsx) - 作为标签页的内容展示
 *
 * ## [STATE]
 * - **overview: DashboardOverview | null** - 从 store 获取的概览数据，包含数据库、文档、存储和活动统计
 * - **isLoading: boolean** - 加载状态
 * - **error: string | null** - 错误信息
 *
 * ## [SIDE-EFFECTS]
 * - **数据获取**: 组件挂载时自动调用 fetchOverview() 获取概览数据
 * - **自动刷新**: 没有数据时自动触发数据获取
 * - **响应式布局**: 根据屏幕尺寸调整网格列数
 */
'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Database,
  FileText,
  HardDrive,
  CheckCircle,
  TrendingUp,
  Clock,
  AlertCircle
} from 'lucide-react'
import { useDashboardStore, DashboardOverview } from '@/store/dashboardStore'

interface StatCardProps {
  title: string
  value: string | number
  icon: React.ReactNode
  color: string
  trend?: {
    value: number
    isPositive: boolean
  }
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, color, trend }) => {
  const colorClasses = {
    blue: 'text-blue-600 bg-blue-50 border-blue-200',
    green: 'text-green-600 bg-green-50 border-green-200',
    orange: 'text-orange-600 bg-orange-50 border-orange-200',
    purple: 'text-purple-600 bg-purple-50 border-purple-200',
  }

  return (
    <Card className={`border-l-4 ${colorClasses[color as keyof typeof colorClasses]}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {trend && (
          <div className="flex items-center text-xs text-muted-foreground">
            <TrendingUp className={`mr-1 h-3 w-3 ${trend.isPositive ? 'text-green-600' : 'text-red-600'}`} />
            {trend.isPositive ? '+' : ''}{trend.value}% 较上周
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface ActivityItemProps {
  activity: DashboardOverview['recent_activity'][0]
}

const ActivityItem: React.FC<ActivityItemProps> = ({ activity }) => {
  const getActivityIcon = () => {
    switch (activity.type) {
      case 'database':
        return <Database className="h-4 w-4" />
      case 'document':
        return <FileText className="h-4 w-4" />
      default:
        return <AlertCircle className="h-4 w-4" />
    }
  }

  const getActivityText = () => {
    switch (activity.action) {
      case 'created':
        return '创建了'
      case 'updated':
        return '更新了'
      case 'deleted':
        return '删除了'
      case 'tested':
        return '测试了'
      default:
        return '操作了'
    }
  }

  const getTypeText = () => {
    return activity.type === 'database' ? '数据库连接' : '文档'
  }

  return (
    <div className="flex items-center space-x-3 py-2">
      <div className={`flex-shrink-0 p-2 rounded-full ${
        activity.status === 'success' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
      }`}>
        {getActivityIcon()}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">
          {getActivityText()}{getTypeText()} &quot;{activity.item_name}&quot;
        </p>
        <p className="text-xs text-gray-500">
          {new Date(activity.timestamp).toLocaleString()}
        </p>
      </div>
      <Badge variant={activity.status === 'success' ? 'default' : 'destructive'}>
        {activity.status === 'success' ? '成功' : '失败'}
      </Badge>
    </div>
  )
}

export const DataSourceOverview: React.FC = () => {
  const { overview, isLoading, error, fetchOverview } = useDashboardStore()

  // 如果没有数据，尝试获取
  if (!overview && !isLoading && !error) {
    fetchOverview()
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-2">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              </CardHeader>
              <CardContent>
                <div className="h-8 bg-gray-200 rounded w-1/2"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardContent className="pt-6">
          <div className="flex items-center space-x-2 text-red-600">
            <AlertCircle className="h-5 w-5" />
            <span>加载概览数据失败: {error}</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!overview) {
    return null
  }

  const databaseHealthPercentage = overview.databases.total > 0
    ? Math.round((overview.databases.active / overview.databases.total) * 100)
    : 0

  const documentProcessingPercentage = overview.documents.total > 0
    ? Math.round((overview.documents.ready / overview.documents.total) * 100)
    : 0

  return (
    <div className="space-y-6">
      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="数据库连接"
          value={`${overview.databases.active} / ${overview.databases.total}`}
          icon={<Database className="h-4 w-4 text-blue-600" />}
          color="blue"
        />
        <StatCard
          title="已上传文档"
          value={`${overview.documents.ready} / ${overview.documents.total}`}
          icon={<FileText className="h-4 w-4 text-green-600" />}
          color="green"
        />
        <StatCard
          title="存储使用"
          value={`${Math.round(overview.storage.usage_percentage)}%`}
          icon={<HardDrive className="h-4 w-4 text-orange-600" />}
          color="orange"
        />
        <StatCard
          title="健康连接"
          value={overview.databases.active}
          icon={<CheckCircle className="h-4 w-4 text-green-600" />}
          color="green"
        />
      </div>

      {/* 详细统计 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 数据库状态 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              数据库连接状态
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>健康率</span>
                <span>{databaseHealthPercentage}%</span>
              </div>
              <Progress value={databaseHealthPercentage} className="h-2" />
            </div>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-lg font-semibold text-green-600">{overview.databases.active}</div>
                <div className="text-xs text-gray-500">正常</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-red-600">{overview.databases.error}</div>
                <div className="text-xs text-gray-500">错误</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-blue-600">{overview.databases.total}</div>
                <div className="text-xs text-gray-500">总计</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 文档处理状态 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              文档处理状态
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>就绪率</span>
                <span>{documentProcessingPercentage}%</span>
              </div>
              <Progress value={documentProcessingPercentage} className="h-2" />
            </div>
            <div className="grid grid-cols-4 gap-2 text-center">
              <div>
                <div className="text-lg font-semibold text-green-600">{overview.documents.ready}</div>
                <div className="text-xs text-gray-500">就绪</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-yellow-600">{overview.documents.processing}</div>
                <div className="text-xs text-gray-500">处理中</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-red-600">{overview.documents.error}</div>
                <div className="text-xs text-gray-500">错误</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-blue-600">{overview.documents.total}</div>
                <div className="text-xs text-gray-500">总计</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 存储使用情况 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="h-5 w-5" />
              存储使用情况
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>已使用 {Math.round(overview.storage.used_mb)} MB / {Math.round(overview.storage.quota_mb)} MB</span>
                <span>{Math.round(overview.storage.usage_percentage)}%</span>
              </div>
              <Progress
                value={overview.storage.usage_percentage}
                className={`h-3 ${
                  overview.storage.usage_percentage > 80 ? 'text-red-600' :
                  overview.storage.usage_percentage > 60 ? 'text-yellow-600' : 'text-green-600'
                }`}
              />
            </div>
            <div className="text-sm text-gray-600">
              {overview.storage.usage_percentage > 80 && (
                <div className="text-red-600 flex items-center gap-1">
                  <AlertCircle className="h-4 w-4" />
                  存储空间即将用完，建议清理或升级
                </div>
              )}
              {overview.storage.usage_percentage > 60 && overview.storage.usage_percentage <= 80 && (
                <div className="text-yellow-600 flex items-center gap-1">
                  <AlertCircle className="h-4 w-4" />
                  存储使用率较高，请注意
                </div>
              )}
              {overview.storage.usage_percentage <= 60 && (
                <div className="text-green-600 flex items-center gap-1">
                  <CheckCircle className="h-4 w-4" />
                  存储空间充足
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* 最近活动 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              最近活动
            </CardTitle>
          </CardHeader>
          <CardContent>
            {overview.recent_activity.length > 0 ? (
              <div className="space-y-0">
                {overview.recent_activity.slice(0, 5).map((activity) => (
                  <ActivityItem key={activity.id} activity={activity} />
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-gray-500">
                暂无最近活动
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}