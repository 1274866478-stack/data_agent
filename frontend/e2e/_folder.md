# E2E Tests

Playwright 端到端测试。

## Scope
用户流程的完整测试覆盖。

## Members
| 文件 | 职责 |
|------|------|
| `health-check.spec.ts` | 健康检查测试 |
| `tenant-management.spec.ts` | 租户管理测试 |
| `data-source-management.spec.ts` | 数据源管理测试 |
| `document-management.spec.ts` | 文档管理测试 |

## Constraints
- 测试必须独立运行
- 使用测试账号和数据
- 清理测试产生的数据
