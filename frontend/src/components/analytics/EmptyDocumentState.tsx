/**
 * [HEADER]
 * 空状态组件 (Empty Document State) - Analytics 页面专用
 *
 * [MODULE]
 * 模块类型: React UI 组件
 * 所属功能: 空状态显示 - 文档注册库
 * 技术栈: React, TypeScript, Tailwind CSS
 *
 * [INPUT]
 * Props:
 * - 无 props
 *
 * [OUTPUT]
 * - 渲染玻璃态风格的空状态提示
 *
 * [LINK]
 * - 使用路径: @/components/analytics/EmptyDocumentState
 * - 配套组件: DonutChart, ActivityLogTable
 *
 * [POS]
 * - 文件路径: frontend/src/components/analytics/EmptyDocumentState.tsx
 *
 * [STATE]
 * - 无状态组件
 *
 * [PROTOCOL]
 * - 使用 analytics-glass-card 玻璃态样式
 * - 虚线边框表示可拖放区域
 * - 居中显示提示信息
 */

import { MaterialIcon } from '@/components/icons/MaterialIcon'

interface EmptyDocumentStateProps {
  /** 自定义标题 */
  title?: string
  /** 自定义描述 */
  description?: string
  /** 自定义图标名称 */
  iconName?: string
  /** 点击回调 */
  onAction?: () => void
  /** 操作按钮文本 */
  actionText?: string
}

/**
 * 空状态组件
 *
 * 显示带有玻璃态效果的空状态提示
 *
 * @example
 * ```tsx
 * <EmptyDocumentState />
 *
 * <EmptyDocumentState
 *   title="自定义标题"
 *   description="自定义描述文本"
 *   iconName="folder_off"
 *   onAction={() => console.log('Action clicked')}
 *   actionText="上传文档"
 * />
 * ```
 */
export function EmptyDocumentState({
  title = '文档注册库',
  description = '当前没有任何文档挂载至语义分析引擎，请初始化数据流。',
  iconName = 'upload_file',
  onAction,
  actionText = '初始化数据流',
}: EmptyDocumentStateProps) {
  return (
    <div className="analytics-glass-card p-8 rounded-sm min-h-[400px] flex flex-col">
      {/* Header */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <h3 className="analytics-tech-label text-slate-800 dark:text-slate-200">
            {title}
          </h3>
          <p className="text-[10px] text-slate-400 mt-1 uppercase">
            Semantic Index Registry
          </p>
        </div>
        <MaterialIcon icon="account_tree" className="text-slate-300 dark:text-slate-600" />
      </div>

      {/* Empty State Content */}
      <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-tiffany/20 bg-white/20 dark:bg-slate-800/20 rounded">
        {/* Icon */}
        <div className="w-16 h-16 rounded-full bg-tiffany/5 dark:bg-tiffany/10 border border-tiffany/10 flex items-center justify-center mb-4">
          <MaterialIcon icon={iconName} className="text-tiffany/40 dark:text-tiffany/60 text-3xl" />
        </div>

        {/* Text */}
        <p className="analytics-tech-label text-slate-400 dark:text-slate-500">
          等待实验数据摄入
        </p>
        <p className="text-[10px] text-slate-300 dark:text-slate-600 mt-2 text-center max-w-[200px]">
          {description}
        </p>

        {/* Action Button */}
        {onAction && (
          <button
            onClick={onAction}
            className="mt-6 px-6 py-2.5 bg-tiffany text-white rounded-lg font-semibold text-xs hover:opacity-90 transition-opacity shadow-[0_4px_15px_rgba(129,216,207,0.3)]"
          >
            {actionText}
          </button>
        )}
      </div>
    </div>
  )
}

/**
 * 简化版空状态组件 - 用于小型卡片
 */
interface SimpleEmptyStateProps {
  /** 图标名称 */
  icon: string
  /** 标题 */
  title: string
  /** 描述 */
  description?: string
  /** 点击回调 */
  onAction?: () => void
  /** 操作按钮文本 */
  actionText?: string
}

export function SimpleEmptyState({
  icon,
  title,
  description,
  onAction,
  actionText,
}: SimpleEmptyStateProps) {
  return (
    <div className="analytics-glass-card p-6 rounded-sm flex flex-col items-center justify-center min-h-[200px]">
      <MaterialIcon icon={icon} className="text-tiffany/30 text-4xl mb-3" />
      <p className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">
        {title}
      </p>
      {description && (
        <p className="text-xs text-slate-400 dark:text-slate-500 text-center mb-4">
          {description}
        </p>
      )}
      {onAction && actionText && (
        <button
          onClick={onAction}
          className="px-4 py-2 bg-tiffany text-white rounded-md text-xs font-semibold hover:opacity-90 transition-opacity"
        >
          {actionText}
        </button>
      )}
    </div>
  )
}

/**
 * 数据源空状态组件
 */
export function DataSourceEmptyState({
  onAction,
}: {
  onAction?: () => void
}) {
  return (
    <EmptyDocumentState
      title="数据源注册库"
      description="当前没有任何数据源连接，请添加数据库连接以开始分析。"
      iconName="storage"
      onAction={onAction}
      actionText="添加数据源"
    />
  )
}
