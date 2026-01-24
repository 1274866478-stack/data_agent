'use client'

import { cn } from '@/lib/utils'
import { ReactNode } from 'react'

interface GlassPanelProps {
  children: ReactNode
  className?: string
}

export function GlassPanel({ children, className }: GlassPanelProps) {
  return (
    <div className={cn('settings-glass-card rounded-2xl p-8', className)}>
      {children}
    </div>
  )
}
