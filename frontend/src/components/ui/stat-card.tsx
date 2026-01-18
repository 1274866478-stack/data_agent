/**
 * # [STAT_CARD] 统计卡片组件
 *
 * ## [MODULE]
 * **文件名**: stat-card.tsx
 * **职责**: 提供用于仪表板的统计卡片，包含图标、数值、变化趋势
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 */

import { cn } from '@/lib/utils'
import { LucideIcon, Minus, TrendingDown, TrendingUp } from 'lucide-react'
import * as React from 'react'

// 渐变色配置
const gradientVariants = {
  primary: 'bg-gradient-to-r from-violet-600 to-purple-600',
  secondary: 'bg-gradient-to-r from-pink-600 to-rose-600',
  accent: 'bg-gradient-to-r from-blue-600 to-cyan-600',
  success: 'bg-gradient-to-r from-green-600 to-emerald-600',
  warning: 'bg-gradient-to-r from-orange-600 to-amber-600',
} as const

// 背景色配置（浅色渐变）
const bgVariants = {
  primary: 'from-violet-500/10 to-purple-500/10',
  secondary: 'from-pink-500/10 to-rose-500/10',
  accent: 'from-blue-500/10 to-cyan-500/10',
  success: 'from-green-500/10 to-emerald-500/10',
  warning: 'from-orange-500/10 to-amber-500/10',
} as const

// 图标背景色
const iconBgVariants = {
  primary: 'bg-violet-500/20 text-violet-600 dark:text-violet-400',
  secondary: 'bg-pink-500/20 text-pink-600 dark:text-pink-400',
  accent: 'bg-blue-500/20 text-blue-600 dark:text-blue-400',
  success: 'bg-green-500/20 text-green-600 dark:text-green-400',
  warning: 'bg-orange-500/20 text-orange-600 dark:text-orange-400',
} as const

export interface StatCardProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  value: string | number
  icon?: LucideIcon
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  gradient?: keyof typeof gradientVariants
  variant?: 'default' | 'filled'
}

const StatCard = React.forwardRef<HTMLDivElement, StatCardProps>(
  ({ 
    className, 
    title, 
    value, 
    icon: Icon, 
    trend, 
    trendValue,
    gradient = 'primary',
    variant = 'default',
    ...props 
  }, ref) => {
    const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
    const trendColor = trend === 'up'
      ? 'text-green-600 dark:text-green-400'
      : trend === 'down'
        ? 'text-destructive dark:text-destructive'
        : 'text-muted-foreground'

    const cardClasses = variant === 'filled'
      ? cn(gradientVariants[gradient], 'text-white')
      : cn('bg-gradient-to-br', bgVariants[gradient], 'border border-border')

    return (
      <div
        ref={ref}
        className={cn(
          'rounded-xl p-6 transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5',
          cardClasses,
          className
        )}
        {...props}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className={cn(
              'text-sm font-medium mb-1',
              variant === 'filled' ? 'text-white/80' : 'text-muted-foreground'
            )}>
              {title}
            </p>
            <p className={cn(
              'text-3xl font-bold',
              variant === 'filled' ? 'text-white' : 'text-foreground'
            )}>
              {value}
            </p>
            
            {/* 趋势指示 */}
            {trend && trendValue && (
              <div className={cn('flex items-center gap-1 mt-2', trendColor)}>
                <TrendIcon className="h-4 w-4" />
                <span className="text-sm font-medium">{trendValue}</span>
              </div>
            )}
          </div>

          {/* 图标 */}
          {Icon && (
            <div className={cn(
              'w-12 h-12 rounded-xl flex items-center justify-center',
              variant === 'filled' 
                ? 'bg-white/20' 
                : iconBgVariants[gradient]
            )}>
              <Icon className={cn(
                'h-6 w-6',
                variant === 'filled' ? 'text-white' : ''
              )} />
            </div>
          )}
        </div>
      </div>
    )
  }
)
StatCard.displayName = 'StatCard'

export { StatCard }
