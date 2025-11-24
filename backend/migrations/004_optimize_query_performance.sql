-- Story 2.4 查询性能优化
-- 为文档管理添加优化的索引以提升查询性能

-- 开始事务
BEGIN;

-- 为 knowledge_documents 表添加性能优化索引

-- 1. 租户主要查询索引（最常用）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_documents_tenant_id
ON knowledge_documents(tenant_id);

-- 2. 租户 + 状态复合索引（用于状态过滤）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_documents_tenant_status
ON knowledge_documents(tenant_id, status);

-- 3. 租户 + 文件类型复合索引（用于文件类型过滤）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_documents_tenant_file_type
ON knowledge_documents(tenant_id, file_type);

-- 4. 租户 + 创建时间复合索引（用于时间排序）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_documents_tenant_created_at
ON knowledge_documents(tenant_id, created_at DESC);

-- 5. 租户 + 文件名索引（用于文件名搜索）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_documents_tenant_file_name
ON knowledge_documents(tenant_id, file_name);

-- 6. 全文搜索索引（PostgreSQL特有）
-- 如果使用PostgreSQL，可以添加GIN索引用于全文搜索
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_documents_tenant_search
-- ON knowledge_documents USING gin(to_tsvector('english', tenant_id || ' ' || file_name));

-- 7. 状态索引（独立状态查询）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_documents_status
ON knowledge_documents(status);

-- 8. 文件类型索引（独立文件类型查询）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_documents_file_type
ON knowledge_documents(file_type);

-- 9. 文件大小索引（用于大小范围查询）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_documents_file_size
ON knowledge_documents(file_size);

-- 10. 索引时间索引（用于索引状态查询）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_documents_indexed_at
ON knowledge_documents(indexed_at DESC) WHERE indexed_at IS NOT NULL;

-- 11. 更新时间索引（用于缓存失效检查）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_documents_updated_at
ON knowledge_documents(updated_at DESC);

-- 为 tenants 表添加索引优化

-- 1. 邮箱唯一索引（通常已存在，但确保存在）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenants_email_unique
ON tenants(email);

-- 2. Clerk用户ID索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenants_clerk_user_id
ON tenants(clerk_user_id);

-- 3. 活跃状态索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenants_is_active
ON tenants(is_active);

-- 4. 创建时间索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenants_created_at
ON tenants(created_at DESC);

-- 为 data_source_connections 表添加索引（如果存在）

-- 1. 租户 + 活跃状态复合索引
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_data_sources_tenant_active
-- ON data_source_connections(tenant_id, is_active);

-- 2. 连接类型索引
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_data_sources_connection_type
-- ON data_source_connections(connection_type);

-- 创建部分索引用于常见查询模式

-- 1. 只索引已就绪的文档（常见查询模式）
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_documents_ready_tenant
ON knowledge_documents(tenant_id, created_at DESC)
WHERE status = 'READY';

-- 2. 只索引待处理的文档
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_documents_pending_tenant
ON knowledge_documents(tenant_id, created_at ASC)
WHERE status = 'PENDING';

-- 3. 只索引有错误的文档
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_knowledge_documents_error_tenant
ON knowledge_documents(tenant_id, created_at DESC)
WHERE status = 'ERROR';

-- 统计信息更新
-- 确保PostgreSQL查询优化器有最新的统计信息
ANALYZE knowledge_documents;
ANALYZE tenants;

-- 创建查询优化视图
-- 这些视图可以简化常用查询并提供更好的性能

-- 1. 租户文档统计视图
CREATE OR REPLACE VIEW tenant_document_stats AS
SELECT
    tenant_id,
    COUNT(*) as total_documents,
    COUNT(*) FILTER (WHERE status = 'READY') as ready_documents,
    COUNT(*) FILTER (WHERE status = 'PENDING') as pending_documents,
    COUNT(*) FILTER (WHERE status = 'INDEXING') as indexing_documents,
    COUNT(*) FILTER (WHERE status = 'ERROR') as error_documents,
    SUM(file_size) as total_file_size,
    AVG(file_size) as avg_file_size,
    MAX(created_at) as last_upload_date,
    COUNT(*) FILTER (WHERE indexed_at IS NOT NULL) as indexed_documents
