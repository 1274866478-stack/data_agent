/**
 * # [SKELETON] 骨架屏加载组件
 *
 * ## [MODULE]
 * **文件名**: skeleton.tsx
 * **职责**: 提供优雅的内容加载占位符
 *
 * ## [DESCRIPTION]
 * 遵循 UX Pro Max 建议，使用骨架屏代替传统 spinner，
 * 提供更好的用户体验和感知性能。
 *
 * ## [USAGE]
 * ```tsx
 * <Skeleton className="h-4 w-32" />
 * <Skeleton className="h-12 w-12 rounded-full" />
 * ```
 *
 * ## [ACCESSIBILITY]
 * - role="status" 表示加载状态
 * - aria-live="polite" 通知屏幕阅读器
 * - span.visually-hidden 提供文本描述
 */

import * as React from 'react'
import { cn } from '@/lib/utils'

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * 骨架屏动画变体
   * @default 'pulse'
   */
  variant?: 'pulse' | 'shimmer' | 'none'
}

/**
 * Skeleton 组件 - 内容加载占位符
 */
const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, variant = 'pulse', ...props }, ref) => {
    const variantClasses = {
      pulse: 'animate-pulse',
      shimmer: 'animate-shimmer',
      none: '',
    }

    return (
      <div
        ref={ref}
        className={cn(
          'bg-muted rounded-md',
          variantClasses[variant],
          className
        )}
        {...props}
      />
    )
  }
)
Skeleton.displayName = 'Skeleton'

/**
 * SkeletonCard - 卡片骨架屏
 */
interface SkeletonCardProps {
  /**
   * 是否显示头像
   */
  showAvatar?: boolean
  /**
   * 行数
   */
  lines?: number
  /**
   * 自定义类名
   */
  className?: string
}

export function SkeletonCard({
  showAvatar = false,
  lines = 3,
  className,
}: SkeletonCardProps) {
  return (
    <div
      className={cn(
        'rounded-lg border bg-card p-4 space-y-3',
        className
      )}
      role="status"
      aria-live="polite"
      aria-label="加载中"
    >
      {showAvatar && (
        <div className="flex items-center space-x-4">
          <Skeleton className="h-12 w-12 rounded-full" />
          <div className="space-y-2 flex-1">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-3 w-16" />
          </div>
        </div>
      )}
      <div className="space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton
            key={i}
            className={cn(
              'h-4',
              i === lines - 1 ? 'w-3/4' : 'w-full'
            )}
          />
        ))}
      </div>
      <span className="sr-only">正在加载内容...</span>
    </div>
  )
}

/**
 * SkeletonTable - 表格骨架屏
 */
interface SkeletonTableProps {
  /**
   * 行数
   */
  rows?: number
  /**
   * 列数
   */
  cols?: number
  /**
   * 是否显示表头
   */
  showHeader?: boolean
  /**
   * 自定义类名
   */
  className?: string
}

export function SkeletonTable({
  rows = 5,
  cols = 4,
  showHeader = true,
  className,
}: SkeletonTableProps) {
  return (
    <div
      className={cn('rounded-lg border bg-card', className)}
      role="status"
      aria-live="polite"
      aria-label="正在加载表格数据"
    >
      <div className="divide-y">
        {showHeader && (
          <div className="flex gap-4 p-4 bg-muted/50">
            {Array.from({ length: cols }).map((_, i) => (
              <Skeleton key={i} className="h-4 flex-1" />
            ))}
          </div>
        )}
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex gap-4 p-4">
            {Array.from({ length: cols }).map((_, j) => (
              <Skeleton key={j} className="h-4 flex-1" />
            ))}
          </div>
        ))}
      </div>
      <span className="sr-only">正在加载表格数据...</span>
    </div>
  )
}

/**
 * SkeletonChart - 图表骨架屏
 */
interface SkeletonChartProps {
  /**
   * 图表类型
   */
  type?: 'bar' | 'line' | 'pie'
  /**
   * 自定义类名
   */
  className?: string
}

export function SkeletonChart({
  type = 'bar',
  className,
}: SkeletonChartProps) {
  return (
    <div
      className={cn('rounded-lg border bg-card p-4', className)}
      role="status"
      aria-live="polite"
      aria-label="正在加载图表"
    >
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-8 w-24" />
        </div>
        <div
          className={cn(
            'h-64 bg-muted rounded-md',
            type === 'bar' && 'flex items-end justify-around p-4 gap-2'
          )}
        >
          {type === 'bar' &&
            Array.from({ length: 8 }).map((_, i) => (
              <Skeleton
                key={i}
                className="w-full rounded-t"
                style={{ height: `${Math.random() * 60 + 20}%` }}
              />
            ))}
        </div>
      </div>
      <span className="sr-only">正在加载图表数据...</span>
    </div>
  )
}

/**
 * SkeletonList - 列表骨架屏
 */
interface SkeletonListProps {
  /**
   * 项目数量
   */
  count?: number
  /**
   * 是否显示图标
   */
  showIcon?: boolean
  /**
   * 自定义类名
   */
  className?: string
}

export function SkeletonList({
  count = 5,
  showIcon = false,
  className,
}: SkeletonListProps) {
  return (
    <div
      className={cn('space-y-3', className)}
      role="status"
      aria-live="polite"
      aria-label="正在加载列表"
    >
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 p-3 rounded-lg border bg-card"
        >
          {showIcon && <Skeleton className="h-10 w-10 rounded-md" />}
          <div className="space-y-2 flex-1">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          <Skeleton className="h-8 w-20" />
        </div>
      ))}
      <span className="sr-only">正在加载列表项...</span>
    </div>
  )
}

export { Skeleton }
export default Skeleton
