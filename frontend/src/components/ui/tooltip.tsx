/**
 * # [TOOLTIP] 工具提示组件
 *
 * ## [MODULE]
 * **文件名**: tooltip.tsx
 * **职责**: 提供悬停提示信息
 *
 * ## [DESCRIPTION]
 * 基于 Radix UI Tooltip 实现的工具提示组件，
 * 遵循 UX Pro Max 最佳实践。
 *
 * ## [FEATURES]
 * - 键盘可访问 (Focus + Hover)
 * - 延迟显示避免误触发
 * - 自动定位避免溢出
 * - 支持多行文本
 *
 * ## [ACCESSIBILITY]
 * - role="tooltip"
 * - 鼠标悬停和键盘焦点触发
 * - ESC 关闭
 */

import * as React from 'react'
import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import { cn } from '@/lib/utils'

const TooltipProvider = TooltipPrimitive.Provider

const Tooltip = TooltipPrimitive.Root

const TooltipTrigger = TooltipPrimitive.Trigger

const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Content
    ref={ref}
    sideOffset={sideOffset}
    className={cn(
      'z-50 overflow-hidden rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground',
      'animate-in fade-in-0 zoom-in-95',
      'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
      'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
      'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
      'max-w-xs break-words',
      className
    )}
    {...props}
  />
))
TooltipContent.displayName = TooltipPrimitive.Content.displayName

/**
 * SimpleTooltip - 简化的工具提示组件
 *
 * @example
 * ```tsx
 * <SimpleTooltip content="这是提示信息">
 *   <button>悬停查看</button>
 * </SimpleTooltip>
 * ```
 */
interface SimpleTooltipProps {
  /**
   * 提示内容
   */
  content: React.ReactNode
  /**
   * 触发元素
   */
  children: React.ReactNode
  /**
   * 延迟显示时间 (ms)
   * @default 200
   */
  delayDuration?: number
  /**
   * 跳过延迟显示
   * @default false
   */
  skipDelayDuration?: number
  /**
   * 显示位置
   */
  side?: 'top' | 'right' | 'bottom' | 'left'
  /**
   * 是否禁用
   */
  disabled?: boolean
}

export function SimpleTooltip({
  content,
  children,
  delayDuration = 200,
  skipDelayDuration = 300,
  side = 'top',
  disabled = false,
}: SimpleTooltipProps) {
  if (disabled) {
    return <>{children}</>
  }

  return (
    <TooltipProvider>
      <Tooltip delayDuration={delayDuration}>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipContent side={side}>{content}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

/**
 * IconTooltip - 图标按钮工具提示
 *
 * @example
 * ```tsx
 * <IconTooltip icon={<HelpCircle />} content="帮助信息" />
 * ```
 */
interface IconTooltipProps {
  /**
   * 图标
   */
  icon: React.ReactNode
  /**
   * 提示内容
   */
  content: React.ReactNode
  /**
   * 显示位置
   */
  side?: 'top' | 'right' | 'bottom' | 'left'
  /**
   * 图标大小
   */
  iconSize?: string
  /**
   * 自定义类名
   */
  className?: string
}

export function IconTooltip({
  icon,
  content,
  side = 'top',
  iconSize = 'h-4 w-4',
  className,
}: IconTooltipProps) {
  return (
    <TooltipProvider>
      <Tooltip delayDuration={200}>
        <TooltipTrigger asChild>
          <button
            type="button"
            className={cn(
              'inline-flex items-center justify-center',
              'text-muted-foreground hover:text-foreground',
              'transition-colors duration-200',
              'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
              'cursor-pointer',
              iconSize,
              className
            )}
            aria-label={typeof content === 'string' ? content : '查看更多信息'}
          >
            {icon}
          </button>
        </TooltipTrigger>
        <TooltipContent side={side} className="max-w-sm">
          {content}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider }
export default Tooltip
