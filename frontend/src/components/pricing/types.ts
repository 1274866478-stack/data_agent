/**
 * # Pricing Types 会员收费类型定义
 *
 * ## [MODULE]
 * **文件名**: types.ts
 * **职责**: 定义会员收费页面的 TypeScript 类型
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [TYPES]
 */

/**
 * 计费周期
 */
export type BillingPeriod = 'monthly' | 'yearly'

/**
 * 套餐类型
 */
export type PlanType = 'free' | 'pro' | 'enterprise'

/**
 * 功能项配置
 */
export interface Feature {
  /** 功能文本描述 */
  text: string
  /** 是否包含在套餐中 */
  included: boolean
  /** 是否为高亮功能 */
  highlight?: boolean
}

/**
 * 套餐配置
 */
export interface Plan {
  /** 套餐类型 */
  type: PlanType
  /** 套餐名称 */
  name: string
  /** 套餐描述 */
  description: string
  /** 月付价格（美元） */
  monthlyPrice: number
  /** 年付价格（美元） */
  yearlyPrice: number
  /** 功能列表 */
  features: Feature[]
  /** 是否高亮显示（Pro套餐） */
  highlighted?: boolean
  /** CTA 按钮文字 */
  ctaText: string
}

/**
 * 套餐价格计算结果
 */
export interface PlanPrice {
  /** 显示价格 */
  displayPrice: string
  /** 原价（年付时显示月付原价） */
  originalPrice?: string
  /** 计费周期文字 */
  periodText: string
}

/**
 * 订阅状态
 */
export type SubscriptionStatus =
  | 'inactive'
  | 'active'
  | 'canceled'
  | 'past_due'
  | 'trialing'

/**
 * 用户订阅信息
 */
export interface UserSubscription {
  /** 订阅状态 */
  status: SubscriptionStatus
  /** 当前套餐类型 */
  planType: PlanType
  /** 计费周期 */
  billingPeriod: BillingPeriod
  /** 订阅开始时间 */
  startDate: string
  /** 下次续费时间 */
  nextBillingDate?: string
  /** 是否取消 */
  cancelAtPeriodEnd?: boolean
}

/**
 * PricingCard 组件 Props
 */
export interface PricingCardProps {
  /** 套餐配置 */
  plan: Plan
  /** 当前计费周期 */
  billingPeriod: BillingPeriod
  /** 是否为当前套餐 */
  isCurrentPlan?: boolean
  /** 点击订阅回调 */
  onSubscribe?: (planType: PlanType) => void
  /** 是否正在加载 */
  isLoading?: boolean
}

/**
 * BillingToggle 组件 Props
 */
export interface BillingToggleProps {
  /** 当前计费周期 */
  value: BillingPeriod
  /** 切换回调 */
  onChange: (period: BillingPeriod) => void
  /** 是否禁用 */
  disabled?: boolean
}

/**
 * PricingPage 组件 Props
 */
export interface PricingPageProps {
  /** 用户当前订阅信息 */
  currentSubscription?: UserSubscription
  /** 订阅回调 */
  onSubscribe?: (planType: PlanType, billingPeriod: BillingPeriod) => void
}

/* ============================================================
   算力证书风格类型定义 - Pricing Page V2
   ============================================================ */

/**
 * 证书套餐类型
 */
export type CertificatePlanType = 'basic' | 'pro' | 'enterprise'

/**
 * 证书套餐配置接口
 */
export interface CertificatePlan {
  /** 套餐类型 */
  type: CertificatePlanType
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

/**
 * PricingPageV2 组件 Props
 */
export interface PricingPageV2Props {
  /** 订阅回调 */
  onSubscribe?: (planType: CertificatePlanType, billingPeriod: BillingPeriod) => void
}
