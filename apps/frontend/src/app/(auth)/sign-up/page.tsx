'use client'

/**
 * # Sign Up Page 注册页面 - EnergyLab 风格
 *
 * ## [MODULE]
 * **文件名**: page.tsx
 * **职责**: 能量脉冲实验室风格的注册页面，使用技术网格背景和居中玻璃态卡片布局
 * **作者**: Data Agent Team
 * **版本**: 3.0.0
 *
 * ## [INPUT]
 * - 无Props输入
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - EnergyLab 风格注册页面
 *
 * ## [LINK]
 * **上游依赖**:
 * - [next/navigation](https://nextjs.org/docs/app/navigation) - Next.js导航
 * - [@/components/auth/EnergyLabSignUpForm](../../../components/auth/EnergyLabSignUpForm.tsx) - EnergyLab 注册表单
 * - [@/components/auth/BackgroundGrid](../../../components/auth/BackgroundGrid.tsx) - 网格背景组件
 *
 * **下游依赖**: 无
 */

import { EnergyLabSignUpForm } from '@/components/auth/EnergyLabSignUpForm'
import { BackgroundGrid } from '@/components/auth/BackgroundGrid'

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-lab-light overflow-x-hidden relative">
      {/* 背景效果 */}
      <div className="fixed inset-0 radial-glow-center pointer-events-none"></div>
      <div className="fixed inset-0 technical-grid pointer-events-none opacity-40"></div>
      <div className="fixed inset-0 glowing-nodes pointer-events-none opacity-50"></div>
      <BackgroundGrid />

      {/* 顶部系统标识 */}
      <div className="fixed top-8 left-8 text-[10px] text-lab-navy/40 uppercase tracking-[0.5em] font-bold z-20">
        High-Pulse Laboratory // Light-Sys.v2.0
      </div>

      <EnergyLabSignUpForm />
    </div>
  )
}
