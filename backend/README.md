# Data Agent Backend

基于 FastAPI 的多租户 SaaS 数据智能代理后端服务

## 项目结构

```
backend/
├── src/
│   └── app/
│       ├── main.py                 # FastAPI 应用入口
│       ├── api/                    # API 路由
│       │   └── v1/
│       │       ├── __init__.py
│       │       └── endpoints/      # API 端点
│       │           ├── health.py   # 健康检查
│       │           ├── tenants.py  # 租户管理
│       │           ├── documents.py # 文档管理
│       │           └── data_sources.py # 数据源管理
│       ├── core/                   # 核心配置
│       │   └── config.py          # 配置管理
│       ├── data/                   # 数据库相关
│       │   ├── database.py         # 数据库连接
│       │   └── models.py           # 数据模型
│       └── services/               # 业务服务
│           ├── minio_client.py     # MinIO 对象存储
│           ├── chromadb_client.py  # ChromaDB 向量数据库
│           └── zhipu_client.py     # 智谱 AI 服务
├── tests/                          # 测试文件
│   ├── conftest.py                # pytest 配置
│   ├── api/                       # API 测试
│   ├── services/                  # 服务测试
│   └── data/                      # 数据模型测试
├── requirements.txt               # Python 依赖
├── Dockerfile                     # Docker 配置
└── .env.example                   # 环境变量示例
```

## 功能特性

### 核心功能
- ✅ FastAPI 应用框架配置
- ✅ PostgreSQL 数据库连接和 ORM
- ✅ MinIO 对象存储集成
- ✅ ChromaDB 向量数据库集成
- ✅ 智谱 AI API 集成
- ✅ 健康检查端点
- ✅ 多租户支持
- ✅ RESTful API 设计

### API 端点

#### 健康检查
- `GET /health` - 主要健康检查
- `GET /api/v1/health/status` - 详细服务状态
- `GET /api/v1/health/ping` - 简单连通性测试
- `GET /api/v1/health/database` - 数据库连接检查
- `GET /api/v1/health/services` - 服务状态总览

#### 租户管理
- `GET /api/v1/tenants/` - 获取租户列表
- `POST /api/v1/tenants/` - 创建租户
- `GET /api/v1/tenants/{id}` - 获取租户详情
- `PUT /api/v1/tenants/{id}` - 更新租户信息
- `DELETE /api/v1/tenants/{id}` - 删除租户（软删除）
- `GET /api/v1/tenants/{id}/stats` - 获取租户统计信息

#### 文档管理
- `GET /api/v1/documents/` - 获取文档列表
- `POST /api/v1/documents/upload` - 上传文档
- `GET /api/v1/documents/{id}` - 获取文档详情
- `DELETE /api/v1/documents/{id}` - 删除文档
- `GET /api/v1/documents/{id}/download` - 下载文档
- `GET /api/v1/documents/stats/summary` - 文档统计摘要

#### 数据源管理
- `GET /api/v1/data-sources/` - 获取数据源连接列表
- `POST /api/v1/data-sources/` - 创建数据源连接
- `GET /api/v1/data-sources/{id}` - 获取连接详情
- `PUT /api/v1/data-sources/{id}` - 更新连接信息
- `DELETE /api/v1/data-sources/{id}` - 删除连接（软删除）
- `POST /api/v1/data-sources/{id}/test` - 测试连接
- `GET /api/v1/data-sources/types/supported` - 支持的数据源类型

## 快速开始

### 环境要求
- Python 3.11+
- PostgreSQL 16+
- Docker & Docker Compose

### 安装依赖
```bash
pip install -r requirements.txt
```

### 环境配置
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库连接、API密钥等
```

### 启动应用
```bash
# 开发模式
uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
gunicorn src.app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Docker 部署
```bash
# 构建镜像
docker build -t data-agent-backend .

# 运行容器
docker run -p 8000:8000 -e DATABASE_URL=your_db_url data-agent-backend
```

## 数据模型

### Tenant（租户）
- id: 主键
- name: 租户名称（唯一）
- display_name: 显示名称
- description: 描述信息
- is_active: 是否活跃
- created_at/updated_at: 时间戳

### DataSourceConnection（数据源连接）
- id: 主键
- tenant_id: 租户ID（外键）
- name: 连接名称
- connection_type: 连接类型（postgresql, mysql等）
- connection_string: 连接字符串（加密存储）
- host/port/database_name: 连接信息
- is_active: 是否活跃

### KnowledgeDocument（知识文档）
- id: 主键
- tenant_id: 租户ID（外键）
- title: 文档标题
- file_name: 文件名
- file_path: MinIO对象路径
- file_size: 文件大小
- file_type: 文件类型
- processing_status: 处理状态
- vectorized: 是否已向量化
- vector_count: 向量数量

## 测试

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/api/v1/endpoints/test_health.py

# 运行测试并生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 测试覆盖
- 健康检查端点测试
- 租户管理功能测试
- MinIO 服务测试
- 数据库模型测试
- API 集成测试

## 配置说明

### 应用配置
- `APP_NAME`: 应用名称
- `APP_VERSION`: 应用版本
- `DEBUG`: 调试模式开关

### 数据库配置
- `DATABASE_URL`: PostgreSQL 连接字符串
- `DATABASE_POOL_SIZE`: 连接池大小
- `DATABASE_MAX_OVERFLOW`: 最大溢出连接数

### MinIO 配置
- `MINIO_ENDPOINT`: MinIO 服务地址
- `MINIO_ACCESS_KEY`: 访问密钥
- `MINIO_SECRET_KEY`: 秘密密钥
- `MINIO_SECURE`: 是否使用 HTTPS

### ChromaDB 配置
- `CHROMA_HOST`: ChromaDB 主机地址
- `CHROMA_PORT`: ChromaDB 端口
- `CHROMA_COLLECTION_NAME`: 默认集合名称

### 智谱 AI 配置
- `ZHIPUAI_API_KEY`: 智谱 AI API 密钥

## 开发指南

### 添加新 API 端点
1. 在 `src/app/api/v1/endpoints/` 创建新的端点文件
2. 实现路由处理函数
3. 在 `src/app/api/v1/__init__.py` 注册路由
4. 编写对应的测试用例

### 添加新服务
1. 在 `src/app/services/` 创建服务文件
2. 实现服务类和方法
3. 在端点文件中导入和使用服务
4. 编写服务测试

### 数据库迁移
```bash
# 生成迁移文件
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head
```

## 部署说明

### 生产环境检查清单
- [ ] 设置适当的日志级别
- [ ] 配置环境变量管理
- [ ] 启用 HTTPS
- [ ] 配置 API 限流
- [ ] 设置监控和告警
- [ ] 配置备份策略
- [ ] 执行安全扫描

## 监控和日志

### 健康检查
应用提供多个健康检查端点用于监控：
- 服务连接状态
- 数据库连接检查
- 外部服务可用性

### 日志格式
使用结构化日志记录，包含：
- 时间戳
- 日志级别
- 模块名称
- 请求ID（如果适用）

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 编写代码和测试
4. 提交 Pull Request
5. 等待代码审查

## 许可证

MIT License