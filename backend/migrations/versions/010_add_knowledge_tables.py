# -*- coding: utf-8 -*-
"""
Add Knowledge System Tables Migration

创建知识系统相关表，支持双知识系统功能：
    - validated_queries: 验证通过的查询模板（静态知识库）
    - query_learnings: 错误学习记录（动态学习库）

支持:
    - 查询模板持久化存储
    - 错误修复方案记录
    - 租户隔离
    - 使用统计和成功率跟踪

作者: Data Agent Team
版本: 1.0.0
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers
revision = '010_add_knowledge_tables'
down_revision = '009_add_agent_logs'
branch_labels = None
depends_on = None


def upgrade():
    """
    创建知识系统相关表
    """
    # ========================================
    # 1. 创建 validated_queries 表
    # ========================================
    op.create_table(
        'validated_queries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('sql', sa.Text(), nullable=False),
        sa.Column('tables', JSONB(), nullable=True),  # 涉及的表名列表
        sa.Column('answer', sa.Text(), nullable=True),  # 答案描述
        sa.Column('knowledge_type', sa.String(50), nullable=False, default='query_template', index=True),
        sa.Column('metadata', JSONB(), nullable=True),  # 额外元数据
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('success_rate', sa.Float(), nullable=False, default=1.0),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=False),

        # 索引
        sa.Index('idx_validated_queries_tenant_question', 'tenant_id', 'question'),
        sa.Index('idx_validated_queries_type', 'knowledge_type'),
        sa.Index('idx_validated_queries_created_at', 'created_at'),
        sa.Index('idx_validated_queries_usage_count', 'usage_count'),
    )

    print("[Migration] validated_queries table created successfully")

    # ========================================
    # 2. 创建 query_learnings 表
    # ========================================
    op.create_table(
        'query_learnings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        sa.Column('error_category', sa.String(50), nullable=False, index=True),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('fix_suggestion', sa.Text(), nullable=True),
        sa.Column('corrected_sql', sa.Text(), nullable=True),
        sa.Column('original_query', sa.Text(), nullable=True),
        sa.Column('metadata', JSONB(), nullable=True),  # 额外元数据
        sa.Column('applied_count', sa.Integer(), nullable=False, default=0),
        sa.Column('success_rate', sa.Float(), nullable=False, default=0.0),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('last_applied_at', sa.TIMESTAMP(), nullable=True),

        # 索引
        sa.Index('idx_query_learnings_tenant_error', 'tenant_id', 'error_category'),
        sa.Index('idx_query_learnings_created_at', 'created_at'),
        sa.Index('idx_query_learnings_success_rate', 'success_rate'),
    )

    print("[Migration] query_learnings table created successfully")

    # ========================================
    # 3. 扩展 agent_logs 表（添加知识引用字段）
    # ========================================
    # 检查列是否存在，如果不存在则添加
    try:
        op.add_column(
            'agent_logs',
            sa.Column('knowledge_references', JSONB(), nullable=True)
        )
        print("[Migration] agent_logs.knowledge_references column added successfully")
    except Exception as e:
        # 列可能已存在，跳过
        print(f"[Migration] Skipping knowledge_references column: {e}")

    try:
        op.add_column(
            'agent_logs',
            sa.Column('learning_applied', UUID(as_uuid=True), nullable=True)
        )
        print("[Migration] agent_logs.learning_applied column added successfully")
    except Exception as e:
        # 列可能已存在，跳过
        print(f"[Migration] Skipping learning_applied column: {e}")

    print("[Migration] Knowledge system tables upgrade completed successfully")


def downgrade():
    """
    删除知识系统相关表
    """
    # 删除 agent_logs 扩展列
    try:
        op.drop_column('agent_logs', 'learning_applied')
        print("[Migration] agent_logs.learning_applied column dropped")
    except Exception:
        pass

    try:
        op.drop_column('agent_logs', 'knowledge_references')
        print("[Migration] agent_logs.knowledge_references column dropped")
    except Exception:
        pass

    # 删除 query_learnings 表
    op.drop_table('query_learnings')
    print("[Migration] query_learnings 表已删除")

    # 删除 validated_queries 表
    op.drop_table('validated_queries')
    print("[Migration] validated_queries 表已删除")

    print("[Migration] Knowledge system tables downgrade completed")
