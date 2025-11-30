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
          title: 'AI 助手',
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
              <p className="text-xs text-muted-foreground">导航功能</p>
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
                "w-full justify-start font-medium text-muted-foreground mb-2",
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