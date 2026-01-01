/**
 * # [BADGE] 徽章标签组件
 *
 * ## [MODULE]
 * **文件名**: badge.tsx
 * **职责**: 提供标准化的徽章标签组件 - 用于显示状态、标签、计数等信息，支持4种变体
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 徽章标签组件
 *
 * ## [INPUT]
 * Props (BadgeProps extends React.HTMLAttributes<HTMLDivElement>):
 * - **variant?: 'default' | 'secondary' | 'destructive' | 'outline'** - 徽章变体（默认'default'）
 * - **className?: string** - 自定义类名
 * - **children**: React.ReactNode - 徽章内容（通常是文本或数字）
 * - **所有div HTML属性**: onClick, style等
 *
 * ## [OUTPUT]
 * - **Badge组件** - 渲染徽章标签元素
 *   - **基础样式**: inline-flex.items-center.rounded-full.px-2.5.py-0.5.text-xs.font-medium
 *   - **过渡效果**: transition-colors（颜色过渡）
 *   - **focus状态**: focus:outline-none.focus:ring-2.focus:ring-blue-500.focus:ring-offset-2
 *   - **4种variant样式**:
 *     - **default**: bg-blue-100.text-blue-800.hover:bg-blue-200（蓝色徽章）
 *     - **secondary**: bg-gray-100.text-gray-800.hover:bg-gray-200（灰色徽章）
 *     - **destructive**: bg-red-100.text-red-800.hover:bg-red-200（红色徽章，用于警告/错误）
 *     - **outline**: text-gray-800.border.border-gray-300.hover:bg-gray-50（轮廓徽章，透明背景）
 * - **形状**: rounded-full（完全圆角，pill形状）
 * - **尺寸**: px-2.5.py-0.5.text-xs（水平10px，垂直2px，字体12px）
 * - **React.FC函数组件**: 使用React.FC类型声明
 * - **variantClasses对象**: 内联对象存储variant样式映射
 *
 * **上游依赖**:
 * - [react](https://react.dev/) - React框架（React.FC类型）
 * - [@/lib/utils](../../lib/utils.ts) - 工具函数（cn）
 *
 * **下游依赖**:
 * - 无（Badge是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要徽章标签的组件
 * - 状态标签、计数徽章、分类标签、通知徽章等
 * - 数据源类型标签、文档状态标签、通知数量徽章等
 *
 * ## [STATE]
 * - **无状态**: Badge是无状态组件（纯展示组件）
 * - **variantClasses对象**: 内联对象存储4种variant的样式映射
 *   - **default**: bg-blue-100.text-blue-800.hover:bg-blue-200
 *   - **secondary**: bg-gray-100.text-gray-800.hover:bg-gray-200
 *   - **destructive**: bg-red-100.text-red-800.hover:bg-red-200
 *   - **outline**: text-gray-800.border.border-gray-300.hover:bg-gray-50
 * - **variant默认值**: variant = 'default'（默认蓝色徽章）
 * - **pill形状**: rounded-full（完全圆角，左右圆角半径9999px）
 * - **紧凑尺寸**: px-2.5.py-0.5（水平padding 10px，垂直padding 2px）
 * - **小字体**: text-xs（12px字体）
 * - **focus ring**: focus:ring-2.focus:ring-blue-500.focus:ring-offset-2（2px蓝色ring，2px offset）
 * - **过渡效果**: transition-colors（背景色和文字色过渡动画）
 * - **React.FC类型**: React.FC<BadgeProps>函数组件类型声明
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: Badge是纯展示组件
 * - **类名合并**: cn(baseClasses, variantClasses[variant], className)合并类名
 * - **Props透传**: {...props}传递所有HTML div属性
 * - **variant查找**: variantClasses[variant]动态获取variant样式
 * - **hover效果**: 所有variant都包含hover:bg-*样式（背景色变化）
 * - **focus效果**: focus-visible状态显示ring（outline-none + ring-2 + ring-offset-2）
 * - **过渡动画**: transition-colors触发颜色过渡
 */

import React from 'react'
import { cn } from '../../lib/utils'

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline'
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'default',
  ...props
}) => {
  const variantClasses = {
    default:
      'bg-blue-100 text-blue-800 hover:bg-blue-200',
    secondary:
      'bg-gray-100 text-gray-800 hover:bg-gray-200',
    destructive:
      'bg-red-100 text-red-800 hover:bg-red-200',
    outline:
      'text-gray-800 border border-gray-300 hover:bg-gray-50',
  }

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
        variantClasses[variant],
        className
      )}
      {...props}
    />
  )
}

export default Badge
