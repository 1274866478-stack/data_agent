'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Checkbox } from '@/components/ui/checkbox'
import {
  MoreHorizontal,
  Trash2,
  Download,
  RefreshCw,
  CheckSquare,
  Square,
} from 'lucide-react'
import { useDashboardStore, SearchResult } from '@/store/dashboardStore'

interface BulkOperationsProps {
  items: SearchResult[]
  selectedItems: string[]
  onSelectionChange: (selectedItems: string[]) => void
  onRefresh?: () => void
}

interface BulkConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: string
  confirmText: string
  onConfirm: () => Promise<void>
  isLoading?: boolean
}

const BulkConfirmDialog: React.FC<BulkConfirmDialogProps> = ({
  open,
  onOpenChange,
  title,
  description,
  confirmText,
  onConfirm,
  isLoading = false,
}) => {
  const [isConfirming, setIsConfirming] = useState(false)

  const handleConfirm = async () => {
    setIsConfirming(true)
    try {
      await onConfirm()
      onOpenChange(false)
    } catch (error) {
      // 错误处理在调用方
    } finally {
      setIsConfirming(false)
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>
            {description}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isConfirming}>
            取消
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={isConfirming || isLoading}
            className="bg-red-600 hover:bg-red-700"
          >
            {isConfirming ? '处理中...' : confirmText}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

export const BulkOperations: React.FC<BulkOperationsProps> = ({
  items,
  selectedItems,
  onSelectionChange,
  onRefresh,
}) => {
  const {
    activeTab,
    bulkDelete,
    isLoading,
    error,
    clearError,
  } = useDashboardStore()

  const [showDeleteDialog, setShowDeleteDialog] = useState(false)

  // 处理全选/反选
  const handleSelectAll = () => {
    if (selectedItems.length === items.length && items.length > 0) {
      onSelectionChange([])
    } else {
      onSelectionChange(items.map(item => item.id))
    }
  }

  // 处理单个项目选择
  const handleToggleSelection = (itemId: string) => {
    if (selectedItems.includes(itemId)) {
      onSelectionChange(selectedItems.filter(id => id !== itemId))
    } else {
      onSelectionChange([...selectedItems, itemId])
    }
  }

  // 处理批量删除
  const handleBulkDelete = async () => {
    if (selectedItems.length === 0) return

    try {
      await bulkDelete(selectedItems, activeTab)
    } catch (error) {
      console.error('批量删除失败:', error)
    }
  }

  // 获取选中的项目名称
  const getSelectedItemNames = () => {
    return items
      .filter(item => selectedItems.includes(item.id))
      .map(item => item.name)
      .slice(0, 3) // 只显示前3个
  }

  // 判断是否全部选中
  const isAllSelected = items.length > 0 && selectedItems.length === items.length
  const isPartiallySelected = selectedItems.length > 0 && selectedItems.length < items.length

  return (
    <div className="space-y-4">
      {/* 批量操作栏 */}
      {selectedItems.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Checkbox
                checked={isAllSelected}
                ref={isPartiallySelected ? undefined : undefined}
                className={isPartiallySelected ? 'data-[state=checked]:bg-blue-600' : ''}
                onCheckedChange={handleSelectAll}
              />
              <span className="text-sm font-medium text-blue-900">
                已选择 {selectedItems.length} 项
              </span>
              <Badge variant="secondary">
                {activeTab === 'databases' ? '数据库' : '文档'}
              </Badge>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onSelectionChange([])}
              >
                清除选择
              </Button>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <MoreHorizontal className="h-4 w-4 mr-2" />
                    批量操作
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    onClick={() => setShowDeleteDialog(true)}
                    className="text-red-600 focus:text-red-600"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    批量删除
                  </DropdownMenuItem>
                  {onRefresh && (
                    <DropdownMenuItem onClick={onRefresh}>
                      <RefreshCw className="h-4 w-4 mr-2" />
                      刷新数据
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuItem>
                    <Download className="h-4 w-4 mr-2" />
                    导出选中项
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {/* 显示选中的项目名称 */}
          <div className="mt-2 text-xs text-blue-700">
            {getSelectedItemNames().join(', ')}
            {selectedItems.length > 3 && (
              <> 等 {selectedItems.length} 项</>
            )}
          </div>
        </div>
      )}

      {/* 列表头部的选择框 */}
      {items.length > 0 && (
        <div className="flex items-center justify-between p-2 bg-gray-50 rounded-t-lg">
          <div className="flex items-center gap-3">
            <Checkbox
              checked={isAllSelected}
              ref={isPartiallySelected ? undefined : undefined}
              className={isPartiallySelected ? 'data-[state=checked]:bg-blue-600' : ''}
              onCheckedChange={handleSelectAll}
            />
            <span className="text-sm font-medium text-gray-700">
              {isAllSelected ? '已选择全部' :
               isPartiallySelected ? `已选择 ${selectedItems.length} 项` :
               '选择项目'}
            </span>
          </div>
          <div className="text-sm text-gray-500">
            共 {items.length} 项
          </div>
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <span className="text-red-700 text-sm">{error}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearError}
              className="text-red-600 hover:text-red-700"
            >
              ×
            </Button>
          </div>
        </div>
      )}

      {/* 批量删除确认对话框 */}
      <BulkConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="确认批量删除"
        description={
          <div>
            <p>您即将删除以下 {activeTab === 'databases' ? '数据库连接' : '文档'}：</p>
            <ul className="mt-2 list-disc list-inside text-sm text-gray-600">
              {getSelectedItemNames().map((name, index) => (
                <li key={index}>{name}</li>
              ))}
              {selectedItems.length > 3 && (
                <li>等 {selectedItems.length} 项</li>
              )}
            </ul>
            <p className="mt-3 text-red-600 font-medium">
              ⚠️ 此操作不可恢复，请确认是否继续？
            </p>
          </div>
        }
        confirmText={`删除 ${selectedItems.length} 项`}
        onConfirm={handleBulkDelete}
        isLoading={isLoading}
      />

      {/* 项目列表中的选择框 */}
      {items.map((item) => (
        <div key={item.id} className="flex items-center p-3 border-b hover:bg-gray-50">
          <Checkbox
            checked={selectedItems.includes(item.id)}
            onCheckedChange={() => handleToggleSelection(item.id)}
          />
          <div className="ml-3 flex-1">
            <div className="font-medium">{item.name}</div>
            <div className="text-sm text-gray-500">
              {item.type === 'database' ?
                `${item.db_type} - ${item.host}` :
                `${item.file_type} - ${Math.round(item.file_size_mb || 0)}MB`
              }
            </div>
          </div>
          <Badge variant={item.status === 'active' || item.status === 'ready' ? 'default' : 'secondary'}>
            {item.status}
          </Badge>
        </div>
      ))}

      {/* 空状态 */}
      {items.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          暂无数据
        </div>
      )}
    </div>
  )
}