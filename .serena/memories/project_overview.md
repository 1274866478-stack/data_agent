# Data Agent V4 项目概览

## 项目基本信息
- **项目名称**: Data Agent V4 - 多租户SaaS数据智能分析平台
- **版本**: V4.1 (SaaS MVP)
- **最后更新**: 2025-11-17
- **技术栈**: Next.js 14 + FastAPI + PostgreSQL + Docker
- **架构模式**: 微服务 + 多租户SaaS

## 核心价值主张
- 🔐 **多租户数据隔离**: 企业级安全性与租户隔离
- 🧠 **AI驱动分析**: 基于智谱(Zhipu)AI的智能数据洞察
- 📊 **自带数据库**: 用户安全连接外部PostgreSQL数据源
- 📚 **知识库增强**: PDF/Word文档上传与向量检索
- 🚀 **云原生架构**: Docker容器化，支持快速云部署

## 模块结构
```
data-agent-v4/
├── backend/           # FastAPI后端服务 (Python 3.8+)
├── frontend/          # Next.js前端应用 (TypeScript)
├── docs/             # 项目文档和规范
├── scripts/          # 自动化脚本和部署工具
└── docker-compose.yml # 容器编排配置
```

## 关键服务端口
| 服务 | 端口 | 描述 |
|------|------|------|
| 前端应用 | 3000 | Next.js 应用 |
| 后端API | 8004 | FastAPI 服务 |
| PostgreSQL | 5432 | 主数据库 |
| MinIO API | 9000 | 对象存储 API |
| MinIO Console | 9001 | 存储管理界面 |
| ChromaDB | 8001 | 向量数据库 |

## 关键依赖
### 后端核心依赖
- fastapi==0.111.0 (Web框架)
- sqlalchemy==2.0.31 (ORM)
- zhipuai==2.0.1 (AI服务)
- minio==7.2.0 (对象存储)
- chromadb==0.4.18 (向量数据库)

### 前端核心依赖
- next==14.2.5 (React框架)
- typescript==5.5.3 (类型系统)
- tailwindcss==3.4.6 (CSS框架)
- zustand==5.0.8 (状态管理)

## 必需环境变量
- `ZHIPUAI_API_KEY`: 智谱AI API密钥 (必需)
- `DATABASE_URL`: PostgreSQL连接字符串
- `MINIO_ACCESS_KEY`: MinIO访问密钥 (至少32字符)
- `MINIO_SECRET_KEY`: MinIO秘密密钥 (至少64字符)
- `SECRET_KEY`: JWT签名密钥 (至少64字符)

## 开发工作流

### 快速启动
```bash
# 1. 配置环境变量
cp .env.example .env
python scripts/generate_keys.py --save

# 2. Docker方式启动 (推荐)
docker-compose up -d

# 3. 验证服务状态
curl http://localhost:8004/health
```

### 本地开发
```bash
# 后端开发
cd backend
uvicorn src.app.main:app --reload --port 8004

# 前端开发
cd frontend
npm run dev
```

### 测试命令
```bash
# 后端测试
cd backend
pytest tests/ -v --cov

# 前端测试
cd frontend
npm test
```

### 代码质量检查
```bash
# 后端格式化和检查
cd backend
black src/
isort src/
flake8 src/
mypy src/

# 前端检查
cd frontend
npm run lint
npm run type-check
```

## 核心功能特性

### 多租户认证
- **托管认证**: 集成Clerk认证服务
- **租户隔离**: 基于tenant_id的完全数据隔离
- **JWT验证**: API级别的身份验证和授权

### 数据管理
- **外部数据库**: 支持PostgreSQL连接字符串导入
- **文档上传**: MinIO对象存储，支持PDF/Word
- **向量化**: ChromaDB向量数据库，支持语义检索

### AI分析引擎
- **LLM服务**: 智谱GLM-4-flash模型集成
- **多轮对话**: 支持上下文理解的对话式分析
- **结果溯源**: XAI可解释推理路径

## 项目文档
- [PRD文档](docs/prd-v4.md) - 产品需求文档
- [架构文档](docs/architecture-v4.md) - 技术架构设计
- [开发故事](docs/stories/) - 用户故事和开发任务
- [API文档](http://localhost:8004/docs) - FastAPI自动生成的API文档

## 常见问题
1. **端口冲突**: 使用 `python scripts/check-ports.py` 检查端口占用
2. **密钥安全**: 使用 `python scripts/generate_keys.py` 生成强密钥
3. **配置验证**: 使用 `python scripts/validate_config.py` 验证配置
4. **服务监控**: 使用 `/api/v1/health` 端点检查服务状态

## 安全注意事项
- 所有API操作都需要租户隔离 (tenant_id过滤)
- 敏感信息通过环境变量管理，不硬编码在代码中
- 生产环境必须使用强密码和HTTPS
- 定期轮换API密钥和访问密钥