/**
 * # [SIDEBAR] 应用侧边栏导航组件
 *
 * ## [MODULE]
 * **文件名**: Sidebar.tsx
 * **职责**: 应用侧边栏导航 - 可折叠导航菜单、导航项高亮、徽章显示、分组展开/收起
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 应用侧边栏导航组件
 *
 * ## [INPUT]
 * Props:
 * - **collapsed: boolean** - 侧边栏折叠状态
 * - **onCollapse: () => void** - 切换折叠状态的回调函数
 *
 * ## [OUTPUT]
 * - **Sidebar组件** - 渲染侧边栏导航
 *   - 顶部：菜单标题和折叠按钮（ChevronDown/Right图标）
 *   - 中间：导航区域（可滚动，包含2个分组：主要功能、管理）
 *   - 底部：新建项目按钮
 * - **导航项**: NavItem[]（title, href, icon, badge?）
 * - **导航分组**: NavSection[]（title, items[]）
 * - **路由高亮**: isActive(href)判断当前路径（pathname.startsWith(href)）
 * - **折叠宽度**: collapsed?w-16:w-64（transition-all duration-300）
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（useState hook）
 * - [next/navigation](https://nextjs.org/docs) - Next.js路由（usePathname）
 * - [lucide-react](https://lucide.dev/) - 图标库（LayoutDashboard, Database, BarChart3, Bot, Settings, FileText, Users, ChevronDown, ChevronRight, Plus）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 * - [@/components/ui/button](../ui/button.tsx) - Button组件
 *
 * **下游依赖**:
 * - 无（Sidebar是叶子组件）
 *
 * **调用方**:
 * - [./Layout.tsx](./Layout.tsx) - 布局组件
 *
 * ## [STATE]
 * - **expandedSections: string[]** - 展开的导航分组列表（默认['main']）
 * - **setExpandedSections(string[])** - 更新展开分组列表
 * - **toggleSection(section)** - 切换分组展开/收起（filter或push）
 * - **pathname**: 当前路径（usePathname()）
 * - **navSections**: 导航分组数据（主要功能、管理）
 * - **isActive(href)**: 判断导航项是否激活
 *   - /dashboard特殊处理：pathname === '/dashboard' || pathname === '/'
 *   - 其他：pathname.startsWith(href)
 * - **Sidebar样式**: flex.flex-col.h-full.bg-background.border-r.border-border.transition-all.duration-300
 * - **折叠宽度**: collapsed?w-16:w-64（16px或256px）
 * - **导航项徽章**: badge字符串（'3', '新'）
 *
 * ## [SIDE-EFFECTS]
 * - **状态更新**: setExpandedSections更新展开分组
 * - **路由读取**: usePathname()获取当前路径
 * - **Props传递**: collapsed和onCollapse从Layout传入
 * - **条件渲染**: collapsed控制菜单标题、导航项文本、徽章显示
 * - **按钮渲染**: Link包装Button组件（variant={isActive?"secondary":"ghost"}）
 * - **数组操作**: filter、includes、push、map处理展开分组和导航项
 * - **样式计算**: cn()合并类名（collapsed条件、isActive条件）
 * - **图标渲染**: 动态Icon组件（item.icon）
 */

'use client'

import { cn } from '@/lib/utils'
import {
    BarChart3,
    Bot,
    Crown,
    Database,
    FileText,
    FlaskConical,
    LayoutDashboard,
    Settings
} from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'

interface SidebarProps {
  collapsed: boolean
  onCollapse: () => void
}

interface NavItem {
  title: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badge?: string
}

interface NavSection {
  title: string
  items: NavItem[]
}

