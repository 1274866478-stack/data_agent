# Data Sources Components

数据源管理组件。

## Scope
数据源连接的 CRUD 界面组件。

## Members
| 组件 | 职责 |
|------|------|
| `DataSourceList.tsx` | 数据源列表 |
| `DataSourceForm.tsx` | 数据源表单 |
| `DataSourceOverview.tsx` | 数据源概览 |
| `ConnectionTest.tsx` | 连接测试 |
| `BulkOperations.tsx` | 批量操作 |

## Constraints
- 支持多种数据库类型
- 连接字符串加密存储
- 测试连接后才能保存
