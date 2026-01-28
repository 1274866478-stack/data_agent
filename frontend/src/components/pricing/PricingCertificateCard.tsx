/**
 * # PricingCertificateCard 算力证书风格套餐卡片组件
 *
 * ## [MODULE]
 * **文件名**: PricingCertificateCard.tsx
 * **职责**: 算力证书风格的套餐卡片，展示套餐信息、价格和功能列表
 * **作者**: Data Agent Team
 * **版本**: 2.0.0
 *
 * ## [INPUT]
 * - plan: CertificatePlan - 套餐配置
 * - billingPeriod: 'monthly' | 'yearly' - 当前计费周期
 * - isHighlighted?: boolean - 是否高亮显示（专业版）
 * - onSubscribe?: (planType: PlanType) => void - 订阅回调
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 套餐卡片
 */
'use client'

import { CertificatePlan, PlanType } from './types'

interface PricingCertificateCardProps {
  plan: CertificatePlan
  billingPeriod: 'monthly' | 'yearly'
  onSubscribe?: (planType: PlanType) => void
}

/**
 * 计算显示价格
 */
function calculatePrice(
  monthlyPrice: number,
  yearlyPrice: number,
  billingPeriod: 'monthly' | 'yearly'
): { displayPrice: string; periodText: string } {
  if (billingPeriod === 'monthly') {
    return {
      displayPrice: monthlyPrice === 0 ? '¥0' : `¥${monthlyPrice}`,
      periodText: '/月',
    }
  }
  return {
    displayPrice: `¥${Math.round(yearlyPrice / 12)}`,
    periodText: '/月',
  }
}

export function PricingCertificateCard({
  plan,
  billingPeriod,
  onSubscribe,
}: PricingCertificateCardProps) {
  const price = calculatePrice(plan.monthlyPrice, plan.yearlyPrice, billingPeriod)
  const isHighlighted = plan.highlighted

  const handleSubscribe = () => {
    if (onSubscribe) {
      onSubscribe(plan.type)
    }
  }

  return (
    <div
      className={`
        relative flex flex-col rounded-lg overflow-hidden
        transition-all duration-200
        ${isHighlighted
          ? 'pricing-pulse-border pricing-bg-card-highlight border border-[#82d9d0]/40 z-20 transform scale-105 shadow-2xl shadow-[#82d9d0]/10'
          : 'pricing-bg-card-dark border border-white/10 hover:border-white/20 group'
        }
      `}
    >
      {/* 证书网格背景 */}
      <div className={`pricing-certificate-grid absolute inset-0 ${isHighlighted ? 'opacity-30' : 'opacity-20'}`} />

      {/* 高亮标签 */}
      {isHighlighted && (
        <div className="bg-[#82d9d0] px-4 py-1 text-[#0a0f0e] text-[10px] font-bold uppercase tracking-[0.2em] text-center">
          最高优先级授权
        </div>
      )}

      {/* 卡片内容 */}
      <div className="p-8 relative z-10">
        {/* 头部：序列号和名称 */}
        <div className="flex justify-between items-start mb-10">
          <div>
            <span className="text-[10px] pricing-primary font-mono block mb-1">
              {plan.serial}
            </span>
            <h3 className="text-white text-xl font-bold uppercase tracking-tight font-display">
              {plan.name}
            </h3>
          </div>
          <span className="pricing-material-symbols material-symbols-outlined text-white/20">
            {plan.icon}
          </span>
        </div>

        {/* 价格区域 */}
        <div className="mb-10">
          <div className="flex items-baseline gap-1">
            <span className={`pricing-price-display text-white text-5xl ${isHighlighted ? 'tracking-tighter' : ''}`}>
              {price.displayPrice}
            </span>
            <span className="text-white/40 text-sm uppercase">{price.periodText}</span>
          </div>
          {/* 分隔线 */}
          <div className={`w-full h-[1px] mt-4 relative overflow-hidden ${isHighlighted ? 'bg-[#82d9d0]/20' : 'bg-white/5'}`}>
            {isHighlighted && (
              <div className="pricing-scan-line" />
            )}
          </div>
        </div>

        {/* 功能列表 */}
        <div className="space-y-4 mb-10">
          {plan.features.map((feature, index) => (
            <div
              key={index}
              className={`flex items-center gap-3 text-xs ${
                isHighlighted ? 'text-white' : 'text-white/70'
              }`}
            >
              <span className={`pricing-feature-dot ${isHighlighted ? 'highlight' : ''}`} />
              {feature}
            </div>
          ))}
        </div>

        {/* CTA 按钮 */}
        <button
          onClick={handleSubscribe}
          className={isHighlighted
            ? 'pricing-btn-primary'
            : 'pricing-btn-outline'
          }
        >
          {plan.ctaText}
        </button>
      </div>
    </div>
  )
}

/**
 * 证书套餐配置接口
 */
export interface CertificatePlan {
  /** 套餐类型 */
  type: PlanType
  /** 序列号 */
  serial: string
  /** 套餐名称 */
  name: string
  /** Material Symbol 图标名称 */
  icon: string
  /** 月付价格 */
  monthlyPrice: number
  /** 年付价格 */
  yearlyPrice: number
  /** 功能列表 */
  features: string[]
  /** 是否高亮 */
  highlighted?: boolean
  /** CTA 按钮文字 */
  ctaText: string
}
