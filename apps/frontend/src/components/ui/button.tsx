/**
 * # [BUTTON] 基础按钮组件
 *
 * ## [MODULE]
 * **文件名**: button.tsx
 * **职责**: 提供标准化的按钮组件 - 支持多种变体、尺寸、asChild模式、Radix UI Slot集成
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 基础按钮组件
 *
 * ## [INPUT]
 * Props (ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>):
 * - **variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'** - 按钮变体（默认'default'）
 * - **size?: 'default' | 'sm' | 'lg' | 'icon'** - 按钮尺寸（默认'default'）
 * - **asChild?: boolean** - 是否作为子元素渲染（默认false，使用Slot组件）
 * - **className?: string** - 自定义类名
 * - **children**: React.ReactNode - 按钮内容
 * - **所有button HTML属性**: onClick, disabled, type, form等
 *
 * ## [OUTPUT]
 * - **Button组件** - 渲染按钮或Slot组件
 *   - 基础样式：inline-flex.items-center.justify-center.gap-2.rounded-md.text-sm.font-medium.transition-colors
 *   - 状态样式：focus-visible:ring-1, disabled:opacity-50
 *   - variant样式：default（bg-primary）, destructive（bg-destructive）, outline（border）, secondary（bg-secondary）, ghost（hover:bg-accent）, link（underline）
 *   - size样式：default（h-9）, sm（h-8）, lg（h-10）, icon（h-9 w-9）
 * - **buttonVariants函数**: cva生成的类型安全变体函数
 * - **forwardRef**: 支持ref转发到HTMLButtonElement
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@radix-ui/react-slot](https://www.radix-ui.com/primitives/docs/utilities/slot) - Slot组件（asChild模式）
 * - [class-variance-authority](https://cva.style/docs) - CVA类名变体管理（cva, VariantProps）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Button是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要按钮的组件
 * - [../layout/Header.tsx](../layout/Header.tsx) - 头部导航按钮
 * - [../layout/Sidebar.tsx](../layout/Sidebar.tsx) - 侧边栏导航按钮
 * - 所有表单和交互组件
 *
 * ## [STATE]
 * - **无状态**: Button是无状态组件（纯展示组件）
 * - **CVA变体系统**: cva()创建类型安全的类名变体
 * - **variant变体**:
 *   - default: bg-primary.text-primary-foreground.shadow.hover:bg-primary/90
 *   - destructive: bg-destructive.text-destructive-foreground.shadow-sm.hover:bg-destructive/90
 *   - outline: border.border-input.bg-background.shadow-sm.hover:bg-accent
 *   - secondary: bg-secondary.text-secondary-foreground.shadow-sm.hover:bg-secondary/80
 *   - ghost: hover:bg-accent.hover:text-accent-foreground
 *   - link: text-primary.underline-offset-4.hover:underline
 * - **size变体**:
 *   - default: h-9.px-4.py-2
 *   - sm: h-8.rounded-md.px-3.text-xs
 *   - lg: h-10.rounded-md.px-8
 *   - icon: h-9.w-9
 * - **Slot模式**: asChild时渲染为Slot（子元素替换）
 * - **基础样式**: whitespace-nowrap, focus-visible:ring-1, focus-visible:ring-ring
 * - **禁用状态**: disabled:pointer-events-none.disabled:opacity-50
 * - **SVG样式**: [&_svg]:pointer-events-none.[&_svg]:size-4.[&_svg]:shrink-0
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Button是纯展示组件
 * - **ref转发**: React.forwardRef转发ref到HTMLButtonElement或Slot
 * - **类名合并**: cn(buttonVariants({ variant, size, className }))合并类名
 * - **条件渲染**: asChild ? Slot : "button"
 * - **Props透传**: {...props}传递所有HTML button属性
 * - **CVA类型安全**: VariantProps<typeof buttonVariants>提供类型提示
 */

import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import * as React from "react"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow hover:bg-primary/90 hover:-translate-y-0.5 hover:shadow-md",
        destructive:
          "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline:
          "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
        secondary:
          "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        // UX-modern 新增变体
        gradient:
          "bg-gradient-modern-primary text-white shadow-md hover:-translate-y-0.5 hover:shadow-lg",
        modernPrimary:
          "bg-gradient-to-r from-violet-600 to-purple-600 text-white shadow-md hover:-translate-y-0.5 hover:shadow-lg",
        modernAccent:
          "bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-md hover:-translate-y-0.5 hover:shadow-lg",
        modernSuccess:
          "bg-gradient-to-r from-green-500 to-emerald-500 text-white shadow-md hover:-translate-y-0.5 hover:shadow-lg",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }

