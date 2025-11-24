-- Migration script to update data_source_connections table structure
-- This aligns the database schema with the DataSourceConnection model in models.py

-- Step 1: Backup existing data (if any)
CREATE TABLE IF NOT EXISTS data_source_connections_backup AS 
SELECT * FROM data_source_connections;

-- Step 2: Drop the old table (since it's likely empty in development)
DROP TABLE IF EXISTS data_source_connections CASCADE;

-- Step 3: Create the new table structure matching the model
CREATE TABLE data_source_connections (
    id VARCHAR(255) PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    db_type VARCHAR(50) NOT NULL DEFAULT 'postgresql',
    _connection_string TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'testing',
    last_tested_at TIMESTAMP WITH TIME ZONE,
    test_result JSONB,
    host VARCHAR(255),
    port INTEGER,
    database_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Step 4: Create indexes
CREATE INDEX idx_data_source_connections_tenant_id ON data_source_connections(tenant_id);
CREATE INDEX idx_data_source_connections_status ON data_source_connections(status);
CREATE INDEX idx_data_source_connections_db_type ON data_source_connections(db_type);

-- Step 5: Add foreign key constraint (if tenants table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'tenants') THEN
        ALTER TABLE data_source_connections 
        ADD CONSTRAINT fk_data_source_connections_tenant_id 
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Step 6: Create trigger for updated_at
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

-- Step 7: Migrate data from backup (if needed)
-- Note: This requires manual mapping since the schema changed significantly
-- INSERT INTO data_source_connections (id, tenant_id, name, db_type, ...)
-- SELECT id::text, tenant_id::text, name, 'postgresql', ...
-- FROM data_source_connections_backup;

-- Step 8: Verify the new structure
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'data_source_connections'
ORDER BY ordinal_position;

COMMENT ON TABLE data_source_connections IS 'Stores encrypted database connection strings for tenant data sources';
COMMENT ON COLUMN data_source_connections._connection_string IS 'Encrypted connection string - use model property to access decrypted value';
COMMENT ON COLUMN data_source_connections.status IS 'Connection status: active, inactive, error, testing';

