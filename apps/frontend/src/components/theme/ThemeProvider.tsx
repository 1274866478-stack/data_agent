'use client'

import { useEffect, useState } from 'react'
import { useAppStore, getEffectiveTheme } from '@/store/appStore'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false)
  const theme = useAppStore((state) => state.theme)

  // 初始化：标记组件已挂载
  useEffect(() => {
    setMounted(true)
  }, [])

  // 应用主题到 DOM
  useEffect(() => {
    if (!mounted) return

    const root = document.documentElement
    const effectiveTheme = getEffectiveTheme(theme)

    root.classList.remove('light', 'dark')
    root.classList.add(effectiveTheme)
  }, [mounted, theme])

  // 监听系统主题变化
  useEffect(() => {
    if (!mounted || theme !== 'system') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    const handleChange = () => {
      const root = document.documentElement
      root.classList.remove('light', 'dark')
      root.classList.add(mediaQuery.matches ? 'dark' : 'light')
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [mounted, theme])

  return <>{children}</>
}
