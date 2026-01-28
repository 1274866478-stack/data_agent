'use client'

/**
 * # EnergyLabSignIn 能量脉冲实验室风格登录组件
 *
 * ## [MODULE]
 * **文件名**: EnergyLabSignIn.tsx
 * **职责**: Tiffany Blue 配色的"能量脉冲实验室"风格登录页面
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
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
 * - [BackgroundGrid](./BackgroundGrid.tsx) - 科技网格背景
 * - [ThemeToggle](./ThemeToggle.tsx) - 主题切换
 * - [AuthContext](./AuthContext.tsx) - 认证上下文
 *
 * **下游依赖**: 无
 */

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { BackgroundGrid } from './BackgroundGrid'
import { ThemeToggle } from './ThemeToggle'
import { useAuth } from './AuthContext'
import { useAuthStore } from '@/store'
import { Chrome, Github, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export function EnergyLabSignIn() {
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
        // 开发模式：直接设置用户状态
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
    <div className="min-h-screen lab-gradient flex items-center justify-center p-4 relative overflow-hidden">
      {/* 背景网格 */}
      <BackgroundGrid />

      {/* 主题切换 */}
      <ThemeToggle />

      {/* 登录卡片容器 */}
      <div className="relative z-10 w-full max-w-md">
        {/* 登录卡片 */}
        <div className="energy-card energy-glass-panel rounded-2xl p-8 shadow-2xl">
          {/* 头部 - 显微镜图标 + 欢迎回来 + 副标题 */}
          <div className="mb-8 text-center">
            <div className="w-16 h-16 bg-primary/20 border border-primary/50 rounded-xl
                        flex items-center justify-center mx-auto microscope-aura mb-4">
              <span className="material-symbols-outlined text-primary text-4xl">
                biotech
              </span>
            </div>
            <h1 className="text-3xl font-bold text-slate-800 dark:text-white mb-2">
              欢迎回来
            </h1>
            <p className="text-slate-500 dark:text-primary/70 text-sm
                       font-medium tracking-widest uppercase">
              能量脉冲实验室 • Security Portal
            </p>
          </div>

          {/* OAuth 按钮 */}
          <div className="w-full space-y-3 mb-8">
            <button
              type="button"
              onClick={handleGoogleLogin}
              disabled={oAuthLoading === 'google'}
              className={cn(
                'energy-oauth-btn w-full h-11 rounded-md font-medium text-sm',
                'flex items-center justify-center gap-3',
                'transition-all duration-200',
                'disabled:cursor-not-allowed disabled:opacity-50'
              )}
            >
              {oAuthLoading === 'google' ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  <Chrome className="h-5 w-5" />
                  <span>Continue with Google</span>
                </>
              )}
            </button>
            <button
              type="button"
              onClick={handleGitHubLogin}
              disabled={oAuthLoading === 'github'}
              className={cn(
                'energy-oauth-btn w-full h-11 rounded-md font-medium text-sm',
                'flex items-center justify-center gap-3',
                'transition-all duration-200',
                'disabled:cursor-not-allowed disabled:opacity-50'
              )}
            >
              {oAuthLoading === 'github' ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  <Github className="h-5 w-5" />
                  <span>Continue with GitHub</span>
                </>
              )}
            </button>
          </div>

          {/* 分隔线 */}
          <div className="w-full flex items-center gap-4 mb-8">
            <div className="flex-1 h-px bg-slate-200 dark:bg-slate-700/50" />
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">
              或者
            </span>
            <div className="flex-1 h-px bg-slate-200 dark:bg-slate-700/50" />
          </div>

          {/* 邮箱登录表单 */}
          <form onSubmit={showPasswordInput ? handleEmailSubmit : handleEmailContinue} className="w-full space-y-4">
            {/* 邮箱输入框 */}
            <div className="floating-label-group">
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder=" "
                disabled={isLoading}
                className={cn(
                  'floating-label-input energy-input w-full h-12 px-3 rounded-md text-sm',
                  'placeholder:text-transparent',
                  'focus:outline-none',
                  'disabled:cursor-not-allowed disabled:opacity-50'
                )}
                autoComplete="email"
              />
              <label htmlFor="email" className="floating-label">
                邮箱地址
              </label>
            </div>

            {/* 密码输入框 */}
            {showPasswordInput && (
              <div className="floating-label-group">
                <input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder=" "
                  disabled={isLoading}
                  className={cn(
                    'floating-label-input energy-input w-full h-12 px-3 rounded-md text-sm',
                    'placeholder:text-transparent',
                    'focus:outline-none',
                    'disabled:cursor-not-allowed disabled:opacity-50'
                  )}
                  autoComplete="current-password"
                />
                <label htmlFor="password" className="floating-label">
                  密码
                </label>
              </div>
            )}

            {/* 内联错误提示 */}
            {error && (
              <p className={cn(
                'text-xs',
                error.includes('检查您的邮箱') || error.includes('已发送')
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-red-500 dark:text-red-400'
              )}>
                {error}
              </p>
            )}

            {!showPasswordInput ? (
              <div className="space-y-3">
                {/* 继续访问按钮 (带光效) */}
                <button
                  type="submit"
                  disabled={isLoading || !email.trim()}
                  className={cn(
                    'energy-btn w-full h-11 rounded-md font-medium text-sm',
                    'flex items-center justify-center',
                    'disabled:cursor-not-allowed disabled:opacity-50'
                  )}
                >
                  {isLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    '继续访问'
                  )}
                </button>

                {/* 发送魔力链接按钮 */}
                <button
                  type="button"
                  onClick={handleMagicLink}
                  disabled={isLoading || !email.trim()}
                  className={cn(
                    'energy-oauth-btn w-full h-11 rounded-md font-medium text-sm',
                    'flex items-center justify-center',
                    'transition-all duration-200',
                    'disabled:cursor-not-allowed disabled:opacity-50'
                  )}
                >
                  {isLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    '发送魔力链接'
                  )}
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {/* 继续按钮 */}
                <button
                  type="submit"
                  disabled={isLoading || !email.trim() || !password.trim()}
                  className={cn(
                    'energy-btn w-full h-11 rounded-md font-medium text-sm',
                    'flex items-center justify-center',
                    'disabled:cursor-not-allowed disabled:opacity-50'
                  )}
                >
                  {isLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    '继续访问'
                  )}
                </button>

                {/* 返回按钮 */}
                <button
                  type="button"
                  onClick={() => {
                    setShowPasswordInput(false)
                    setPassword('')
                    setError('')
                  }}
                  disabled={isLoading}
                  className="w-full text-sm text-slate-500 hover:text-primary transition-colors"
                >
                  返回
                </button>
              </div>
            )}
          </form>

          {/* 底部注册链接 */}
          <div className="mt-8 pt-6 border-t border-slate-200/50 dark:border-slate-700/50">
            <p className="text-slate-500 dark:text-slate-400 text-sm">
              还没有账号？
              <Link
                href="/sign-up"
                className="text-primary hover:text-white
                               hover:bg-primary/80 px-2 py-1 rounded transition-colors ml-1"
              >
                立即注册
              </Link>
            </p>
          </div>
        </div>

        {/* 系统状态指示器 */}
        <div className="mt-6 flex justify-between px-2">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 status-glow-green" />
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
              系统状态：核心稳定
            </span>
          </div>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
            脉冲加密: SECURE-9X
          </div>
        </div>
      </div>

      {/* 右下角 LAB 水印 */}
      <div className="fixed bottom-0 left-0 p-8 pointer-events-none opacity-10">
        <span className="text-[140px] font-black text-primary select-none leading-none">
          LAB
        </span>
      </div>
    </div>
  )
}
