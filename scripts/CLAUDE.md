[根目录](../CLAUDE.md) > **scripts**

# Scripts - 自动化脚本模块

**模块类型**: 自动化工具和部署脚本
**支持平台**: Windows, Linux, macOS
**最后更新**: 2025-11-17 12:06:42

---

## 模块职责

Scripts模块提供Data Agent V4的自动化工具和部署脚本：

- 🐳 **Docker管理**: 容器启动、停止、监控
- 🔧 **环境配置**: 初始化脚本、配置验证
- 📊 **系统监控**: 资源监控、健康检查
- 🛠️ **开发工具**: 端口检查、服务验证

---

## 脚本分类

### Windows批处理脚本 (.bat)
- `start-services.bat` - 启动所有Docker服务
- `docker-stop.bat` - 停止Docker服务
- `check-ports.bat` - 检查端口占用情况
- `monitor-resources.bat` - 监控系统资源
- `verify-services.bat` - 验证服务状态

### Shell脚本 (.sh)
- `setup.sh` - 项目初始化和环境设置
- `docker-start.sh` - Docker服务启动
- `docker-stop.sh` - Docker服务停止
- `validate-config.sh` - 配置验证脚本

### Python脚本 (.py)
- `validate-docker-config.py` - Docker配置验证
- `check-docker.py` - Docker环境检查
- `init-db.sql` - 数据库初始化脚本

---

## 核心脚本说明

### 项目初始化 (`setup.sh`)
```bash
# 功能：
# 1. 创建必要目录结构
# 2. 从模板创建环境变量文件
# 3. 安装前后端依赖
# 4. 启动Docker服务
# 5. 初始化数据库
# 6. 创建MinIO存储桶
# 7. 验证配置完整性

# 使用方法：
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 服务启动 (`start-services.bat`)
```batch
@echo off
echo Starting Data Agent V4 services...
docker-compose up -d
echo Services started. Check http://localhost:3000
```

### 配置验证 (`validate-config.sh`)
```bash
# 验证：
# 1. 环境变量完整性
# 2. Docker服务连接
# 3. API服务响应
# 4. 数据库连接
# 5. AI服务可用性

./scripts/validate-config.sh
```

### 端口检查 (`check-ports.bat`)
```batch
@echo off
echo Checking port availability...
netstat -an | findstr :3000
netstat -an | findstr :8004
netstat -an | findstr :5432
```

---

## 使用指南

### 新环境部署
1. 运行 `scripts/setup.sh` 进行完整初始化
2. 验证 `scripts/validate-config.sh` 配置正确性
3. 使用 `scripts/start-services.bat` 启动服务

### 日常开发
- 启动: `docker-compose up -d`
- 停止: `docker-compose down`
- 重启: `docker-compose restart`
- 查看日志: `docker-compose logs -f`

### 故障排除
- 检查端口: `scripts/check-ports.bat`
- 验证服务: `scripts/verify-services.bat`
- 监控资源: `scripts/monitor-resources.bat`

---

## 变更记录 (Changelog)

| 日期 | 版本 | 变更类型 | 描述 | 作者 |
|------|------|----------|------|------|
| 2025-11-17 | V4.1 | 🆕 新增 | 脚本模块AI上下文文档创建 | AI Assistant |
| 2025-11-16 | V4.1 | 🔧 优化 | 添加配置验证和资源监控脚本 | John |
| 2025-11-15 | V4.0 | 🔄 重构 | 适配Docker Compose V4配置 | John |

---

**⚡ 开发提示**: 脚本提供了自动化的项目管理工作流程，建议使用脚本而不是手动Docker命令，确保环境一致性和操作规范性。**