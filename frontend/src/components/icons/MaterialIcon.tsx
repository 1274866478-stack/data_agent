/**
 * [HEADER]
 * Material Icon 组件 - Material Symbols Outlined 封装
 *
 * [MODULE]
 * 模块类型: React UI 组件
 * 所属功能: 图标显示
 * 技术栈: React, TypeScript, Material Symbols Outlined
 *
 * [INPUT]
 * Props:
 * - icon: string - Material Symbols 图标名称
 * - className?: string - 自定义 CSS 类名
 *
 * [OUTPUT]
 * - 渲染 Material Symbols Outlined 图标
 *
 * [LINK]
 * - 依赖: Google Fonts Material Symbols Outlined
 * - 使用路径: @/components/icons/MaterialIcon
 *
 * [POS]
 * - 文件路径: frontend/src/components/icons/MaterialIcon.tsx
 *
 * [STATE]
 * - 无状态组件
 *
 * [PROTOCOL]
 * - 使用 Google Fonts Material Symbols Outlined 字体
 * - 通过 material-symbols-outlined 类应用样式
 */

interface MaterialIconProps {
  /** Material Symbols 图标名称 */
  icon: string
  /** 自定义 CSS 类名 */
  className?: string
}

/**
 * Material Icon 组件
 *
 * 使用 Google Material Symbols Outlined 字体渲染图标
 *
 * @example
 * ```tsx
 * <MaterialIcon icon="home" />
 * <MaterialIcon icon="refresh" className="text-lg" />
 * <MaterialIcon icon="terminal" className="text-tiffany text-2xl" />
 * ```
 */
export function MaterialIcon({ icon, className = '' }: MaterialIconProps) {
  return (
    <span className={`material-symbols-outlined ${className}`} aria-hidden>
      {icon}
    </span>
  )
}

/**
 * 预定义常用图标的大小变体
 */
export const IconSizes = {
  xs: 'text-[16px]',
  sm: 'text-[18px]',
  md: 'text-[20px]',
  lg: 'text-[24px]',
  xl: 'text-[32px]',
  '2xl': 'text-[40px]',
  '3xl': 'text-[48px]',
} as const

/**
 * Material Icon 组件 - 带预定义尺寸
 */
interface MaterialIconWithSizeProps {
  /** Material Symbols 图标名称 */
  icon: string
  /** 预定义尺寸 */
  size?: keyof typeof IconSizes
  /** 自定义 CSS 类名 */
  className?: string
}

export function MaterialIconWithSize({
  icon,
  size = 'md',
  className = '',
}: MaterialIconWithSizeProps) {
  return (
    <span className={`material-symbols-outlined ${IconSizes[size]} ${className}`} aria-hidden>
      {icon}
    </span>
  )
}
