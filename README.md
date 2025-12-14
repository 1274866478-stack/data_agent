# Data Agent V4 (SaaS MVP)

Multi-tenant SaaS platform for intelligent data analysis powered by AI.

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.8+ (for local development)
- PostgreSQL 14+ (for local development)

### 🔧 Development Mode (No Authentication Required)

**Good News!** In development mode, you can start using the application immediately without configuring Clerk authentication.

The application will automatically use a development token for API calls. This is perfect for:
- ✅ Local development and testing
- ✅ Feature development
- ✅ Bug fixing
- ✅ Learning the codebase

**Note**: Production deployment requires proper Clerk authentication setup.

### 🔒 Security Configuration (Important)

**⚠️ CRITICAL: Before running for the first time, you MUST configure secure environment variables!**

#### Quick Setup (Recommended)

1. **Copy the environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Generate strong keys automatically**:
   ```bash
   python scripts/generate_keys.py --save
   ```
   This will create a `.env.generated` file with cryptographically secure keys.

3. **Copy generated keys to `.env`**:
   - Open `.env.generated` and copy the generated keys
   - Paste them into your `.env` file
   - Set your ZhipuAI API key: `ZHIPUAI_API_KEY=your_api_key_here`

4. **Verify security configuration**:
   ```bash
   python scripts/security_audit.py
   ```
   You should see "✅ STRONG" status for all keys.

#### Manual Setup (Not Recommended)

If you prefer to generate keys manually:

```bash
# Generate SECRET_KEY (64 characters)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Generate MINIO_ACCESS_KEY (32 characters)
python -c "import secrets; print(secrets.token_urlsafe(24))"

# Generate MINIO_SECRET_KEY (64 characters)
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Security Requirements**:
- `SECRET_KEY`: Minimum 64 characters, mixed case + digits + special chars
- `MINIO_ACCESS_KEY`: Minimum 16 characters, alphanumeric
- `MINIO_SECRET_KEY`: Minimum 32 characters, mixed complexity
- `ZHIPUAI_API_KEY`: Valid API key from https://open.bigmodel.cn/

📖 **For detailed security guidelines, see [docs/SECURITY.md](docs/SECURITY.md)**

### Start the Application

```bash
docker-compose up -d
```

This will start:
- Frontend (Next.js): http://localhost:3000
- Backend API (FastAPI): http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Stop the Application

```bash
docker-compose down
```

## 📁 Project Structure

```
data-agent-v4/
├── frontend/           # Next.js 14+ frontend application
│   ├── src/
│   │   ├── app/       # App Router pages and layouts
│   │   ├── components/ # Reusable React components
│   │   └── lib/       # Utility functions and configurations
│   ├── public/        # Static assets
│   └── package.json   # Node.js dependencies
├── backend/           # FastAPI backend application
│   ├── src/
│   │   ├── api/       # API routes and endpoints
│   │   ├── core/      # Core configuration and utilities
│   │   ├── models/    # Database models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic services
│   │   └── main.py    # FastAPI application entry point
│   ├── tests/         # Test files
│   └── requirements.txt # Python dependencies
├── Agent/             # LangGraph SQL Agent (集成)
│   ├── sql_agent.py   # Agent 主程序
│   ├── config.py      # 配置管理（支持后端配置集成）
│   ├── models.py      # 数据模型
│   ├── chart_service.py # 图表生成服务
│   └── README.md      # Agent 使用文档
├── docs/              # Project documentation
│   ├── prd-v4.md      # Product Requirements Document
│   ├── architecture-v4.md # Technical Architecture
│   └── stories/       # User stories and development tasks
└── docker-compose.yml # Docker Compose configuration
```

## 🛠️ Development Setup

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```

## 🏗️ Architecture

Data Agent V4 follows a modern multi-tenant SaaS architecture:

- **Frontend**: Next.js 14+ with App Router, TypeScript, Tailwind CSS
- **Backend**: FastAPI with async/await, SQLAlchemy ORM, Pydantic validation
- **Database**: PostgreSQL with multi-tenant isolation
- **Authentication**: JWT-based authentication with tenant isolation
- **AI Agent**: LangGraph SQL Agent with DeepSeek LLM for natural language queries
- **MCP Protocol**: Model Context Protocol for database and chart generation
- **Deployment**: Docker containers with Docker Compose orchestration

### 🤖 SQL Agent Integration

Data Agent V4 includes an integrated LangGraph SQL Agent that enables natural language database queries:

- **LLM Provider**: DeepSeek (default) with fallback to Zhipu AI
- **Agent Framework**: LangGraph for multi-step reasoning
- **Database Access**: MCP (Model Context Protocol) for PostgreSQL
- **Chart Generation**: ECharts MCP server for data visualization
- **API Endpoint**: `/api/v1/query` for natural language queries

See [Agent/README.md](Agent/README.md) for detailed Agent documentation.

## 📚 Documentation

