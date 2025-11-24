-- Database initialization script for Data Agent V4
-- Creates basic table structure for multi-tenant SaaS architecture

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create custom types
CREATE TYPE tenant_status AS ENUM ('active', 'inactive', 'suspended');
CREATE TYPE connection_type AS ENUM('api', 'database', 'file', 'webhook');
CREATE TYPE connection_status AS ENUM('active', 'inactive', 'error');
CREATE TYPE document_status AS ENUM('processing', 'completed', 'failed');
CREATE TYPE data_source_type AS ENUM('database', 'api', 'file', 'webhook', 'stream');

-- Tenants table - Multi-tenant core table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    status tenant_status DEFAULT 'active',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Data Source Connections table
CREATE TABLE data_source_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type connection_type NOT NULL,
    status connection_status DEFAULT 'active',
    config JSONB NOT NULL DEFAULT '{}',
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_tested TIMESTAMP WITH TIME ZONE,
    test_result JSONB
);

-- Knowledge Documents table
CREATE TABLE knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES data_source_connections(id) ON DELETE SET NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    file_path VARCHAR(1000),
    file_size BIGINT,
    file_type VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    embedding_id VARCHAR(255), -- Reference to ChromaDB embedding
    status document_status DEFAULT 'processing',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Data Sources table - Extended connection management
CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type data_source_type NOT NULL,
    connection_config JSONB NOT NULL DEFAULT '{}',
    sync_config JSONB DEFAULT '{}',
    status connection_status DEFAULT 'active',
    last_sync_at TIMESTAMP WITH TIME ZONE,
    sync_frequency_minutes INTEGER DEFAULT 60,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Users table - Basic user management
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- API Keys table - For external integrations
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    key_prefix VARCHAR(20) NOT NULL,
    permissions JSONB DEFAULT '{}',
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

-- Audit Logs table - For compliance and debugging
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_status ON tenants(status);
CREATE INDEX idx_data_source_connections_tenant_id ON data_source_connections(tenant_id);
CREATE INDEX idx_data_source_connections_type ON data_source_connections(type);
CREATE INDEX idx_knowledge_documents_tenant_id ON knowledge_documents(tenant_id);
CREATE INDEX idx_knowledge_documents_connection_id ON knowledge_documents(connection_id);
CREATE INDEX idx_knowledge_documents_status ON knowledge_documents(status);
CREATE INDEX idx_data_sources_tenant_id ON data_sources(tenant_id);
CREATE INDEX idx_data_sources_type ON data_sources(type);
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_api_keys_tenant_id ON api_keys(tenant_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_data_source_connections_updated_at BEFORE UPDATE ON data_source_connections FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_knowledge_documents_updated_at BEFORE UPDATE ON knowledge_documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_data_sources_updated_at BEFORE UPDATE ON data_sources FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default tenant
INSERT INTO tenants (name, slug, description, status)
VALUES ('Default Tenant', 'default', 'Default tenant for initial setup', 'active');

-- Insert default admin user (password: admin123 - should be changed in production)
INSERT INTO users (tenant_id, email, password_hash, first_name, last_name, is_admin)
SELECT
    id,
    'admin@dataagent.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNjrKK9H9Q7qO', -- admin123
    'Admin',
    'User',
    true
FROM tenants
WHERE slug = 'default';

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Create views for easier querying
CREATE VIEW active_tenants AS
SELECT * FROM tenants WHERE status = 'active';

CREATE VIEW tenant_connections AS
SELECT
    t.id as tenant_id,
    t.name as tenant_name,
    dsc.id as connection_id,
    dsc.name as connection_name,
    dsc.type as connection_type,
    dsc.status as connection_status
FROM tenants t
LEFT JOIN data_source_connections dsc ON t.id = dsc.tenant_id
WHERE t.status = 'active';

CREATE VIEW tenant_document_stats AS
SELECT
    t.id as tenant_id,
    t.name as tenant_name,
    COUNT(kd.id) as total_documents,
    COUNT(CASE WHEN kd.status = 'completed' THEN 1 END) as completed_documents,
    COUNT(CASE WHEN kd.status = 'processing' THEN 1 END) as processing_documents,
    COUNT(CASE WHEN kd.status = 'failed' THEN 1 END) as failed_documents
FROM tenants t
LEFT JOIN knowledge_documents kd ON t.id = kd.tenant_id
WHERE t.status = 'active'
GROUP BY t.id, t.name;