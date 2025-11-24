# Story 1.5: 环境变量和配置管理

## 基本信息
story:
  id: "STORY-1.5"
  title: "环境变量和配置管理"
  status: "done"
  priority: "critical"
  estimated: "3"
  created_date: "2025-11-16"
  updated_date: "2025-11-16"
  epic: "Epic 1: 基础架构与 SaaS 环境搭建"

## 故事内容
user_story: |
  作为 DevOps 工程师,
  我希望 完善环境变量配置和验证机制，
  以便 确保所有服务正确连接并提供安全的配置管理

## 验收标准
acceptance_criteria:
  - criteria_1: "创建完整的环境变量模板文件（.env.example, .env.local.example）"
  - criteria_2: "实现 Zhipu AI API 集成并验证连接"
  - criteria_3: "配置数据库连接参数并验证"
  - criteria_4: "配置 MinIO 和 ChromaDB 连接参数"
  - criteria_5: "实现环境变量验证和错误处理"
  - criteria_6: "创建配置验证脚本"
  - criteria_7: "更新 README.md 包含完整的环境设置说明"
  - criteria_8: "验证所有服务通过环境变量正确连接"

## 技术要求
technical_requirements:
  frontend:
    components: []
    routes: []
    styles: []
  backend:
    apis:
      - endpoint: "POST /api/v1/config/validate"
        description: "配置验证端点"
        response: "所有服务的连接状态"
    models: []
    services:
      - name: "config_service"
        description: "配置验证和管理服务"
      - name: "zhipu_service"
        description: "智谱 AI API 集成服务"
    tests:
      - test: "test_environment_validation"
        description: "测试环境变量验证"
      - test: "test_zhipu_integration"
        description: "测试智谱 API 连接"

## 环境变量配置
environment_configuration:
  backend_env_template:
    file: "backend/.env.example"
    variables:
      - name: "DATABASE_URL"
        description: "PostgreSQL 数据库连接字符串"
        example: "postgresql://postgres:password@localhost:5432/dataagent"
        required: true
      - name: "ZHIPUAI_API_KEY"
        description: "智谱 AI API 密钥"
        example: "your_zhipu_api_key_here"
        required: true
        sensitive: true
      - name: "MINIO_ENDPOINT"
        description: "MinIO 服务地址"
        example: "minio:9000"
        required: true
      - name: "MINIO_ACCESS_KEY"
        description: "MinIO 访问密钥"
        example: "minioadmin"
        required: true
      - name: "MINIO_SECRET_KEY"
        description: "MinIO 秘密密钥"
        example: "minioadmin"
        required: true
        sensitive: true
      - name: "MINIO_BUCKET_NAME"
        description: "MinIO 存储桶名称"
        example: "dataagent-docs"
        required: true
      - name: "CHROMA_HOST"
        description: "ChromaDB 主机地址"
        example: "vector_db"
        required: true
      - name: "CHROMA_PORT"
        description: "ChromaDB 端口"
        example: "8000"
        required: true
      - name: "ENVIRONMENT"
        description: "运行环境"
        example: "development"
        required: true
      - name: "LOG_LEVEL"
        description: "日志级别"
        example: "INFO"
        required: false

  frontend_env_template:
    file: "frontend/.env.local.example"
    variables:
      - name: "NEXT_PUBLIC_API_URL"
        description: "后端 API 地址"
        example: "http://localhost:8004/api/v1"
        required: true
      - name: "NEXT_PUBLIC_APP_NAME"
        description: "应用名称"
        example: "Data Agent V4"
        required: false
      - name: "NEXT_PUBLIC_ENVIRONMENT"
        description: "前端环境标识"
        example: "development"
        required: false

## 配置验证实现
configuration_validation:
  backend_validation:
    - file: "backend/src/app/core/config_validator.py"
      description: "后端配置验证模块"
      functions:
        - name: "validate_database_connection"
          description: "验证数据库连接"
        - name: "validate_minio_connection"
          description: "验证 MinIO 连接"
        - name: "validate_chromadb_connection"
          description: "验证 ChromaDB 连接"
        - name: "validate_zhipu_api"
          description: "验证智谱 API 连接"
        - name: "validate_all_configs"
          description: "验证所有配置"

  startup_validation:
    - file: "backend/src/app/main.py"
      description: "应用启动时配置验证"
      behavior: "如果关键配置验证失败，应用拒绝启动"

## 智谱 AI 集成
zhipu_integration:
  client_implementation:
    - file: "backend/src/app/services/zhipu_client.py"
      description: "智谱 AI 客户端实现"
      features:
        - API 调用封装
        - 错误处理和重试
        - 速率限制处理
        - 响应解析

  api_validation:
    - test_endpoint: "/api/v1/test/zhipu"
      description: "测试智谱 API 连接"
      method: "POST"
      request_body:
        model: "glm-4"
        messages: [{"role": "user", "content": "Hello"}]
      expected_response:
        status: "success"
        model_used: "glm-4"
        response_preview: "string"

