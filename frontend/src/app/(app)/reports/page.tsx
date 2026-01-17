/**
 * [HEADER]
 * 报告中心页面 - Data Agent V4 Reports Center
 * 提供系统性能报告与分析报告的查看和下载功能
 *
 * [MODULE]
 * 模块类型: Next.js 14 App Router Page Component
 * 所属功能: 报告管理与生成
 * 技术栈: React, TypeScript, Lucide Icons
 *
 * [INPUT]
 * - 无路由参数
 * - 无依赖的全局状态 (当前使用模拟数据)
 * - 未来将接入后端API:
 *   - GET /api/v1/reports - 获取报告列表
 *   - GET /api/v1/reports/{id} - 获取报告详情
 *   - POST /api/v1/reports/generate - 生成新报告
 *   - GET /api/v1/reports/{id}/download - 下载报告
 *
 * [OUTPUT]
 * - 渲染内容:
 *   - 统计卡片 (总报告数、平均响应时间)
 *   - 报告列表 (标题、类型、创建时间、摘要)
 *   - 报告指标展示 (总查询数、平均响应时间、成功率)
 *   - 下载按钮
 * - 用户交互:
 *   - 生成新报告按钮 (功能待实现)
 *   - 下载报告功能 (handleDownloadReport)
 *   - 加载状态显示
 *   - 错误重试机制
 *
 * [LINK]
 * - 依赖组件:
 *   - @/components/ui/card - Card组件族
 *   - @/components/ui/button - Button组件
 *   - @/components/ui/input - Input组件 (搜索框)
 * - 图标库:
 *   - lucide-react - FileText, Download, Calendar, TrendingUp, AlertCircle
 * - 路由:
 *   - /reports - 当前页面路由
 * - 后端API (规划中):
 *   - /api/v1/reports - 报告管理端点
 *
 * [POS]
 * - 文件路径: frontend/src/app/(app)/reports/page.tsx
 * - 访问URL: http://localhost:3000/reports
 * - 布局位置: (app) 路由组, 继承主应用布局
 * - 导航入口: 侧边栏 "报告中心" 菜单项
 *
 * [STATE]
 * - 局部状态:
 *   - reports: PerformanceReport[] - 报告列表
 *   - loading: boolean - 加载状态
 *   - error: string | null - 错误信息
 * - 数据接口:
 *   - PerformanceReport - 报告数据结构
 *     - id: string - 报告ID
 *     - title: string - 报告标题
 *     - type: string - 报告类型 (performance, analytics等)
 *     - created_at: string - 创建时间
 *     - summary: string - 报告摘要
 *     - metrics: - 性能指标
 *       - total_queries: number - 总查询数
 *       - avg_response_time: number - 平均响应时间
 *       - success_rate: number - 成功率
 *
 * [PROTOCOL]
 * - 初始化流程:
 *   1. 组件挂载时调用 loadReports()
 *   2. 显示加载状态 (spinner + 文字提示)
 *   3. 加载成功后渲染报告列表
 * - 数据加载:
 *   - 当前状态: 使用模拟数据 (mockReports)
 *   - TODO: 替换为真实API调用
 *   - 错误处理: 显示错误卡片, 提供重试按钮
 * - 用户操作:
 *   - 下载报告: 控制台日志输出 (TODO: 实现实际下载)
 *   - 生成报告: 按钮存在但功能待实现
 * - 空状态处理:
 *   - 无报告时显示空列表
 * - 响应式布局:
 *   - 移动端: 单列布局
 *   - 平板: 双列布局
 *   - 桌面: 三列布局
 */

'use client'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertCircle, Calendar, Download, FileText, TrendingUp } from 'lucide-react'
import { useEffect, useState } from 'react'

interface PerformanceReport {
  id: string
  title: string
  type: string
  created_at: string
  summary: string
  metrics: {
    total_queries: number
    avg_response_time: number
    success_rate: number
  }
}

export default function ReportsPage() {
  const [reports, setReports] = useState<PerformanceReport[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadReports()
  }, [])

  const loadReports = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // TODO: 调用后端API获取报告列表
      // const response = await fetch('/api/v1/reports')
      // const data = await response.json()
      
      // 模拟数据
      const mockReports: PerformanceReport[] = [
        {
          id: '1',
          title: '本周性能报告',
          type: 'performance',
          created_at: new Date().toISOString(),
          summary: '本周系统运行稳定，查询响应时间平均为 1.2 秒',
          metrics: {
            total_queries: 1250,
            avg_response_time: 1.2,
            success_rate: 98.5
          }
        },
        {
          id: '2',
          title: '数据源使用分析',
          type: 'analytics',
          created_at: new Date(Date.now() - 86400000).toISOString(),
          summary: '数据源连接稳定，使用率较上周提升 15%',
          metrics: {
            total_queries: 850,
            avg_response_time: 0.9,
            success_rate: 99.2
          }
        }
      ]
      
      setReports(mockReports)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载报告失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadReport = (reportId: string) => {
    // TODO: 实现报告下载功能
    console.log('下载报告:', reportId)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">加载报告中...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              加载失败
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={loadReports}>重试</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">报告中心</h1>
          <p className="text-gray-300 mt-2">查看和下载系统性能报告与分析报告</p>
        </div>
        <Button>
          <Calendar className="h-4 w-4 mr-2" />
          生成新报告
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* 统计卡片 */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总报告数</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{reports.length}</div>
            <p className="text-xs text-muted-foreground">最近30天</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">平均响应时间</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1.05s</div>
            <p className="text-xs text-muted-foreground">较上周 -8%</p>
          </CardContent>
        </Card>
      </div>

      {/* 报告列表 */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">最近报告</h2>
        {reports.map((report) => (
          <Card key={report.id}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle>{report.title}</CardTitle>
                  <CardDescription>
                    {new Date(report.created_at).toLocaleDateString('zh-CN')}
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={() => handleDownloadReport(report.id)}>
                  <Download className="h-4 w-4 mr-2" />
                  下载
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground mb-4">{report.summary}</p>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">总查询数</p>
                  <p className="text-lg font-semibold">{report.metrics.total_queries}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">平均响应时间</p>
                  <p className="text-lg font-semibold">{report.metrics.avg_response_time}s</p>
                </div>
                <div>
                  <p className="text-muted-foreground">成功率</p>
                  <p className="text-lg font-semibold">{report.metrics.success_rate}%</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

