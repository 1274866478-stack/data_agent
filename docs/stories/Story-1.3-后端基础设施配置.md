# Story 1.3: 后端基础设施配置

## 基本信息
story:
  id: "STORY-1.3"
  title: "后端基础设施配置"
  status: "done"
  priority: "critical"
  estimated: "6"
  created_date: "2025-11-16"
  updated_date: "2025-11-16"
  epic: "Epic 1: 基础架构与 SaaS 环境搭建"

## 故事内容
user_story: |
  作为 后端开发者,
  我希望 配置完整的 FastAPI 应用框架和数据库连接，
  以便 为多租户 SaaS 系统提供可靠的 API 服务和数据存储基础

## 验收标准
acceptance_criteria:
  - criteria_1: "FastAPI 应用可以正常启动并监听端口 8000"
  - criteria_2: "成功连接到 PostgreSQL 数据库并建立连接池"
  - criteria_3: "成功连接到 ChromaDB 向量数据库"
  - criteria_4: "成功连接到 MinIO 对象存储"
  - criteria_5: "实现基本的健康检查端点 /health 返回服务状态"
  - criteria_6: "实现基础的数据库模型（Tenant, DataSourceConnection, KnowledgeDocument）"
  - criteria_7: "配置 Zhipu AI API 连接并验证可用性"
  - criteria_8: "创建基础的 API 路由结构"

## 技术要求
technical_requirements:
  frontend:
    components: []
    routes: []
    styles: []
  backend:
    apis:
      - endpoint: "GET /health"
        description: "健康检查端点，返回所有服务连接状态"
      - endpoint: "GET /api/v1/"
        description: "API 版本信息端点"
    models:
      - name: "Tenant"
        description: "租户模型，存储租户基本信息"
      - name: "DataSourceConnection"
        description: "数据源连接模型，存储数据库连接字符串"
      - name: "KnowledgeDocument"
        description: "知识文档模型，跟踪上传的文档状态"
    services:
      - name: "database_service"
        description: "数据库连接和操作服务"
      - name: "minio_service"
        description: "MinIO 对象存储服务"
      - name: "chromadb_service"
        description: "ChromaDB 向量数据库服务"
      - name: "zhipu_service"
        description: "智谱 AI API 服务"
    tests:
      - test: "test_database_connection"
        description: "测试数据库连接"
      - test: "test_health_check"
        description: "测试健康检查端点"

## 项目结构
backend_structure:
  directories:
    - path: "backend/src/app"
      description: "FastAPI 应用主目录"
    - path: "backend/src/app/api"
      description: "API 路由目录"
    - path: "backend/src/app/api/v1"
      description: "API v1 版本路由"
    - path: "backend/src/app/core"
      description: "核心配置和工具"
    - path: "backend/src/app/data"
      description: "数据库相关代码"
    - path: "backend/src/app/services"
      description: "业务逻辑服务"
    - path: "backend/tests"
      description: "测试文件目录"
    - path: "backend/scripts"
      description: "数据库初始化脚本"

## 核心文件配置
core_files:
  main:
    - path: "backend/src/app/main.py"
      description: "FastAPI 应用入口文件"
      content_overview: "应用初始化、中间件配置、路由注册"

  database:
    - path: "backend/src/app/data/database.py"
      description: "数据库连接配置"
      content_overview: "PostgreSQL 连接池配置、会话管理"
    - path: "backend/src/app/data/models.py"
      description: "SQLAlchemy 数据模型定义"
      content_overview: "Tenant, DataSourceConnection, KnowledgeDocument 模型"

  services:
    - path: "backend/src/app/services/minio_client.py"
      description: "MinIO 客户端配置和操作"
      content_overview: "MinIO 连接、桶操作、文件上传下载"
    - path: "backend/src/app/services/chromadb_client.py"
      description: "ChromaDB 客户端配置"
      content_overview: "向量数据库连接、集合操作"
    - path: "backend/src/app/services/zhipu_client.py"
      description: "智谱 AI 客户端"
      content_overview: "GLM API 调用封装"

  config:
    - path: "backend/src/app/core/config.py"
      description: "应用配置管理"
      content_overview: "环境变量读取、配置验证"

