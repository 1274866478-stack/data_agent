/**
 * # ClerkProviderWrapper Clerk认证服务包装器
 *
 * ## [MODULE]
 * **文件名**: ClerkProvider.tsx
 * **职责**: 动态加载Clerk认证服务库，管理认证状态初始化
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - **children**: ReactNode - 子组件
 * - **publishableKey**: string - Clerk公开密钥
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 带加载状态的Provider包装器
 * - **副作用**: 动态加载Clerk浏览器SDK，触发认证检查
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [./AuthContext.tsx](./AuthContext.tsx) - 认证上下文
 * - [@/store/useAuthStore](../../store/authStore.ts) - 认证状态管理
 *
 * **下游依赖**:
 * - 无直接下游组件
 *
 * **调用方**:
 * - [../../app/layout.tsx](../../app/layout.tsx) - 根布局
 *
 * ## [STATE]
 * - **clerkLoaded**: boolean - Clerk SDK加载完成状态
 *
 * ## [SIDE-EFFECTS]
 * - 动态插入script标签加载Clerk浏览器SDK (v4.72.4)
 * - SDK加载完成后调用checkAuth()触发认证状态检查
 * - 显示加载动画直到SDK加载完成
 */
'use client'

import { ReactNode, useEffect, useState } from 'react'
import { AuthProvider } from './AuthContext'
import { useAuthStore } from '@/store'

interface ClerkProviderProps {
  children: ReactNode
  publishableKey: string
}

// 扩展Window类型以包含Clerk
declare global {
  interface Window {
    Clerk?: any
  }
}

export function ClerkProviderWrapper({ children, publishableKey }: ClerkProviderProps) {
  const [clerkLoaded, setClerkLoaded] = useState(false)
  const { checkAuth } = useAuthStore()

  useEffect(() => {
    // 动态加载Clerk
    const loadClerk = async () => {
      try {
        // 检查Clerk是否已加载
        if (typeof window !== 'undefined' && !window.Clerk) {
          // 动态加载Clerk
          const script = document.createElement('script')
          script.src = 'https://js.clerk.dev/v4.72.4/clerk.browser.js'
          script.async = true
          script.onload = () => {
            setClerkLoaded(true)
          }
          document.body.appendChild(script)
        } else {
          setClerkLoaded(true)
        }
      } catch (error) {
        console.error('Failed to load Clerk:', error)
        setClerkLoaded(false)
      }
    }

    loadClerk()
  }, [])

  useEffect(() => {
    if (clerkLoaded) {
      // 检查认证状态
      checkAuth()
    }
  }, [clerkLoaded, checkAuth])

  if (!clerkLoaded) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <AuthProvider>
      {children}
    </AuthProvider>
  )
}