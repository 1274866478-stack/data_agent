/**
 * # [STREAM_CONTROL_PANEL] 流式会话控制面板组件
 *
 * ## [MODULE]
 * **文件名**: StreamControlPanel.tsx
 * **职责**: 显示和控制 V2 流式查询会话的暂停/恢复/取消操作
 *
 * ## [INPUT]
 * Props:
 * - sessionId: string - 会话ID（可选，如果不提供则使用 store 中的当前会话）
 * - className?: string - 额外的CSS类名
 *
 * ## [OUTPUT]
 * - 渲染会话控制面板，包括状态指示器和控制按钮
 *
 * ## [LINK]
 * **上游依赖**:
 * - [../store/chatStore.ts](../store/chatStore.ts) - 获取 V2 会话状态和控制方法
 * - [../types/chat.ts](../types/chat.ts) - V2 会话类型定义
 *
 * **下游依赖**:
 * - [ChatInterface.tsx](./ChatInterface.tsx) - 聊天界面集成
 *
 * ## [STATE]
 * - 从 chatStore 订阅 v2Session 状态
 * - 本地 loading 状态用于操作反馈
 *
 * ## [SIDE-EFFECTS]
 * - 调用 chatStore 的 pauseV2Session/resumeV2Session/cancelV2Session 方法
 * - 触发状态更新导致 UI 重新渲染
 */

