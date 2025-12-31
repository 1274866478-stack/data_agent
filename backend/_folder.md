# Backend Module

FastAPI 后端服务模块。

## Scope
提供 RESTful API、业务逻辑处理、数据持久化和外部服务集成。

## Members
| 目录 | 职责 |
|------|------|
| `/src` | 源代码目录 |
| `/tests` | 测试文件 |
| `/data` | 测试数据 |
| `/logs` | 日志输出 |
| `/migrations` | 数据库迁移 |
| `/scripts` | 后端脚本 |

## Constraints
- 必须使用 async/await 模式
- 所有业务 API 必须包含租户隔离
- 使用 Pydantic 进行请求验证
