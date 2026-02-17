/**
 * # [LEFT_ICON_BAR] 左侧图标导航栏组件
 *
 * ## [MODULE]
 * **文件名**: LeftIconBar.tsx
 * **职责**: 提供 64px 固定宽度的左侧图标导航栏，包含主导航图标和底部用户头像
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 */

'use client'

import { cn } from '@/lib/utils'
import {
    BarChart3,
    Bot,
    Database,
    FileText,
    Home,
    Settings,
    User,
} from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

// 导航项配置
const navItems = [
  { href: '/dashboard', icon: Home, label: '仪表板' },
  { href: '/data-sources', icon: Database, label: '数据源' },
  { href: '/documents', icon: FileText, label: '文档' },
  { href: '/ai-assistant', icon: Bot, label: 'Insight Agent' },
  { href: '/analytics', icon: BarChart3, label: '分析' },
]

const bottomItems = [
  { href: '/settings', icon: Settings, label: '设置' },
]

export function LeftIconBar() {
  const pathname = usePathname()

  return (
    <div className="w-16 h-full bg-gradient-to-b from-slate-900 to-slate-800 flex flex-col items-center py-4 border-r border-slate-700/50">
      {/* Logo 区域 */}
      <div className="w-10 h-10 rounded-xl bg-gradient-modern-primary flex items-center justify-center mb-6">
        <span className="text-primary-foreground font-bold text-lg">D</span>
      </div>

      {/* 主导航 */}
      <nav className="flex-1 flex flex-col items-center gap-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          const Icon = item.icon

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'group relative w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-200',
                isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:text-accent-foreground hover:bg-accent/50'
              )}
            >
              <Icon className="h-5 w-5" />
              
              {/* Tooltip */}
              <div className="absolute left-full ml-3 px-2 py-1 bg-popover text-popover-foreground text-xs rounded-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50 shadow-md border border-border">
                {item.label}
              </div>

              {/* 激活指示器 */}
              {isActive && (
                <div className="absolute left-0 w-0.5 h-6 bg-gradient-modern-primary rounded-r" />
              )}
            </Link>
          )
        })}
      </nav>

      {/* 底部导航 */}
      <div className="flex flex-col items-center gap-2 pt-4 border-t border-slate-700/50">
        {bottomItems.map((item) => {
          const isActive = pathname === item.href
          const Icon = item.icon

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'group relative w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-200',
                isActive
                  ? 'bg-accent text-accent-foreground'
                  : 'text-muted-foreground hover:text-accent-foreground hover:bg-accent/50'
              )}
            >
              <Icon className="h-5 w-5" />
              
              {/* Tooltip */}
              <div className="absolute left-full ml-3 px-2 py-1 bg-popover text-popover-foreground text-xs rounded-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50 shadow-md border border-border">
                {item.label}
              </div>
            </Link>
          )
        })}

        {/* 用户头像 */}
        <div className="w-10 h-10 rounded-full bg-gradient-modern-accent flex items-center justify-center mt-2 cursor-pointer hover:ring-2 hover:ring-white/20 transition-all">
          <User className="h-5 w-5 text-primary-foreground" />
        </div>
      </div>
    </div>
  )
}
