/**
 * # [MODERN_LAYOUT] 现代化布局容器组件
 *
 * ## [MODULE]
 * **文件名**: ModernLayout.tsx
 * **职责**: 提供现代化的双边栏布局容器，包含左侧图标栏和右侧分类栏
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 */

'use client'

import { useState } from 'react'
import { LeftIconBar } from './LeftIconBar'
import { RightCategoryBar, RightCategoryBarToggle } from './RightCategoryBar'

interface ModernLayoutProps {
  children: React.ReactNode
}

export function ModernLayout({ children }: ModernLayoutProps) {
  const [rightBarCollapsed, setRightBarCollapsed] = useState(false)

  return (
    <div className="h-screen flex overflow-hidden bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      {/* 左侧图标栏 - 固定 64px */}
      <LeftIconBar />

      {/* 右侧分类栏 - 可折叠 0/240px */}
      <RightCategoryBar
        collapsed={rightBarCollapsed}
        onToggle={() => setRightBarCollapsed(!rightBarCollapsed)}
      />

      {/* 折叠时的展开按钮 */}
      {rightBarCollapsed && (
        <RightCategoryBarToggle onClick={() => setRightBarCollapsed(false)} />
      )}

      {/* 主内容区 */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
