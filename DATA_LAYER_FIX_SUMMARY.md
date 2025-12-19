# 数据层修复总结

## 修复内容

### 第一步：强制落地逻辑 ✅

**文件**：`backend/src/app/api/v1/endpoints/data_sources.py`

**修复内容**：
1. **强制保存到本地磁盘**：无论MinIO是否成功，都先将文件保存到本地磁盘
2. **统一路径格式**：数据库存储使用容器内绝对路径（`/app/uploads/data-sources/{tenant_id}/{file_id}{ext}`）
3. **确保目录存在**：使用`os.makedirs`确保目录结构存在

**关键代码变更**：
```python
# 🔥 关键修复：无论MinIO是否成功，都先保存到本地磁盘
local_file_path = os.path.join(tenant_upload_dir, f"{file_id}{file_ext}")
with open(local_file_path, "wb") as f:
    f.write(file_content)
logger.info(f"✅ 文件已强制保存到本地: {local_file_path}")

# 数据库存储使用容器内绝对路径
connection_string = local_file_path  # 直接使用容器内绝对路径
```

### 第二步：路径解析桥梁 ✅

**文件**：`backend/src/app/services/agent/tools.py`

**修复内容**：
1. **增强容器内绝对路径验证**：检查文件是否存在
2. **MinIO回退机制**：如果本地文件不存在，尝试从MinIO下载
3. **明确的错误返回**：文件不存在时返回明确的错误信息

**关键代码变更**：
```python
# 2. 容器内绝对路径（如 /app/uploads/data-sources/...）
elif file_path.startswith("/"):
    container_file_path = file_path
    # 🔥 关键修复：验证文件是否存在
    if not os.path.exists(container_file_path):
        # 尝试从MinIO下载或返回错误
        ...
```

### 第三步：基础设施验证 ✅

**文件**：`docker-compose.yml`

**验证结果**：
- ✅ 卷映射已正确配置：`./data_storage:/app/uploads`
- ✅ 清理了未使用的命名卷 `backend_uploads`

## 修复效果

1. **文件强制落地**：上传的文件一定会保存到本地磁盘
2. **路径一致性**：数据库存储的路径与物理文件路径一致
3. **Agent可访问**：Agent可以通过容器内绝对路径找到文件
4. **持久化存储**：文件存储在主机目录`./data_storage`，容器重启不会丢失

## 测试建议

1. **上传测试**：
   - 上传一个Excel文件
   - 检查`./data_storage/data-sources/{tenant_id}/`目录是否有文件
   - 检查数据库中存储的路径是否为容器内绝对路径

2. **Agent访问测试**：
   - 使用Agent查询上传的文件
   - 检查日志，确认文件路径解析正确
   - 确认Agent能成功读取文件内容

3. **持久化测试**：
   - 重启后端容器
   - 确认文件仍然存在
   - 确认Agent仍然能访问文件

