/**
 * # HeroSection 算力证书风格标题区域组件
 *
 * ## [MODULE]
 * **文件名**: HeroSection.tsx
 * **职责**: 页面标题区域，包含状态指示器和主标题
 * **作者**: Data Agent Team
 * **版本**: 2.0.0
 *
 * ## [INPUT]
 * - 无Props
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 标题区域组件
 */
'use client'

export function HeroSection() {
  return (
    <section className="pt-32 pb-12 px-6">
      <div className="max-w-4xl mx-auto text-center">
        {/* 状态指示器 */}
        <div className="inline-flex items-center gap-2 mb-8">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#82d9d0] opacity-75 pricing-status-ping" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#82d9d0]" />
          </span>
          <span className="pricing-tech-label text-[#82d9d0]">
            SYSTEM ONLINE
          </span>
        </div>

        {/* 主标题 */}
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-display font-bold text-white mb-6 tracking-tight">
          选择您的算力等级
        </h1>

        {/* 描述文字 */}
        <p className="text-lg md:text-xl text-white/50 max-w-2xl mx-auto leading-relaxed">
          从基础节点到企业级集群，为不同规模的智能体部署提供灵活的算力支持。
          <br className="hidden md:block" />
          所有套餐均包含 24/7 技术支持和 99.9% SLA 保证。
        </p>

        {/* 技术规格标签 */}
        <div className="flex items-center justify-center gap-6 mt-8">
          {[
            { label: 'GPU 集群', value: 'A100/H100' },
            { label: '延迟', value: '<20ms' },
            { label: '可用性', value: '99.9%' },
          ].map((spec) => (
            <div
              key={spec.label}
              className="flex flex-col items-center gap-1 px-4 py-2
                rounded-lg border border-white/5 bg-white/[0.02]"
            >
              <span className="pricing-tech-label text-white/30">
                {spec.label}
              </span>
              <span className="text-sm text-white/60 font-mono">
                {spec.value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
