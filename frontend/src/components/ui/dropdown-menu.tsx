/**
 * # [DROPDOWN MENU] 下拉菜单组件组
 *
 * ## [MODULE]
 * **文件名**: dropdown-menu.tsx
 * **职责**: 提供标准化的下拉菜单组件 - 基于Radix UI Dropdown Menu原语，包含14个子组件，支持嵌套子菜单、RadioGroup、CheckboxItem
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 下拉菜单组件组
 *
 * ## [INPUT]
 * Props (各子组件的Props extends Radix UI组件Props):
 * - **DropdownMenu**: Radix UI Root组件的所有Props
 * - **DropdownMenuTrigger**: children（触发按钮）
 * - **DropdownMenuContent**: className?, sideOffset?(number, 默认4)
 * - **DropdownMenuItem**: className?, inset?(boolean, 缩进)
 * - **DropdownMenuCheckboxItem**: className?, children, checked
 * - **DropdownMenuRadioItem**: className?, children
 * - **DropdownMenuLabel**: className?, inset?(boolean)
 * - **其他子组件**: DropdownMenuGroup, DropdownMenuSeparator, DropdownMenuShortcut, DropdownMenuPortal, DropdownMenuSub, DropdownMenuSubTrigger, DropdownMenuSubContent, DropdownMenuRadioGroup
 *
 * ## [OUTPUT]
 * - **DropdownMenu组件组** - 14个子组件
 *   - **DropdownMenu**: Root组件（管理菜单打开/关闭状态）
 *   - **DropdownMenuTrigger**: 触发按钮（点击打开菜单）
 *   - **DropdownMenuContent**: 菜单内容（Portal渲染，min-w-[8rem].rounded-md.border.bg-popover.p-1）
 *   - **DropdownMenuItem**: 菜单项（relative.flex.cursor-default.select-none.items-center.rounded-sm.px-2.py-1.5.text-sm）
 *   - **DropdownMenuCheckboxItem**: 复选框菜单项（pl-8.Check图标）
 *   - **DropdownMenuRadioItem**: 单选框菜单项（pl-8.Circle图标）
 *   - **DropdownMenuLabel**: 标签（px-2.py-1.5.text-sm.font-semibold）
 *   - **DropdownMenuSeparator**: 分隔线（-mx-1.my-1.h-px.bg-muted）
 *   - **DropdownMenuShortcut**: 快捷键（ml-auto.text-xs.tracking-widest.opacity-60）
 *   - **DropdownMenuSub**: 子菜单容器
 *   - **DropdownMenuSubTrigger**: 子菜单触发器（ChevronRight图标）
 *   - **DropdownMenuSubContent**: 子菜单内容（动画与Content相同）
 *   - **DropdownMenuGroup**: 分组容器
 *   - **DropdownMenuPortal**: Portal容器
 *   - **DropdownMenuRadioGroup**: Radio分组容器
 * - **Portal渲染**: DropdownMenuPrimitive.Portal渲染到body
 *   - **sideOffset**: sideOffset=4（4px偏移）
 *   - **inset缩进**: inset && 'pl-8'（嵌套菜单缩进）
 *   - **动画效果**: animate-in/out, fade-in/out, zoom-in/out, slide-in-from-*
 *   - **ItemIndicator**: 指示器容器（absolute.left-2.flex.h-3.5.w-3.5）
 *   - **图标**: Check（CheckboxItem）, Circle（RadioItem）, ChevronRight（SubTrigger）
 *   - **forwardRef**: 所有组件支持ref转发到Radix UI原语
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@radix-ui/react-dropdown-menu](https://www.radix-ui.com/primitives/docs/components/dropdown-menu) - Radix UI Dropdown Menu原语
 * - [lucide-react](https://lucide.dev/) - 图标库（Check, ChevronRight, Circle）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（DropdownMenu组件组是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要下拉菜单的组件
 * - 操作菜单、设置菜单、用户菜单、更多操作等
 *
 * ## [STATE]
 * - **DropdownMenu Root状态**: 菜单打开/关闭状态由Radix UI管理
 * - **DropdownMenuContent样式**: z-50.min-w-[8rem].overflow-hidden.rounded-md.border.bg-popover.p-1.text-popover-foreground.shadow-md
 *   - **z-50**: z-index 50（确保菜单在最上层）
 *   - **min-w-[8rem]**: 最小宽度128px
 *   - **overflow-hidden**: 隐藏溢出内容
 *   - **动画效果**: animate-in/out, fade-in/out, zoom-in/out, slide-in-from-top/left/right/bottom
 *   - **Portal渲染**: DropdownMenuPrimitive.Portal渲染到body
 * - **DropdownMenuItem样式**: relative.flex.cursor-default.select-none.items-center.rounded-sm.px-2.py-1.5.text-sm.outline-none.transition-colors
 *   - **focus:bg-accent.focus:text-accent-foreground**: focus时背景色变化
 *   - **data-[disabled]:pointer-events-none.data-[disabled]:opacity-50**: 禁用状态
 *   - **inset缩进**: inset && 'pl-8'（嵌套菜单左缩进32px）
 * - **DropdownMenuCheckboxItem样式**: relative.flex.cursor-default.select-none.items-center.rounded-sm.py-1.5.pl-8.pr-2.text-sm
 *   - **pl-8**: 左padding 32px（为Indicator留空间）
 *   - **ItemIndicator**: absolute.left-2.flex.h-3.5.w-3.5.items-center.justify-center
 *   - **Check图标**: h-4.w-4（选中时显示）
 * - **DropdownMenuRadioItem样式**: 同CheckboxItem，但使用Circle图标（h-2.w-2.fill-current）
 * - **DropdownMenuSubTrigger**: ChevronRight图标（ml-auto.h-4.w-4，右侧）
 *   - **ChevronRight**: 向右箭头（指示子菜单）
 *   - **ml-auto**: margin-left自动（推到最右侧）
 * - **DropdownMenuShortcut**: ml-auto.text-xs.tracking-widest.opacity-60
 *   - **ml-auto**: margin-left自动（推到最右侧）
 *   - **tracking-widest**: 字母间距最大化（0.1em）
 *   - **opacity-60**: 透明度60%
 * - **DropdownMenuSeparator**: -mx-1.my-1.h-px.bg-muted
 *   - **-mx-1**: 负margin-left（去除父级padding）
 *   - **h-px**: 1px高度
 *   - **bg-muted**: 次要背景色（灰色）
 * - **forwardRef**: React.forwardRef转发ref到Radix UI原语
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: DropdownMenu组件组是无状态组件（状态由Radix UI管理）
 * - **ref转发**: React.forwardRef转发ref到Radix UI原语
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有Radix UI Props
 * - **Portal渲染**: DropdownMenuPrimitive.Portal渲染到body
 * - **数据属性**: data-[state], data-[disabled]控制样式和动画
 * - **事件处理**: Radix UI处理点击、键盘导航、焦点管理等事件
 * - **动画效果**: CSS transition + Radix UI data属性触发动画
 * - **inset条件渲染**: inset && 'pl-8'（嵌套菜单缩进）
 * - **ItemIndicator条件渲染**: CheckboxItem和RadioItem的Check/Circle图标
 * - **Icon显示**: Check, Circle, ChevronRight图标（lucide-react）
 */