export function Sidebar({ collapsed, onCollapse }: SidebarProps) {
  const pathname = usePathname()
  const [expandedSections, setExpandedSections] = useState<string[]>(['main'])

  const toggleSection = (section: string) => {
    setExpandedSections(prev =>
      prev.includes(section)
        ? prev.filter(s => s !== section)
        : [...prev, section]
    )
  }

  const navSections: NavSection[] = [
    {
      title: 'OVERVIEW',
      items: [
        {
          title: 'Dashboard',
          href: '/dashboard',
          icon: LayoutDashboard
        }
      ]
    },
    {
      title: 'DATA MANAGEMENT',
      items: [
        {
          title: 'Data Sources',
          href: '/data-sources',
          icon: Database,
          badge: '3'
        },
        {
          title: 'Documents',
          href: '/analytics',
          icon: FileText
        }
      ]
    },
    {
      title: 'ANALYSIS TOOLS',
      items: [
        {
          title: 'AI Assistant',
          href: '/ai-assistant',
          icon: Bot,
          badge: '新'
        },
        {
          title: 'Analysis',
          href: '/analytics',
          icon: BarChart3
        },
        {
          title: 'Reports',
          href: '/reports',
          icon: FileText
        }
      ]
    }
  ]

  const isActive = (href: string) => {
    if (href === '/dashboard') {
      return pathname === '/dashboard' || pathname === '/'
    }
    return pathname.startsWith(href)
  }

  return (
    <aside className={cn(
      "flex flex-col h-full bg-surface-light dark:bg-surface-dark border-r border-slate-200 dark:border-slate-700 transition-all duration-300",
      collapsed ? "w-16" : "w-64"
    )}>
      {/* Logo 区域 */}
      <div className="h-16 flex items-center px-6 border-b border-slate-100 dark:border-slate-700/50">
        {!collapsed ? (
          <div className="flex items-center">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-slate-900 mr-3 shadow-glow">
              <FlaskConical className="h-5 w-5" />
            </div>
            <h1 className="font-display font-bold text-lg tracking-tight">
              Data<span className="text-primary">Lab</span> Agent
            </h1>
          </div>
        ) : (
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-slate-900 shadow-glow mx-auto">
            <FlaskConical className="h-5 w-5" />
          </div>
        )}
      </div>

      {/* 导航区域 */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-8">
        {navSections.map((section) => (
          <div key={section.title}>
            {!collapsed && (
              <p className="px-2 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                {section.title}
              </p>
            )}

            <div className="space-y-1">
              {section.items.map((item) => {
                const Icon = item.icon
                const active = isActive(item.href)
                return (
                  <Link key={item.href} href={item.href}>
                    <div
                      className={cn(
                        "flex items-center px-2 py-2.5 text-sm font-medium rounded-lg transition-colors group",
                        active 
                          ? "bg-secondary/30 text-primary border border-primary/20" 
                          : "text-slate-600 dark:text-slate-400 hover:text-primary hover:bg-slate-50 dark:hover:bg-slate-700/50",
                        collapsed && "justify-center"
                      )}
                    >
                      <Icon className={cn(
                        "h-4 w-4 transition-colors",
                        active ? "text-primary" : "text-slate-400 group-hover:text-primary"
                      )} />
                      {!collapsed && (
                        <>
                          <span className="ml-3">{item.title}</span>
                          {item.badge && (
                            <span className="ml-auto text-[10px] bg-primary/20 text-primary-700 dark:text-primary-300 px-2 py-0.5 rounded-full border border-primary/30">
                              {item.badge}
                            </span>
                          )}
                        </>
                      )}
                    </div>
                  </Link>
                )
              })}
            </div>
          </div>
        ))}

        {/* 升级 Pro 按钮 - 金色渐变卡片 */}
        {!collapsed ? (
          <Link href="/pricing" className="mx-2 mt-4 block">
            <div className="px-3 py-2.5 rounded-xl transition-all duration-300 bg-gradient-to-r from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600 shadow-lg shadow-amber-500/30 hover:shadow-xl hover:shadow-amber-500/50 hover:scale-[1.02] active:scale-[0.98]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 bg-white/20 rounded-lg flex items-center justify-center">
                    <Crown className="h-4 w-4 text-white" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-bold text-white">升级 Pro</span>
                    <span className="text-[10px] text-white/80">解锁更多功能</span>
                  </div>
                </div>
                <span className="text-sm">⭐</span>
              </div>
            </div>
          </Link>
        ) : (
          <Link href="/pricing" className="mx-auto mt-4 block">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 shadow-lg shadow-amber-500/30 hover:shadow-xl hover:shadow-amber-500/50 hover:scale-105 active:scale-95 transition-all flex items-center justify-center">
              <Crown className="h-5 w-5 text-white" />
            </div>
          </Link>
        )}
      </nav>

      {/* 底部用户区域 */}
      <div className="p-4 border-t border-slate-100 dark:border-slate-700/50">
        <div className="flex items-center w-full px-2 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50 rounded-lg transition-colors cursor-pointer">
          {!collapsed && (
            <>
              <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-600 flex items-center justify-center text-xs font-bold mr-3">
                JD
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold">John Doe</p>
                <p className="text-xs text-slate-400">Data Scientist</p>
              </div>
              <Settings className="h-4 w-4 text-slate-400" />
            </>
          )}
          {collapsed && (
            <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-600 flex items-center justify-center text-xs font-bold mx-auto">
              JD
            </div>
          )}
        </div>
      </div>
    </aside>
  )
}