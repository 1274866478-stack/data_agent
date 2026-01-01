/**
 * # [LABEL] 表单标签组件
 *
 * ## [MODULE]
 * **文件名**: label.tsx
 * **职责**: 提供标准化的表单标签组件 - 基于Radix UI Label原语，支持CVA变体系统
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 表单标签组件
 *
 * ## [INPUT]
 * Props (extends React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root> & VariantProps<typeof labelVariants>):
 * - **className?: string** - 自定义类名
 * - **htmlFor?: string** - 关联的input表单元素的id（通过LabelPrimitive.Root传递）
 * - **所有label HTML属性**: children, id, form等
 *
 * ## [OUTPUT]
 * - **Label组件** - 渲染表单label元素
 *   - **基础样式**: text-sm.font-medium.leading-none（14px字体，中等粗细，无行高）
 *   - **peer-disabled样式**: peer-disabled:cursor-not-allowed.peer-disabled:opacity-70
 *   - **CVA变体系统**: cva()创建类型安全的类名变体（虽然当前只有1个基础变体）
 *   - **htmlFor属性**: 通过LabelPrimitive.Root传递，关联input表单元素
 *   - **forwardRef**: 支持ref转发到LabelPrimitive.Root（HTMLLabelElement）
 *   - **displayName**: 设置为LabelPrimitive.Root.displayName（用于调试）
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@radix-ui/react-label](https://www.radix-ui.com/primitives/docs/components/label) - Radix UI Label原语
 * - [class-variance-authority](https://cva.style/) - CVA变体系统（cva, VariantProps）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Label是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要表单标签的组件
 * - 表单组件、输入框组合、复选框标签、单选框标签等
 *
 * ## [STATE]
 * - **无状态**: Label是无状态组件（纯展示组件）
 * - **CVA变体系统**: cva()创建类型安全的类名变体
 * - **基础样式**: text-sm.font-medium.leading-none（14px字体，中等粗细，行高1.0）
 * - **peer-disabled样式**: peer-disabled:cursor-not-allowed.peer-disabled:opacity-70
 *   - **peer-disabled**: 当关联的表单元素（peer）有disabled属性时生效
 *   - **cursor-not-allowed**: 禁用状态下鼠标指针变为not-allowed
 *   - **opacity-70**: 禁用状态下透明度降低到70%
 * - **forwardRef**: React.forwardRef转发ref到LabelPrimitive.Root
 * - **htmlFor关联**: 通过LabelPrimitive.Root的htmlFor属性关联input的id
 * - **displayName设置**: Label.displayName = LabelPrimitive.Root.displayName
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Label是纯展示组件
 * - **ref转发**: React.forwardRef转发ref到LabelPrimitive.Root（HTMLLabelElement）
 * - **类名合并**: cn(labelVariants(), className)合并类名
 * - **Props透传**: {...props}传递所有LabelPrimitive.Root的Props（包括htmlFor）
 * - **CVA类型安全**: VariantProps<typeof labelVariants>提供类型提示
 * - **peer-disabled伪类**: 当关联的表单元素（peer）disabled时，Label样式自动变化
 * - **htmlFor关联**: LabelPrimitive.Root的htmlFor属性关联input的id（点击Label聚焦input）
 */

"use client"

import * as React from "react"
import * as LabelPrimitive from "@radix-ui/react-label"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const labelVariants = cva(
  "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
)

const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root> &
    VariantProps<typeof labelVariants>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn(labelVariants(), className)}
    {...props}
  />
))
Label.displayName = LabelPrimitive.Root.displayName

export { Label }
