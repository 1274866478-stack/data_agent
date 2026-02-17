/**
 * # PricingFooter 技术风格页脚组件
 *
 * ## [MODULE]
 * **文件名**: PricingFooter.tsx
 * **职责**: 技术风格的页面页脚
 * **作者**: Data Agent Team
 * **版本**: 2.0.0
 *
 * ## [INPUT]
 * - 无Props
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 页脚组件
 */
'use client'

import Link from 'next/link'

export function PricingFooter() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t border-white/5 py-12 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Logo + 描述 */}
          <div className="md:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <svg
                width="32"
                height="32"
                viewBox="0 0 40 40"
                fill="none"
              >
                <circle
                  cx="20"
                  cy="20"
                  r="18"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  className="text-[#82d9d0]/40"
                />
                <circle
                  cx="20"
                  cy="20"
                  r="12"
                  stroke="currentColor"
                  strokeWidth="1"
                  className="text-[#82d9d0]/60"
                />
                <circle
                  cx="20"
                  cy="20"
                  r="4"
                  fill="currentColor"
                  className="text-[#82d9d0]"
                />
              </svg>
              <span className="text-white font-display font-bold text-lg">
                Data Agent
              </span>
            </div>
            <p className="text-white/40 text-sm max-w-sm leading-relaxed">
              新一代智能数据体分析平台，帮助企业从数据中提取洞察，
              加速决策流程。
            </p>
          </div>

          {/* 产品链接 */}
          <div>
            <h4 className="pricing-tech-label text-white/60 mb-4">
              产品
            </h4>
            <ul className="space-y-2">
              {['定价', '文档', 'API 参考', '更新日志'].map((item) => (
                <li key={item}>
                  <Link
                    href="#"
                    className="pricing-footer-link text-sm inline-block"
                  >
                    {item}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* 法律链接 */}
          <div>
            <h4 className="pricing-tech-label text-white/60 mb-4">
              法律
            </h4>
            <ul className="space-y-2">
              {['隐私政策', '服务条款', 'Cookie 政策', 'SLA'].map((item) => (
                <li key={item}>
                  <Link
                    href="#"
                    className="pricing-footer-link text-sm inline-block"
                  >
                    {item}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* 底部状态栏 */}
        <div className="pt-8 border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-4">
          {/* 系统状态 */}
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
              </span>
              <span className="text-white/40 text-xs">
                所有系统正常运行
              </span>
            </div>
            <div className="hidden sm:flex items-center gap-2 text-white/30 text-xs">
              <span>v4.2.0</span>
              <span>•</span>
              <span>Build 2025.01.28</span>
            </div>
          </div>

          {/* 版权信息 */}
          <p className="text-white/30 text-xs">
            © {currentYear} Data Agent. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  )
}
