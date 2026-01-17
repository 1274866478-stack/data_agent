/**
 * # [AUTH_LAYOUT] 认证页面布局组件
 *
 * ## [MODULE]
 * **文件名**: layout.tsx
 * **职责**: 为认证相关页面（登录/注册）提供统一的居中布局和品牌展示
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * Props:
 * - **children: React.ReactNode** - 子页面内容（登录表单或注册表单）
 *
 * ## [OUTPUT]
 * UI组件:
 * - **居中容器**: flex布局，垂直水平居中
 * - **品牌展示**: Data Agent V4标题和简介
 * - **最大宽度**: max-w-md限制内容宽度
 * - **背景**: muted背景色
 *
 * ## [LINK]
 * **上游依赖**:
 * - 无（纯布局组件）
 *
 * **下游依赖**:
 * - [./sign-in/page.tsx](./sign-in/page.tsx) - 登录页面
 * - [./sign-up/page.tsx](./sign-up/page.tsx) - 注册页面
 *
 * **调用方**:
 * - Next.js路由系统 (认证页面组布局)
 *
 * ## [STATE]
 * - 无（纯展示组件）
 *
 * ## [SIDE-EFFECTS]
 * - 无（纯展示组件）
 */

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-muted">
      <div className="max-w-md w-full space-y-8 p-8">
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-bold text-foreground">
            智能数据Agent V4
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            多租户 SaaS 数据智能平台
          </p>
        </div>
        {children}
      </div>
    </div>
  )
}