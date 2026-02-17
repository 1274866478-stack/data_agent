/**
 * # PricingCard 价格卡片组件
 *
 * ## [MODULE]
 * **文件名**: PricingCard.tsx
 * **职责**: ChatGPT 风格的价格卡片，展示套餐信息和价格
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - plan: Plan - 套餐配置
 * - billingPeriod: BillingPeriod - 当前计费周期
 * - isCurrentPlan?: boolean - 是否为当前套餐
 * - onSubscribe?: (planType: PlanType) => void - 点击订阅回调
 * - isLoading?: boolean - 是否正在加载
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 价格卡片
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [lucide-react](https://lucide.dev) - 图标库 (Check, Loader2)
 * - [@/components/ui/button](../ui/button.tsx) - UI基础按钮组件
 * - [./types.ts](./types.ts) - 类型定义
 *
 * **下游依赖**: 无
 */
'use client'

import { PricingCardProps, PlanType } from './types'
import { Check, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

/**
 * 计算显示价格
 */
function calculatePrice(
  monthlyPrice: number,
  yearlyPrice: number,
  billingPeriod: 'monthly' | 'yearly'
) {
  if (billingPeriod === 'monthly') {
    return {
      displayPrice: monthlyPrice === 0 ? 'Free' : `$${monthlyPrice}`,
      periodText: '/month',
    }
  }

  // 年付时显示月均价
  const monthlyEquivalent = yearlyPrice / 12
  return {
    displayPrice: `$${Math.round(monthlyEquivalent)}`,
    originalPrice: `$${monthlyPrice}`,
    periodText: '/month',
    billedText: `billed $${yearlyPrice} yearly`,
  }
}

export function PricingCard({
  plan,
  billingPeriod,
  isCurrentPlan = false,
  onSubscribe,
  isLoading = false,
}: PricingCardProps) {
  const price = calculatePrice(plan.monthlyPrice, plan.yearlyPrice, billingPeriod)
  const isHighlighted = plan.highlighted
  const isFree = plan.type === 'free'
  const isEnterprise = plan.type === 'enterprise'

  const handleSubscribe = () => {
    if (onSubscribe && !isCurrentPlan) {
      onSubscribe(plan.type)
    }
  }

  return (
    <Card
      className={cn(
        'relative transition-all duration-200',
        isHighlighted && 'scale-105 border-black border-2 shadow-lg',
        !isHighlighted && 'border-gray-200',
        isHighlighted && 'hover:shadow-xl'
      )}
    >
      {/* Most Popular 标签 */}
      {isHighlighted && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-black text-white">
            Most Popular
          </span>
        </div>
      )}

      <CardContent className="p-6">
        <div className="space-y-6">
          {/* 套餐名称和描述 */}
          <div className="space-y-2">
            <h3 className="text-xl font-semibold text-gray-900">{plan.name}</h3>
            {plan.description && (
              <p className="text-sm text-gray-500">{plan.description}</p>
            )}
          </div>

          {/* 价格 */}
          <div className="space-y-1">
            <div className="flex items-baseline gap-1">
              <span className="text-4xl font-semibold text-gray-900">
                {price.displayPrice}
              </span>
              <span className="text-gray-500">{price.periodText}</span>
            </div>
            {billingPeriod === 'yearly' && !isFree && price.originalPrice && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400 line-through">
                  {price.originalPrice}
                </span>
                <span className="text-xs text-gray-500">
                  {price.billedText}
                </span>
              </div>
            )}
          </div>

          {/* CTA 按钮 */}
          <Button
            onClick={handleSubscribe}
            disabled={isCurrentPlan || isLoading}
            className={cn(
              'w-full h-10',
              isHighlighted
                ? 'bg-black text-white hover:bg-gray-800'
                : 'bg-white text-black border border-gray-300 hover:bg-gray-50',
              isCurrentPlan && 'cursor-not-allowed opacity-70'
            )}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : isCurrentPlan ? (
              'Current Plan'
            ) : (
              plan.ctaText
            )}
          </Button>

          {/* 功能列表 */}
          <ul className="space-y-3">
            {plan.features.map((feature, index) => (
              <li key={index} className="flex items-start gap-3">
                <div
                  className={cn(
                    'mt-0.5 flex-shrink-0',
                    feature.included ? 'text-green-600' : 'text-gray-300'
                  )}
                >
                  <Check className="h-5 w-5" />
                </div>
                <span
                  className={cn(
                    'text-sm',
                    feature.included ? 'text-gray-700' : 'text-gray-400'
                  )}
                >
                  {feature.text}
                </span>
              </li>
            ))}
          </ul>

          {/* Enterprise 提示 */}
          {isEnterprise && (
            <div className="pt-4 border-t border-gray-200">
              <p className="text-sm text-gray-500 text-center">
                Contact sales for custom pricing and features
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
