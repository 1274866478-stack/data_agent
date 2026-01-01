/**
 * # ChatTest 聊天测试组件
 *
 * ## [MODULE]
 * **文件名**: ChatTest.tsx
 * **职责**: 提供全屏测试环境用于ChatInterface组件的开发和调试
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - 无Props输入
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 全屏容器内的ChatInterface组件
 * - **副作用**: 无
 *
 * ## [LINK]
 * **上游依赖**:
 * - [react](https://react.dev) - React核心库
 * - [./ChatInterface.tsx](./ChatInterface.tsx) - 主聊天界面组件
 *
 * **下游依赖**:
 * - 无直接下游组件
 *
 * **调用方**:
 * - 测试页面或开发环境
 *
 * ## [STATE]
 * - 无内部状态
 *
 * ## [SIDE-EFFECTS]
 * - 无副作用
 */
'use client'

import { ChatInterface } from './ChatInterface'

export function ChatTest() {
  return (
    <div className="h-screen">
      <ChatInterface />
    </div>
  )
}