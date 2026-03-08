'use client'

/**
 * # SelfHostSignIn 自托管登录组件
 *
 * 直接调用后端 /api/v1/auth/login 端点
 * 使用 localStorage 存储 JWT token
 * 不依赖 Clerk 等第三方服务
 */

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { BackgroundGrid } from './BackgroundGrid'
import { ThemeToggle } from './ThemeToggle'
import { Chrome, Github, Loader2, Eye, EyeOff } from 'lucide-react'
import { cn } from '@/lib/utils'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'

export function SelfHostSignIn() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  const router = useRouter()
  const searchParams = useSearchParams()

  // 邮箱验证
  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  // 处理登录
  const handleLogin = async (e: React.FormEvent) => {
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
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email.trim(),
          password: password,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || '登录失败，请检查邮箱和密码')
      }

      // 存储token到localStorage
      localStorage.setItem('auth_token', data.access_token)
      localStorage.setItem('user_id', data.user_id)
      localStorage.setItem('tenant_id', data.tenant_id)
      localStorage.setItem('user_email', data.email)

      // 触发存储事件以更新其他标签页
      window.dispatchEvent(new Event('storage'))

      // 跳转到目标页面或首页
      const redirect = searchParams?.get('redirect') || '/'
      router.push(redirect)
    } catch (err: any) {
      setError(err.message || '登录失败，请重试')
    } finally {
      setIsLoading(false)
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
          {/* 头部 */}
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
              能量脉冲实验室 • Self-Hosted
            </p>
          </div>

          {/* 登录表单 */}
          <form onSubmit={handleLogin} className="w-full space-y-4">
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
                required
              />
              <label htmlFor="email" className="floating-label">
                邮箱地址
              </label>
            </div>

            {/* 密码输入框 */}
            <div className="floating-label-group relative">
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder=" "
                disabled={isLoading}
                className={cn(
                  'floating-label-input energy-input w-full h-12 px-3 rounded-md text-sm pr-10',
                  'placeholder:text-transparent',
                  'focus:outline-none',
                  'disabled:cursor-not-allowed disabled:opacity-50'
                )}
                autoComplete="current-password"
                required
              />
              <label htmlFor="password" className="floating-label">
                密码
              </label>
              {/* 显示/隐藏密码按钮 */}
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                disabled={isLoading}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 disabled:cursor-not-allowed"
              >
                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>

            {/* 错误提示 */}
            {error && (
              <p className="text-xs text-red-500 dark:text-red-400">
                {error}
              </p>
            )}

            {/* 登录按钮 */}
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
                '登录'
              )}
            </button>
          </form>

          {/* 底部注册链接 */}
          <div className="mt-8 pt-6 border-t border-slate-200/50 dark:border-slate-700/50">
            <p className="text-slate-500 dark:text-slate-400 text-sm">
              还没有账号？
              <Link
                href="/register"
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
              系统状态：自托管模式
            </span>
          </div>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
            JWT认证: HS256
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
