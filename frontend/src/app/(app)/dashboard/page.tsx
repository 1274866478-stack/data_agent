/**
 * # DashboardPage 仪表板页面
 *
 * ## [MODULE]
 * **文件名**: app/(app)/dashboard/page.tsx
 * **职责**: 提供系统概览仪表板，展示数据源统计、快捷操作和导航入口
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - 无直接 Props（页面组件）
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 仪表板页面，包含数据源概览和快捷操作卡片
 *
 * ## [LINK]
 * **上游依赖**:
 * - [@/store/dashboardStore](../../../store/dashboardStore.ts) - 提供概览数据和刷新功能
 * - [@/components/data-sources/DataSourceOverview](../../components/data-sources/DataSourceOverview.tsx) - 数据源概览组件
 * - [@/components/ui/button](../../components/ui/button.tsx) - 按钮组件
 * - [@/components/ui/card](../../components/ui/card.tsx) - 卡片容器组件
 * - [lucide-react](https://lucide.dev) - 图标库
 *
 * **下游依赖**:
 * - [/data-sources/page.tsx](./data-sources/page.tsx) - 数据源管理页面
 * - [/documents/page.tsx](./documents/page.tsx) - 文档管理页面
 * - [/ai-assistant/page.tsx](./ai-assistant/page.tsx) - AI助手页面
 * - [/reports/page.tsx](./reports/page.tsx) - 报告页面
 *
 * ## [STATE]
 * - **isLoading: boolean** - 数据加载状态（从 store 获取）
 *
 * ## [SIDE-EFFECTS]
 * - **数据获取**: 组件挂载时自动调用 fetchOverview() 获取概览数据
 * - **手动刷新**: 点击刷新按钮重新获取最新数据
 * - **页面导航**: 提供快捷操作卡片跳转到其他功能页面
 */
'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { DataSourceOverview } from '@/components/data-sources/DataSourceOverview'
import { useDashboardStore } from '@/store/dashboardStore'
import {
  Database,
  FileText,
  Bot,
  BarChart3,
  RefreshCw,
  ArrowRight,
  Plus
} from 'lucide-react'

export default function DashboardPage() {
  const { fetchOverview, isLoading } = useDashboardStore()

  useEffect(() => {
    fetchOverview()
  }, [fetchOverview])

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">仪表板</h1>
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

      {/* 快捷操作卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link href="/data-sources">
          <Card className="hover:shadow-md transition-shadow cursor-pointer group">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Database className="h-5 w-5 text-blue-600" />
                数据源管理
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-3">
                连接和管理您的数据库
              </p>
              <div className="flex items-center text-sm text-primary group-hover:underline">
                前往管理 <ArrowRight className="h-4 w-4 ml-1" />
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/documents">
          <Card className="hover:shadow-md transition-shadow cursor-pointer group">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-5 w-5 text-green-600" />
                文档管理
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-3">
                上传和管理您的文档
              </p>
              <div className="flex items-center text-sm text-primary group-hover:underline">
                查看文档 <ArrowRight className="h-4 w-4 ml-1" />
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/ai-assistant">
          <Card className="hover:shadow-md transition-shadow cursor-pointer group">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Bot className="h-5 w-5 text-purple-600" />
                AI 助手
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-3">
                智能数据分析对话
              </p>
              <div className="flex items-center text-sm text-primary group-hover:underline">
                开始对话 <ArrowRight className="h-4 w-4 ml-1" />
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link href="/analytics">
          <Card className="hover:shadow-md transition-shadow cursor-pointer group">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <BarChart3 className="h-5 w-5 text-orange-600" />
                数据分析
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-3">
                查看分析报告图表
              </p>
              <div className="flex items-center text-sm text-primary group-hover:underline">
                查看分析 <ArrowRight className="h-4 w-4 ml-1" />
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* 快速操作按钮 */}
      <Card>
        <CardHeader>
          <CardTitle>快速操作</CardTitle>
          <CardDescription>
            常用功能的快捷入口
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Button asChild>
              <Link href="/data-sources?action=add">
                <Plus className="h-4 w-4 mr-2" />
                添加数据源
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/documents?action=upload">
                <Plus className="h-4 w-4 mr-2" />
                上传文档
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/ai-assistant">
                <Bot className="h-4 w-4 mr-2" />
                开始 AI 对话
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

