'use client'

import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Calendar } from '@/components/ui/calendar'
import { CalendarIcon, Filter, X, Search } from 'lucide-react'
import { cn } from '@/lib/utils'

// 简单的日期格式化函数
const formatDate = (date: Date) => {
  return date.toISOString().split('T')[0] // YYYY-MM-DD格式
}
import { useDashboardStore, DataSourceFilters } from '@/store/dashboardStore'

const STATUS_OPTIONS = [
  { value: 'active', label: '正常' },
  { value: 'inactive', label: '未激活' },
  { value: 'error', label: '错误' },
  { value: 'ready', label: '就绪' },
  { value: 'processing', label: '处理中' },
  { value: 'tested', label: '已测试' },
]

const TYPE_OPTIONS = [
  { value: 'all', label: '全部' },
  { value: 'database', label: '数据库' },
  { value: 'document', label: '文档' },
]

interface FilterBadgeProps {
  label: string
  onRemove: () => void
}

const FilterBadge: React.FC<FilterBadgeProps> = ({ label, onRemove }) => (
  <Badge variant="secondary" className="gap-1">
    {label}
    <X
      className="h-3 w-3 cursor-pointer hover:text-destructive"
      onClick={onRemove}
    />
  </Badge>
)

export const SearchAndFilter: React.FC = () => {
  const {
    searchQuery,
    filters,
    setSearchQuery,
    updateFilters,
    clearFilters,
    activeTab,
  } = useDashboardStore()

  const [isFilterOpen, setIsFilterOpen] = useState(false)

  // 获取当前标签页可用的状态选项
  const getCurrentStatusOptions = () => {
    if (activeTab === 'databases') {
      return STATUS_OPTIONS.filter(status =>
        ['active', 'inactive', 'error', 'tested'].includes(status.value)
      )
    } else {
      return STATUS_OPTIONS.filter(status =>
        ['ready', 'processing', 'error'].includes(status.value)
      )
    }
  }

  // 处理日期选择
  const handleDateSelect = (date: Date | undefined, type: 'from' | 'to') => {
    if (date) {
      updateFilters({
        dateRange: {
          ...filters.dateRange,
          [type]: date.toISOString(),
        },
      })
    }
  }

  // 移除特定筛选条件
  const removeFilter = (filterType: keyof DataSourceFilters, value?: string) => {
    if (filterType === 'status' && value) {
      const newStatus = filters.status.filter(s => s !== value)
      updateFilters({ status: newStatus })
    } else if (filterType === 'dateRange') {
      updateFilters({ dateRange: {} })
    } else if (filterType === 'type') {
      updateFilters({ type: 'all' })
    }
  }

  // 获取活动筛选条件数量
  const getActiveFilterCount = () => {
    let count = 0
    if (filters.type !== 'all') count++
    if (filters.status.length > 0) count++
    if (filters.dateRange.from || filters.dateRange.to) count++
    return count
  }

  const activeFilterCount = getActiveFilterCount()

  return (
    <div className="space-y-4">
      {/* 搜索和快速筛选 */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* 搜索框 */}
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="搜索数据源名称、类型或描述..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* 类型筛选 */}
        <Select
          value={filters.type}
          onValueChange={(value) => updateFilters({ type: value as any })}
        >
          <SelectTrigger className="w-full sm:w-40">
            <SelectValue placeholder="选择类型" />
          </SelectTrigger>
          <SelectContent>
            {TYPE_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* 高级筛选按钮 */}
        <Popover open={isFilterOpen} onOpenChange={setIsFilterOpen}>
          <PopoverTrigger asChild>
            <Button variant="outline" className="relative">
              <Filter className="h-4 w-4 mr-2" />
              筛选
              {activeFilterCount > 0 && (
                <Badge
                  variant="secondary"
                  className="ml-2 h-5 w-5 rounded-full p-0 text-xs"
                >
                  {activeFilterCount}
                </Badge>
              )}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-80" align="start">
            <div className="space-y-4">
              <div className="font-medium">高级筛选</div>

              {/* 状态筛选 */}
              <div className="space-y-2">
                <Label>状态</Label>
                <div className="grid grid-cols-2 gap-2">
                  {getCurrentStatusOptions().map((status) => (
                    <div key={status.value} className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id={`status-${status.value}`}
                        checked={filters.status.includes(status.value)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            updateFilters({
                              status: [...filters.status, status.value],
                            })
                          } else {
                            updateFilters({
                              status: filters.status.filter(s => s !== status.value),
                            })
                          }
                        }}
                        className="rounded"
                      />
                      <Label htmlFor={`status-${status.value}`} className="text-sm">
                        {status.label}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>

              {/* 日期范围筛选 */}
              <div className="space-y-2">
                <Label>日期范围</Label>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">开始日期</Label>
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          className={cn(
                            'w-full justify-start text-left font-normal',
                            !filters.dateRange.from && 'text-muted-foreground'
                          )}
                        >
                          <CalendarIcon className="mr-2 h-4 w-4" />
                          {filters.dateRange.from ? (
                            formatDate(new Date(filters.dateRange.from))
                          ) : (
                            '开始日期'
                          )}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0" align="start">
                        <Calendar
                          mode="single"
                          selected={
                            filters.dateRange.from
                              ? new Date(filters.dateRange.from)
                              : undefined
                          }
                          onSelect={(date) => handleDateSelect(date, 'from')}
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                  </div>
                  <div>
                    <Label className="text-xs">结束日期</Label>
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          className={cn(
                            'w-full justify-start text-left font-normal',
                            !filters.dateRange.to && 'text-muted-foreground'
                          )}
                        >
                          <CalendarIcon className="mr-2 h-4 w-4" />
                          {filters.dateRange.to ? (
                            formatDate(new Date(filters.dateRange.to))
                          ) : (
                            '结束日期'
                          )}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0" align="start">
                        <Calendar
                          mode="single"
                          selected={
                            filters.dateRange.to
                              ? new Date(filters.dateRange.to)
                              : undefined
                          }
                          onSelect={(date) => handleDateSelect(date, 'to')}
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                  </div>
                </div>
              </div>

              {/* 操作按钮 */}
              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    clearFilters()
                    setIsFilterOpen(false)
                  }}
                  className="flex-1"
                >
                  清除筛选
                </Button>
                <Button
                  size="sm"
                  onClick={() => setIsFilterOpen(false)}
                  className="flex-1"
                >
                  应用筛选
                </Button>
              </div>
            </div>
          </PopoverContent>
        </Popover>
      </div>

      {/* 活动筛选条件显示 */}
      {(activeFilterCount > 0 || searchQuery) && (
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-sm text-gray-500">当前筛选:</span>

          {/* 搜索查询 */}
          {searchQuery && (
            <FilterBadge
              label={`搜索: "${searchQuery}"`}
              onRemove={() => setSearchQuery('')}
            />
          )}

          {/* 类型筛选 */}
          {filters.type !== 'all' && (
            <FilterBadge
              label={`类型: ${TYPE_OPTIONS.find(t => t.value === filters.type)?.label}`}
              onRemove={() => removeFilter('type')}
            />
          )}

          {/* 状态筛选 */}
          {filters.status.map((status) => (
            <FilterBadge
              key={status}
              label={`状态: ${STATUS_OPTIONS.find(s => s.value === status)?.label}`}
              onRemove={() => removeFilter('status', status)}
            />
          ))}

          {/* 日期范围筛选 */}
          {filters.dateRange.from && filters.dateRange.to && (
            <FilterBadge
              label={`日期: ${formatDate(new Date(filters.dateRange.from))} - ${formatDate(new Date(filters.dateRange.to))}`}
              onRemove={() => removeFilter('dateRange')}
            />
          )}
          {filters.dateRange.from && !filters.dateRange.to && (
            <FilterBadge
              label={`开始日期: ${formatDate(new Date(filters.dateRange.from))}`}
              onRemove={() => removeFilter('dateRange')}
            />
          )}
          {filters.dateRange.to && !filters.dateRange.from && (
            <FilterBadge
              label={`结束日期: ${formatDate(new Date(filters.dateRange.to))}`}
              onRemove={() => removeFilter('dateRange')}
            />
          )}

          {/* 清除所有按钮 */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              clearFilters()
              setSearchQuery('')
            }}
            className="text-red-600 hover:text-red-700"
          >
            清除所有
          </Button>
        </div>
      )}
    </div>
  )
}