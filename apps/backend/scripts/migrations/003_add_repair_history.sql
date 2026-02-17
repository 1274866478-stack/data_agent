-- SOTA 重构 Phase 4: 自愈机制相关表
-- 存储 DSL 修复历史，用于学习和优化

-- 修复历史表
CREATE TABLE IF NOT EXISTS repair_history (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,

    -- 错误信息
    original_dsl JSONB NOT NULL,
    error_message TEXT NOT NULL,
    error_pattern VARCHAR(255),
    error_category VARCHAR(100),  -- measure_not_found, invalid_join, etc.

    -- 修复信息
    repaired_dsl JSONB NOT NULL,
    repair_strategy VARCHAR(255),
    repair_details JSONB,

    -- 结果
    success BOOLEAN NOT NULL,
    execution_time_ms INTEGER,

    -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),

    -- 关联
    cube_name VARCHAR(255),
    query_context TEXT
);

COMMENT ON TABLE repair_history IS 'DSL 修复历史，用于自愈机制学习和优化';
COMMENT ON COLUMN repair_history.error_pattern IS '匹配的错误模式名称';
COMMENT ON COLUMN repair_history.repair_strategy IS '使用的修复策略';
COMMENT ON COLUMN repair_history.repair_details IS '修复详情 (JSONB)';
COMMENT ON COLUMN repair_history.success IS '修复是否成功';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_repair_history_tenant ON repair_history(tenant_id);
CREATE INDEX IF NOT EXISTS idx_repair_history_pattern ON repair_history(error_pattern);
CREATE INDEX IF NOT EXISTS idx_repair_history_success ON repair_history(success);
CREATE INDEX IF NOT EXISTS idx_repair_history_created ON repair_history(created_at DESC);

-- 错误模式统计视图
CREATE OR REPLACE VIEW error_pattern_stats AS
SELECT
    error_pattern,
    error_category,
    COUNT(*) as total_attempts,
    SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as successful_repairs,
    ROUND(
        SUM(CASE WHEN success = true THEN 1 ELSE 0 END)::NUMERIC / COUNT(*) * 100,
        2
    ) as success_rate,
    AVG(execution_time_ms) as avg_repair_time_ms
FROM repair_history
GROUP BY error_pattern, error_category
ORDER BY total_attempts DESC;

COMMENT ON VIEW error_pattern_stats IS '错误模式统计视图';

-- 最常用的修复策略视图
CREATE OR REPLACE VIEW repair_strategy_stats AS
SELECT
    repair_strategy,
    error_pattern,
    COUNT(*) as usage_count,
    ROUND(
        SUM(CASE WHEN success = true THEN 1 ELSE 0 END)::NUMERIC / COUNT(*) * 100,
        2
    ) as success_rate
FROM repair_history
WHERE repair_strategy IS NOT NULL
GROUP BY repair_strategy, error_pattern
ORDER BY usage_count DESC;

COMMENT ON VIEW repair_strategy_stats IS '修复策略统计视图';
