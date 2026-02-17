/**
 * # ChatGPTSignInForm ChatGPT 风格登录表单
 *
 * ## [MODULE]
 * **文件名**: ChatGPTSignInForm.tsx
 * **职责**: ChatGPT 风格的登录表单，集成 Clerk 认证（可选）
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 */
'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { OAuthButton } from './OAuthButton'
import { useAuth } from './AuthContext'
import { useAuthStore } from '@/store'
import { cn } from '@/lib/utils'

export function ChatGPTSignInForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [oAuthLoading, setOAuthLoading] = useState<'google' | 'github' | null>(null)
  const [showPasswordInput, setShowPasswordInput] = useState(false)
  const [clerkAvailable, setClerkAvailable] = useState(false)

  const router = useRouter()
  const searchParams = useSearchParams()
  const { login } = useAuth()
  const { setUser, setToken } = useAuthStore()

  // 检查 Clerk 是否可用
  useEffect(() => {
    const checkClerk = () => {
      const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
      const isConfigured = publishableKey && !publishableKey.includes('xxx')
      setClerkAvailable(!!isConfigured && typeof window !== 'undefined' && !!(window as any).Clerk)
    }

    // 延迟检查，等待 Clerk SDK 可能的加载
    const timer = setTimeout(checkClerk, 500)
    return () => clearTimeout(timer)
  }, [])

  // 邮箱验证
  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  // 处理邮箱继续
  const handleEmailContinue = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!email.trim()) {
      setError('请输入邮箱地址')
      return
    }

    if (!validateEmail(email)) {
      setError('请输入有效的邮箱地址')
      return
    }

    setShowPasswordInput(true)
  }

  // 处理邮箱密码登录
  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!email.trim()) {
      setError('请输入邮箱地址')
      return
    }

    if (!validateEmail(email)) {
      setError('请输入有效的邮箱地址')
      return
    }

    if (!password.trim()) {
      setError('请输入密码')
      return
    }

    setIsLoading(true)

    try {
      if (clerkAvailable && typeof window !== 'undefined' && (window as any).Clerk) {
        const clerk = (window as any).Clerk

        await clerk.signIn.create({
          identifier: email,
          password: password,
        })

        const result = await clerk.signIn.authenticate({
          strategy: 'password',
        })

        if (result) {
          const token = await clerk.session?.getToken()
          if (token) {
            await login(token)
            const redirect = searchParams?.get('redirect') || '/'
            router.push(redirect)
          }
        }
      } else {
        // 开发模式：直接设置用户状态，跳过 API 验证
        await new Promise(resolve => setTimeout(resolve, 500))

        const mockUser = {
          id: 'dev-user',
          email: email,
          name: email.split('@')[0],
          tenant_id: 'default_tenant',
        }

        setUser(mockUser)
        setToken('dev-mode-token')
        localStorage.setItem('auth_token', 'dev-mode-token')

        const redirect = searchParams?.get('redirect') || '/'
        router.push(redirect)
      }
    } catch (err: any) {
      const clerkError = err?.errors?.[0]?.message || err?.message || '登录失败，请重试'
      setError(clerkError)
    } finally {
      setIsLoading(false)
    }
  }

  // 处理魔法链接登录
  const handleMagicLink = async () => {
    if (!email.trim() || !validateEmail(email)) {
      setError('请输入有效的邮箱地址')
      return
    }

    setIsLoading(true)
    setError('')

    try {
      if (clerkAvailable && typeof window !== 'undefined' && (window as any).Clerk) {
        const clerk = (window as any).Clerk

        await clerk.signIn.create({
          identifier: email,
        })

        await clerk.signIn.prepareFirstFactor({
          strategy: 'email_link',
          redirectUrl: `${window.location.origin}/verify`,
        })

        setError('请检查您的邮箱以继续登录')
      } else {
        // 开发模式
        await new Promise(resolve => setTimeout(resolve, 1000))
        setError('开发模式：魔法链接功能需要配置 Clerk')
      }
    } catch (err: any) {
      const clerkError = err?.errors?.[0]?.message || err?.message || '发送魔法链接失败'
      setError(clerkError)
    } finally {
      setIsLoading(false)
    }
  }

  // 处理 Google 登录
  const handleGoogleLogin = async () => {
    setOAuthLoading('google')
    setError('')

    if (clerkAvailable && typeof window !== 'undefined' && (window as any).Clerk) {
      try {
        const clerk = (window as any).Clerk
        await clerk.authenticate({
          strategy: 'oauth_google',
          redirectUrl: `${window.location.origin}/`,
        })
      } catch (err: any) {
        setError(err?.message || 'Google 登录失败')
      } finally {
        setOAuthLoading(null)
      }
    } else {
      await new Promise(resolve => setTimeout(resolve, 500))
      setError('开发模式：Google 登录需要配置 Clerk OAuth')
      setOAuthLoading(null)
    }
  }

  // 处理 GitHub 登录
  const handleGitHubLogin = async () => {
    setOAuthLoading('github')
    setError('')

    if (clerkAvailable && typeof window !== 'undefined' && (window as any).Clerk) {
      try {
        const clerk = (window as any).Clerk
        await clerk.authenticate({
          strategy: 'oauth_github',
          redirectUrl: `${window.location.origin}/`,
        })
      } catch (err: any) {
        setError(err?.message || 'GitHub 登录失败')
      } finally {
        setOAuthLoading(null)
      }
    } else {
      await new Promise(resolve => setTimeout(resolve, 500))
      setError('开发模式：GitHub 登录需要配置 Clerk OAuth')
      setOAuthLoading(null)
    }
  }

  return (
    <div className="w-full max-w-[360px] mx-auto space-y-6">
      {/* 标题 */}
      <div className="text-center space-y-1">
        <h1 className="text-2xl font-semibold text-gray-900">Welcome back</h1>
      </div>

      {/* 第三方登录按钮 */}
      <div className="space-y-3">
        <OAuthButton
          provider="google"
          isLoading={oAuthLoading === 'google'}
          onClick={handleGoogleLogin}
        >
          Continue with Google
        </OAuthButton>
        <OAuthButton
          provider="github"
          isLoading={oAuthLoading === 'github'}
          onClick={handleGitHubLogin}
        >
          Continue with GitHub
        </OAuthButton>
      </div>

      {/* 分隔线 */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-gray-200" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-white px-2 text-gray-500">or</span>
        </div>
      </div>

      {/* 邮箱登录表单 */}
      <form onSubmit={showPasswordInput ? handleEmailSubmit : handleEmailContinue} className="space-y-4">
        <div className="space-y-2">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="name@example.com"
            disabled={isLoading}
            className={cn(
              'w-full h-11 px-3',
              'border border-gray-300 rounded-md',
              'text-sm',
              'placeholder:text-gray-400',
              'focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-400',
              'disabled:cursor-not-allowed disabled:opacity-50',
              'transition-colors'
            )}
            autoComplete="email"
          />
        </div>

        {showPasswordInput && (
          <div className="space-y-2">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              disabled={isLoading}
              className={cn(
                'w-full h-11 px-3',
                'border border-gray-300 rounded-md',
                'text-sm',
                'placeholder:text-gray-400',
                'focus:outline-none focus:ring-2 focus:ring-gray-200 focus:border-gray-400',
                'disabled:cursor-not-allowed disabled:opacity-50',
                'transition-colors'
              )}
              autoComplete="current-password"
            />
          </div>
        )}

        {/* 内联错误提示 */}
        {error && (
          <p className={cn(
            'text-xs',
            error.includes('检查您的邮箱') || error.includes('已发送') ? 'text-green-600' : 'text-red-500'
          )}>
            {error}
          </p>
        )}

        {!showPasswordInput ? (
          <>
            <button
              type="submit"
              disabled={isLoading || !email.trim()}
              className={cn(
                'w-full h-10',
                'bg-black text-white',
                'rounded-md',
                'text-sm font-medium',
                'hover:bg-gray-800',
                'focus:outline-none focus:ring-2 focus:ring-gray-300 focus:ring-offset-2',
                'disabled:cursor-not-allowed disabled:opacity-50',
                'disabled:hover:bg-black',
                'transition-colors'
              )}
            >
              {isLoading ? 'Continuing...' : 'Continue'}
            </button>

            <button
              type="button"
              onClick={handleMagicLink}
              disabled={isLoading || !email.trim()}
              className={cn(
                'w-full h-10',
                'bg-white text-black',
                'border border-gray-300',
                'rounded-md',
                'text-sm font-medium',
                'hover:bg-gray-50',
                'focus:outline-none focus:ring-2 focus:ring-gray-300 focus:ring-offset-2',
                'disabled:cursor-not-allowed disabled:opacity-50',
                'transition-colors'
              )}
            >
              Send magic link
            </button>
          </>
        ) : (
          <div className="space-y-3">
            <button
              type="submit"
              disabled={isLoading || !email.trim() || !password.trim()}
              className={cn(
                'w-full h-10',
                'bg-black text-white',
                'rounded-md',
                'text-sm font-medium',
                'hover:bg-gray-800',
                'focus:outline-none focus:ring-2 focus:ring-gray-300 focus:ring-offset-2',
                'disabled:cursor-not-allowed disabled:opacity-50',
                'disabled:hover:bg-black',
                'transition-colors'
              )}
            >
              {isLoading ? 'Signing in...' : 'Continue'}
            </button>

            <button
              type="button"
              onClick={() => {
                setShowPasswordInput(false)
                setPassword('')
                setError('')
              }}
              disabled={isLoading}
              className="w-full text-sm text-gray-500 hover:text-gray-700"
            >
              Back
            </button>
          </div>
        )}
      </form>

      {/* 底部链接 */}
      <div className="text-center text-sm">
        <span className="text-gray-500">Don&apos;t have an account? </span>
        <Link
          href="/sign-up"
          className="text-gray-900 hover:underline font-medium"
        >
          Sign up
        </Link>
      </div>
    </div>
  )
}
