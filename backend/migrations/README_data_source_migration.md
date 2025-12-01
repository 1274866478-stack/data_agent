# Data Source Connections 表迁移指南

## 概述

本迁移将 `data_source_connections` 表结构从独立的SQL脚本转换为标准的Alembic迁移，确保与SQLAlchemy模型的完全一致性。

## 迁移信息

- **迁移文件**: `007_migrate_data_source_connections.py`
- **前一个版本**: `006_fix_foreign_key_types`
- **创建日期**: 2025-12-01
- **目的**: 统一表结构与SQLAlchemy模型定义

## 主要变更

### 1. 表结构更新
- **主键**: `id VARCHAR(255)` (匹配SQLAlchemy的String类型)
- **外键**: `tenant_id VARCHAR(255)` 指向 `tenants(id)`
- **状态字段**: 使用PostgreSQL枚举类型 `dataconnectionstatus`
- **索引**: 添加 `tenant_id`, `status`, `db_type` 索引
- **触发器**: 自动更新 `updated_at` 字段

### 2. 枚举类型定义
```sql
CREATE TYPE dataconnectionstatus AS ENUM (
    'active',    -- 活跃连接
    'inactive',  -- 非活跃连接
    'error',     -- 错误状态
    'testing'    -- 测试中
);
```

### 3. 安全机制
- **数据备份**: 自动创建 `data_source_connections_backup` 表
- **事务安全**: 整个迁移在单个事务中执行
- **回滚支持**: 提供完整的downgrade方法

## 使用方法

### 方法1: 使用自动化脚本（推荐）

```bash
# 在项目根目录执行
cd backend
python scripts/run_data_source_migration.py
```

### 方法2: 手动执行Alembic命令

```bash
# 1. 检查当前状态
python -m alembic current

# 2. 执行迁移
python -m alembic upgrade head

# 3. 验证迁移结果
python -m alembic current
```

### 方法3: 迁移到特定版本

```bash
# 只迁移data source connections表
python -m alembic upgrade 007_migrate_data_source_connections
```

## 验证步骤

迁移完成后，可以通过以下方式验证：

### 1. 检查表结构
```sql
-- 连接到数据库
\c dataagent

-- 查看表结构
\d data_source_connections

-- 检查索引
\di data_source_connections_*

-- 检查约束
\d+ data_source_connections
```

### 2. 验证枚举类型
```sql
-- 查看枚举定义
\dT dataconnectionstatus

-- 验证枚举值
SELECT unnest(enum_range(NULL::dataconnectionstatus));
```

### 3. 检查触发器
```sql
-- 查看触发器
\df update_data_source_connections_updated_at
```

## 回滚方案

如果需要回滚迁移：

### 方法1: 使用Alembic回滚
```bash
# 回滚一个版本
python -m alembic downgrade -1

# 回滚到特定版本
python -m alembic downgrade 006_fix_foreign_key_types
```

### 方法2: 手动恢复（紧急情况）
```sql
-- 如果备份表存在，可以手动恢复
DROP TABLE IF EXISTS data_source_connections;
ALTER TABLE data_source_connections_backup RENAME TO data_source_connections;
```

## 注意事项

### 1. 数据兼容性
- 迁移会自动创建备份表 `data_source_connections_backup`
- 如果原表中有数据，需要手动映射到新结构
- 枚举值会自动转换，但建议验证转换结果

### 2. 环境要求
- PostgreSQL 12+ (支持枚举类型和JSONB)
- Alembic 1.8+
- SQLAlchemy 2.0+

### 3. 性能影响
- 迁移期间会短暂锁定表
- 大量表数据迁移可能需要较长时间
- 建议在维护窗口执行

## 故障排除

### 问题1: 迁移失败
```bash
# 检查错误详情
python -m alembic upgrade head --verbose

# 查看迁移历史
python -m alembic history
```

### 问题2: 枚举类型错误
```sql
-- 手动删除冲突的枚举类型
DROP TYPE IF EXISTS dataconnectionstatus CASCADE;
```

### 问题3: 外键约束错误
```sql
-- 检查tenants表是否存在
SELECT * FROM information_schema.tables WHERE table_name = 'tenants';

-- 验证外键数据完整性
SELECT DISTINCT tenant_id FROM data_source_connections
WHERE tenant_id NOT IN (SELECT id FROM tenants);
```

## 相关文件

- **迁移文件**: `backend/migrations/versions/007_migrate_data_source_connections.py`
- **SQL模型**: `backend/src/app/data/models.py` 中的 `DataSourceConnection` 类
- **原始SQL**: `backend/scripts/migrate-data-source-connections.sql` (可以删除)
- **执行脚本**: `backend/scripts/run_data_source_migration.py`

## 联系支持

如果在迁移过程中遇到问题，请：

1. 检查错误日志
2. 验证数据库连接
3. 确认权限设置
4. 备份数据后重试