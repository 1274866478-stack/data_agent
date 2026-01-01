/**
 * # [APP_STORE] 应用全局状态管理Store
 *
 * ## [MODULE]
 * **文件名**: appStore.ts
 * **职责**: 应用全局状态管理 - 加载状态、错误处理、主题切换
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 应用全局状态管理Store
 *
 * ## [INPUT]
 * Props (无 - Zustand Store):
 * - loading: boolean - 加载状态
 * - error: string | null - 错误信息
 * - theme: 'light' | 'dark' - 主题模式
 *
 * ## [OUTPUT]
 * Store:
 * - **loading: boolean** - 全局加载状态
 * - **error: string | null** - 全局错误信息
 * - **theme: 'light' | 'dark'** - 主题模式
 * Actions:
 * - setLoading(loading) - 设置加载状态
 * - setError(error) - 设置错误信息
 * - setTheme(theme) - 设置主题（同步localStorage）
 * - clearError() - 清除错误信息
 *
 * **上游依赖**:
 * - [zustand](https://github.com/pmndrs/zustand) - 状态管理库
 *
 * **下游依赖**:
 * - 无（Store是叶子状态管理模块）
 *
 * **调用方**:
 * - 全局加载和错误状态管理
 * - 主题切换组件
 * - 所有需要全局状态的组件
 *
 * ## [STATE]
 * - **全局状态**: loading, error, theme
 * - **主题持久化**: localStorage.setItem('theme', theme)保存主题
 * - **简单状态管理**: 无中间件，纯Zustand store
 *
 * ## [SIDE-EFFECTS]
 * - **localStorage操作**: localStorage.setItem('theme', theme)保存主题
 * - **状态更新**: set()更新loading, error, theme
 * - **简洁设计**: 最小化全局状态，专注核心功能
 */

import { create } from 'zustand'

interface AppState {
  loading: boolean
  error: string | null
  theme: 'light' | 'dark'
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setTheme: (theme: 'light' | 'dark') => void
  clearError: () => void
}

export const useAppStore = create<AppState>((set) => ({
  loading: false,
  error: null,
  theme: 'light',

  setLoading: (loading: boolean) => set({ loading }),

  setError: (error: string | null) => set({ error }),

  setTheme: (theme: 'light' | 'dark') => {
    set({ theme })
    localStorage.setItem('theme', theme)
  },

  clearError: () => set({ error: null }),
}))