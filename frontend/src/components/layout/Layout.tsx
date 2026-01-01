/**
 * # [LAYOUT] 应用主布局组件
 *
 * ## [MODULE]
 * **文件名**: Layout.tsx
 * **职责**: 应用主布局容器 - 管理侧边栏折叠状态、协调Header和Sidebar组件、渲染主内容区域
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 应用主布局组件
 *
 * ## [INPUT]
 * Props:
 * - **children: React.ReactNode** - 子组件内容（页面内容）
 *
 * ## [OUTPUT]
 * - **Layout组件** - 渲染完整的应用布局
 *   - 左侧：Sidebar组件（可折叠）
 *   - 顶部：Header组件（包含折叠按钮）
 *   - 中间：main元素（渲染children，overflow-y-auto可滚动）
 * - **布局结构**: Flexbox布局（h-screen固定高度，flex-1自适应宽度）
 * - **状态管理**: sidebarCollapsed状态（boolean，控制侧边栏折叠）
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（useState hook）
 * - [./Header.tsx](./Header.tsx) - 头部组件
 * - [./Sidebar.tsx](./Sidebar.tsx) - 侧边栏组件
 *
 * **下游依赖**:
 * - 无（Layout是容器组件）
 *
 * **调用方**:
 * - [../../app/layout.tsx](../../app/layout.tsx) - 根布局
 * - 所有需要包裹在布局中的页面
 *
 * ## [STATE]
 * - **sidebarCollapsed: boolean** - 侧边栏折叠状态（默认false）
 * - **setSidebarCollapsed(boolean)** - 切换折叠状态函数
 * - **布局容器**: div.h-screen.flex.overflow-hidden（固定视口高度）
 * - **侧边栏容器**: Sidebar组件（collapsed状态传入）
 * - **主内容区**: div.flex-1.flex-col.overflow-hidden（自适应宽度）
 * - **Header**: onSidebarToggle回调（切换折叠）
 * - **main**: flex-1.overflow-y-auto.p-6（可滚动内容区）
 *
 * ## [SIDE-EFFECTS]
 * - **状态更新**: setSidebarCollapsed(!sidebarCollapsed)切换折叠状态
 * - **Props传递**: collapsed和onCollapse传递给Sidebar
 * - **Props传递**: onSidebarToggle和sidebarCollapsed传递给Header
 * - **DOM渲染**: 渲染Sidebar、Header、main元素
 * - **Flexbox布局**: 使用flex布局实现响应式布局
 * - **子组件渲染**: children在main元素中渲染
 */

'use client'

import { useState } from 'react'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

interface LayoutProps {
  children: React.ReactNode
}

export function Layout({ children }: LayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className="h-screen flex overflow-hidden">
      <Sidebar
        collapsed={sidebarCollapsed}
        onCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header
          onSidebarToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          sidebarCollapsed={sidebarCollapsed}
        />

        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}