/**
 * # [APP_LAYOUT] App路由布局组件
 *
 * ## [MODULE]
 * **文件名**: layout.tsx
 * **职责**: 为所有App路由页面提供统一的布局容器和认证保护
 *
 * ## [INPUT]
 * Props:
 * - **children: React.ReactNode** - 子页面内容
 *
 * ## [OUTPUT]
 * UI结构:
 * - **ProtectedRoute包裹**: 确保用户已认证
 * - **Layout组件**: 提供导航栏、侧边栏等通用UI（支持 Modern/Legacy 切换）
 * - **children渲染**: 在布局中渲染子页面内容
 *
 * **上游依赖**:
 * - [../../components/layout/Layout.tsx](../../components/layout/Layout.tsx) - 原有布局组件
 * - [../../components/layout/ModernLayout.tsx](../../components/layout/ModernLayout.tsx) - 现代化布局组件
 * - [../../components/auth/ProtectedRoute.tsx](../../components/auth/ProtectedRoute.tsx) - 认证保护组件
 *
 * **下游依赖**:
 * - 所有 (app) 路由组下的页面组件（作为children）
 *
 * **调用方**:
 * - Next.js App Router (自动应用到 (app) 路由组下的所有页面)
 *   - [chat/page.tsx](chat/page.tsx) - 聊天页面
 *   - [dashboard/page.tsx](dashboard/page.tsx) - 仪表板页面
 *   - [data-sources/page.tsx](data-sources/page.tsx) - 数据源页面
 *   - [documents/page.tsx](documents/page.tsx) - 文档页面
 *
 * ## [STATE]
 * - **认证状态**: 通过ProtectedRoute检查用户登录状态
 * - **布局状态**: Layout组件维护侧边栏、导航栏等状态
 * - **布局选择**: 通过 NEXT_PUBLIC_USE_MODERN_LAYOUT 环境变量控制
 *
 * ## [SIDE-EFFECTS]
 * - 认证检查（ProtectedRoute组件）
 * - 路由重定向（未认证时重定向到登录页）
 */

'use client'

import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Layout } from '@/components/layout/Layout'
import { ModernLayout } from '@/components/layout/ModernLayout'

// 通过环境变量控制布局切换，默认使用现代布局
const useModernLayout = process.env.NEXT_PUBLIC_USE_MODERN_LAYOUT !== 'false'

export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // 根据环境变量选择布局
  const LayoutComponent = useModernLayout ? ModernLayout : Layout

  return (
    <ProtectedRoute>
      <LayoutComponent>{children}</LayoutComponent>
    </ProtectedRoute>
  )
}