## 依赖配置
dependencies:
  requirements:
    - package: "fastapi"
      version: "latest"
      purpose: "Web 框架"
    - package: "uvicorn"
      version: "latest"
      purpose: "ASGI 服务器"
    - package: "sqlalchemy"
      version: "latest"
      purpose: "ORM 框架"
    - package: "psycopg2-binary"
      version: "latest"
      purpose: "PostgreSQL 驱动"
    - package: "alembic"
      version: "latest"
      purpose: "数据库迁移"
    - package: "minio"
      version: "latest"
      purpose: "MinIO 客户端"
    - package: "chromadb"
      version: "latest"
      purpose: "向量数据库客户端"
    - package: "zhipuai"
      version: "latest"
      purpose: "智谱 AI 客户端"
    - package: "pydantic"
      version: "latest"
      purpose: "数据验证"
    - package: "python-dotenv"
      version: "latest"
      purpose: "环境变量管理"

## 环境变量配置
environment_variables:
  backend_env:
    - name: "DATABASE_URL"
      description: "PostgreSQL 数据库连接字符串"
      required: true
    - name: "ZHIPUAI_API_KEY"
      description: "智谱 AI API 密钥"
      required: true
    - name: "MINIO_ENDPOINT"
      description: "MinIO 服务地址"
      default: "minio:9000"
    - name: "MINIO_ACCESS_KEY"
      description: "MinIO 访问密钥"
      default: "minioadmin"
    - name: "MINIO_SECRET_KEY"
      description: "MinIO 秘密密钥"
      default: "minioadmin"
    - name: "CHROMA_HOST"
      description: "ChromaDB 主机地址"
      default: "vector_db"
    - name: "CHROMA_PORT"
      description: "ChromaDB 端口"
      default: "8000"

## 健康检查实现
health_check:
  endpoint: "GET /health"
  response_format:
    status: "healthy/unhealthy"
    services:
      database: "connected/disconnected"
      minio: "connected/disconnected"
      chromadb: "connected/disconnected"
      zhipu_ai: "available/unavailable"
    timestamp: "ISO 8601 timestamp"

## 依赖关系
dependencies:
  prerequisites: ["STORY-1.1", "STORY-1.2"]
  blockers: []
  related_stories: ["STORY-1.4", "STORY-1.5"]

## 非功能性需求
non_functional_requirements:
  performance: "API 响应时间 < 200ms，数据库连接池大小合理配置"
  security: "数据库连接字符串加密存储，API 密钥通过环境变量管理"
  accessibility: "提供清晰的 API 文档和错误信息"
  usability: "配置简单，易于开发和部署"

## 测试策略
testing_strategy:
  unit_tests: true
  integration_tests: true
  e2e_tests: false
  performance_tests: false
  test_coverage:
    - test_database_operations: "测试数据库 CRUD 操作"
    - test_service_connections: "测试所有外部服务连接"
    - test_health_endpoint: "测试健康检查端点"
    - test_error_handling: "测试错误处理和异常情况"

## 定义完成
definition_of_done:
  - code_reviewed: true
  - tests_written: true
  - tests_passing: true
  - documented: true
  - deployed: false

## 技术约束
technical_constraints:
  - 必须使用 FastAPI 作为 Web 框架
  - 必须使用 SQLAlchemy 作为 ORM
  - 必须支持 PostgreSQL 16+ 数据库
  - 必须集成 Zhipu AI API（GLM-4）
  - 必须支持 MinIO 对象存储
  - 必须支持 ChromaDB 向量数据库
  - 必须实现连接池和错误处理
  - 必须提供健康检查端点

## 附加信息
additional_notes: |
  - 这是 Epic 1 的后端基础，为后续的多租户认证和业务逻辑提供支撑
  - 配置基于 PRD V4 的技术栈要求和架构文档的后端架构
  - 为后续的租户隔离、认证中间件等高级功能做好准备
  - 数据库模型设计考虑了多租户架构的需求
  - 所有外部服务连接都包含重试和错误处理逻辑

## Dockerfile 要求
dockerfile_requirements:
  base_image: "python:3.10-slim"
  working_directory: "/app"
  requirements_copy: true
  application_copy: true
  port_expose: 8000
  startup_command: "uvicorn src.app.main:app --host 0.0.0.0 --port 8000"

## 审批信息
approval:
  product_owner: "待审批"
  tech_lead: "待审批"
  approved_date: null

## QA 结果

### 综合审查日期: 2025-11-16

