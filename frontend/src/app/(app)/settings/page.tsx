/**
 * # SettingsPage 系统设置页面
 *
 * ## [MODULE]
 * **文件名**: app/(app)/settings/page.tsx
 * **职责**: 提供租户系统设置界面，包括显示名称、时区、语言、主题、通知和存储配额配置
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - 无直接 Props（页面组件）
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 系统设置页面，包含设置表单和保存功能
 *
 * ## [LINK]
 * **上游依赖**:
 * - [@/components/ui/card](../../components/ui/card.tsx) - 卡片容器组件
 * - [@/components/ui/button](../../components/ui/button.tsx) - 按钮组件
 * - [@/components/ui/input](../../components/ui/input.tsx) - 输入框组件
 * - [@/components/ui/label](../../components/ui/label.tsx) - 标签组件
 * - [@/components/ui/switch](../../components/ui/switch.tsx) - 开关组件
 * - [lucide-react](https://lucide.dev) - 图标库
 *
 * **下游依赖**:
 * - 无（页面是用户交互入口点）
 *
 * ## [STATE]
 * - **settings: TenantSettings** - 当前设置对象，包含 display_name, timezone, language, theme, email_notifications, system_alerts, storage_quota_mb
 * - **loading: boolean** - 加载状态
 * - **error: string | null** - 错误信息
 * - **success: boolean** - 保存成功状态
 *
 * ## [SIDE-EFFECTS]
 * - **设置加载**: 组件挂载时调用 loadSettings() 获取当前设置（TODO: 待实现API）
 * - **设置保存**: 调用 handleSave() 保存设置更改（TODO: 待实现API）
 * - **成功提示**: 保存成功后显示3秒成功提示
 * - **错误处理**: 显示和清除错误信息
 * - **字段更新**: 实时更新设置对象的状态
 */
'use client'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { AlertCircle, Bell, Database, Save, Settings } from 'lucide-react'
import { useEffect, useState } from 'react'

interface TenantSettings {
  display_name: string
  timezone: string
  language: string
  theme: string
  email_notifications: boolean
  system_alerts: boolean
  storage_quota_mb: number
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<TenantSettings>({
    display_name: '我的租户',
    timezone: 'Asia/Shanghai',
    language: 'zh-CN',
    theme: 'light',
    email_notifications: true,
    system_alerts: true,
    storage_quota_mb: 1024
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // TODO: 调用后端API获取设置
      // const response = await fetch('/api/v1/tenants/me')
      // const data = await response.json()
      // setSettings(data.settings)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载设置失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setLoading(true)
      setError(null)
      setSuccess(false)
      
      // TODO: 调用后端API保存设置
      // await fetch('/api/v1/tenants/me', {
      //   method: 'PUT',
      //   body: JSON.stringify(settings)
      // })
      
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存设置失败')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (field: keyof TenantSettings, value: any) => {
    setSettings(prev => ({ ...prev, [field]: value }))
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">系统设置</h1>
          <p className="text-gray-300 mt-2">管理租户配置和系统偏好</p>
        </div>
        <Button onClick={handleSave} disabled={loading} className="bg-gradient-modern-primary hover:opacity-90 transition-opacity">
          <Save className="h-4 w-4 mr-2" />
          {loading ? '保存中...' : '保存设置'}
        </Button>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <p>{error}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {success && (
        <Card className="border-green-500">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-green-600">
              <Settings className="h-5 w-5" />
              <p>设置已成功保存</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 基本设置 */}
      <Card className="hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            基本设置
          </CardTitle>
          <CardDescription>配置租户的基本信息</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="display_name">显示名称</Label>
            <Input
              id="display_name"
              value={settings.display_name}
              onChange={(e) => handleChange('display_name', e.target.value)}
              placeholder="输入租户显示名称"
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="timezone">时区</Label>
              <Input
                id="timezone"
                value={settings.timezone}
                onChange={(e) => handleChange('timezone', e.target.value)}
                placeholder="Asia/Shanghai"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="language">语言</Label>
              <Input
                id="language"
                value={settings.language}
                onChange={(e) => handleChange('language', e.target.value)}
                placeholder="zh-CN"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 通知设置 */}
      <Card className="hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            通知设置
          </CardTitle>
          <CardDescription>管理系统通知和提醒</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>邮件通知</Label>
              <p className="text-sm text-muted-foreground">接收重要事件的邮件通知</p>
            </div>
            <Switch
              checked={settings.email_notifications}
              onCheckedChange={(checked) => handleChange('email_notifications', checked)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>系统警报</Label>
              <p className="text-sm text-muted-foreground">接收系统状态和错误警报</p>
            </div>
            <Switch
              checked={settings.system_alerts}
              onCheckedChange={(checked) => handleChange('system_alerts', checked)}
            />
          </div>
        </CardContent>
      </Card>

      {/* 存储设置 */}
      <Card className="hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            存储配额
          </CardTitle>
          <CardDescription>管理数据存储限制</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label htmlFor="storage_quota">存储配额 (MB)</Label>
            <Input
              id="storage_quota"
              type="number"
              value={settings.storage_quota_mb}
              onChange={(e) => handleChange('storage_quota_mb', parseInt(e.target.value))}
              min={0}
            />
            <p className="text-sm text-muted-foreground">
              当前使用: 256 MB / {settings.storage_quota_mb} MB
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

