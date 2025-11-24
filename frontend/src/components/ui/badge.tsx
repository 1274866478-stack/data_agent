/**
 * Badge组件
 * 用于显示状态、标签等信息
 */

import React from 'react'
import { cn } from '../../lib/utils'

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline'
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'default',
  ...props
}) => {
  const variantClasses = {
    default:
      'bg-blue-100 text-blue-800 hover:bg-blue-200',
    secondary:
      'bg-gray-100 text-gray-800 hover:bg-gray-200',
    destructive:
      'bg-red-100 text-red-800 hover:bg-red-200',
    outline:
      'text-gray-800 border border-gray-300 hover:bg-gray-50',
  }

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
        variantClasses[variant],
        className
      )}
      {...props}
    />
  )
}

export default Badge