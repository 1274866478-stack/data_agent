'use client'

/**
 * # ThemeToggle 主题切换组件
 *
 * ## [MODULE]
 * **文件名**: ThemeToggle.tsx
 * **职责**: 能量脉冲实验室风格的深色/浅色模式切换按钮
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - 无Props输入
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 主题切换按钮组件
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [@/store/appStore](../../store/appStore.ts) - 应用状态管理
 *
 * **下游依赖**:
 * - [EnergyLabSignIn.tsx](./EnergyLabSignIn.tsx) - 登录页面
 */

import { useEffect, useState } from 'react'
import { useAppStore, getEffectiveTheme } from '@/store/appStore'

export function ThemeToggle() {
  const theme = useAppStore((state) => state.theme)
  const setTheme = useAppStore((state) => state.setTheme)
  const [mounted, setMounted] = useState(false)
  const [effectiveTheme, setEffectiveTheme] = useState<'light' | 'dark'>('light')

  // 避免服务端渲染不匹配
  useEffect(() => {
    setMounted(true)
    setEffectiveTheme(getEffectiveTheme(theme))
  }, [theme])

  // 监听系统主题变化
  useEffect(() => {
    if (theme !== 'system') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    const handleChange = () => {
      setEffectiveTheme(mediaQuery.matches ? 'dark' : 'light')
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme])

  if (!mounted) {
    return null
  }

  const isDark = effectiveTheme === 'dark'

  const handleToggle = () => {
    setTheme(isDark ? 'light' : 'dark')
  }

  return (
    <button
      onClick={handleToggle}
      className="fixed top-6 right-6 z-50 p-3 rounded-full border border-primary/30
                 bg-white/20 dark:bg-black/20 backdrop-blur-md
                 flex items-center justify-center transition-all hover:bg-primary/10
                 hover:scale-110 active:scale-95
                 shadow-lg hover:shadow-primary/20"
      aria-label={isDark ? '切换到浅色模式' : '切换到深色模式'}
    >
      {isDark ? (
        // 浅色模式图标 - 太阳
        <span className="material-symbols-outlined text-primary text-xl">
          light_mode
        </span>
      ) : (
        // 深色模式图标 - 月亮
        <span className="material-symbols-outlined text-primary text-xl">
          dark_mode
        </span>
      )}
    </button>
  )
}
