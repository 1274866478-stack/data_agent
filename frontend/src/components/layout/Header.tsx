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
            <h1 className="text-xl font-semibold">Data Agent V4</h1>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 bg-muted rounded-lg px-3 py-2">
              <Search className="h-4 w-4 text-muted-foreground" />
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
                <p className="text-xs text-muted-foreground">{user?.email}</p>
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