/**
 * # [DONUT_CHART] DataLab 圆环图组件
 *
 * ## [MODULE]
 * **文件名**: DonutChart.tsx
 * **职责**: 提供 SVG 圆环图，中心显示百分比，支持 Tiffany 主题渐变
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 */

'use client'

import { cn } from '@/lib/utils'
import * as React from 'react'

export interface DonutChartProps extends React.HTMLAttributes<HTMLDivElement> {
  /** 百分比值 (0-100) */
  percentage: number
  /** 圆环大小 */
  size?: 'sm' | 'md' | 'lg'
  /** 圆环粗细 */
  strokeWidth?: number
  /** 颜色主题 */
  variant?: 'tiffany' | 'success' | 'warning' | 'danger' | 'primary'
  /** 中心显示的标签 */
  label?: string
  /** 是否显示动画 */
  animated?: boolean
}

// 尺寸配置
const sizeConfig = {
  sm: { width: 80, fontSize: 'text-lg', labelSize: 'text-[10px]' },
  md: { width: 120, fontSize: 'text-2xl', labelSize: 'text-xs' },
  lg: { width: 160, fontSize: 'text-3xl', labelSize: 'text-sm' },
}

// 颜色配置 - DataLab Tiffany 主题
const colorConfig = {
  tiffany: {
    gradient: ['#5eead4', '#14b8a6', '#0d9488'], // tiffany 色系
    track: 'stroke-slate-200 dark:stroke-slate-700',
  },
  success: {
    gradient: ['#4ade80', '#22c55e', '#16a34a'],
    track: 'stroke-slate-200 dark:stroke-slate-700',
  },
  warning: {
    gradient: ['#fbbf24', '#f59e0b', '#d97706'],
    track: 'stroke-slate-200 dark:stroke-slate-700',
  },
  danger: {
    gradient: ['#f87171', '#ef4444', '#dc2626'],
    track: 'stroke-slate-200 dark:stroke-slate-700',
  },
  primary: {
    gradient: ['#818cf8', '#6366f1', '#4f46e5'],
    track: 'stroke-slate-200 dark:stroke-slate-700',
  },
}

const DonutChart = React.forwardRef<HTMLDivElement, DonutChartProps>(
  ({
    className,
    percentage,
    size = 'md',
    strokeWidth = 10,
    variant = 'tiffany',
    label,
    animated = true,
    ...props
  }, ref) => {
    const { width, fontSize, labelSize } = sizeConfig[size]
    const colors = colorConfig[variant]
    const gradientId = React.useId()
    
    // 计算 SVG 参数
    const radius = (width - strokeWidth) / 2
    const circumference = 2 * Math.PI * radius
    const strokeDashoffset = circumference - (percentage / 100) * circumference
    const center = width / 2

    return (
      <div
        ref={ref}
        className={cn('relative inline-flex items-center justify-center', className)}
        {...props}
      >
        <svg
          width={width}
          height={width}
          viewBox={`0 0 ${width} ${width}`}
          className="transform -rotate-90"
        >
          {/* 渐变定义 */}
          <defs>
            <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={colors.gradient[0]} />
              <stop offset="50%" stopColor={colors.gradient[1]} />
              <stop offset="100%" stopColor={colors.gradient[2]} />
            </linearGradient>
          </defs>
          
          {/* 背景圆环 */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            className={colors.track}
          />
          
          {/* 进度圆环 */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            stroke={`url(#${gradientId})`}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className={cn(
              animated && 'transition-all duration-1000 ease-out'
            )}
          />
        </svg>
        
        {/* 中心文字 */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn(
            'font-bold text-slate-800 dark:text-slate-100',
            fontSize
          )}>
            {Math.round(percentage)}%
          </span>
          {label && (
            <span className={cn(
              'text-slate-500 dark:text-slate-400 mt-0.5',
              labelSize
            )}>
              {label}
            </span>
          )}
        </div>
      </div>
    )
  }
)
DonutChart.displayName = 'DonutChart'

export { DonutChart }
