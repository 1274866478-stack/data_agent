/**
 * # SignUpForm 用户注册表单
 *
 * ## [MODULE]
 * **文件名**: SignUpForm.tsx
 * **职责**: 提供Clerk集成的注册界面，展示服务特性和注册入口
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - 无Props输入，组件内部管理状态
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 完整的注册界面（Clerk表单 + 服务介绍 + 服务条款）
 * - **副作用**: 调用Clerk SDK注册，成功后调用AuthContext.login()并重定向
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [next/navigation](https://nextjs.org/docs/app/navigation) - Next.js导航
 * - [next/link](https://nextjs.org/docs/app/linking) - Next.js链接
 * - [@/components/ui/*](../ui/) - UI基础组件（Button, Input, Label, Card, Alert, Checkbox）
 * - [./AuthContext.tsx](./AuthContext.tsx) - 认证上下文
 *
 * **下游依赖**:
 * - 无直接下游组件
 *
 * **调用方**:
 * - [../../app/(auth)/sign-up/page.tsx](../../app/(auth)/sign-up/page.tsx) - 注册页面
 *
 * ## [STATE]
 * - **error**: string - 注册错误信息
 * - **clerkError**: string - Clerk SDK的错误信息
 *
 * ## [SIDE-EFFECTS]
 * - 动态加载Clerk SDK并挂载注册表单到 `#clerk-sign-up` DOM节点
 * - 监听Clerk的 `sign-up.completed` 和 `sign-up.failed` 事件
 * - 注册成功后获取token并调用AuthContext.login()
 * - 展示四大服务特性卡片（安全认证、即时可用、智能分析、灵活配置）
 * - 组件卸载时清理Clerk事件监听器
 */
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useAuth } from './AuthContext'

export function SignUpForm() {
  const [error, setError] = useState('')
  const [clerkError, setClerkError] = useState('')
  const router = useRouter()
  const { login } = useAuth()

  useEffect(() => {
    // 初始化Clerk注册表单
    const initClerkSignUp = async () => {
      try {
        if (typeof window !== 'undefined' && window.Clerk) {
          const clerk = window.Clerk

          // 创建注册表单容器
          const signUpContainer = document.getElementById('clerk-sign-up')

          if (signUpContainer && !signUpContainer.hasChildNodes()) {
            try {
              await clerk.load({
                publishableKey: process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
              })

              // 渲染Clerk注册表单
              clerk.mountSignUp(signUpContainer, {
                appearance: {
                  elements: {
                    rootBox: "mx-auto",
                    card: "shadow-none",
                  }
                },
                redirectUrl: `${window.location.origin}/`,
                afterSignUpUrl: `${window.location.origin}/`,
                signInUrl: '/sign-in'
              })

              // 监听注册成功事件
              clerk.addListener('sign-up.completed', async (session: any) => {
                try {
                  const token = await session.getToken()
                  await login(token)
                  router.push('/')
                } catch (error) {
                  console.error('Sign up completed but token handling failed:', error)
                  setError('注册成功，但会话处理失败')
                }
              })

              clerk.addListener('sign-up.failed', (error: any) => {
                console.error('Clerk sign up failed:', error)
                setClerkError(error.message || '注册失败')
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

    initClerkSignUp()

    // 清理函数
    return () => {
      if (typeof window !== 'undefined' && window.Clerk) {
        window.Clerk.removeListener('sign-up.completed')
        window.Clerk.removeListener('sign-up.failed')
      }
    }
  }, [login, router])

  return (
    <div className="space-y-6">
      {/* Clerk 注册表单 */}
      <div className="space-y-4">
        <div className="text-center">
          <h2 className="text-2xl font-semibold">创建账户</h2>
          <p className="text-muted-foreground mt-2">
            注册您的 智能数据Agent 账户，开始智能数据探索之旅
          </p>
        </div>

        {/* Clerk 注册容器 */}
        <div id="clerk-sign-up" className="w-full">
          {/* Clerk 将在这里渲染注册表单 */}
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
            服务说明
          </span>
        </div>
      </div>

      {/* 服务介绍卡片 */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border-dashed">
          <CardContent className="pt-6">
            <h3 className="font-semibold mb-2">🔒 安全认证</h3>
            <p className="text-sm text-muted-foreground">
              使用业界标准的Clerk认证服务，确保您的账户安全
            </p>
          </CardContent>
        </Card>

        <Card className="border-dashed">
          <CardContent className="pt-6">
            <h3 className="font-semibold mb-2">🚀 即时可用</h3>
            <p className="text-sm text-muted-foreground">
              注册后立即获得完整的智能数据分析功能
            </p>
          </CardContent>
        </Card>

        <Card className="border-dashed">
          <CardContent className="pt-6">
            <h3 className="font-semibold mb-2">📊 智能分析</h3>
            <p className="text-sm text-muted-foreground">
              集成先进的AI技术，让数据分析变得简单高效
            </p>
          </CardContent>
        </Card>

        <Card className="border-dashed">
          <CardContent className="pt-6">
            <h3 className="font-semibold mb-2">🔧 灵活配置</h3>
            <p className="text-sm text-muted-foreground">
              支持多种数据源，自定义分析模型
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 服务条款 */}
      <div className="text-center text-xs text-muted-foreground space-y-1">
        <p>
          注册即表示您同意我们的{' '}
          <Link href="/terms" className="hover:underline">
            服务条款
          </Link>{' '}
          和{' '}
          <Link href="/privacy" className="hover:underline">
            隐私政策
          </Link>
        </p>
        <p>
          已有账户？{' '}
          <Link href="/sign-in" className="text-primary hover:underline font-medium">
            立即登录
          </Link>
        </p>
      </div>
    </div>
  )
}