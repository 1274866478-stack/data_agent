'use client'

import { MaterialIcon } from '@/components/icons/MaterialIcon'
import { cn } from '@/lib/utils'

interface SettingsSectionHeaderProps {
  icon: string
  title: string
  description: string
  className?: string
}

export function SettingsSectionHeader({
  icon,
  title,
  description,
  className,
}: SettingsSectionHeaderProps) {
  return (
    <div className={cn('flex items-start gap-4 mb-6', className)}>
      <div className="p-2 bg-primary/10 rounded-lg border border-primary/20">
        <MaterialIcon icon={icon} className="text-primary text-xl" />
      </div>
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">{description}</p>
      </div>
    </div>
  )
}
