# ChatBI Project Root

ChatBI 数据智能分析平台的顶层入口。

## Scope
多租户 SaaS 数据分析平台，支持自然语言查询数据库、AI 对话分析和可视化展示。

## Members
| 目录 | 职责 |
|------|------|
| `/backend` | FastAPI 后端服务 (API, 业务逻辑, 数据层) |
| `/frontend` | Next.js 前端应用 (用户界面, 状态管理) |
| `/Agent` | LangGraph SQL 智能代理 (独立服务) |
| `/data_storage` | 本地数据库文件存储 (开发环境) |
| `/docs` | 项目文档 (PRD, 架构设计, 用户故事) |
| `/scripts` | 自动化脚本 (Docker管理, 配置验证) |
| `/openspec` | OpenSpec 变更管理 (提案, 规格) |

## Constraints
- **修改代码前必须阅读 [`.claudecode.md`](.claudecode.md) 协议**
- 遵循多租户数据隔离原则
- 新功能需要通过 OpenSpec 提案流程
- 敏感配置通过环境变量管理，禁止硬编码