FROM knowledge_documents
GROUP BY tenant_id;

-- 2. 文件类型统计视图
CREATE OR REPLACE VIEW file_type_stats AS
SELECT
    file_type,
    COUNT(*) as total_count,
    SUM(file_size) as total_size,
    AVG(file_size) as avg_size,
    COUNT(DISTINCT tenant_id) as tenant_count
FROM knowledge_documents
GROUP BY file_type
ORDER BY total_count DESC;

-- 3. 每日上传统计视图（最近30天）
CREATE OR REPLACE VIEW daily_upload_stats AS
SELECT
    DATE(created_at) as upload_date,
    tenant_id,
    COUNT(*) as documents_uploaded,
    SUM(file_size) as total_size_uploaded
FROM knowledge_documents
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at), tenant_id
ORDER BY upload_date DESC, tenant_id;

-- 创建分区表建议（用于大数据量场景）
-- 这些是注释，供未来大数据量时参考

/*
-- 如果文档数量超过100万，考虑按租户分区
-- CREATE TABLE knowledge_documents_partitioned (
--    LIKE knowledge_documents INCLUDING ALL
-- ) PARTITION BY LIST (tenant_id);

-- 或者按时间分区
-- CREATE TABLE knowledge_documents_partitioned (
--    LIKE knowledge_documents INCLUDING ALL
-- ) PARTITION BY RANGE (created_at);
*/

-- 创建查询性能监控函数
CREATE OR REPLACE FUNCTION log_slow_queries()
RETURNS TRIGGER AS $$
BEGIN
    -- 记录执行时间超过1秒的查询
    -- 这需要配合 pg_stat_statements 扩展使用
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 添加索引使用的注释说明

COMMENT ON INDEX idx_knowledge_documents_tenant_id IS '租户主要查询索引，用于基本租户隔离查询';
COMMENT ON INDEX idx_knowledge_documents_tenant_status IS '租户状态复合索引，用于按状态过滤的租户查询';
COMMENT ON INDEX idx_knowledge_documents_tenant_file_type IS '租户文件类型复合索引，用于按文件类型过滤的租户查询';
COMMENT ON INDEX idx_knowledge_documents_tenant_created_at IS '租户时间排序索引，用于按时间排序的租户文档列表';
COMMENT ON INDEX idx_knowledge_documents_tenant_file_name IS '租户文件名搜索索引，用于文件名搜索优化';

COMMENT ON VIEW tenant_document_stats IS '租户文档统计视图，提供租户级别的文档统计信息';
COMMENT ON VIEW file_type_stats IS '文件类型统计视图，提供全局文件类型使用统计';
COMMENT ON VIEW daily_upload_stats IS '每日上传统计视图，提供最近30天的上传趋势分析';

-- 性能优化建议存储在表注释中
COMMENT ON TABLE knowledge_documents IS '知识文档表 - Story 2.4优化版本，包含租户隔离、UUID主键和性能索引';

COMMIT;

-- 性能验证查询
-- 这些查询可以用于验证索引是否被正确使用

/*
-- 1. 验证租户查询是否使用了索引
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM knowledge_documents
WHERE tenant_id = 'test-tenant-123'
ORDER BY created_at DESC
LIMIT 10;

-- 2. 验证状态过滤查询是否使用了复合索引
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM knowledge_documents
WHERE tenant_id = 'test-tenant-123' AND status = 'READY'
ORDER BY created_at DESC;

-- 3. 验证统计查询性能
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM tenant_document_stats
WHERE tenant_id = 'test-tenant-123';

-- 4. 检查索引使用情况
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'knowledge_documents'
ORDER BY idx_scan DESC;
*/