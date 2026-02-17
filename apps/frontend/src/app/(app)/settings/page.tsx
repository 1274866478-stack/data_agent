'use client'

import { Button } from '@/components/ui/button'
import { MaterialIcon } from '@/components/icons/MaterialIcon'
import { GlassPanel } from '@/components/settings/GlassPanel'
import { SettingsInput } from '@/components/settings/SettingsInput'
import { SettingsToggle } from '@/components/settings/SettingsToggle'
import { ProgressBar } from '@/components/settings/ProgressBar'
import { SettingsSectionHeader } from '@/components/settings/SettingsSectionHeader'
import { useState, useEffect } from 'react'

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
    storage_quota_mb: 1024,
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
      // TODO: API 调用
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
      // TODO: API 调用
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存设置失败')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (field: keyof TenantSettings, value: any) => {
    setSettings((prev) => ({ ...prev, [field]: value }))
  }

  const storageUsed = 256.4
  const storagePercentage = (storageUsed / settings.storage_quota_mb) * 100

  return (
    <div className="min-h-screen bg-settings-parallax">
      <div className="flex-1 flex flex-col overflow-y-auto">
        {/* Header */}
        <header className="h-20 flex items-center justify-between px-10 shrink-0">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
              系统设置
            </h1>
            <p className="text-slate-500 text-sm mt-1 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-primary/40 animate-pulse" />
              内核调优版 · 管理租户配置和系统偏好
            </p>
          </div>
          <Button
            onClick={handleSave}
            disabled={loading}
            className="bg-primary hover:bg-primary/90 text-white px-6 py-2.5 rounded-full font-medium flex items-center gap-2 shadow-xl shadow-primary/20 transition-all"
          >
            <MaterialIcon icon="save" className="text-lg" />
            {loading ? '保存中...' : '保存设置'}
          </Button>
        </header>

        {/* Alerts */}
        {error && (
          <div className="mx-10 mb-4 p-4 rounded-xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 text-rose-600 dark:text-rose-400">
            <div className="flex items-center gap-2">
              <MaterialIcon icon="error" />
              <p>{error}</p>
            </div>
          </div>
        )}

        {success && (
          <div className="mx-10 mb-4 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 text-emerald-600 dark:text-emerald-400">
            <div className="flex items-center gap-2">
              <MaterialIcon icon="check_circle" />
              <p>设置已成功保存</p>
            </div>
          </div>
        )}

        {/* Settings Cards */}
        <div className="flex-1 px-10 pb-12 space-y-8">
          {/* 基本设置 */}
          <GlassPanel>
            <SettingsSectionHeader
              icon="settings_input_component"
              title="基本设置"
              description="配置租户的基本核心信息"
            />
            <div className="grid grid-cols-1 gap-6">
              <SettingsInput
                label="显示名称"
                value={settings.display_name}
                onChange={(e) => handleChange('display_name', e.target.value)}
                placeholder="输入名称..."
              />
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="settings-label flex items-center gap-2">
                    时区
                    <span className="w-1 h-1 bg-primary rounded-full" />
                  </label>
                  <select
                    className="w-full h-12 px-4 rounded-xl settings-input text-sm appearance-none bg-transparent"
                    value={settings.timezone}
                    onChange={(e) => handleChange('timezone', e.target.value)}
                  >
                    <option>Asia/Shanghai (UTC+8)</option>
                    <option>UTC (GMT+0)</option>
                    <option>America/New_York (UTC-5)</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="settings-label flex items-center gap-2">
                    语言
                    <span className="w-1 h-1 bg-primary rounded-full" />
                  </label>
                  <select
                    className="w-full h-12 px-4 rounded-xl settings-input text-sm appearance-none bg-transparent"
                    value={settings.language}
                    onChange={(e) => handleChange('language', e.target.value)}
                  >
                    <option>zh-CN (简体中文)</option>
                    <option>en-US (English)</option>
                    <option>ja-JP (日本語)</option>
                  </select>
                </div>
              </div>
            </div>
          </GlassPanel>

          {/* 通知设置 */}
          <GlassPanel>
            <SettingsSectionHeader
              icon="notifications_active"
              title="通知设置"
              description="管理系统通知和异常提醒阈值"
            />
            <div className="space-y-4">
              <SettingsToggle
                checked={settings.email_notifications}
                onCheckedChange={(checked) =>
                  handleChange('email_notifications', checked)
                }
                label="邮件通知"
                description="接收重要事件、离线警告和周报的邮件通知"
              />
              <div className="w-full h-px bg-slate-200/30 dark:bg-slate-700/30" />
              <SettingsToggle
                checked={settings.system_alerts}
                onCheckedChange={(checked) => handleChange('system_alerts', checked)}
                label="系统警报"
                description="接收系统运行状态异常和连接错误警报"
              />
            </div>
          </GlassPanel>

          {/* 存储配额 */}
          <GlassPanel>
            <SettingsSectionHeader
              icon="data_usage"
              title="存储配额"
              description="管理数据存储限制与资源校准"
            />
            <div className="space-y-6">
              <SettingsInput
                label="存储配额 (MB)"
                type="number"
                value={settings.storage_quota_mb.toString()}
                onChange={(e) =>
                  handleChange('storage_quota_mb', parseInt(e.target.value))
                }
                placeholder="1024"
                className="font-mono"
              />
              <div className="space-y-3">
                <div className="flex justify-between items-end">
                  <span className="text-xs text-slate-500 font-medium">
                    存储使用情况
                  </span>
                  <div className="text-right">
                    <span className="text-sm font-bold font-mono text-primary">
                      {storageUsed}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono ml-0.5">
                      {' '}
                      / {settings.storage_quota_mb.toFixed(1)} MB
                    </span>
                  </div>
                </div>
                <ProgressBar value={storageUsed} max={settings.storage_quota_mb} />
                <div className="flex justify-between">
                  <span className="text-[10px] text-slate-400 font-mono uppercase tracking-tighter">
                    Usage Floor
                  </span>
                  <span className="text-[10px] text-primary font-mono font-bold">
                    {storagePercentage.toFixed(2)}% Calibrated
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono uppercase tracking-tighter">
                    Ceiling
                  </span>
                </div>
              </div>
            </div>
          </GlassPanel>
        </div>
      </div>
    </div>
  )
}
