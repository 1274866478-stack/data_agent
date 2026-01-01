/**
 * # OfflineStatusIndicator 离线状态与同步指示器
 *
 * ## [MODULE]
 * **文件名**: OfflineStatusIndicator.tsx
 * **职责**: 显示在线/离线状态、同步进度、缓存统计，支持手动触发同步
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - **className**: string (可选) - 自定义样式类名
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - Popover触发按钮和详情面板
 * - **副作用**: 手动同步时调用chatStore.syncPendingMessages()
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [lucide-react](https://lucide.dev) - 图标库
 * - [@/components/ui/*](../ui/) - UI基础组件（Button, Badge, Popover, Progress）
 * - [@/store/chatStore.ts](../../store/chatStore.ts) - 在线状态和同步方法
 * - [@/services/messageCacheService.ts](../../services/messageCacheService.ts) - 缓存统计和同步事件
 * - [@/lib/utils.ts](../../lib/utils.ts) - 工具函数
 *
 * **下游依赖**:
 * - 无直接下游组件
 *
 * **调用方**:
 * - [./ChatInterface.tsx](./ChatInterface.tsx) - 聊天界面顶部的状态指示器
 *
 * ## [STATE]
 * - **syncProgress**: number - 同步进度百分比
 * - **syncMessage**: string | null - 同步状态消息
 * - **cacheStats**: 缓存统计（待同步、失败、总会话、总消息）
 *
 * ## [SIDE-EFFECTS]
 * - 监听同步事件（start, progress, complete, error）
 * - 每5秒自动更新缓存统计
 * - 支持手动触发同步和重试失败消息
 * - 根据状态自动切换图标（在线/离线/同步中/有失败/待同步）
 * - 有待处理消息时显示脉冲动画
 */
'use client'

import { useEffect, useState } from 'react'
import { Wifi, WifiOff, RefreshCw, AlertCircle, Check, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Progress } from '@/components/ui/progress'
import { useChatStore } from '@/store/chatStore'
import {
  messageCacheService,
  addSyncEventListener,
  removeSyncEventListener,
  SyncEvent,
} from '@/services/messageCacheService'
import { cn } from '@/lib/utils'

interface OfflineStatusIndicatorProps {
  className?: string
}

