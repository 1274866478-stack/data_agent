# 数据库迁移指南

本文档介绍如何使用Alembic管理Data Agent V4的数据库迁移。

---

## 📋 目录

- [Alembic简介](#alembic简介)
- [迁移文件结构](#迁移文件结构)
- [常用命令](#常用命令)
- [创建迁移](#创建迁移)
- [应用迁移](#应用迁移)
- [回滚迁移](#回滚迁移)
- [最佳实践](#最佳实践)
- [故障排查](#故障排查)

---

## 🔧 Alembic简介

Alembic是SQLAlchemy的数据库迁移工具,用于:

- ✅ 版本控制数据库schema
- ✅ 自动生成迁移脚本
- ✅ 支持升级和降级
- ✅ 多环境配置

---

## 📁 迁移文件结构

```
backend/
├── alembic/
│   ├── versions/          # 迁移脚本目录
│   │   ├── __init__.py
│   │   └── xxxx_initial_schema.py
│   ├── env.py            # Alembic环境配置
│   ├── script.py.mako    # 迁移脚本模板
│   └── README
├── alembic.ini           # Alembic配置文件
└── src/
    └── app/
        └── data/
            └── models.py  # SQLAlchemy模型定义
```

---

## 🚀 常用命令

### 查看当前版本

```bash
cd backend
alembic current
```

### 查看迁移历史

```bash
alembic history --verbose
```

### 查看待应用的迁移

```bash
alembic show head
```

---

## ✨ 创建迁移

### 1. 自动生成迁移 (推荐)

修改`models.py`后,自动检测变更并生成迁移:

```bash
cd backend

# 生成迁移脚本
alembic revision --autogenerate -m "add user profile fields"
```

**示例输出:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.autogenerate.compare] Detected added column 'tenants.phone_number'
INFO  [alembic.autogenerate.compare] Detected added column 'tenants.avatar_url'
  Generating /path/to/backend/alembic/versions/abc123_add_user_profile_fields.py ...  done
```

### 2. 手动创建迁移

对于复杂的数据迁移,手动创建:

```bash
alembic revision -m "migrate legacy data"
```

然后编辑生成的文件:

```python
"""migrate legacy data

Revision ID: def456
Revises: abc123
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'def456'
down_revision = 'abc123'
branch_labels = None
depends_on = None

def upgrade():
    # 数据迁移逻辑
    op.execute("""
        UPDATE tenants 
        SET status = 'active' 
        WHERE status IS NULL
    """)

def downgrade():
    # 回滚逻辑
    op.execute("""
        UPDATE tenants 
        SET status = NULL 
        WHERE status = 'active'
    """)
```

---

## ⬆️ 应用迁移

### 升级到最新版本

```bash
alembic upgrade head
```

### 升级到特定版本

```bash
alembic upgrade abc123
```

### 升级一个版本

```bash
alembic upgrade +1
```

---

## ⬇️ 回滚迁移

### 回滚到上一个版本

```bash
alembic downgrade -1
```

### 回滚到特定版本

```bash
alembic downgrade abc123
```

### 回滚所有迁移

```bash
alembic downgrade base
```

---

## 📝 最佳实践

### 1. 迁移命名规范

使用描述性的迁移消息:

```bash
# ✅ 好的命名
alembic revision --autogenerate -m "add tenant quota fields"
alembic revision --autogenerate -m "create data_sources table"
alembic revision --autogenerate -m "add index on tenant_id"

# ❌ 不好的命名
alembic revision --autogenerate -m "update"
alembic revision --autogenerate -m "fix"
```

### 2. 审查自动生成的迁移

自动生成后,**务必审查**迁移脚本:

```bash
# 生成迁移
alembic revision --autogenerate -m "add new fields"

# 查看生成的文件
cat alembic/versions/xxx_add_new_fields.py

# 测试迁移
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

### 3. 测试迁移的可逆性

确保`downgrade()`函数正确实现:

```python
def upgrade():
    op.add_column('tenants', sa.Column('phone_number', sa.String(20)))

def downgrade():
    op.drop_column('tenants', 'phone_number')  # ✅ 正确实现回滚
```

### 4. 数据迁移与Schema迁移分离

```bash
# 第一步: Schema变更
alembic revision --autogenerate -m "add status column"

# 第二步: 数据迁移
alembic revision -m "populate status column"
```

### 5. 使用事务

```python
def upgrade():
    # Alembic默认使用事务
    # 如果需要禁用事务:
    # op.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
    
    op.add_column('tenants', sa.Column('new_field', sa.String(100)))
    
    # 数据迁移
    op.execute("""
        UPDATE tenants 
        SET new_field = 'default_value'
    """)
```

### 6. 添加索引

```python
def upgrade():
    # 创建索引
    op.create_index(
        'ix_tenants_email',
        'tenants',
        ['email'],
        unique=True
    )

def downgrade():
    # 删除索引
    op.drop_index('ix_tenants_email', table_name='tenants')
```

---

## 🔍 故障排查

### 问题1: 迁移冲突

**错误:**
```
FAILED: Multiple head revisions are present
```

**解决:**
```bash
# 查看所有head
alembic heads

# 合并heads
alembic merge -m "merge heads" head1 head2
```

### 问题2: 数据库状态不一致

**错误:**
```
Target database is not up to date
```

**解决:**
```bash
# 查看当前版本
alembic current

# 标记为特定版本(不执行SQL)
alembic stamp head
```

### 问题3: 迁移失败

**错误:**
```
sqlalchemy.exc.ProgrammingError: column "xxx" already exists
```

**解决:**
```bash
# 回滚失败的迁移
alembic downgrade -1

# 修复迁移脚本
vim alembic/versions/xxx_migration.py

# 重新应用
alembic upgrade head
```

---

## 🌍 多环境配置

### 开发环境

```bash
# 使用默认配置
alembic upgrade head
```

### 生产环境

```bash
# 使用生产数据库URL
export DATABASE_URL="postgresql://prod_user:password@prod_host:5432/prod_db"
alembic upgrade head
```

### 测试环境

```bash
# 使用测试数据库
export DATABASE_URL="postgresql://test_user:password@localhost:5432/test_db"
alembic upgrade head
```

---

## 📚 相关资源

- [Alembic官方文档](https://alembic.sqlalchemy.org/)
- [SQLAlchemy文档](https://docs.sqlalchemy.org/)
- [项目数据模型](../src/app/data/models.py)

---

**最后更新:** 2025-11-17

