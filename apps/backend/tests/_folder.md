# Backend Tests

后端测试套件。

## Scope
API 端点、服务层和数据模型的测试。

## Members
| 目录 | 职责 |
|------|------|
| `/api` | API 端点测试 |
| `/services` | 服务层测试 |
| `/data` | 数据模型测试 |
| `/e2e` | 端到端测试 |

## Constraints
- 使用 pytest 框架
- 测试文件命名: `test_*.py`
- 每个新功能必须有对应测试
