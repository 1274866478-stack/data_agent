/**
 * # [SHEET] 侧边抽屉组件组
 *
 * ## [MODULE]
 * **文件名**: sheet.tsx
 * **职责**: 提供标准化的侧边抽屉组件 - 基于Radix UI Dialog原语，包含10个子组件，支持4个方向的侧边滑入
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 侧边抽屉组件组
 *
 * ## [INPUT]
 * Props (各子组件的Props extends Radix UI组件Props):
 * - **Sheet**: Radix UI Root组件的所有Props（open, onOpenChange, defaultOpen等）
 * - **SheetTrigger**: className?, children（触发按钮）
 * - **SheetClose**: className?, children（关闭按钮）
 * - **SheetContent**: className?, side?('top' | 'bottom' | 'left' | 'right', 默认'right')
 * - **SheetHeader**: className?, children
 * - **SheetFooter**: className?, children
 * - **SheetTitle**: className?, children
 * - **SheetDescription**: className?, children
 *
 * ## [OUTPUT]
 * - **Sheet组件组** - 10个子组件
 *   - **Sheet**: Root组件（管理抽屉打开/关闭状态）
 *   - **SheetTrigger**: 触发按钮（点击打开抽屉）
 *   - **SheetClose**: 关闭按钮（点击关闭抽屉）
 *   - **SheetPortal**: Portal容器（渲染到body）
 *   - **SheetOverlay**: 遮罩层（fixed.inset-0.z-50.bg-black/80，半透明黑色背景）
 *   - **SheetContent**: 抽屉内容（fixed.z-50.gap-4.bg-background.p-6.shadow-lg）
 *   - **SheetHeader**: 头部容器（flex.flex-col.space-y-2.text-center.sm:text-left）
 *   - **SheetFooter**: 底部容器（flex.flex-col-reverse.sm:flex-row.sm:justify-end）
 *   - **SheetTitle**: 标题（text-lg.font-semibold.text-foreground）
 *   - **SheetDescription**: 描述（text-sm.text-muted-foreground）
 * - **side方向**: 4个方向（top/bottom/left/right，默认right）
 * - **CVA variants**: sheetVariants({ side })管理4个方向的样式
 *   - **top**: inset-x-0.top-0.border-b，从顶部滑入（slide-in-from-top）
 *   - **bottom**: inset-x-0.bottom-0.border-t，从底部滑入（slide-in-from-bottom）
 *   - **left**: inset-y-0.left-0.h-full.w-3/4.border-r，从左侧滑入（slide-in-from-left），sm:max-w-sm
 *   - **right**: inset-y-0.right-0.h-full.w-3/4.border-l，从右侧滑入（slide-in-from-right），sm:max-w-sm
 * - **关闭按钮**: SheetContent包含绝对定位的关闭按钮（absolute.right-4.top-4，Cross2Icon）
 * - **动画效果**: animate-in/out, fade-in/out, slide-in-from-*
 * - **Portal渲染**: SheetPrimitive.Portal渲染到body
 * - **forwardRef**: 所有组件支持ref转发到Radix UI原语
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@radix-ui/react-dialog](https://www.radix-ui.com/primitives/docs/components/dialog) - Radix UI Dialog原语（Sheet基于Dialog）
 * - [@radix-ui/react-icons](https://www.radix-ui.com/icons) - Radix UI图标库（Cross2Icon）
 * - [class-variance-authority](https://cva.style/) - CVA库（sheetVariants）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Sheet组件组是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要侧边抽屉的组件
 * - 设置面板、表单抽屉、详情展示等
 *
 * ## [STATE]
 * - **Sheet Root状态**: open和onOpenChange由Radix UI管理
 *   - **open**: boolean（抽屉打开/关闭状态）
 *   - **onOpenChange**: (open: boolean) => void（状态变化回调）
 *   - **defaultOpen**: 初始打开状态（非受控模式）
 * - **sheetVariants**: CVA variants管理side方向样式
 *   - **baseClasses**: fixed.z-50.gap-4.bg-background.p-6.shadow-lg.transition.ease-in-out
 *   - **side variants**:
 *     - **top**: inset-x-0.top-0.border-b（顶部全宽，上边框）
 *     - **bottom**: inset-x-0.bottom-0.border-t（底部全宽，下边框）
 *     - **left**: inset-y-0.left-0.h-full.w-3/4.border-r.sm:max-w-sm（左侧全高，75%宽度，小屏最大384px）
 *     - **right**: inset-y-0.right-0.h-full.w-3/4.border-l.sm:max-w-sm（右侧全高，75%宽度，小屏最大384px）
 *   - **defaultVariants**: { side: 'right' }（默认从右侧滑入）
 * - **SheetContent样式**: sheetVariants({ side })应用
 *   - **data-[state=open/closed]**: Radix UI自动添加（基于open prop）
 *   - **duration-300/500**: 关闭动画300ms，打开动画500ms
 *   - **动画效果**: slide-out-to-[*]/slide-in-from-[*]（根据side方向）
 * - **SheetOverlay样式**: fixed.inset-0.z-50.bg-black/80
 *   - **bg-black/80**: 黑色背景80%不透明度
 *   - **动画效果**: fade-in-0/fade-out-0
 * - **关闭按钮**: absolute.right-4.top-4.rounded-sm.opacity-70
 *   - **Cross2Icon**: h-4.w-4（X图标）
 *   - **sr-only**: "Close"文本仅屏幕阅读器可见
 *   - **hover:opacity-100**: 悬停时完全不透明
 *   - **focus:ring-2**: 聚焦时显示焦点环
 * - **SheetHeader**: flex.flex-col.space-y-2.text-center.sm:text-left（移动端居中，桌面端左对齐）
 * - **SheetFooter**: flex.flex-col-reverse.sm:flex-row.sm:justify-end（移动端反向排列，桌面端右对齐）
 * - **Portal渲染**: SheetPrimitive.Portal渲染到body（脱离DOM层级）
 * - **forwardRef**: React.forwardRef转发ref到Radix UI原语
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Sheet组件组是无状态组件（状态由Radix UI管理）
 * - **ref转发**: React.forwardRef转发ref到Radix UI原语
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有Radix UI Props
 * - **CVA variants**: sheetVariants({ side })根据side prop动态生成样式
 * - **Portal渲染**: SheetPrimitive.Portal渲染到body
 *   - **脱离DOM层级**: 抽屉渲染到body，避免父组件的overflow:hidden或z-index问题
 * - **遮罩层**: SheetOverlay覆盖全屏（fixed.inset-0）
 * - **数据属性**: data-[state=open/closed]由Radix UI自动添加（基于open prop）
 * - **事件处理**: Radix UI处理点击遮罩关闭、点击关闭按钮、Escape键关闭等事件
 * - **动画效果**: CSS transition + Radix UI data属性触发动画（duration-300关闭，duration-500打开）
 * - **关闭按钮**: SheetContent内部包含绝对定位的关闭按钮（Cross2Icon）
 * - **side条件渲染**: sheetVariants CVA根据side prop应用不同方向样式
 */

