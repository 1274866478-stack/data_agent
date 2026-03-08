'use client'

/**
 * # Login Page 自托管登录页面
 *
 * 自托管认证模式的登录页面
 * 不依赖 Clerk 等第三方服务
 */

import { SelfHostSignIn } from '@/components/auth/SelfHostSignIn'

export default function LoginPage() {
  return <SelfHostSignIn />
}
