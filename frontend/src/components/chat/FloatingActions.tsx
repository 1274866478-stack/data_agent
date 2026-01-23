'use client'

import { Languages, LayoutGrid } from 'lucide-react'

interface FloatingActionsProps {
  onQuickAction?: () => void
  onTranslate?: () => void
}

/**
 * DataLab 右侧浮动按钮组
 * 包含快捷方式和翻译按钮
 */
export function FloatingActions({ onQuickAction, onTranslate }: FloatingActionsProps) {
  return (
    <div className="fixed right-6 top-1/2 -translate-y-1/2 flex flex-col gap-2 z-40">
      {/* 快捷方式按钮 */}
      <button
        onClick={onQuickAction}
        className="w-10 h-10 rounded-lg bg-white dark:bg-slate-800 shadow-soft border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-500 hover:text-primary hover:border-primary/30 transition-all hover:shadow-glow"
        title="Quick Actions"
      >
        <LayoutGrid className="w-5 h-5" />
      </button>

      {/* 翻译按钮 */}
      <button
        onClick={onTranslate}
        className="w-10 h-10 rounded-lg bg-white dark:bg-slate-800 shadow-soft border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-500 hover:text-primary hover:border-primary/30 transition-all hover:shadow-glow"
        title="Translate"
      >
        <Languages className="w-5 h-5" />
      </button>
    </div>
  )
}
