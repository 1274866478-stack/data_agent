/**
 * # [ERROR MESSAGE] 错误消息组件
 *
 * ## [MODULE]
 * **文件名**: error-message.tsx
 * **职责**: 提供标准化的错误消息显示组件 - 包含图标、消息文本和可选的关闭按钮，支持两种变体（default/destructive）
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 错误消息组件
 *
 * ## [INPUT]
 * Props (ErrorMessageProps):
 * - **message: string** - 错误消息文本
 * - **onDismiss?: () => void** - 关闭回调函数（可选，存在时显示关闭按钮）
 * - **variant?: 'default' | 'destructive'** - 变体类型（默认'default'）
 *
 * ## [OUTPUT]
 * - **ErrorMessage组件** - 渲染错误消息div元素
 *   - **基础样式**: flex.items-start.gap-3.p-4.rounded-lg（flex布局，上对齐，间距12px，padding 16px，圆角）
 *   - **variant条件样式**:
 *     - **default**: bg-muted/50.text-muted-foreground.border.border-border（次要背景，次要前景色，边框）
 *     - **destructive**: bg-destructive/10.text-destructive.border.border-destructive/20（破坏性背景10%，破坏性前景色，边框20%）
 *   - **AlertCircle图标**: h-5.w-5.flex-shrink-0.mt-0.5（20px × 20px，禁止收缩，顶部margin 2px）
 *   - **消息容器**: flex-1（填充剩余空间）
 *   - **消息文本**: p元素，text-sm.font-medium（14px，字体粗细500）
 *   - **关闭按钮**: Button组件（variant='ghost', size='sm', h-6.w-6.p-0）
 *     - **X图标**: h-4.w-4（16px × 16px）
 *   - **条件渲染**: onDismiss存在时显示关闭按钮
 *   - **函数组件**: export function ErrorMessage()（非forwardRef）
 *
 * **上游依赖**:
 * - [lucide-react](https://lucide.dev/) - 图标库（AlertCircle, X）
 * - [@/components/ui/button](./button.tsx) - Button组件（关闭按钮）
 *
 * **下游依赖**:
 * - 无（ErrorMessage组件是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要显示错误消息的组件
 * - 表单验证错误、API错误响应、操作失败提示等
 *
 * ## [STATE]
 * - **无状态**: ErrorMessage是无状态组件（纯展示组件）
 * - **variant默认值**: variant = 'default'（默认次要样式）
 * - **variant条件样式**:
 *   - **default**: bg-muted/50.text-muted-foreground.border.border-border（灰色背景和边框）
 *   - **destructive**: bg-destructive/10.text-destructive.border.border-destructive/20（红色背景10%，红色边框20%）
 * - **flex布局**: flex.items-start.gap-3（flex布局，子元素上对齐，间距12px）
 * - **AlertCircle图标**: h-5.w-5.flex-shrink-0.mt-0.5（20px × 20px，禁止收缩，顶部margin 2px）
 * - **消息容器**: flex-1（flex填充，占据剩余空间）
 * - **消息文本**: text-sm.font-medium（14px，字体粗细500）
 * - **关闭按钮条件渲染**: onDismiss && <Button>（onDismiss存在时显示）
 * - **Button样式**: variant='ghost', size='sm', h-6.w-6.p-0（ghost变体，小尺寸，24px × 24px，无padding）
 * - **X图标**: h-4.w-4（16px × 16px）
 * - **函数组件**: export function ErrorMessage()（非forwardRef）
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: ErrorMessage是纯展示组件
 * - **条件样式**: variant === 'destructive' ? destructive样式 : default样式
 * - **条件渲染**: onDismiss存在时渲染关闭按钮
 * - **Button组件**: Button的onClick事件触发onDismiss回调
 * - **模板字符串**: 使用模板字符串合并类名（`${baseClasses} ${variantClasses}`）
 * - **图标显示**: AlertCircle和X图标（lucide-react）
 */

import { AlertCircle, X } from 'lucide-react'
import { Button } from './button'

interface ErrorMessageProps {
  message: string
  onDismiss?: () => void
  variant?: 'default' | 'destructive'
}

export function ErrorMessage({ message, onDismiss, variant = 'default' }: ErrorMessageProps) {
  return (
    <div className={`
      flex items-start gap-3 p-4 rounded-lg
      ${variant === 'destructive'
        ? 'bg-destructive/10 text-destructive border border-destructive/20'
        : 'bg-muted/50 text-muted-foreground border border-border'
      }
    `}>
      <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="text-sm font-medium">{message}</p>
      </div>
      {onDismiss && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onDismiss}
          className="h-6 w-6 p-0"
        >
          <X className="h-4 w-4" />
        </Button>
      )}
    </div>
  )
}