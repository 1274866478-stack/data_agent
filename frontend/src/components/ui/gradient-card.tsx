/**
 * # [GRADIENT_CARD] 渐变卡片组件
 *
 * ## [MODULE]
 * **文件名**: gradient-card.tsx
 * **职责**: 提供带渐变背景的卡片组件，支持多种渐变色和强度
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 */

import { cn } from '@/lib/utils'
import * as React from 'react'

// 渐变色配置 - 蒂芙尼蓝主题
const gradientVariants = {
  primary: 'from-tiffany-400/20 to-cyan-500/20 dark:from-tiffany-500/30 dark:to-cyan-600/30',
  secondary: 'from-tiffany-100 to-cyan-100 dark:from-tiffany-950/20 dark:to-cyan-950/20',
  accent: 'from-cyan-500/20 to-teal-500/20 dark:from-cyan-600/30 dark:to-teal-600/30',
  success: 'from-emerald-400/20 to-teal-500/20 dark:from-emerald-500/30 dark:to-teal-600/30',
  warning: 'from-amber-400/20 to-orange-500/20 dark:from-amber-500/30 dark:to-orange-600/30',
} as const

// 强渐变配置（用于按钮等） - 蒂芙尼蓝主题
const strongGradientVariants = {
  primary: 'from-tiffany-500 to-cyan-600',
  secondary: 'from-tiffany-300 to-cyan-400',
  accent: 'from-cyan-500 to-teal-600',
  success: 'from-emerald-500 to-teal-600',
  warning: 'from-amber-500 to-orange-600',
} as const

// 边框色配置 - 蒂芙尼蓝主题
const borderVariants = {
  primary: 'border-tiffany-200 dark:border-tiffany-500/30',
  secondary: 'border-cyan-200 dark:border-cyan-500/30',
  accent: 'border-cyan-300 dark:border-cyan-600/30',
  success: 'border-emerald-200 dark:border-emerald-500/30',
  warning: 'border-amber-200 dark:border-amber-500/30',
} as const

export interface GradientCardProps extends React.HTMLAttributes<HTMLDivElement> {
  gradient?: keyof typeof gradientVariants
  intensity?: 'subtle' | 'medium' | 'strong'
  hoverEffect?: boolean
}

const GradientCard = React.forwardRef<HTMLDivElement, GradientCardProps>(
  ({ className, gradient = 'primary', intensity = 'subtle', hoverEffect = true, children, ...props }, ref) => {
    const baseClasses = 'rounded-xl border bg-gradient-to-br transition-all duration-200'
    const gradientClass = intensity === 'strong' 
      ? strongGradientVariants[gradient] 
      : gradientVariants[gradient]
    const borderClass = borderVariants[gradient]
    const hoverClasses = hoverEffect ? 'hover:shadow-lg hover:-translate-y-0.5' : ''

    return (
      <div
        ref={ref}
        className={cn(
          baseClasses,
          gradientClass,
          borderClass,
          hoverClasses,
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)
GradientCard.displayName = 'GradientCard'

// 渐变卡片头部
const GradientCardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex flex-col space-y-1.5 p-6', className)}
    {...props}
  />
))
GradientCardHeader.displayName = 'GradientCardHeader'

// 渐变卡片标题
const GradientCardTitle = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('font-semibold leading-none tracking-tight', className)}
    {...props}
  />
))
GradientCardTitle.displayName = 'GradientCardTitle'

// 渐变卡片描述
const GradientCardDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('text-sm text-muted-foreground', className)}
    {...props}
  />
))
GradientCardDescription.displayName = 'GradientCardDescription'

// 渐变卡片内容
const GradientCardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
))
GradientCardContent.displayName = 'GradientCardContent'

// 渐变卡片底部
const GradientCardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex items-center p-6 pt-0', className)}
    {...props}
  />
))
GradientCardFooter.displayName = 'GradientCardFooter'

export {
    GradientCard, GradientCardContent, GradientCardDescription, GradientCardFooter, GradientCardHeader,
    GradientCardTitle, gradientVariants,
    strongGradientVariants
}

