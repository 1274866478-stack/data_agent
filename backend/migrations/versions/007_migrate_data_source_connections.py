"""Migrate data_source_connections table to match SQLAlchemy model

Revision ID: 007_migrate_data_source_connections
Revises: 006_fix_foreign_key_types
Create Date: 2025-12-01 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007_migrate_data_source_connections'
down_revision: Union[str, None] = '006_fix_foreign_key_types'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate data_source_connections table structure to match SQLAlchemy model"""

    # Step 1: Create backup of existing data (if table exists)
    connection = op.get_bind()
    if connection.dialect.has_table(connection, 'data_source_connections'):
        op.execute("CREATE TABLE IF NOT EXISTS data_source_connections_backup AS SELECT * FROM data_source_connections")

        # Step 2: Drop existing table and recreate with correct structure
        op.drop_table('data_source_connections', cascade=True)

    # Step 3: Create DataSourceConnectionStatus enum
    connection_status_enum = postgresql.ENUM(
        'active', 'inactive', 'error', 'testing',
        name='dataconnectionstatus'
    )
    connection_status_enum.create(op.get_bind())

    # Step 4: Create the new table structure matching the model
    op.create_table('data_source_connections',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('db_type', sa.String(length=50), nullable=False, server_default=sa.text("'postgresql'")),
        sa.Column('_connection_string', sa.Text(), nullable=False),
        sa.Column('status', connection_status_enum, nullable=False, server_default=sa.text("'testing'::dataconnectionstatus")),
        sa.Column('last_tested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('test_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('host', sa.String(length=255), nullable=True),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('database_name', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Step 5: Create indexes
    op.create_index(op.f('ix_data_source_connections_tenant_id'), 'data_source_connections', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_data_source_connections_status'), 'data_source_connections', ['status'], unique=False)
    op.create_index(op.f('ix_data_source_connections_db_type'), 'data_source_connections', ['db_type'], unique=False)

    # Step 6: Add foreign key constraint (if tenants table exists)
    op.create_foreign_key(
        'fk_data_source_connections_tenant_id',
        'data_source_connections',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Step 7: Create trigger for updated_at (PostgreSQL specific)
    op.execute("""
        CREATE OR REPLACE FUNCTION update_data_source_connections_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trigger_update_data_source_connections_updated_at
            BEFORE UPDATE ON data_source_connections
            FOR EACH ROW
            EXECUTE FUNCTION update_data_source_connections_updated_at();
    """)

    # Step 8: Add table comments
    op.execute("COMMENT ON TABLE data_source_connections IS 'Stores encrypted database connection strings for tenant data sources'")
    op.execute("COMMENT ON COLUMN data_source_connections._connection_string IS 'Encrypted connection string - use model property to access decrypted value'")
    op.execute("COMMENT ON COLUMN data_source_connections.status IS 'Connection status: active, inactive, error, testing'")


def downgrade() -> None:
    """Downgrade migration - restore previous table structure"""

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS trigger_update_data_source_connections_updated_at ON data_source_connections")
    op.execute("DROP FUNCTION IF EXISTS update_data_source_connections_updated_at()")

    # Drop table
    op.drop_table('data_source_connections')

    # Drop enum
    connection_status_enum = postgresql.ENUM(name='dataconnectionstatus')
    connection_status_enum.drop(op.get_bind())

    # Restore backup if it exists
    connection = op.get_bind()
    if connection.dialect.has_table(connection, 'data_source_connections_backup'):
        op.execute("ALTER TABLE data_source_connections_backup RENAME TO data_source_connections")

        # Note: This will restore the old structure, but indexes and constraints
        # from the old version would need to be recreated manually if needed