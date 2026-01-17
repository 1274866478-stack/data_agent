'use client'

/**
 * # [THEME_TOGGLE] 主题切换按钮组件
 *
 * ## [MODULE]
 * **文件名**: ThemeToggle.tsx
 * **职责**: 提供亮色/暗色模式切换按钮，支持下拉菜单选择系统主题
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-17): 初始版本 - 主题切换按钮组件
 *
 * ## [INPUT]
 * Props (无 - 内部使用 useAppStore)
 *
 * ## [OUTPUT]
 * - **切换按钮**: 点击切换亮色/暗色模式
 * - **下拉菜单**: 支持 light/dark/system 三种模式选择
 * - **图标显示**: 根据当前主题显示对应图标
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架
 * - [lucide-react](https://lucide.dev/) - 图标库（Moon, Sun, Monitor）
 * - [../../store/appStore](../../store/appStore.ts) - 应用状态管理
 * - [../ui/button](../ui/button.tsx) - 按钮组件
 * - [../ui/dropdown-menu](../ui/dropdown-menu.tsx) - 下拉菜单组件
 *
 * **下游依赖**:
 * - 无（叶子组件）
 *
 * **调用方**:
 * - 所有需要主题切换的页面/布局
 *
 * ## [STATE]
 * - **theme**: 从 appStore 读取当前主题
 * - **setTheme**: 更新主题的方法
 *
 * ## [SIDE-EFFECTS]
 * - **Store 更新**: 调用 setTheme 更新主题到 appStore
 */

import { Moon, Sun, Monitor } from 'lucide-react'
import { useAppStore, getEffectiveTheme } from '@/store/appStore'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

export function ThemeToggle() {
  const theme = useAppStore((state) => state.theme)
  const setTheme = useAppStore((state) => state.setTheme)
  const effectiveTheme = getEffectiveTheme(theme)

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme)
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon" className="h-9 w-9">
          <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">切换主题</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={() => handleThemeChange('light')}>
          <Sun className="mr-2 h-4 w-4" />
          <span>亮色</span>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => handleThemeChange('dark')}>
          <Moon className="mr-2 h-4 w-4" />
          <span>暗色</span>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => handleThemeChange('system')}>
          <Monitor className="mr-2 h-4 w-4" />
          <span>跟随系统</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// 简单版切换按钮（不带下拉菜单）
export function ThemeToggleSimple() {
  const theme = useAppStore((state) => state.theme)
  const toggleTheme = useAppStore((state) => state.toggleTheme)
  const effectiveTheme = getEffectiveTheme(theme)

  return (
    <Button
      variant="outline"
      size="icon"
      onClick={toggleTheme}
      className="h-9 w-9"
      title={effectiveTheme === 'dark' ? '切换到亮色模式' : '切换到暗色模式'}
    >
      <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
      <span className="sr-only">切换主题</span>
    </Button>
  )
}
