/**
 * # [AUTH_STORE] 认证状态管理Store
 *
 * ## [MODULE]
 * **文件名**: authStore.ts
 * **职责**: 管理用户认证状态、JWT Token持久化、用户信息刷新和登录状态检查，集成Zustand状态管理和localStorage持久化
 *
 * ## [INPUT]
 * Props (无 - Zustand Store):
 * - 初始从localStorage恢复持久化状态
 * - 接收外部JWT token和用户信息
 *
 * ## [OUTPUT]
 * Store:
 * - **user: User | null** - 当前用户信息
 * - **token: string | null** - JWT认证令牌
 * - **isAuthenticated: boolean** - 认证状态
 * - **loading: boolean** - 加载状态
 * - **error: string | null** - 错误信息
 * Actions:
 * - setUser(user) - 设置用户信息
 * - setToken(token) - 设置Token并同步localStorage
 * - setLoading(loading) - 设置加载状态
 * - setError(error) - 设置错误信息
 * - logout() - 登出并清除状态
 * - checkAuth() - 验证Token有效性
 * - refreshUserInfo() - 刷新用户信息
 *
 * **上游依赖**:
 * - [zustand](https://github.com/pmndrs/zustand) - 状态管理库
 * - [zustand/middleware](https://github.com/pmndrs/zustand#persisting-store-data) - persist中间件
 *
 * **下游依赖**:
 * - 无（Store是叶子状态管理模块）
 *
 * **调用方**:
 * - [../app/layout.tsx](../app/layout.tsx) - 根布局组件
 * - [../lib/api-client.ts](../lib/api-client.ts) - API客户端（获取token）
 * - 所有需要认证的页面和组件
 *
 * ## [STATE]
 * - **持久化字段**: token, user, isAuthenticated (存储到localStorage 'auth-store')
 * - **恢复策略**: 从localStorage恢复后自动设置loading=false
 * - **Token同步**: Token变化时自动同步到localStorage 'auth_token' key
 *
 * ## [SIDE-EFFECTS]
 * - localStorage操作 (读写auth_token)
 * - API调用 (/api/v1/auth/verify, /api/v1/auth/me)
 * - 网络请求 (验证token有效性)
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  tenant_id: string
  email?: string
  first_name?: string
  last_name?: string
  full_name?: string
  is_verified?: boolean
  profile_image_url?: string
  permissions?: string[]
  features?: string[]
  role?: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  loading: boolean
  error: string | null

  // Actions
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  logout: () => void
  checkAuth: () => Promise<void>
  refreshUserInfo: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      loading: true,
      error: null,

      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setToken: (token) => {
        set({ token })
        // 同时保存到localStorage的auth_token key，供API客户端使用
        if (typeof window !== 'undefined') {
          if (token) {
            localStorage.setItem('auth_token', token)
          } else {
            localStorage.removeItem('auth_token')
          }
        }
      },
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),

      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          error: null,
        })
      },

      checkAuth: async () => {
        const { token, setLoading, setUser, logout } = get()
        setLoading(true)

        try {
          if (!token) {
            setLoading(false)
            return
          }

          // 验证token有效性
          const response = await fetch('/api/v1/auth/verify', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token }),
          })

          if (response.ok) {
            const data = await response.json()
            if (data.valid && data.user_info) {
              // 获取完整用户信息
              const userResponse = await fetch('/api/v1/auth/me', {
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json',
                },
              })

              if (userResponse.ok) {
                const userData = await userResponse.json()
                setUser(userData)
              } else {
                setUser(data.user_info as User)
              }
            } else {
              logout()
            }
          } else {
            logout()
          }
        } catch (error) {
          console.error('Auth check failed:', error)
          logout()
        } finally {
          setLoading(false)
        }
      },

      refreshUserInfo: async () => {
        const { token, setUser, setError } = get()

        if (!token) {
          setError('No authentication token')
          return
        }

        try {
          const response = await fetch('/api/v1/auth/me', {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
          })

          if (response.ok) {
            const userData = await response.json()
            setUser(userData)
            setError(null)
          } else {
            setError('Failed to refresh user information')
          }
        } catch (error) {
          console.error('Failed to refresh user info:', error)
          setError('Network error while refreshing user information')
        }
      },
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        // hydration 完成后，设置 loading 为 false
        if (state) {
          state.setLoading(false)
        }
      },
    }
  )
)

// 导出便捷的hooks
export const useUser = () => {
  const { user } = useAuthStore()
  return user
}

export const useTenantId = () => {
  const { user } = useAuthStore()
  return user?.tenant_id
}

export const useIsAuthenticated = () => {
  const { isAuthenticated, loading } = useAuthStore()
  return { isAuthenticated, loading }
}