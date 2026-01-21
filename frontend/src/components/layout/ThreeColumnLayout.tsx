'use client'

import { cn } from '@/lib/utils'
import { ReactNode } from 'react'

/**
 * ThreeColumnLayout - 三栏布局组件
 * 用于 AI 助手页面的 Tiffany UI 主题
 * 布局比例: 左侧 3/12, 中间 5/12, 右侧 4/12
 */
export interface ThreeColumnLayoutProps {
  /** 左侧栏内容 - 通常用于上下文/数据源选择 */
  left: ReactNode
  /** 中间栏内容 - 通常用于对话/消息流 */
  center: ReactNode
  /** 右侧栏内容 - 通常用于洞察/可视化 */
  right: ReactNode
  /** 额外的CSS类名 */
  className?: string
  /** 左侧栏额外类名 */
  leftClassName?: string
  /** 中间栏额外类名 */
  centerClassName?: string
  /** 右侧栏额外类名 */
  rightClassName?: string
}

export function ThreeColumnLayout({
  left,
  center,
  right,
  className,
  leftClassName,
  centerClassName,
  rightClassName,
}: ThreeColumnLayoutProps) {
  return (
    <div
      className={cn(
        'grid grid-cols-1 lg:grid-cols-12 gap-0 min-h-0',
        className
      )}
    >
      {/* 左侧栏 - 25% 宽度 (3/12) */}
      <div
        className={cn(
          'lg:col-span-3 border-r border-border overflow-hidden',
          leftClassName
        )}
      >
        {left}
      </div>

      {/* 中间栏 - 42% 宽度 (5/12) */}
      <div
        className={cn(
          'lg:col-span-5 overflow-hidden',
          centerClassName
        )}
      >
        {center}
      </div>

      {/* 右侧栏 - 33% 宽度 (4/12) */}
      <div
        className={cn(
          'lg:col-span-4 border-l border-border overflow-hidden',
          rightClassName
        )}
      >
        {right}
      </div>
    </div>
  )
}

/**
 * ThreeColumnLayoutHeader - 布局头部组件
 * 可选的顶部标题栏
 */
export interface ThreeColumnLayoutHeaderProps {
  children: ReactNode
  className?: string
}

export function ThreeColumnLayoutHeader({
  children,
  className,
}: ThreeColumnLayoutHeaderProps) {
  return (
    <div
      className={cn(
        'h-16 border-b border-border px-6 flex items-center flex-shrink-0',
        className
      )}
    >
      {children}
    </div>
  )
}

/**
 * ThreeColumnLayoutPanel - 面板容器组件
 * 用于各栏内部的内容容器，提供统一的滚动和内边距
 */
export interface ThreeColumnLayoutPanelProps {
  children: ReactNode
  className?: string
  /** 是否启用滚动，默认 true */
  scrollable?: boolean
}

export function ThreeColumnLayoutPanel({
  children,
  className,
  scrollable = true,
}: ThreeColumnLayoutPanelProps) {
  return (
    <div
      className={cn(
        'min-h-0',
        scrollable && 'overflow-y-auto',
        className
      )}
    >
      {children}
    </div>
  )
}
