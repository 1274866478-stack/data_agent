/**
 * # [TYPOGRAPHY] 排版组件组
 *
 * ## [MODULE]
 * **文件名**: typography.tsx
 * **职责**: 提供标准化的排版组件组 - 包含11个子组件（H1-H4标题、段落、引用、代码等），统一文档排版样式
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 排版组件组
 *
 * ## [INPUT]
 * Props (TypographyProps):
 * - **className?: string** - 自定义类名
 * - **children: React.ReactNode** - 子元素内容
 *
 * ## [OUTPUT]
 * - **Typography组件组** - 11个子组件
 *   - **H1**: 一级标题（h1，scroll-m-20.text-4xl.font-extrabold.tracking-tight.lg:text-5xl）
 *   - **H2**: 二级标题（h2，scroll-m-20.border-b.pb-2.text-3xl.font-semibold.tracking-tight.first:mt-0）
 *   - **H3**: 三级标题（h3，scroll-m-20.text-2xl.font-semibold.tracking-tight）
 *   - **H4**: 四级标题（h4，scroll-m-20.text-xl.font-semibold.tracking-tight）
 *   - **P**: 段落（p，leading-7.[&:not(:first-child)]:mt-6）
 *   - **Blockquote**: 引用块（blockquote，mt-6.border-l-2.pl-6.italic.text-muted-foreground）
 *   - **Code**: 行内代码（code，relative.rounded.bg-muted.px-[0.3rem].py-[0.2rem].font-mono.text-sm.font-semibold）
 *   - **Pre**: 代码块（pre，mb-4.mt-6.overflow-x-auto.rounded-lg.border.bg-black.py-4）
 *   - **Lead**: 引导段落（p，text-xl.text-muted-foreground）
 *   - **Large**: 大号文本（div，text-lg.font-semibold）
 *   - **Small**: 小号文本（small，text-sm.font-medium.leading-none）
 *   - **Muted**: 次要文本（p，text-sm.text-muted-foreground）
 * - **scroll-m-20**: scroll-margin-top 5rem（锚点跳转时顶部留出空间）
 * - **tracking-tight**: letter-spacing -0.025em（紧凑字间距）
 * - **font-extrabold/font-semibold**: 字体粗细800/600
 * - **forwardRef**: 所有组件支持ref转发到HTML元素
 * - **displayName**: 所有组件设置displayName用于调试
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Typography组件组是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要排版的组件
 * - 文档页面、博客文章、内容展示等
 *
 * ## [STATE]
 * - **无状态**: Typography组件组是无状态组件（纯展示组件）
 * - **H1样式**: scroll-m-20.text-4xl.font-extrabold.tracking-tight.lg:text-5xl
 *   - **scroll-m-20**: scroll-margin-top 5rem（锚点跳转时顶部留出80px空间）
 *   - **text-4xl/lg:text-5xl**: 36px/48px字体大小（响应式）
 *   - **font-extrabold**: 字体粗重800
 *   - **tracking-tight**: 字间距-0.025em（紧凑）
 * - **H2样式**: scroll-m-20.border-b.pb-2.text-3xl.font-semibold.tracking-tight.first:mt-0
 *   - **border-b**: 底部边框（分隔线）
 *   - **pb-2**: 底部padding 8px
 *   - **first:mt-0**: 第一个元素无顶部margin
 * - **H3样式**: scroll-m-20.text-2xl.font-semibold.tracking-tight（24px，字体粗重600）
 * - **H4样式**: scroll-m-20.text-xl.font-semibold.tracking-tight（20px，字体粗重600）
 * - **P样式**: leading-7.[&:not(:first-child)]:mt-6
 *   - **leading-7**: 行高1.75（28px）
 *   - **[&:not(:first-child)]:mt-6**: 非第一个元素顶部margin 24px
 * - **Blockquote样式**: mt-6.border-l-2.pl-6.italic.text-muted-foreground
 *   - **border-l-2**: 左边框2px
 *   - **pl-6**: 左padding 24px
 *   - **italic**: 斜体
 * - **Code样式**: relative.rounded.bg-muted.px-[0.3rem].py-[0.2rem].font-mono.text-sm.font-semibold
 *   - **px-[0.3rem].py-[0.2rem]**: 水平/垂直padding 0.3rem/0.2rem（自定义值）
 *   - **font-mono**: 等宽字体
 * - **Pre样式**: mb-4.mt-6.overflow-x-auto.rounded-lg.border.bg-black.py-4
 *   - **overflow-x-auto**: 水平溢出滚动
 *   - **bg-black**: 黑色背景
 *   - **py-4**: 垂直padding 16px
 * - **Lead样式**: text-xl.text-muted-foreground（20px，次要前景色）
 * - **Large样式**: text-lg.font-semibold（18px，字体粗重600）
 * - **Small样式**: text-sm.font-medium.leading-none（14px，字体粗重500，行高1）
 * - **Muted样式**: text-sm.text-muted-foreground（14px，次要前景色）
 * - **forwardRef**: React.forwardRef转发ref到HTML元素
 * - **displayName**: 组件.displayName用于React DevTools调试
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Typography组件组是无状态组件（纯展示组件）
 * - **ref转发**: React.forwardRef转发ref到HTML元素（h1-h4, p, blockquote, code, pre, small）
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有Props
 * - **displayName**: 所有组件设置displayName用于调试
 * - **scroll-m-20**: 锚点跳转时顶部留出80px空间（避免被固定导航栏遮挡）
 * - **响应式字体**: text-4xl.lg:text-5xl（H1响应式字体大小）
 * - **条件margin**: first:mt-0（H2第一个元素无顶部margin）
 * - **条件margin**: [&:not(:first-child)]:mt-6（P非第一个元素顶部margin 24px）
 */

