/**
 * # PricingPageV2 算力证书风格主页面组件
 *
 * ## [MODULE]
 * **文件名**: PricingPageV2.tsx
 * **职责**: 算力证书风格的主页面，组装所有子组件
 * **作者**: Data Agent Team
 * **版本**: 2.0.0
 *
 * ## [INPUT]
 * - onSubscribe?: (planType: 'basic' | 'pro' | 'enterprise', billingPeriod: 'monthly' | 'yearly') => void
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 完整的定价页面
 */
'use client'

import { useState } from 'react'
import { PricingHeader } from './PricingHeader'
import { HeroSection } from './HeroSection'
import { GlassBillingToggle } from './GlassBillingToggle'
import { PricingCertificateCard } from './PricingCertificateCard'
import { ComparisonTable } from './ComparisonTable'
import { PricingFooter } from './PricingFooter'

interface PricingPageV2Props {
  onSubscribe?: (planType: 'basic' | 'pro' | 'enterprise', billingPeriod: 'monthly' | 'yearly') => void
}

// 套餐配置数据
const CERTIFICATE_PLANS = [
  {
    type: 'basic' as const,
    serial: 'SERIAL: BK-001-X',
    name: '基础版 (Basic)',
    icon: 'terminal',
    monthlyPrice: 0,
    yearlyPrice: 0,
    features: [
      '500k Token 吞吐量',
      '基础级神经延迟',
      '1个并行处理线程',
      '基础系统日志访问',
    ],
    ctaText: '初始化节点',
  },
  {
    type: 'pro' as const,
    serial: 'SERIAL: PR-772-L',
    name: '专业版 (Professional)',
    icon: 'verified_user',
    monthlyPrice: 299,
    yearlyPrice: 2870,
    highlighted: true,
    features: [
      '5M Token 吞吐量',
      '低延迟神经节点',
      '10个并行处理线程',
      '实时数据流水线',
      '24/7 优先技术支持',
    ],
    ctaText: '立即部署协议',
  },
  {
    type: 'enterprise' as const,
    serial: 'SERIAL: ET-999-MAX',
    name: '企业级 (Enterprise)',
    icon: 'hub',
    monthlyPrice: 999,
    yearlyPrice: 9590,
    features: [
      '无限 Token 吞吐量',
      '超低延迟集群 (专用)',
      '无限并行线程',
      '定制化模型微调支持',
      '专家级架构咨询',
    ],
    ctaText: '联系架构师',
  },
]

export function PricingPageV2({ onSubscribe }: PricingPageV2Props) {
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('yearly')

  const handleSubscribe = (planType: 'basic' | 'pro' | 'enterprise') => {
    if (onSubscribe) {
      onSubscribe(planType, billingPeriod)
    }
  }

  return (
    <div className="min-h-screen pricing-bg-dark pricing-neural-bg">
      {/* 顶部导航 */}
      <PricingHeader />

      {/* 主内容区域 */}
      <main>
        {/* 标题区域 */}
        <HeroSection />

        {/* 计费周期切换 */}
        <GlassBillingToggle
          billingPeriod={billingPeriod}
          onChange={setBillingPeriod}
        />

        {/* 套餐卡片 */}
        <section className="px-6 pb-16">
          <div className="max-w-6xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
              {CERTIFICATE_PLANS.map((plan) => (
                <PricingCertificateCard
                  key={plan.type}
                  plan={plan}
                  billingPeriod={billingPeriod}
                  onSubscribe={handleSubscribe}
                />
              ))}
            </div>
          </div>
        </section>

        {/* 对比表格 */}
        <ComparisonTable />
      </main>

      {/* 页脚 */}
      <PricingFooter />
    </div>
  )
}
