/**
 * # [SELECT] 下拉选择组件（Radix UI）
 *
 * ## [MODULE]
 * **文件名**: select.tsx
 * **职责**: 提供标准化的下拉选择组件 - 基于Radix UI Select原语，包含10个子组件，支持动画、键盘导航、Portal渲染
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 下拉选择组件
 *
 * ## [INPUT]
 * Props (各子组件的Props extends Radix UI组件Props):
 * - **Select**: Radix UI Root组件的所有Props（value, onValueChange, disabled等）
 * - **SelectTrigger**: className?, children（SelectValue + ChevronDown图标）
 * - **SelectContent**: className?, children, position?('popper')
 * - **SelectItem**: className?, children（选项文本）
 * - **其他子组件**: SelectGroup, SelectValue, SelectLabel, SelectSeparator, SelectScrollUpButton, SelectScrollDownButton
 *
 * ## [OUTPUT]
 * - **Select组件组** - 10个子组件
 *   - **Select**: Root组件（管理value和onValueChange状态）
 *   - **SelectTrigger**: 触发按钮（显示SelectValue + ChevronDown图标，h-9, rounded-md, border）
 *   - **SelectContent**: 下拉内容（Portal渲染，max-h-96, 圆角, 阴影, 动画效果）
 *   - **SelectItem**: 选项（Check图标 + ItemText, pr-8, focus:bg-accent）
 *   - **SelectLabel**: 标签（px-2.py-1.5, font-semibold）
 *   - **SelectValue**: 显示选中值的占位组件
 *   - **SelectGroup**: 分组容器
 *   - **SelectSeparator**: 分隔线（-mx-1, h-px, bg-muted）
 *   - **SelectScrollUpButton/DownButton**: 滚动按钮（ChevronUp/Down图标）
 * - **动画效果**: animate-in/out, fade-in/out, zoom-in/out, slide-in-from-*
 *   - **position模式**: 'popper'（使用Radix UI Popper定位）
 * - **forwardRef**: 所有组件支持ref转发到Radix UI原语
 *   - **Portal**: SelectContent使用Portal渲染（脱离DOM层级）
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@radix-ui/react-select](https://www.radix-ui.com/primitives/docs/components/select) - Radix UI Select原语
 * - [lucide-react](https://lucide.dev/) - 图标库（Check, ChevronDown, ChevronUp）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Select组件组是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要下拉选择的组件
 * - 表单组件、筛选器、设置页面等
 *
 * ## [STATE]
 * - **Select Root状态**: value和onValueChange由Radix UI管理
 * - **SelectTrigger**: h-9.w-full.rounded-md.border.border-input.bg-background.px-3.py-2
 * - **SelectContent动画**:
 *   - animate-in/out: 打开/关闭动画
 *   - fade-in/out: 淡入淡出（0ms）
 *   - zoom-in/out: 缩放（95% → 100%）
 *   - slide-in-from-top/left/right/bottom: 从四个方向滑入（2px）
 *   - max-h-96: 最大高度384px（超出滚动）
 * - **SelectItem**: relative.flex.w-full.cursor-default.select-none.items-center.rounded-sm.py-1.5.pl-2.pr-8
 *   - Check图标: absolute.right-2.flex.h-3.5.w-3.5
 *   - focus:bg-accent.focus:text-accent-foreground
 *   - data-[disabled]:pointer-events-none.data-[disabled]:opacity-50
 * - **SelectSeparator**: -mx-1.my-1.h-px.bg-muted
 * - **ScrollButtons**: flex.cursor-default.items-center.justify-center.py-1
 * - **Portal渲染**: SelectContent使用Portal渲染到body
 * - **position模式**: 'popper'时添加translate-y-1和translate-x-1偏移
 * - **数据属性**: data-[state], data-[side], data-[disabled]控制样式和动画
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Select组件组是无状态组件（状态由Radix UI管理）
 * - **ref转发**: React.forwardRef转发ref到Radix UI原语
 * - **Portal渲染**: SelectPrimitive.Portal渲染到body
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有Radix UI Props
 * - **数据属性**: data-[state], data-[side], data-[disabled]控制样式
 * - **事件处理**: Radix UI处理键盘导航、点击、focus等事件
 * - **动画效果**: CSS transition + Radix UI data属性触发动画
 */