import * as React from "react"
import * as SheetPrimitive from "@radix-ui/react-dialog"
import { Cross2Icon } from "@radix-ui/react-icons"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const Sheet = SheetPrimitive.Root

const SheetTrigger = SheetPrimitive.Trigger

const SheetClose = SheetPrimitive.Close

const SheetPortal = SheetPrimitive.Portal

const SheetOverlay = React.forwardRef<
  React.ElementRef<typeof SheetPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof SheetPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <SheetPrimitive.Overlay
    className={cn(
      "fixed inset-0 z-50 bg-black/80  data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props}
    ref={ref}
  />
))
SheetOverlay.displayName = SheetPrimitive.Overlay.displayName

const sheetVariants = cva(
  "fixed z-50 gap-4 bg-background p-6 shadow-lg transition ease-in-out data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:duration-300 data-[state=open]:duration-500",
  {
    variants: {
      side: {
        top: "inset-x-0 top-0 border-b data-[state=closed]:slide-out-to-top data-[state=open]:slide-in-from-top",
        bottom:
          "inset-x-0 bottom-0 border-t data-[state=closed]:slide-out-to-bottom data-[state=open]:slide-in-from-bottom",
        left: "inset-y-0 left-0 h-full w-3/4 border-r data-[state=closed]:slide-out-to-left data-[state=open]:slide-in-from-left sm:max-w-sm",
        right:
          "inset-y-0 right-0 h-full w-3/4 border-l data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right sm:max-w-sm",
      },
    },
    defaultVariants: {
      side: "right",
    },
  }
)

interface SheetContentProps
  extends React.ComponentPropsWithoutRef<typeof SheetPrimitive.Content>,
    VariantProps<typeof sheetVariants> {}

const SheetContent = React.forwardRef<
  React.ElementRef<typeof SheetPrimitive.Content>,
  SheetContentProps
>(({ side = "right", className, children, ...props }, ref) => (
  <SheetPortal>
    <SheetOverlay />
    <SheetPrimitive.Content
      ref={ref}
      className={cn(sheetVariants({ side }), className)}
      {...props}
    >
      {children}
      <SheetPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-secondary">
        <Cross2Icon className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </SheetPrimitive.Close>
    </SheetPrimitive.Content>
  </SheetPortal>
))
SheetContent.displayName = SheetPrimitive.Content.displayName

const SheetHeader = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex flex-col space-y-2 text-center sm:text-left",
      className
    )}
    {...props}
  />
)
SheetHeader.displayName = "SheetHeader"

const SheetFooter = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2",
      className
    )}
    {...props}
  />
)
SheetFooter.displayName = "SheetFooter"

const SheetTitle = React.forwardRef<
  React.ElementRef<typeof SheetPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof SheetPrimitive.Title>
>(({ className, ...props }, ref) => (
  <SheetPrimitive.Title
    ref={ref}
    className={cn("text-lg font-semibold text-foreground", className)}
    {...props}
  />
))
SheetTitle.displayName = SheetPrimitive.Title.displayName

const SheetDescription = React.forwardRef<
  React.ElementRef<typeof SheetPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof SheetPrimitive.Description>
>(({ className, ...props }, ref) => (
  <SheetPrimitive.Description
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
))
SheetDescription.displayName = SheetPrimitive.Description.displayName

export {
  Sheet,
  SheetPortal,
  SheetOverlay,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
}