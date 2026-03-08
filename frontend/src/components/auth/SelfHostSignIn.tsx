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
import { Loader2, Eye, EyeOff } from 'lucide-react'

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

      if (response.ok) {
        // 保存 JWT token
        localStorage.setItem('auth_token', data.access_token)
        localStorage.setItem('user_id', data.user_id)
        localStorage.setItem('tenant_id', data.tenant_id)
        localStorage.setItem('user_email', data.email)

        // 触发存储事件以更新其他标签页
        window.dispatchEvent(new Event('storage'))

        // 跳转到目标页面或首页
        const redirect = searchParams?.get('redirect') || '/'
        router.push(redirect)
      } else {
        setError(data.detail || '登录失败，请检查邮箱和密码')
      }
    } catch (err: any) {
      setError(err.message || '登录失败，请重试')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
          {/* 头部 */}
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              登录
            </h1>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              Insight Agent - 自托管模式
            </p>
          </div>

          {/* 登录表单 */}
          <form onSubmit={handleLogin} className="space-y-4">
            {/* 邮箱输入框 */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                邮箱地址
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                disabled={isLoading}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                autoComplete="email"
                required
              />
            </div>

            {/* 密码输入框 */}
            <div className="relative">
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                密码
              </label>
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="•••••••••"
                disabled={isLoading}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 dark:bg-gray-700 dark:border-gray-600 dark:text-white pr-10"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                disabled={isLoading}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:cursor-not-allowed"
              >
                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>

            {/* 错误提示 */}
            {error && (
              <p className="text-sm text-red-500 dark:text-red-400">
                {error}
              </p>
            )}

            {/* 登录按钮 */}
            <button
              type="submit"
              disabled={isLoading || !email.trim() || !password.trim()}
              className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  登录中...
                </span>
              ) : (
                '登录'
              )}
            </button>

            {/* 注册链接 */}
            <p className="text-center text-sm text-gray-500 dark:text-gray-400">
              还没有账号？{' '}
              <Link href="/register" className="text-blue-600 hover:text-blue-500 font-medium">
                立即注册
              </Link>
            </p>
          </form>
        </div>

        {/* 返回首页 */}
        <div className="mt-4 text-center">
          <Link href="/" className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">
            ← 返回首页
          </Link>
        </div>
      </div>
    </div>
  )
}