export function OfflineStatusIndicator({ className }: OfflineStatusIndicatorProps) {
  const { isOnline, isSyncing, syncPendingMessages, stats } = useChatStore()
  const [syncProgress, setSyncProgress] = useState(0)
  const [syncMessage, setSyncMessage] = useState<string | null>(null)
  const [cacheStats, setCacheStats] = useState({
    pendingMessages: 0,
    failedMessages: 0,
    totalMessages: 0,
    totalSessions: 0,
  })

  // 监听同步事件
  useEffect(() => {
    const handleSyncEvent = (event: SyncEvent) => {
      switch (event.type) {
        case 'start':
          setSyncProgress(0)
          setSyncMessage(`正在同步 ${event.totalMessages} 条消息...`)
          break
        case 'progress':
          setSyncProgress(event.progress || 0)
          setSyncMessage(`同步中... ${event.syncedCount}/${event.totalMessages}`)
          break
        case 'complete':
          setSyncProgress(100)
          if (event.failedCount && event.failedCount > 0) {
            setSyncMessage(`同步完成，${event.failedCount} 条失败`)
          } else {
            setSyncMessage('同步完成')
          }
          // 3秒后清除消息
          setTimeout(() => setSyncMessage(null), 3000)
          break
        case 'error':
          setSyncMessage(event.message || '同步失败')
          setTimeout(() => setSyncMessage(null), 5000)
          break
      }
    }

    addSyncEventListener(handleSyncEvent)
    return () => removeSyncEventListener(handleSyncEvent)
  }, [])

  // 定期更新缓存统计
  useEffect(() => {
    const updateStats = () => {
      const stats = messageCacheService.getCacheStats()
      setCacheStats(stats)
    }

    updateStats()
    const interval = setInterval(updateStats, 5000) // 每5秒更新一次

    return () => clearInterval(interval)
  }, [])

  // 手动触发同步
  const handleManualSync = async () => {
    if (!isOnline || isSyncing) return
    await syncPendingMessages()
  }

  // 获取状态图标和颜色
  const getStatusIcon = () => {
    if (!isOnline) {
      return <WifiOff className="w-4 h-4 text-destructive" />
    }
    if (isSyncing) {
      return <Loader2 className="w-4 h-4 text-primary animate-spin" />
    }
    if (cacheStats.failedMessages > 0) {
      return <AlertCircle className="w-4 h-4 text-warning" />
    }
    if (cacheStats.pendingMessages > 0) {
      return <RefreshCw className="w-4 h-4 text-muted-foreground" />
    }
    return <Wifi className="w-4 h-4 text-green-500" />
  }

  const getStatusText = () => {
    if (!isOnline) return '离线'
    if (isSyncing) return '同步中'
    if (cacheStats.failedMessages > 0) return `${cacheStats.failedMessages} 条失败`
    if (cacheStats.pendingMessages > 0) return `${cacheStats.pendingMessages} 待同步`
    return '已同步'
  }

  const hasPendingActions = cacheStats.pendingMessages > 0 || cacheStats.failedMessages > 0

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            'h-8 px-2 gap-1.5',
            !isOnline && 'text-destructive',
            hasPendingActions && 'animate-pulse',
            className
          )}
        >
          {getStatusIcon()}
          <span className="text-xs hidden sm:inline">{getStatusText()}</span>
          {hasPendingActions && (
            <Badge variant="secondary" className="h-5 px-1.5 text-xs">
              {cacheStats.pendingMessages + cacheStats.failedMessages}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72" align="end">
        <div className="space-y-4">
          {/* 状态标题 */}
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-sm">同步状态</h4>
            <div className="flex items-center gap-1.5">
              {getStatusIcon()}
              <span className="text-xs text-muted-foreground">
                {isOnline ? '在线' : '离线'}
              </span>
            </div>
          </div>

          {/* 同步进度 */}
          {isSyncing && (
            <div className="space-y-2">
              <Progress value={syncProgress} className="h-2" />
              <p className="text-xs text-muted-foreground">{syncMessage}</p>
            </div>
          )}

          {/* 同步消息（非同步状态时显示） */}
          {!isSyncing && syncMessage && (
            <p className="text-xs text-muted-foreground">{syncMessage}</p>
          )}

          {/* 缓存统计 */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex justify-between p-2 bg-muted rounded">
              <span className="text-muted-foreground">待同步</span>
              <span className="font-medium">{cacheStats.pendingMessages}</span>
            </div>
            <div className="flex justify-between p-2 bg-muted rounded">
              <span className="text-muted-foreground">失败</span>
              <span className={cn(
                'font-medium',
                cacheStats.failedMessages > 0 && 'text-destructive'
              )}>
                {cacheStats.failedMessages}
              </span>
            </div>
            <div className="flex justify-between p-2 bg-muted rounded">
              <span className="text-muted-foreground">总会话</span>
              <span className="font-medium">{cacheStats.totalSessions}</span>
            </div>
            <div className="flex justify-between p-2 bg-muted rounded">
              <span className="text-muted-foreground">总消息</span>
              <span className="font-medium">{cacheStats.totalMessages}</span>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={handleManualSync}
              disabled={!isOnline || isSyncing || cacheStats.pendingMessages === 0}
            >
              {isSyncing ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <RefreshCw className="w-3 h-3 mr-1" />
              )}
              同步
            </Button>
            {cacheStats.failedMessages > 0 && (
              <Button
                variant="outline"
                size="sm"
                className="flex-1"
                onClick={handleManualSync}
                disabled={!isOnline || isSyncing}
              >
                <AlertCircle className="w-3 h-3 mr-1" />
                重试失败
              </Button>
            )}
          </div>

          {/* 离线提示 */}
          {!isOnline && (
            <div className="p-2 bg-destructive/10 text-destructive text-xs rounded">
              <p className="flex items-center gap-1">
                <WifiOff className="w-3 h-3" />
                网络连接已断开，消息将在恢复后自动同步
              </p>
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}

