-- Migration: Fix tenants table schema to match SQLAlchemy model
-- Date: 2025-11-20
-- Description: 修复 tenants 表结构，使其与 models.py 中的 Tenant 模型定义一致
--              主要变更：
--              1. 将 id 从 UUID 改为 VARCHAR(255) (支持 Clerk user_id)
--              2. 添加 email 字段 (必需，唯一)
--              3. 将 name 改为 display_name (可选)
--              4. 移除 slug 和 description 字段
--              5. 添加 storage_quota_mb 字段

-- ============================================
-- 第一步：备份现有数据
-- ============================================
CREATE TABLE IF NOT EXISTS tenants_backup AS 
SELECT * FROM tenants;

-- ============================================
-- 第二步：创建新的 tenants 表结构
-- ============================================
DROP TABLE IF EXISTS tenants CASCADE;

-- 重新创建 tenant_status 枚举类型（如果需要）
DO $$ BEGIN
    CREATE TYPE tenant_status AS ENUM ('active', 'suspended', 'deleted');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE tenants (
    -- 租户唯一标识符（来自认证服务，如 Clerk）
    id VARCHAR(255) PRIMARY KEY,
    
    -- 租户邮箱（必需，唯一）
    email VARCHAR(255) NOT NULL UNIQUE,
    
    -- 租户状态管理
    status tenant_status DEFAULT 'active' NOT NULL,
    
    -- 租户基本信息
    display_name VARCHAR(255),
    
    -- 租户特定设置（JSONB）
    settings JSONB DEFAULT '{}'::jsonb,
    
    -- 存储配额（MB）
    storage_quota_mb INTEGER DEFAULT 1024 NOT NULL,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================
-- 第三步：创建索引
-- ============================================
CREATE INDEX idx_tenants_email ON tenants(email);
CREATE INDEX idx_tenants_status ON tenants(status);

-- ============================================
-- 第四步：迁移现有数据（如果有）
-- ============================================
-- 从备份表迁移数据，将 UUID 转换为字符串，name 映射到 display_name
INSERT INTO tenants (id, email, status, display_name, settings, storage_quota_mb, created_at, updated_at)
SELECT 
    id::text,  -- UUID 转换为字符串
    COALESCE(
        -- 尝试从 settings 中提取 email，如果没有则生成一个
        (settings->>'email')::text,
        'tenant_' || id::text || '@dataagent.local'
    ) as email,
    status,
    name as display_name,
    settings,
    1024 as storage_quota_mb,  -- 默认 1GB
    created_at,
    updated_at
FROM tenants_backup
WHERE EXISTS (SELECT 1 FROM tenants_backup)
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 第五步：重新创建触发器
-- ============================================
-- 创建或替换 updated_at 自动更新函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 创建触发器
DROP TRIGGER IF EXISTS update_tenants_updated_at ON tenants;
CREATE TRIGGER update_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 第六步：重新创建外键约束
-- ============================================
-- 注意：需要先修复其他表的外键引用

-- 修复 data_source_connections 表的外键
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'data_source_connections') THEN
        -- 删除旧的外键约束（如果存在）
        ALTER TABLE data_source_connections DROP CONSTRAINT IF EXISTS fk_data_source_connections_tenant_id;
        ALTER TABLE data_source_connections DROP CONSTRAINT IF EXISTS data_source_connections_tenant_id_fkey;
        
        -- 添加新的外键约束
        ALTER TABLE data_source_connections 
        ADD CONSTRAINT fk_data_source_connections_tenant_id 
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
    END IF;
END $$;

-- 修复 knowledge_documents 表的外键
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'knowledge_documents') THEN
        -- 删除旧的外键约束（如果存在）
        ALTER TABLE knowledge_documents DROP CONSTRAINT IF EXISTS fk_documents_tenant_id;
        ALTER TABLE knowledge_documents DROP CONSTRAINT IF EXISTS knowledge_documents_tenant_id_fkey;
        
        -- 添加新的外键约束
        ALTER TABLE knowledge_documents 
        ADD CONSTRAINT fk_documents_tenant_id 
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
    END IF;
END $$;

-- ============================================
-- 第七步：创建默认租户（用于测试）
-- ============================================
INSERT INTO tenants (id, email, status, display_name, settings, storage_quota_mb)
VALUES (
    'default_tenant',
    'admin@dataagent.local',
    'active',
    'Default Tenant',
    '{"timezone": "UTC", "language": "zh-CN"}'::jsonb,
    1024
)
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 验证迁移结果
-- ============================================
-- 显示新表结构
\d tenants

-- 显示迁移的数据
SELECT id, email, status, display_name, storage_quota_mb, created_at 
FROM tenants 
LIMIT 5;

-- 显示统计信息
SELECT 
    COUNT(*) as total_tenants,
    COUNT(DISTINCT email) as unique_emails,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_tenants
FROM tenants;

