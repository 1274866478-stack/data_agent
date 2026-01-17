/**
 * # [RIGHT_CATEGORY_BAR] 右侧分类导航栏组件
 *
 * ## [MODULE]
 * **文件名**: RightCategoryBar.tsx
 * **职责**: 提供 240px 可折叠的右侧分类导航栏，包含分组菜单和激活状态
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 */

'use client'

import { cn } from '@/lib/utils'
import {
    BarChart3,
    Bot,
    ChevronLeft,
    ChevronRight,
    Database,
    FileBarChart,
    FileText,
    Home,
    Settings,
    Users,
} from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

interface RightCategoryBarProps {
  collapsed: boolean
  onToggle: () => void
}

// 分组导航配置
const navGroups = [
  {
    label: '概览',
    items: [
      { href: '/dashboard', icon: Home, label: '仪表板' },
    ],
  },
  {
    label: '数据管理',
    items: [
      { href: '/data-sources', icon: Database, label: '数据源' },
      { href: '/documents', icon: FileText, label: '文档' },
    ],
  },
  {
    label: '分析工具',
    items: [
      { href: '/ai-assistant', icon: Bot, label: '智能数据助手' },
      { href: '/analytics', icon: BarChart3, label: '数据分析' },
      { href: '/reports', icon: FileBarChart, label: '报告' },
    ],
  },
  {
    label: '系统',
    items: [
      { href: '/users', icon: Users, label: '用户管理' },
      { href: '/settings', icon: Settings, label: '设置' },
    ],
  },
]

export function RightCategoryBar({ collapsed, onToggle }: RightCategoryBarProps) {
  const pathname = usePathname()

  return (
    <div
      className={cn(
        'h-full bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-700/50 transition-all duration-300 flex flex-col',
        collapsed ? 'w-0 overflow-hidden' : 'w-60'
      )}
    >
      {/* 标题栏 */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-slate-200 dark:border-slate-700/50">
        <span className="font-semibold text-slate-900 dark:text-white">智能数据Agent</span>
        <button
          onClick={onToggle}
          className="w-6 h-6 rounded-md flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
      </div>

      {/* 导航分组 */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        {navGroups.map((group, groupIndex) => (
          <div key={group.label} className={cn(groupIndex > 0 && 'mt-6')}>
            <div className="px-3 mb-2">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                {group.label}
              </span>
            </div>

            <div className="space-y-1">
              {group.items.map((item) => {
                const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
                const Icon = item.icon

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-200',
                      isActive
                        ? 'bg-gradient-modern-primary text-white shadow-sm'
                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                    )}
                  >
                    <Icon className="h-4 w-4 flex-shrink-0" />
                    <span>{item.label}</span>
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* 底部版本信息 */}
      <div className="p-4 border-t border-slate-200 dark:border-slate-700/50">
        <p className="text-xs text-slate-400 text-center">
          智能数据Agent V4
        </p>
      </div>
    </div>
  )
}

// 折叠时的展开按钮
export function RightCategoryBarToggle({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="fixed left-16 top-1/2 -translate-y-1/2 w-6 h-12 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-r-lg flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm z-10"
    >
      <ChevronRight className="h-4 w-4" />
    </button>
  )
}
