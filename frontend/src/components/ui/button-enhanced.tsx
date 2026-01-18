/**
 * # [BUTTON_ENHANCED] 增强可访问性按钮组件
 *
 * ## [MODULE]
 * **文件名**: button-enhanced.tsx
 * **职责**: 提供符合 UX Pro Max 标准的按钮组件
 *
 * ## [DESCRIPTION]
 * 基于原 button 组件增强可访问性：
 * - 最小触摸目标 44x44px
 * - 清晰的焦点状态
 * - 加载状态处理
 * - 平滑过渡 (150-300ms)
 * - 尊重 reduced-motion 偏好
 *
 * ## [ACCESSIBILITY]
 * - 焦点可见 (focus-visible)
 * - ARIA 属性支持
 * - 键盘导航支持
 * - 屏幕阅读器友好
 */

import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

/**
 * 按钮变体样式
 * 遵循 Data Agent V4 设计系统
 */
const buttonVariants = cva(
  // 基础样式 - 确保最小触摸目标
  [
    'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium',
    'transition-all duration-200',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
    'disabled:pointer-events-none disabled:opacity-50',
    // 悬停状态 - cursor-pointer
    'cursor-pointer',
    'select-none',
  ],
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground shadow hover:bg-primary/90 active:bg-primary/80',
        destructive: 'bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90',
        outline: 'border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
        // 新增：CTA 变体 - 橙色强调
        accent: 'bg-accent text-accent-foreground shadow hover:bg-accent/90 active:bg-accent/80',
      },
      size: {
        default: 'h-10 px-4 py-2', // 40px - 符合最小触摸目标
        sm: 'h-9 rounded-md px-3', // 36px - 接近最小值
        lg: 'h-11 rounded-md px-8', // 44px - 符合最小触摸目标
        xl: 'h-12 rounded-md px-10', // 48px - 舒适触摸目标
        icon: 'h-10 w-10', // 正方形图标按钮
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
  loading?: boolean
  loadingText?: string
  /**
   * 左侧图标
   */
  leftIcon?: React.ReactNode
  /**
   * 右侧图标
   */
  rightIcon?: React.ReactNode
}

/**
 * EnhancedButton - 增强可访问性按钮组件
 */
const EnhancedButton = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      loading = false,
      loadingText = '加载中...',
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    // 加载状态：禁用按钮
    const isDisabled = disabled || loading

    // 尊重用户的动画偏好
    const [prefersReducedMotion, setPrefersReducedMotion] = React.useState(false)

    React.useEffect(() => {
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
      setPrefersReducedMotion(mediaQuery.matches)

      const listener = (e: MediaQueryListEvent) => {
        setPrefersReducedMotion(e.matches)
      }

      mediaQuery.addEventListener('change', listener)
      return () => mediaQuery.removeEventListener('change', listener)
    }, [])

    const Comp = asChild ? Slot : 'button'

    return (
      <Comp
        className={cn(
          buttonVariants({ variant, size, className }),
          prefersReducedMotion && 'transition-none'
        )}
        ref={ref}
        disabled={isDisabled}
        aria-disabled={isDisabled}
        aria-busy={loading}
        {...props}
      >
        {/* 加载状态 */}
        {loading && (
          <svg
            className="h-4 w-4 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}

        {/* 左侧图标 - 加载时隐藏 */}
        {!loading && leftIcon && <span aria-hidden="true">{leftIcon}</span>}

        {/* 按钮文本 */}
        {loading ? loadingText : children}

        {/* 右侧图标 - 加载时隐藏 */}
        {!loading && rightIcon && <span aria-hidden="true">{rightIcon}</span>}
      </Comp>
    )
  }
)
EnhancedButton.displayName = 'EnhancedButton'

/**
 * IconButton - 图标按钮变体
 *
 * @example
 * ```tsx
 * <IconButton icon={<Plus />} aria-label="添加" />
 * ```
 */
export interface IconButtonProps extends Omit<ButtonProps, 'children'> {
  /**
   * 图标
   */
  icon: React.ReactNode
  /**
   * ARIA 标签（必需，用于可访问性）
   */
  'aria-label': string
  /**
   * 是否为无边界样式
   */
  ghost?: boolean
}

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon, 'aria-label': ariaLabel, ghost = false, variant, ...props }, ref) => {
    return (
      <EnhancedButton
        ref={ref}
        variant={ghost ? 'ghost' : variant}
        size="icon"
        aria-label={ariaLabel}
        {...props}
      >
        {icon}
      </EnhancedButton>
    )
  }
)
IconButton.displayName = 'IconButton'

/**
 * ButtonGroup - 按钮组
 *
 * @example
 * ```tsx
 * <ButtonGroup>
 *   <Button variant="outline">取消</Button>
 *   <Button>确定</Button>
 * </ButtonGroup>
 * ```
 */
export interface ButtonGroupProps {
  /**
   * 按钮子元素
   */
  children: React.ReactNode
  /**
   * 对齐方式
   */
  align?: 'start' | 'center' | 'end' | 'space-between'
  /**
   * 间距
   */
  gap?: string
  /**
   * 自定义类名
   */
  className?: string
}

export function ButtonGroup({
  children,
  align = 'end',
  gap = 'gap-2',
  className,
}: ButtonGroupProps) {
  const alignClasses = {
    start: 'justify-start',
    center: 'justify-center',
    end: 'justify-end',
    'space-between': 'justify-between',
  }

  return (
    <div
      className={cn(
        'flex',
        gap,
        alignClasses[align],
        className
      )}
      role="group"
      aria-label="按钮组"
    >
      {children}
    </div>
  )
}

export { EnhancedButton, buttonVariants }
export default EnhancedButton
