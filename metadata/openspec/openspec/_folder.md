# OpenSpec

规格驱动开发变更管理系统。

## Scope
管理项目变更提案、规格说明和实施追踪。

## Members
| 文件/目录 | 职责 |
|----------|------|
| `AGENTS.md` | AI 助手工作流说明 |
| `project.md` | 项目上下文配置 |
| `/changes` | 变更提案目录（当前为空） |

## Constraints
- 使用 `/proposal` 命令创建新变更
- 使用 `/apply` 命令实施已批准的变更
- 使用 `/archive` 命令归档已部署的变更
- 参见 AGENTS.md 了解完整工作流
