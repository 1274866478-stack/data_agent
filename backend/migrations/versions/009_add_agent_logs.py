# -*- coding: utf-8 -*-
"""
Add Agent Logs Table Migration

创建 agent_logs 表用于持久化 Agent V2 执行日志。

支持:
    - 完整的审计级别日志记录
    - 租户隔离
    - 会话追踪
    - 步骤级别记录

作者: BMad Master
版本: 1.0.0
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers
revision = '009_add_agent_logs'
down_revision = '008_add_sql_error_memory'
branch_labels = None
depends_on = None


def upgrade():
    """
    创建 agent_logs 表及相关索引
    """
    # 创建 agent_logs 表
    op.create_table(
        'agent_logs',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        sa.Column('session_id', sa.String(255), nullable=False, index=True),
        sa.Column('user_id', sa.String(255), nullable=True, index=True),
        sa.Column('step_number', sa.Integer(), nullable=True),
        sa.Column('node_name', sa.String(100), nullable=True, index=True),
        sa.Column('message_type', sa.String(50), nullable=False, index=True),
        sa.Column('content', JSONB(), nullable=True),
        sa.Column('raw_message', sa.Text(), nullable=True),
        sa.Column('metadata', JSONB(), nullable=True),  # 数据库列名为 metadata
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=False),

        # 复合索引
        sa.Index('idx_agent_logs_tenant_session', 'tenant_id', 'session_id'),
        sa.Index('idx_agent_logs_created_at', 'created_at'),
        sa.Index('idx_agent_logs_session_step', 'session_id', 'step_number'),
    )

    print("[Migration] agent_logs table created successfully")


def downgrade():
    """
    删除 agent_logs 表
    """
    op.drop_table('agent_logs')
    print("[Migration] agent_logs 表已删除")
