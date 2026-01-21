'use client'

import { Card } from './card'
import { Badge } from './badge'
import { Button } from './button'
import { cn } from '@/lib/utils'
import { CheckCircle, Database, FileText, Table, X } from 'lucide-react'
import { ReactNode } from 'react'

/**
 * ContextCard - 上下文卡片组件
 * 用于显示数据源、文件、Schema 等上下文信息
 */
export interface ContextCardProps {
  /** 卡片标题 */
  title: string
  /** 上下文类型 */
  type: 'database' | 'file' | 'schema' | 'table' | 'custom'
  /** 元数据键值对 */
  metadata?: Record<string, string | number>
  /** 额外的CSS类名 */
  className?: string
  /** 点击事件 */
  onClick?: () => void
  /** 是否激活状态 */
  active?: boolean
  /** 是否显示操作按钮 */
  showActions?: boolean
  /** 自定义图标 */
  icon?: ReactNode
  /** 删除回调 */
  onDelete?: () => void
  /** 状态标签 */
  status?: 'active' | 'inactive' | 'loading' | 'error'
}

const typeIcons = {
  database: Database,
  file: FileText,
  schema: Table,
  table: Table,
  custom: CheckCircle,
}

const typeBadgeVariants = {
  database: 'default',
  file: 'secondary',
  schema: 'outline',
  table: 'outline',
  custom: 'default',
} as const

export function ContextCard({
  title,
  type,
  metadata,
  className,
  onClick,
  active = false,
  showActions = false,
  icon,
  onDelete,
  status = 'active',
}: ContextCardProps) {
  const IconComponent = icon || typeIcons[type]

  return (
    <Card
      className={cn(
        'p-4 transition-all duration-200 cursor-pointer group relative',
        'hover:shadow-md',
        // 左侧边框颜色根据状态变化
        active
          ? 'border-l-4 border-l-tiffany-400 bg-tiffany-50/50 dark:bg-tiffany-950/20'
          : 'border-l-4 border-l-border hover:border-l-tiffany-300',
        'dark:bg-card',
        className
      )}
      onClick={onClick}
    >
      {/* 头部：标题和类型标签 */}
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {IconComponent && (
            <IconComponent className="w-4 h-4 text-tiffany-600 dark:text-tiffany-400 flex-shrink-0" />
          )}
          <span className="font-medium text-sm truncate">{title}</span>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <Badge variant={typeBadgeVariants[type]} className="text-[10px]">
            {type}
          </Badge>
          {status === 'active' && (
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          )}
          {status === 'loading' && (
            <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
          )}
          {status === 'error' && (
            <div className="w-2 h-2 rounded-full bg-red-500" />
          )}
        </div>
      </div>

      {/* 元数据 */}
      {metadata && Object.keys(metadata).length > 0 && (
        <div className="text-xs text-muted-foreground space-y-1">
          {Object.entries(metadata).map(([key, value]) => (
            <p key={key} className="flex justify-between gap-2">
              <span className="font-medium">{key}:</span>
              <span className="truncate">{value}</span>
            </p>
          ))}
        </div>
      )}

      {/* 操作按钮 */}
      {showActions && (
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          {onDelete && (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={(e) => {
                e.stopPropagation()
                onDelete()
              }}
            >
              <X className="w-3 h-3" />
            </Button>
          )}
        </div>
      )}
    </Card>
  )
}

/**
 * ContextCardList - 上下文卡片列表容器
 */
export interface ContextCardListProps {
  children: ReactNode
  title?: string
  className?: string
}

export function ContextCardList({
  children,
  title,
  className,
}: ContextCardListProps) {
  return (
    <div className={cn('space-y-3', className)}>
      {title && (
        <h2 className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">
          {title}
        </h2>
      )}
      {children}
    </div>
  )
}

/**
 * SchemaMapDisplay - 表结构可视化组件
 * 用于显示数据库表的字段和关系
 */
export interface SchemaMapDisplayProps {
  tables: Array<{
    name: string
    columns: Array<{
      name: string
      type: string
      nullable?: boolean
      primaryKey?: boolean
    }>
  }>
  className?: string
}

export function SchemaMapDisplay({
  tables,
  className,
}: SchemaMapDisplayProps) {
  return (
    <div className={cn('space-y-3', className)}>
      {tables.map((table) => (
        <Card key={table.name} className="p-3 bg-muted/30">
          <h3 className="text-sm font-semibold mb-2 font-mono text-tiffany-700 dark:text-tiffany-300">
            {table.name}
          </h3>
          <div className="space-y-1">
            {table.columns.map((column) => (
              <div
                key={column.name}
                className="flex items-center gap-2 text-xs"
              >
                {column.primaryKey && (
                  <div className="w-2 h-2 rounded-full bg-tiffany-500" />
                )}
                <span
                  className={cn(
                    'font-mono',
                    column.primaryKey && 'font-semibold'
                  )}
                >
                  {column.name}
                </span>
                <span className="text-muted-foreground">{column.type}</span>
                {column.nullable && (
                  <span className="text-[10px] text-muted-foreground/70">
                    nullable
                  </span>
                )}
              </div>
            ))}
          </div>
        </Card>
      ))}
    </div>
  )
}
