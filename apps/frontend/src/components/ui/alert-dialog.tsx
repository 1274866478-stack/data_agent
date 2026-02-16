/**
 * # [ALERT DIALOG] 警告对话框组件组
 *
 * ## [MODULE]
 * **文件名**: alert-dialog.tsx
 * **职责**: 提供标准化的警告对话框组件 - 基于Radix UI AlertDialog原语，包含11个子组件，用于中断式确认对话框
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 警告对话框组件组
 *
 * ## [INPUT]
 * Props (各子组件的Props extends Radix UI组件Props):
 * - **AlertDialog**: Radix UI Root组件的所有Props（open, onOpenChange, defaultOpen等）
 * - **AlertDialogTrigger**: className?, children（触发按钮）
 * - **AlertDialogContent**: className?
 * - **AlertDialogHeader**: className?, children
 * - **AlertDialogFooter**: className?, children
 * - **AlertDialogTitle**: className?, children
 * - **AlertDialogDescription**: className?, children
 * - **AlertDialogAction**: className?（继承buttonVariants）
 * - **AlertDialogCancel**: className?（继承buttonVariants outline）
 *
 * ## [OUTPUT]
 * - **AlertDialog组件组** - 11个子组件
 *   - **AlertDialog**: Root组件（管理对话框打开/关闭状态）
 *   - **AlertDialogTrigger**: 触发按钮（点击打开对话框）
 *   - **AlertDialogPortal**: Portal容器（渲染到body）
 *   - **AlertDialogOverlay**: 遮罩层（fixed.inset-0.z-50.bg-black/80，半透明黑色背景）
 *   - **AlertDialogContent**: 对话框内容（fixed.left-[50%].top-[50%].translate-x-[-50%].translate-y-[-50%]）
 *   - **AlertDialogHeader**: 头部容器（flex.flex-col.space-y-2.text-center.sm:text-left）
 *   - **AlertDialogFooter**: 底部容器（flex.flex-col-reverse.sm:flex-row.sm:justify-end）
 *   - **AlertDialogTitle**: 标题（text-lg.font-semibold）
 *   - **AlertDialogDescription**: 描述（text-sm.text-muted-foreground）
 *   - **AlertDialogAction**: 确认按钮（继承buttonVariants默认样式）
 *   - **AlertDialogCancel**: 取消按钮（继承buttonVariants outline，mt-2.sm:mt-0）
 * - **居中定位**: left-[50%].top-[50%].translate-x-[-50%].translate-y-[-50%]（绝对居中）
 * - **动画效果**: animate-in/out, fade-in/out, zoom-in/out, slide-in-from-left-1/2, slide-in-from-top-[48%]
 * - **遮罩层**: AlertDialogOverlay（bg-black/80，80%不透明度黑色）
 * - **forwardRef**: 所有组件支持ref转发到Radix UI原语
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@radix-ui/react-alert-dialog](https://www.radix-ui.com/primitives/docs/components/alert-dialog) - Radix UI AlertDialog原语
 * - [@/components/ui/button](./button.tsx) - Button组件的buttonVariants（AlertDialogAction和Cancel复用）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（AlertDialog组件组是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要警告确认对话框的组件
 * - 删除确认、操作撤销、危险操作确认等
 *
 * ## [STATE]
 * - **AlertDialog Root状态**: open和onOpenChange由Radix UI管理
 *   - **open**: boolean（对话框打开/关闭状态）
 *   - **onOpenChange**: (open: boolean) => void（状态变化回调）
 *   - **defaultOpen**: 初始打开状态（非受控模式）
 * - **AlertDialogContent样式**: fixed.left-[50%].top-[50%].z-50.grid.w-full.max-w-lg.translate-x-[-50%].translate-y-[-50%].gap-4.border.bg-background.p-6.shadow-lg.duration-200
 *   - **fixed.inset-0**: 固定定位，覆盖全屏
 *   - **left-[50%].top-[50%]**: 左上角在中心点
 *   - **translate-x-[-50%].translate-y-[-50%]**: 向左上平移自身50%宽度/高度，实现居中
 *   - **max-w-lg**: 最大宽度32rem（512px）
 *   - **sm:rounded-lg**: 小屏幕以上中等圆角
 *   - **动画效果**: animate-in/out, fade-in/out, zoom-in/out, slide-in-from-left-1/2, slide-in-from-top-[48%]
 * - **AlertDialogOverlay样式**: fixed.inset-0.z-50.bg-black/80
 *   - **bg-black/80**: 黑色背景80%不透明度（rgba(0,0,0,0.8)）
 *   - **动画效果**: fade-in-0/fade-out-0（淡入淡出）
 * - **AlertDialogAction**: 继承buttonVariants()默认样式（bg-primary.text-primary-foreground）
 * - **AlertDialogCancel**: 继承buttonVariants({ variant: 'outline' })，mt-2.sm:mt-0（移动端上下排列，桌面端左右排列）
 * - **AlertDialogHeader**: flex.flex-col.space-y-2.text-center.sm:text-left（移动端居中，桌面端左对齐）
 * - **AlertDialogFooter**: flex.flex-col-reverse.sm:flex-row.sm:justify-end（移动端反向排列，桌面端右对齐）
 * - **Portal渲染**: AlertDialogPrimitive.Portal渲染到body（脱离DOM层级）
 * - **forwardRef**: React.forwardRef转发ref到Radix UI原语
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: AlertDialog组件组是无状态组件（状态由Radix UI管理）
 * - **ref转发**: React.forwardRef转发ref到Radix UI原语
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有Radix UI Props
 * - **Portal渲染**: AlertDialogPrimitive.Portal渲染到body
 *   - **脱离DOM层级**: 对话框渲染到body，避免父组件的overflow:hidden或z-index问题
 * - **遮罩层**: AlertDialogOverlay覆盖全屏（fixed.inset-0）
 * - **数据属性**: data-[state=open/closed]由Radix UI自动添加（基于open prop）
 * - **事件处理**: Radix UI处理点击遮罩关闭、Escape键关闭等事件
 * - **动画效果**: CSS transition + Radix UI data属性触发动画
 * - **居中定位**: left-[50%].top-[50%].translate-x-[-50%].translate-y-[-50%]
 * - **buttonVariants复用**: AlertDialogAction和Cancel复用button.tsx的buttonVariants
 */

