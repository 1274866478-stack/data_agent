/**
 * # [CLARIFICATION_VIEW] 澄清问题视图组件
 *
 * ## [MODULE]
 * **文件名**: ClarificationView.tsx
 * **职责**: 提供澄清问题的用户界面，当 Agent 检测到模糊问题时，展示澄清选项并收集用户回复
 *
 * ## [INPUT]
 * Props:
 * - **questions**: ClarificationQuestion[] - 澄清问题列表
 * - **onConfirm**: (responses: Record<string, any>) => void - 确认回调
 * - **onCancel**: () => void - 取消回调
 * - **isLoading?: boolean** - 加载状态
 *
 * ## [OUTPUT]
 * UI组件:
 * - **澄清问题卡片**: 显示所有澄清问题，每个问题包含选项
 * - **选项选择**: 单选/多选按钮，支持自定义输入
 * * **确认/取消按钮**: 提交或取消澄清
 * - **加载状态**: 提交中显示加载动画
 *
 * ## [UPSTREAM_DEPENDENCIES]
 * - [../../store/chatStore.ts](../../store/chatStore.ts) - 聊天状态管理
 * - [../ui/card.tsx](../ui/card.tsx) - 卡片组件
 * - [../ui/button.tsx](../ui/button.tsx) - 按钮组件
 * - [../ui/radio.tsx](../ui/radio.tsx) - 单选按钮组件
 * - [../ui/checkbox.tsx](../ui/checkbox.tsx) - 多选框组件
 * - [../ui/input.tsx](../ui/input.tsx) - 输入框组件
 *
 * ## [DOWNSTREAM_DEPENDENCIES]
 * - [ChatInterface.tsx](./ChatInterface.tsx) - 聊天界面组件（调用此组件）
 *
 * ## [STATE]
 * - **选择状态**: selections - 记录用户选择的澄清选项
 * - **UI状态**: showCustomInput - 是否显示自定义输入框
 * - **错误状态**: errors - 表单验证错误
 *
 * ## [SIDE-EFFECTS]
 * - 调用onConfirm回调传递用户选择
 * - 调用onCancel回调取消澄清
 * - 触发chatStore的澄清回复发送
 */

'use client'

