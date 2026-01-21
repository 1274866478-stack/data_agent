-- SOTA 重构 Phase 3: 少样本 RAG 相关表
-- 存储成功的查询历史，用于动态少样本学习
-- 注意: 向量存储在 Qdrant 中，PostgreSQL 只存储元数据

-- 成功查询历史表
CREATE TABLE IF NOT EXISTS successful_queries (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    original_question TEXT NOT NULL,
    rewritten_question TEXT,
    dsl_json JSONB NOT NULL,
    cube_name VARCHAR(255) NOT NULL,
    execution_time_ms INTEGER,
    row_count INTEGER,
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    qdrant_point_id VARCHAR(255),  -- Qdrant 向量 ID
    created_at TIMESTAMP DEFAULT NOW(),

    -- 元数据
    query_complexity VARCHAR(50),  -- simple, medium, complex
    success BOOLEAN DEFAULT true,
    error_message TEXT
);

COMMENT ON TABLE successful_queries IS '成功查询历史，用于少样本 RAG';
COMMENT ON COLUMN successful_queries.original_question IS '原始用户问题';
COMMENT ON COLUMN successful_queries.dsl_json IS '生成的 DSL JSON';
COMMENT ON COLUMN successful_queries.qdrant_point_id IS 'Qdrant 向量 ID (用于关联向量检索)';
COMMENT ON COLUMN successful_queries.user_rating IS '用户评分 (1-5)';
COMMENT ON COLUMN successful_queries.query_complexity IS '查询复杂度';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_successful_queries_tenant ON successful_queries(tenant_id);
CREATE INDEX IF NOT EXISTS idx_successful_queries_created ON successful_queries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_successful_queries_rating ON successful_queries(user_rating) WHERE user_rating IS NOT NULL;

-- 触发器：自动计算查询复杂度
CREATE OR REPLACE FUNCTION infer_query_complexity()
RETURNS TRIGGER AS '
BEGIN
    -- 简单规则推断查询复杂度
    IF NEW.dsl_json::text LIKE ''%JOIN%'' OR NEW.dsl_json::text LIKE ''%GROUP BY%'' THEN
        NEW.query_complexity := ''complex'';
    ELSIF NEW.dsl_json::text LIKE ''%WHERE%'' OR NEW.dsl_json::text LIKE ''%ORDER BY%'' THEN
        NEW.query_complexity := ''medium'';
    ELSE
        NEW.query_complexity := ''simple'';
    END IF;
    RETURN NEW;
END;
' LANGUAGE plpgsql;

CREATE TRIGGER trigger_infer_complexity
BEFORE INSERT ON successful_queries
FOR EACH ROW
EXECUTE FUNCTION infer_query_complexity();
