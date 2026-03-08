'use client'

/**
 * # Register Page 自托管注册页面
 *
 * 自托管认证模式的注册页面
 * 不依赖 Clerk 等第三方服务
 */

import { SelfHostSignUp } from '@/components/auth/SelfHostSignUp'

export default function RegisterPage() {
  return <SelfHostSignUp />
}
