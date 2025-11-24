'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Settings, Save, AlertCircle, Bell, Shield, Database } from 'lucide-react'

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
          <h1 className="text-3xl font-bold">系统设置</h1>
          <p className="text-muted-foreground mt-2">管理租户配置和系统偏好</p>
        </div>
        <Button onClick={handleSave} disabled={loading}>
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
      <Card>
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
      <Card>
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
      <Card>
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

