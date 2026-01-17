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

// 渐变色配置
const gradientVariants = {
  primary: 'from-violet-500/10 to-purple-500/10 dark:from-violet-500/20 dark:to-purple-500/20',
  secondary: 'from-pink-500/10 to-rose-500/10 dark:from-pink-500/20 dark:to-rose-500/20',
  accent: 'from-blue-500/10 to-cyan-500/10 dark:from-blue-500/20 dark:to-cyan-500/20',
  success: 'from-green-500/10 to-emerald-500/10 dark:from-green-500/20 dark:to-emerald-500/20',
  warning: 'from-orange-500/10 to-amber-500/10 dark:from-orange-500/20 dark:to-amber-500/20',
} as const

// 强渐变配置（用于按钮等）
const strongGradientVariants = {
  primary: 'from-violet-600 to-purple-600',
  secondary: 'from-pink-500 to-rose-500',
  accent: 'from-blue-500 to-cyan-500',
  success: 'from-green-500 to-emerald-500',
  warning: 'from-orange-500 to-amber-500',
} as const

// 边框色配置
const borderVariants = {
  primary: 'border-violet-200 dark:border-violet-500/30',
  secondary: 'border-pink-200 dark:border-pink-500/30',
  accent: 'border-blue-200 dark:border-blue-500/30',
  success: 'border-green-200 dark:border-green-500/30',
  warning: 'border-orange-200 dark:border-orange-500/30',
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

