'use client'

import React from 'react'
import { cn } from '@/lib/utils'
import { 
  Database, 
  Search, 
  FileCode, 
  Play, 
  CheckCircle2, 
  XCircle, 
  Loader2,
  ChevronDown,
  ChevronUp,
  Clock,
  MessageSquare,
  TableProperties,
  Wand2,
  Code2,
  Zap
} from 'lucide-react'
import { ProcessingStep } from '@/types/chat'

interface ProcessingStepsProps {
  steps: ProcessingStep[]
  className?: string
  defaultExpanded?: boolean
}

// 根据步骤编号和标题返回对应的图标
function getStepIcon(step: number, title: string, status: ProcessingStep['status']) {
  const iconClass = 'w-4 h-4'
  
  // 根据状态返回状态图标
  if (status === 'running') {
    return <Loader2 className={cn(iconClass, 'animate-spin text-blue-500')} />
  }
  if (status === 'error') {
    return <XCircle className={cn(iconClass, 'text-red-500')} />
  }
  if (status === 'completed') {
    // 根据步骤编号显示对应图标（6步流程）
    switch (step) {
      case 1: // 理解用户问题
        return <MessageSquare className={cn(iconClass, 'text-green-500')} />
      case 2: // 获取数据库Schema
        return <TableProperties className={cn(iconClass, 'text-green-500')} />
      case 3: // 构建AI Prompt
        return <Wand2 className={cn(iconClass, 'text-green-500')} />
      case 4: // AI生成SQL
        return <Code2 className={cn(iconClass, 'text-green-500')} />
      case 5: // 提取SQL语句
        return <FileCode className={cn(iconClass, 'text-green-500')} />
      case 6: // 执行SQL查询
        return <Zap className={cn(iconClass, 'text-green-500')} />
      default:
        // 回退到标题匹配
        if (title.includes('数据源') || title.includes('Schema')) {
          return <Database className={cn(iconClass, 'text-green-500')} />
        }
        if (title.includes('SQL') || title.includes('生成')) {
          return <FileCode className={cn(iconClass, 'text-green-500')} />
        }
        if (title.includes('执行') || title.includes('查询')) {
          return <Play className={cn(iconClass, 'text-green-500')} />
        }
        return <CheckCircle2 className={cn(iconClass, 'text-green-500')} />
    }
  }
  
  // pending 状态
  return <Clock className={cn(iconClass, 'text-gray-400')} />
}

// 获取步骤的状态颜色
function getStatusColor(status: ProcessingStep['status']) {
  switch (status) {
    case 'completed':
      return 'border-green-200 bg-green-50'
    case 'running':
      return 'border-blue-200 bg-blue-50'
    case 'error':
      return 'border-red-200 bg-red-50'
    default:
      return 'border-gray-200 bg-gray-50'
  }
}

// 格式化耗时
function formatDuration(ms?: number) {
  if (!ms) return ''
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

export function ProcessingSteps({ steps, className, defaultExpanded = true }: ProcessingStepsProps) {
  const [isExpanded, setIsExpanded] = React.useState(defaultExpanded)
  
  // 调试日志
  console.log('[ProcessingSteps] 渲染，steps数量:', steps?.length, steps)
  
  if (!steps || steps.length === 0) return null

  // 计算总耗时
  const totalDuration = steps.reduce((sum, step) => sum + (step.duration || 0), 0)
  const completedSteps = steps.filter(s => s.status === 'completed').length
  const hasError = steps.some(s => s.status === 'error')
  const isRunning = steps.some(s => s.status === 'running')

  return (
    <div className={cn(
      'mt-3 rounded-lg border overflow-hidden',
      hasError ? 'border-red-200 bg-red-50/50' : 
      isRunning ? 'border-blue-200 bg-blue-50/50' : 
      'border-emerald-200 bg-emerald-50/50',
      className
    )}>
      {/* 标题栏 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'w-full px-3 py-2 flex items-center justify-between text-sm font-medium',
          'hover:bg-black/5 transition-colors',
          hasError ? 'text-red-800' : 
          isRunning ? 'text-blue-800' : 
          'text-emerald-800'
        )}
      >
        <div className="flex items-center gap-2">
          {isRunning ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : hasError ? (
            <XCircle className="w-4 h-4" />
          ) : (
            <CheckCircle2 className="w-4 h-4" />
          )}
          <span>
            AI 推理过程 
            <span className="ml-2 text-xs font-normal opacity-75">
              ({completedSteps}/{steps.length} 步骤完成
              {totalDuration > 0 && ` · ${formatDuration(totalDuration)}`})
            </span>
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
      </button>

      {/* 步骤列表 */}
      {isExpanded && (
        <div className="px-3 pb-3 space-y-2">
          {steps.map((step, index) => (
            <div
              key={step.step || index}
              className={cn(
                'rounded-md border p-2 transition-all duration-300',
                getStatusColor(step.status)
              )}
            >
              <div className="flex items-start gap-2">
                {/* 步骤图标 */}
                <div className="mt-0.5">
                  {getStepIcon(step.step, step.title, step.status)}
                </div>
                
                {/* 步骤内容 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className={cn(
                      'text-xs font-medium',
                      step.status === 'completed' ? 'text-green-700' :
                      step.status === 'running' ? 'text-blue-700' :
                      step.status === 'error' ? 'text-red-700' :
                      'text-gray-600'
                    )}>
                      {step.step}. {step.title}
                    </span>
                    {step.duration && step.status === 'completed' && (
                      <span className="text-xs text-gray-500">
                        {formatDuration(step.duration)}
                      </span>
                    )}
                  </div>
                  
                  {step.description && (
                    <p className="text-xs text-gray-600 mt-0.5">
                      {step.description}
                    </p>
                  )}
                  
                  {/* 详情（如SQL内容） */}
                  {step.details && (
                    <details className="mt-1">
                      <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                        查看详情
                      </summary>
                      <pre className="mt-1 p-2 bg-white/50 rounded text-xs overflow-x-auto max-h-32 overflow-y-auto">
                        <code>{step.details}</code>
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

