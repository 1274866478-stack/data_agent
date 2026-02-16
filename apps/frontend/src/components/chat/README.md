# Chat Interface Components

这个目录包含了 Data Agent V4 聊天界面相关的所有组件和功能。

## 组件概览

### 核心组件

#### `ChatInterface.tsx`
主聊天界面组件，包含：
- 侧边栏：会话列表、搜索、操作按钮
- 主聊天区域：消息列表、输入框
- 响应式设计：支持移动端和桌面端

#### `MessageList.tsx`
消息列表组件，负责：
- 渲染用户和AI消息
- 支持Markdown格式显示
- 显示消息状态和时间戳
- 自动滚动到最新消息
- 显示元数据（来源、推理过程、置信度）

#### `MessageInput.tsx`
消息输入组件，功能包括：
- 多行文本输入
- 自动调整高度
- 键盘快捷键支持（Enter发送、Shift+Enter换行、Escape清空）
- 文件拖拽上传支持
- 字符计数和限制
- 发送状态指示

## 状态管理

### `chatStore.ts`
使用Zustand进行状态管理：
- 会话管理（创建、切换、删除）
- 消息管理（添加、更新、删除）
- 加载和错误状态
- 本地存储持久化

### 主要状态
```typescript
interface ChatState {
  sessions: ChatSession[]           // 会话列表
  currentSession: ChatSession | null // 当前会话
  isLoading: boolean               // 加载状态
  isTyping: boolean                // 输入状态
  error: string | null            // 错误信息
  stats: ChatStats                // 统计信息
}
```

## UI组件

### 创建的UI组件
- `textarea.tsx`: 多行文本输入组件
- `separator.tsx`: 分隔线组件
- `sheet.tsx`: 侧边抽屉组件
- `scroll-area.tsx`: 滚动区域组件
- `markdown.tsx`: Markdown渲染组件
- `typography.tsx`: 文字排版组件

## API集成

### `api-client.ts`
统一的API客户端，支持：
- 聊天查询（/api/v1/query）
- 会话管理（/api/v1/chat/sessions）
- 数据源管理（/api/v1/data-sources）
- 文档管理（/api/v1/documents）
- 健康检查（/api/v1/health）

## 功能特性

### ✅ 已实现功能
1. **会话管理**
   - 创建新会话
   - 切换会话
   - 删除会话
   - 会话持久化存储

2. **消息处理**
   - 发送用户消息
   - 接收AI响应
   - 消息状态显示
   - Markdown渲染
   - 元数据显示

3. **用户体验**
   - 响应式设计
   - 键盘快捷键
   - 拖拽文件上传
   - 实时输入状态
   - 自动滚动

4. **界面设计**
   - the curator风格设计
   - 现代化UI组件
   - 深色/浅色主题支持
   - 移动端适配

### 🔧 待优化功能
1. **性能优化**
   - 消息虚拟滚动
   - 图片懒加载
   - 代码分割

2. **功能增强**
   - 文件上传集成
   - 语音输入
   - 消息导出
   - 搜索功能

3. **错误处理**
   - 网络重试机制
   - 离线支持
   - 更好的错误提示

## 使用方法

### 基本用法
```tsx
import { ChatInterface } from '@/components/chat/ChatInterface'

export default function ChatPage() {
  return (
    <div className="h-screen">
      <ChatInterface />
    </div>
  )
}
```

### 自定义消息输入
```tsx
import { MessageInput } from '@/components/chat/MessageInput'

export default function CustomChat() {
  const handleFileAttach = (files: File[]) => {
    console.log('Files attached:', files)
  }

  return (
    <MessageInput
      placeholder="输入您的问题..."
      maxLength={2000}
      onFileAttach={handleFileAttach}
    />
  )
}
```

### 使用聊天状态
```tsx
import { useChatStore } from '@/store/chatStore'

export default function ChatStats() {
  const { stats, sessions } = useChatStore()

  return (
    <div>
      <p>总会话数: {stats.totalSessions}</p>
      <p>总消息数: {stats.totalMessages}</p>
      <p>当前会话数: {sessions.length}</p>
    </div>
  )
}
```

## 样式规范

### 设计系统
- 遵循 the curator 设计规范
- 使用 Tailwind CSS utility classes
- 响应式断点：sm (640px), md (768px), lg (1024px)
- 颜色系统：primary, secondary, muted, destructive

### 组件样式
- 圆角：rounded-lg (8px), rounded-full (50%)
- 间距：p-4 (16px), gap-3 (12px)
- 阴影：shadow-sm, shadow-md
- 边框：border (1px), border-2 (2px)

## 测试

### 组件测试
```tsx
import { render, screen } from '@testing-library/react'
import { ChatInterface } from '@/components/chat/ChatInterface'

test('renders chat interface', () => {
  render(<ChatInterface />)
  expect(screen.getByText('开始对话')).toBeInTheDocument()
})
```

### 状态测试
```tsx
import { useChatStore } from '@/store/chatStore'

test('creates new session', () => {
  const { createSession, sessions } = useChatStore.getState()
  const sessionId = createSession('Test Session')

  expect(sessionId).toBeDefined()
  expect(sessions).toHaveLength(1)
})
```

## 开发指南

### 添加新功能
1. 在 `chatStore.ts` 中添加状态和操作
2. 创建相应的组件
3. 更新 API 客户端（如需要）
4. 添加测试用例
5. 更新文档

### 调试技巧
1. 使用浏览器开发工具检查状态变化
2. 查看 Network 标签检查API调用
3. 使用 React DevTools 检查组件树
4. 检查控制台错误信息

## 部署注意事项

1. **环境变量**: 确保 `NEXT_PUBLIC_API_URL` 正确配置
2. **CORS设置**: 后端API需要正确配置CORS
3. **静态资源**: 确保所有组件和依赖正确打包
4. **性能监控**: 使用性能监控工具跟踪用户体验

## 相关文件

- `src/store/chatStore.ts`: 聊天状态管理
- `src/lib/api-client.ts`: API客户端
- `src/app/(app)/chat/page.tsx`: 聊天页面路由
- `src/components/ui/`: UI组件库
- `tailwind.config.js`: Tailwind配置