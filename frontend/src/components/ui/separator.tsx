/**
 * # [SEPARATOR] 分隔线组件
 *
 * ## [MODULE]
 * **文件名**: separator.tsx
 * **职责**: 提供标准化的分隔线组件 - 基于Radix UI Separator原语，支持水平/垂直方向
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 分隔线组件
 *
 * ## [INPUT]
 * Props (extends React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>):
 * - **className?: string** - 自定义类名
 * - **orientation?: 'horizontal' | 'vertical'** - 分隔线方向（默认'horizontal'）
 * - **decorative?: boolean** - 装饰性标识（默认true，用于辅助技术）
 * - **所有div HTML属性**: style, id等
 *
 * ## [OUTPUT]
 * - **Separator组件** - 渲染分隔线元素（hr或div）
 *   - **基础样式**: shrink-0.bg-border
 *   - **水平方向**: orientation === "horizontal" ? "h-[1px].w-full" : "h-full.w-[1px]"
 *   - **水平尺寸**: h-[1px].w-full（1px高，100%宽）
 *   - **垂直尺寸**: h-full.w-[1px]（100%高，1px宽）
 *   - **shrink-0**: 防止flex容器中收缩
 *   - **bg-border**: 边框颜色（灰色）
 *   - **decorative属性**: decorative={decorative}（默认true，告知辅助技术这是装饰性元素）
 *   - **forwardRef**: 支持ref转发到SeparatorPrimitive.Root
 *   - **displayName**: 设置为SeparatorPrimitive.Root.displayName
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@radix-ui/react-separator](https://www.radix-ui.com/primitives/docs/components/separator) - Radix UI Separator原语
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Separator是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要分隔线的组件
 * - 菜单项分隔、内容区域分隔、视觉分隔等
 *
 * ## [STATE]
 * - **无状态**: Separator是无状态组件（纯展示组件）
 * - **orientation方向**: orientation?: 'horizontal' | 'vertical'（默认'horizontal'）
 * - **decorative属性**: decorative?: boolean（默认true，用于辅助技术）
 *   - **decorative=true**: 告知屏幕阅读器这是装饰性元素，不需要朗读
 *   - **decorative=false**: 告知屏幕阅读器这是有意义的分隔线，需要朗读
 * - **基础样式**: shrink-0.bg-border
 *   - **shrink-0**: 防止flex容器中收缩（保持最小尺寸）
 *   - **bg-border**: 边框颜色（灰色，与border颜色一致）
 * - **方向条件样式**: orientation === "horizontal" ? "h-[1px].w-full" : "h-full.w-[1px]"
 *   - **horizontal**: h-[1px].w-full（1px高，100%宽，水平线）
 *   - **vertical**: h-full.w-[1px]（100%高，1px宽，垂直线）
 * - **forwardRef**: React.forwardRef转发ref到SeparatorPrimitive.Root
 * - **displayName设置**: Separator.displayName = SeparatorPrimitive.Root.displayName
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Separator是纯展示组件
 * - **ref转发**: React.forwardRef转发ref到SeparatorPrimitive.Root
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有SeparatorPrimitive.Root的Props（orientation, decorative等）
 * - **方向条件渲染**: orientation === "horizontal" ? "h-[1px].w-full" : "h-full.w-[1px]"
 * - **decorative属性**: decorative={decorative}传递给Radix UI（用于辅助技术）
 */

import * as React from "react"
import * as SeparatorPrimitive from "@radix-ui/react-separator"

import { cn } from "@/lib/utils"

const Separator = React.forwardRef<
  React.ElementRef<typeof SeparatorPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root>
>(
  (
    { className, orientation = "horizontal", decorative = true, ...props },
    ref
  ) => (
    <SeparatorPrimitive.Root
      ref={ref}
      decorative={decorative}
      orientation={orientation}
      className={cn(
        "shrink-0 bg-border",
        orientation === "horizontal" ? "h-[1px] w-full" : "h-full w-[1px]",
        className
      )}
      {...props}
    />
  )
)
Separator.displayName = SeparatorPrimitive.Root.displayName

export { Separator }
