/**
 * # [SCROLL AREA] 滚动区域组件组
 *
 * ## [MODULE]
 * **文件名**: scroll-area.tsx
 * **职责**: 提供标准化的滚动区域组件 - 基于Radix UI ScrollArea原语，包含2个子组件
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 滚动区域组件组
 *
 * ## [INPUT]
 * Props (各子组件的Props extends Radix UI组件Props):
 * - **ScrollArea**: className?, children（子元素内容）
 * - **ScrollBar**: className?, orientation?('vertical' | 'horizontal')
 *
 * ## [OUTPUT]
 * - **ScrollArea组件组** - 2个子组件
 *   - **ScrollArea**: Root容器（relative.overflow-hidden）
 *   - **ScrollBar**: 滚动条（flex.touch-none.select-none.transition-colors）
 *   - **Viewport**: ScrollAreaPrimitive.Viewport（h-full.w-full.rounded-[inherit]）
 *   - **Corner**: ScrollAreaPrimitive.Corner（水平和垂直滚动条交汇角）
 *   - **ScrollAreaScrollbar**: 滚动条容器（orientation条件样式）
 *   - **ScrollAreaThumb**: 滚动条滑块（relative.flex-1.rounded-full.bg-border）
 *   - **forwardRef**: 所有组件支持ref转发到Radix UI原语
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@radix-ui/react-scroll-area](https://www.radix-ui.com/primitives/docs/components/scroll-area) - Radix UI ScrollArea原语
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（ScrollArea组件组是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要自定义滚动区域的组件
 * - 长列表滚动、内容溢出滚动、自定义滚动条样式等
 *
 * ## [STATE]
 * - **ScrollArea Root状态**: 滚动状态由Radix UI管理
 * - **ScrollArea样式**: relative.overflow-hidden（相对定位，隐藏溢出）
 *   - **relative**: 相对定位（Viewport和ScrollBar的绝对定位基准）
 *   - **overflow-hidden**: 隐藏溢出内容（Viewport负责滚动）
 * - **Viewport样式**: h-full.w-full.rounded-[inherit]
 *   - **h-full.w-full**: 100%高度和宽度（填充ScrollArea容器）
 *   - **rounded-[inherit]**: 继承父组件的圆角
 * - **ScrollBar样式**: flex.touch-none.select-none.transition-colors
 *   - **flex**: flex布局（Thumb填充剩余空间）
 *   - **touch-none**: 禁用触摸手势（使用Radix UI的滚动）
 *   - **select-none**: 禁止文本选择
 *   - **transition-colors**: 背景色过渡动画（hover时）
 * - **ScrollBar orientation条件样式**:
 *   - **vertical**: h-full.w-2.5.border-l.border-l-transparent.p-[1px]（100%高，10px宽，左边框）
 *   - **horizontal**: h-2.5.flex-col.border-t.border-t-transparent.p-[1px]（10px高，flex列布局，上边框）
 *   - **w-2.5/h-2.5**: 10px宽度/高度
 *   - **border-l/border-t-transparent**: 透明边框（避免双倍边框）
 *   - **p-[1px]**: 4px padding（为Thumb留空间）
 * - **ScrollAreaThumb样式**: relative.flex-1.rounded-full.bg-border
 *   - **relative**: 相对定位
 *   - **flex-1**: flex填充（填充ScrollBar剩余空间）
 *   - **rounded-full**: 完全圆角（pill形状）
 *   - **bg-border**: 边框颜色（灰色滚动条）
 * - **Corner**: ScrollAreaPrimitive.Corner（水平和垂直滚动条交汇角，渲染小方块）
 * - **forwardRef**: React.forwardRef转发ref到Radix UI原语
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: ScrollArea组件组是无状态组件（滚动状态由Radix UI管理）
 * - **ref转发**: React.forwardRef转发ref到Radix UI原语
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有Radix UI Props
 * - **orientation条件渲染**: orientation === "vertical" ? "h-full.w-2.5" : "h-2.5.flex-col"
 * - **子组件嵌套**: ScrollArea包裹Viewport + ScrollBar + Corner
 * - **自定义滚动条**: Radix UI ScrollArea覆盖浏览器默认滚动条
 * - **触摸禁用**: touch-none（使用Radix UI的滚动，而非浏览器原生滚动）
 */

import * as React from "react"
import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area"

import { cn } from "@/lib/utils"

const ScrollArea = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.Root>
>(({ className, children, ...props }, ref) => (
  <ScrollAreaPrimitive.Root
    ref={ref}
    className={cn("relative overflow-hidden", className)}
    {...props}
  >
    <ScrollAreaPrimitive.Viewport className="h-full w-full rounded-[inherit]">
      {children}
    </ScrollAreaPrimitive.Viewport>
    <ScrollBar />
    <ScrollAreaPrimitive.Corner />
  </ScrollAreaPrimitive.Root>
))
ScrollArea.displayName = ScrollAreaPrimitive.Root.displayName

const ScrollBar = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>,
  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>
>(({ className, orientation = "vertical", ...props }, ref) => (
  <ScrollAreaPrimitive.ScrollAreaScrollbar
    ref={ref}
    orientation={orientation}
    className={cn(
      "flex touch-none select-none transition-colors",
      orientation === "vertical" &&
        "h-full w-2.5 border-l border-l-transparent p-[1px]",
      orientation === "horizontal" &&
        "h-2.5 flex-col border-t border-t-transparent p-[1px]",
      className
    )}
    {...props}
  >
    <ScrollAreaPrimitive.ScrollAreaThumb className="relative flex-1 rounded-full bg-border" />
  </ScrollAreaPrimitive.ScrollAreaScrollbar>
))
ScrollBar.displayName = ScrollAreaPrimitive.ScrollAreaScrollbar.displayName

export { ScrollArea, ScrollBar }
