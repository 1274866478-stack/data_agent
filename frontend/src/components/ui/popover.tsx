/**
 * # [POPOVER] 弹出框组件组
 *
 * ## [MODULE]
 * **文件名**: popover.tsx
 * **职责**: 提供标准化的弹出框组件 - 基于Radix UI Popover原语，包含3个子组件，支持Portal渲染和动画
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 弹出框组件组
 *
 * ## [INPUT]
 * Props (各子组件的Props extends Radix UI组件Props):
 * - **Popover**: Radix UI Root组件的所有Props（open, onOpenChange, defaultOpen等）
 * - **PopoverTrigger**: className?, children（触发按钮）
 * - **PopoverContent**: className?, align?('start' | 'center' | 'end'), sideOffset?(number)
 *
 * ## [OUTPUT]
 * - **Popover组件组** - 3个子组件
 *   - **Popover**: Root组件（管理open和onOpenChange状态）
 *   - **PopoverTrigger**: 触发按钮（点击打开/关闭弹出框）
 *   - **PopoverContent**: 弹出内容（Portal渲染，w-72.rounded-md.border.bg-popover.p-4）
 * - **Portal渲染**: PopoverPrimitive.Portal渲染到body
 *   - **align对齐**: align='center'（默认居中对齐，可选'start'或'end'）
 *   - **sideOffset**: sideOffset=4（4px偏移，避免与触发器重叠）
 *   - **动画效果**: animate-in/out, fade-in/out, zoom-in/out, slide-in-from-*
 *   - **z-index**: z-50（确保弹出框在最上层）
 *   - **最小宽度**: min-w-[8rem]（128px最小宽度）
 *   - **固定宽度**: w-72（288px固定宽度）
 *   - **forwardRef**: 所有组件支持ref转发到Radix UI原语
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@radix-ui/react-popover](https://www.radix-ui.com/primitives/docs/components/popover) - Radix UI Popover原语
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Popover组件组是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要弹出框的组件
 * - 信息提示、操作菜单、帮助文档、确认对话框等
 *
 * ## [STATE]
 * - **Popover Root状态**: open和onOpenChange由Radix UI管理
 *   - **open**: boolean（弹出框打开/关闭状态）
 *   - **onOpenChange**: (open: boolean) => void（状态变化回调）
 *   - **defaultOpen**: 初始打开状态（非受控模式）
 * - **PopoverContent样式**: z-50.w-72.rounded-md.border.bg-popover.p-4.text-popover-foreground.shadow-md.outline-none
 *   - **z-50**: z-index 50（确保弹出框在最上层）
 *   - **w-72**: 288px固定宽度
 *   - **rounded-md**: 中等圆角（6px）
 *   - **border**: 1px边框
 *   - **bg-popover**: 弹出框背景色（白色）
 *   - **p-4**: 16px padding
 *   - **text-popover-foreground**: 弹出框前景色（黑色）
 *   - **shadow-md**: 中等阴影
 *   - **outline-none**: 去除outline
 *   - **align对齐**: align='center'（默认居中对齐，可选'start'或'end'）
 *   - **sideOffset**: sideOffset=4（4px偏移，避免与触发器重叠）
 * - **动画效果**:
 *     - animate-in/out: 打开/关闭动画
 *     - fade-in/out: 淡入淡出（0ms）
 *     - zoom-in/out: 缩放（95% → 100%）
 *     - slide-in-from-top/left/right/bottom: 从四个方向滑入（2px）
 *   - **Portal渲染**: PopoverPrimitive.Portal渲染到body（脱离DOM层级）
 *   - **数据属性**: data-[state], data-[side]控制样式和动画
 *   - **forwardRef**: React.forwardRef转发ref到Radix UI原语
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Popover组件组是无状态组件（状态由Radix UI管理）
 * - **ref转发**: React.forwardRef转发ref到Radix UI原语
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有Radix UI Props（align, sideOffset等）
 * - **Portal渲染**: PopoverPrimitive.Portal渲染到body
 *   - **脱离DOM层级**: 弹出框渲染到body，避免父组件的overflow:hidden或z-index问题
 * - **数据属性**: data-[state=open/closed]由Radix UI自动添加（基于open prop）
 * - **事件处理**: Radix UI处理点击外部关闭、Escape键关闭等事件
 * - **动画效果**: CSS transition + Radix UI data属性触发动画
 * - **align和sideOffset**: 控制弹出框相对于触发器的位置和偏移
 */

'use client'

import * as React from 'react'
import * as PopoverPrimitive from '@radix-ui/react-popover'

import { cn } from '@/lib/utils'

const Popover = PopoverPrimitive.Root

const PopoverTrigger = PopoverPrimitive.Trigger

const PopoverContent = React.forwardRef<
  React.ElementRef<typeof PopoverPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof PopoverPrimitive.Content>
>(({ className, align = 'center', sideOffset = 4, ...props }, ref) => (
  <PopoverPrimitive.Portal>
    <PopoverPrimitive.Content
      ref={ref}
      align={align}
      sideOffset={sideOffset}
      className={cn(
        'z-50 w-72 rounded-md border bg-popover p-4 text-popover-foreground shadow-md outline-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
        className
      )}
      {...props}
    />
  </PopoverPrimitive.Portal>
))
PopoverContent.displayName = PopoverPrimitive.Content.displayName

export { Popover, PopoverTrigger, PopoverContent }
