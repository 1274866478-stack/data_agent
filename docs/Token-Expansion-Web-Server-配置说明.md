# Token Expansion - Web Server 超时配置说明

## 概述

为了支持生成 8000+ tokens 的长文本输出（可能需要 1-2 分钟），我们已将 Web 服务器的超时设置提升至 300 秒（5分钟）。

## 已更新的文件

### 1. Dockerfile (`backend/Dockerfile`)

#### 开发环境
```dockerfile
# 修改前
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# 修改后
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug", "--timeout-keep-alive", "300"]
```

#### 生产环境
```dockerfile
# 修改前
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# 修改后
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--timeout-keep-alive", "300"]
```

### 2. 主启动文件 (`backend/src/app/main.py`)

```python
# 修改前
uvicorn.run(
    "main:app", host="0.0.0.0", port=8000, reload=settings.debug, log_level="info"
)

# 修改后
uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=8000,
    reload=settings.debug,
    log_level="info",
    timeout_keep_alive=300  # 5分钟，支持长文本生成
)
```

### 3. 启动脚本

#### `scripts/start-backend-local.bat`
```batch
# 修改前
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8004

# 修改后
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8004 --timeout-keep-alive 300
```

#### `scripts/start-all-local.bat`
```batch
# 修改前
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8004

# 修改后
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8004 --timeout-keep-alive 300
```

### 4. 文档更新

#### `backend/README.md`
```bash
# 开发模式
uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --reload --timeout-keep-alive 300

# 生产模式（使用 Gunicorn）
gunicorn src.app.main:app -w 4 -k uvicorn.workers.UvicornWorker --timeout 300
```

## Uvicorn 超时参数说明

### `--timeout-keep-alive`

- **作用**：设置保持连接的超时时间（秒）
- **默认值**：5 秒
- **新值**：300 秒（5分钟）
- **说明**：这个参数控制服务器在关闭空闲连接之前等待的时间。对于长文本生成，需要更长的超时时间。

### 其他相关参数

- `--timeout-graceful-shutdown`：优雅关闭的超时时间（默认 30 秒）
- `--timeout-notify`：通知关闭的超时时间（默认 30 秒）

## Gunicorn 超时参数说明

如果使用 Gunicorn 作为生产服务器：

```bash
gunicorn src.app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --timeout 300 \
  --graceful-timeout 30
```

- `--timeout`：工作进程超时时间（秒），默认 30 秒
- `--graceful-timeout`：优雅关闭超时时间（秒），默认 30 秒

## 验证配置

### 1. 检查 Docker 容器配置

```bash
# 查看运行中的容器
docker ps

# 查看容器的启动命令
docker inspect dataagent-backend | grep -A 10 "Cmd"
```

### 2. 检查进程参数

```bash
# 在容器内检查 uvicorn 进程
docker exec dataagent-backend ps aux | grep uvicorn
```

### 3. 测试长文本生成

发送一个会生成长文本的查询，观察是否在 300 秒内完成：

```bash
curl -X POST http://localhost:8004/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "请生成一份详细的数据分析报告，包含多个图表的完整 ECharts 配置"
  }'
```

## 注意事项

### 1. 资源消耗

- **内存**：更长的超时时间意味着连接会保持更长时间，可能增加内存使用
- **并发连接**：如果有很多长时间运行的请求，可能会占用更多连接资源

### 2. 负载均衡器配置

如果使用负载均衡器（如 Nginx、HAProxy），也需要配置相应的超时设置：

#### Nginx 配置示例
```nginx
proxy_read_timeout 300s;
proxy_connect_timeout 300s;
proxy_send_timeout 300s;
```

#### HAProxy 配置示例
```haproxy
timeout connect 300s
timeout client 300s
timeout server 300s
```

### 3. 客户端超时

确保客户端（前端、API 调用方）的超时设置也足够长：

```javascript
// 前端示例（Axios）
const axios = require('axios');

const api = axios.create({
  baseURL: 'http://localhost:8004/api/v1',
  timeout: 300000,  // 5分钟（毫秒）
});
```

## 故障排查

### 问题：请求仍然超时

**可能原因**：
1. 负载均衡器或反向代理的超时设置过短
2. 客户端超时设置过短
3. 网络层面的超时

**解决方案**：
1. 检查所有中间件的超时配置
2. 增加客户端的超时时间
3. 检查网络防火墙或代理设置

### 问题：连接被提前关闭

**可能原因**：
1. 反向代理（如 Nginx）的超时设置
2. 云服务提供商的负载均衡器限制

**解决方案**：
1. 更新反向代理配置
2. 联系云服务提供商调整超时限制

## 回退方案

如果需要回退到之前的超时设置：

### Dockerfile
```dockerfile
# 回退到默认值（5秒）
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 启动脚本
```bash
# 移除 --timeout-keep-alive 参数
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8004
```

## 完成时间

2025-01-XX

## 相关文档

- [Token Expansion Plan 实施总结](./Token-Expansion-Plan-实施总结.md)
- [Uvicorn 官方文档](https://www.uvicorn.org/settings/)
- [Gunicorn 官方文档](https://docs.gunicorn.org/en/stable/settings.html)

