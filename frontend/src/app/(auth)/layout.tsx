/**
 * # [AUTH_LAYOUT] 认证页面布局组件
 *
 * ## [MODULE]
 * **文件名**: layout.tsx
 * **职责**: 为认证相关页面（登录/注册）提供统一的布局，支持能量脉冲实验室风格
 * **作者**: Data Agent Team
 * **版本**: 2.0.0
 *
 * ## [INPUT]
 * Props:
 * - **children: React.ReactNode** - 子页面内容（登录表单或注册表单）
 *
 * ## [OUTPUT]
 * UI组件:
 * - **居中容器**: 白色背景，flex布局
 * - **开发模式**: 没有 Clerk 时也能正常显示 UI
 */

'use client'

import { ReactNode, useEffect, useState } from 'react'

// 扩展 Window 类型以包含 Clerk
declare global {
  interface Window {
    Clerk?: any
  }
}

interface AuthLayoutProps {
  children: ReactNode
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  const [clerkLoaded, setClerkLoaded] = useState(false)
  const [isClerkEnabled, setIsClerkEnabled] = useState(false)
  const [initAttempted, setInitAttempted] = useState(false)

  useEffect(() => {
    const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY

    // 检查是否启用了 Clerk
    if (!publishableKey || publishableKey.startsWith('pk_test_xxx') || publishableKey.includes('xxx')) {
      // Clerk 未配置或使用占位符密钥
      setIsClerkEnabled(false)
      setInitAttempted(true)
      return
    }

    setIsClerkEnabled(true)

    // 动态加载 Clerk SDK
    const loadClerk = async () => {
      try {
        if (typeof window !== 'undefined') {
          // 检查是否已加载
          if (window.Clerk) {
            const clerk = window.Clerk
            await clerk.load({ publishableKey })
            setClerkLoaded(true)
            setInitAttempted(true)
            return
          }

          // 动态加载 Clerk SDK
          const script = document.createElement('script')
          script.src = 'https://js.clerk.dev/v4.72.4/clerk.browser.js'
          script.async = true

          script.onload = async () => {
            try {
              if (window.Clerk) {
                await window.Clerk.load({ publishableKey })
                setClerkLoaded(true)
              }
            } catch (err) {
              console.error('Clerk initialization failed:', err)
            } finally {
              setInitAttempted(true)
            }
          }

          script.onerror = () => {
            console.warn('Clerk SDK loading failed, running in dev mode')
            setInitAttempted(true)
          }

          document.body.appendChild(script)
        }
      } catch (error) {
        console.error('Failed to load Clerk:', error)
        setInitAttempted(true)
      }
    }

    loadClerk()
  }, [])

  // 如果启用了 Clerk 但还没加载完成，显示加载状态
  if (isClerkEnabled && !clerkLoaded && !initAttempted) {
    return (
      <div className="min-h-screen lab-gradient flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="text-sm text-slate-500">加载认证服务中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      {children}
    </div>
  )
}
