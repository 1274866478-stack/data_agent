# Data Agent V4 开发工作流程

## 项目启动流程

### 1. 环境准备
```bash
# 检查Docker和Docker Compose是否安装
docker --version
docker-compose --version

# 检查Node.js和Python版本 (本地开发)
node --version  # >= 18.0.0
python --version  # >= 3.8
```

### 2. 快速启动 (推荐)
```bash
# 1. 克隆项目
git clone <repository-url>
cd data-agent-v4

# 2. 配置环境变量
cp .env.example .env
python scripts/generate_keys.py --save

# 3. 设置智谱AI API密钥 (必需)
# 编辑 .env 文件，设置 ZHIPUAI_API_KEY=your_actual_api_key

# 4. 启动所有服务
docker-compose up -d

# 5. 验证服务状态
curl http://localhost:8004/health
```

### 3. 本地开发环境
```bash
# 后端开发
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.app.main:app --reload --port 8004

# 前端开发 (新终端)
cd frontend
npm install
npm run dev
```

## 开发任务流程

### 1. 功能开发流程
```bash
# 1. 创建功能分支
git checkout -b feature/user-authentication

# 2. 后端开发
cd backend
# 添加新的API端点
# 编写测试
pytest tests/api/v1/test_auth.py -v

# 3. 前端开发
cd frontend
# 添加新组件和页面
# 运行测试
npm test

# 4. 集成测试
docker-compose up -d
# 测试完整功能流程

# 5. 代码质量检查
cd backend
black src/ && isort src/ && flake8 src/ && mypy src/
cd frontend
npm run lint && npm run type-check

# 6. 提交代码
git add .
git commit -m "feat(auth): implement user authentication"
git push origin feature/user-authentication
```

### 2. 数据库变更流程
```bash
# 1. 修改模型文件
# 编辑 backend/src/app/data/models.py

# 2. 生成迁移文件
cd backend
alembic revision --autogenerate -m "add user profile table"

# 3. 检查生成的迁移文件
# 编辑 backend/alembic/versions/xxx_add_user_profile.py

# 4. 应用迁移
alembic upgrade head

# 5. 测试数据库变更
python scripts/test_db_migration.py
```

### 3. API开发流程
```bash
# 1. 定义Pydantic模式
# 创建 backend/src/app/schemas/user.py

# 2. 实现业务逻辑服务
# 创建 backend/src/app/services/user_service.py

# 3. 创建API端点
# 创建 backend/src/app/api/v1/endpoints/users.py

# 4. 添加路由注册
# 编辑 backend/src/app/api/v1/__init__.py

# 5. 编写测试
# 创建 tests/api/v1/test_users.py

# 6. 测试API
pytest tests/api/v1/test_users.py -v
curl -X GET http://localhost:8004/api/v1/users
```

## 测试策略

### 1. 后端测试
```bash
# 单元测试
pytest tests/services/test_user_service.py -v

# API集成测试
pytest tests/api/v1/test_users.py -v

# 数据库测试
pytest tests/data/test_models.py -v

# 运行所有测试
pytest tests/ -v --cov

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### 2. 前端测试
```bash
# 单元测试
npm test

# 覆盖率测试
npm run test:coverage

# 端到端测试
npm run test:e2e

# 可视化E2E测试
npm run test:e2e:ui
```

### 3. 集成测试
```bash
# 启动完整环境
docker-compose up -d

# 等待服务就绪
python scripts/wait-for-services.py

# 运行集成测试
pytest tests/integration/ -v

