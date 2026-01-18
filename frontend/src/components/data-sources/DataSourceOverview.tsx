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

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { StatCard } from '@/components/ui/stat-card'
import { DashboardOverview, useDashboardStore } from '@/store/dashboardStore'
import {
    AlertCircle,
    CheckCircle,
    Clock,
    Database,
    FileText,
    HardDrive
} from 'lucide-react'


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
        activity.status === 'success' ? 'bg-green-500/20 text-green-600' : 'bg-destructive/20 text-destructive'
      }`}>
        {getActivityIcon()}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">
          {getActivityText()}{getTypeText()} &quot;{activity.item_name}&quot;
        </p>
        <p className="text-xs text-muted-foreground">
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
                <div className="h-4 bg-muted rounded w-3/4"></div>
              </CardHeader>
              <CardContent>
                <div className="h-8 bg-muted rounded w-1/2"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card className="border-destructive/30 bg-destructive/10">
        <CardContent className="pt-6">
          <div className="flex items-center space-x-2 text-destructive">
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
          icon={Database}
          gradient="accent"
          trend={overview.databases.active > 0 ? 'up' : 'neutral'}
          trendValue={`${databaseHealthPercentage}% 健康`}
        />
        <StatCard
          title="已上传文档"
          value={`${overview.documents.ready} / ${overview.documents.total}`}
          icon={FileText}
          gradient="success"
          trend={overview.documents.ready > 0 ? 'up' : 'neutral'}
          trendValue={`${documentProcessingPercentage}% 就绪`}
        />
        <StatCard
          title="存储使用"
          value={`${Math.round(overview.storage.usage_percentage)}%`}
          icon={HardDrive}
          gradient="warning"
          trend={overview.storage.usage_percentage > 80 ? 'down' : 'neutral'}
          trendValue={`${Math.round(overview.storage.used_mb)} MB`}
        />
        <StatCard
          title="健康连接"
          value={overview.databases.active}
          icon={CheckCircle}
          gradient="primary"
          variant="filled"
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
                <div className="text-xs text-muted-foreground">正常</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-destructive">{overview.databases.error}</div>
                <div className="text-xs text-muted-foreground">错误</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-primary">{overview.databases.total}</div>
                <div className="text-xs text-muted-foreground">总计</div>
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
                <div className="text-xs text-muted-foreground">就绪</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-yellow-600">{overview.documents.processing}</div>
                <div className="text-xs text-muted-foreground">处理中</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-destructive">{overview.documents.error}</div>
                <div className="text-xs text-muted-foreground">错误</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-primary">{overview.documents.total}</div>
                <div className="text-xs text-muted-foreground">总计</div>
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
                  overview.storage.usage_percentage > 80 ? 'text-destructive' :
                  overview.storage.usage_percentage > 60 ? 'text-yellow-600' : 'text-green-600'
                }`}
              />
            </div>
            <div className="text-sm text-muted-foreground">
              {overview.storage.usage_percentage > 80 && (
                <div className="text-destructive flex items-center gap-1">
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
              <div className="text-center py-4 text-muted-foreground">
                暂无最近活动
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}