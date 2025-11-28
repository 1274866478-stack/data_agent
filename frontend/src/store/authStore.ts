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