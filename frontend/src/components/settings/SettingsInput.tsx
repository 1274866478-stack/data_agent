'use client'

import { cn } from '@/lib/utils'
import { forwardRef, InputHTMLAttributes } from 'react'

interface SettingsInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
}

export const SettingsInput = forwardRef<HTMLInputElement, SettingsInputProps>(
  ({ className, label, ...props }, ref) => {
    return (
      <div className="space-y-2">
        {label && (
          <label className="settings-label flex items-center gap-2">
            {label}
            <span className="w-1 h-1 bg-primary rounded-full" />
          </label>
        )}
        <input
          ref={ref}
          className={cn(
            'w-full h-12 px-4 rounded-xl settings-input text-sm',
            className
          )}
          {...props}
        />
      </div>
    )
  }
)
SettingsInput.displayName = 'SettingsInput'
