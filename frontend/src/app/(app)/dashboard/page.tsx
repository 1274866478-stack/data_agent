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

import { DataSourceOverview } from '@/components/data-sources/DataSourceOverview'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { GradientCard, GradientCardContent, GradientCardHeader, GradientCardTitle } from '@/components/ui/gradient-card'
import { useDashboardStore } from '@/store/dashboardStore'
import {
    ArrowRight,
    BarChart3,
    Bot,
    Database,
    FileText,
    Plus,
    RefreshCw
} from 'lucide-react'
import Link from 'next/link'
import { useEffect } from 'react'

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
          <h1 className="text-3xl font-bold text-white">仪表板</h1>
          <p className="text-gray-300">
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
          <GradientCard gradient="accent" className="cursor-pointer group h-full">
            <GradientCardHeader className="pb-3">
              <GradientCardTitle className="flex items-center gap-2 text-base">
                <div className="p-2 bg-blue-100 dark:bg-blue-500/20 rounded-lg">
                  <Database className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                数据源管理
              </GradientCardTitle>
            </GradientCardHeader>
            <GradientCardContent>
              <p className="text-sm text-muted-foreground mb-3">
                连接和管理您的数据库
              </p>
              <div className="flex items-center text-sm text-blue-600 dark:text-blue-400 font-medium group-hover:underline">
                前往管理 <ArrowRight className="h-4 w-4 ml-1 transition-transform group-hover:translate-x-1" />
              </div>
            </GradientCardContent>
          </GradientCard>
        </Link>

        <Link href="/documents">
          <GradientCard gradient="success" className="cursor-pointer group h-full">
            <GradientCardHeader className="pb-3">
              <GradientCardTitle className="flex items-center gap-2 text-base">
                <div className="p-2 bg-green-100 dark:bg-green-500/20 rounded-lg">
                  <FileText className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                文档管理
              </GradientCardTitle>
            </GradientCardHeader>
            <GradientCardContent>
              <p className="text-sm text-muted-foreground mb-3">
                上传和管理您的文档
              </p>
              <div className="flex items-center text-sm text-green-600 dark:text-green-400 font-medium group-hover:underline">
                查看文档 <ArrowRight className="h-4 w-4 ml-1 transition-transform group-hover:translate-x-1" />
              </div>
            </GradientCardContent>
          </GradientCard>
        </Link>

        <Link href="/ai-assistant">
          <GradientCard gradient="primary" className="cursor-pointer group h-full">
            <GradientCardHeader className="pb-3">
              <GradientCardTitle className="flex items-center gap-2 text-base">
                <div className="p-2 bg-violet-100 dark:bg-violet-500/20 rounded-lg">
                  <Bot className="h-5 w-5 text-violet-600 dark:text-violet-400" />
                </div>
                AI 助手
              </GradientCardTitle>
            </GradientCardHeader>
            <GradientCardContent>
              <p className="text-sm text-muted-foreground mb-3">
                智能数据分析对话
              </p>
              <div className="flex items-center text-sm text-violet-600 dark:text-violet-400 font-medium group-hover:underline">
                开始对话 <ArrowRight className="h-4 w-4 ml-1 transition-transform group-hover:translate-x-1" />
              </div>
            </GradientCardContent>
          </GradientCard>
        </Link>

        <Link href="/analytics">
          <GradientCard gradient="warning" className="cursor-pointer group h-full">
            <GradientCardHeader className="pb-3">
              <GradientCardTitle className="flex items-center gap-2 text-base">
                <div className="p-2 bg-orange-100 dark:bg-orange-500/20 rounded-lg">
                  <BarChart3 className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                </div>
                数据分析
              </GradientCardTitle>
            </GradientCardHeader>
            <GradientCardContent>
              <p className="text-sm text-muted-foreground mb-3">
                查看分析报告图表
              </p>
              <div className="flex items-center text-sm text-orange-600 dark:text-orange-400 font-medium group-hover:underline">
                查看分析 <ArrowRight className="h-4 w-4 ml-1 transition-transform group-hover:translate-x-1" />
              </div>
            </GradientCardContent>
          </GradientCard>
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

