# 🚀 快速重启和验收指南

## ✅ 已完成的修复

1. ✅ **文件上传Fallback逻辑** - 修复了MinIO失败时的本地存储
2. ✅ **Agent工具本地文件Fallback** - 增强了文件读取能力
3. ✅ **Docker卷持久化** - 改为本地目录映射 `./data_storage:/app/uploads`
4. ✅ **本地存储目录** - 已创建 `./data_storage` 目录

---

## 🔄 重启后端服务（应用代码修复）

### 方法1：使用容器名称（推荐）

```bash
docker restart dataagent-backend
```

### 方法2：使用容器ID

```bash
docker restart d2dd585b36d8
```

### 方法3：使用docker-compose

```bash
docker-compose restart backend
```

### 方法4：完全重启（如果需要重新加载配置）

```bash
# 停止服务
docker-compose down

# 重新启动（会应用新的卷映射配置）
docker-compose up -d
```

---

## ✅ 验证修复是否生效

### 1. 检查后端服务状态

```bash
# 查看容器状态
docker ps | grep backend

# 查看日志，确认服务正常启动
docker logs -f dataagent-backend

# 应该看到：
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. 检查卷映射

```bash
# 检查容器挂载点
docker inspect dataagent-backend | grep -A 10 Mounts

# 应该看到：
# "Source": "/path/to/data_agent/data_storage"
# "Destination": "/app/uploads"
```

### 3. 测试文件上传（MinIO正常）

```bash
# 创建测试文件
echo "name,age,city" > test.csv
echo "Alice,25,Beijing" >> test.csv
echo "Bob,30,Shanghai" >> test.csv

# 上传文件（替换 YOUR_TENANT_ID 为实际租户ID）
curl -X POST "http://localhost:8004/api/v1/data-sources/upload?tenant_id=YOUR_TENANT_ID" \
  -F "file=@test.csv" \
  -F "name=测试数据源" \
  -F "db_type=csv"

# 检查响应，应该返回成功，包含 file_info
```

### 4. 测试文件上传（MinIO失败Fallback）

```bash
# 停止MinIO服务
docker-compose stop storage

# 上传文件（应该Fallback到本地）
curl -X POST "http://localhost:8004/api/v1/data-sources/upload?tenant_id=YOUR_TENANT_ID" \
  -F "file=@test.csv" \
  -F "name=测试数据源Fallback" \
  -F "db_type=csv"

# 验证文件已保存到本地
ls -la ./data_storage/data-sources/YOUR_TENANT_ID/

# 应该看到上传的文件（如：xxx.csv）
```

### 5. 测试Agent读取文件

```bash
# 通过前端或API使用Agent查询数据
# 例如：查询"这个文件有多少行数据？"
# 验证Agent能正确读取文件并返回真实数据，而不是幻觉数据（如"John Doe"）
```

### 6. 验证持久化

```bash
# 重启容器
docker restart dataagent-backend

# 检查文件是否仍然存在
ls -la ./data_storage/data-sources/YOUR_TENANT_ID/

# 再次使用Agent查询，验证文件仍然可访问
```

---

## 🎯 验收标准检查清单

- [ ] 后端服务正常启动，无错误日志
- [ ] 卷映射正确：`./data_storage` → `/app/uploads`
- [ ] MinIO正常时，文件上传到MinIO成功
- [ ] MinIO失败时，文件保存到 `./data_storage/data-sources/` 成功
- [ ] Agent能正确读取文件并返回真实数据（不是幻觉数据）
- [ ] 容器重启后，文件仍然存在且可访问
- [ ] 本地目录 `./data_storage/` 中有上传的文件

---

## 🔧 常见问题排查

### 问题1：容器重启后找不到文件

**检查**：
```bash
# 1. 检查卷映射是否正确
docker inspect dataagent-backend | grep -A 10 Mounts

# 2. 检查本地目录是否存在
ls -la ./data_storage/

# 3. 检查容器内目录
docker exec dataagent-backend ls -la /app/uploads/
```

### 问题2：权限错误

**解决**：
```bash
# Windows: 确保目录可写
# Linux/Mac: 调整权限
chmod -R 755 ./data_storage
```

### 问题3：Agent仍然生成幻觉数据

**检查**：
```bash
# 1. 查看Agent日志
docker logs dataagent-backend | grep -i "analyze_dataframe\|SYSTEM ERROR"

# 2. 检查文件是否真的存在
docker exec dataagent-backend ls -la /app/uploads/data-sources/

# 3. 检查数据库中的路径格式
# 连接数据库，查看 data_source_connections 表中的 connection_string
```

---

## 📝 下一步

修复完成后，系统应该能够：

1. ✅ 正常上传文件到MinIO
2. ✅ MinIO失败时自动Fallback到本地存储
3. ✅ Agent能正确读取文件（从MinIO或本地）
4. ✅ 文件持久化存储，容器重启不丢失
5. ✅ AI不会生成幻觉数据，而是返回真实数据或明确错误

如果所有验收标准都通过，说明修复成功！🎉

