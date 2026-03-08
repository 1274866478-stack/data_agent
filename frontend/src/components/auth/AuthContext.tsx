/**
 * # AuthContext 认证上下文管理
 *
 * ## [MODULE]
 * **文件名**: AuthContext.tsx
 * **职责**: 提供全局认证状态管理和认证操作，支持Clerk和自托管两种模式
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - **children**: ReactNode - 子组件
 * - **token**: string - JWT认证令牌
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - Context Provider组件
 * - **副作用**: 管理localStorage中的token，调用后端API验证用户身份
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [@/store/useAuthStore](../../store/authStore.ts) - 全局认证状态管理
 *
 * **下游依赖**:
 * - [./ProtectedRoute.tsx](./ProtectedRoute.tsx) - 受保护路由组件
 * - [./SignInForm.tsx](./SignInForm.tsx) - 登录表单
 * - [./ClerkProvider.tsx](./ClerkProvider.tsx) - Clerk认证提供者
 *
 * **调用方**:
 * - [../../app/layout.tsx](../../app/layout.tsx) - 根布局
 *
 * ## [STATE]
 * - **user**: any | null - 当前用户信息对象
 * - **token**: string | null - JWT认证令牌
 * - **isAuthenticated**: boolean - 认证状态标志
 * - **loading**: boolean - 认证加载状态
 *
 * ## [SIDE-EFFECTS]
 * - 调用 `/api/v1/auth/me` 验证token并获取用户信息
 * - 调用 `/api/v1/auth/logout` 登出时通知后端
 * - 调用 `/api/v1/auth/verify` 验证token有效性
 * - localStorage读写auth_token
 * - 开发模式下自动设置模拟用户（当无Clerk密钥时)
 */
'use client'

import { createContext, useContext, useEffect, ReactNode } from 'react'
import { useAuthStore } from '@/store'

// 获取认证模式：clerk | selfhost
const getAuthMode = (): string => {
  return process.env.NEXT_PUBLIC_AUTH_MODE || 'clerk'
}

interface AuthContextType {
  user: any | null
  isAuthenticated: boolean
  loading: boolean
  login: (token: string) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const {
    user,
    token,
    isAuthenticated,
    loading,
    setUser,
    setToken,
    setLoading,
    logout: storeLogout
  } = useAuthStore()

  // 设置用户信息和token
  const login = async (token: string) => {
    try {
      setToken(token)
      localStorage.setItem('auth_token', token)

      // 验证token并获取用户信息
      const response = await fetch('/api/v1/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
        setLoading(false) // 登录成功后设置loading为false
      } else {
        throw new Error('Failed to validate token')
      }
    } catch (error) {
      console.error('Login failed:', error)
      logout()
      setLoading(false) // 登录失败后也要设置loading为false
      throw error
    }
  }

  // 登出
  const logout = async () => {
    try {
      if (token) {
        // 调用后端登出API
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        })
      }
    } catch (error) {
      console.error('Logout API call failed:', error)
    } finally {
      // 清除本地状态
      storeLogout()
      localStorage.removeItem('auth_token')
      // 自托管模式：清除所有用户相关数据
      if (getAuthMode() === 'selfhost') {
        localStorage.removeItem('user_id')
        localStorage.removeItem('tenant_id')
        localStorage.removeItem('user_email')
      }
    }
  }

  // 刷新token
  const refreshToken = async () => {
    try {
      if (!token) return

      const response = await fetch('/api/v1/auth/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token }),
      })

      if (!response.ok) {
        throw new Error('Token refresh failed')
      }

      // Token仍然有效，无需刷新
      // 如果需要实现真正的token刷新逻辑，在这里处理
    } catch (error) {
      console.error('Token refresh failed:', error)
      logout()
    }
  }

  useEffect(() => {
    // 页面加载时检查认证状态
    const initAuth = async () => {
      const authMode = getAuthMode()
      const isDevelopmentMode = process.env.NODE_ENV === 'development' ||
                                process.env.NEXT_PUBLIC_ENVIRONMENT === 'development'
      const hasClerkKey = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY

      // === 开发模式：自动设置模拟用户 ===
      if (isDevelopmentMode && authMode === 'clerk' && !hasClerkKey) {
        const mockUser = {
          id: 'anonymous',
          email: 'admin@dataagent.local',
          name: 'Development User',
          tenant_id: 'default_tenant',
        }
        setUser(mockUser)
        setToken('dev-mock-token')
        setLoading(false)
        console.log('🔧 开发模式：使用模拟用户', mockUser)
        return
      }

      // === 自托管模式：从 localStorage 恢复用户 ===
      if (authMode === 'selfhost') {
        const storedToken = localStorage.getItem('auth_token')
        const userId = localStorage.getItem('user_id')
        const tenantId = localStorage.getItem('tenant_id')
        const userEmail = localStorage.getItem('user_email')

        if (storedToken && userId && tenantId) {
          // 有完整的数据，直接设置用户信息
          const restoredUser = {
            id: userId,
            email: userEmail,
            tenant_id: tenantId,
          }
          setUser(restoredUser)
          setToken(storedToken)
          setLoading(false)
          console.log('🔓 自托管模式：已恢复用户会话', restoredUser)
          return
        }
      }

      // === Clerk 模式：验证存储的 token ===
      const storedToken = localStorage.getItem('auth_token')
      if (storedToken) {
        try {
          await login(storedToken)
        } catch (error) {
          console.error('Failed to restore auth session:', error)
          localStorage.removeItem('auth_token')
          setLoading(false)
        }
      } else {
        // 没有token时也要设置loading为false
        setLoading(false)
      }
    }

    initAuth()
  }, [])

  const value: AuthContextType = {
    user,
    isAuthenticated,
    loading,
    login,
    logout,
    refreshToken,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}