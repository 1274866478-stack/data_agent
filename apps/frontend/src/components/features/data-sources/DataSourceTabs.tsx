/**
 * # DataSourceTabs 数据源标签页组件
 *
 * ## [MODULE]
 * **文件名**: DataSourceTabs.tsx
 * **职责**: 提供数据库连接和文档管理的标签页切换功能，显示各类别的数据数量
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - **databasesContent: React.ReactNode** - 数据库连接标签页的内容
 * - **documentsContent: React.ReactNode** - 文档管理标签页的内容
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 标签页导航组件，包含数据库和文档两个标签页
 *
 * ## [LINK]
 * **上游依赖**:
 * - [@/store/dashboardStore](../../store/dashboardStore.ts) - 管理当前活动标签页和数据概览
 * - [@/components/ui/tabs](../ui/tabs.tsx) - 标签页基础组件
 * - [@/components/ui/badge](../ui/badge.tsx) - 数量徽章组件
 * - [lucide-react](https://lucide.dev) - 图标库
 *
 * **下游依赖**:
 * - [../../app/(app)/data-sources/page.tsx](../../app/(app)/data-sources/page.tsx) - 在数据源页面中使用
 * - [../../app/(app)/dashboard/page.tsx](../../app/(app)/dashboard/page.tsx) - 在仪表板页面中使用
 *
 * ## [STATE]
 * - **activeTab: 'databases' | 'documents'** - 当前活动的标签页（从 store 获取）
 * - **databaseCount: number** - 数据库连接总数（从 overview 获取）
 * - **documentCount: number** - 文档总数（从 overview 获取）
 *
 * ## [SIDE-EFFECTS]
 * - **状态同步**: 通过 setActiveTab 同步当前标签页状态到 store
 * - **UI更新**: 标签切换时自动显示对应的内容组件
 */
'use client'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Database, FileText } from 'lucide-react'
import { useDashboardStore } from '@/store/dashboardStore'

interface DataSourceTabsProps {
  databasesContent: React.ReactNode
  documentsContent: React.ReactNode
}

export const DataSourceTabs: React.FC<DataSourceTabsProps> = ({
  databasesContent,
  documentsContent,
}) => {
  const { activeTab, setActiveTab, overview } = useDashboardStore()

  const databaseCount = overview?.databases.total || 0
  const documentCount = overview?.documents.total || 0

  return (
    <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'databases' | 'documents')}>
      <TabsList className="grid w-full grid-cols-2">
        <TabsTrigger value="databases" className="flex items-center gap-2">
          <Database className="h-4 w-4" />
          数据库连接
          <Badge variant="secondary" className="ml-1">
            {databaseCount}
          </Badge>
        </TabsTrigger>
        <TabsTrigger value="documents" className="flex items-center gap-2">
          <FileText className="h-4 w-4" />
          文档管理
          <Badge variant="secondary" className="ml-1">
            {documentCount}
          </Badge>
        </TabsTrigger>
      </TabsList>

      <TabsContent value="databases" className="mt-6">
        {databasesContent}
      </TabsContent>

      <TabsContent value="documents" className="mt-6">
        {documentsContent}
      </TabsContent>
    </Tabs>
  )
}