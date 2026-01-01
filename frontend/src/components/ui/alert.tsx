/**
 * # [ALERT] 警告提示组件组
 *
 * ## [MODULE]
 * **文件名**: alert.tsx
 * **职责**: 提供标准化的警告提示组件 - Alert容器和2个子组件（Title, Description），支持CVA变体系统
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 警告提示组件组
 *
 * ## [INPUT]
 * Props (各子组件的Props):
 * - **Alert**: className?, variant?('default' | 'destructive'), ...div属性
 * - **AlertTitle**: className?, ...h5属性
 * - **AlertDescription**: className?, ...div属性
 * - **children**: React.ReactNode - 子元素内容
 *
 * ## [OUTPUT]
 * - **Alert组件组** - 渲染警告提示容器和子组件
 *   - **Alert**: relative.w-full.rounded-lg.border.p-4（role="alert"用于无障碍访问）
 *   - **AlertTitle**: h5.mb-1.font-medium.leading-none.tracking-tight
 *   - **AlertDescription**: div.text-sm.[&_p]:leading-relaxed
 * - **CVA变体系统**: 2种variant（default, destructive）
 *   - **default**: bg-background.text-foreground
 *   - **destructive**: border-destructive/50.text-destructive.dark:border-destructive（icon颜色也变为destructive）
 * - **特殊选择器**:
 *   - [&>svg~*]:pl-7 - 当有icon时，后续兄弟元素左padding 28px
 *   - [&>svg+div]:translate-y-[-3px] - icon后的div向上偏移3px
 *   - [&>svg]:absolute.[&>svg]:left-4.[&>svg]:top-4 - icon绝对定位在左上角
 *   - [&>svg]:text-foreground - icon颜色（destructive variant中覆盖为text-destructive）
 * - **forwardRef**: 所有组件支持ref转发
 * - **displayName**: 设置组件显示名称（用于调试）
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [class-variance-authority](https://cva.style/) - CVA变体系统（cva, VariantProps）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Alert组件组是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要警告提示的组件
 * - 表单验证错误提示、操作成功/失败提示、重要信息通知等
 *
 * ## [STATE]
 * - **无状态**: 所有Alert组件是无状态组件（纯展示组件）
 * - **CVA变体系统**: cva()创建类型安全的类名变体
 * - **variant变体**: 2种（default, destructive）
 *   - **default**: bg-background.text-foreground（默认样式）
 *   - **destructive**: border-destructive/50.text-destructive（警告样式，icon也变红）
 * - **特殊选择器**:
 *   - [&>svg~*]:pl-7 - icon后续元素左padding 28px（为icon留空间）
 *   - [&>svg+div]:translate-y-[-3px] - icon后div向上偏移3px（视觉对齐）
 *   - [&>svg]:absolute.[&>svg]:left-4.[&>svg]:top-4 - icon绝对定位（left-16px, top-16px）
 *   - [&>svg]:text-foreground - icon颜色（destructive variant中为[&>svg]:text-destructive）
 * - **Alert样式**: relative.w-full.rounded-lg.border.p-4（relative用于icon绝对定位）
 * - **AlertTitle样式**: h5.mb-1.font-medium.leading-none.tracking-tight（标题h5语义标签）
 * - **AlertDescription样式**: text-sm.[&_p]:leading-relaxed（描述文本，p标签行高1.625）
 * - **role="alert"**: Alert组件的ARIA角色（用于屏幕阅读器等辅助技术）
 * - **forwardRef**: React.forwardRef转发ref到HTMLDivElement或HTMLHeadingElement
 * - **displayName设置**: 组件.displayName用于调试和React DevTools
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: 所有Alert组件是纯展示组件
 * - **ref转发**: React.forwardRef转发ref到HTMLDivElement或HTMLHeadingElement
 * - **类名合并**: cn(alertVariants({ variant }), className)合并类名
 * - **Props透传**: {...props}传递所有HTML属性
 * - **CVA类型安全**: VariantProps<typeof alertVariants>提供类型提示
 * - **role属性**: role="alert"用于ARIA无障碍访问
 * - **特殊选择器**: Tailwind的[&>...]子选择器实现icon定位和文本偏移
 */

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const alertVariants = cva(
  "relative w-full rounded-lg border p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground",
  {
    variants: {
      variant: {
        default: "bg-background text-foreground",
        destructive:
          "border-destructive/50 text-destructive dark:border-destructive [&>svg]:text-destructive",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

const Alert = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof alertVariants>
>(({ className, variant, ...props }, ref) => (
  <div
    ref={ref}
    role="alert"
    className={cn(alertVariants({ variant }), className)}
    {...props}
  />
))
Alert.displayName = "Alert"

const AlertTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h5
    ref={ref}
    className={cn("mb-1 font-medium leading-none tracking-tight", className)}
    {...props}
  />
))
AlertTitle.displayName = "AlertTitle"

const AlertDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm [&_p]:leading-relaxed", className)}
    {...props}
  />
))
AlertDescription.displayName = "AlertDescription"

export { Alert, AlertTitle, AlertDescription }
