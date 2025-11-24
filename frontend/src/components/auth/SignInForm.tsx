'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2 } from 'lucide-react'
import { useAuth } from './AuthContext'

export function SignInForm() {
  const [error, setError] = useState('')
  const [clerkError, setClerkError] = useState('')
  const router = useRouter()
  const { login, isAuthenticated } = useAuth()

  useEffect(() => {
    // 如果已认证，重定向到主页
    if (isAuthenticated) {
      router.push('/')
    }
  }, [isAuthenticated, router])

  useEffect(() => {
    // 初始化Clerk登录表单
    const initClerkSignIn = async () => {
      try {
        if (typeof window !== 'undefined' && window.Clerk) {
          const clerk = window.Clerk

          // 创建登录表单容器
          const signInContainer = document.getElementById('clerk-sign-in')

          if (signInContainer && !signInContainer.hasChildNodes()) {
            try {
              await clerk.load({
                publishableKey: process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
              })

              // 渲染Clerk登录表单
              clerk.mountSignIn(signInContainer, {
                appearance: {
                  elements: {
                    rootBox: "mx-auto",
                    card: "shadow-none",
                  }
                },
                redirectUrl: `${window.location.origin}/`,
                afterSignInUrl: `${window.location.origin}/`,
                signUpUrl: '/sign-up'
              })

              // 监听登录成功事件
              clerk.addListener('sign-in.completed', async (session: any) => {
                try {
                  const token = await session.getToken()
                  await login(token)
                  router.push('/')
                } catch (error) {
                  console.error('Login completed but token handling failed:', error)
                  setError('登录成功，但会话处理失败')
                }
              })

              clerk.addListener('sign-in.failed', (error: any) => {
                console.error('Clerk sign in failed:', error)
                setClerkError(error.message || '登录失败')
              })

            } catch (clerkError) {
              console.error('Clerk initialization failed:', clerkError)
              setClerkError('认证服务初始化失败，请刷新页面重试')
            }
          }
        }
      } catch (error) {
        console.error('Failed to initialize Clerk:', error)
        setClerkError('认证服务加载失败')
      }
    }

    initClerkSignIn()

    // 清理函数
    return () => {
      if (typeof window !== 'undefined' && window.Clerk) {
        window.Clerk.removeListener('sign-in.completed')
        window.Clerk.removeListener('sign-in.failed')
      }
    }
  }, [login, router])

  const handleManualLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')

    const formData = new FormData(e.currentTarget)
    const email = formData.get('email') as string
    const password = formData.get('password') as string

    try {
      // 这里可以实现备用的手动登录逻辑
      setError('请使用上方的Clerk登录表单')
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败')
    }
  }

  return (
    <div className="space-y-6">
      {/* Clerk 登录表单 */}
      <div className="space-y-4">
        <div className="text-center">
          <h2 className="text-2xl font-semibold">欢迎回来</h2>
          <p className="text-muted-foreground mt-2">
            使用您的账户登录到 Data Agent 平台
          </p>
        </div>

        {/* Clerk 登录容器 */}
        <div id="clerk-sign-in" className="w-full">
          {/* Clerk 将在这里渲染登录表单 */}
        </div>

        {/* Clerk 错误显示 */}
        {clerkError && (
          <Alert variant="destructive">
            <AlertDescription>{clerkError}</AlertDescription>
          </Alert>
        )}
      </div>

      {/* 分隔线 */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">
            或者
          </span>
        </div>
      </div>

      {/* 备用登录表单 */}
      <Card className="border-dashed">
        <CardContent className="pt-6">
          <form onSubmit={handleManualLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">邮箱地址</Label>
              <Input
                id="email"
                name="email"
                type="email"
                placeholder="your@email.com"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                name="password"
                type="password"
                placeholder="输入您的密码"
                required
              />
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Button type="submit" className="w-full" variant="outline">
              使用邮箱密码登录（开发模式）
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="text-center text-sm">
        <span className="text-muted-foreground">还没有账户？ </span>
        <Link href="/sign-up" className="text-primary hover:underline font-medium">
          立即注册
        </Link>
      </div>
    </div>
  )
}