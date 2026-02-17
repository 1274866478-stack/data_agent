'use client'

import { useDashboardStore } from '@/store/dashboardStore'
import { Activity } from 'lucide-react'

export function DataSourceStatsPanel() {
  const { overview } = useDashboardStore()

  if (!overview) return null

  const getPipelineStatus = () => {
    if (overview.documents.processing > 0) return 'processing'
    if (overview.databases.error > 0) return 'error'
    return 'active'
  }

  const status = getPipelineStatus()

  return (
    <div className="datasource-stats-panel">
      <div className="datasource-pipeline-status">
        <Activity className="h-3.5 w-3.5" />
        <span className="datasource-tech-label">
          {status === 'active' ? 'Pipeline Active' : status === 'processing' ? 'Processing' : 'Error'}
        </span>
      </div>

      <div className="datasource-stat-divider" />

      <div className="datasource-stat-item">
        <span className="datasource-stat-label">Sources</span>
        <span className="datasource-stat-value">{overview.databases.total}</span>
      </div>

      <div className="datasource-stat-divider" />

      <div className="datasource-stat-item">
        <span className="datasource-stat-label">Documents</span>
        <span className="datasource-stat-value">{overview.documents.total}</span>
      </div>

      <div className="datasource-stat-divider" />

      <div className="datasource-stat-item">
        <span className="datasource-stat-label">Storage</span>
        <span className="datasource-stat-value">{Math.round(overview.storage.usage_percentage)}%</span>
      </div>
    </div>
  )
}
