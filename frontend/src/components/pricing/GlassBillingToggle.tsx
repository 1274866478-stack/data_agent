/**
 * # GlassBillingToggle 玻璃态计费周期切换组件
 *
 * ## [MODULE]
 * **文件名**: GlassBillingToggle.tsx
 * **职责**: 玻璃态风格的月付/年付切换开关
 * **作者**: Data Agent Team
 * **版本**: 2.0.0
 *
 * ## [INPUT]
 * - billingPeriod: 'monthly' | 'yearly' - 当前计费周期
 * - onChange: (period: 'monthly' | 'yearly') => void - 切换回调
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 玻璃态切换组件
 */
'use client'

import { useState } from 'react'

interface GlassBillingToggleProps {
  billingPeriod: 'monthly' | 'yearly'
  onChange: (period: 'monthly' | 'yearly') => void
}

export function GlassBillingToggle({
  billingPeriod,
  onChange,
}: GlassBillingToggleProps) {
  const [isAnimating, setIsAnimating] = useState(false)

  const handleChange = (period: 'monthly' | 'yearly') => {
    if (period !== billingPeriod) {
      setIsAnimating(true)
      onChange(period)
      setTimeout(() => setIsAnimating(false), 300)
    }
  }

  return (
    <div className="flex items-center justify-center my-12">
      <div
        className={`
          pricing-glass-toggle relative rounded-lg p-1
          flex items-center gap-1
          w-[280px] h-[48px]
          ${isAnimating ? 'scale-105' : ''}
          transition-transform duration-300
        `}
      >
        {/* 月付选项 */}
        <label className="flex-1 h-full relative cursor-pointer">
          <input
            type="radio"
            name="billing-period"
            value="monthly"
            checked={billingPeriod === 'monthly'}
            onChange={() => handleChange('monthly')}
            className="pricing-radio-hidden"
          />
          <span className="pricing-billing-label">
            月付
          </span>
        </label>

        {/* 年付选项 */}
        <label className="flex-1 h-full relative cursor-pointer">
          <input
            type="radio"
            name="billing-period"
            value="yearly"
            checked={billingPeriod === 'yearly'}
            onChange={() => handleChange('yearly')}
            className="pricing-radio-hidden"
          />
          <span className="pricing-billing-label">
            年付
            <span className="ml-1 pricing-primary text-[10px] font-normal">
              省20%
            </span>
          </span>
        </label>
      </div>
    </div>
  )
}
