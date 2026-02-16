"""Add QueryLog model for Story 3.1

Revision ID: 005_add_query_log_model
Revises: 004_optimize_query_performance
Create Date: 2024-11-17 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_add_query_log_model'
down_revision: Union[str, None] = '004_optimize_query_performance'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create query_logs table and related enums for Story 3.1"""

    # Create query_status enum
    query_status_enum = postgresql.ENUM(
        'pending', 'processing', 'success', 'error', 'timeout',
        name='querystatus'
    )
    query_status_enum.create(op.get_bind())

    # Create query_type enum
    query_type_enum = postgresql.ENUM(
        'sql', 'document', 'mixed',
        name='querytype'
    )
    query_type_enum.create(op.get_bind())

    # Create query_logs table
    op.create_table('query_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('query_type', query_type_enum, nullable=False),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('response_summary', sa.Text(), nullable=True),
        sa.Column('response_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('explainability_log', sa.Text(), nullable=True),
        sa.Column('query_hash', sa.String(length=64), nullable=True),
        sa.Column('cache_hit', sa.Boolean(), nullable=False, default=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('status', query_status_enum, nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance (Story requirements)
    op.create_index(op.f('ix_query_logs_id'), 'query_logs', ['id'], unique=False)
    op.create_index(op.f('ix_query_logs_tenant_id'), 'query_logs', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_query_logs_user_id'), 'query_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_query_logs_query_type'), 'query_logs', ['query_type'], unique=False)
    op.create_index(op.f('ix_query_logs_status'), 'query_logs', ['status'], unique=False)
    op.create_index(op.f('ix_query_logs_query_hash'), 'query_logs', ['query_hash'], unique=False)
    op.create_index('ix_query_logs_tenant_status_created', 'query_logs', ['tenant_id', 'status', 'created_at'], unique=False)


def downgrade() -> None:
    """Drop query_logs table and related enums"""

    # Drop indexes
    op.drop_index('ix_query_logs_tenant_status_created', table_name='query_logs')
    op.drop_index(op.f('ix_query_logs_query_hash'), table_name='query_logs')
    op.drop_index(op.f('ix_query_logs_status'), table_name='query_logs')
    op.drop_index(op.f('ix_query_logs_query_type'), table_name='query_logs')
    op.drop_index(op.f('ix_query_logs_user_id'), table_name='query_logs')
    op.drop_index(op.f('ix_query_logs_tenant_id'), table_name='query_logs')
    op.drop_index(op.f('ix_query_logs_id'), table_name='query_logs')

    # Drop table
    op.drop_table('query_logs')

    # Drop enums
    sa.Enum(name='querystatus').drop(op.get_bind())
    sa.Enum(name='querytype').drop(op.get_bind())