/**
 * # [TEXTAREA] 文本域组件
 *
 * ## [MODULE]
 * **文件名**: textarea.tsx
 * **职责**: 提供标准化的多行文本输入组件 - 最小高度、focus状态、禁用状态、ring-offset效果
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 文本域组件
 *
 * ## [INPUT]
 * Props (TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement>):
 * - **className?: string** - 自定义类名
 * - **所有textarea HTML属性**: placeholder, value, onChange, disabled, name, id, rows, cols等
 *
 * ## [OUTPUT]
 * - **Textarea组件** - 渲染HTML textarea元素
 *   - 最小高度：min-h-[80px]（80px）
 *   - 基础样式：flex.w-full.rounded-md.border.border-input.bg-background.px-3.py-2
 *   - 字体大小：text-sm
 *   - 占位符：placeholder:text-muted-foreground
 *   - focus状态：focus-visible:outline-none.focus-visible:ring-2.focus-visible:ring-ring.focus-visible:ring-offset-2
 *   - ring-offset：ring-offset-background（focus时的偏移效果）
 *   - 禁用状态：disabled:cursor-not-allowed.disabled:opacity-50
 *   - **forwardRef**: 支持ref转发到HTMLTextAreaElement
 *   - **TextareaProps接口**: extends React.TextareaHTMLAttributes<HTMLTextAreaElement>
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Textarea是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要多行文本输入的组件
 * - 表单组件、评论输入、消息输入等
 *
 * ## [STATE]
 * - **无状态**: Textarea是无状态组件（纯展示组件）
 * - **受控组件**: value和onChange由父组件控制
 * - **最小高度**: min-h-[80px]（80px最小高度）
 * - **基础样式**: flex.w-full.rounded-md.border.border-input.bg-background.px-3.py-2.text-sm
 * - **ring-offset**: ring-offset-background（focus时的偏移效果，与ring配合）
 *   - focus-visible:ring-2（2px ring）
 *   - focus-visible:ring-offset-2（2px offset，避免border与ring重叠）
 * - **占位符样式**: placeholder:text-muted-foreground
 * - **focus样式**: focus-visible:outline-none（去除outline）+ focus-visible:ring-2（2px ring）+ focus-visible:ring-ring（ring颜色）+ focus-visible:ring-offset-2（2px offset）
 * - **禁用样式**: disabled:cursor-not-allowed.disabled:opacity-50
 * - **多行文本**: 支持rows和cols属性控制大小
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Textarea是纯展示组件
 * - **ref转发**: React.forwardRef转发ref到HTMLTextAreaElement
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有textarea HTML属性
 * - **自动调整**: textarea根据内容自动调整高度（由浏览器原生支持）
 */

import * as React from "react"

import { cn } from "@/lib/utils"

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Textarea.displayName = "Textarea"

export { Textarea }