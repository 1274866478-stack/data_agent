'use client'

import { cn } from '@/lib/utils'
import { MaterialIcon } from '@/components/icons/MaterialIcon'

interface SettingsToggleProps {
  checked: boolean
  onCheckedChange: (checked: boolean) => void
  label: string
  description?: string
}

export function SettingsToggle({
  checked,
  onCheckedChange,
  label,
  description,
}: SettingsToggleProps) {
  return (
    <div className="flex items-center justify-between p-4 rounded-xl hover:bg-white/40 dark:hover:bg-slate-800/40 transition-colors">
      <div className="flex-1">
        <h4 className="text-sm font-medium">{label}</h4>
        {description && (
          <p className="text-xs text-slate-500 dark:text-slate-400">{description}</p>
        )}
      </div>
      <button
        onClick={() => onCheckedChange(!checked)}
        className={cn(
          'relative w-11 h-6 rounded-full transition-all duration-300',
          checked
            ? 'bg-primary shadow-[0_0_10px_rgba(129,216,207,0.4)]'
            : 'bg-slate-200 dark:bg-slate-700'
        )}
      >
        <span
          className={cn(
            'absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-md transition-transform duration-300 cubic-bezier(0.4, 0, 0.2, 1)',
            checked && 'translate-x-5'
          )}
        />
      </button>
    </div>
  )
}
