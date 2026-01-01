/**
 * # [COLLAPSIBLE] 折叠组件组
 *
 * ## [MODULE]
 * **文件名**: collapsible.tsx
 * **职责**: 提供标准化的折叠组件 - 基于Radix UI Collapsible原语，包含3个子组件，用于可折叠/展开的内容区域
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 折叠组件组
 *
 * ## [INPUT]
 * Props (各子组件的Props extends Radix UI组件Props):
 * - **Collapsible**: Radix UI Root组件的所有Props（open, onOpenChange, defaultOpen, disabled等）
 * - **CollapsibleTrigger**: className?, children（触发按钮）
 * - **CollapsibleContent**: className?, children（折叠内容）
 *
 * ## [OUTPUT]
 * - **Collapsible组件组** - 3个子组件
 *   - **Collapsible**: Root组件（管理折叠/展开状态）
 *   - **CollapsibleTrigger**: 触发按钮（点击切换折叠/展开状态）
 *   - **CollapsibleContent**: 折叠内容（根据open状态显示/隐藏）
 * - **状态管理**: open状态由Radix UI管理（controlled或uncontrolled模式）
 * - **无样式**: Collapsible组件是无样式原语，需要自定义样式
 *
 * **上游依赖**:
 * - [@radix-ui/react-collapsible](https://www.radix-ui.com/primitives/docs/components/collapsible) - Radix UI Collapsible原语
 *
 * **下游依赖**:
 * - 无（Collapsible组件组是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要折叠/展开功能的组件
 * - FAQ列表、长内容折叠、设置面板等
 *
 * ## [STATE]
 * - **Collapsible Root状态**: open和onOpenChange由Radix UI管理
 *   - **open**: boolean（折叠内容打开/关闭状态）
 *   - **onOpenChange**: (open: boolean) => void（状态变化回调）
 *   - **defaultOpen**: 初始打开状态（非受控模式）
 *   - **disabled**: boolean（禁用状态）
 * - **CollapsibleTrigger**: 触发器组件（通常是button）
 *   - **data-state**: Radix UI自动添加data-state属性（'open' | 'closed'）
 *   - **aria-expanded**: 无障碍属性，反映open状态
 * - **CollapsibleContent**: 内容容器
 *   - **data-state**: Radix UI自动添加data-state属性（'open' | 'closed'）
 *   - **hidden**: 当open=false时，Radix UI添加hidden属性
 * - **无样式**: Collapsible组件是无样式原语，不包含任何CSS类
 * - **组合模式**: 需要组合Collapsible、CollapsibleTrigger、CollapsibleContent使用
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Collapsible组件组是无状态组件（状态由Radix UI管理）
 * - **无样式**: 不包含任何CSS类或样式，需要使用自定义样式
 * - **Props透传**: 所有Radix UI Props通过直接赋值传递（Collapsible = CollapsiblePrimitive.Root）
 * - **数据属性**: data-[state=open/closed]由Radix UI自动添加（基于open prop）
 * - **无障碍属性**: aria-expanded、aria-controls等ARIA属性由Radix UI自动管理
 * - **事件处理**: Radix UI处理点击触发器切换状态等事件
 * - **直接导出**: Collapsible = CollapsiblePrimitive.Root（无forwardRef包装）
 */

"use client"

import * as CollapsiblePrimitive from "@radix-ui/react-collapsible"

const Collapsible = CollapsiblePrimitive.Root

const CollapsibleTrigger = CollapsiblePrimitive.CollapsibleTrigger

const CollapsibleContent = CollapsiblePrimitive.CollapsibleContent

export { Collapsible, CollapsibleTrigger, CollapsibleContent }