'use client'

import * as React from 'react'
import * as SelectPrimitive from '@radix-ui/react-select'
import { Check, ChevronDown, ChevronUp } from 'lucide-react'

import { cn } from '@/lib/utils'

const Select = SelectPrimitive.Root

const SelectGroup = SelectPrimitive.Group

const SelectValue = SelectPrimitive.Value

const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger
    ref={ref}
    className={cn(
      'flex h-9 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1',
      className
    )}
    {...props}
  >
    {children}
    <SelectPrimitive.Icon asChild>
      <ChevronDown className="h-4 w-4 opacity-50" />
    </SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
))
SelectTrigger.displayName = SelectPrimitive.Trigger.displayName

const SelectScrollUpButton = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.ScrollUpButton>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.ScrollUpButton>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.ScrollUpButton
    ref={ref}
    className={cn(
      'flex cursor-default items-center justify-center py-1',
      className
    )}
    {...props}
  >
    <ChevronUp className="h-4 w-4" />
  </SelectPrimitive.ScrollUpButton>
))
SelectScrollUpButton.displayName = SelectPrimitive.ScrollUpButton.displayName

const SelectScrollDownButton = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.ScrollDownButton>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.ScrollDownButton>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.ScrollDownButton
    ref={ref}
    className={cn(
      'flex cursor-default items-center justify-center py-1',
      className
    )}
    {...props}
  >
    <ChevronDown className="h-4 w-4" />
  </SelectPrimitive.ScrollDownButton>
))
SelectScrollDownButton.displayName =
  SelectPrimitive.ScrollDownButton.displayName

const SelectContent = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(({ className, children, position = 'popper', ...props }, ref) => (
  <SelectPrimitive.Portal>
    <SelectPrimitive.Content
      ref={ref}
      className={cn(
        'relative z-50 max-h-96 min-w-[8rem] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
        position === 'popper' &&
          'data-[side=bottom]:translate-y-1 data-[side=left]:translate-x-1 data-[side=right]:translate-x-1 data-[side=top]:translate-y-1',
        className
      )}
      position={position}
      {...props}
    >
      <SelectScrollUpButton />
      <SelectPrimitive.Viewport
        className={cn(
          'p-1',
          position === 'popper' &&
            'h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)]'
        )}
      >
        {children}
      </SelectPrimitive.Viewport>
      <SelectScrollDownButton />
    </SelectPrimitive.Content>
  </SelectPrimitive.Portal>
))
SelectContent.displayName = SelectPrimitive.Content.displayName

const SelectLabel = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Label>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Label>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.Label
    ref={ref}
    className={cn('px-2 py-1.5 text-sm font-semibold', className)}
    {...props}
  />
))
SelectLabel.displayName = SelectPrimitive.Label.displayName

const SelectItem = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={cn(
      'relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-2 pr-8 text-sm outline-none focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
      className
    )}
    {...props}
  >
    <span className="absolute right-2 flex h-3.5 w-3.5 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <Check className="h-4 w-4" />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
))
SelectItem.displayName = SelectPrimitive.Item.displayName

const SelectSeparator = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Separator>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Separator>
>(({ className, ...props }, ref) => (
  <SelectPrimitive.Separator
    ref={ref}
    className={cn('-mx-1 my-1 h-px bg-muted', className)}
    {...props}
  />
))
SelectSeparator.displayName = SelectPrimitive.Separator.displayName

export {
  Select,
  SelectGroup,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectLabel,
  SelectItem,
  SelectSeparator,
  SelectScrollUpButton,
  SelectScrollDownButton,
}
