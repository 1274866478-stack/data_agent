/**
 * # DataSourcesPage 数据源管理页面
 *
 * ## [MODULE]
 * **文件名**: app/(app)/data-sources/page.tsx
 * **职责**: 提供数据源和文档的统一管理界面，包括列表展示、搜索筛选、批量操作和上传功能
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - 无直接 Props（页面组件）
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 数据源管理页面，包含概览、标签页、搜索、列表和上传界面
 *
 * ## [LINK]
 * **上游依赖**:
 * - [@/store/dashboardStore](../../../store/dashboardStore.ts) - 提供数据源状态管理
 * - [@/store/authStore](../../../store/authStore.ts) - 提供租户ID
 * - [@/components/data-sources/DataSourceOverview](../../components/data-sources/DataSourceOverview.tsx) - 概览组件
 * - [@/components/data-sources/DataSourceTabs](../../components/data-sources/DataSourceTabs.tsx) - 标签页组件
 * - [@/components/data-sources/SearchAndFilter](../../components/data-sources/SearchAndFilter.tsx) - 搜索筛选组件
 * - [@/components/data-sources/BulkOperations](../../components/data-sources/BulkOperations.tsx) - 批量操作组件
 * - [@/components/data-sources/DataSourceList](../../components/data-sources/DataSourceList.tsx) - 数据源列表
 * - [@/components/documents/DocumentList](../../components/documents/DocumentList.tsx) - 文档列表
 * - [DocumentUpload](../../components/documents/DocumentUpload.tsx) - 文档上传组件
 * - [@/components/ui/button](../../components/ui/button.tsx) - 按钮组件
 * - [lucide-react](https://lucide.dev) - 图标库
 *
 * **下游依赖**:
 * - 无（页面是用户交互入口点）
 *
 * ## [STATE]
 * - **tenantId: string** - 当前租户ID（从 authStore 获取）
 * - **overview: DashboardOverview | null** - 数据源概览（从 dashboardStore 获取）
 * - **searchResults: SearchResult[]** - 搜索和筛选结果
 * - **isLoading: boolean** - 加载状态
 * - **error: string | null** - 错误信息
 * - **activeTab: 'databases' | 'documents'** - 当前活动标签页
 * - **selectedItems: string[]** - 已选中的项目ID列表
 * - **showOverview: boolean** - 是否显示概览面板
 * - **isCreateMode: boolean** - 是否处于创建模式（添加数据源或上传文档）
 *
 * ## [SIDE-EFFECTS]
 * - **数据获取**: 组件挂载时自动调用 fetchOverview() 和 searchDataSources()
 * - **租户验证**: 检查租户ID是否存在，不存在时显示认证错误
 * - **标签切换**: 切换数据库/文档标签时重新搜索数据
 * - **选择同步**: 处理批量选择状态变化
 * - **数据刷新**: 提供手动刷新功能
 * - **上传处理**: 处理文档上传成功和错误回调
 * - **模式切换**: 在管理界面和创建界面之间切换
 */
'use client'

