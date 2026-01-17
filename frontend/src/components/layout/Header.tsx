/**
 * # [HEADER] 应用顶部导航栏组件
 *
 * ## [MODULE]
 * **文件名**: Header.tsx
 * **职责**: 应用顶部导航栏 - 搜索、通知、主题切换、用户菜单、侧边栏折叠按钮
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 应用顶部导航栏组件
 *
 * ## [INPUT]
 * Props:
 * - **onSidebarToggle: () => void** - 切换侧边栏折叠状态的回调函数
 * - **sidebarCollapsed: boolean** - 侧边栏当前折叠状态
 *
 * ## [OUTPUT]
 * - **Header组件** - 渲染顶部导航栏
 *   - 左侧：移动端侧边栏折叠按钮（Menu图标）
 *   - 中间左侧：应用标题（Data Agent V4）
 *   - 中间右侧：搜索框、通知按钮、主题切换、设置按钮
 *   - 右侧：用户信息（头像、名称、邮箱、退出按钮）
 * - **主题切换**: darkMode状态，toggleDarkMode函数（document.documentElement.classList.toggle('dark')）
 * - **用户信息**: 从useAuthStore获取user和logout函数
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（useState hook）
 * - [lucide-react](https://lucide.dev/) - 图标库（Bell, Search, Settings, User, Menu, Moon, Sun）
 * - [../store/authStore](../store/authStore.ts) - 认证状态（useAuthStore）
 * - [../ui/button.tsx](../ui/button.tsx) - Button组件
 *
 * **下游依赖**:
 * - 无（Header是叶子组件）
 *
 * **调用方**:
 * - [./Layout.tsx](./Layout.tsx) - 布局组件
 *
 * ## [STATE]
 * - **darkMode: boolean** - 暗色模式状态（默认false）
 * - **setDarkMode(boolean)** - 切换暗色模式函数
 * - **用户信息**: user, logout从useAuthStore获取
 * - **主题切换**: document.documentElement.classList.toggle('dark')
 * - **Header样式**: h-16, border-b, bg-background/95, backdrop-blur, sticky, top-0, z-50
 * - **布局容器**: div.flex.h-full.items-center.px-4.gap-4
 * - **搜索框**: input.bg-transparent.border-none.outline-none（w-64）
 * - **用户头像**: div.w-8.h-8.bg-primary.rounded-full（User图标）
 *
 * ## [SIDE-EFFECTS]
 * - **状态更新**: setDarkMode(!darkMode)切换暗色模式
 * - **DOM操作**: document.documentElement.classList.toggle('dark')切换CSS类
 * - **Props传递**: onSidebarToggle传递给Button的onClick
 * - **Store读取**: useAuthStore()获取user和logout
 * - **条件渲染**: className="lg:hidden"控制移动端按钮显示
 * - **用户信息显示**: user?.full_name || user?.email || '用户'
 * - **按钮渲染**: Bell, Sun/Moon, Settings, 退出按钮
 */

'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/store'
import {
  Bell,
  Search,
  Settings,
  User,
  Menu,
  Moon,
  Sun
} from 'lucide-react'

interface HeaderProps {
  onSidebarToggle: () => void
  sidebarCollapsed: boolean
}

export function Header({ onSidebarToggle, sidebarCollapsed }: HeaderProps) {
  const { user, logout } = useAuthStore()
  const [darkMode, setDarkMode] = useState(false)

  const toggleDarkMode = () => {
    setDarkMode(!darkMode)
    document.documentElement.classList.toggle('dark')
  }

  return (
    <header className="h-16 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
      <div className="flex h-full items-center px-4 gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={onSidebarToggle}
          className="lg:hidden"
        >
          <Menu className="h-4 w-4" />
        </Button>

        <div className="flex-1 flex items-center justify-between">
          <div className="hidden md:block">
            <h1 className="text-xl font-semibold">智能数据Agent V4</h1>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 bg-muted rounded-lg px-3 py-2">
              <Search className="h-4 w-4 text-gray-500 dark:text-gray-400" />
              <input
                type="text"
                placeholder="搜索..."
                className="bg-transparent border-none outline-none text-sm w-64 placeholder:text-muted-foreground"
              />
            </div>

            <Button variant="ghost" size="sm">
              <Bell className="h-4 w-4" />
            </Button>

            <Button variant="ghost" size="sm" onClick={toggleDarkMode}>
              {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>

            <Button variant="ghost" size="sm">
              <Settings className="h-4 w-4" />
            </Button>

            <div className="flex items-center gap-2 pl-2 border-l border-border">
              <div className="hidden md:block text-right">
                <p className="text-sm font-medium">{user?.full_name || user?.email || '用户'}</p>
                <p className="text-xs text-gray-600 dark:text-gray-400">{user?.email}</p>
              </div>
              <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                <User className="h-4 w-4 text-primary-foreground" />
              </div>
              <Button variant="ghost" size="sm" onClick={logout}>
                退出
              </Button>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}