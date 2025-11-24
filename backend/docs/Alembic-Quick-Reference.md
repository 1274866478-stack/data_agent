# Alembic 快速参考

## 🚀 常用命令速查

### 查看状态
```bash
alembic current              # 查看当前版本
alembic history              # 查看迁移历史
alembic history --verbose    # 详细历史
alembic heads                # 查看所有head版本
alembic show head            # 查看最新版本详情
```

### 创建迁移
```bash
# 自动生成迁移 (推荐)
alembic revision --autogenerate -m "描述性消息"

# 手动创建空迁移
alembic revision -m "描述性消息"

# 合并多个head
alembic merge -m "merge heads" head1 head2
```

### 应用迁移
```bash
alembic upgrade head         # 升级到最新版本
alembic upgrade +1           # 升级一个版本
alembic upgrade abc123       # 升级到特定版本
alembic upgrade abc123:head  # 从abc123升级到最新
```

### 回滚迁移
```bash
alembic downgrade -1         # 回滚一个版本
alembic downgrade abc123     # 回滚到特定版本
alembic downgrade base       # 回滚所有迁移
```

### 其他操作
```bash
alembic stamp head           # 标记数据库版本(不执行SQL)
alembic stamp abc123         # 标记为特定版本
alembic branches             # 查看分支
```

---

## 📝 迁移脚本模板

### 基础模板
```python
"""描述性消息

Revision ID: abc123
Revises: def456
Create Date: 2025-01-15 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'abc123'
down_revision = 'def456'
branch_labels = None
depends_on = None

def upgrade():
    # 升级逻辑
    pass

def downgrade():
    # 降级逻辑
    pass
```

### 添加列
```python
def upgrade():
    op.add_column('table_name', 
        sa.Column('column_name', sa.String(100), nullable=True)
    )

def downgrade():
    op.drop_column('table_name', 'column_name')
```

### 修改列
```python
def upgrade():
    op.alter_column('table_name', 'column_name',
        type_=sa.String(200),
        nullable=False,
        server_default='default_value'
    )

def downgrade():
    op.alter_column('table_name', 'column_name',
        type_=sa.String(100),
        nullable=True,
        server_default=None
    )
```

### 创建表
```python
def upgrade():
    op.create_table(
        'new_table',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )

def downgrade():
    op.drop_table('new_table')
```

### 创建索引
```python
def upgrade():
    op.create_index('ix_table_column', 'table_name', ['column_name'])

def downgrade():
    op.drop_index('ix_table_column', table_name='table_name')
```

### 数据迁移
```python
def upgrade():
    # 使用SQL
    op.execute("""
        UPDATE table_name 
        SET status = 'active' 
        WHERE status IS NULL
    """)
    
    # 或使用SQLAlchemy
    from sqlalchemy import table, column
    from sqlalchemy.sql import select
    
    t = table('table_name',
        column('id', sa.Integer),
        column('status', sa.String)
    )
    
    op.execute(
        t.update().where(t.c.status == None).values(status='active')
    )

def downgrade():
    op.execute("""
        UPDATE table_name 
        SET status = NULL 
        WHERE status = 'active'
    """)
```

---

## ⚠️ 常见陷阱

### 1. 忘记实现downgrade
```python
# ❌ 错误
def downgrade():
    pass  # 没有实现回滚逻辑

# ✅ 正确
def downgrade():
    op.drop_column('table_name', 'new_column')
```

### 2. 数据迁移不可逆
```python
# ❌ 错误 - 数据删除无法恢复
def upgrade():
    op.execute("DELETE FROM old_table")

def downgrade():
    pass  # 无法恢复删除的数据

# ✅ 正确 - 先备份再删除
def upgrade():
    # 备份数据
    op.execute("""
        INSERT INTO old_table_backup 
        SELECT * FROM old_table
    """)
    # 删除数据
    op.execute("DELETE FROM old_table")

def downgrade():
    # 恢复数据
    op.execute("""
        INSERT INTO old_table 
        SELECT * FROM old_table_backup
    """)
```

### 3. 忽略NULL约束
```python
# ❌ 错误 - 直接添加NOT NULL列
def upgrade():
    op.add_column('table_name',
        sa.Column('new_column', sa.String(100), nullable=False)
    )  # 如果表有数据会失败

# ✅ 正确 - 分步骤添加
def upgrade():
    # 1. 添加可空列
    op.add_column('table_name',
        sa.Column('new_column', sa.String(100), nullable=True)
    )
    # 2. 填充默认值
    op.execute("UPDATE table_name SET new_column = 'default'")
    # 3. 设置为NOT NULL
    op.alter_column('table_name', 'new_column', nullable=False)
```

---

## 🔍 调试技巧

### 查看将要执行的SQL
```bash
alembic upgrade head --sql > migration.sql
cat migration.sql
```

### 测试迁移
```bash
# 1. 应用迁移
alembic upgrade head

# 2. 回滚
alembic downgrade -1

# 3. 重新应用
alembic upgrade head

# 4. 验证数据
psql -d database_name -c "SELECT * FROM table_name LIMIT 5"
```

---

## 📋 检查清单

创建迁移前:
- [ ] 修改了models.py
- [ ] 运行了代码格式化
- [ ] 测试了模型变更

创建迁移后:
- [ ] 审查了生成的迁移脚本
- [ ] 实现了downgrade函数
- [ ] 测试了upgrade和downgrade
- [ ] 添加了描述性的commit message

应用到生产前:
- [ ] 在开发环境测试
- [ ] 在测试环境验证
- [ ] 备份生产数据库
- [ ] 准备回滚计划

---

**最后更新:** 2025-11-17

