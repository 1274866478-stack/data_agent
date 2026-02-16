/**
 * # [INPUT] 基础输入框组件
 *
 * ## [MODULE]
 * **文件名**: input.tsx
 * **职责**: 提供标准化的输入框组件 - 支持所有input类型、文件上传样式、focus状态、禁用状态
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 基础输入框组件
 *
 * ## [INPUT]
 * Props (extends React.ComponentProps<"input">):
 * - **type?: string** - input类型（text, password, email, number, file等）
 * - **className?: string** - 自定义类名
 * - **所有input HTML属性**: placeholder, value, onChange, disabled, name, id等
 *
 * ## [OUTPUT]
 * - **Input组件** - 渲染HTML input元素
 *   - 基础样式：flex.h-9.w-full.rounded-md.border.border-input.bg-transparent.px-3.py-1
 *   - 阴影：shadow-sm
 *   - 过渡：transition-colors
 *   - 文件上传样式：file:border-0.file:bg-transparent.file:text-sm.file:font-medium.file:text-foreground
 *   - 占位符：placeholder:text-muted-foreground
 *   - focus状态：focus-visible:outline-none.focus-visible:ring-1.focus-visible:ring-ring
 *   - 禁用状态：disabled:cursor-not-allowed.disabled:opacity-50
 *   - 响应式字体：md:text-sm
 * - **forwardRef**: 支持ref转发到HTMLInputElement
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Input是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要输入框的组件
 * - 表单组件、搜索框、登录注册表单等
 *
 * ## [STATE]
 * - **无状态**: Input是无状态组件（纯展示组件）
 * - **受控组件**: value和onChange由父组件控制
 * - **基础样式**: flex.h-9.w-full.rounded-md.border.border-input.bg-transparent.px-3.py-1.text-base.shadow-sm
 * - **文件上传样式**: file:border-0.file:bg-transparent.file:text-sm.file:font-medium.file:text-foreground
 * - **占位符样式**: placeholder:text-muted-foreground
 * - **focus样式**: focus-visible:outline-none.focus-visible:ring-1.focus-visible:ring-ring
 * - **禁用样式**: disabled:cursor-not-allowed.disabled:opacity-50
 * - **响应式字体**: text-base（默认）, md:text-sm（中等屏幕以上）
 * - **type支持**: text, password, email, number, file, date等所有HTML input类型
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Input是纯展示组件
 * - **ref转发**: React.forwardRef转发ref到HTMLInputElement
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有input HTML属性
 * - **type属性**: type={type}设置input类型
 */

import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
