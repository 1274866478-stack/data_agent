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

