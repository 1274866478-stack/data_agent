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

import { useAuthStore } from '@/store'
import {
    ChevronDown,
    Database,
    History,
    Moon,
    Plus,
    Sun
} from 'lucide-react'
import { useState } from 'react'

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
    <header className="h-16 flex items-center justify-between px-8 bg-surface-light/80 dark:bg-surface-dark/80 backdrop-blur-sm z-10 border-b border-slate-200/50 dark:border-slate-700/50 sticky top-0">
      <div className="flex items-center gap-4">
        {/* 数据库选择器 - DataLab 胶囊风格 */}
        <div className="flex items-center gap-2 bg-accent-light dark:bg-slate-800 px-4 py-2 rounded-full border-2 border-primary-400/40 dark:border-primary-500/30 shadow-sm hover:border-primary-500/60 transition-all cursor-pointer">
          <Database className="text-primary-400 h-4 w-4" />
          <span className="text-xs font-medium text-slate-600 dark:text-slate-300">test_database_optimized</span>
          <span className="text-[10px] bg-white dark:bg-slate-700 px-1.5 rounded text-slate-500 border border-slate-200 dark:border-slate-600">XLSX</span>
          <ChevronDown className="text-slate-400 h-3 w-3 cursor-pointer" />
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* 暗色模式切换 */}
        <button 
          onClick={toggleDarkMode}
          className="p-2 text-slate-400 hover:text-tiffany-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-full transition-colors"
        >
          {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>

        {/* 分隔线 */}
        <div className="h-6 w-px bg-slate-200 dark:bg-slate-700 mx-1"></div>

        {/* 历史记录按钮 */}
        <button className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors">
          <History className="h-4 w-4" />
          History 
          <span className="bg-slate-200 dark:bg-slate-600 px-1.5 rounded-full text-xs">107</span>
        </button>

        {/* 新建会话按钮 - DataLab 风格 */}
        <button className="btn-datalab flex items-center gap-2 px-5 py-2 text-sm hover:scale-105 active:scale-95 transition-transform">
          <Plus className="h-4 w-4" />
          New Chat
        </button>
      </div>
    </header>
  )
}