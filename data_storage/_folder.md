# Data Storage

本地数据存储目录（开发环境）。

## Scope
存储开发环境的数据库文件和测试数据。

## Members
| 目录 | 职责 |
|------|------|
| `/data-sources` | 数据源配置存储 |

## Constraints
- 仅用于本地开发环境
- 生产环境使用外部 PostgreSQL
- 不要提交到版本控制
