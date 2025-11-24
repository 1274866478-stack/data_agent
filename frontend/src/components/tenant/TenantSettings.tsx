/**
 * 租户设置管理组件
 * 实现Story-2.2要求的租户设置管理
 */

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { LoadingSpinner } from '../ui/loading-spinner'
import { ErrorMessage } from '../ui/error-message'
import { useCurrentTenant, useTenantLoading, useTenantError, useTenantActions } from '../../store/tenantStore'

interface TenantSettingsProps {
  onSave?: () => void
  onCancel?: () => void
}

interface SettingsFormData {
  display_name: string
  timezone: string
  language: string
  theme: string
  dashboard_layout: string
  email_notifications: boolean
  system_alerts: boolean
  storage_quota_mb: number
}

export const TenantSettings: React.FC<TenantSettingsProps> = ({
  onSave,
  onCancel
}) => {
  const tenant = useCurrentTenant()
  const loading = useTenantLoading()
  const error = useTenantError()
  const { updateTenantProfile } = useTenantActions()

  const [formData, setFormData] = useState<SettingsFormData>({
    display_name: '',
    timezone: 'UTC',
    language: 'en',
    theme: 'light',
    dashboard_layout: 'default',
    email_notifications: true,
    system_alerts: true,
    storage_quota_mb: 1024
  })

  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    if (tenant) {
      setFormData({
        display_name: tenant.display_name || '',
        timezone: tenant.settings.timezone,
        language: tenant.settings.language,
        theme: tenant.settings.ui_preferences.theme,
        dashboard_layout: tenant.settings.ui_preferences.dashboard_layout,
        email_notifications: tenant.settings.notification_preferences.email_notifications,
        system_alerts: tenant.settings.notification_preferences.system_alerts,
        storage_quota_mb: tenant.storage_quota_mb
      })
    }
  }, [tenant])

  const handleInputChange = (field: keyof SettingsFormData, value: string | number | boolean) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
    setHasChanges(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      const updateData = {
        display_name: formData.display_name || undefined,
        settings: {
          timezone: formData.timezone,
          language: formData.language,
          notification_preferences: {
            email_notifications: formData.email_notifications,
            system_alerts: formData.system_alerts
          },
          ui_preferences: {
            theme: formData.theme,
            dashboard_layout: formData.dashboard_layout
          }
        },
        storage_quota_mb: formData.storage_quota_mb
      }

      await updateTenantProfile(updateData)
      setHasChanges(false)
      onSave?.()
    } catch (error) {
      // 错误已由store处理
    }
  }

  const handleReset = () => {
    if (tenant) {
      setFormData({
        display_name: tenant.display_name || '',
        timezone: tenant.settings.timezone,
        language: tenant.settings.language,
        theme: tenant.settings.ui_preferences.theme,
        dashboard_layout: tenant.settings.ui_preferences.dashboard_layout,
        email_notifications: tenant.settings.notification_preferences.email_notifications,
        system_alerts: tenant.settings.notification_preferences.system_alerts,
        storage_quota_mb: tenant.storage_quota_mb
      })
      setHasChanges(false)
    }
  }

  if (!tenant) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center p-6">
          <p className="text-gray-500">No tenant information available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl font-semibold">租户设置</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 基本信息 */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">基本信息</h3>
            <div>
              <Label htmlFor="display_name">显示名称</Label>
              <Input
                id="display_name"
                value={formData.display_name}
                onChange={(e) => handleInputChange('display_name', e.target.value)}
                placeholder="输入租户显示名称"
              />
            </div>
          </div>

          {/* 本地化设置 */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">本地化设置</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="timezone">时区</Label>
                <select
                  id="timezone"
                  value={formData.timezone}
                  onChange={(e) => handleInputChange('timezone', e.target.value)}
                  className="w-full mt-1 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="UTC">UTC</option>
                  <option value="Asia/Shanghai">Asia/Shanghai</option>
                  <option value="America/New_York">America/New_York</option>
                  <option value="Europe/London">Europe/London</option>
                </select>
              </div>
              <div>
                <Label htmlFor="language">语言</Label>
                <select
                  id="language"
                  value={formData.language}
                  onChange={(e) => handleInputChange('language', e.target.value)}
                  className="w-full mt-1 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="en">English</option>
                  <option value="zh">中文</option>
                </select>
              </div>
            </div>
          </div>

          {/* UI设置 */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">界面设置</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="theme">主题</Label>
                <select
                  id="theme"
                  value={formData.theme}
                  onChange={(e) => handleInputChange('theme', e.target.value)}
                  className="w-full mt-1 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="light">浅色主题</option>
                  <option value="dark">深色主题</option>
                  <option value="auto">跟随系统</option>
                </select>
              </div>
              <div>
                <Label htmlFor="dashboard_layout">仪表板布局</Label>
                <select
                  id="dashboard_layout"
                  value={formData.dashboard_layout}
                  onChange={(e) => handleInputChange('dashboard_layout', e.target.value)}
                  className="w-full mt-1 p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="default">默认布局</option>
                  <option value="compact">紧凑布局</option>
                  <option value="expanded">扩展布局</option>
                </select>
              </div>
            </div>
          </div>

          {/* 通知设置 */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">通知设置</h3>
            <div className="space-y-3">
              <div className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  id="email_notifications"
                  checked={formData.email_notifications}
                  onChange={(e) => handleInputChange('email_notifications', e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <Label htmlFor="email_notifications" className="text-sm">
                  接收邮件通知
                </Label>
              </div>
              <div className="flex items-center space-x-3">
                <input
                  type="checkbox"
                  id="system_alerts"
                  checked={formData.system_alerts}
                  onChange={(e) => handleInputChange('system_alerts', e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <Label htmlFor="system_alerts" className="text-sm">
                  接收系统警报
                </Label>
              </div>
            </div>
          </div>

          {/* 存储配额 */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium text-gray-900">存储配额</h3>
            <div>
              <Label htmlFor="storage_quota_mb">存储配额 (GB)</Label>
              <Input
                id="storage_quota_mb"
                type="number"
                value={(formData.storage_quota_mb / 1024).toFixed(1)}
                onChange={(e) => handleInputChange('storage_quota_mb', Math.max(1, parseFloat(e.target.value) || 1) * 1024)}
                min="1"
                step="0.1"
              />
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex justify-end space-x-3 pt-4 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                handleReset()
                onCancel?.()
              }}
              disabled={loading}
            >
              取消
            </Button>
            <Button
              type="submit"
              disabled={loading || !hasChanges}
            >
              {loading ? (
                <>
                  <LoadingSpinner size="sm" className="mr-2" />
                  保存中...
                </>
              ) : (
                '保存设置'
              )}
            </Button>
          </div>

          {error && (
            <ErrorMessage
              message={error}
              className="mt-4"
            />
          )}
        </form>
      </CardContent>
    </Card>
  )
}

export default TenantSettings