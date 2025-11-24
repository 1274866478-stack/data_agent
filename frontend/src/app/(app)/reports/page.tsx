'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText, Download, Calendar, TrendingUp, AlertCircle } from 'lucide-react'

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
          <h1 className="text-3xl font-bold">报告中心</h1>
          <p className="text-muted-foreground mt-2">查看和下载系统性能报告与分析报告</p>
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