'use client'

import * as React from 'react'
import * as AlertDialogPrimitive from '@radix-ui/react-alert-dialog'

import { buttonVariants } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const AlertDialog = AlertDialogPrimitive.Root

const AlertDialogTrigger = AlertDialogPrimitive.Trigger

const AlertDialogPortal = AlertDialogPrimitive.Portal

const AlertDialogOverlay = React.forwardRef<
  React.ElementRef<typeof AlertDialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <AlertDialogPrimitive.Overlay
    className={cn(
      'fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
      className
    )}
    {...props}
    ref={ref}
  />
))
AlertDialogOverlay.displayName = AlertDialogPrimitive.Overlay.displayName

const AlertDialogContent = React.forwardRef<
  React.ElementRef<typeof AlertDialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Content>
>(({ className, ...props }, ref) => (
  <AlertDialogPortal>
    <AlertDialogOverlay />
    <AlertDialogPrimitive.Content
      ref={ref}
      className={cn(
        'fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg md:w-full',
        className
      )}
      {...props}
    />
  </AlertDialogPortal>
))
AlertDialogContent.displayName = AlertDialogPrimitive.Content.displayName

const AlertDialogHeader = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      'flex flex-col space-y-2 text-center sm:text-left',
      className
    )}
    {...props}
  />
)
AlertDialogHeader.displayName = 'AlertDialogHeader'

const AlertDialogFooter = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      'flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2',
      className
    )}
    {...props}
  />
)
AlertDialogFooter.displayName = 'AlertDialogFooter'

const AlertDialogTitle = React.forwardRef<
  React.ElementRef<typeof AlertDialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <AlertDialogPrimitive.Title
    ref={ref}
    className={cn('text-lg font-semibold', className)}
    {...props}
  />
))
AlertDialogTitle.displayName = AlertDialogPrimitive.Title.displayName

const AlertDialogDescription = React.forwardRef<
  React.ElementRef<typeof AlertDialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <AlertDialogPrimitive.Description
    ref={ref}
    className={cn('text-sm text-muted-foreground', className)}
    {...props}
  />
))
AlertDialogDescription.displayName =
  AlertDialogPrimitive.Description.displayName

const AlertDialogAction = React.forwardRef<
  React.ElementRef<typeof AlertDialogPrimitive.Action>,
  React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Action>
>(({ className, ...props }, ref) => (
  <AlertDialogPrimitive.Action
    ref={ref}
    className={cn(buttonVariants(), className)}
    {...props}
  />
))
AlertDialogAction.displayName = AlertDialogPrimitive.Action.displayName

const AlertDialogCancel = React.forwardRef<
  React.ElementRef<typeof AlertDialogPrimitive.Cancel>,
  React.ComponentPropsWithoutRef<typeof AlertDialogPrimitive.Cancel>
>(({ className, ...props }, ref) => (
  <AlertDialogPrimitive.Cancel
    ref={ref}
    className={cn(
      buttonVariants({ variant: 'outline' }),
      'mt-2 sm:mt-0',
      className
    )}
    {...props}
  />
))
AlertDialogCancel.displayName = AlertDialogPrimitive.Cancel.displayName

export {
  AlertDialog,
  AlertDialogPortal,
  AlertDialogOverlay,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogAction,
  AlertDialogCancel,
}