- [Product Requirements Document](docs/prd-v4.md)
- [Technical Architecture](docs/architecture-v4.md)
- [Development Stories](docs/stories/)
- [SQL Agent Documentation](Agent/README.md)
- [API Documentation](http://localhost:8000/docs) (when running)

## 🔧 Environment Configuration

### 环境变量配置概述

Data Agent V4 使用分层环境变量管理，确保配置的安全性和可维护性：

- **根目录** `.env` - 全局配置
- **后端** `backend/.env` - 后端服务专用配置
- **前端** `frontend/.env.local` - 前端应用配置

### 环境变量模板文件

项目提供了完整的配置模板：

- `.env.example` - 根目录配置模板
- `backend/.env.example` - 后端配置模板
- `frontend/.env.local.example` - 前端配置模板

### 快速环境配置

#### 方法 1: 使用初始化脚本 (推荐)

```bash
# 运行环境初始化脚本
chmod +x scripts/setup.sh
./scripts/setup.sh
```

初始化脚本将：
- ✅ 创建必要的目录结构
- ✅ 从模板创建环境变量文件
- ✅ 安装前后端依赖
- ✅ 启动 Docker 服务
- ✅ 初始化数据库
- ✅ 创建 MinIO 存储桶
- ✅ 验证配置完整性

#### 方法 2: 手动配置

1. **复制环境变量模板**
```bash
# 根目录配置
cp .env.example .env

# 后端配置
cp backend/.env.example backend/.env

# 前端配置
cp frontend/.env.local.example frontend/.env.local
```

2. **配置必需的环境变量**

**根目录 `.env` 文件**：
```bash
# 数据库配置 (更新密码)
DATABASE_URL=postgresql://postgres:your_secure_password@localhost:5432/dataagent

# MinIO 配置 (更新访问密钥)
MINIO_ACCESS_KEY=your_strong_minio_access_key
MINIO_SECRET_KEY=your_strong_minio_secret_key_at_least_16_chars

# DeepSeek API 配置 (推荐，默认 LLM 提供商，用于 SQL Agent)
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_DEFAULT_MODEL=deepseek-chat

# 智谱 AI API 密钥 (可选，备用 LLM 提供商)
ZHIPUAI_API_KEY=your_zhipu_api_key_here

# 应用配置
ENVIRONMENT=development
DEBUG=true
```

**前端 `frontend/.env.local` 文件**：
```bash
# 后端 API 地址
NEXT_PUBLIC_API_URL=http://localhost:8004/api/v1

# 应用配置
NEXT_PUBLIC_APP_NAME=Data Agent V4
NEXT_PUBLIC_ENVIRONMENT=development
```

### 关键配置说明

#### 1. DeepSeek API 配置（默认 LLM 提供商）

DeepSeek 是项目的默认 LLM 提供商，用于 SQL Agent 和智能查询功能。

获取 DeepSeek API 密钥：
1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/)
2. 注册账号并登录
3. 创建 API 密钥
4. 配置到环境变量中

```bash
# DeepSeek API 配置（推荐，默认 LLM 提供商）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_DEFAULT_MODEL=deepseek-chat
```

**注意**：
- `DEEPSEEK_API_KEY` 是必需的，用于 SQL Agent 功能
- 如果未设置 DeepSeek API 密钥，系统将自动回退到智谱 AI 或 OpenRouter
- API 密钥长度至少 20 个字符

#### 2. 智谱 AI API 配置（可选，备用 LLM 提供商）

获取智谱 API 密钥：
1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册账号并实名认证
3. 创建 API 密钥
4. 配置到环境变量中

```bash
ZHIPUAI_API_KEY=sk-xxxxxxxxxxxxxxxxxx
```

#### 3. 安全配置

**生成强密码**：
```python
import secrets
print("SECRET_KEY:", secrets.token_urlsafe(32))
print("MINIO_ACCESS_KEY:", secrets.token_urlsafe(16))
print("MINIO_SECRET_KEY:", secrets.token_urlsafe(24))
```

**密码要求**：
- `MINIO_ACCESS_KEY`: 最少 8 个字符，不能使用默认值
- `MINIO_SECRET_KEY`: 最少 16 个字符，不能使用默认值
- `SECRET_KEY`: 使用随机生成的强密码

#### 4. 数据库配置

```bash
# 开发环境
DATABASE_URL=postgresql://postgres:password@localhost:5432/dataagent

# 生产环境 (示例)
DATABASE_URL=postgresql://username:strong_password@db-host:5432/production_db
```

### 端口配置

| 服务 | 端口 | 描述 |
|------|------|------|
| 前端应用 | 3000 | Next.js 应用 |
| 后端API | 8004 | FastAPI 服务 |
| PostgreSQL | 5432 | 数据库 |
| MinIO API | 9000 | 对象存储 API |
| MinIO Console | 9001 | 对象存储管理界面 |
| ChromaDB | 8001 | 向量数据库 |

### 配置验证

