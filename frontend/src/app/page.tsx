/**
 * # [HOME_PAGE] 应用首页组件
 *
 * ## [MODULE]
 * **文件名**: page.tsx
 * **职责**: 应用根路径首页，自动重定向到主仪表板
 *
 * ## [INPUT]
 * Props (无): Next.js页面组件无需props
 *
 * ## [OUTPUT]
 * - **路由重定向**: 自动将用户重定向到 /dashboard
 *
 * **上游依赖**:
 * - next/navigation - Next.js导航模块
 *
 * **下游依赖**:
 * - [dashboard/page.tsx](./(app)/dashboard/page.tsx) - 仪表板页面（重定向目标）
 *
 * **调用方**:
 * - Next.js App Router (访问根路径 / 时调用)
 *
 * ## [STATE]
 * - **无状态**: 纯函数组件，只执行重定向逻辑
 *
 * ## [SIDE-EFFECTS]
 * - 客户端路由重定向（使用next/navigation的redirect）
 */

import { redirect } from 'next/navigation'

export default function Home() {
  redirect('/dashboard')
}