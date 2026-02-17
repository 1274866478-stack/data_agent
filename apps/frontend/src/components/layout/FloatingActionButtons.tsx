'use client'

import { cn } from '@/lib/utils'
import { Grid3x3, Languages } from 'lucide-react'

/**
 * FloatingActionButtons - 右侧浮动快捷操作按钮
 * 基于 DataLab 设计参考的浮动按钮组
 */
export function FloatingActionButtons() {
  return (
    <div className="fixed right-6 top-1/2 transform -translate-y-1/2 flex flex-col gap-3 z-30">
      <button
        className={cn(
          "w-10 h-10 rounded-full",
          "bg-surface-light dark:bg-slate-800",
          "text-slate-500 hover:text-tiffany-400",
          "shadow-lg border border-slate-100 dark:border-slate-700",
          "flex items-center justify-center",
          "transition-all hover:scale-110"
        )}
        title="快捷方式"
      >
        <Grid3x3 className="h-5 w-5" />
      </button>
      <button
        className={cn(
          "w-10 h-10 rounded-full",
          "bg-surface-light dark:bg-slate-800",
          "text-slate-500 hover:text-tiffany-400",
          "shadow-lg border border-slate-100 dark:border-slate-700",
          "flex items-center justify-center",
          "transition-all hover:scale-110"
        )}
        title="翻译"
      >
        <Languages className="h-5 w-5" />
      </button>
    </div>
  )
}
