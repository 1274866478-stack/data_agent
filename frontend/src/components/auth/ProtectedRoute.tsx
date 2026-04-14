'use client'

/**
 * # ProtectedRoute 受保护路由组件
 *
 * ## [MODULE]
 * **文件名**: ProtectedRoute.tsx
 * **职责**: 路由级别的认证和授权控制，支持普通用户、管理员和功能权限控制
 * **作者**: Data Agent Team
 * **版本**: 1.1.0
 *
 * ## [SIDE-EFFECTS]
 * - ProtectedRoute: 未认证时自动重定向到登录页（公开路径除外）
 * - AdminRoute: 未授权时重定向到 /unauthorized
 * - FeatureGate: 功能不可用时显示fallback或提示信息
 * - 显示加载动画（Loader2）直到认证状态确定
 */

// 公开路径白名单 - 不需要认证即可访问
const PUBLIC_PATHS = ['/ai-assistant', '/sign-in', '/sign-up', '/forgot-password']

import { useEffect, ReactNode, useMemo } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { Loader2 } from 'lucide-react'
import { useAuth } from './AuthContext'

interface ProtectedRouteProps {
  children: ReactNode
  fallback?: ReactNode
  redirectTo?: string
  allowPublic?: boolean
}

export function ProtectedRoute({
  children,
  fallback,
  redirectTo = '/sign-in',
  allowPublic = false
}: ProtectedRouteProps) {
  const { isAuthenticated, loading } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  // 检查当前路径是否为公开路径
  const isPublicPath = useMemo(() => {
    return PUBLIC_PATHS.some(path => pathname === path || pathname.startsWith(path + '/'))
  }, [pathname])

  // 如果是公开路径且allowPublic=true，则跳过认证检查
  const shouldSkipAuth = allowPublic && isPublicPath

  useEffect(() => {
    if (!loading && !isAuthenticated && !shouldSkipAuth) {
      // 未认证且不是公开路径，重定向到登录页面
      router.push(redirectTo)
    }
  }, [isAuthenticated, loading, router, redirectTo, shouldSkipAuth])

  // 加载中显示加载器
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">正在验证身份...</p>
        </div>
      </div>
    )
  }

  // 未认证但有fallback，显示fallback
  if (!isAuthenticated && fallback && !shouldSkipAuth) {
    return <>{fallback}</>
  }

  // 已认证或为公开路径，渲染子组件
  return <>{children}</>
}

interface AdminRouteProps {
  children: ReactNode
  fallback?: ReactNode
}

export function AdminRoute({ children, fallback }: AdminRouteProps) {
  const { user, isAuthenticated } = useAuth()
  const router = useRouter()

  // 检查是否为管理员（这里需要根据实际业务逻辑调整）
  const isAdmin = user?.email?.endsWith('@dataagent.com') ||
                 user?.role === 'admin' ||
                 user?.permissions?.includes('admin')

  useEffect(() => {
    if (isAuthenticated && !isAdmin) {
      router.push('/unauthorized')
    }
  }, [isAuthenticated, isAdmin, router])

  if (!isAuthenticated) {
    return (
      <ProtectedRoute fallback={fallback}>
        {children}
      </ProtectedRoute>
    )
  }

  if (!isAdmin) {
    return fallback || (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <h2 className="text-2xl font-semibold text-destructive">访问被拒绝</h2>
          <p className="text-muted-foreground">您没有权限访问此页面</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}

interface FeatureGateProps {
  children: ReactNode
  feature: string
  fallback?: ReactNode
}

export function FeatureGate({ children, feature, fallback }: FeatureGateProps) {
  const { user, isAuthenticated } = useAuth()

  // 检查用户是否有特定功能的权限
  const hasFeature = () => {
    if (!user || !isAuthenticated) return false

    // 这里可以根据实际业务逻辑实现功能权限检查
    const userFeatures = user.features || []
    const userPermissions = user.permissions || []

    return userFeatures.includes(feature) ||
           userPermissions.includes(`feature:${feature}`) ||
           user.role === 'admin'
  }

  if (!hasFeature()) {
    return fallback || (
      <div className="text-center py-8">
        <h3 className="text-lg font-semibold text-muted-foreground">功能不可用</h3>
        <p className="text-sm text-muted-foreground mt-2">
          此功能需要更高权限或订阅计划
        </p>
      </div>
    )
  }

  return <>{children}</>
}