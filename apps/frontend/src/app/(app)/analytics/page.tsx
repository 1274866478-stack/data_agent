/**
 * [HEADER]
 * 数据分析页面 - Data Agent V4 Analytics Dashboard
 * Tiffany 玻璃态风格 UI 一比一复刻实现
 *
 * [MODULE]
 * 模块类型: Next.js 14 App Router Page Component
 * 所属功能: 数据可视化与分析
 * 技术栈: React, TypeScript, Zustand, Tailwind CSS
 *
 * [INPUT]
 * - 无路由参数
 * - 依赖的全局状态:
 *   - tenantId (useTenantId): 当前租户ID
 *   - overview (useDashboardStore): 概览数据
 *   - dataSources (useDataSourceStore): 数据源列表
 *   - documents (useDocumentStore): 文档列表
 *
 * [OUTPUT]
 * - 渲染内容:
 *   - 页面标题和操作按钮 (刷新、导出)
 *   - 统计卡片区 (数据源、文档总量、内存占用、数字资产)
 *   - 图表区 (数据源分布环形图、文档注册库空状态)
 *   - 实时活动日志表格
 * - 用户交互:
 *   - 刷新数据按钮 (handleRefresh)
 *   - 浮动操作按钮 (FAB)
 *
 * [LINK]
 * - 依赖组件:
 *   - @/components/analytics/DonutChart - 环形图
 *   - @/components/analytics/ActivityLogTable - 活动日志表格
 *   - @/components/analytics/EmptyDocumentState - 空状态
 *   - @/components/icons/MaterialIcon - Material 图标
 * - 依赖状态管理:
 *   - @/store/authStore - useTenantId
 *   - @/store/dashboardStore - fetchOverview
 *   - @/store/dataSourceStore - fetchDataSources
 *   - @/store/documentStore - fetchDocuments
 * - 路由:
 *   - /analytics - 当前页面路由
 *
 * [POS]
 * - 文件路径: frontend/src/app/(app)/analytics/page.tsx
 * - 访问URL: http://localhost:3000/analytics
 * - 布局位置: (app) 路由组, 继承主应用布局
 *
 * [STATE]
 * - 局部状态:
 *   - isRefreshing: boolean - 刷新状态标记
 * - 衍生状态 (useMemo):
 *   - stats - 统计数据对象
 *   - activityLogs - 活动日志数组
 * - 副作用:
 *   - useEffect: 加载初始数据 (tenantId变化时)
 *   - handleRefresh: 手动刷新所有数据
 *
 * [PROTOCOL]
 * - 初始化流程:
 *   1. 从 authStore 获取 tenantId
 *   2. 并行调用 fetchOverview, fetchDataSources, fetchDocuments
 *   3. 计算统计指标和活动日志数据
 * - 数据刷新机制:
 *   - 自动刷新: tenantId 变化时触发
 *   - 手动刷新: 点击刷新按钮, 防抖处理
 * - 错误处理:
 *   - 租户未认证: 显示认证错误提示
 * - 性能优化:
 *   - useMemo 缓存统计计算结果
 *   - Promise.all 并行数据请求
 */

'use client'

import { EmptyDocumentState } from '@/components/analytics/EmptyDocumentState'
import { ActivityLogTable, type ActivityLog } from '@/components/analytics/ActivityLogTable'
import { DonutChart } from '@/components/analytics/DonutChart'
import { MaterialIcon } from '@/components/icons/MaterialIcon'
import { useTenantId } from '@/store/authStore'
import { useDashboardStore } from '@/store/dashboardStore'
import { useDataSourceStore } from '@/store/dataSourceStore'
import { useDocumentStore } from '@/store/documentStore'
import { useEffect, useMemo, useState } from 'react'

/**
 * 数据分析页面
 *
 * Tiffany 玻璃态风格的数据分析控制台
 */