import * as React from "react"
import { cn } from "@/lib/utils"

export interface TypographyProps {
  className?: string
  children: React.ReactNode
}

export const H1 = React.forwardRef<HTMLHeadingElement, TypographyProps>(
  ({ className, children, ...props }, ref) => (
    <h1
      ref={ref}
      className={cn(
        "scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-5xl",
        className
      )}
      {...props}
    >
      {children}
    </h1>
  )
)
H1.displayName = "H1"

export const H2 = React.forwardRef<HTMLHeadingElement, TypographyProps>(
  ({ className, children, ...props }, ref) => (
    <h2
      ref={ref}
      className={cn(
        "scroll-m-20 border-b pb-2 text-3xl font-semibold tracking-tight first:mt-0",
        className
      )}
      {...props}
    >
      {children}
    </h2>
  )
)
H2.displayName = "H2"

export const H3 = React.forwardRef<HTMLHeadingElement, TypographyProps>(
  ({ className, children, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn(
        "scroll-m-20 text-2xl font-semibold tracking-tight",
        className
      )}
      {...props}
    >
      {children}
    </h3>
  )
)
H3.displayName = "H3"

export const H4 = React.forwardRef<HTMLHeadingElement, TypographyProps>(
  ({ className, children, ...props }, ref) => (
    <h4
      ref={ref}
      className={cn("scroll-m-20 text-xl font-semibold tracking-tight", className)}
      {...props}
    >
      {children}
    </h4>
  )
)
H4.displayName = "H4"

export const P = React.forwardRef<HTMLParagraphElement, TypographyProps>(
  ({ className, children, ...props }, ref) => (
    <p
      ref={ref}
      className={cn("leading-7 [&:not(:first-child)]:mt-6", className)}
      {...props}
    >
      {children}
    </p>
  )
)
P.displayName = "P"

export const Blockquote = React.forwardRef<HTMLQuoteElement, TypographyProps>(
  ({ className, children, ...props }, ref) => (
    <blockquote
      ref={ref}
      className={cn(
        "mt-6 border-l-2 pl-6 italic text-muted-foreground",
        className
      )}
      {...props}
    >
      {children}
    </blockquote>
  )
)
Blockquote.displayName = "Blockquote"

export const Code = React.forwardRef<HTMLElement, TypographyProps>(
  ({ className, children, ...props }, ref) => (
    <code
      ref={ref}
      className={cn(
        "relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-sm font-semibold",
        className
      )}
      {...props}
    >
      {children}
    </code>
  )
)
Code.displayName = "Code"

export const Pre = React.forwardRef<HTMLPreElement, TypographyProps>(
  ({ className, children, ...props }, ref) => (
    <pre
      ref={ref}
      className={cn(
        "mb-4 mt-6 overflow-x-auto rounded-lg border bg-black py-4",
        className
      )}
      {...props}
    >
      {children}
    </pre>
  )
)
Pre.displayName = "Pre"

export const Lead = React.forwardRef<HTMLParagraphElement, TypographyProps>(
  ({ className, children, ...props }, ref) => (
    <p
      ref={ref}
      className={cn("text-xl text-muted-foreground", className)}
      {...props}
    >
      {children}
    </p>
  )
)
Lead.displayName = "Lead"

export const Large = React.forwardRef<HTMLDivElement, TypographyProps>(
  ({ className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("text-lg font-semibold", className)}
      {...props}
    >
      {children}
    </div>
  )
)
Large.displayName = "Large"

export const Small = React.forwardRef<HTMLElement, TypographyProps>(
  ({ className, children, ...props }, ref) => (
    <small
      ref={ref}
      className={cn("text-sm font-medium leading-none", className)}
      {...props}
    >
      {children}
    </small>
  )
)
Small.displayName = "Small"

export const Muted = React.forwardRef<HTMLParagraphElement, TypographyProps>(
  ({ className, children, ...props }, ref) => (
    <p
      ref={ref}
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    >
      {children}
    </p>
  )
)
Muted.displayName = "Muted"