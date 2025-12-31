# API V1

API V1 路由组。

## Scope
版本 1 的所有 API 路由。

## Members
| 目录 | 职责 |
|------|------|
| `/endpoints` | API 端点实现 |

## Constraints
- 所有路由以 `/api/v1` 开头
- 健康检查端点无需认证
- 业务端点需要租户认证
