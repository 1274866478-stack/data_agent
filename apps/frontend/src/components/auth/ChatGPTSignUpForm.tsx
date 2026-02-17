/**
 * # ChatGPTSignUpForm ChatGPT 风格注册表单
 *
 * ## [MODULE]
 * **文件名**: ChatGPTSignUpForm.tsx
 * **职责**: ChatGPT 风格的注册表单，集成 Clerk 认证（可选）
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 */
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { OAuthButton } from './OAuthButton'
import { useAuth } from './AuthContext'
import { useAuthStore } from '@/store'
import { cn } from '@/lib/utils'

export function ChatGPTSignUpForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [agreedToTerms, setAgreedToTerms] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [oAuthLoading, setOAuthLoading] = useState<'google' | 'github' | null>(null)
  const [clerkAvailable, setClerkAvailable] = useState(false)

  const router = useRouter()
  const { login } = useAuth()
  const { setUser, setToken } = useAuthStore()

  // 检查 Clerk 是否可用
  useEffect(() => {
    const checkClerk = () => {
      const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
      const isConfigured = publishableKey && !publishableKey.includes('xxx')
      setClerkAvailable(!!isConfigured && typeof window !== 'undefined' && !!(window as any).Clerk)
    }

    const timer = setTimeout(checkClerk, 500)
    return () => clearTimeout(timer)
  }, [])

  // 邮箱验证
  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  // 密码验证
  const validatePassword = (password: string): { valid: boolean; message?: string } => {
    if (password.length < 8) {
      return { valid: false, message: '密码至少需要8个字符' }
    }
    return { valid: true }
  }

  // 处理邮箱注册
  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    // 验证邮箱
    if (!email.trim()) {
      setError('请输入邮箱地址')
      return
    }

    if (!validateEmail(email)) {
      setError('请输入有效的邮箱地址')
      return
    }

    // 验证密码
    const passwordValidation = validatePassword(password)
    if (!passwordValidation.valid) {
      setError(passwordValidation.message || '密码格式不正确')
      return
    }

    // 验证确认密码
    if (password !== confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }

    // 验证服务条款
    if (!agreedToTerms) {
      setError('请同意服务条款和隐私政策')
      return
    }

    setIsLoading(true)

    try {
      if (clerkAvailable && typeof window !== 'undefined' && (window as any).Clerk) {
        const clerk = (window as any).Clerk

        await clerk.signUp.create({
          emailAddress: email,
          password: password,
        })

        await clerk.signUp.prepareEmailAddressVerification({
          strategy: 'email_link',
          redirectUrl: `${window.location.origin}/`,
        })

        setSuccess('请检查您的邮箱以验证账户')
      } else {
        // 开发模式：模拟注册成功后自动登录
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

        // 注册成功后跳转到首页
        router.push('/')
      }
    } catch (err: any) {
      const clerkError = err?.errors?.[0]?.message || err?.message || '注册失败，请重试'
      setError(clerkError)
    } finally {
      setIsLoading(false)
    }
  }

  // 处理 Google 注册
  const handleGoogleSignUp = async () => {
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
        setError(err?.message || 'Google 注册失败')
      } finally {
        setOAuthLoading(null)
      }
    } else {
      await new Promise(resolve => setTimeout(resolve, 500))
      setError('开发模式：Google 注册需要配置 Clerk OAuth')
      setOAuthLoading(null)
    }
  }

  // 处理 GitHub 注册
  const handleGitHubSignUp = async () => {
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
        setError(err?.message || 'GitHub 注册失败')
      } finally {
        setOAuthLoading(null)
      }
    } else {
      await new Promise(resolve => setTimeout(resolve, 500))
      setError('开发模式：GitHub 注册需要配置 Clerk OAuth')
      setOAuthLoading(null)
    }
  }

  return (
    <div className="w-full max-w-[360px] mx-auto space-y-6">
      {/* 标题 */}
      <div className="text-center space-y-1">
        <h1 className="text-2xl font-semibold text-gray-900">Sign up</h1>
        <p className="text-sm text-gray-500">to continue to ChatBI</p>
      </div>

      {/* 第三方登录按钮 */}
      <div className="space-y-3">
        <OAuthButton
          provider="google"
          isLoading={oAuthLoading === 'google'}
          onClick={handleGoogleSignUp}
        >
          Continue with Google
        </OAuthButton>
        <OAuthButton
          provider="github"
          isLoading={oAuthLoading === 'github'}
          onClick={handleGitHubSignUp}
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

      {/* 邮箱注册表单 */}
      <form onSubmit={handleEmailSubmit} className="space-y-4">
        {/* 邮箱输入 */}
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

        {/* 密码输入 */}
        <div className="space-y-2">
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password (min. 8 characters)"
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
            autoComplete="new-password"
          />
        </div>

        {/* 确认密码输入 */}
        <div className="space-y-2">
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm password"
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
            autoComplete="new-password"
          />
        </div>

        {/* 内联错误/成功提示 */}
        {error && (
          <p className="text-xs text-red-500">{error}</p>
        )}
        {success && (
          <p className="text-xs text-green-600">{success}</p>
        )}

        {/* 服务条款复选框 */}
        <div className="flex items-start gap-2">
          <input
            type="checkbox"
            id="terms"
            checked={agreedToTerms}
            onChange={(e) => setAgreedToTerms(e.target.checked)}
            disabled={isLoading}
            className={cn(
              'mt-0.5 h-4 w-4',
              'border border-gray-300 rounded',
              'text-black focus:ring-black',
              'disabled:cursor-not-allowed disabled:opacity-50'
            )}
          />
          <label
            htmlFor="terms"
            className="text-xs text-gray-500 leading-tight cursor-pointer"
          >
            I agree to the{' '}
            <Link href="/terms" className="underline hover:text-gray-700">
              Terms of Service
            </Link>{' '}
            and{' '}
            <Link href="/privacy" className="underline hover:text-gray-700">
              Privacy Policy
            </Link>
          </label>
        </div>

        <button
          type="submit"
          disabled={isLoading || !email.trim() || !password.trim() || !confirmPassword.trim() || !agreedToTerms}
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
          {isLoading ? 'Creating account...' : 'Continue'}
        </button>
      </form>

      {/* 底部链接 */}
      <div className="text-center text-sm">
        <span className="text-gray-500">Already have an account? </span>
        <Link
          href="/sign-in"
          className="text-gray-900 hover:underline font-medium"
        >
          Sign in
        </Link>
      </div>
    </div>
  )
}
