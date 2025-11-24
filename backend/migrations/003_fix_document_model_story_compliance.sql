-- KnowledgeDocument模型重构迁移脚本
-- Story 2.4 - 文档上传和管理
-- 将模型从旧结构迁移到符合Story规范的新结构
--
-- 变更内容：
-- 1. 主键从Integer改为UUID
-- 2. 字段重命名：file_path -> storage_path, processing_status -> status
-- 3. 状态枚举改为Story规范：PENDING, INDEXING, READY, ERROR
-- 4. 添加缺失字段：indexed_at
-- 5. 字段类型调整：file_size改为BIGINT
-- 6. 移除不需要的字段：title, vectorized, vector_count, chroma_collection, doc_metadata, uploaded_at, processed_at

BEGIN;

-- 创建新的knowledge_documents表结构（符合Story规范）
CREATE TABLE knowledge_documents_new (
    -- Story规范: UUID主键
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Story规范: 租户ID外键
    tenant_id VARCHAR(255) NOT NULL,

    -- Story规范: 文件基本信息
    file_name VARCHAR(500) NOT NULL,
    storage_path VARCHAR(1000) NOT NULL,

    -- Story规范: 文件类型和大小
    file_type VARCHAR(10) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,

    -- Story规范: 状态枚举
    status VARCHAR(20) DEFAULT 'PENDING' NOT NULL,
    processing_error TEXT,

    -- Story规范: 索引时间
    indexed_at TIMESTAMP WITH TIME ZONE,

    -- 时间戳 (Story规范)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 创建索引（Story规范要求的索引）
CREATE INDEX idx_documents_new_tenant_id ON knowledge_documents_new(tenant_id);
CREATE INDEX idx_documents_new_status ON knowledge_documents_new(status);
CREATE INDEX idx_documents_new_created_at ON knowledge_documents_new(created_at);

-- 迁移现有数据
-- 从旧表结构映射到新表结构
INSERT INTO knowledge_documents_new (
    id,
    tenant_id,
    file_name,
    storage_path,
    file_type,
    file_size,
    mime_type,
    status,
    processing_error,
    indexed_at,
    created_at,
    updated_at
)
SELECT
    -- 生成新的UUID主键
    gen_random_uuid() as id,

    -- 保持原有字段
    tenant_id,
    COALESCE(file_name, 'unknown_document.pdf') as file_name,
    file_path as storage_path,  -- 重命名字段

    -- 文件类型处理
    CASE
        WHEN LOWER(file_type) = 'pdf' THEN 'pdf'
        WHEN LOWER(file_type) LIKE '%docx%' OR LOWER(file_type) LIKE '%doc%' THEN 'docx'
        WHEN LOWER(file_type) = 'txt' THEN 'txt'
        ELSE 'unknown'
    END as file_type,

    file_size::BIGINT,  -- 转换为BIGINT
    COALESCE(mime_type, 'application/octet-stream') as mime_type,

    -- 状态枚举转换
    CASE
        WHEN LOWER(processing_status) = 'pending' THEN 'PENDING'
        WHEN LOWER(processing_status) = 'processing' THEN 'INDEXING'
        WHEN LOWER(processing_status) = 'completed' THEN 'READY'
        WHEN LOWER(processing_status) = 'failed' THEN 'ERROR'
        ELSE 'PENDING'
    END as status,

    processing_error,

    -- indexed_at字段处理
    CASE
        WHEN LOWER(processing_status) = 'completed' THEN processed_at
        ELSE NULL
    END as indexed_at,

    -- 时间戳字段映射
    created_at,
    updated_at
FROM knowledge_documents;

-- 更新updated_at为当前时间
UPDATE knowledge_documents_new SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL;

-- 创建外键约束（如果不存在租户表的话先添加检查）
ALTER TABLE knowledge_documents_new
ADD CONSTRAINT fk_documents_tenant_id
FOREIGN KEY (tenant_id) REFERENCES tenants(id);

-- 备份旧表
ALTER TABLE knowledge_documents RENAME TO knowledge_documents_backup;

-- 将新表重命名为正式表
ALTER TABLE knowledge_documents_new RENAME TO knowledge_documents;

-- 创建更新时间戳触发器（PostgreSQL）
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_knowledge_documents_updated_at
    BEFORE UPDATE ON knowledge_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMIT;

-- 验证迁移结果
DO $$
DECLARE
    old_count INTEGER;
    new_count INTEGER;
BEGIN
    -- 统计旧表记录数
    SELECT COUNT(*) INTO old_count FROM knowledge_documents_backup;

    -- 统计新表记录数
    SELECT COUNT(*) INTO new_count FROM knowledge_documents;

    -- 输出迁移统计信息
    RAISE NOTICE '迁移完成统计:';
    RAISE NOTICE '旧表记录数: %', old_count;
    RAISE NOTICE '新表记录数: %', new_count;
    RAISE NOTICE '迁移成功率: %%%', CASE WHEN old_count > 0 THEN (new_count::FLOAT / old_count::FLOAT * 100) ELSE 100 END;

    -- 检查数据完整性
    IF old_count != new_count THEN
        RAISE EXCEPTION '数据迁移不完整！旧表有%条记录，新表只有%条记录', old_count, new_count;
    END IF;
END $$;

-- 添加约束确保status枚举值正确（可选的检查约束）
ALTER TABLE knowledge_documents
ADD CONSTRAINT chk_document_status
CHECK (status IN ('PENDING', 'INDEXING', 'READY', 'ERROR'));

-- 添加约束确保file_type格式正确
ALTER TABLE knowledge_documents
ADD CONSTRAINT chk_file_type
CHECK (file_type IN ('pdf', 'docx', 'txt', 'unknown'));

-- 输出表结构信息
\d knowledge_documents;

-- 迁移成功提示
SELECT 'KnowledgeDocument表迁移完成！新结构完全符合Story 2.4规范。' AS migration_result;

-- 回滚脚本（如果需要回滚，请执行以下脚本）
/*
BEGIN;

DROP TABLE knowledge_documents;
ALTER TABLE knowledge_documents_backup RENAME TO knowledge_documents;

COMMIT;

SELECT '已回滚到迁移前的状态。' AS rollback_result;
*/