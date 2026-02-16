/**
 * # [SWITCH] 开关切换组件
 *
 * ## [MODULE]
 * **文件名**: switch.tsx
 * **职责**: 提供标准化的开关切换组件 - 基于Radix UI Switch原语，支持checked/unchecked状态和Thumb滑块动画
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 开关切换组件
 *
 * ## [INPUT]
 * Props (extends React.ComponentPropsWithoutRef<typeof SwitchPrimitives.Root>):
 * - **className?: string** - 自定义类名
 * - **checked?: boolean** - 开关状态（true=开, false=关）
 * - **onCheckedChange?: (checked: boolean) => void** - 状态变化回调
 * - **disabled?: boolean** - 禁用状态
 * - **required?: boolean** - 必填状态
 * - **name?: string** - 表单字段名
 * - **value?: string** - 表单字段值
 *
 * ## [OUTPUT]
 * - **Switch组件** - 渲染开关切换元素
 *   - **Root样式**: peer.inline-flex.h-6.w-11.shrink-0.cursor-pointer.items-center.rounded-full.border-2.border-transparent
 *   - **尺寸**: h-6.w-11（24px高 × 44px宽）
 *   - **形状**: rounded-full（完全圆角，pill形状）
 *   - **边框**: border-2.border-transparent（2px透明边框）
 *   - **transition-colors**: 背景色过渡动画
 *   - **focus状态**: focus-visible:outline-none.focus-visible:ring-2.focus-visible:ring-ring.focus-visible:ring-offset-2.focus-visible:ring-offset-background
 *   - **禁用状态**: disabled:cursor-not-allowed.disabled:opacity-50
 *   - **checked样式**: data-[state=checked]:bg-primary
 *   - **unchecked样式**: data-[state=unchecked]:bg-input
 *   - **Thumb滑块**: SwitchPrimitives.Thumb（h-5.w-5.rounded-full.bg-background.shadow-lg.ring-0）
 *   - **Thumb动画**: transition-transform.data-[state=checked]:translate-x-5.data-[state=unchecked]:translate-x-0
 *   - **forwardRef**: 支持ref转发到SwitchPrimitives.Root
 *   - **displayName**: 设置为SwitchPrimitives.Root.displayName
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@radix-ui/react-switch](https://www.radix-ui.com/primitives/docs/components/switch) - Radix UI Switch原语
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Switch是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要开关切换的组件
 * - 设置页面、偏好设置、功能开关、主题切换等
 *
 * ## [STATE]
 * - **无状态**: Switch是无状态组件（checked状态由父组件控制）
 * - **checked状态**: checked?: boolean（受控组件，由父组件管理）
 * - **Root尺寸**: h-6.w-11（24px高 × 44px宽）
 * - **Thumb尺寸**: h-5.w-5（20px × 20px，比Root小4px）
 * - **形状**: rounded-full（完全圆角，pill形状）
 * - **边框**: border-2.border-transparent（2px透明边框，提升点击区域）
 * - **shrink-0**: 防止flex容器中收缩
 * - **cursor-pointer**: 鼠标指针变为pointer（可点击）
 * - **peer类**: 用于peer-disabled样式（与Label配合）
 * - **transition-colors**: 背景色过渡动画（checked时切换颜色）
 * - **focus样式**: focus-visible:outline-none.focus-visible:ring-2.focus-visible:ring-ring.focus-visible:ring-offset-2.focus-visible:ring-offset-background
 * - **禁用样式**: disabled:cursor-not-allowed.disabled:opacity-50
 * - **checked样式**: data-[state=checked]:bg-primary（选中时背景色变为主题色）
 * - **unchecked样式**: data-[state=unchecked]:bg-input（未选中时背景色变为input颜色）
 * - **Thumb样式**: h-5.w-5.rounded-full.bg-background.shadow-lg.ring-0
 *   - **bg-background**: Thumb背景色（与页面背景色一致）
 *   - **shadow-lg**: Thumb阴影（大阴影，提升立体感）
 *   - **ring-0**: 无ring（ring-offset由Root提供）
 * - **Thumb动画**: transition-transform.data-[state=checked]:translate-x-5.data-[state=unchecked]:translate-x-0
 *   - **transition-transform**: transform过渡动画
 *   - **translate-x-5**: checked时向右偏移20px（w-11=44px, h-5=20px, 偏移=44-20-4=20px）
 *   - **translate-x-0**: unchecked时无偏移（在最左侧）
 * - **pointer-events-none**: Thumb禁止鼠标事件（点击事件由Root处理）
 * - **forwardRef**: React.forwardRef转发ref到SwitchPrimitives.Root
 * - **displayName设置**: Switch.displayName = SwitchPrimitives.Root.displayName
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Switch是纯展示组件（状态由父组件控制）
 * - **ref转发**: React.forwardRef转发ref到SwitchPrimitives.Root
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有SwitchPrimitives.Root的Props（checked, onCheckedChange, disabled等）
 * - **数据属性**: data-[state=checked]和data-[state=unchecked]由Radix UI自动添加（基于checked prop）
 * - **Thumb动画**: CSS transition-transform触发Thumb滑块移动动画
 * - **背景色过渡**: CSS transition-colors触发Root背景色变化动画
 * - **peer类**: peer类用于配合peer-disabled样式（与Label组件配合使用）
 * - **事件处理**: Radix UI处理点击、键盘导航（Enter/Space切换状态）等事件
 * - **Thumb pointer-events-none**: Thumb禁止鼠标事件（防止重复触发Root的点击事件）
 */

"use client"

import * as React from "react"
import * as SwitchPrimitives from "@radix-ui/react-switch"

import { cn } from "@/lib/utils"

const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitives.Root>,
  React.ComponentPropsWithoutRef<typeof SwitchPrimitives.Root>
>(({ className, ...props }, ref) => (
  <SwitchPrimitives.Root
    className={cn(
      "peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-primary data-[state=unchecked]:bg-input",
      className
    )}
    {...props}
    ref={ref}
  >
    <SwitchPrimitives.Thumb
      className={cn(
        "pointer-events-none block h-5 w-5 rounded-full bg-background shadow-lg ring-0 transition-transform data-[state=checked]:translate-x-5 data-[state=unchecked]:translate-x-0"
      )}
    />
  </SwitchPrimitives.Root>
))
Switch.displayName = SwitchPrimitives.Root.displayName

export { Switch }