'use client'

import * as React from 'react'
import * as DropdownMenuPrimitive from '@radix-ui/react-dropdown-menu'
import { Check, ChevronRight, Circle } from 'lucide-react'

import { cn } from '@/lib/utils'

const DropdownMenu = DropdownMenuPrimitive.Root

const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger

const DropdownMenuGroup = DropdownMenuPrimitive.Group

const DropdownMenuPortal = DropdownMenuPrimitive.Portal

const DropdownMenuSub = DropdownMenuPrimitive.Sub

const DropdownMenuRadioGroup = DropdownMenuPrimitive.RadioGroup

const DropdownMenuSubTrigger = React.forwardRef<
  React.ElementRef<typeof DropdownMenuPrimitive.SubTrigger>,
  React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.SubTrigger> & {
    inset?: boolean
  }
>(({ className, inset, children, ...props }, ref) => (
  <DropdownMenuPrimitive.SubTrigger
    ref={ref}
    className={cn(
      'flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none focus:bg-accent data-[state=open]:bg-accent',
      inset && 'pl-8',
      className
    )}
    {...props}
  >
    {children}
    <ChevronRight className="ml-auto h-4 w-4" />
  </DropdownMenuPrimitive.SubTrigger>
))
DropdownMenuSubTrigger.displayName =
  DropdownMenuPrimitive.SubTrigger.displayName

