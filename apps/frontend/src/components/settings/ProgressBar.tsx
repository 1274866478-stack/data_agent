'use client'

import { cn } from '@/lib/utils'

interface ProgressBarProps {
  value: number
  max: number
  className?: string
}

export function ProgressBar({ value, max, className }: ProgressBarProps) {
  const percentage = (value / max) * 100

  return (
    <div className={cn('settings-progress', className)}>
      <div
        className="settings-progress-fill"
        style={{ width: `${percentage}%` }}
      />
    </div>
  )
}