#### 方法 1: 使用验证脚本 (推荐)

```bash
# 运行配置验证脚本
chmod +x scripts/validate-config.sh
./scripts/validate-config.sh
```

#### 方法 2: 使用 API 端点

```bash
# 全面配置验证
curl http://localhost:8004/api/v1/config/validate

# 单个服务验证
curl -X POST http://localhost:8004/api/v1/config/validate \
  -H "Content-Type: application/json" \
  -d '{"service_name": "database"}'

# 智谱 AI 连接测试
curl -X POST http://localhost:8004/api/v1/test/zhipu
```

#### 方法 3: 使用 API 文档

访问 http://localhost:8004/docs 查看完整的 API 文档和交互式测试界面。

### 故障排除

#### 常见配置问题

1. **端口冲突**
```bash
# 检查端口占用
lsof -i :3000
lsof -i :8004

# 修改 docker-compose.yml 中的端口映射
```

2. **权限问题**
```bash
# 设置脚本执行权限
chmod +x scripts/*.sh

# 设置目录权限
chmod -R 755 backend/uploads
```

3. **依赖安装失败**
```bash
# 清理并重新安装前端依赖
cd frontend
rm -rf node_modules package-lock.json
npm install

# 重新安装后端依赖
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

4. **数据库连接失败**
```bash
# 检查数据库容器状态
docker ps | grep postgres

# 查看数据库日志
docker logs dataagent-postgres
```

### 生产环境配置

生产环境需要额外的安全配置：

1. **环境变量安全**
- 使用强密码
- 定期轮换密钥
- 不要在代码中硬编码敏感信息

2. **网络安全**
- 使用 HTTPS
- 配置防火墙
- 限制数据库访问

3. **监控和日志**
- 启用结构化日志
- 配置错误监控
- 设置性能监控

### 配置文件参考

完整的配置示例和说明请参考：
- [后端配置模板](backend/.env.example)
- [前端配置模板](frontend/.env.local.example)
- [Docker Compose 配置](docker-compose.yml)

## 🧪 Testing

### Frontend Tests
```bash
cd frontend
npm test
```

### Backend Tests
```bash
cd backend
pytest
```

## 📦 Deployment

### Production Deployment

1. Update environment variables for production
2. Build and deploy containers:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Environment-Specific Configurations

- Development: `docker-compose.yml`
- Staging: `docker-compose.staging.yml`
- Production: `docker-compose.prod.yml`

## 🔧 Troubleshooting

### Chat Send Button Not Working

**Symptom**: Input works but send button is disabled or shows "401 Unauthorized" error.

**Solution**: This has been fixed in the latest version. The application now uses development tokens automatically in development mode.

**Steps to verify**:
1. Refresh the browser page
2. Check for the yellow debug panel above the input box
3. Verify it shows "开发环境：使用开发token" in the console
4. The send button should now work

**Details**: See [Bug Fix Documentation](docs/bugfix/2025-11-20-chat-send-button-auth-issue.md)

### Backend Container Unhealthy

**Symptom**: `docker ps` shows backend container as "unhealthy"

**Solution**:
```bash
# Restart the backend container
docker-compose restart backend

# Check logs
docker logs dataagent-backend --tail 50

# If issues persist, rebuild
docker-compose up backend --build -d
```

### MinIO Connection Issues

**Symptom**: Backend logs show "Failed to resolve 'minio'"

**Solution**:
```bash
# Ensure all services are running
docker-compose up -d

# Check MinIO status
docker ps | grep minio

# Restart MinIO if needed
docker-compose restart storage
```

### Frontend Not Loading

**Symptom**: Cannot access http://localhost:3000

**Solution**:
```bash
# Check if frontend is running
docker ps | grep frontend

# Restart frontend
docker-compose restart frontend

# For local development
cd frontend
npm install
npm run dev
```

### Database Connection Errors

**Symptom**: "Database connection failed" errors

**Solution**:
```bash
# Check PostgreSQL status
docker ps | grep postgres

# Restart database
docker-compose restart db

# Verify database is healthy
docker exec -it dataagent-postgres pg_isready -U postgres
```

### API Test Tool

Use the included test tool to verify backend API:
```bash
# Open in browser
file:///path/to/data_agent/test-api.html
```

This tool tests:
- ✅ Health check endpoint
- ✅ Chat API without authentication
- ✅ Chat API with development token

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📚 Documentation

- [Main Documentation](CLAUDE.md) - Project overview and AI assistant guide
- [Backend Documentation](backend/CLAUDE.md) - Backend architecture and API
- [Frontend Documentation](frontend/CLAUDE.md) - Frontend components and state management
- [Bug Fix Records](docs/bugfix/) - Detailed bug fix documentation
- [Changelog](CHANGELOG.md) - Version history and changes

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the project repository
- Check the [documentation](docs/)
- Review existing [issues](../../issues)

---

**Data Agent V4** - Empowering intelligent data analysis for modern businesses.