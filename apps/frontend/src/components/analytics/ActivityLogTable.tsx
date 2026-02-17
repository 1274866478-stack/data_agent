/**
 * [HEADER]
 * 活动日志表格组件 (Activity Log Table) - Analytics 页面专用
 *
 * [MODULE]
 * 模块类型: React UI 组件
 * 所属功能: 数据展示 - 实时活动日志
 * 技术栈: React, TypeScript, Tailwind CSS
 *
 * [INPUT]
 * Props:
 * - activities: ActivityLog[] - 活动日志数组
 *
 * [OUTPUT]
 * - 渲染玻璃态风格的活动日志表格
 *
 * [LINK]
 * - 使用路径: @/components/analytics/ActivityLogTable
 * - 配套组件: DonutChart, EmptyDocumentState
 *
 * [POS]
 * - 文件路径: frontend/src/components/analytics/ActivityLogTable.tsx
 *
 * [STATE]
 * - 无状态组件
 *
 * [PROTOCOL]
 * - 使用 analytics-glass-card 玻璃态样式
 * - 状态指示器带发光效果
 * - 支持悬停高亮
 */

import { MaterialIcon } from '@/components/icons/MaterialIcon'

/**
 * 活动日志状态类型
 */
export type ActivityStatus = 'success' | 'syncing' | 'warning' | 'error'

/**
 * 活动日志项
 */
export interface ActivityLog {
  /** 唯一标识 */
  id: string
  /** 状态 */
  status: ActivityStatus
  /** 源 ID / 标识码 */
  sourceId: string
  /** 操作类型 */
  operation: string
  /** 同步时间戳 */
  timestamp: string
}

interface ActivityLogTableProps {
  activities: ActivityLog[]
}

/**
 * 状态配置
 */
const statusConfig: Record<
  ActivityStatus,
  { color: string; textColor: string; label: string }
> = {
  success: {
    color: 'bg-emerald-400',
    textColor: 'text-emerald-600',
    label: 'Success',
  },
  syncing: {
    color: 'bg-tiffany',
    textColor: 'text-tiffany',
    label: 'Syncing',
  },
  warning: {
    color: 'bg-amber-400',
    textColor: 'text-amber-600',
    label: 'Warning',
  },
  error: {
    color: 'bg-red-400',
    textColor: 'text-red-600',
    label: 'Error',
  },
}

/**
 * 活动日志表格组件
 *
 * 显示带有玻璃态效果的活动日志表格
 *
 * @example
 * ```tsx
 * const activities = [
 *   {
 *     id: '1',
 *     status: 'success',
 *     sourceId: 'POSTGRES_01',
 *     operation: '创建 • 静态注入',
 *     timestamp: '2025-01-24 10:30:45.123',
 *   },
 * ]
 *
 * <ActivityLogTable activities={activities} />
 * ```
 */
export function ActivityLogTable({ activities }: ActivityLogTableProps) {
  return (
    <div className="analytics-glass-card rounded-sm overflow-hidden">
      {/* Header */}
      <div className="px-8 py-5 border-b border-tiffany/10 flex justify-between items-center bg-white/40 dark:bg-slate-800/40">
        <div className="flex items-center gap-2">
          <MaterialIcon icon="terminal" className="text-tiffany text-lg" />
          <h3 className="analytics-tech-label text-slate-800 dark:text-slate-200">
            实时活动日志
          </h3>
        </div>
        <div className="analytics-tech-label text-tiffany">实时监控激活</div>
      </div>

      {/* Table */}
      <div className="w-full overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50/30 dark:bg-slate-700/30 border-b border-tiffany/5">
              <th className="px-8 py-4 analytics-tech-label">事件状态</th>
              <th className="px-8 py-4 analytics-tech-label">源 ID / 标识码</th>
              <th className="px-8 py-4 analytics-tech-label">操作类型</th>
              <th className="px-8 py-4 analytics-tech-label">同步时间戳</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-tiffany/5">
            {activities.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-8 py-12 text-center text-slate-400">
                  <div className="flex flex-col items-center gap-3">
                    <MaterialIcon icon="history" className="text-4xl text-slate-300" />
                    <p className="analytics-tech-label text-slate-400">
                      暂无活动记录
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              activities.map((activity) => {
                const config = statusConfig[activity.status]
                return (
                  <tr
                    key={activity.id}
                    className="hover:bg-tiffany/5 dark:hover:bg-tiffany/10 transition-colors"
                  >
                    <td className="px-8 py-5">
                      <div className="flex items-center gap-3">
                        <div
                          className={`analytics-status-dot ${config.color} analytics-glow-tiffany`}
                        />
                        <span
                          className={`text-[10px] font-bold uppercase ${config.textColor}`}
                        >
                          {config.label}
                        </span>
                      </div>
                    </td>
                    <td className="px-8 py-5">
                      <span className="text-xs font-medium text-slate-700 dark:text-slate-300 font-mono">
                        {activity.sourceId}
                      </span>
                    </td>
                    <td className="px-8 py-5 text-xs text-slate-500 dark:text-slate-400 uppercase tracking-widest">
                      {activity.operation}
                    </td>
                    <td className="px-8 py-5 text-xs text-slate-400 dark:text-slate-500 font-mono">
                      {activity.timestamp}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="px-8 py-4 bg-white/20 dark:bg-slate-800/20 text-center border-t border-tiffany/5">
        <button className="analytics-tech-label text-slate-400 hover:text-tiffany transition-colors">
          加载更多实验记录
        </button>
      </div>
    </div>
  )
}

/**
 * 带加载状态的活动日志表格
 */
interface ActivityLogTableWithLoadingProps extends ActivityLogTableProps {
  isLoading?: boolean
}

export function ActivityLogTableWithLoading({
  activities,
  isLoading = false
}: ActivityLogTableWithLoadingProps) {
  if (isLoading) {
    return (
      <div className="analytics-glass-card rounded-sm overflow-hidden p-12">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-tiffany border-t-transparent rounded-full animate-spin" />
          <p className="analytics-tech-label text-slate-400">加载活动日志...</p>
        </div>
      </div>
    )
  }

  return <ActivityLogTable activities={activities} />
}
