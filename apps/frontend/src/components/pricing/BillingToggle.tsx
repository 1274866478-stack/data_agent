/**
 * # BillingToggle 月付/年付切换组件
 *
 * ## [MODULE]
 * **文件名**: BillingToggle.tsx
 * **职责**: ChatGPT 风格的月付/年付切换开关
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - value: BillingPeriod - 当前计费周期
 * - onChange: (period: BillingPeriod) => void - 切换回调
 * - disabled?: boolean - 是否禁用
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 计费周期切换组件
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [@/components/ui/switch](../ui/switch.tsx) - UI Switch组件
 * - [./types.ts](./types.ts) - 类型定义
 *
 * **下游依赖**:
 * - [PricingPage.tsx](./PricingPage.tsx) - 定价页面主组件
 */
'use client'

import { BillingPeriod, BillingToggleProps } from './types'
import { cn } from '@/lib/utils'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'

export function BillingToggle({ value, onChange, disabled = false }: BillingToggleProps) {
  const isYearly = value === 'yearly'

  return (
    <div className="flex items-center justify-center gap-3">
      <Label
        htmlFor="billing-toggle"
        className={cn(
          'text-sm font-medium cursor-pointer transition-colors',
          !isYearly ? 'text-gray-900' : 'text-gray-500'
        )}
        onClick={() => !disabled && onChange('monthly')}
      >
        Monthly
      </Label>

      <Switch
        id="billing-toggle"
        checked={isYearly}
        onCheckedChange={(checked) => onChange(checked ? 'yearly' : 'monthly')}
        disabled={disabled}
        className="data-[state=checked]:bg-black data-[state=unchecked]:bg-gray-300"
      />

      <div className="flex items-center gap-2">
        <Label
          htmlFor="billing-toggle"
          className={cn(
            'text-sm font-medium cursor-pointer transition-colors',
            isYearly ? 'text-gray-900' : 'text-gray-500'
          )}
          onClick={() => !disabled && onChange('yearly')}
        >
          Yearly
        </Label>

        {/* Save 20% 标签 */}
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
          Save 20%
        </span>
      </div>
    </div>
  )
}