import React, { useState, useCallback } from 'react'
import { useChatStore } from '@/store/chatStore'
import { V2SessionStatus } from '@/types/chat'
import { Pause, Play, X, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StreamControlPanelProps {
  sessionId?: string
  className?: string
}

/**
 * 获取状态对应的图标和样式
 */
const getStatusInfo = (status: V2SessionStatus, isPaused: boolean) => {
  // 优先检查 isPaused 状态
  if (isPaused || status === 'paused') {
    return {
      icon: Pause,
      iconClassName: 'text-yellow-600',
      bgClassName: 'bg-yellow-50 border-yellow-200',
      text: '已暂停',
      textColor: 'text-yellow-700'
    }
  }

  switch (status) {
    case 'running':
      return {
        icon: Loader2,
        iconClassName: 'text-blue-600 animate-spin',
        bgClassName: 'bg-blue-50 border-blue-200',
        text: '运行中',
        textColor: 'text-blue-700'
      }
    case 'completed':
      return {
        icon: CheckCircle2,
        iconClassName: 'text-green-600',
        bgClassName: 'bg-green-50 border-green-200',
        text: '已完成',
        textColor: 'text-green-700'
      }
    case 'error':
      return {
        icon: AlertCircle,
        iconClassName: 'text-red-600',
        bgClassName: 'bg-red-50 border-red-200',
        text: '错误',
        textColor: 'text-red-700'
      }
    case 'cancelled':
      return {
        icon: X,
        iconClassName: 'text-gray-600',
        bgClassName: 'bg-gray-50 border-gray-200',
        text: '已取消',
        textColor: 'text-gray-700'
      }
    default:
      return {
        icon: Loader2,
        iconClassName: 'text-gray-600',
        bgClassName: 'bg-gray-50 border-gray-200',
        text: '未知状态',
        textColor: 'text-gray-700'
      }
  }
}

/**
 * V2 流式会话控制面板组件
 */
export const StreamControlPanel: React.FC<StreamControlPanelProps> = ({
  sessionId: propSessionId,
  className
}) => {
  const [localLoading, setLocalLoading] = useState<string | null>(null)

  // 从 store 获取状态和方法
  const v2Session = useChatStore((state) => state.v2Session)
  const pauseV2Session = useChatStore((state) => state.pauseV2Session)
  const resumeV2Session = useChatStore((state) => state.resumeV2Session)
  const cancelV2Session = useChatStore((state) => state.cancelV2Session)

  // 使用传入的 sessionId 或 store 中的当前会话 ID
  const activeSessionId = propSessionId || v2Session.currentSessionId
  const sessionState = v2Session.sessionState
  const isPaused = v2Session.isPaused

  // 如果没有活跃会话，不渲染
  if (!activeSessionId) {
    return null
  }

  // 获取当前状态（优先使用 sessionState.status，否则根据 isPaused 推断）
  const currentStatus: V2SessionStatus = sessionState?.status || (isPaused ? 'paused' : 'running')
  const progress = sessionState?.current_progress || 0

  const statusInfo = getStatusInfo(currentStatus, isPaused)
  const StatusIcon = statusInfo.icon

  // 检查是否可以控制（只有 running 或 paused 状态可以控制）
  const canControl = currentStatus === 'running' || currentStatus === 'paused'

  /**
   * 暂停会话
   */
  const handlePause = useCallback(async () => {
    if (!activeSessionId) return
    setLocalLoading('pause')
    try {
      await pauseV2Session(activeSessionId)
    } finally {
      setLocalLoading(null)
    }
  }, [activeSessionId, pauseV2Session])

  /**
   * 恢复会话
   */
  const handleResume = useCallback(async () => {
    if (!activeSessionId) return
    setLocalLoading('resume')
    try {
      await resumeV2Session(activeSessionId)
    } finally {
      setLocalLoading(null)
    }
  }, [activeSessionId, resumeV2Session])

  /**
   * 取消会话
   */
  const handleCancel = useCallback(async () => {
    if (!activeSessionId) return
    setLocalLoading('cancel')
    try {
      await cancelV2Session(activeSessionId)
    } finally {
      setLocalLoading(null)
    }
  }, [activeSessionId, cancelV2Session])

  // 如果会话已完成/取消/出错且没有累积答案，不显示控制面板
  if (!canControl && (!sessionState?.accumulated_answer || sessionState.accumulated_answer.length === 0)) {
    return null
  }

  return (
    <div className={cn(
      'rounded-lg border p-3 space-y-2',
      statusInfo.bgClassName,
      className
    )}>
      {/* 状态指示器 */}
      <div className="flex items-center gap-2">
        <StatusIcon className={cn('w-4 h-4', statusInfo.iconClassName)} />
        <span className={cn('text-sm font-medium', statusInfo.textColor)}>
          {statusInfo.text}
        </span>
        {progress > 0 && progress < 100 && (
          <span className="text-sm text-gray-600 ml-auto">
            {progress}%
          </span>
        )}
      </div>

      {/* 进度条（如果有进度） */}
      {progress > 0 && progress < 100 && (
        <div className="w-full bg-gray-200 rounded-full h-1.5">
          <div
            className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* 控制按钮 */}
      {canControl && (
        <div className="flex items-center gap-2">
          {isPaused || currentStatus === 'paused' ? (
            // 暂停状态：显示恢复按钮
            <button
              onClick={handleResume}
              disabled={localLoading === 'resume'}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
                'bg-blue-600 text-white hover:bg-blue-700',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'transition-colors'
              )}
            >
              {localLoading === 'resume' ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5" />
              )}
              <span>恢复</span>
            </button>
          ) : (
            // 运行状态：显示暂停按钮
            <button
              onClick={handlePause}
              disabled={localLoading === 'pause'}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
                'bg-yellow-600 text-white hover:bg-yellow-700',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'transition-colors'
              )}
            >
              {localLoading === 'pause' ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Pause className="w-3.5 h-3.5" />
              )}
              <span>暂停</span>
            </button>
          )}

          {/* 取消按钮 */}
          <button
            onClick={handleCancel}
            disabled={localLoading === 'cancel'}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
              'bg-red-600 text-white hover:bg-red-700',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'transition-colors'
            )}
          >
            {localLoading === 'cancel' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <X className="w-3.5 h-3.5" />
            )}
            <span>取消</span>
          </button>
        </div>
      )}
    </div>
  )
}

export default StreamControlPanel