import { useState, useCallback, useEffect } from 'react'
import {
  HelpCircle,
  Check,
  X,
  ChevronRight,
  Info,
  AlertCircle
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

// ========================================================================
// 类型定义
// ========================================================================

/**
 * 澄清选项
 */
export interface ClarificationOption {
  value: string
  label: string
  description?: string
  is_default?: boolean
}

/**
 * 澄清问题
 */
export interface ClarificationQuestion {
  question_id: string
  question_type: 'time_range' | 'entity' | 'metric' | 'comparison' | 'aggregation' | 'other'
  question_text: string
  options: ClarificationOption[]
  allow_multiple?: boolean
  allow_custom?: boolean
}

/**
 * ClarificationView 组件 Props
 */
export interface ClarificationViewProps {
  /** 澄清问题列表 */
  questions: ClarificationQuestion[]

  /** 确认回调 */
  onConfirm: (responses: Record<string, any>) => void

  /** 取消回调 */
  onCancel?: () => void

  /** 是否加载中 */
  isLoading?: boolean

  /** 可选的CSS类名 */
  className?: string
}

/**
 * 澄清回复（用户选择的汇总）
 */
export interface ClarificationResponse {
  [key: string]: string | string[]
}

// ========================================================================
// 辅助组件
// ========================================================================

/**
 * 问题图标组件 - 根据问题类型显示不同图标
 */
function QuestionIcon({ type }: { type: ClarificationQuestion['question_type'] }) {
  const iconMap = {
    time_range: '🕒',
    entity: '🏷️',
    metric: '📊',
    comparison: '📈',
    aggregation: '📐',
    other: '❓',
  }

  return (
    <span className="text-2xl mr-2">
      {iconMap[type] || iconMap.other}
    </span>
  )
}

/**
 * 选项选择按钮
 */
function OptionButton({
  option,
  isSelected,
  isMultiple,
  onSelect,
  onDeselect
}: {
  option: ClarificationOption
  isSelected: boolean
  isMultiple: boolean
  onSelect: (value: string) => void
  onDeselect: (value: string) => void
}) {
  const handleClick = () => {
    if (isSelected) {
      onDeselect(option.value)
    } else {
      onSelect(option.value)
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className={cn(
        // 玻璃态基础样式
        "relative overflow-hidden group",
        // 按钮基础样式
        "px-4 py-3 rounded-xl",
        "text-left transition-all duration-200",
        "w-full",
        // 边框和背景（玻璃态）
        "border border-white/20",
        "bg-white/10 backdrop-blur-md",
        "hover:bg-white/20",
        // 选中状态
        isSelected && "bg-gradient-to-r from-blue-500/20 to-purple-500/20 border-blue-400/50",
        // 阴影
        "shadow-lg shadow-black/5"
      )}
    >
      {/* 选中指示器 */}
      {isSelected && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          <div className="w-5 h-5 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center">
            <Check className="w-3 h-3 text-white" />
          </div>
        </div>
      )}

      <div className="flex-1">
        {/* 选项标签 */}
        <div className={cn(
          "font-medium text-sm",
          isSelected ? "text-white" : "text-gray-700"
        )}>
          {option.label}
        </div>

        {/* 选项描述 */}
        {option.description && (
          <div className={cn(
            "text-xs mt-1",
            isSelected ? "text-blue-100" : "text-gray-500"
          )}>
            {option.description}
          </div>
        )}

        {/* 默认标记 */}
        {option.is_default && !isSelected && (
          <Badge
            variant="secondary"
            className="mt-1 text-[10px] opacity-70"
          >
            默认
          </Badge>
        )}
      </div>
    </button>
  )
}

/**
 * 自定义输入框
 */
function CustomInput({
  question,
  value,
  onChange,
  placeholder
}: {
  question: ClarificationQuestion
  value: string
  onChange: (value: string) => void
  placeholder?: string
}) {
  return (
    <div className="mt-3">
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder || `自定义${question.question_type}...`}
        className={cn(
          "glass-input",
          "bg-white/10 border-white/20",
          "text-white placeholder:text-gray-400"
        )}
      />
      <p className="text-xs text-gray-400 mt-1">
        💡 输入您自定义的值
      </p>
    </div>
  )
}

// ========================================================================
// 主组件
// ========================================================================