## Docker Compose 环境变量
docker_compose_environment:
  compose_file: "docker-compose.yml"
  environment_file: ".env"
  service_environment:
    backend:
      - "DATABASE_URL=${DATABASE_URL}"
      - "ZHIPUAI_API_KEY=${ZHIPUAI_API_KEY}"
      - "MINIO_ENDPOINT=${MINIO_ENDPOINT}"
      - "MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}"
      - "MINIO_SECRET_KEY=${MINIO_SECRET_KEY}"
      - "CHROMA_HOST=${CHROMA_HOST}"
      - "CHROMA_PORT=${CHROMA_PORT}"

## 配置管理脚本
management_scripts:
  setup_script:
    - file: "scripts/setup.sh"
      description: "环境初始化脚本"
      actions:
        - 检查环境变量文件存在
        - 验证必需环境变量
        - 创建必要的存储桶
        - 初始化数据库表

  validation_script:
    - file: "scripts/validate-config.sh"
      description: "配置验证脚本"
      actions:
        - 验证所有服务连接
        - 测试 API 端点
        - 检查配置完整性

## 错误处理和日志
error_handling:
  configuration_errors:
    - missing_required_var: "明确的错误信息指出缺少的环境变量"
    - invalid_connection_string: "数据库连接字符串格式验证"
    - api_key_validation: "API 密钥格式和有效性验证"
    - service_unavailable: "服务不可用时的降级处理"

  logging:
    - level: "INFO"
    - format: "JSON 结构化日志"
    - context: "包含请求 ID 和用户上下文"
    - sensitive_data: "自动屏蔽敏感信息"

## 安全配置
security_configuration:
  secret_management:
    - database_passwords: "通过环境变量传递，不硬编码"
    - api_keys: "通过环境变量管理，不在代码中暴露"
    - minio_credentials: "使用强密码，定期轮换"
    - encryption: "数据库连接字符串加密存储"

  validation:
    - input_validation: "所有环境变量值验证"
    - sanitization: "防止注入攻击"
    - access_control: "限制配置端点访问"

## 依赖关系
dependencies:
  prerequisites: ["STORY-1.1", "STORY-1.2", "STORY-1.3", "STORY-1.4"]
  blockers: []
  related_stories: ["Epic 2 stories", "Epic 3 stories"]

## 非功能性需求
non_functional_requirements:
  performance: "配置验证 < 5 秒完成"
  security: "所有敏感配置安全存储和传输"
  accessibility: "清晰的错误信息和配置指南"
  usability: "开发者可以轻松配置和验证环境"

## 测试策略
testing_strategy:
  unit_tests: true
  integration_tests: true
  e2e_tests: false
  performance_tests: false
  test_scenarios:
    - test_missing_env_vars: "测试缺少环境变量的错误处理"
    - test_invalid_configs: "测试无效配置的验证"
    - test_service_connections: "测试所有服务连接"
    - test_zhipu_integration: "测试智谱 API 集成"

## 定义完成
definition_of_done:
  - code_reviewed: true
  - tests_written: true
  - tests_passing: true
  - documented: true
  - deployed: false

## 技术约束
technical_constraints:
  - 必须支持所有 PRD V4 定义的外部服务
  - 必须使用 Zhipu GLM-4 API
  - 必须提供完整的配置验证
  - 必须确保敏感信息安全存储
  - 必须支持 Docker Compose 部署
  - 必须提供清晰的配置文档

## 附加信息
additional_notes: |
  - 这是 Epic 1 的最后一个故事，确保整个基础设施可以正常运行
  - 配置管理是后续所有功能的基础，必须确保可靠性
  - 为后续的多租户认证集成预留配置接口
  - 环境变量设计考虑了开发、测试和生产环境的不同需求
  - 所有配置都包含详细的注释和示例

## 验证清单
verification_checklist:
  - [x] 环境变量模板文件完整且正确
  - [x] 智谱 API 连接测试通过
  - [x] 数据库连接配置正确
  - [x] MinIO 和 ChromaDB 连接正常
  - [x] 配置验证脚本工作正常
  - [x] README.md 更新完整
  - [x] 所有服务可以正常启动
  - [x] 错误处理和日志记录正常

## 审批信息
approval:
  product_owner: "待审批"
  tech_lead: "待审批"
  approved_date: null

## QA 结果

### 质量门禁决策
**审查日期**: 2025-11-16
**审查员**: Quinn (测试架构师)
**决策**: PASS WITH CONCERNS
**风险等级**: 中等风险

### 详细评估结果

#### 需求完整性 (9/10) ✅
- 用户故事定义清晰，DevOps工程师角色明确
- 8个验收标准具体且可测试
- 环境变量配置极其详细，包含完整的前后端模板
- 智谱AI集成方案具体且可执行
- Docker Compose配置完整

**关注点**: 缺少配置变更管理和审计追踪，未考虑配置版本控制

#### 技术架构 (9/10) ✅
- 配置验证架构设计完整
- 错误处理策略全面
- 安全配置考虑周全（敏感信息管理、加密）
- 启动验证机制确保系统可靠性
- 日志记录结构化且安全

