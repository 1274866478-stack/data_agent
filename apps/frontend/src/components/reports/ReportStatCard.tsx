/**
 * ReportStatCard - 报告页面统计卡片组件
 * Tiffany 玻璃态风格
 */

import { MaterialIcon } from '@/components/icons/MaterialIcon'
import { cn } from '@/lib/utils'

interface ReportStatCardProps {
  /** 左上角标签 */
  label: string
  /** Material 图标名称 */
  icon: string
  /** 主数值 */
  value: string | number
  /** 趋势标签 */
  trend?: {
    label: string
    type: 'positive' | 'neutral'
  }
  /** 柱状图数据（7个值，0-100） */
  bars?: number[]
  className?: string
}

export function ReportStatCard({
  label,
  icon,
  value,
  trend,
  bars = [40, 60, 45, 80, 70, 55, 65],
  className
}: ReportStatCardProps) {
  return (
    <div className={cn('reports-glass-card rounded-sm p-5', className)}>
      <div className="flex items-start justify-between mb-4">
        <p className="analytics-tech-label text-slate-600 dark:text-slate-400">{label}</p>
        <MaterialIcon icon={icon} className="text-tiffany/30 text-xl" />
      </div>

      <div className="flex items-baseline gap-3 mb-4">
        <span className="text-5xl digital-readout text-slate-800 dark:text-slate-200">
          {typeof value === 'number' ? String(value).padStart(4, '0') : value}
        </span>
        {trend && (
          <span className={cn('trend-tag', trend.type)}>{trend.label}</span>
        )}
      </div>

      <div className="bar-chart">
        {bars.map((height, index) => (
          <div
            key={index}
            className="bar-chart-bar"
            style={{ height: `${height}%` }}
          />
        ))}
      </div>
    </div>
  )
}