import { BulkOperations } from '@/components/data-sources/BulkOperations'
import { DataSourceList } from '@/components/data-sources/DataSourceList'
import { DataSourceOverview } from '@/components/data-sources/DataSourceOverview'
import { DataSourceTabs } from '@/components/data-sources/DataSourceTabs'
import { SearchAndFilter } from '@/components/data-sources/SearchAndFilter'
import { DocumentList } from '@/components/documents/DocumentList'
import DocumentUpload from '@/components/documents/DocumentUpload'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ErrorMessage } from '@/components/ui/error-message'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { useTenantId } from '@/store/authStore'
import { useDashboardStore } from '@/store/dashboardStore'
import { Eye, EyeOff, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'

export default function DataSourcesPage() {
  const tenantId = useTenantId()
  const {
    overview,
    searchResults,
    isLoading,
    error,
    activeTab,
    selectedItems,
    fetchOverview,
    searchDataSources,
    clearError,
  } = useDashboardStore()

  const [showOverview, setShowOverview] = useState(true)
  const [isCreateMode, setIsCreateMode] = useState(false)

  // 获取初始数据
  useEffect(() => {
    if (tenantId) {
      fetchOverview()
      searchDataSources(1)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId])

  // 如果租户ID不存在，说明用户未正确认证
  if (!tenantId) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">认证错误</h1>
          <p className="text-gray-600">无法获取租户信息，请重新登录。</p>
        </div>
      </div>
    )
  }

  // 处理标签页切换
  const handleTabChange = (tab: 'databases' | 'documents') => {
    const { setActiveTab } = useDashboardStore.getState()
    setActiveTab(tab)
    searchDataSources(1)
  }

  // 处理选择变化
  const handleSelectionChange = (newSelection: string[]) => {
    const { setSelectedItems } = useDashboardStore.getState()
    setSelectedItems(newSelection)
  }

  // 刷新数据
  const handleRefresh = () => {
    fetchOverview()
    searchDataSources(1)
    clearError()
  }

  // 处理上传成功
  const handleUploadSuccess = (files: File[]) => {
    // 成功后刷新列表并退出创建模式
    handleRefresh()
    setIsCreateMode(false)
  }

  // 处理上传错误
  const handleUploadError = (errorMessage: string) => {
    console.error('Upload error:', errorMessage)
  }

  if (isCreateMode) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">
            {activeTab === 'databases' ? '添加数据库连接' : '上传文档'}
          </h2>
          <Button variant="outline" onClick={() => setIsCreateMode(false)}>
            返回管理界面
          </Button>
        </div>

        {activeTab === 'databases' ? (
          <DataSourceList
            tenantId={tenantId}
            onDataSourceSelect={() => {}}
          />
        ) : (
          <DocumentUpload
            onClose={() => setIsCreateMode(false)}
            onSuccess={handleUploadSuccess}
            onError={handleUploadError}
          />
        )}
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      {/* 页面标题和操作 */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">数据源管理</h1>
          <p className="text-muted-foreground">
            管理您的数据库连接和文档，进行数据分析和处理
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowOverview(!showOverview)}
            className="hidden sm:flex"
          >
            {showOverview ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
            {showOverview ? '隐藏概览' : '显示概览'}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            {isLoading ? <LoadingSpinner className="h-4 w-4 mr-2" /> : null}
            刷新
          </Button>

          <Button onClick={() => setIsCreateMode(true)} className="bg-gradient-modern-primary hover:opacity-90 transition-opacity">
            <Plus className="h-4 w-4 mr-2" />
            添加数据源
          </Button>
        </div>
      </div>

      {/* 错误信息 */}
      {error && <ErrorMessage message={error} />}

      {/* 概览仪表板 */}
      {showOverview && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">数据源概览</CardTitle>
              <Badge variant="outline" className="text-xs">
                实时数据
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <DataSourceOverview />
          </CardContent>
        </Card>
      )}

      {/* 搜索和筛选 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">搜索和筛选</CardTitle>
        </CardHeader>
        <CardContent>
          <SearchAndFilter />
        </CardContent>
      </Card>

      {/* 数据源标签页和内容 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">
              {activeTab === 'databases' ? '数据库连接' : '文档管理'}
            </CardTitle>
            {selectedItems.length > 0 && (
              <Badge variant="secondary">
                已选择 {selectedItems.length} 项
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <DataSourceTabs
            databasesContent={
              <div className="space-y-4">
                {selectedItems.length > 0 ? (
                  <BulkOperations
                    items={searchResults.filter(item => item.type === 'database')}
                    selectedItems={selectedItems}
                    onSelectionChange={handleSelectionChange}
                    onRefresh={handleRefresh}
                  />
                ) : (
                  <DataSourceList
                    tenantId={tenantId}
                    onDataSourceSelect={() => {}}
                  />
                )}
              </div>
            }
            documentsContent={
              <div className="space-y-4">
                {selectedItems.length > 0 ? (
                  <BulkOperations
                    items={searchResults.filter(item => item.type === 'document')}
                    selectedItems={selectedItems}
                    onSelectionChange={handleSelectionChange}
                    onRefresh={handleRefresh}
                  />
                ) : (
                  <DocumentList />
                )}
              </div>
            }
          />
        </CardContent>
      </Card>

      {/* 响应式设计：移动端概览切换按钮 */}
      <div className="sm:hidden fixed bottom-4 right-4 z-10">
        <Button
          size="sm"
          onClick={() => setShowOverview(!showOverview)}
          className="rounded-full shadow-lg"
        >
          {showOverview ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  )
}