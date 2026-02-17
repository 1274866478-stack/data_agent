'use client'

import { ReportStatCard } from '@/components/reports/ReportStatCard'
import { ReportListCard, type Report } from '@/components/reports/ReportListCard'
import { ReportPagination } from '@/components/reports/ReportPagination'
import { MaterialIcon } from '@/components/icons/MaterialIcon'
import { useEffect, useState } from 'react'

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 6

  useEffect(() => {
    loadReports()
  }, [])

  const loadReports = async () => {
    try {
      setLoading(true)

      // 模拟数据
      const mockReports: Report[] = [
        {
          id: 'rpt-001',
          title: '本周性能分析报告',
          description: '系统运行稳定，所有关键性能指标均优于基准值。AI Agent 查询响应时间平均降低至 1.2 秒。',
          totalQueries: 1250,
          avgResponse: '1.2s',
          successRate: 98.5,
          createdAt: '2025-01-24'
        },
        {
          id: 'rpt-002',
          title: '数据源使用情况月度审计',
          description: '核心数据库连接率稳定。各部门数据使用频率较上月平均提升了 15%，尤其是营销与研发部门。',
          totalQueries: 850,
          avgResponse: '0.9s',
          successRate: 99.2,
          createdAt: '2025-01-23'
        },
        {
          id: 'rpt-003',
          title: '年度系统扩展性预测报告',
          description: '基于近三个月增长趋势，预计未来半年需增加 20% 的计算节点以满足增长的查询需求。',
          totalQueries: 12400,
          avgResponse: '1.5s',
          successRate: 97.8,
          createdAt: '2025-01-22'
        }
      ]

      setReports(mockReports)
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = (id: string) => {
    console.log('下载报告:', id)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-reports-gradient flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-2 border-tiffany border-t-transparent rounded-full animate-spin" />
          <p className="analytics-tech-label text-slate-400">Loading Reports...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-reports-gradient p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="w-2 h-2 bg-tiffany rounded-full animate-pulse shadow-[0_0_8px_#81d8cf]" />
              <span className="analytics-tech-label text-tiffany">Laboratory Control</span>
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              报告中心
            </h1>
          </div>
          <button className="btn-glass px-8 py-3 rounded-xl">
            <span className="relative z-10 flex items-center gap-2">
              <MaterialIcon icon="add_circle" />
              生成新报告
            </span>
          </button>
        </header>

        {/* Stats Cards */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
          <ReportStatCard
            label="Report Volume"
            icon="query_stats"
            value={24}
            trend={{ label: '+12.5%', type: 'positive' }}
            bars={[30, 50, 40, 70, 45, 90, 60]}
          />
          <ReportStatCard
            label="Latency Monitoring"
            icon="speed"
            value="1.05s"
            trend={{ label: '-8%', type: 'positive' }}
            bars={[60, 55, 65, 50, 45, 40, 35]}
          />
        </section>

        {/* Reports List */}
        <section>
          <div className="flex items-center justify-between mb-8">
            <h4 className="text-xl font-bold flex items-center gap-3">
              <MaterialIcon icon="history" className="text-tiffany" />
              最近分析报告
            </h4>
            <div className="flex gap-2">
              <button className="p-2 rounded-lg hover:bg-white dark:hover:bg-slate-800 border border-transparent hover:border-slate-200 dark:hover:border-slate-700 transition-all">
                <MaterialIcon icon="tune" />
              </button>
            </div>
          </div>

          <div className="space-y-4">
            {reports.map((report) => (
              <ReportListCard
                key={report.id}
                report={report}
                onDownload={handleDownload}
              />
            ))}
          </div>

          {/* Pagination */}
          <div className="mt-8 pt-8 border-t border-slate-200/50 dark:border-slate-800/50 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="analytics-tech-label text-slate-400">
              Displaying 01-03 of 24 Lab Reports
            </p>
            <div className="flex items-center gap-2">
              <button className="w-10 h-10 flex items-center justify-center border border-slate-200 dark:border-slate-800 rounded-lg hover:bg-white dark:hover:bg-slate-800 transition-all">
                <MaterialIcon icon="chevron_left" />
              </button>
              <button className="w-10 h-10 flex items-center justify-center bg-tiffany text-slate-900 font-bold rounded-lg shadow-[0_0_10px_rgba(129,216,207,0.4)]">
                1
              </button>
              <button className="w-10 h-10 flex items-center justify-center border border-slate-200 dark:border-slate-800 rounded-lg hover:bg-white dark:hover:bg-slate-800 transition-all font-bold">
                2
              </button>
              <button className="w-10 h-10 flex items-center justify-center border border-slate-200 dark:border-slate-800 rounded-lg hover:bg-white dark:hover:bg-slate-800 transition-all font-bold">
                3
              </button>
              <button className="w-10 h-10 flex items-center justify-center border border-slate-200 dark:border-slate-800 rounded-lg hover:bg-white dark:hover:bg-slate-800 transition-all">
                <MaterialIcon icon="chevron_right" />
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
