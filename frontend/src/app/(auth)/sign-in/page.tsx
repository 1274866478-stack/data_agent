'use client'

/**
 * # Sign In Page 登录页面
 *
 * ## [MODULE]
 * **文件名**: page.tsx
 * **职责**: 能量脉冲实验室风格的登录页面入口
 * **作者**: Data Agent Team
 * **版本**: 2.0.0
 *
 * ## [INPUT]
 * - 无Props输入
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 登录页面
 *
 * ## [LINK]
 * **上游依赖**:
 * - [next/navigation](https://nextjs.org/docs/app/navigation) - Next.js导航
 * - [@/components/auth/EnergyLabSignIn](../../../components/auth/EnergyLabSignIn.tsx) - 能量脉冲风格登录组件
 *
 * **下游依赖**: 无
 */

import { Suspense } from 'react'
import { EnergyLabSignIn } from '@/components/auth/EnergyLabSignIn'

function SignInWrapper() {
  return <EnergyLabSignIn />
}

export default function SignInPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="text-gray-600 dark:text-gray-400">加载中...</div>
      </div>
    }>
      <SignInWrapper />
    </Suspense>
  )
}