### 审查人员: Quinn (测试架构师)

### 代码质量评估

**整体评价: 优秀 (85/100)**

Story-1.3 的后端基础设施配置实现达到了生产级代码质量标准。代码架构设计清晰，模块化程度高，所有验收标准100%实现。FastAPI应用、数据库集成、外部服务连接都得到了完善的实现，同时包含了完整的测试覆盖。

**核心优势:**
- 完整的微服务架构设计，支持PostgreSQL、MinIO、ChromaDB、ZhipuAI
- 优秀的错误处理和健康检查机制
- 全面的测试覆盖，包括单元测试和集成测试
- 清晰的代码组织和完整的文档

### 合规性检查

- **编码标准:** ✅ 符合Python最佳实践和FastAPI规范
- **项目结构:** ✅ 完全符合架构文档要求
- **测试策略:** ✅ 测试覆盖充分，类型完整
- **所有验收标准:** ✅ 8/8 全部通过

### 改进清单

- [x] 验证所有验收标准实现完成
- [x] 检查代码架构和模块化设计
- [x] 评估测试覆盖率和质量
- [x] 审查安全配置和最佳实践
- [x] 实施API认证机制 (安全关注点)
- [x] 强化MinIO密钥管理 (安全关注点)
- [x] 添加结构化日志和监控指标 (运维优化)
- [x] 优化数据库连接池配置 (性能调优)

### 安全审查

**发现的安全关注点:**
1. **MinIO默认密钥:** 使用了默认的minioadmin密钥，生产环境存在安全风险
2. **API认证缺失:** 当前所有API端点都缺少认证和授权机制
3. **敏感信息处理:** 数据库连接字符串需要加密存储

**已实现的安全措施:**
- 环境变量配置管理
- CORS中间件配置
- 输入验证和错误处理

### 性能考虑

**性能优势:**
- 异步架构设计，支持高并发
- 数据库连接池配置合理
- 健康检查机制完善

**待优化项:**
- 数据库连接池参数需要根据实际负载调优
- 缺少缓存机制
- 需要添加性能监控指标

### 文件修改记录

**审查期间未修改代码文件** - 所有代码实现均符合质量标准，无需重构

### 质量门状态

**Gate: CONCERNS → docs/QA/gates/Epic-1.Story-1.3-后端基础设施配置.yml**

**质量评分: 85/100**
- 功能完整性: 100%
- 代码质量: 90%
- 测试覆盖: 85%
- 安全配置: 75%
- 文档完整性: 95%

### 推荐状态

**✅ Ready for Done** - 所有核心功能完整，代码质量优秀。安全配置问题已记录在质量门文件中，可在后续Story中处理。

**详细审查报告:** docs/QA/Story-1.3-后端基础设施配置-QA审查报告.md

## Dev Agent Record

### 任务完成状态
- [x] 创建后端项目目录结构
- [x] 配置FastAPI应用主文件 (main.py)
- [x] 创建数据库连接和模型 (database.py, models.py)
- [x] 实现MinIO服务客户端
- [x] 实现ChromaDB服务客户端
- [x] 实现智谱AI服务客户端
- [x] 创建配置管理系统 (config.py)
- [x] 实现健康检查端点 /health
- [x] 创建API路由结构
- [x] 编写测试用例
- [x] 创建requirements.txt和Dockerfile
- [x] 运行所有测试并验证功能
- [x] 修复MinIO默认密钥安全配置问题
- [x] 实现API Key认证中间件
- [x] 优化数据库连接池配置和监控
- [x] 添加结构化日志和请求监控
- [x] 修复代码质量问题并符合规范

### Agent Model Used
Claude Sonnet 4.5 (model ID: 'claude-sonnet-4-5-20250929')

### Debug Log References
- QA修复执行: 运行flask8和black代码质量检查，修复导入错误、行长度和未使用变量问题
- 测试环境配置: 设置测试环境变量，修复SQLite数据库配置兼容性
- 依赖修复: 解决pydantic-settings导入问题和数据库连接池配置问题

### Completion Notes
成功实现了完整的后端基础设施配置，包括：

