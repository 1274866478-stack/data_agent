/**
 * 租户信息显示组件
 * 实现Story-2.2要求的租户信息展示
 */

import React, { useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { LoadingSpinner } from '../ui/loading-spinner'
import { ErrorMessage } from '../ui/error-message'
import {
  useCurrentTenant,
  useTenantLoading,
  useTenantError,
  useTenantActions,
  getStatusColor,
  getStatusBadgeVariant
} from '../../store/tenantStore'

interface TenantProfileProps {
  onEdit?: () => void
  showActions?: boolean
}

export const TenantProfile: React.FC<TenantProfileProps> = ({
  onEdit,
  showActions = true
}) => {
  const tenant = useCurrentTenant()
  const loading = useTenantLoading()
  const error = useTenantError()
  const { fetchTenantProfile } = useTenantActions()

  useEffect(() => {
    // 组件挂载时获取租户信息
    fetchTenantProfile()
  }, [fetchTenantProfile])

  if (loading && !tenant) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center p-6">
          <LoadingSpinner size="lg" />
        </CardContent>
      </Card>
    )
  }

  if (error && !tenant) {
    return (
      <ErrorMessage
        message={error}
        onRetry={fetchTenantProfile}
      />
    )
  }

  if (!tenant) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-center text-gray-500">No tenant information available</p>
        </CardContent>
      </Card>
    )
  }

  const formatDate = (dateString?: string): string => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString()
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-xl font-semibold">租户信息</CardTitle>
        {showActions && (
          <Button variant="outline" size="sm" onClick={onEdit}>
            编辑
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 基本信息 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium text-gray-500">租户ID</label>
            <p className="text-sm font-mono bg-gray-100 p-2 rounded">{tenant.id}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">邮箱地址</label>
            <p className="text-sm">{tenant.email}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">显示名称</label>
            <p className="text-sm">{tenant.display_name || '未设置'}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">状态</label>
            <div className="mt-1">
              <Badge variant={getStatusBadgeVariant(tenant.status)}>
                {tenant.status === 'active' && '活跃'}
                {tenant.status === 'suspended' && '暂停'}
                {tenant.status === 'deleted' && '已删除'}
              </Badge>
            </div>
          </div>
        </div>

        {/* 存储配额 */}
        <div>
          <label className="text-sm font-medium text-gray-500">存储配额</label>
          <p className="text-sm">{(tenant.storage_quota_mb / 1024).toFixed(1)} GB</p>
        </div>

        {/* 设置信息 */}
        <div>
          <label className="text-sm font-medium text-gray-500 mb-2 block">设置信息</label>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="font-medium">时区:</span> {tenant.settings.timezone}
            </div>
            <div>
              <span className="font-medium">语言:</span> {tenant.settings.language}
            </div>
            <div>
              <span className="font-medium">主题:</span> {tenant.settings.ui_preferences.theme}
            </div>
          </div>
        </div>

        {/* 通知设置 */}
        <div>
          <label className="text-sm font-medium text-gray-500 mb-2 block">通知设置</label>
          <div className="space-y-1 text-sm">
            <div className="flex items-center space-x-2">
              <span className={`w-2 h-2 rounded-full ${tenant.settings.notification_preferences.email_notifications ? 'bg-green-500' : 'bg-gray-300'}`} />
              <span>邮件通知: {tenant.settings.notification_preferences.email_notifications ? '启用' : '禁用'}</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`w-2 h-2 rounded-full ${tenant.settings.notification_preferences.system_alerts ? 'bg-green-500' : 'bg-gray-300'}`} />
              <span>系统警报: {tenant.settings.notification_preferences.system_alerts ? '启用' : '禁用'}</span>
            </div>
          </div>
        </div>

        {/* 时间信息 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <label className="text-sm font-medium text-gray-500">创建时间</label>
            <p>{formatDate(tenant.created_at)}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">更新时间</label>
            <p>{formatDate(tenant.updated_at)}</p>
          </div>
        </div>

        {loading && (
          <div className="flex justify-center">
            <LoadingSpinner size="sm" />
          </div>
        )}

        {error && (
          <ErrorMessage
            message={error}
            onRetry={fetchTenantProfile}
            className="mt-4"
          />
        )}
      </CardContent>
    </Card>
  )
}

export default TenantProfile