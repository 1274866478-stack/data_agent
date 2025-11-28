'use client'

import { createContext, useContext, useEffect, ReactNode } from 'react'
import { useAuthStore } from '@/store'

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
      // 开发模式：自动设置模拟用户
      if (process.env.NODE_ENV === 'development' && !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
        const mockUser = {
          id: 'dev-user-001',
          email: 'dev@dataagent.local',
          name: 'Development User',
          tenant_id: 'dev-tenant-001',
        }
        setUser(mockUser)
        setToken('dev-mock-token')
        setLoading(false) // 关键修复：设置loading为false
        console.log('🔧 开发模式：使用模拟用户', mockUser)
        return
      }

      const storedToken = localStorage.getItem('auth_token')

      if (storedToken) {
        try {
          await login(storedToken)
        } catch (error) {
          console.error('Failed to restore auth session:', error)
          localStorage.removeItem('auth_token')
          setLoading(false) // 恢复会话失败后设置loading为false
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