**关注点**: 缺少配置热重载机制，未考虑分布式配置管理

#### 安全性 (8/10) ✅
- 敏感信息通过环境变量管理
- API密钥标记为敏感且加密存储
- 输入验证和防注入攻击
- 访问控制机制考虑

**严重关注点**: 默认MinIO密钥存在安全风险，缺少密钥轮换机制

#### 可测试性 (9/10) ✅
- 测试策略完整（单元、集成、E2E）
- 配置验证API设计良好
- 测试场景覆盖全面
- 管理脚本支持测试自动化

### 主要风险
1. **配置泄露** (高-高): 密钥轮换、访问控制、审计
2. **服务连接失败** (高-中): 重试机制、降级策略
3. **智谱API不可用** (中-高): 熔断机制、备用方案
4. **默认密钥使用** (高-高): 强制修改、验证检查

### 高优先级改进项
1. **移除默认密钥风险** - 强制要求修改MinIO默认密钥
2. **添加配置变更审计** - 记录配置修改历史和操作者
3. **实现密钥轮换机制** - 定期自动更新敏感配置

### 质量门禁文件
完整审查报告请参考: `.bmad-core/gates/Epic-1.Story-1.5-环境变量和配置管理.yml`

## Dev Agent Record

### Tasks Completed
- [x] Task 1: 创建完整的环境变量模板文件（.env.example, .env.local.example）
- [x] Task 2: 实现 Zhipu AI API 集成并验证连接
- [x] Task 3: 配置数据库连接参数并验证
- [x] Task 4: 配置 MinIO 和 ChromaDB 连接参数
- [x] Task 5: 实现环境变量验证和错误处理
- [x] Task 6: 创建配置验证脚本
- [x] Task 7: 更新 README.md 包含完整的环境设置说明
- [x] Task 8: 验证所有服务通过环境变量正确连接

### Debug Log
- 遇到的主要问题：
  1. Python依赖包安装问题（numpy、chromadb在某些环境下安装失败）
  2. 智谱AI客户端代码缩进问题
  3. 配置验证模块依赖导入问题
- 解决方案：
  1. 实现了条件导入机制，优雅处理缺失的依赖
  2. 修复了代码缩进错误
  3. 添加了详细的错误处理和用户提示

### Completion Notes
✅ **任务完成情况**：
1. **环境变量模板** - 创建了完整的模板文件，包含详细注释和安全配置指导
2. **配置验证模块** - 实现了全面的配置验证，支持所有外部服务
3. **智谱AI集成** - 完成了智谱AI客户端，包含重试机制、错误处理和多种功能
4. **API端点** - 创建了配置验证和AI测试的REST API端点
5. **自动化脚本** - 提供了环境初始化和配置验证的自动化脚本
6. **文档更新** - 完善了README.md，提供详细的配置指南和故障排除
7. **测试用例** - 编写了全面的单元测试，确保代码质量

### Change Log
**新增文件**：
- `backend/.env.example` - 后端环境变量模板
- `frontend/.env.local.example` - 前端环境变量模板
- `backend/src/app/core/config_validator.py` - 配置验证模块
- `backend/src/app/api/v1/endpoints/config.py` - 配置验证API端点
- `backend/src/app/api/v1/endpoints/test.py` - AI服务测试API端点
- `scripts/setup.sh` - 环境初始化脚本
- `scripts/validate-config.sh` - 配置验证脚本
- `backend/tests/test_config_validator.py` - 配置验证测试
- `backend/tests/test_zhipu_client.py` - 智谱AI客户端测试

**修改文件**：
- `backend/src/app/services/zhipu_client.py` - 增强智谱AI客户端功能
- `backend/src/app/main.py` - 集成启动时配置验证
- `backend/src/app/api/v1/__init__.py` - 注册新的API端点
- `README.md` - 添加完整的环境配置说明

### File List
**新建文件**：
- C:\data_agent\backend\.env.example
- C:\data_agent\frontend\.env.local.example
- C:\data_agent\backend\src\app\core\config_validator.py
- C:\data_agent\backend\src\app\api\v1\endpoints\config.py
- C:\data_agent\backend\src\app\api\v1\endpoints\test.py
- C:\data_agent\scripts\setup.sh
- C:\data_agent\scripts\validate-config.sh
- C:\data_agent\backend\tests\test_config_validator.py
- C:\data_agent\backend\tests\test_zhipu_client.py

**修改文件**：
- C:\data_agent\backend\src\app\services\zhipu_client.py
- C:\data_agent\backend\src\app\main.py
- C:\data_agent\backend\src\app\api\v1\__init__.py
- C:\data_agent\README.md

### Agent Model Used
- Claude Code (Sonnet 4.5)

### Status
- ready_for_review

## 参考文档
reference_documents:
  - "PRD V4 - 第 4 部分：技术假设"
  - "PRD V4 - 第 5 部分：LLM 依赖 (Zhipu API)"
  - "Architecture V4 - 第 3 部分：技术栈"
  - "Architecture V4 - 第 13 部分：开发工作流"
  - "Architecture V4 - 第 17 部分：编码标准"