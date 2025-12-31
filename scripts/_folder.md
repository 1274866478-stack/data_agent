# Scripts

项目自动化脚本。

## Scope
提供 Docker 管理、环境检查、测试数据生成等自动化工具。

## Members
| 文件/目录 | 职责 |
|-----------|------|
| `check-*.py` | 环境和配置检查脚本 |
| `check-*.sh` | Shell 环境检查脚本 |
| `docker-*.sh` | Docker 启动/停止脚本 |
| `generate_*.py` | 测试数据生成 |
| `validate-*.py` | 配置验证脚本 |
| `verify-*.py` | 集成验证脚本 |
| `test-all-features.*` | 功能测试脚本 |

## Constraints
- 脚本优先使用 Python 跨平台
- Shell 脚本仅用于 Linux/Mac
- Batch 脚本仅用于 Windows
