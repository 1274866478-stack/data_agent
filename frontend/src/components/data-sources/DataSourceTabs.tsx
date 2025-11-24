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