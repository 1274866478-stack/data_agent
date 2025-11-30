'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { ErrorMessage } from '@/components/ui/error-message'
import { DataSourceOverview } from '@/components/data-sources/DataSourceOverview'
import { DataSourceTabs } from '@/components/data-sources/DataSourceTabs'
import { SearchAndFilter } from '@/components/data-sources/SearchAndFilter'
import { BulkOperations } from '@/components/data-sources/BulkOperations'
import { DataSourceList } from '@/components/data-sources/DataSourceList'
import { DocumentList } from '@/components/documents/DocumentList'
import DocumentUpload from '@/components/documents/DocumentUpload'
import { useTenantId } from '@/store/authStore'
import { useDashboardStore } from '@/store/dashboardStore'
import { Database, FileText, Plus, Eye, EyeOff } from 'lucide-react'

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
          <h1 className="text-3xl font-bold tracking-tight">数据源管理</h1>
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

          <Button onClick={() => setIsCreateMode(true)}>
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