# Docker 卷持久化修复指南

## 🔍 问题分析

**当前状态**：
- `docker-compose.yml` 使用命名卷 `backend_uploads:/app/uploads`
- 命名卷已提供持久化，但文件存储在Docker内部，不易访问和调试

**修复方案**：
- 改为本地目录映射 `./data_storage:/app/uploads`
- 文件直接存储在项目目录中，易于访问、备份和调试

---

## 📋 迁移步骤

### 步骤1：停止容器（如果正在运行）

```bash
docker-compose down
```

### 步骤2：迁移现有数据（如果有）

如果之前已经有文件上传到命名卷中，需要先迁移数据：

```bash
# 1. 创建临时容器访问命名卷
docker volume inspect data_agent_backend_uploads

# 2. 创建本地目录
mkdir -p ./data_storage

# 3. 从命名卷复制数据到本地目录（如果需要）
# 注意：如果命名卷中没有重要数据，可以跳过此步骤
docker run --rm \
  -v data_agent_backend_uploads:/source \
  -v $(pwd)/data_storage:/target \
  alpine sh -c "cp -r /source/* /target/ 2>/dev/null || true"
```

### 步骤3：更新 docker-compose.yml

✅ **已完成**：`docker-compose.yml` 已更新为使用本地目录映射

**变更内容**：
```yaml
# 修改前
- backend_uploads:/app/uploads  # 命名卷

# 修改后
- ./data_storage:/app/uploads  # 本地目录映射
```

### 步骤4：重新启动服务

```bash
# 重新构建并启动（如果需要）
docker-compose up -d --build

# 或者只重启后端服务
docker-compose restart backend
```

### 步骤5：验证配置

```bash
# 检查卷映射是否正确
docker inspect dataagent-backend | grep -A 10 Mounts

# 检查本地目录是否存在
ls -la ./data_storage

# 测试上传文件后，检查文件是否出现在本地目录
ls -la ./data_storage/data-sources/
```

---

## 🚀 最终验收流程

### 1. 重启后端服务（应用代码修复）

```bash
# 方法1：使用容器名称
docker restart dataagent-backend

# 方法2：使用容器ID（如果知道）
docker restart d2dd585b36d8

# 方法3：使用docker-compose
docker-compose restart backend
```

### 2. 验证代码修复已生效

```bash
# 检查后端日志，确认服务正常启动
docker logs -f dataagent-backend

# 应该看到类似信息：
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. 测试文件上传（MinIO正常情况）

```bash
# 准备测试文件
echo "name,age" > test.csv
echo "Alice,25" >> test.csv
echo "Bob,30" >> test.csv

# 上传文件（替换 YOUR_TENANT_ID）
curl -X POST "http://localhost:8004/api/v1/data-sources/upload?tenant_id=YOUR_TENANT_ID" \
  -F "file=@test.csv" \
  -F "name=测试数据源" \
  -F "db_type=csv"

# 检查响应，应该返回成功
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

# 应该看到上传的文件
```

### 5. 测试Agent读取文件

```bash
# 通过前端或API使用Agent查询数据
# 验证Agent能正确读取文件并返回真实数据，而不是幻觉数据
```

### 6. 验证持久化

```bash
# 重启容器
docker-compose restart backend

# 检查文件是否仍然存在
ls -la ./data_storage/data-sources/YOUR_TENANT_ID/

# 再次使用Agent查询，验证文件仍然可访问
```

---

## ✅ 验收标准

- [ ] 后端服务正常启动，无错误日志
- [ ] MinIO正常时，文件上传到MinIO成功
- [ ] MinIO失败时，文件保存到 `./data_storage/data-sources/` 成功
- [ ] Agent能正确读取文件并返回真实数据（不是幻觉数据）
- [ ] 容器重启后，文件仍然存在且可访问
- [ ] 本地目录 `./data_storage/` 中有上传的文件

---

## 🔧 故障排查

### 问题1：权限错误

**症状**：上传文件时出现权限错误

**解决方案**：
```bash
# 确保本地目录有正确权限
chmod -R 755 ./data_storage

# 或者在Windows上，确保目录可写
```

### 问题2：文件找不到

**症状**：Agent报告文件不存在

**检查步骤**：
```bash
# 1. 检查文件是否在本地目录
ls -la ./data_storage/data-sources/

# 2. 检查容器内文件
docker exec dataagent-backend ls -la /app/uploads/data-sources/

# 3. 检查数据库中的路径
# 连接数据库，查看 data_source_connections 表中的 connection_string
```

### 问题3：MinIO和本地文件不一致

**症状**：MinIO中有文件，但本地没有

**说明**：
- 这是正常现象，因为文件可能只上传到MinIO
- Agent会优先从MinIO下载，失败时才Fallback到本地
- 如果需要同步，可以手动从MinIO下载文件到本地

---

## 📝 注意事项

1. **数据备份**：
   - 定期备份 `./data_storage/` 目录
   - 建议添加到 `.gitignore`（如果包含敏感数据）

2. **目录结构**：
   ```
   ./data_storage/
   └── data-sources/
       └── {tenant_id}/
           └── {file_id}.{ext}
   ```

3. **清理策略**：
   - 定期清理旧文件
   - 考虑实现文件生命周期管理

4. **生产环境**：
   - 考虑使用更可靠的存储方案（如云存储）
   - 实现文件备份和恢复机制

---

## 🎯 总结

✅ **修复完成**：
- 代码修复：文件上传Fallback逻辑
- 代码修复：Agent工具本地文件Fallback
- 配置修复：Docker卷持久化映射

✅ **预期效果**：
- 文件持久化存储，容器重启不丢失
- 文件易于访问和调试
- Agent能正确读取文件，不会生成幻觉数据

