/**
 * 租户统计信息组件
 * 实现Story-2.2要求的租户统计信息展示
 */

import React, { useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { LoadingSpinner } from '../ui/loading-spinner'
import { ErrorMessage } from '../ui/error-message'
import {
  useTenantStats,
  useTenantLoading,
  useTenantError,
  useTenantActions,
  formatFileSize,
  getStorageUsageColor,
  getStorageUsageVariant
} from '../../store/tenantStore'

interface TenantStatsProps {
  onRefresh?: () => void
  refreshInterval?: number // 自动刷新间隔（毫秒）
}

export const TenantStats: React.FC<TenantStatsProps> = ({
  onRefresh,
  refreshInterval
}) => {
  const stats = useTenantStats()
  const loading = useTenantLoading()
  const error = useTenantError()
  const { fetchTenantStats } = useTenantActions()

  useEffect(() => {
    // 组件挂载时获取统计信息
    fetchTenantStats()

    // 设置自动刷新
    let interval: NodeJS.Timeout | null = null
    if (refreshInterval && refreshInterval > 0) {
      interval = setInterval(fetchTenantStats, refreshInterval)
    }

    return () => {
      if (interval) {
        clearInterval(interval)
      }
    }
  }, [fetchTenantStats, refreshInterval])

  const handleRefresh = () => {
    fetchTenantStats()
    onRefresh?.()
  }

  if (loading && !stats) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center p-6">
          <LoadingSpinner size="lg" />
        </CardContent>
      </Card>
    )
  }

  if (error && !stats) {
    return (
      <ErrorMessage
        message={error}
        onRetry={fetchTenantStats}
      />
    )
  }

  if (!stats) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-center text-gray-500">No statistics available</p>
        </CardContent>
      </Card>
    )
  }

  // 计算进度条百分比
  const usagePercent = Math.min(100, (stats.storage_used_mb / stats.storage_quota_mb) * 100)

  return (
    <div className="space-y-6">
      {/* 概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-blue-600">
              {stats.total_documents}
            </div>
            <div className="text-sm text-gray-500">总文档数</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-green-600">
              {stats.processed_documents}
            </div>
            <div className="text-sm text-gray-500">已处理文档</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-yellow-600">
              {stats.pending_documents}
            </div>
            <div className="text-sm text-gray-500">待处理文档</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-purple-600">
              {stats.total_data_sources}
            </div>
            <div className="text-sm text-gray-500">数据源连接</div>
          </CardContent>
        </Card>
      </div>

      {/* 详细统计 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 存储使用情况 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-semibold">存储使用情况</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium">已使用存储</span>
                <span className={`text-sm font-medium ${getStorageUsageColor(usagePercent)}`}>
                  {formatFileSize(stats.storage_used_mb)} / {formatFileSize(stats.storage_quota_mb)}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-300 ${
                    usagePercent >= 90 ? 'bg-red-600' :
                    usagePercent >= 75 ? 'bg-yellow-600' : 'bg-green-600'
                  }`}
                  style={{ width: `${usagePercent}%` }}
                />
              </div>
              <div className="text-xs text-gray-500 mt-1">
                使用率: {usagePercent.toFixed(1)}%
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">总配额:</span>
                <div className="font-medium">{formatFileSize(stats.storage_quota_mb)}</div>
              </div>
              <div>
                <span className="text-gray-500">已使用:</span>
                <div className="font-medium text-blue-600">{formatFileSize(stats.storage_used_mb)}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 文档处理状态 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg font-semibold">文档处理状态</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {stats.processed_documents}
                </div>
                <div className="text-sm text-gray-600">已完成</div>
                {stats.total_documents > 0 && (
                  <div className="text-xs text-gray-500 mt-1">
                    {((stats.processed_documents / stats.total_documents) * 100).toFixed(1)}%
                  </div>
                )}
              </div>
              <div className="text-center p-4 bg-yellow-50 rounded-lg">
                <div className="text-2xl font-bold text-yellow-600">
                  {stats.pending_documents}
                </div>
                <div className="text-sm text-gray-600">处理中</div>
                {stats.total_documents > 0 && (
                  <div className="text-xs text-gray-500 mt-1">
                    {((stats.pending_documents / stats.total_documents) * 100).toFixed(1)}%
                  </div>
                )}
              </div>
            </div>

            {stats.total_documents > 0 && (
              <div className="mt-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm font-medium">处理进度</span>
                  <span className="text-sm text-gray-500">
                    {stats.processed_documents} / {stats.total_documents}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 h-2 rounded-full transition-all duration-300"
                    style={{
                      width: `${(stats.processed_documents / stats.total_documents) * 100}%`
                    }}
                  />
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 操作按钮 */}
      <div className="flex justify-end">
        <Button
          variant="outline"
          onClick={handleRefresh}
          disabled={loading}
        >
          {loading ? (
            <>
              <LoadingSpinner size="sm" className="mr-2" />
              刷新中...
            </>
          ) : (
            '刷新统计'
          )}
        </Button>
      </div>

      {error && (
        <ErrorMessage
          message={error}
          onRetry={fetchTenantStats}
        />
      )}
    </div>
  )
}

export default TenantStats