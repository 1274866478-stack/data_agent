/**
 * # ComparisonTable 实验室规格对比表格组件
 *
 * ## [MODULE]
 * **文件名**: ComparisonTable.tsx
 * **职责**: 技术风格的功能对比表格
 * **作者**: Data Agent Team
 * **版本**: 2.0.0
 *
 * ## [INPUT]
 * - 无Props
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 对比表格组件
 */
'use client'

export function ComparisonTable() {
  // 对比数据
  const comparisons = [
    {
      category: '计算资源',
      features: [
        { label: 'Token 吞吐量', basic: '500K/月', pro: '5M/月', enterprise: '无限' },
        { label: '并发线程', basic: '1', pro: '10', enterprise: '无限' },
        { label: 'GPU 类型', basic: '共享', pro: '专用 A100', enterprise: 'H100 集群' },
      ],
    },
    {
      category: '网络性能',
      features: [
        { label: '神经延迟', basic: '标准', pro: '低延迟', enterprise: '超低延迟' },
        { label: '数据流水线', basic: '批处理', pro: '实时', enterprise: '定制化' },
        { label: 'CDN 加速', basic: '-', pro: '全球节点', enterprise: '专属边缘' },
      ],
    },
    {
      category: '支持服务',
      features: [
        { label: '技术支持', basic: '社区', pro: '24/7 优先', enterprise: '专属经理' },
        { label: '响应时间', basic: '48小时', pro: '4小时', enterprise: '30分钟' },
        { label: '架构咨询', basic: '-', pro: '标准', enterprise: '专家级' },
      ],
    },
  ]

  return (
    <section className="py-20 px-6">
      <div className="max-w-5xl mx-auto">
        {/* 标题 */}
        <div className="text-center mb-12">
          <h2 className="text-2xl md:text-3xl font-display font-bold text-white mb-3">
            实验室规格对比
          </h2>
          <p className="text-white/40 text-sm">
            详细的技术规格对比，助您选择最合适的算力方案
          </p>
        </div>

        {/* 表格 */}
        <div className="pricing-bg-card-dark border border-white/10 rounded-lg overflow-hidden">
          {/* 表头 */}
          <div className="grid grid-cols-4 border-b border-white/10">
            <div className="p-4 border-r border-white/10">
              <span className="pricing-comparison-header">规格项目</span>
            </div>
            <div className="p-4 border-r border-white/10 text-center">
              <span className="pricing-comparison-header">基础版</span>
            </div>
            <div className="p-4 border-r border-white/10 text-center bg-[#82d9d0]/5">
              <span className="pricing-comparison-header text-[#82d9d0]">专业版</span>
            </div>
            <div className="p-4 text-center">
              <span className="pricing-comparison-header">企业级</span>
            </div>
          </div>

          {/* 表格内容 */}
          {comparisons.map((group, groupIndex) => (
            <div key={groupIndex}>
              {/* 分类标题行 */}
              <div className="grid grid-cols-4 bg-white/[0.02] border-b border-white/5">
                <div className="p-3 border-r border-white/10">
                  <span className="pricing-tech-label text-[#82d9d0]">
                    {group.category.toUpperCase()}
                  </span>
                </div>
                <div className="p-3 border-r border-white/10" />
                <div className="p-3 border-r border-white/10" />
                <div className="p-3" />
              </div>

              {/* 功能行 */}
              {group.features.map((feature, featureIndex) => (
                <div
                  key={featureIndex}
                  className={`
                    grid grid-cols-4 border-b border-white/5
                    ${featureIndex === group.features.length - 1 ? 'border-b-white/10' : ''}
                  `}
                >
                  <div className="p-4 border-r border-white/10">
                    <span className="pricing-comparison-row-label">
                      {feature.label}
                    </span>
                  </div>
                  <div className="p-4 border-r border-white/10 text-center">
                    <span className="pricing-comparison-row-value">
                      {feature.basic}
                    </span>
                  </div>
                  <div className="p-4 border-r border-white/10 text-center bg-[#82d9d0]/5">
                    <span className="pricing-comparison-row-value highlight">
                      {feature.pro}
                    </span>
                  </div>
                  <div className="p-4 text-center">
                    <span className="pricing-comparison-row-value primary">
                      {feature.enterprise}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* 底部说明 */}
        <div className="mt-6 text-center">
          <p className="text-white/30 text-xs">
            * 企业级套餐支持定制化配置，请联系销售团队获取详细方案
          </p>
        </div>
      </div>
    </section>
  )
}
