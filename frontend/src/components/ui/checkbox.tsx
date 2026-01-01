/**
 * # [CHECKBOX] 复选框组件
 *
 * ## [MODULE]
 * **文件名**: checkbox.tsx
 * **职责**: 提供标准化的复选框组件 - 基于Radix UI Checkbox原语，支持checked/unchecked/indeterminate状态
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 复选框组件
 *
 * ## [INPUT]
 * Props (extends React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>):
 * - **className?: string** - 自定义类名
 * - **checked?: boolean | 'indeterminate'** - 复选框状态（true=选中, false=未选中, 'indeterminate'=半选）
 * - **onCheckedChange?: (checked: boolean | 'indeterminate') => void** - 状态变化回调
 * - **disabled?: boolean** - 禁用状态
 * - **required?: boolean** - 必填状态
 * - **name?: string** - 表单字段名
 * - **value?: string** - 表单字段值
 *
 * ## [OUTPUT]
 * - **Checkbox组件** - 渲染复选框元素
 *   - **基础样式**: peer.h-4.w-4.shrink-0.rounded-sm.border.border-primary.ring-offset-background
 *   - **尺寸**: h-4.w-4（16px × 16px）
 *   - **形状**: rounded-sm（小圆角，4px）
 *   - **边框**: border.border-primary（主题色边框）
 *   - **focus状态**: focus-visible:outline-none.focus-visible:ring-2.focus-visible:ring-ring.focus-visible:ring-offset-2
 *   - **禁用状态**: disabled:cursor-not-allowed.disabled:opacity-50
 *   - **checked样式**: data-[state=checked]:bg-primary.data-[state=checked]:text-primary-foreground
 *   - **Check图标**: CheckboxPrimitive.Indicator包裹Check图标（h-4.w-4）
 *   - **forwardRef**: 支持ref转发到CheckboxPrimitive.Root
 *   - **displayName**: 设置为CheckboxPrimitive.Root.displayName
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@radix-ui/react-checkbox](https://www.radix-ui.com/primitives/docs/components/checkbox) - Radix UI Checkbox原语
 * - [lucide-react](https://lucide.dev/) - 图标库（Check）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Checkbox是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要复选框的组件
 * - 表单组件、设置页面、批量操作、多选列表等
 *
 * ## [STATE]
 * - **无状态**: Checkbox是无状态组件（checked状态由父组件控制）
 * - **checked状态**: checked?: boolean | 'indeterminate'（受控组件，由父组件管理）
 * - **尺寸**: h-4.w-4（16px × 16px固定尺寸）
 * - **形状**: rounded-sm（小圆角，border-radius 4px）
 * - **边框**: border.border-primary（1px主题色边框）
 * - **shrink-0**: 防止flex容器中收缩
 * - **peer类**: 用于peer-disabled样式（与Label配合）
 * - **ring-offset**: ring-offset-background（focus时的偏移效果）
 * - **focus样式**: focus-visible:outline-none.focus-visible:ring-2.focus-visible:ring-ring.focus-visible:ring-offset-2
 * - **禁用样式**: disabled:cursor-not-allowed.disabled:opacity-50
 * - **checked样式**: data-[state=checked]:bg-primary.data-[state=checked]:text-primary-foreground
 *   - **data-[state=checked]**: Radix UI自动添加的数据属性（当checked=true或'indeterminate'时）
 *   - **bg-primary**: 选中时背景色变为主题色
 *   - **text-primary-foreground**: 选中时文字色变为主题前景色（Check图标颜色）
 * - **CheckboxPrimitive.Indicator**: 仅在checked=true或'indeterminate'时渲染
 * - **Check图标**: h-4.w-4（16px × 16px，与Checkbox尺寸一致）
 * - **forwardRef**: React.forwardRef转发ref到CheckboxPrimitive.Root
 * - **displayName设置**: Checkbox.displayName = CheckboxPrimitive.Root.displayName
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Checkbox是纯展示组件（状态由父组件控制）
 * - **ref转发**: React.forwardRef转发ref到CheckboxPrimitive.Root
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有CheckboxPrimitive.Root的Props（checked, onCheckedChange, disabled等）
 * - **数据属性**: data-[state=checked]由Radix UI自动添加（基于checked prop）
 * - **Indicator条件渲染**: CheckboxPrimitive.Indicator仅在checked=true或'indeterminate'时渲染
 * - **Check图标显示**: Indicator内部渲染Check图标（h-4.w-4）
 * - **peer类**: peer类用于配合peer-disabled样式（与Label组件配合使用）
 * - **事件处理**: Radix UI处理点击、键盘导航（Space切换状态）等事件
 */

'use client'

import * as React from 'react'
import * as CheckboxPrimitive from '@radix-ui/react-checkbox'
import { Check } from 'lucide-react'

import { cn } from '@/lib/utils'

const Checkbox = React.forwardRef<
  React.ElementRef<typeof CheckboxPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>
>(({ className, ...props }, ref) => (
  <CheckboxPrimitive.Root
    ref={ref}
    className={cn(
      'peer h-4 w-4 shrink-0 rounded-sm border border-primary ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground',
      className
    )}
    {...props}
  >
    <CheckboxPrimitive.Indicator
      className={cn('flex items-center justify-center text-current')}
    >
      <Check className="h-4 w-4" />
    </CheckboxPrimitive.Indicator>
  </CheckboxPrimitive.Root>
))
Checkbox.displayName = CheckboxPrimitive.Root.displayName

export { Checkbox }
