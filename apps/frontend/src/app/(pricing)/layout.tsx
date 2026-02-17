'use client'

/**
 * # Pricing 路由组专用布局
 *
 * ## [MODULE]
 * **文件名**: layout.tsx
 * **职责**: Pricing 页面全屏显示布局，不受 ModernLayout 影响
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - children: React.ReactNode - 子页面内容
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 直接渲染子页面，实现全屏效果
 *
 * ## [NOTES]
 * - 不使用 ProtectedRoute，允许未登录用户访问
 * - 不使用 ModernLayout，实现全屏显示
 * - PricingPageV2 已包含完整的 Header、Hero、Cards、Table、Footer
 */

export default function PricingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
