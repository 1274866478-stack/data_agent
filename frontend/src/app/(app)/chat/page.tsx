/**
 * # ChatPage AI聊天页面
 *
 * ## [MODULE]
 * **文件名**: app/(app)/chat/page.tsx
 * **职责**: 提供AI智能分析对话界面，集成聊天组件和数据查询功能
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - 无直接 Props（页面组件）
 *
 * ## [OUTPUT]
 * - **返回值**: JSX.Element - 全屏聊天界面容器
 *
 * ## [LINK]
 * **上游依赖**:
 * - [@/components/chat/ChatInterface](../../components/chat/ChatInterface.tsx) - 核心聊天界面组件
 *
 * **下游依赖**:
 * - 无（页面是用户交互入口点）
 *
 * ## [STATE]
 * - 无直接状态（由 ChatInterface 组件管理）
 *
 * ## [SIDE-EFFECTS]
 * - **全屏布局**: 使用 h-screen 和 flex 布局实现全屏聊天界面
 * - **组件集成**: 托管 ChatInterface 组件的所有交互和状态管理
 */
'use client'

import { ChatInterface } from '@/components/chat/ChatInterface'

export default function ChatPage() {
  return (
    <div className="h-screen flex flex-col">
      <ChatInterface className="flex-1" />
    </div>
  )
}