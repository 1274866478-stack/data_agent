"""Add SQLErrorMemory model for SQL Error Learning System

Revision ID: 008_add_sql_error_memory
Revises: 007_migrate_data_source_connections
Create Date: 2026-01-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008_add_sql_error_memory'
down_revision: Union[str, None] = '007_migrate_data_source_connections'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sql_error_memory table and related enum for SQL Error Learning System"""

    # Create sql_error_type enum
    sql_error_type_enum = postgresql.ENUM(
        'column_not_exist',
        'table_not_exist',
        'syntax_error',
        'ambiguous_column',
        'type_mismatch',
        'relation_error',
        'aggregate_error',
        'group_by_error',
        'other',
        name='sqlerrortype',
        create_type=True
    )
    sql_error_type_enum.create(op.get_bind())

    # Create sql_error_memory table
    op.create_table('sql_error_memory',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=False),
        sa.Column('error_pattern_hash', sa.String(length=64), nullable=False),
        sa.Column('error_type', sql_error_type_enum, nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('original_query', sa.Text(), nullable=False),
        sa.Column('fixed_query', sa.Text(), nullable=False),
        sa.Column('fix_description', sa.Text(), nullable=True),
        sa.Column('table_name', sa.String(length=100), nullable=True),
        sa.Column('schema_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('occurrence_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('last_occurrence', sa.DateTime(timezone=True), nullable=True),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index(op.f('ix_sql_error_memory_id'), 'sql_error_memory', ['id'], unique=False)
    op.create_index(op.f('ix_sql_error_memory_tenant_id'), 'sql_error_memory', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_sql_error_memory_error_pattern_hash'), 'sql_error_memory', ['error_pattern_hash'], unique=True)
    op.create_index(op.f('ix_sql_error_memory_error_type'), 'sql_error_memory', ['error_type'], unique=False)
    op.create_index(op.f('ix_sql_error_memory_table_name'), 'sql_error_memory', ['table_name'], unique=False)

    # Composite index for tenant + table queries (common use case)
    op.create_index('ix_sql_error_memory_tenant_table', 'sql_error_memory', ['tenant_id', 'table_name'], unique=False)


def downgrade() -> None:
    """Drop sql_error_memory table and related enum"""

    # Drop indexes
    op.drop_index('ix_sql_error_memory_tenant_table', table_name='sql_error_memory')
    op.drop_index(op.f('ix_sql_error_memory_table_name'), table_name='sql_error_memory')
    op.drop_index(op.f('ix_sql_error_memory_error_type'), table_name='sql_error_memory')
    op.drop_index(op.f('ix_sql_error_memory_error_pattern_hash'), table_name='sql_error_memory')
    op.drop_index(op.f('ix_sql_error_memory_tenant_id'), table_name='sql_error_memory')
    op.drop_index(op.f('ix_sql_error_memory_id'), table_name='sql_error_memory')

    # Drop table
    op.drop_table('sql_error_memory')

    # Drop enum
    sa.Enum(name='sqlerrortype').drop(op.get_bind())
