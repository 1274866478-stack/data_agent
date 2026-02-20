/**
 * ReportListCard - 报告列表卡片组件
 */

import { MaterialIcon } from '@/components/icons/MaterialIcon'
import { cn } from '@/lib/utils'

export interface Report {
  id: string
  title: string
  description: string
  totalQueries: number
  avgResponse: string
  successRate: number
  createdAt: string
}

interface ReportListCardProps {
  report: Report
  onDownload?: (id: string) => void
  className?: string
}

export function ReportListCard({ report, onDownload, className }: ReportListCardProps) {
  return (
    <div className={cn('reports-glass-card rounded-sm p-5 hover:shadow-lg transition-all duration-200', className)}>
      <div className="report-list-card">
        {/* 左侧：ID + 标题 + 描述 */}
        <div className="min-w-0">
          <span className="report-id-tag">ID: {report.id.toUpperCase()}</span>
          <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-1">
            {report.title}
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 line-clamp-2">
            {report.description}
          </p>
        </div>

        {/* 中间：三列数据 */}
        <div className="flex gap-8">
          <div>
            <p className="analytics-tech-label text-slate-400 mb-1">Total Queries</p>
            <p className="text-lg font-semibold text-slate-700 dark:text-slate-300">
              {report.totalQueries.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="analytics-tech-label text-slate-400 mb-1">Avg Response</p>
            <p className="text-lg font-semibold text-slate-700 dark:text-slate-300">
              {report.avgResponse}
            </p>
          </div>
          <div>
            <p className="analytics-tech-label text-slate-400 mb-1">Success Rate</p>
            <p className="text-lg font-semibold text-tiffany">
              {report.successRate}%
            </p>
          </div>
        </div>

        {/* 右侧：下载按钮 */}
        <button
          onClick={() => onDownload?.(report.id)}
          className="btn-glass px-4 py-2 rounded-lg flex items-center gap-2 btn-download"
        >
          <MaterialIcon icon="download" className="text-sm" />
          <span className="text-sm font-semibold">Download</span>
        </button>
      </div>
    </div>
  )
}
