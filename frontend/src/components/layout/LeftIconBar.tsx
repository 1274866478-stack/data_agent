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
import Image from 'next/image'
import {
    Bot,
    Database,
    FileText,
    Home,
    Settings,
    User,
} from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

// 导航项配置 - Agent放在首位并突出显示
const navItems = [
  { href: '/ai-assistant', icon: Bot, label: 'Insight Agent', highlight: true },
  { href: '/data-sources', icon: Database, label: '数据源' },
  { href: '/documents', icon: FileText, label: '文档' },
  { href: '/dashboard', icon: Home, label: '仪表盘' },
]

const bottomItems = [
  { href: '/settings', icon: Settings, label: '设置' },
]

export function LeftIconBar() {
  const pathname = usePathname()

  return (
    <div className="w-16 h-full bg-gradient-to-b from-slate-900 to-slate-800 flex flex-col items-center py-4 border-r border-slate-700/50">
      {/* Logo 区域 */}
      <Link href="/dashboard" className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center mb-6 overflow-hidden">
        <Image src="/logo-icon-only.svg" alt="Insight Agent" width={40} height={40} className="object-contain" />
      </Link>

      {/* 主导航 - Agent突出显示在最顶部 */}
      <nav className="flex-1 flex flex-col items-center gap-2">
        {/* Agent 专用突出指示 */}
        <div className="relative mb-1">
          <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-amber-400 rounded-full animate-pulse" />
          <div className="absolute -top-0.5 left-1/2 -translate-x-1/2 w-4 h-4 bg-amber-500/30 rounded-full animate-ping" />
        </div>
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          const Icon = item.icon
          const isHighlight = item.highlight

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'group relative w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-200',
                isActive
                  ? isHighlight
                    ? 'bg-gradient-modern-primary text-white shadow-lg shadow-primary/30'
                    : 'bg-accent text-accent-foreground'
                  : isHighlight
                    ? 'text-amber-400 hover:text-amber-300 hover:bg-amber-500/20'
                    : 'text-muted-foreground hover:text-accent-foreground hover:bg-accent/50'
              )}
            >
              {/* 高亮项发光效果 */}
              {isHighlight && !isActive && (
                <div className="absolute inset-0 rounded-lg bg-amber-500/10 animate-pulse" />
              )}
              <Icon className={cn('h-5 w-5 relative z-10', isHighlight && 'drop-shadow-lg')} />

              {/* 文字标签 - 高亮项常驻显示 */}
              {isHighlight ? (
                <div className="absolute left-full ml-3 px-2 py-1 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs rounded-md whitespace-nowrap z-50 shadow-lg">
                  {item.label}
                </div>
              ) : (
                <div className="absolute left-full ml-3 px-2 py-1 bg-popover text-popover-foreground text-xs rounded-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50 shadow-md border border-border">
                  {item.label}
                </div>
              )}

              {/* 激活指示器 - 高亮项使用渐变 */}
              {isActive && (
                <div className={cn(
                  'absolute left-0 w-0.5 h-6 rounded-r',
                  isHighlight
                    ? 'bg-gradient-to-b from-amber-300 to-orange-400'
                    : 'bg-gradient-modern-primary'
                )} />
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
