# Chat Components

聊天界面组件。

## Scope
AI 对话界面的所有组件。

## Members
| 组件 | 职责 |
|------|------|
| `ChatInterface.tsx` | 主聊天界面 |
| `MessageList.tsx` | 消息列表 |
| `MessageInput.tsx` | 输入框 |
| `SearchPanel.tsx` | 搜索面板 |
| `EChartsRenderer.tsx` | 图表渲染器 |

## Constraints
- 使用 Zustand 管理聊天状态
- 支持 Markdown 渲染
- 处理流式响应
