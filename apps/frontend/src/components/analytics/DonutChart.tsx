/**
 * [HEADER]
 * 环形图组件 (Donut Chart) - Analytics 页面专用
 *
 * [MODULE]
 * 模块类型: React UI 组件
 * 所属功能: 数据可视化 - 环形进度图
 * 技术栈: React, TypeScript, SVG
 *
 * [INPUT]
 * Props:
 * - percentage: number - 百分比值 (0-100)
 * - size?: number - 图表尺寸 (px)，默认 192
 * - label?: string - 中心标签文本，默认 '主节点'
 * - subLabel?: string - 中心副标签文本，默认 '65%'
 * - gradientId?: string - SVG 渐变 ID，默认 'tiffanyGradient'
 *
 * [OUTPUT]
 * - 渲染 SVG 环形图，带有 Tiffany 渐变效果和发光效果
 *
 * [LINK]
 * - 使用路径: @/components/analytics/DonutChart
 * - 配套组件: ActivityLogTable, EmptyDocumentState
 *
 * [POS]
 * - 文件路径: frontend/src/components/analytics/DonutChart.tsx
 *
 * [STATE]
 * - 无状态组件
 *
 * [PROTOCOL]
 * - 使用 SVG stroke-dasharray 实现环形进度
 * - 使用 SVG linearGradient 实现 Tiffany 渐变
 * - 添加 drop-shadow 发光效果
 */

interface DonutChartProps {
  /** 百分比值 (0-100) */
  percentage: number
  /** 图表尺寸 (px)，默认 192 */
  size?: number
  /** 中心标签文本，默认 '主节点' */
  label?: string
  /** 中心副标签文本，默认显示百分比 */
  subLabel?: string
  /** SVG 渐变 ID，默认 'tiffanyGradient' */
  gradientId?: string
}

/**
 * 环形图组件
 *
 * 显示带有 Tiffany 渐变效果的环形进度图
 *
 * @example
 * ```tsx
 * <DonutChart percentage={65} />
 * <DonutChart
 *   percentage={80}
 *   size={240}
 *   label="完成度"
 *   subLabel="80%"
 * />
 * ```
 */
export function DonutChart({
  percentage,
  size = 192,
  label = '主节点',
  subLabel,
  gradientId = 'tiffanyGradient'
}: DonutChartProps) {
  const radius = 16
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (percentage / 100) * circumference

  return (
    <div
      className="relative"
      style={{ width: `${size}px`, height: `${size}px` }}
    >
      <svg
        className="w-full h-full -rotate-90"
        viewBox="0 0 36 36"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#81d8cf" />
            <stop offset="100%" stopColor="#6bc9c0" />
          </linearGradient>
        </defs>
        {/* 背景圆环 */}
        <circle
          cx="18"
          cy="18"
          fill="none"
          r={radius}
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-slate-100 dark:text-slate-700"
        />
        {/* 进度圆环 */}
        <circle
          cx="18"
          cy="18"
          fill="none"
          r={radius}
          stroke={`url(#${gradientId})`}
          strokeWidth="2.5"
          strokeDasharray={`${percentage} ${100 - percentage}`}
          strokeLinecap="round"
          style={{
            filter: 'drop-shadow(0 0 5px rgba(129,216,207,0.4))',
          }}
        />
      </svg>
      {/* 中心文本 */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-extralight text-slate-800 dark:text-slate-200">
          {subLabel || `${percentage}%`}
        </span>
        <span className="analytics-tech-label !text-[8px]">{label}</span>
      </div>
    </div>
  )
}

/**
 * 多环形图组件
 *
 * 显示多个嵌套的环形进度图
 */
interface MultiDonutChartProps {
  /** 环形数据数组 */
  rings: Array<{
    percentage: number
    label: string
    color?: string
  }>
  /** 图表尺寸 (px) */
  size?: number
}

export function MultiDonutChart({ rings, size = 192 }: MultiDonutChartProps) {
  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: `${size}px`, height: `${size}px` }}
    >
      <svg
        className="w-full h-full -rotate-90"
        viewBox="0 0 36 36"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="ringGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#81d8cf" />
            <stop offset="100%" stopColor="#6bc9c0" />
          </linearGradient>
        </defs>
        {rings.map((ring, index) => {
          const radius = 6 + index * 3
          const circumference = 2 * Math.PI * radius
          const offset = circumference - (ring.percentage / 100) * circumference

          return (
            <circle
              key={index}
              cx="18"
              cy="18"
              fill="none"
              r={radius}
              stroke={ring.color || 'url(#ringGradient)'}
              strokeWidth="1.5"
              strokeDasharray={`${ring.percentage} ${100 - ring.percentage}`}
              strokeLinecap="round"
              style={{
                filter: 'drop-shadow(0 0 3px rgba(129,216,207,0.3))',
              }}
            />
          )
        })}
      </svg>
      {/* 中心统计 */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-light text-slate-800 dark:text-slate-200">
          {rings.length}
        </span>
        <span className="analytics-tech-label !text-[8px]">NODES</span>
      </div>
    </div>
  )
}
