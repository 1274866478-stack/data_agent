-- SOTA 重构 Phase 1: 语义层相关表
-- 执行前请备份数据库

-- 1. Cubes 表 - 存储 Cube 定义
CREATE TABLE IF NOT EXISTS cubes (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    cube_name VARCHAR(255) NOT NULL,
    cube_definition JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, cube_name)
);

COMMENT ON TABLE cubes IS '语义层 Cube 定义';
COMMENT ON COLUMN cubes.tenant_id IS '租户ID';
COMMENT ON COLUMN cubes.cube_name IS 'Cube 名称';
COMMENT ON COLUMN cubes.cube_definition IS 'Cube 定义 (JSONB)';
COMMENT ON COLUMN cubes.is_active IS '是否激活';

-- 2. Cube Measures 表 - 存储度量定义
CREATE TABLE IF NOT EXISTS cube_measures (
    id SERIAL PRIMARY KEY,
    cube_id INTEGER REFERENCES cubes(id) ON DELETE CASCADE,
    measure_name VARCHAR(255) NOT NULL,
    measure_type VARCHAR(50) NOT NULL,  -- sum, count, avg, min, max, etc.
    measure_definition JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE cube_measures IS 'Cube 度量定义';
COMMENT ON COLUMN cube_measures.measure_type IS '度量类型: sum, count, avg, min, max, etc.';

-- 3. Cube Dimensions 表 - 存储维度定义
CREATE TABLE IF NOT EXISTS cube_dimensions (
    id SERIAL PRIMARY KEY,
    cube_id INTEGER REFERENCES cubes(id) ON DELETE CASCADE,
    dimension_name VARCHAR(255) NOT NULL,
    dimension_type VARCHAR(50) NOT NULL,  -- time, string, number, boolean, etc.
    dimension_definition JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE cube_dimensions IS 'Cube 维度定义';
COMMENT ON COLUMN cube_dimensions.dimension_type IS '维度类型: time, string, number, boolean, etc.';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_cubes_tenant_id ON cubes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_cubes_tenant_active ON cubes(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_cube_measures_cube_id ON cube_measures(cube_id);
CREATE INDEX IF NOT EXISTS idx_cube_dimensions_cube_id ON cube_dimensions(cube_id);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS '
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
' LANGUAGE plpgsql;

CREATE TRIGGER update_cubes_updated_at BEFORE UPDATE ON cubes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
