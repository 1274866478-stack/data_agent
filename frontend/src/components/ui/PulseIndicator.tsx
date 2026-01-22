'use client'

import { cn } from '@/lib/utils'
import * as React from 'react'

/**
 * 脉冲指示器组件 - DataLab 风格的状态指示器
 * 
 * 用于显示处理中、成功、警告、错误等状态的脉冲动画指示器
 */
export interface PulseIndicatorProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 指示器变体 */
  variant?: 'success' | 'processing' | 'warning' | 'danger'
  /** 指示器尺寸 */
  size?: 'sm' | 'md' | 'lg'
  /** 是否显示脉冲动画 */
  showPing?: boolean
}

const colorConfig = {
  success: 'bg-green-500',
  processing: 'bg-primary-400',
  warning: 'bg-amber-500',
  danger: 'bg-red-500',
}

const pingColorConfig = {
  success: 'bg-green-400',
  processing: 'bg-primary-300',
  warning: 'bg-amber-400',
  danger: 'bg-red-400',
}

const sizeConfig = {
  sm: { dot: 'w-2 h-2', ping: 'w-2 h-2' },
  md: { dot: 'w-3 h-3', ping: 'w-3 h-3' },
  lg: { dot: 'w-4 h-4', ping: 'w-4 h-4' },
}

const PulseIndicator = React.forwardRef<HTMLDivElement, PulseIndicatorProps>(
  ({ className, variant = 'processing', size = 'md', showPing = true, ...props }, ref) => {
    const { dot, ping } = sizeConfig[size]
    const color = colorConfig[variant]
    const pingColor = pingColorConfig[variant]

    return (
      <div ref={ref} className={cn('relative inline-flex', className)} {...props}>
        {showPing && (
          <span className={cn(
            'absolute inline-flex rounded-full opacity-75 animate-ping-slow',
            ping,
            pingColor
          )} />
        )}
        <span className={cn(
          'relative inline-flex rounded-full animate-subtle-pulse',
          dot,
          color
        )} />
      </div>
    )
  }
)
PulseIndicator.displayName = 'PulseIndicator'

export { PulseIndicator }
