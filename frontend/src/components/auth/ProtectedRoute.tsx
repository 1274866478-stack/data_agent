'use client'

import { useEffect, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2 } from 'lucide-react'
import { useAuth } from './AuthContext'

interface ProtectedRouteProps {
  children: ReactNode
  fallback?: ReactNode
  redirectTo?: string
}

export function ProtectedRoute({
  children,
  fallback,
  redirectTo = '/sign-in'
}: ProtectedRouteProps) {
  const { isAuthenticated, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      // 未认证，重定向到登录页面
      router.push(redirectTo)
    }
  }, [isAuthenticated, loading, router, redirectTo])

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

  // 未认证且未提供fallback，则不渲染任何内容（等待重定向）
  if (!isAuthenticated && !fallback) {
    return null
  }

  // 未认证但有fallback，显示fallback
  if (!isAuthenticated && fallback) {
    return <>{fallback}</>
  }

  // 已认证，渲染子组件
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