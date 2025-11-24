-- Migration: Fix foreign key types in related tables
-- Date: 2025-11-20
-- Description: 将所有引用 tenants.id 的外键字段从 UUID 改为 VARCHAR(255)

-- ============================================
-- 修复 knowledge_documents 表
-- ============================================
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'knowledge_documents') THEN
        -- 删除旧的外键约束
        ALTER TABLE knowledge_documents DROP CONSTRAINT IF EXISTS fk_documents_tenant_id;
        ALTER TABLE knowledge_documents DROP CONSTRAINT IF EXISTS knowledge_documents_tenant_id_fkey;
        
        -- 修改 tenant_id 字段类型
        ALTER TABLE knowledge_documents ALTER COLUMN tenant_id TYPE VARCHAR(255);
        
        -- 添加新的外键约束
        ALTER TABLE knowledge_documents 
        ADD CONSTRAINT fk_documents_tenant_id 
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Fixed knowledge_documents.tenant_id type';
    END IF;
END $$;

-- ============================================
-- 修复 data_sources 表
-- ============================================
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'data_sources') THEN
        -- 删除旧的外键约束
        ALTER TABLE data_sources DROP CONSTRAINT IF EXISTS data_sources_tenant_id_fkey;
        
        -- 修改 tenant_id 字段类型
        ALTER TABLE data_sources ALTER COLUMN tenant_id TYPE VARCHAR(255);
        
        -- 添加新的外键约束
        ALTER TABLE data_sources 
        ADD CONSTRAINT fk_data_sources_tenant_id 
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Fixed data_sources.tenant_id type';
    END IF;
END $$;

-- ============================================
-- 修复 users 表
-- ============================================
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
        -- 删除旧的外键约束
        ALTER TABLE users DROP CONSTRAINT IF EXISTS users_tenant_id_fkey;
        
        -- 修改 tenant_id 字段类型
        ALTER TABLE users ALTER COLUMN tenant_id TYPE VARCHAR(255);
        
        -- 添加新的外键约束
        ALTER TABLE users 
        ADD CONSTRAINT fk_users_tenant_id 
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Fixed users.tenant_id type';
    END IF;
END $$;

-- ============================================
-- 修复 api_keys 表
-- ============================================
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'api_keys') THEN
        -- 删除旧的外键约束
        ALTER TABLE api_keys DROP CONSTRAINT IF EXISTS api_keys_tenant_id_fkey;
        
        -- 修改 tenant_id 字段类型
        ALTER TABLE api_keys ALTER COLUMN tenant_id TYPE VARCHAR(255);
        
        -- 添加新的外键约束
        ALTER TABLE api_keys 
        ADD CONSTRAINT fk_api_keys_tenant_id 
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Fixed api_keys.tenant_id type';
    END IF;
END $$;

-- ============================================
-- 修复 audit_logs 表
-- ============================================
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_logs') THEN
        -- 删除旧的外键约束
        ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS audit_logs_tenant_id_fkey;
        
        -- 修改 tenant_id 字段类型
        ALTER TABLE audit_logs ALTER COLUMN tenant_id TYPE VARCHAR(255);
        
        -- 添加新的外键约束
        ALTER TABLE audit_logs 
        ADD CONSTRAINT fk_audit_logs_tenant_id 
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Fixed audit_logs.tenant_id type';
    END IF;
END $$;

-- ============================================
-- 修复 data_source_connections 表（如果还没修复）
-- ============================================
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'data_source_connections' 
        AND column_name = 'tenant_id'
        AND data_type = 'uuid'
    ) THEN
        -- 删除旧的外键约束
        ALTER TABLE data_source_connections DROP CONSTRAINT IF EXISTS fk_data_source_connections_tenant_id;
        ALTER TABLE data_source_connections DROP CONSTRAINT IF EXISTS data_source_connections_tenant_id_fkey;
        
        -- 修改 tenant_id 字段类型
        ALTER TABLE data_source_connections ALTER COLUMN tenant_id TYPE VARCHAR(255);
        
        -- 添加新的外键约束
        ALTER TABLE data_source_connections 
        ADD CONSTRAINT fk_data_source_connections_tenant_id 
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Fixed data_source_connections.tenant_id type';
    END IF;
END $$;

-- ============================================
-- 验证修复结果
-- ============================================
SELECT 
    table_name,
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE column_name = 'tenant_id'
AND table_schema = 'public'
ORDER BY table_name;

