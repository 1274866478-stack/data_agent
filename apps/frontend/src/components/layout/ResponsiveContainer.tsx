/**
 * # [RESPONSIVE_CONTAINER] 响应式容器组件
 *
 * ## [MODULE]
 * **文件名**: ResponsiveContainer.tsx
 * **职责**: 提供响应式布局容器，遵循 UX Pro Max 断点规范
 *
 * ## [DESCRIPTION]
 * 根据不同屏幕尺寸提供优化的布局：
 * - 375px: 移动端（最小宽度）
 * - 768px: 平板
 * - 1024px: 桌面
 * - 1440px: 大屏
 *
 * ## [FEATURES]
 * - 自动内边距调整
 * - 最大宽度限制
 * - 居中对齐
 * - 安全区域支持
 */

import * as React from 'react'
import { cn } from '@/lib/utils'

export interface ResponsiveContainerProps {
  /**
   * 容器最大宽度
   * @default '1280px'
   */
  maxWidth?: '640px' | '768px' | '1024px' | '1280px' | '1536px' | 'full'
  /**
   * 是否移除水平内边距
   * @default false
   */
  noPadding?: boolean
  /**
   * 自定义类名
   */
  className?: string
  /**
   * 子元素
   */
  children: React.ReactNode
}

const maxWidthClasses = {
  '640px': 'max-w-sm',
  '768px': 'max-w-md',
  '1024px': 'max-w-lg',
  '1280px': 'max-w-screen-xl',
  '1536px': 'max-w-screen-2xl',
  'full': 'max-w-full',
}

/**
 * ResponsiveContainer - 响应式容器组件
 *
 * @example
 * ```tsx
 * <ResponsiveContainer>
 *   <h1>标题</h1>
 *   <p>内容</p>
 * </ResponsiveContainer>
 *
 * <ResponsiveContainer maxWidth="1024px">
 *   <article>文章内容</article>
 * </ResponsiveContainer>
 * ```
 */
export function ResponsiveContainer({
  maxWidth = '1280px',
  noPadding = false,
  className,
  children,
}: ResponsiveContainerProps) {
  return (
    <div
      className={cn(
        'mx-auto',
        maxWidthClasses[maxWidth],
        !noPadding && 'px-4 sm:px-6 lg:px-8',
        className
      )}
    >
      {children}
    </div>
  )
}

/**
 * ResponsiveGrid - 响应式网格组件
 */
export interface ResponsiveGridProps {
  /**
   * 列数配置
   */
  cols?: {
    mobile?: 1 | 2
    tablet?: 1 | 2 | 3
    desktop?: 1 | 2 | 3 | 4
    wide?: 1 | 2 | 3 | 4 | 5 | 6
  }
  /**
   * 间距
   * @default '1.5rem'
   */
  gap?: string
  /**
   * 自定义类名
   */
  className?: string
  /**
   * 子元素
   */
  children: React.ReactNode
}

export function ResponsiveGrid({
  cols = { mobile: 1, tablet: 2, desktop: 3, wide: 4 },
  gap = '1.5rem',
  className,
  children,
}: ResponsiveGridProps) {
  const gridColsClass = [
    cols.mobile && `grid-cols-${cols.mobile}`,
    cols.tablet && `sm:grid-cols-${cols.tablet}`,
    cols.desktop && `lg:grid-cols-${cols.desktop}`,
    cols.wide && `xl:grid-cols-${cols.wide}`,
  ].filter(Boolean).join(' ')

  return (
    <div
      className={cn(
        'grid',
        gridColsClass || 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4',
        className
      )}
      style={{ gap }}
    >
      {children}
    </div>
  )
}

/**
 * ResponsiveFlex - 响应式弹性布局
 */
export interface ResponsiveFlexProps {
  /**
   * 方向
   */
  direction?: {
    mobile?: 'row' | 'column'
    tablet?: 'row' | 'column'
    desktop?: 'row' | 'column'
  }
  /**
   * 对齐方式
   */
  align?: 'start' | 'center' | 'end' | 'stretch'
  /**
   * 交叉轴对齐
   */
  justify?: 'start' | 'center' | 'end' | 'between' | 'around'
  /**
   * 间距
   */
  gap?: string
  /**
   * 自定义类名
   */
  className?: string
  /**
   * 子元素
   */
  children: React.ReactNode
}

export function ResponsiveFlex({
  direction = { mobile: 'column', tablet: 'row', desktop: 'row' },
  align = 'start',
  justify = 'start',
  gap = '1rem',
  className,
  children,
}: ResponsiveFlexProps) {
  const alignClass = {
    start: 'items-start',
    center: 'items-center',
    end: 'items-end',
    stretch: 'items-stretch',
  }[align]

  const justifyClass = {
    start: 'justify-start',
    center: 'justify-center',
    end: 'justify-end',
    between: 'justify-between',
    around: 'justify-around',
  }[justify]

  const directionClasses = [
    direction.mobile === 'row' ? 'flex-row' : 'flex-col',
    direction.tablet === 'row' ? 'sm:flex-row' : 'sm:flex-col',
    direction.desktop === 'row' ? 'lg:flex-row' : 'lg:flex-col',
  ].join(' ')

  return (
    <div
      className={cn(
        'flex',
        directionClasses,
        alignClass,
        justifyClass,
        className
      )}
      style={{ gap }}
    >
      {children}
    </div>
  )
}

/**
 * ShowAt - 仅在指定断点显示
 */
export interface ShowAtProps {
  /**
   * 显示断点
   */
  breakpoint: 'mobile' | 'tablet' | 'desktop' | 'wide'
  /**
   * 子元素
   */
  children: React.ReactNode
}

export function ShowAt({ breakpoint, children }: ShowAtProps) {
  const breakpointClasses = {
    mobile: 'block sm:hidden',
    tablet: 'hidden sm:block lg:hidden',
    desktop: 'hidden lg:block xl:hidden',
    wide: 'hidden xl:block',
  }

  return <div className={breakpointClasses[breakpoint]}>{children}</div>
}

/**
 * HideAt - 在指定断点隐藏
 */
export interface HideAtProps {
  /**
   * 隐藏断点
   */
  breakpoint: 'mobile' | 'tablet' | 'desktop' | 'wide'
  /**
   * 子元素
   */
  children: React.ReactNode
}

export function HideAt({ breakpoint, children }: HideAtProps) {
  const breakpointClasses = {
    mobile: 'hidden sm:block',
    tablet: 'block sm:hidden lg:block',
    desktop: 'block lg:hidden xl:block',
    wide: 'block xl:hidden',
  }

  return <div className={breakpointClasses[breakpoint]}>{children}</div>
}

export default ResponsiveContainer
