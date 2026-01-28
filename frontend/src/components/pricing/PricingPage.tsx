/**
 * # PricingPage 会员收费页面主组件
 *
 * ## [MODULE]
 * **文件名**: PricingPage.tsx
 * **职责**: ChatGPT 风格的会员收费页面，展示套餐价格和功能
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - currentSubscription?: UserSubscription - 用户当前订阅信息
 * - onSubscribe?: (planType: PlanType, billingPeriod: BillingPeriod) => void - 订阅回调
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 完整的会员收费页面
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [lucide-react](https://lucide.dev) - 图标库
 * - [./BillingToggle.tsx](./BillingToggle.tsx) - 计费周期切换
 * - [./PricingCard.tsx](./PricingCard.tsx) - 价格卡片
 * - [./types.ts](./types.ts) - 类型定义
 *
 * **下游依赖**: 无
 *
 * **调用方**:
 * - [../../app/(app)/pricing/page.tsx](../../app/(app)/pricing/page.tsx) - 定价页面
 */
'use client'

import { useState } from 'react'
import { BillingPeriod, Plan, PlanType, PricingPageProps } from './types'
import { BillingToggle } from './BillingToggle'
import { PricingCard } from './PricingCard'
import { Info } from 'lucide-react'

/**
 * 套餐配置
 */
const PLANS: Plan[] = [
  {
    type: 'free',
    name: 'Free',
    description: 'For individuals exploring data analytics',
    monthlyPrice: 0,
    yearlyPrice: 0,
    features: [
      { text: 'Basic AI chat interface', included: true },
      { text: '5 queries per day', included: true },
      { text: 'Community support', included: true },
      { text: 'Basic data visualizations', included: true },
      { text: 'Advanced analytics', included: false },
      { text: 'Priority support', included: false },
      { text: 'API access', included: false },
    ],
    ctaText: 'Get Started',
  },
  {
    type: 'pro',
    name: 'Pro',
    description: 'For professionals who need more power',
    monthlyPrice: 20,
    yearlyPrice: 192,
    highlighted: true,
    features: [
      { text: 'Advanced AI chat interface', included: true },
      { text: 'Unlimited queries', included: true },
      { text: 'Priority email support', included: true },
      { text: 'Advanced data visualizations', included: true },
      { text: 'Custom AI models', included: true },
      { text: 'Export to CSV/Excel', included: true },
      { text: 'API access (10,000 calls/month)', included: true },
    ],
    ctaText: 'Upgrade to Pro',
  },
  {
    type: 'enterprise',
    name: 'Enterprise',
    description: 'For teams and organizations',
    monthlyPrice: 0,
    yearlyPrice: 0,
    features: [
      { text: 'Everything in Pro', included: true },
      { text: 'Unlimited API calls', included: true },
      { text: 'Dedicated account manager', included: true },
      { text: 'Custom integrations', included: true },
      { text: 'SSO authentication', included: true },
      { text: 'SLA guarantee', included: true },
      { text: 'On-premise deployment option', included: true },
    ],
    ctaText: 'Contact Sales',
  },
]

export function PricingPage({ currentSubscription, onSubscribe }: PricingPageProps) {
  const [billingPeriod, setBillingPeriod] = useState<BillingPeriod>('monthly')
  const [loadingPlan, setLoadingPlan] = useState<PlanType | null>(null)

  const handleSubscribe = async (planType: PlanType) => {
    if (planType === 'enterprise') {
      // Enterprise 套餐跳转到联系销售页面
      window.location.href = 'mailto:sales@chatbi.com?subject=Enterprise Plan Inquiry'
      return
    }

    setLoadingPlan(planType)

    try {
      // 调用订阅回调
      if (onSubscribe) {
        await onSubscribe(planType, billingPeriod)
      }
    } finally {
      setLoadingPlan(null)
    }
  }

  // 获取用户当前套餐
  const currentPlanType = currentSubscription?.planType

  return (
    <div className="w-full max-w-6xl mx-auto px-4 py-12">
      {/* 页面标题 */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-semibold text-gray-900 mb-4">
          Choose your plan
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Start with our free plan, upgrade when you need more features.
          No credit card required for free plan.
        </p>
      </div>

      {/* 计费周期切换 */}
      <div className="mb-12">
        <BillingToggle
          value={billingPeriod}
          onChange={setBillingPeriod}
        />
      </div>

      {/* 价格卡片网格 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        {PLANS.map((plan) => (
          <PricingCard
            key={plan.type}
            plan={plan}
            billingPeriod={billingPeriod}
            isCurrentPlan={currentPlanType === plan.type}
            onSubscribe={handleSubscribe}
            isLoading={loadingPlan === plan.type}
          />
        ))}
      </div>

      {/* 底部说明 */}
      <div className="max-w-2xl mx-auto">
        <div className="flex items-start gap-3 p-4 bg-gray-50 rounded-lg">
          <Info className="h-5 w-5 text-gray-500 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-gray-600 space-y-1">
            <p className="font-medium text-gray-700">About billing</p>
            <ul className="space-y-1 text-gray-500">
              <li>• Monthly plans renew automatically each month</li>
              <li>• Yearly plans save you 20% compared to monthly</li>
              <li>• You can change or cancel your plan anytime</li>
              <li>• Refunds available within 30 days of purchase</li>
            </ul>
          </div>
        </div>
      </div>

      {/* FAQ 链接 */}
      <div className="text-center mt-8">
        <a
          href="/faq"
          className="text-sm text-gray-500 hover:text-gray-700 underline"
        >
          Have questions? View our FAQ
        </a>
      </div>
    </div>
  )
}