# API健康检查
curl http://localhost:8004/health
curl http://localhost:3000  # 前端
```

## 代码审查检查清单

### 后端审查要点
- [ ] 是否包含适当的类型注解
- [ ] 是否遵循异步编程模式 (async/await)
- [ ] 是否实现租户隔离 (tenant_id过滤)
- [ ] 是否有适当的错误处理和日志记录
- [ ] 是否包含输入验证和安全检查
- [ ] 是否有相应的单元测试
- [ ] 是否通过mypy类型检查

### 前端审查要点
- [ ] 是否使用TypeScript严格类型检查
- [ ] 组件是否可复用和可测试
- [ ] 状态管理是否合理
- [ ] 是否有适当的错误边界
- [ ] 是否包含加载和错误状态
- [ ] 是否响应式设计友好
- [ ] 是否通过ESLint检查

### 通用审查要点
- [ ] 代码是否遵循项目命名规范
- [ ] 是否有适当的文档字符串和注释
- [ ] 是否包含安全敏感信息的泄露
- [ ] 性能是否满足要求
- [ ] 可访问性是否考虑

## 部署流程

### 1. 开发环境部署
```bash
# 启动开发环境
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 2. 生产环境准备
```bash
# 1. 配置生产环境变量
cp .env.example .env.production
# 编辑 .env.production 设置生产环境配置

# 2. 构建生产镜像
docker-compose -f docker-compose.prod.yml build

# 3. 运行安全配置审计
python scripts/security_audit.py

# 4. 验证配置
python scripts/validate_config.py --env=production
```

### 3. 生产部署
```bash
# 1. 停止旧服务
docker-compose -f docker-compose.prod.yml down

# 2. 启动新服务
docker-compose -f docker-compose.prod.yml up -d

# 3. 运行健康检查
curl http://localhost/health

# 4. 验证关键功能
python scripts/smoke_test.py
```

## 监控和维护

### 1. 日志监控
```bash
# 实时查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 使用结构化日志查询
docker-compose logs backend | grep "ERROR"
```

### 2. 性能监控
```bash
# 查看容器资源使用情况
docker stats

# 检查数据库连接
docker exec -it dataagent-postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# 检查API响应时间
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8004/health
```

### 3. 健康检查
```bash
# 全面健康检查
curl http://localhost:8004/api/v1/health/status

# 单个服务检查
curl http://localhost:8004/api/v1/health/database
curl http://localhost:8004/api/v1/health/minio
curl http://localhost:8004/api/v1/health/zhipu

# 配置验证
curl -X POST http://localhost:8004/api/v1/config/validate
```

## 故障排除

### 1. 常见问题诊断
```bash
# 端口冲突检查
python scripts/check-ports.py

# Docker服务状态
docker-compose ps
docker-compose logs --tail=50

# 数据库连接测试
docker exec -it dataagent-postgres pg_isready -U postgres

# MinIO连接测试
curl http://localhost:9000/minio/health/live
```

### 2. 性能问题排查
```bash
# 慢查询检查
docker exec -it dataagent-postgres psql -U postgres -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;"

# 内存使用检查
docker stats --no-stream

# 磁盘空间检查
df -h
docker system df
```

### 3. 安全问题处理
```bash
# 运行安全审计
python scripts/security_audit.py

# 检查密钥强度
python scripts/test_security_config.py

# 查看访问日志
docker-compose logs backend | grep "ERROR\|WARNING"
```

## 发布流程

### 1. 版本发布准备
```bash
# 1. 更新版本号
# 更新 backend/src/app/core/config.py 中的 app_version
# 更新 frontend/package.json 中的 version

# 2. 运行完整测试套件
npm test  # 前端测试
pytest tests/ -v --cov  # 后端测试

# 3. 代码质量检查
npm run lint && npm run type-check  # 前端
black src/ && isort src/ && mypy src/  # 后端

# 4. 构建验证
docker-compose build
docker-compose up -d
python scripts/smoke_test.py
```

### 2. 发布执行
```bash
# 1. 创建发布标签
git tag -a v4.1.0 -m "Release version 4.1.0"
git push origin v4.1.0

# 2. 构建生产镜像
docker-compose -f docker-compose.prod.yml build

# 3. 备份当前数据
docker-compose exec db pg_dump -U postgres dataagent > backup-$(date +%Y%m%d).sql

# 4. 部署新版本
docker-compose -f docker-compose.prod.yml up -d

# 5. 验证部署
python scripts/smoke_test.py
curl http://localhost/health
```

### 3. 发布后监控
```bash
# 监控服务状态
docker-compose ps

# 检查错误日志
docker-compose logs --tail=100 backend | grep "ERROR"

# 监控性能指标
curl http://localhost/api/v1/health/status
```