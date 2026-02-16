/**
 * # [ACCORDION] 手风琴组件组
 *
 * ## [MODULE]
 * **文件名**: accordion.tsx
 * **职责**: 提供标准化的手风琴组件 - 包含4个子组件，用于可折叠/展开的手风琴列表，支持同时打开多个
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 手风琴组件组
 *
 * ## [INPUT]
 * Props (各子组件的Props):
 * - **Accordion**: className?, children（容器）
 * - **AccordionItem**: className?, children（单个手风琴项）
 * - **AccordionTrigger**: className?, children, asChild?（触发按钮）
 * - **AccordionContent**: className?, children（折叠内容）
 *
 * ## [OUTPUT]
 * - **Accordion组件组** - 4个子组件
 *   - **Accordion**: 根容器（w-full，全宽）
 *   - **AccordionItem**: 单个手风琴项（border-b，下边框分隔）
 *   - **AccordionTrigger**: 触发按钮（flex.flex-1.items-center.justify-between.py-4.font-medium.transition-all.hover:underline）
 *     - **ChevronDown图标**: h-4.w-4.shrink-0.transition-transform.duration-200
 *     - **[data-state=open]旋转**: &[data-state=open]>svg:rotate-180（打开时图标旋转180度）
 *   - **AccordionContent**: 折叠内容（overflow-hidden.text-sm.transition-all）
 *     - **data-[state=closed]**: animate-accordion-up（向上折叠动画）
 *     - **data-[state=open]**: animate-accordion-down（向下展开动画）
 *     - **内部容器**: pb-4.pt-0（底部padding，顶部无padding）
 * - **无状态管理**: Accordion组件不包含状态管理逻辑（需要外部或Radix UI管理）
 * - **ChevronDown图标**: lucide-react图标，data-state=open时旋转180度
 * - **自定义动画**: animate-accordion-up/down（需要在globals.css中定义keyframes）
 * - **forwardRef**: Accordion和AccordionItem支持ref转发
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [lucide-react](https://lucide.dev/) - 图标库（ChevronDown）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Accordion组件组是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要手风琴列表的组件
 * - FAQ列表、折叠面板、可折叠导航等
 *
 * ## [STATE]
 * - **Accordion样式**: w-full（全宽）
 *   - **无状态**: Accordion本身不管理状态（状态由Radix UI或外部管理）
 * - **AccordionItem样式**: border-b（下边框分隔每个手风琴项）
 *   - **分隔线**: border-b创建视觉分隔
 * - **AccordionTrigger样式**: flex.flex-1.items-center.justify-between.py-4.font-medium.transition-all.hover:underline
 *   - **flex.flex-1**: flex布局，填充剩余空间
 *   - **justify-between**: 子元素两端对齐（文本在左，图标在右）
 *   - **py-4**: 上下padding 16px
 *   - **font-medium**: 字体粗细500
 *   - **hover:underline**: 悬停时显示下划线
 *   - **[&[data-state=open]>svg]:rotate-180**: 打开时ChevronDown图标旋转180度
 * - **ChevronDown图标**: h-4.w-4.shrink-0.transition-transform.duration-200
 *   - **h-4.w-4**: 16px × 16px
 *   - **shrink-0**: 禁止flex收缩
 *   - **transition-transform.duration-200**: transform过渡动画200ms
 *   - **rotate-180**: data-state=open时旋转180度
 * - **AccordionContent样式**: overflow-hidden.text-sm.transition-all
 *   - **overflow-hidden**: 隐藏溢出内容（折叠时）
 *   - **text-sm**: 小号字体（14px）
 *   - **transition-all**: 所有属性过渡动画
 *   - **data-[state=closed]**: animate-accordion-up（向上折叠动画）
 *   - **data-[state=open]**: animate-accordion-down（向下展开动画）
 * - **内部容器**: pb-4.pt-0（底部padding 16px，顶部无padding）
 * - **自定义动画keyframes**:
 *   - **@keyframes accordion-down**: from { height: 0 } to { height: var(--radix-accordion-content-height) }
 *   - **@keyframes accordion-up**: from { height: var(--radix-accordion-content-height) } to { height: 0 }
 * - **data-state属性**: Radix UI自动添加data-state属性（'open' | 'closed'）
 * - **forwardRef**: React.forwardRef转发ref到HTML元素
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Accordion组件组是无状态组件（状态由外部或Radix UI管理）
 * - **ref转发**: React.forwardRef转发ref到HTML元素
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有Props
 * - **数据属性**: data-[state=open/closed]由Radix UI或外部管理
 * - **CSS动画**: animate-accordion-up/down（需要在globals.css中定义keyframes）
 * - **ChevronDown旋转**: data-state=open时rotate-180，transition-transform.duration-200过渡动画
 * - **悬停效果**: hover:underline显示下划线
 * - **展开/折叠动画**: CSS grid-template-rows动画（基于--radix-accordion-content-height CSS变量）
 */

"use client"

import * as React from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

const Accordion = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("w-full", className)}
    {...props}
  />
))
Accordion.displayName = "Accordion"

const AccordionItem = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("border-b", className)}
    {...props}
  />
))
AccordionItem.displayName = "AccordionItem"

const AccordionTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    asChild?: boolean
  }
>(({ className, children, ...props }, ref) => (
  <button
    ref={ref}
    className={cn(
      "flex flex-1 items-center justify-between py-4 font-medium transition-all hover:underline [&[data-state=open]>svg]:rotate-180",
      className
    )}
    {...props}
  >
    {children}
    <ChevronDown className="h-4 w-4 shrink-0 transition-transform duration-200" />
  </button>
))
AccordionTrigger.displayName = AccordionTrigger.displayName || "AccordionTrigger"

const AccordionContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, children, ...props }, ref) => (
  <div
    ref={ref}
    className="overflow-hidden text-sm transition-all data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down"
    {...props}
  >
    <div className={cn("pb-4 pt-0", className)}>{children}</div>
  </div>
))
AccordionContent.displayName = AccordionContent.displayName || "AccordionContent"

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent }