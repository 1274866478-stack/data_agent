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