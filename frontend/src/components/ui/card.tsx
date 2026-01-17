/**
 * # [CARD] 基础卡片组件组
 *
 * ## [MODULE]
 * **文件名**: card.tsx
 * **职责**: 提供标准化的卡片容器组件 - Card容器和5个子组件（Header, Title, Description, Content, Footer）
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 基础卡片组件组
 *
 * ## [INPUT]
 * Props (所有组件都继承 React.HTMLAttributes<HTMLDivElement>):
 * - **Card**: className?, ...div属性
 * - **CardHeader**: className?, ...div属性
 * - **CardTitle**: className?, ...div属性
 * - **CardDescription**: className?, ...div属性
 * - **CardContent**: className?, ...div属性
 * - **CardFooter**: className?, ...div属性
 * - **children**: React.ReactNode - 子元素内容
 *
 * ## [OUTPUT]
 * - **Card组件组** - 渲染卡片容器和子组件
 *   - **Card**: rounded-xl.border.bg-card.text-card-foreground.shadow
 *   - **CardHeader**: flex.flex-col.space-y-1.5.p-6
 *   - **CardTitle**: font-semibold.leading-none.tracking-tight
 *   - **CardDescription**: text-sm.text-muted-foreground
 *   - **CardContent**: p-6.pt-0（padding上下文，顶部无padding）
 *   - **CardFooter**: flex.items-center.p-6.pt-0（flex布局，底部操作区）
 * - **forwardRef**: 所有组件支持ref转发到HTMLDivElement
 * - **displayName**: 设置组件显示名称（用于调试）
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Card组件组是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要卡片布局的组件
 * - 数据展示卡片、信息卡片、表单卡片等
 * - Dashboard统计卡片、文档卡片、数据源卡片等
 *
 * ## [STATE]
 * - **无状态**: 所有Card组件是无状态组件（纯展示组件）
 * - **Card样式**: rounded-xl.border.bg-card.text-card-foreground.shadow
 * - **CardHeader样式**: flex.flex-col.space-y-1.5.p-6（垂直flex布局，间距1.5）
 * - **CardTitle样式**: font-semibold.leading-none.tracking-tight（标题样式）
 * - **CardDescription样式**: text-sm.text-muted-foreground（次要文本）
 * - **CardContent样式**: p-6.pt-0（水平padding 24px，顶部padding 0）
 * - **CardFooter样式**: flex.items-center.p-6.pt-0（flex布局，底部操作区）
 * - **组合模式**: Card包裹CardHeader、CardContent、CardFooter
 * - **类名合并**: cn()合并默认类名和自定义className
 * - **ref转发**: React.forwardRef转发ref到HTMLDivElement
 * - **Props透传**: {...props}传递所有HTML div属性
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: 所有Card组件是纯展示组件
 * - **ref转发**: React.forwardRef转发ref到HTMLDivElement
 * - **类名合并**: cn(defaultClasses, className)合并类名
 * - **Props透传**: {...props}传递所有HTML div属性
 * - **组合渲染**: Card包裹Header、Content、Footer组合使用
 * - **displayName设置**: 组件.displayName用于调试和React DevTools
 */

import * as React from "react"

import { cn } from "@/lib/utils"

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-xl border bg-card text-card-foreground shadow-sm transition-all duration-200 hover:shadow-md",
      className
    )}
    {...props}
  />
))
Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("font-semibold leading-none tracking-tight", className)}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"

export { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle }

