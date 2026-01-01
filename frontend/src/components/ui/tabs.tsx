/**
 * # [TABS] 标签页组件组
 *
 * ## [MODULE]
 * **文件名**: tabs.tsx
 * **职责**: 提供标准化的标签页组件组 - 基于Radix UI Tabs原语，包含4个子组件，支持激活状态和内容切换
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 标签页组件组
 *
 * ## [INPUT]
 * Props (各子组件的Props extends Radix UI组件Props):
 * - **Tabs**: Radix UI Root组件的所有Props（defaultValue, value, onValueChange, orientation等）
 * - **TabsList**: className?, children（TabsTrigger集合）
 * - **TabsTrigger**: className?, children, value（必需，标识符）
 * - **TabsContent**: className?, children, value（必需，标识符）
 *
 * ## [OUTPUT]
 * - **Tabs组件组** - 4个子组件
 *   - **Tabs**: Root组件（管理value和onValueChange状态）
 *   - **TabsList**: 标签列表容器（inline-flex.h-9.items-center.justify-center.rounded-lg.bg-muted.p-1.text-muted-foreground）
 *   - **TabsTrigger**: 标签触发按钮（inline-flex.items-center.justify-center.whitespace-nowrap.rounded-md.px-3.py-1.text-sm.font-medium）
 *   - **TabsContent**: 标签内容容器（mt-2，包含focus ring）
 * - **激活状态**: data-[state=active]:bg-background.data-[state=active]:text-foreground.data-[state=active]:shadow
 * - **focus状态**: focus-visible:outline-none.focus-visible:ring-2.focus-visible:ring-ring.focus-visible:ring-offset-2
 * - **禁用状态**: disabled:pointer-events-none.disabled:opacity-50
 * - **forwardRef**: 所有组件支持ref转发到Radix UI原语
 * - **displayName**: 所有组件设置displayName（用于调试）
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（forwardRef）
 * - [@radix-ui/react-tabs](https://www.radix-ui.com/primitives/docs/components/tabs) - Radix UI Tabs原语
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Tabs组件组是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要标签页切换的组件
 * - 设置页面、分类内容、多视图切换、向导流程等
 *
 * ## [STATE]
 * - **Tabs Root状态**: value和onValueChange由Radix UI管理
 *   - **defaultValue**: 初始激活的标签值
 *   - **value**: 当前激活的标签值（受控模式）
 *   - **onValueChange**: 标签切换回调函数
 *   - **orientation**: 标签方向（'horizontal' | 'vertical'，默认'horizontal'）
 * - **TabsList样式**: inline-flex.h-9.items-center.justify-center.rounded-lg.bg-muted.p-1.text-muted-foreground
 *   - **h-9**: 36px固定高度
 *   - **rounded-lg**: 大圆角（8px）
 *   - **bg-muted**: 次要背景色（灰色背景）
 *   - **p-1**: 4px padding（为TabsTrigger留空间）
 * - **TabsTrigger样式**: inline-flex.items-center.justify-center.whitespace-nowrap.rounded-md.px-3.py-1.text-sm.font-medium.ring-offset-background.transition-all
 *   - **whitespace-nowrap**: 文本不换行
 *   - **px-3.py-1**: 水平12px，垂直4px padding
 *   - **ring-offset-background**: ring-offset偏移效果
 *   - **transition-all**: 所有属性过渡动画
 * - **TabsTrigger激活状态**: data-[state=active]:bg-background.data-[state=active]:text-foreground.data-[state=active]:shadow
 *   - **bg-background**: 激活时背景色变为页面背景色（白色）
 *   - **text-foreground**: 激活时文字色变为前景色（黑色）
 *   - **shadow**: 激活时显示阴影（浮起效果）
 * - **TabsContent样式**: mt-2.ring-offset-background.focus-visible:outline-none.focus-visible:ring-2.focus-visible:ring-ring.focus-visible:ring-offset-2
 *   - **mt-2**: 顶部8px margin（与TabsList间距）
 *   - **focus ring**: focus-visible时显示ring
 * - **数据属性**: data-[state], data-[orientation], data-[disabled]控制样式
 * - **forwardRef**: React.forwardRef转发ref到Radix UI原语
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Tabs组件组是无状态组件（状态由Radix UI管理）
 * - **ref转发**: React.forwardRef转发ref到Radix UI原语
 * - **类名合并**: cn(baseClasses, className)合并类名
 * - **Props透传**: {...props}传递所有Radix UI Props
 * - **数据属性**: data-[state], data-[orientation], data-[disabled]控制样式
 * - **事件处理**: Radix UI处理点击、键盘导航（方向键、Home、End）等事件
 * - **动画效果**: CSS transition-all触发TabsTrigger的背景色、文字色、阴影变化动画
 */

'use client'

import * as React from 'react'
import * as TabsPrimitive from '@radix-ui/react-tabs'

import { cn } from '@/lib/utils'

const Tabs = TabsPrimitive.Root

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      'inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground',
      className
    )}
    {...props}
  />
))
TabsList.displayName = TabsPrimitive.List.displayName

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow',
      className
    )}
    {...props}
  />
))
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      'mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
      className
    )}
    {...props}
  />
))
TabsContent.displayName = TabsPrimitive.Content.displayName

export { Tabs, TabsList, TabsTrigger, TabsContent }
