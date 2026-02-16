/**
 * # [LOADING SPINNER] 加载动画组件
 *
 * ## [MODULE]
 * **文件名**: loading-spinner.tsx
 * **职责**: 提供标准化的加载旋转动画组件 - 纯CSS动画，支持3种尺寸
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 * **变更记录**:
 * - v1.0.0 (2026-01-01): 初始版本 - 加载动画组件
 *
 * ## [INPUT]
 * Props (LoadingSpinnerProps):
 * - **size?: 'sm' | 'md' | 'lg'** - 尺寸变体（默认'md'）
 * - **className?: string** - 自定义类名
 *
 * ## [OUTPUT]
 * - **LoadingSpinner组件** - 渲染加载旋转动画div元素
 *   - **基础样式**: animate-spin.rounded-full.border-2.border-primary.border-t-transparent
 *   - **animate-spin**: CSS旋转动画（360度无限循环）
 *   - **rounded-full**: 完全圆角（圆形）
 *   - **border-2**: 2px边框
 *   - **border-primary**: 3/4边框为主题色（蓝色）
 *   - **border-t-transparent**: 顶部边框透明（形成缺口效果）
 *   - **3种size尺寸**:
 *     - **sm**: h-4.w-4（16px × 16px）
 *     - **md**: h-6.w-6（24px × 24px，默认）
 *     - **lg**: h-8.w-8（32px × 32px）
 *   - **sizeClasses对象**: 内联对象存储3种size的样式映射
 *   - **函数组件**: 使用函数组件（非forwardRef）
 *
 * **上游依赖**:
 * - 无（纯React组件，无外部依赖）
 *
 * **下游依赖**:
 * - 无（LoadingSpinner是叶子UI组件）
 *
 * **调用方**:
 * - 全应用所有需要加载动画的组件
 * - 异步操作加载、数据请求加载、页面初始化加载等
 *
 * ## [STATE]
 * - **无状态**: LoadingSpinner是无状态组件（纯展示组件）
 * - **sizeClasses对象**: 内联对象存储3种size的样式映射
 *   - **sm**: h-4.w-4（16px × 16px）
 *   - **md**: h-6.w-6（24px × 24px，默认）
 *   - **lg**: h-8.w-8（32px × 32px）
 * - **size默认值**: size = 'md'（默认中等尺寸）
 * - **animate-spin**: Tailwind内置旋转动画（360度无限循环）
 *   - **animation**: spin 1s linear infinite（1秒一圈，匀速，无限循环）
 * - **rounded-full**: 完全圆角（border-radius 9999px，圆形）
 * - **border-2**: 2px边框
 * - **border-primary**: 3/4边框为主题色（蓝色或品牌色）
 * - **border-t-transparent**: 顶部边框透明（border-top-color: transparent，形成缺口效果）
 *   - **缺口效果**: 只有3/4圆环可见（顶部透明），旋转时形成追逐效果
 * - **函数组件**: export function LoadingSpinner()（非forwardRef）
 *
 * ## [SIDE-EFFECTS]
 * - **无副作用**: LoadingSpinner是纯展示组件
 * - **CSS动画**: animate-spin触发旋转动画（360度无限循环）
 * - **size查找**: sizeClasses[size]动态获取size样式
 * - **类名合并**: 模板字符串合并类名（`${baseClasses} ${sizeClasses[size]} ${className}`）
 * - **缺口效果**: border-t-transparent（顶部透明）+ animate-spin（旋转）形成追逐动画
 */

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function LoadingSpinner({ size = 'md', className = '' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8'
  }

  return (
    <div className={`animate-spin rounded-full border-2 border-primary border-t-transparent ${sizeClasses[size]} ${className}`} />
  )
}
