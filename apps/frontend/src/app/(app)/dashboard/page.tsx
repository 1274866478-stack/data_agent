/**
 * # DashboardPage 仪表板页面
 *
 * ## [MODULE]
 * **文件名**: app/(app)/dashboard/page.tsx
 * **职责**: 提供系统概览仪表板，展示数据源状态和系统概览（Glassmorphism Console 风格）
 * **作者**: Data Agent Team
 * **版本**: 2.0.0 - Glassmorphism Console
 *
 * ## [INPUT]
 * - 无直接 Props（页面组件）
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 仪表板页面，包含数据源概览
 *
 * ## [LINK]
 * **上游依赖**:
 * - [@/store/dashboardStore](../../../store/dashboardStore.ts) - 提供概览数据和刷新功能
 * - [@/components/data-sources/DataSourceOverview](../../components/data-sources/DataSourceOverview.tsx) - 数据源概览组件
 * - [@/components/ui/button](../../components/ui/button.tsx) - 按钮组件
 * - [lucide-react](https://lucide.dev) - 图标库
 */
'use client'

import { DataSourceOverview } from '@/components/data-sources/DataSourceOverview'
import { Button } from '@/components/ui/button'
import { useDashboardStore } from '@/store/dashboardStore'
import { RefreshCw } from 'lucide-react'
import { useEffect } from 'react'

export default function DashboardPage() {
  const { fetchOverview, isLoading } = useDashboardStore()

  useEffect(() => {
    fetchOverview()
  }, [fetchOverview])

  return (
    <div className="bg-mesh min-h-screen p-6">
      <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">仪表板</h1>
          <p className="text-muted-foreground">
            查看您的数据源状态和系统概览
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => fetchOverview()}
          disabled={isLoading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          刷新数据
        </Button>
      </div>

      {/* 数据源概览组件 */}
      <DataSourceOverview />
      </div>
    </div>
  )
}
