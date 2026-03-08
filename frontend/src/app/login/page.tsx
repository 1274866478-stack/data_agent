'use client'

/**
 * # Login Page 自托管登录页面
 *
 * 自托管认证模式的登录页面
 * 不依赖 Clerk 等第三方服务
 */

import { Suspense } from 'react'
import { SelfHostSignIn } from '@/components/auth/SelfHostSignIn'

function SignInWrapper() {
  return <SelfHostSignIn />
}

export default function LoginPage() {
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
