'use client'

/**
 * # Pricing Page 算力证书风格会员收费页面
 *
 * ## [MODULE]
 * **文件名**: page.tsx
 * **职责**: 算力证书风格的会员收费页面路由（全屏版本）
 * **作者**: Data Agent Team
 * **版本**: 2.1.0
 *
 * ## [INPUT]
 * - 无Props输入
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 会员收费页面
 *
 * ## [LINK]
 * **上游依赖**:
 * - [next/navigation](https://nextjs.org/docs/app/navigation) - Next.js导航
 * - [@/components/pricing/PricingPageV2](../../../components/pricing/PricingPageV2.tsx) - 定价页面组件 V2
 * - [@/components/auth/AuthContext](../../../components/auth/AuthContext.tsx) - 认证上下文
 *
 * **下游依赖**: 无
 */

import { PricingPageV2 } from '@/components/pricing/PricingPageV2'
import { useAuth } from '@/components/auth/AuthContext'
import { useRouter } from 'next/navigation'

export default function PricingPageRoute() {
  const { user, isAuthenticated } = useAuth()
  const router = useRouter()

  // 处理订阅点击
  const handleSubscribe = async (
    planType: 'basic' | 'pro' | 'enterprise',
    billingPeriod: 'monthly' | 'yearly'
  ) => {
    if (!isAuthenticated) {
      // 未登录用户跳转到登录页
      router.push(`/sign-in?redirect=/pricing&plan=${planType}&billing=${billingPeriod}`)
      return
    }

    // TODO: 实现支付流程
    // 1. 调用后端 API 创建订阅
    // 2. 跳转到支付页面 (Stripe Checkout)
    // 3. 支付完成后回调处理

    console.log('Subscribe to:', planType, billingPeriod)

    // 计算价格
    const prices = {
      basic: { monthly: 0, yearly: 0 },
      pro: { monthly: 299, yearly: Math.round(2870 / 12) },
      enterprise: { monthly: 999, yearly: Math.round(9590 / 12) },
    }

    const price = prices[planType][billingPeriod]

    // 临时提示
    if (planType === 'enterprise') {
      alert(`企业级套餐请联系销售团队\n\n我们将安排架构师与您对接\n提供定制化方案`)
    } else {
      alert(`订阅功能正在开发中\n\n套餐: ${planType.toUpperCase()}\n计费: ${billingPeriod === 'monthly' ? '月付' : '年付'}\n价格: ¥${price}/月`)
    }
  }

  return <PricingPageV2 onSubscribe={handleSubscribe} />
}
