# -*- coding: utf-8 -*-
"""
Add Users Table for Self-Hosted Authentication Migration

创建用户表以支持自托管认证模式：
    - users: 用户账户表
    - 支持密码哈希存储
    - 一对一关联租户
    - 账户状态管理

支持:
    - 自托管 JWT 认证
    - 用户注册/登录
    - 租户隔离

作者: Data Agent Team
版本: 1.0.0
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = '011_add_users_table'
down_revision = '010_add_knowledge_tables'
branch_labels = None
depends_on = None


def upgrade():
    """
    创建用户表
    """
    # ========================================
    # 1. 创建 users 表
    # ========================================
    op.create_table(
        'users',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('tenant_id', sa.String(255), sa.ForeignKey('tenants.id'), nullable=False, unique=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('last_login_at', sa.TIMESTAMP(), nullable=True),

        # 索引
        sa.Index('idx_users_email', 'email'),
        sa.Index('idx_users_tenant_id', 'tenant_id'),
        sa.Index('idx_users_is_active', 'is_active'),
    )

    print("[Migration] users table created successfully")

    # ========================================
    # 2. 添加租户-用户关系注释
    # ========================================
    op.execute("""
        COMMENT ON TABLE users IS '用户表 - 支持自托管认证';
        COMMENT ON COLUMN users.id IS '用户唯一标识符 (UUID)';
        COMMENT ON COLUMN users.email IS '用户邮箱（登录用）';
        COMMENT ON COLUMN users.password_hash IS 'bcrypt 密码哈希';
        COMMENT ON COLUMN users.tenant_id IS '关联的租户 ID（一对一关系）';
        COMMENT ON COLUMN users.is_active IS '账户是否激活';
        COMMENT ON COLUMN users.created_at IS '创建时间';
        COMMENT ON COLUMN users.updated_at IS '更新时间';
        COMMENT ON COLUMN users.last_login_at IS '最后登录时间';
    """)

    print("[Migration] Users table upgrade completed successfully")


def downgrade():
    """
    删除用户表
    """
    op.drop_table('users')
    print("[Migration] users 表已删除")

    print("[Migration] Users table downgrade completed")