export function ClarificationView({
  questions,
  onConfirm,
  onCancel,
  isLoading = false,
  className
}: ClarificationViewProps) {
  // 选择状态：question_id -> 选中的值（或多选数组）
  const [selections, setSelections] = useState<Record<string, string | string[]>>({})
  const [customInputs, setCustomInputs] = useState<Record<string, string>>({})
  const [showCustomInput, setShowCustomInput] = useState<Record<string, boolean>>({})

  // 获取当前选择（考虑默认值）
  const getSelection = useCallback((question: ClarificationQuestion): string | string[] => {
    // 如果已有选择，返回选择
    if (selections[question.question_id]) {
      return selections[question.question_id]
    }

    // 否则返回默认值
    if (question.allow_multiple) {
      const defaults = question.options
        .filter(opt => opt.is_default)
        .map(opt => opt.value)
      return defaults.length > 0 ? defaults : []
    } else {
      const defaultOpt = question.options.find(opt => opt.is_default)
      return defaultOpt?.value || ''
    }
  }, [selections])

  // 处理选项选择
  const handleSelect = useCallback((questionId: string, value: string) => {
    const question = questions.find(q => q.question_id === questionId)
    if (!question) return

    if (question.allow_multiple) {
      // 多选：切换选项
      const current = getSelection(question) as string[] || []
      if (current.includes(value)) {
        // 取消选择
        setSelections(prev => ({
          ...prev,
          [questionId]: current.filter(v => v !== value)
        }))
      } else {
        // 添加选择
        setSelections(prev => ({
          ...prev,
          [questionId]: [...current, value]
        }))
      }
    } else {
      // 单选：直接设置
      setSelections(prev => ({
        ...prev,
        [questionId]: value
      }))
    }
  }, [questions, selections, getSelection])

  // 处理取消选择
  const handleDeselect = useCallback((questionId: string, value: string) => {
    const question = questions.find(q => q.question_id === questionId)
    if (!question) return

    if (question.allow_multiple) {
      const current = getSelection(question) as string[] || []
      setSelections(prev => ({
        ...prev,
        [questionId]: current.filter(v => v !== value)
      }))
    }
  }, [questions, selections, getSelection])

  // 处理自定义输入
  const handleCustomInputChange = useCallback((questionId: string, value: string) => {
    setCustomInputs(prev => ({
      ...prev,
      [questionId]: value
    }))
  }, [])

  // 切换自定义输入显示
  const toggleCustomInput = useCallback((questionId: string) => {
    setShowCustomInput(prev => ({
      ...prev,
      [questionId]: !prev[questionId]
    }))
  }, [])

  // 初始化默认选择
  useEffect(() => {
    const initialSelections: Record<string, string | string[]> = {}

    questions.forEach(question => {
      initialSelections[question.question_id] = getSelection(question)
    })

    setSelections(initialSelections)
  }, [questions, getSelection])

  // 构建最终响应
  const buildResponse = useCallback((): ClarificationResponse => {
    const response: ClarificationResponse = {}

    questions.forEach(question => {
      const customValue = customInputs[question.question_id]
      if (customValue) {
        // 使用自定义输入
        response[question.question_id] = customValue
      } else {
        // 使用选择的值
        response[question.question_id] = selections[question.question_id]
      }
    })

    return response
  }, [questions, selections, customInputs])

  // 处理确认
  const handleConfirm = useCallback(() => {
    const response = buildResponse()
    onConfirm(response)
  }, [onConfirm, buildResponse])

  // 检查是否可以确认（每个问题都有答案）
  const canConfirm = questions.every(question => {
    const hasSelection = selections[question.question_id] !== undefined
    const hasCustomInput = customInputs[question.question_id]
    return (hasSelection && selections[question.question_id]) || hasCustomInput
  })

  // 玻璃态样式类
  const glassCardClass = cn(
    "glass-card",
    "backdrop-blur-xl bg-white/10 border border-white/20",
    "shadow-xl"
  )

  return (
    <div className={cn("w-full max-w-2xl mx-auto", className)}>
      <Card className={glassCardClass}>
        <CardHeader className="border-b border-white/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <HelpCircle className="w-5 h-5 text-white" />
              </div>
              <div>
                <CardTitle className="text-white">
                  需要澄清
                </CardTitle>
                <CardDescription className="text-gray-300">
                  为了更好地回答您的问题，请回答以下问题
                </CardDescription>
              </div>
            </div>
            {onCancel && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onCancel}
                className="text-white/70 hover:text-white hover:bg-white/10"
              >
                <X className="w-4 h-4" />
              </Button>
            )}
          </div>
        </CardHeader>

        <CardContent className="p-6 space-y-6">
          {questions.map((question, index) => {
            const currentSelection = selections[question.question_id]
            const customValue = customInputs[question.question_id]
            const isMulti = question.allow_multiple || false

            return (
              <div
                key={question.question_id}
                className="space-y-3"
              >
                {/* 问题标题 */}
                <div className="flex items-center space-x-2">
                  <Badge variant="outline" className="text-xs">
                    {index + 1}
                  </Badge>
                  <QuestionIcon type={question.question_type} />
                  <h3 className="text-white font-medium">
                    {question.question_text}
                  </h3>
                  {question.allow_multiple && (
                    <Badge variant="secondary" className="text-xs ml-2">
                      多选
                    </Badge>
                  )}
                </div>

                {/* 选项列表 */}
                <div className="space-y-2">
                  {question.options.map((option) => {
                    const isSelected = isMulti
                      ? (currentSelection as string[] || []).includes(option.value)
                      : currentSelection === option.value

                    return (
                      <OptionButton
                        key={option.value}
                        option={option}
                        isSelected={isSelected}
                        isMultiple={isMulti}
                        onSelect={(value) => handleSelect(question.question_id, value)}
                        onDeselect={(value) => handleDeselect(question.question_id, value)}
                      />
                    )
                  })}
                </div>

                {/* 自定义输入选项 */}
                {question.allow_custom && (
                  <>
                    <div className="flex items-center space-x-2 text-sm text-gray-400 pt-2">
                      <Info className="w-4 h-4" />
                      <span>没有合适的选项？</span>
                      <button
                        onClick={() => toggleCustomInput(question.question_id)}
                        className="text-blue-400 hover:text-blue-300 underline"
                      >
                        {showCustomInput[question.question_id] ? '收起' : '自定义输入'}
                      </button>
                    </div>

                    {showCustomInput[question.question_id] && (
                      <CustomInput
                        question={question}
                        value={customValue}
                        onChange={(value) => handleCustomInputChange(question.question_id, value)}
                      />
                    )}
                  </>
                )}
              </div>
            )
          })}
        </CardContent>

        {/* 操作按钮 */}
        <div className="flex justify-end space-x-3 border-t border-white/10 pt-6">
          {onCancel && (
            <Button
              variant="outline"
              onClick={onCancel}
              disabled={isLoading}
              className="border-white/20 text-white/70 hover:text-white hover:bg-white/10"
            >
              取消
            </Button>
          )}
          <Button
            onClick={handleConfirm}
            disabled={!canConfirm || isLoading}
            className={cn(
              "bg-gradient-to-r from-blue-500 to-purple-600",
              "hover:from-blue-600 hover:to-purple-700",
              "text-white",
              "disabled:opacity-50"
            )}
          >
            {isLoading ? (
              <>
                <span className="inline-block animate-spin mr-2">⟳</span>
                处理中...
              </>
            ) : (
              <>
                <Check className="w-4 h-4 mr-2" />
                确认
              </>
            )}
          </Button>
        </div>

        {/* 提示信息 */}
        <div className="flex items-start space-x-2 px-6 pb-4">
          <AlertCircle className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-gray-400">
            💡 您的回答将帮助生成更准确的结果。确认后将基于您的选择生成查询。
          </p>
        </div>
      </Card>

      {/* 背景装饰效果 */}
      <div className="fixed inset-0 -z-10 pointer-events-none overflow-hidden">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl" />
      </div>
    </div>
  )
}

// ========================================================================
// 集成示例组件（用于展示如何在聊天界面中使用）
// ========================================================================

/**
 * 澄清对话框组件 - 模态框版本
 */
export function ClarificationDialog({
  open,
  questions,
  onConfirm,
  onCancel,
  isLoading
}: {
  open: boolean
  questions: ClarificationQuestion[]
  onConfirm: (responses: Record<string, any>) => void
  onCancel: () => void
  isLoading?: boolean
}) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* 澄清视图 */}
      <div className="relative z-10 w-full max-w-2xl">
        <ClarificationView
          questions={questions}
          onConfirm={(responses) => {
            onConfirm(responses)
            onCancel()
          }}
          onCancel={onCancel}
          isLoading={isLoading}
        />
      </div>
    </div>
  )
}

/**
 * 内联澄清卡片 - 用于在消息列表中嵌入
 */
export function InlineClarificationCard({
  questions,
  onConfirm,
  onCancel
}: {
  questions: ClarificationQuestion[]
  onConfirm: (responses: Record<string, any>) => void
  onCancel?: () => void
}) {
  return (
    <div className="my-4">
      <ClarificationView
        questions={questions}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />
    </div>
  )
}

// ========================================================================
// 默认导出
// ========================================================================

export default ClarificationView