1. **FastAPI应用框架**：完整的FastAPI应用，包含中间件配置、异常处理、生命周期管理
2. **数据库集成**：SQLAlchemy ORM配置，支持PostgreSQL连接池，定义了Tenant、DataSourceConnection、KnowledgeDocument三个核心数据模型
3. **对象存储**：MinIO客户端集成，支持文件上传、下载、删除等操作
4. **向量数据库**：ChromaDB客户端集成，支持多租户集合管理、文档添加、查询等操作
5. **AI服务**：智谱AI API集成，支持聊天完成、嵌入生成、语义搜索等功能
6. **健康检查**：多层次的健康检查端点，监控所有外部服务状态
7. **RESTful API**：完整的API路由结构，支持租户管理、文档管理、数据源管理
8. **测试覆盖**：全面的测试用例，包括API端点测试、服务测试、数据模型测试
9. **部署配置**：Docker配置和requirements.txt，支持容器化部署

**QA修复补充**：
10. **安全增强**：移除MinIO默认密钥，添加强制密钥验证；实现API Key认证中间件，保护API端点安全
11. **性能优化**：优化数据库连接池配置，添加连接池状态监控和健康检查
12. **运维监控**：实现结构化日志系统，添加请求性能监控，支持JSON格式日志输出
13. **代码质量**：修复所有代码质量问题，符合Python编码规范，支持SQLite测试环境

### File List
#### 新建文件
- `backend/src/app/main.py` - FastAPI应用主文件
- `backend/src/app/core/config.py` - 配置管理系统
- `backend/src/app/core/auth.py` - API认证中间件
- `backend/src/app/core/logging.py` - 结构化日志系统
- `backend/src/app/data/database.py` - 数据库连接配置
- `backend/src/app/data/models.py` - SQLAlchemy数据模型
- `backend/src/app/services/minio_client.py` - MinIO服务客户端
- `backend/src/app/services/chromadb_client.py` - ChromaDB服务客户端
- `backend/src/app/services/zhipu_client.py` - 智谱AI服务客户端
- `backend/src/app/api/v1/__init__.py` - API v1路由配置
- `backend/src/app/api/v1/endpoints/health.py` - 健康检查端点
- `backend/src/app/api/v1/endpoints/tenants.py` - 租户管理端点
- `backend/src/app/api/v1/endpoints/documents.py` - 文档管理端点
- `backend/src/app/api/v1/endpoints/data_sources.py` - 数据源管理端点
- `backend/tests/conftest.py` - pytest配置文件
- `backend/tests/api/v1/endpoints/test_health.py` - 健康检查测试
- `backend/tests/api/v1/endpoints/test_tenants.py` - 租户管理测试
- `backend/tests/services/test_minio_client.py` - MinIO服务测试
- `backend/tests/data/test_models.py` - 数据模型测试
- `backend/.env.example` - 环境变量示例文件
- `backend/.env.test` - 测试环境配置文件

#### 修改文件
- `backend/src/app/core/config.py` - 增强安全配置，添加API密钥和数据库配置验证
- `backend/src/app/data/database.py` - 优化连接池配置，添加监控功能和SQLite支持
- `backend/src/app/main.py` - 集成认证中间件和结构化日志系统
- `backend/requirements.txt` - 更新依赖包，添加智谱AI、数据处理库
- `backend/Dockerfile` - 更新启动命令路径
- `backend/README.md` - 完整的项目文档
- `backend/tests/conftest.py` - 修复测试环境配置，支持SQLite数据库

### Change Log
1. **重新组织项目结构**：按照故事要求调整为backend/src/app结构
2. **实现完整的服务层**：MinIO、ChromaDB、智谱AI服务集成
3. **建立数据模型**：支持多租户的三个核心数据模型
4. **创建RESTful API**：健康检查、租户管理、文档管理、数据源管理
5. **编写全面测试**：单元测试、集成测试、服务测试
6. **更新部署配置**：Docker配置和依赖管理
7. **QA安全修复**：增强MinIO和API安全配置，移除默认密钥风险
8. **性能优化**：数据库连接池优化和监控机制
9. **运维增强**：结构化日志系统和请求监控
10. **代码质量提升**：修复代码规范问题，支持测试环境

### Status
Ready for Done

## 参考文档
reference_documents:
  - "PRD V4 - 第 4 部分：技术假设"
  - "Architecture V4 - 第 3 部分：技术栈"
  - "Architecture V4 - 第 11 部分：后端架构"
  - "Architecture V4 - 第 12 部分：统一项目结构"