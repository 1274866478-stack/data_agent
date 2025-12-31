# Migrations

数据库迁移目录。

## Scope
Alembic 数据库迁移脚本。

## Members
| 目录 | 职责 |
|------|------|
| `/versions` | 迁移版本文件 |

## Constraints
- 使用 `alembic revision` 创建新迁移
- 迁移文件命名必须描述变更内容
- 迁移必须包含 upgrade() 和 downgrade()
