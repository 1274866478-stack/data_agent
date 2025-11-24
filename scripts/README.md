# Scripts 脚本工具

本目录包含Data Agent V4项目的实用脚本工具。

---

## 📋 脚本列表

### 1. 端口冲突检测 (check-ports)

检查Docker Compose所需端口是否被占用,防止启动失败。

**支持平台:**
- ✅ Linux/macOS: `check-ports.sh`
- ✅ Windows: `check-ports.ps1`
- ✅ 跨平台: `check-ports.py` (需要Python 3.6+)

**检查的端口:**
| 端口 | 服务 |
|------|------|
| 3000 | Frontend (Next.js) |
| 8004 | Backend (FastAPI) |
| 5432 | PostgreSQL |
| 9000 | MinIO API |
| 9001 | MinIO Console |
| 8001 | ChromaDB |

**使用方法:**

```bash
# Linux/macOS
chmod +x scripts/check-ports.sh
./scripts/check-ports.sh

# Windows PowerShell
.\scripts\check-ports.ps1

# Python (跨平台)
python scripts/check-ports.py
```

**输出示例:**

```
==========================================
Data Agent V4 - 端口冲突检测
==========================================

✓ 端口 3000 可用 - Frontend (Next.js)
✗ 端口 5432 已被占用 - PostgreSQL
  占用进程: PID 1234 (postgres)
✓ 端口 8001 可用 - ChromaDB
✓ 端口 8004 可用 - Backend (FastAPI)
✓ 端口 9000 可用 - MinIO API
✓ 端口 9001 可用 - MinIO Console

==========================================
✗ 发现 1 个端口冲突
```

**解决端口冲突:**

**方法1: 停止占用端口的进程**
```bash
# Linux/macOS
kill <PID>

# Windows
Stop-Process -Id <PID>
```

**方法2: 使用自定义端口映射**

1. 复制override示例文件:
```bash
cp docker-compose.override.yml.example docker-compose.override.yml
```

2. 编辑 `docker-compose.override.yml`,修改端口映射:
```yaml
services:
  db:
    ports:
      - "5433:5432"  # 使用5433代替5432
```

3. 启动Docker Compose (会自动合并配置):
```bash
docker-compose up -d
```

---

### 2. 密钥生成 (generate_keys.py)

生成安全的密钥用于MinIO、JWT等服务。

**使用方法:**
```bash
python scripts/generate_keys.py
```

**输出:**
- MinIO Access Key (16字符)
- MinIO Secret Key (32字符)
- JWT Secret Key (64字符)

---

### 3. 配置验证 (validate_config.py)

验证环境变量配置是否正确。

**使用方法:**
```bash
python scripts/validate_config.py
```

**检查项:**
- 必需环境变量是否设置
- 密钥强度是否符合要求
- 数据库连接字符串格式
- API密钥有效性

---

## 🔧 开发工作流

### 启动开发环境

```bash
# 1. 检查端口冲突
python scripts/check-ports.py

# 2. 如果有冲突,解决冲突或创建override配置

# 3. 启动Docker服务
docker-compose up -d

# 4. 验证服务状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f
```

### 停止开发环境

```bash
# 停止所有服务
docker-compose down

# 停止并删除卷(清理数据)
docker-compose down -v
```

---

## 📝 最佳实践

### 1. 启动前检查

**始终在启动Docker前运行端口检测:**
```bash
python scripts/check-ports.py && docker-compose up -d
```

### 2. 使用Override配置

**不要直接修改 `docker-compose.yml`**

创建 `docker-compose.override.yml` 进行本地定制:
```yaml
# docker-compose.override.yml
services:
  frontend:
    ports:
      - "3001:3000"  # 自定义端口
    environment:
      - DEBUG=true   # 额外环境变量
```

### 3. 自动化脚本

**在package.json或Makefile中集成:**

```json
{
  "scripts": {
    "prestart": "python scripts/check-ports.py",
    "start": "docker-compose up -d",
    "stop": "docker-compose down"
  }
}
```

或创建 `Makefile`:
```makefile
.PHONY: check start stop

check:
	python scripts/check-ports.py

start: check
	docker-compose up -d

stop:
	docker-compose down
```

---

## 🐛 故障排查

### 问题: 脚本无法执行

**Linux/macOS:**
```bash
# 添加执行权限
chmod +x scripts/check-ports.sh
```

**Windows:**
```powershell
# 如果PowerShell脚本被阻止
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 问题: Python脚本缺少依赖

```bash
# 安装psutil以获取进程信息
pip install psutil

# 或安装所有后端依赖
cd backend
pip install -r requirements.txt
```

### 问题: 端口检测不准确

某些情况下,端口可能被防火墙或其他网络工具占用但检测不到。

**手动检查端口:**
```bash
# Linux/macOS
lsof -i :3000
netstat -an | grep 3000

# Windows
netstat -ano | findstr :3000
Get-NetTCPConnection -LocalPort 3000
```

---

## 📚 相关文档

- [Docker Compose文档](../docker-compose.yml)
- [环境变量配置](.env.example)
- [开发指南](../README.md)

---

**最后更新:** 2025-11-17

