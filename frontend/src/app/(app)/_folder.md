# App Routes

应用路由组。

## Scope
主应用页面的路由定义。

## Members
| 页面 | 职责 |
|------|------|
| `page.tsx` | 首页 |
| `/ai-assistant` | AI 助手 |
| `/analytics` | 数据分析 |
| `/chat` | 聊天界面 |
| `/dashboard` | 仪表板 |
| `/data-sources` | 数据源管理 |
| `/documents` | 文档管理 |
| `/reports` | 报告 |
| `/settings` | 设置 |
| `/users` | 用户管理 |

## Constraints
- 需要认证才能访问
- 使用 Clerk 进行身份验证
