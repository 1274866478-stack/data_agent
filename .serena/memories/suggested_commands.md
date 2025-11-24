# Data Agent V4 开发命令指南

## 项目启动和停止
```bash
# 完整项目启动 (推荐)
docker-compose up -d

# 完整项目停止
docker-compose down

# 停止并删除数据卷 (清理数据)
docker-compose down -v

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f
docker-compose logs -f backend  # 查看特定服务日志
```

## 环境配置
```bash
# 复制环境变量模板
cp .env.example .env

# 生成安全密钥 (推荐)
python scripts/generate_keys.py --save

# 验证配置完整性
python scripts/validate_config.py

# 检查端口冲突
python scripts/check-ports.py

# 项目完整初始化
chmod +x scripts/setup.sh
./scripts/setup.sh
```

## 后端开发
```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 本地开发启动
uvicorn src.app.main:app --reload --port 8004

# 运行测试
pytest tests/ -v --cov

# 运行特定测试
pytest tests/api/v1/test_health.py -v

# 代码质量检查
black src/
isort src/
flake8 src/
mypy src/

# 数据库迁移
alembic revision --autogenerate -m "描述变更"
alembic upgrade head
```

## 前端开发
```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 本地开发启动
npm run dev

# 生产构建
npm run build

# 启动生产服务器
npm start

# 运行测试
npm test
npm run test:coverage
npm run test:e2e

# 代码质量检查
npm run lint
npm run type-check

# 代码格式化 (如果配置了Prettier)
npx prettier --write src/
```

## 数据库管理
```bash
# 连接到PostgreSQL容器
docker exec -it dataagent-postgres psql -U postgres -d dataagent

# 备份数据库
docker exec dataagent-postgres pg_dump -U postgres dataagent > backup.sql

# 恢复数据库
docker exec -i dataagent-postgres psql -U postgres dataagent < backup.sql

# 查看数据库连接
docker exec -it dataagent-postgres psql -U postgres -d dataagent -c "\l"
```

## MinIO对象存储管理
```bash
# 访问MinIO控制台
# 浏览器打开: http://localhost:9001
# 默认用户名: minioadmin
# 默认密码: minioadmin (请修改为强密码)

# 测试MinIO连接
curl http://localhost:8004/api/v1/health/services
```

## ChromaDB向量数据库
```bash
# 访问ChromaDB (如果需要)
# 浏览器打开: http://localhost:8001

# 测试ChromaDB连接
curl http://localhost:8004/api/v1/test/chromadb
```

## API测试
```bash
# 健康检查
curl http://localhost:8004/health

# API版本信息
curl http://localhost:8004/api/v1/

# 测试智谱AI连接 (需要配置API密钥)
curl -X POST http://localhost:8004/api/v1/test/zhipu

# 配置验证
curl http://localhost:8004/api/v1/config/validate
```

## 服务监控和调试
```bash
# 查看所有服务资源使用情况
docker stats

# 查看特定服务容器信息
docker inspect dataagent-backend
docker inspect dataagent-frontend

# 进入容器调试
docker exec -it dataagent-backend bash
docker exec -it dataagent-frontend sh

# 重启特定服务
docker-compose restart backend
docker-compose restart frontend

# 查看网络配置
docker network ls
docker network inspect dataagent_dataagent-network
```

## 日志管理
```bash
# 实时查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db

# 查看最近的日志 (最后100行)
docker-compose logs --tail=100

# 查看特定时间范围的日志
docker-compose logs --since="2023-01-01T00:00:00" --until="2023-01-02T00:00:00"
```

## 性能测试和压力测试
```bash
# 安装Apache Bench (如果未安装)
# Ubuntu/Debian: sudo apt-get install apache2-utils
# macOS: brew install ab

# API性能测试
ab -n 100 -c 10 http://localhost:8004/health

# 使用curl进行简单性能测试
time curl http://localhost:8004/api/v1/
```

## 安全和配置审计
```bash
# 运行安全配置审计
python scripts/security_audit.py

# 测试日志净化
python scripts/test_log_sanitization.py

# 检查代码注释
python scripts/check-comments.py

# 验证Docker配置
python scripts/validate-docker-config.py
```

## 故障排除命令
```bash
# 检查端口占用
netstat -tulpn | grep :3000  # Linux
lsof -i :3000               # macOS
netstat -ano | findstr :3000 # Windows

# 清理Docker资源
docker system prune -a

# 重新构建镜像
docker-compose build --no-cache

# 强制重新创建容器
docker-compose up -d --force-recreate
```

## 开发工具快捷方式
```bash
# 创建Makefile (可选)
cat > Makefile << 'EOF'
.PHONY: start stop check test clean

start:
	python scripts/check-ports.py && docker-compose up -d

stop:
	docker-compose down

check:
	python scripts/validate_config.py

test:
	cd backend && pytest tests/ -v --cov
	cd frontend && npm test

clean:
	docker-compose down -v
	docker system prune -a
EOF

# 使用make命令
make start   # 启动服务
make stop    # 停止服务
make test    # 运行测试
make clean   # 清理环境
```

## 生产部署相关
```bash
# 生产环境构建
docker-compose -f docker-compose.prod.yml build

# 生产环境启动
docker-compose -f docker-compose.prod.yml up -d

# 查看生产环境日志
docker-compose -f docker-compose.prod.yml logs -f

# 备份生产数据
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres dataagent > prod_backup.sql
```