export default function AnalyticsPage() {
  const { overview, fetchOverview } = useDashboardStore()
  const { dataSources, fetchDataSources } = useDataSourceStore()
  const { documents, fetchDocuments } = useDocumentStore()
  const tenantId = useTenantId()

  const [isRefreshing, setIsRefreshing] = useState(false)

  useEffect(() => {
    if (tenantId) {
      fetchOverview()
      fetchDataSources(tenantId)
      fetchDocuments()
    }
  }, [tenantId, fetchOverview, fetchDataSources, fetchDocuments])

  /**
   * 统计数据
   */
  const stats = useMemo(() => {
    return {
      dataSources: dataSources.length,
      activeDataSources: dataSources.filter(ds => ds.status === 'active').length,
      documents: documents.length,
      storage: (documents.reduce((sum, doc) => sum + (doc.file_size || 0), 0) / (1024 ** 3)).toFixed(1),
      nodes: dataSources.length + documents.length
    }
  }, [dataSources, documents])

  /**
   * 活动日志数据
   */
  const activityLogs = useMemo(() => {
    return overview?.recent_activity?.map(a => ({
      id: a.id,
      status: (a.status === 'success' ? 'success' : 'warning') as ActivityLog['status'],
      sourceId: a.item_name.toUpperCase().replace(/\s/g, '_'),
      operation: `${a.action === 'created' ? '创建' : a.action === 'updated' ? '更新' : '测试'} • 静态注入`,
      timestamp: new Date(a.timestamp).toISOString().replace('T', ' ').substring(0, 23)
    })) || []
  }, [overview])

  /**
   * 刷新所有数据
   */
  const handleRefresh = async () => {
    if (!tenantId) return
    setIsRefreshing(true)
    try {
      await Promise.all([
        fetchOverview(),
        fetchDataSources(tenantId),
        fetchDocuments()
      ])
    } finally {
      setIsRefreshing(false)
    }
  }

  // 租户未认证提示
  if (!tenantId) {
    return (
      <div className="min-h-screen bg-analytics-gradient flex items-center justify-center">
        <div className="text-center space-y-4">
          <MaterialIcon icon="lock" className="text-6xl text-tiffany/40 mx-auto" />
          <h1 className="text-2xl font-bold text-slate-800">认证错误</h1>
          <p className="text-slate-500">无法获取租户信息，请重新登录。</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-analytics-gradient overflow-y-auto p-8">
      {/* Header */}
      <header className="flex justify-between items-end mb-10">
        <div>
          <h1 className="text-3xl font-extralight text-slate-900 tracking-tight uppercase">
            数据分析控制台
          </h1>
          <p className="analytics-tech-label mt-1 text-tiffany">
            Data Analysis Control Console / Digital Assets Environment
          </p>
        </div>
        <div className="flex items-center gap-6">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 analytics-tech-label text-slate-400 hover:text-tiffany transition-colors disabled:opacity-50"
          >
            <MaterialIcon icon="refresh" className="text-sm" />
            刷新内核
          </button>
          <button className="flex items-center gap-2 analytics-tech-label text-slate-400 hover:text-tiffany transition-colors">
            <MaterialIcon icon="download" className="text-sm" />
            导出报告
          </button>
        </div>
      </header>

      {/* Stats Cards */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* 数据源卡片 */}
        <div className="analytics-glass-card p-5 rounded-sm relative group overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <MaterialIcon icon="storage" className="text-4xl" />
          </div>
          <p className="analytics-tech-label mb-4">数据源</p>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-light text-slate-800 tracking-tighter leading-none">
              {String(stats.dataSources).padStart(2, '0')}
            </span>
            <span className="text-[10px] text-emerald-500 font-bold uppercase">Active</span>
          </div>
          <div className="mt-4 h-[1px] w-full bg-tiffany/20 relative">
            <div className="absolute inset-y-0 left-0 w-3/4 bg-tiffany"></div>
          </div>
        </div>

        {/* 文档总量卡片 */}
        <div className="analytics-glass-card p-5 rounded-sm relative group">
          <p className="analytics-tech-label mb-4">文档总量</p>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-light text-slate-800 tracking-tighter leading-none">
              {String(stats.documents).padStart(4, '0')}
            </span>
            <span className="text-[10px] text-slate-400 font-bold uppercase">Index</span>
          </div>
          <div className="mt-4 h-[1px] w-full bg-tiffany/20"></div>
        </div>

        {/* 内存占用卡片 */}
        <div className="analytics-glass-card p-5 rounded-sm relative group">
          <p className="analytics-tech-label mb-4">内存占用</p>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-light text-slate-800 tracking-tighter leading-none">
              {stats.storage}
            </span>
            <span className="text-[10px] text-slate-400 font-bold uppercase">GB</span>
          </div>
          <div className="mt-4 h-[1px] w-full bg-tiffany/20 relative overflow-hidden">
            <div className="absolute inset-y-0 left-0 w-1/4 bg-tiffany shadow-[0_0_8px_#81d8cf]"></div>
          </div>
        </div>

        {/* 数字资产卡片 */}
        <div className="analytics-glass-card p-5 rounded-sm relative group">
          <p className="analytics-tech-label mb-4">数字资产</p>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-light text-slate-800 tracking-tighter leading-none">
              {String(stats.nodes).padStart(2, '0')}
            </span>
            <span className="text-[10px] text-tiffany font-bold uppercase">Nodes</span>
          </div>
          <div className="mt-4 h-[1px] w-full bg-tiffany/20"></div>
        </div>
      </section>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* 数据源分布 */}
        <div className="analytics-glass-card p-8 rounded-sm min-h-[400px]">
          <div className="flex justify-between items-start mb-12">
            <div>
              <h3 className="analytics-tech-label text-slate-800">数据源分布</h3>
              <p className="text-[10px] text-slate-400 mt-1 uppercase">Multicluster Source Distribution</p>
            </div>
            <MaterialIcon icon="hub" className="text-slate-300" />
          </div>
          <div className="flex items-center justify-center gap-16">
            <DonutChart percentage={stats.activeDataSources > 0 ? 65 : 0} subLabel={`${stats.activeDataSources > 0 ? '65' : '0'}%`} label="主节点" />
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <div className="analytics-status-dot bg-tiffany analytics-glow-tiffany"></div>
                <div>
                  <p className="analytics-tech-label text-slate-400 uppercase tracking-widest">
                    PostgreSQL Cluster
                  </p>
                  <p className="text-lg font-light text-slate-800 leading-none mt-1">
                    {String(stats.activeDataSources).padStart(2, '0')}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="analytics-status-dot bg-slate-300"></div>
                <div>
                  <p className="analytics-tech-label text-slate-400 uppercase tracking-widest">
                    Excel Static Data
                  </p>
                  <p className="text-lg font-light text-slate-800 leading-none mt-1">00</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 文档注册库 */}
        <EmptyDocumentState />
      </div>

      {/* Activity Log */}
      <ActivityLogTable activities={activityLogs} />

      {/* Floating Action Button */}
      <button className="fixed bottom-8 right-8 w-14 h-14 bg-tiffany text-white rounded-full flex items-center justify-center shadow-[0_8px_25px_rgba(129,216,207,0.5)] hover:scale-110 transition-transform z-50">
        <MaterialIcon icon="add" className="text-3xl" />
      </button>
    </div>
  )
}
