/**
 * # [PROGRESS] 进度条组件
 *
 * ## [MODULE]
 * **文件名**: progress.tsx
 * **职责**: 提供标准化的进度条组件 - 基于Radix UI Progress原语，支持0-100百分比显示
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 进度条组件
 *
 * ## [INPUT]
 * Props (extends React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root>):
 * - **className?: string** - 自定义类名
 * - **value?: number** - 进度值（0-100之间的数字，0=空, 100=满）
 * - **max?: number** - 最大值（默认100，但Radix UI Progress使用value直接表示百分比）
 * - **所有div HTML属性**: style, id等
 *
 * ## [OUTPUT]
 * - **Progress组件** - 渲染进度条容器和Indicator
 *   - **Root容器**: ProgressPrimitive.Root（relative.h-2.w-full.overflow-hidden.rounded-full.bg-secondary）
 *   - **Indicator**: ProgressPrimitive.Indicator（h-full.w-full.flex-1.bg-primary.transition-all）
 *   - **容器高度**: h-2（8px固定高度）
 *   - **容器宽度**: w-full（100%宽度）
 *   - **容器形状**: rounded-full（完全圆角，pill形状）
 *   - **容器背景**: bg-secondary（次要背景色）
 *   - **overflow-hidden**: 隐藏超出部分（Indicator的transform可能超出）
 *   - **Indicator宽度**: h-full.w-full.flex-1（100%高度，100%宽度，flex-1填充）
 *   - **Indicator背景**: bg-primary（主题色）
 *   - **Indicator动画**: transition-all（所有属性过渡动画）
 *   - **Indicator transform**: translateX(-${100 - (value || 0)}%)（向左偏移实现进度效果）
 *   - **forwardRef**: 支持ref转发到ProgressPrimitive.Root
 *   - **displayName**: 设置为ProgressPrimitive.Root.displayName
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@radix-ui/react-progress](https://www.radix-ui.com/primitives/docs/components/progress) - Radix UI Progress原语
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Progress是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要进度条显示的组件
 * - 文件上传进度、任务完成进度、加载进度、步骤进度等
 *
 * ## [STATE]
 * - **无状态**: Progress是无状态组件（value状态由父组件控制）
 * - **value状态**: value?: number（受控组件，由父组件管理，0-100之间的数字）
 * - **容器尺寸**: h-2.w-full（8px高度，100%宽度）
 * - **容器形状**: rounded-full（完全圆角，pill形状，左右圆角半径9999px）
 * - **容器背景**: bg-secondary（次要背景色，灰色）
 * - **overflow-hidden**: 隐藏超出部分（Indicator的transform可能超出容器）
 * - **Indicator样式**: h-full.w-full.flex-1.bg-primary.transition-all
 *   - **h-full**: 100%高度（填充容器）
 *   - **w-full**: 100%宽度（但通过transform实际显示的宽度由value控制）
 *   - **flex-1**: flex填充（虽然不是flex容器，但保持一致性）
 *   - **bg-primary**: 主题色（蓝色或品牌色）
 *   - **transition-all**: 所有CSS属性过渡动画（width, transform, background等）
 * - **Indicator transform**: style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
 *   - **translateX**: 向左偏移实现进度效果
 *   - **value=0**: translateX(-100%)（完全偏移到左边外，不显示）
 *   - **value=50**: translateX(-50%)（偏移50%，显示一半）
 *   - **value=100**: translateX(-0%)（无偏移，完全显示）
 *   - **(value || 0)**: 防止value为undefined时计算错误
 * - **相对定位**: relative（容器相对定位，Indicator的transform相对于容器）
 * - **forwardRef**: React.forwardRef转发ref到ProgressPrimitive.Root
 * - **displayName设置**: Progress.displayName = ProgressPrimitive.Root.displayName
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Progress是纯展示组件（value状态由父组件控制）
 * - **ref转发**: React.forwardRef转发ref到ProgressPrimitive.Root
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有ProgressPrimitive.Root的Props（value, max等）
 * - **内联样式**: style={{ transform: `translateX(-${100 - (value || 0)}%)` }}（动态计算Indicator的偏移）
 * - **transition-all动画**: CSS transition-all触发Indicator的transform和background变化动画
 * - **overflow-hidden**: 隐藏Indicator的超出部分（translateX偏移可能超出容器）
 */

'use client'

import * as React from 'react'
import * as ProgressPrimitive from '@radix-ui/react-progress'

import { cn } from '@/lib/utils'

const Progress = React.forwardRef<
  React.ElementRef<typeof ProgressPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root>
>(({ className, value, ...props }, ref) => (
  <ProgressPrimitive.Root
    ref={ref}
    className={cn(
      'relative h-2 w-full overflow-hidden rounded-full bg-secondary',
      className
    )}
    {...props}
  >
    <ProgressPrimitive.Indicator
      className="h-full w-full flex-1 bg-primary transition-all"
      style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
    />
  </ProgressPrimitive.Root>
))
Progress.displayName = ProgressPrimitive.Root.displayName

export { Progress }
