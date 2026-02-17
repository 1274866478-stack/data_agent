'use client'

/**
 * # BackgroundGrid 科技网格背景组件
 *
 * ## [MODULE]
 * **文件名**: BackgroundGrid.tsx
 * **职责**: 能量脉冲实验室风格的科技网格背景，带闪烁节点效果
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - 无Props输入
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 科技网格背景组件
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 *
 * **下游依赖**:
 * - [EnergyLabSignIn.tsx](./EnergyLabSignIn.tsx) - 登录页面
 */

import { useEffect, useState } from 'react'

interface GridNode {
  top: number
  left: number
  delay: number
}

export function BackgroundGrid() {
  const [nodes, setNodes] = useState<GridNode[]>([])

  useEffect(() => {
    // 生成随机网格节点
    const generatedNodes: GridNode[] = []
    const nodeCount = 20

    for (let i = 0; i < nodeCount; i++) {
      generatedNodes.push({
        top: Math.random() * 100,
        left: Math.random() * 100,
        delay: Math.random() * 3,
      })
    }

    setNodes(generatedNodes)
  }, [])

  return (
    <div className="fixed inset-0 tech-grid pointer-events-none opacity-60">
      {nodes.map((node, i) => (
        <div
          key={i}
          className="grid-node"
          style={{
            top: `${node.top}%`,
            left: `${node.left}%`,
            animationDelay: `${node.delay}s`,
          }}
        />
      ))}
    </div>
  )
}
