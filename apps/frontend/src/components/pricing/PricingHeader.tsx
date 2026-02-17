/**
 * # PricingHeader 算力证书风格顶部导航栏组件
 *
 * ## [MODULE]
 * **文件名**: PricingHeader.tsx
 * **职责**: 算力证书风格的顶部导航栏
 * **作者**: Data Agent Team
 * **版本**: 2.0.0
 *
 * ## [INPUT]
 * - 无Props
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 顶部导航栏组件
 */
'use client'

import Link from 'next/link'

export function PricingHeader() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md bg-[#0a0f0e]/80 border-b border-white/5">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo + 标题 */}
          <div className="flex items-center gap-6">
            {/* Logo SVG */}
            <Link href="/" className="flex items-center gap-3 group">
              <svg
                width="40"
                height="40"
                viewBox="0 0 40 40"
                fill="none"
                className="transition-transform duration-300 group-hover:scale-110"
              >
                {/* 外圈 */}
                <circle
                  cx="20"
                  cy="20"
                  r="18"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  className="text-[#82d9d0]/40"
                />
                {/* 内圈 */}
                <circle
                  cx="20"
                  cy="20"
                  r="12"
                  stroke="currentColor"
                  strokeWidth="1"
                  className="text-[#82d9d0]/60"
                />
                {/* 中心点 */}
                <circle
                  cx="20"
                  cy="20"
                  r="4"
                  fill="currentColor"
                  className="text-[#82d9d0]"
                />
                {/* 装饰点 */}
                <circle
                  cx="20"
                  cy="8"
                  r="1.5"
                  fill="currentColor"
                  className="text-[#82d9d0]"
                />
                <circle
                  cx="20"
                  cy="32"
                  r="1.5"
                  fill="currentColor"
                  className="text-[#82d9d0]"
                />
                <circle
                  cx="8"
                  cy="20"
                  r="1.5"
                  fill="currentColor"
                  className="text-[#82d9d0]"
                />
                <circle
                  cx="32"
                  cy="20"
                  r="1.5"
                  fill="currentColor"
                  className="text-[#82d9d0]"
                />
              </svg>

              {/* 标题组 */}
              <div className="hidden sm:block">
                <h1 className="text-white font-display font-bold text-lg tracking-tight">
                  Data Agent
                </h1>
                <p className="text-white/40 text-xs tracking-wide">
                  智能数据体分析平台
                </p>
              </div>
            </Link>
          </div>

          {/* 导航链接 */}
          <nav className="hidden md:flex items-center gap-1">
            {[
              { href: '/dashboard', label: '控制台' },
              { href: '/pricing', label: '定价' },
              { href: '/docs', label: '文档' },
            ].map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`
                  px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                  ${link.href === '/pricing'
                    ? 'text-[#82d9d0] bg-[#82d9d0]/10'
                    : 'text-white/60 hover:text-white hover:bg-white/5'
                  }
                `}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* 右侧按钮 */}
          <div className="flex items-center gap-3">
            <Link
              href="/sign-in"
              className="hidden sm:inline-flex px-4 py-2 rounded-lg text-sm font-medium
                text-white/60 hover:text-white transition-colors"
            >
              登录
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg
                bg-[#82d9d0] text-[#0a0f0e] text-sm font-bold
                hover:bg-[#82d9d0]/90 transition-colors"
            >
              <span className="hidden sm:inline">进入控制台</span>
              <span className="sm:hidden">控制台</span>
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                className="transition-transform group-hover:translate-x-0.5"
              >
                <path
                  d="M3 8H13M13 8L9 4M13 8L9 12"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </Link>
          </div>
        </div>
      </div>
    </header>
  )
}
