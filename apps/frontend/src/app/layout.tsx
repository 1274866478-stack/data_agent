/**
 * # [ROOT_LAYOUT] 根布局组件
 *
 * ## [MODULE]
 * **文件名**: layout.tsx
 * **职责**: 提供应用根布局，集成Clerk认证Provider、字体配置和开发模式认证支持
 *
 * ## [INPUT]
 * Props:
 * - **children: React.ReactNode** - 子页面或组件内容
 *
 * ## [OUTPUT]
 * - **布局结构**: ClerkProvider/AuthProvider 包裹的 HTML 结构
 * - **字体配置**: Inter 字体应用到整个应用
 * - **元数据**: 页面标题和描述
 * - **认证模式**:
 *   - 生产模式: 使用ClerkProvider
 *   - 开发模式: 使用AuthProvider (无需Clerk)
 *   - 配置错误: 显示错误提示页面
 *
 * **上游依赖**:
 * - [../components/auth/ClerkProvider.tsx](../components/auth/ClerkProvider.tsx) - Clerk认证Provider
 * - [../components/auth/AuthContext.tsx](../components/auth/AuthContext.tsx) - 开发模式认证Provider
 * - [globals.css](./globals.css) - 全局样式
 * - next/font/google - Google字体 (Inter)
 *
 * **下游依赖**:
 * - 所有应用页面和组件 (通过children)
 *
 * **调用方**:
 * - Next.js App Router (自动应用此布局到所有页面)
 *
 * ## [STATE]
 * - **环境变量检测**: 读取 NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY 和 NODE_ENV
 * - **认证模式选择**: 根据环境变量选择合适的Provider
 * - **全局字体**: Inter字体配置
 *
 * ## [SIDE-EFFECTS]
 * - 读取环境变量 (NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY, NODE_ENV, NEXT_PUBLIC_ENVIRONMENT)
 * - 全局字体注入 (Inter字体)
 * - Clerk SDK初始化 (通过ClerkProviderWrapper)
 */

import './globals.css'
import { Fira_Sans, Fira_Code } from 'next/font/google'
import { ClerkProviderWrapper } from '@/components/auth/ClerkProvider'
import { AuthProvider } from '@/components/auth/AuthContext'
import { ThemeProvider } from '@/components/theme'

/**
 * Fira Sans - 主要正文字体，适合数据密集型界面
 * Fira Code - 代码和等宽字体，用于数据展示
 */
const firaSans = Fira_Sans({
  subsets: ['latin'],
  variable: '--font-fira-sans',
  display: 'swap',
  weight: ['300', '400', '500', '600', '700'],
})

const firaCode = Fira_Code({
  subsets: ['latin'],
  variable: '--font-fira-code',
  display: 'swap',
  weight: ['400', '500', '600'],
})

export const metadata = {
  title: '智能数据Agent V4 - Multi-tenant SaaS Platform',
  description: 'Intelligent data analysis platform for modern businesses',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const clerkPublishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
  // 支持 NODE_ENV 和 NEXT_PUBLIC_ENVIRONMENT 两种方式判断开发模式
  const isDevelopmentMode = process.env.NODE_ENV === 'development' ||
                            process.env.NEXT_PUBLIC_ENVIRONMENT === 'development'

  return (
    <html lang="zh-CN" suppressHydrationWarning className={`${firaSans.variable} ${firaCode.variable}`}>
      <body className="font-sans antialiased">
        <ThemeProvider>
          {clerkPublishableKey ? (
            <ClerkProviderWrapper publishableKey={clerkPublishableKey}>
              {children}
            </ClerkProviderWrapper>
          ) : isDevelopmentMode ? (
            // 开发模式：不需要 Clerk 认证
            <AuthProvider>
              {children}
            </AuthProvider>
          ) : (
            // 生产模式：必须配置 Clerk
            <div className="min-h-screen flex items-center justify-center bg-background">
              <div className="text-center space-y-4">
                <h1 className="text-2xl font-bold text-destructive">配置错误</h1>
                <p className="text-muted-foreground">
                  缺少 Clerk 配置，请设置 NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY 环境变量
                </p>
                <p className="text-sm text-muted-foreground">
                  如需开发模式，请联系开发团队
                </p>
              </div>
            </div>
          )}
        </ThemeProvider>
      </body>
    </html>
  )
}