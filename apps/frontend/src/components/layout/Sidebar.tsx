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

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  LayoutDashboard,
  Database,
  BarChart3,
  Bot,
  Settings,
  FileText,
  Users,
  ChevronDown,
  ChevronRight,
  Plus
} from 'lucide-react'

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
      title: '主要功能',
      items: [
        {
          title: '仪表板',
          href: '/dashboard',
          icon: LayoutDashboard
        },
        {
          title: '数据源管理',
          href: '/data-sources',
          icon: Database,
          badge: '3'
        },
        {
          title: '数据分析',
          href: '/analytics',
          icon: BarChart3
        },
        {
          title: '智能数据助手',
          href: '/ai-assistant',
          icon: Bot,
          badge: '新'
        }
      ]
    },
    {
      title: '管理',
      items: [
        {
          title: '报告中心',
          href: '/reports',
          icon: FileText
        },
        {
          title: '用户管理',
          href: '/users',
          icon: Users
        },
        {
          title: '系统设置',
          href: '/settings',
          icon: Settings
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
      "flex flex-col h-full bg-background border-r border-border transition-all duration-300",
      collapsed ? "w-16" : "w-64"
    )}>
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          {!collapsed && (
            <div>
              <h2 className="text-lg font-bold text-foreground">菜单</h2>
              <p className="text-xs text-gray-600 dark:text-gray-400">导航功能</p>
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={onCollapse}
            className="hidden lg:flex"
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto p-4 space-y-6">
        {navSections.map((section) => (
          <div key={section.title}>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => toggleSection(section.title)}
              className={cn(
                "w-full justify-start font-medium text-gray-600 dark:text-gray-400 mb-2",
                collapsed && "hidden"
              )}
            >
              {expandedSections.includes(section.title) ? (
                <ChevronDown className="h-4 w-4 mr-2" />
              ) : (
                <ChevronRight className="h-4 w-4 mr-2" />
              )}
              {section.title}
            </Button>

            {(expandedSections.includes(section.title) || collapsed) && (
              <div className="space-y-1">
                {section.items.map((item) => {
                  const Icon = item.icon
                  return (
                    <Link key={item.href} href={item.href}>
                      <Button
                        variant={isActive(item.href) ? "secondary" : "ghost"}
                        size="sm"
                        className={cn(
                          "w-full justify-start",
                          collapsed ? "px-2" : "px-3"
                        )}
                      >
                        <Icon className="h-4 w-4" />
                        {!collapsed && (
                          <>
                            <span className="ml-3">{item.title}</span>
                            {item.badge && (
                              <span className="ml-auto text-xs bg-primary text-primary-foreground px-2 py-1 rounded-full">
                                {item.badge}
                              </span>
                            )}
                          </>
                        )}
                      </Button>
                    </Link>
                  )
                })}
              </div>
            )}
          </div>
        ))}
      </nav>

      <div className="p-4 border-t border-border">
        <Button
          variant="default"
          size="sm"
          className={cn(
            "w-full",
            collapsed && "px-2"
          )}
        >
          <Plus className="h-4 w-4" />
          {!collapsed && <span className="ml-2">新建项目</span>}
        </Button>
      </div>
    </aside>
  )
}