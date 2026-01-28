/**
 * # EnergyLabSignUpForm EnergyLab 风格注册表单
 *
 * ## [MODULE]
 * **文件名**: EnergyLabSignUpForm.tsx
 * **职责**: 能量脉冲实验室风格的注册表单，集成 Clerk 认证（可选）
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - 无Props输入
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - EnergyLab 风格的注册表单
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [next/navigation](https://nextjs.org/docs/app/navigation) - Next.js导航
 * - [@/components/auth/ChatGPTSignUpForm](./ChatGPTSignUpForm.tsx) - 复用验证逻辑
 *
 * **下游依赖**: 无
 */
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from './AuthContext'
import { useAuthStore } from '@/store'
import { cn } from '@/lib/utils'

export function EnergyLabSignUpForm() {
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
    <div className="relative z-10 w-full max-w-[480px] px-6 py-12">
      {/* 玻璃态卡片 */}
      <div className="glass-panel-light neon-card-glow rounded-[32px] overflow-hidden relative">
        {/* 流光边框 */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute inset-0 rounded-[32px] bg-gradient-to-r from-transparent via-primary/20 to-transparent animate-[light-run_3s_linear_infinite]" style={{ backgroundSize: '200% 100%' }}></div>
        </div>

        {/* 头部：图标 + 标题 */}
        <div className="text-center pt-20 pb-8 px-10 md:px-14 relative">
          {/* 显微镜图标 */}
          <div className="relative inline-flex items-center justify-center w-24 h-24 mb-10">
            <div className="absolute inset-0 bg-primary/20 blur-2xl rounded-full animate-pulse"></div>
            <div className="relative w-20 h-20 rounded-2xl glass-panel-light flex items-center justify-center border border-primary/30">
              <span className="material-symbols-outlined text-primary text-5xl microscope-aura">biotech</span>
            </div>
          </div>
          <h1 className="text-4xl font-bold text-lab-navy mb-3">注册账号</h1>
          <p className="text-[11px] text-primary/80 uppercase tracking-[0.3em]">
            高能脉冲实验室 · PULSE SECURITY
          </p>
        </div>

        {/* 社交登录按钮 + 表单 */}
        <div className="px-10 md:px-14 pb-16 relative">
          {/* Google 按钮 */}
          <button
            type="button"
            onClick={handleGoogleSignUp}
            disabled={oAuthLoading === 'google'}
            className={cn(
              'social-glass-icon-light w-full h-12 mb-3 flex items-center justify-center gap-3',
              'transition-all duration-300',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {oAuthLoading === 'google' ? (
              <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin"></div>
            ) : (
              <>
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                <span className="text-sm font-medium text-lab-navy/80">使用 Google 继续</span>
              </>
            )}
          </button>

          {/* GitHub 按钮 */}
          <button
            type="button"
            onClick={handleGitHubSignUp}
            disabled={oAuthLoading === 'github'}
            className={cn(
              'social-glass-icon-light w-full h-12 mb-4 flex items-center justify-center gap-3',
              'transition-all duration-300',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {oAuthLoading === 'github' ? (
              <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin"></div>
            ) : (
              <>
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
                <span className="text-sm font-medium text-lab-navy/80">使用 GitHub 继续</span>
              </>
            )}
          </button>

          {/* 分隔线 */}
          <div className="relative flex items-center justify-center mb-4">
            <div className="border-t border-primary/20 w-full"></div>
            <span className="absolute bg-white/80 px-3 text-xs text-primary/60 uppercase tracking-wider">
              或
            </span>
          </div>

          {/* 注册表单 */}
          <form onSubmit={handleEmailSubmit} className="space-y-4">
            {/* 邮箱输入 */}
            <div className="relative">
              <div className={cn(
                'input-instrument-light relative rounded-xl overflow-hidden',
                'transition-all duration-500'
              )}>
                <div className="absolute left-4 top-1/2 -translate-y-1/2 z-10">
                  <span className="material-symbols-outlined text-primary/60 text-xl">alternate_email</span>
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="邮箱地址"
                  disabled={isLoading}
                  className={cn(
                    'w-full h-12 pl-12 pr-4 bg-white/60',
                    'border border-slate-200 rounded-xl',
                    'text-sm text-lab-navy placeholder:text-lab-navy/40',
                    'focus:outline-none focus:border-primary/70',
                    'transition-all duration-500',
                    'disabled:cursor-not-allowed disabled:opacity-50'
                  )}
                  autoComplete="email"
                />
              </div>
            </div>

            {/* 密码输入 */}
            <div className="relative">
              <div className={cn(
                'input-instrument-light relative rounded-xl overflow-hidden',
                'transition-all duration-500'
              )}>
                <div className="absolute left-4 top-1/2 -translate-y-1/2 z-10">
                  <span className="material-symbols-outlined text-primary/60 text-xl">lock</span>
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="密码（至少 8 位）"
                  disabled={isLoading}
                  className={cn(
                    'w-full h-12 pl-12 pr-4 bg-white/60',
                    'border border-slate-200 rounded-xl',
                    'text-sm text-lab-navy placeholder:text-lab-navy/40',
                    'focus:outline-none focus:border-primary/70',
                    'transition-all duration-500',
                    'disabled:cursor-not-allowed disabled:opacity-50'
                  )}
                  autoComplete="new-password"
                />
              </div>
            </div>

            {/* 确认密码输入 */}
            <div className="relative">
              <div className={cn(
                'input-instrument-light relative rounded-xl overflow-hidden',
                'transition-all duration-500'
              )}>
                <div className="absolute left-4 top-1/2 -translate-y-1/2 z-10">
                  <span className="material-symbols-outlined text-primary/60 text-xl">security</span>
                </div>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="确认密码"
                  disabled={isLoading}
                  className={cn(
                    'w-full h-12 pl-12 pr-4 bg-white/60',
                    'border border-slate-200 rounded-xl',
                    'text-sm text-lab-navy placeholder:text-lab-navy/40',
                    'focus:outline-none focus:border-primary/70',
                    'transition-all duration-500',
                    'disabled:cursor-not-allowed disabled:opacity-50'
                  )}
                  autoComplete="new-password"
                />
              </div>
            </div>

            {/* 错误/成功提示 */}
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-xl">
                <span className="material-symbols-outlined text-red-500 text-lg">error</span>
                <p className="text-xs text-red-600">{error}</p>
              </div>
            )}
            {success && (
              <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-xl">
                <span className="material-symbols-outlined text-green-500 text-lg">check_circle</span>
                <p className="text-xs text-green-600">{success}</p>
              </div>
            )}

            {/* 服务条款开关 */}
            <div className="flex items-center gap-3 py-2">
              <button
                type="button"
                onClick={() => setAgreedToTerms(!agreedToTerms)}
                disabled={isLoading}
                className={cn(
                  'relative w-12 h-6 rounded-full transition-all duration-300',
                  'focus:outline-none focus:ring-2 focus:ring-primary/50',
                  agreedToTerms ? 'bg-primary' : 'bg-slate-300',
                  'disabled:cursor-not-allowed disabled:opacity-50'
                )}
              >
                <span className={cn(
                  'absolute top-1 w-4 h-4 bg-white rounded-full shadow-sm',
                  'transition-all duration-300',
                  agreedToTerms ? 'left-7' : 'left-1'
                )}></span>
              </button>
              <label className="text-xs text-lab-navy/70 cursor-pointer">
                我同意<Link href="/terms" className="text-primary hover:underline mx-1">服务条款</Link>
                和<Link href="/privacy" className="text-primary hover:underline mx-1">隐私政策</Link>
              </label>
            </div>

            {/* 立即注册按钮 */}
            <button
              type="submit"
              disabled={isLoading || !email.trim() || !password.trim() || !confirmPassword.trim() || !agreedToTerms}
              className={cn(
                'fast-shimmer btn-blinding-glow w-full h-12 rounded-xl',
                'text-white font-semibold text-sm tracking-wide',
                'transition-all duration-300',
                'hover:scale-[1.02] active:scale-[0.98]',
                'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2',
                'disabled:cursor-not-allowed disabled:opacity-50',
                'disabled:hover:scale-100'
              )}
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  创建中...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <span className="material-symbols-outlined text-lg">bolt</span>
                  立即注册
                </span>
              )}
            </button>
          </form>

          {/* 底部链接 */}
          <div className="text-center mt-6 pt-4 border-t border-primary/10">
            <span className="text-sm text-lab-navy/60">已有账号？</span>
            <Link
              href="/sign-in"
              className="text-sm font-semibold text-primary hover:text-primary/80 ml-1 transition-colors"
            >
              立即登录
            </Link>
          </div>
        </div>
      </div>

      {/* 系统状态 */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-4 px-4 py-2 bg-white/40 backdrop-blur-md rounded-full border border-primary/20">
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-green-500 status-glow-green"></div>
          <span className="text-[10px] text-lab-navy/60 uppercase tracking-wider">System Online</span>
        </div>
        <div className="w-px h-3 bg-primary/20"></div>
        <span className="text-[10px] text-lab-navy/60 uppercase tracking-wider">v2.0.4</span>
      </div>
    </div>
  )
}