const DropdownMenuSubContent = React.forwardRef<
  React.ElementRef<typeof DropdownMenuPrimitive.SubContent>,
  React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.SubContent>
>(({ className, ...props }, ref) => (
  <DropdownMenuPrimitive.SubContent
    ref={ref}
    className={cn(
      'z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-lg data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
      className
    )}
    {...props}
  />
))
DropdownMenuSubContent.displayName =
  DropdownMenuPrimitive.SubContent.displayName

const DropdownMenuContent = React.forwardRef<
  React.ElementRef<typeof DropdownMenuPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <DropdownMenuPrimitive.Portal>
    <DropdownMenuPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        'z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
        className
      )}
      {...props}
    />
  </DropdownMenuPrimitive.Portal>
))
DropdownMenuContent.displayName = DropdownMenuPrimitive.Content.displayName

const DropdownMenuItem = React.forwardRef<
  React.ElementRef<typeof DropdownMenuPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Item> & {
    inset?: boolean
  }
>(({ className, inset, ...props }, ref) => (
  <DropdownMenuPrimitive.Item
    ref={ref}
    className={cn(
      'relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
      inset && 'pl-8',
      className
    )}
    {...props}
  />
))
DropdownMenuItem.displayName = DropdownMenuPrimitive.Item.displayName

const DropdownMenuCheckboxItem = React.forwardRef<
  React.ElementRef<typeof DropdownMenuPrimitive.CheckboxItem>,
  React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.CheckboxItem>
>(({ className, children, checked, ...props }, ref) => (
  <DropdownMenuPrimitive.CheckboxItem
    ref={ref}
    className={cn(
      'relative flex cursor-default select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none transition-colors focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
      className
    )}
    checked={checked}
    {...props}
  >
    <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
      <DropdownMenuPrimitive.ItemIndicator>
        <Check className="h-4 w-4" />
      </DropdownMenuPrimitive.ItemIndicator>
    </span>
    {children}
  </DropdownMenuPrimitive.CheckboxItem>
))
DropdownMenuCheckboxItem.displayName =
  DropdownMenuPrimitive.CheckboxItem.displayName

const DropdownMenuRadioItem = React.forwardRef<
  React.ElementRef<typeof DropdownMenuPrimitive.RadioItem>,
  React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.RadioItem>
>(({ className, children, ...props }, ref) => (
  <DropdownMenuPrimitive.RadioItem
    ref={ref}
    className={cn(
      'relative flex cursor-default select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none transition-colors focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
      className
    )}
    {...props}
  >
    <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
      <DropdownMenuPrimitive.ItemIndicator>
        <Circle className="h-2 w-2 fill-current" />
      </DropdownMenuPrimitive.ItemIndicator>
    </span>
    {children}
  </DropdownMenuPrimitive.RadioItem>
))
DropdownMenuRadioItem.displayName = DropdownMenuPrimitive.RadioItem.displayName

const DropdownMenuLabel = React.forwardRef<
  React.ElementRef<typeof DropdownMenuPrimitive.Label>,
  React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Label> & {
    inset?: boolean
  }
>(({ className, inset, ...props }, ref) => (
  <DropdownMenuPrimitive.Label
    ref={ref}
    className={cn(
      'px-2 py-1.5 text-sm font-semibold',
      inset && 'pl-8',
      className
    )}
    {...props}
  />
))
DropdownMenuLabel.displayName = DropdownMenuPrimitive.Label.displayName

const DropdownMenuSeparator = React.forwardRef<
  React.ElementRef<typeof DropdownMenuPrimitive.Separator>,
  React.ComponentPropsWithoutRef<typeof DropdownMenuPrimitive.Separator>
>(({ className, ...props }, ref) => (
  <DropdownMenuPrimitive.Separator
    ref={ref}
    className={cn('-mx-1 my-1 h-px bg-muted', className)}
    {...props}
  />
))
DropdownMenuSeparator.displayName = DropdownMenuPrimitive.Separator.displayName

const DropdownMenuShortcut = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement>) => {
  return (
    <span
      className={cn('ml-auto text-xs tracking-widest opacity-60', className)}
      {...props}
    />
  )
}
DropdownMenuShortcut.displayName = 'DropdownMenuShortcut'

export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuCheckboxItem,
  DropdownMenuRadioItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuGroup,
  DropdownMenuPortal,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuRadioGroup,
}
