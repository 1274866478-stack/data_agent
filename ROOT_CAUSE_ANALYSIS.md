# 根因分析报告：文件上传数据断开与AI幻觉问题

## 执行摘要

**问题描述**：用户上传Excel文件后，AI Agent声称读取了文件，但生成的是虚假/幻觉数据（如"John Doe"、随机数字），而不是真实文件内容。

**根本原因**：Agent工具无法从MinIO成功下载文件，但错误处理机制不完善，导致工具返回空数据或错误时，AI仍然基于不完整信息生成答案。

---

## 1. 数据流分析

### 1.1 文件上传流程

**位置**：`backend/src/app/api/v1/endpoints/data_sources.py:167-291`

```220:244:backend/src/app/api/v1/endpoints/data_sources.py
        storage_path = f"data-sources/{tenant_id}/{file_id}{file_ext}"

        # 上传到 MinIO
        import io
        try:
            upload_success = minio_service.upload_file(
                bucket_name="data-sources",
                object_name=storage_path,
                file_data=io.BytesIO(file_content),
                file_size=file_size,
                content_type=file.content_type or "application/octet-stream"
            )

            if not upload_success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="文件上传到存储服务失败"
                )
        except Exception as e:
            logger.warning(f"MinIO上传失败，使用本地存储: {e}")
            # 如果MinIO不可用，保存到本地临时目录
            storage_path = f"local://{storage_path}"

        # 创建数据源记录
        connection_string = f"file://{storage_path}"
```

**问题1：Fallback逻辑错误**
- 当MinIO上传失败时，代码设置 `storage_path = f"local://{storage_path}"`
- 但随后创建 `connection_string = f"file://{storage_path}"`
- 结果：`connection_string = "file://local://data-sources/..."`（格式错误）
- **影响**：Agent工具无法正确解析此路径

**问题2：本地存储未实现**
- 代码注释说"保存到本地临时目录"，但**实际上没有保存文件到本地**
- 只是修改了路径字符串，文件数据丢失
- **影响**：即使Agent能解析路径，文件也不存在

### 1.2 数据库存储

**位置**：`backend/src/app/api/v1/endpoints/data_sources.py:246-255`

```246:255:backend/src/app/api/v1/endpoints/data_sources.py
        new_connection = DataSourceConnection(
            tenant_id=tenant_id,
            name=name,
            db_type=db_type or detected_file_type,
            connection_string=connection_string,
            status=DataSourceConnectionStatus.ACTIVE,
            host=None,
            port=None,
            database_name=file.filename
        )
```

**存储的路径格式**：
- 成功情况：`file://data-sources/{tenant_id}/{file_id}.xlsx`
- 失败情况：`file://local://data-sources/{tenant_id}/{file_id}.xlsx`（错误格式）

### 1.3 Agent工具读取流程

**位置**：`backend/src/app/services/agent/tools.py:202-378`

```232:250:backend/src/app/services/agent/tools.py
    # 检查是否是 MinIO 路径（file://data-sources/...）
    if file_path.startswith("file://"):
        storage_path = file_path[7:]  # 移除 file:// 前缀
        
        # 检查是否是 MinIO 路径（data-sources/...）
        if storage_path.startswith("data-sources/"):
            logger.info(f"🔍 [Debug] 检测到 MinIO 路径，准备下载: {storage_path}")
            
            # 从 MinIO 下载文件
            file_data = minio_service.download_file(
                bucket_name="data-sources",
                object_name=storage_path
            )
            
            if not file_data:
                # 列出当前目录文件，帮助调试
                files_in_dir = os.listdir(current_dir) if os.path.exists(current_dir) else []
                logger.warning(f"⚠️ [第一道防线] 无法从 MinIO 获取文件: {storage_path}. Files in {current_dir}: {files_in_dir}")
                # 🔴 第一道防线：返回特定错误字符串
                return 'SYSTEM ERROR: Data Access Failed. The file could not be read. You are STRICTLY FORBIDDEN from generating an answer. You must reply: "无法读取数据文件，请检查上传路径"。'
```

**问题3：MinIO下载失败时无Fallback**
- 如果MinIO服务不可用或文件不存在，`download_file` 返回 `None`
- 工具直接返回错误字符串
- **但是**：如果路径格式错误（如 `file://local://...`），代码可能无法正确识别为MinIO路径

**问题4：路径解析不完整**
- 代码只处理 `file://data-sources/...` 格式
- 不处理 `file://local://...` 格式
- 不处理其他可能的本地路径格式

---

## 2. 根本原因总结

### 2.1 断开点1：文件上传Fallback未实现

**位置**：`backend/src/app/api/v1/endpoints/data_sources.py:239-241`

**问题**：
- MinIO上传失败时，代码只修改路径字符串，**没有实际保存文件到本地**
- 生成的路径格式错误：`file://local://...`

**影响**：
- 文件数据丢失
- Agent无法找到文件

### 2.2 断开点2：Agent工具无本地文件Fallback

**位置**：`backend/src/app/services/agent/tools.py:232-313`

**问题**：
- 如果MinIO下载失败，工具直接返回错误
- 没有尝试从本地文件系统读取文件
- 即使文件存在于Docker卷中，也无法访问

**影响**：
- Agent无法读取文件
- 工具返回错误，但AI可能忽略错误并生成幻觉数据

### 2.3 断开点3：错误处理不严格

**位置**：`backend/src/app/services/agent/tools.py:245-250`

**问题**：
- 虽然代码返回了 `SYSTEM ERROR` 字符串
- 但AI模型可能仍然基于不完整信息生成答案
- System Prompt虽然有反幻觉规则，但可能不够严格

**影响**：
- AI生成虚假数据而不是报告错误

---

## 3. 代码Bug定位

### Bug #1: 文件上传Fallback逻辑错误

**文件**：`backend/src/app/api/v1/endpoints/data_sources.py`

**行号**：239-244

**问题代码**：
```python
except Exception as e:
    logger.warning(f"MinIO上传失败，使用本地存储: {e}")
    # 如果MinIO不可用，保存到本地临时目录
    storage_path = f"local://{storage_path}"  # ❌ 只修改字符串，未保存文件

# 创建数据源记录
connection_string = f"file://{storage_path}"  # ❌ 结果：file://local://...
```

**修复方案**：
1. 实际保存文件到本地目录（如 `/app/uploads` 或 `/app/data`）
2. 使用正确的路径格式（如 `local:///app/uploads/...` 或直接使用容器内绝对路径）

### Bug #2: Agent工具缺少本地文件Fallback

**文件**：`backend/src/app/services/agent/tools.py`

**行号**：232-313

**问题代码**：
```python
if not file_data:
    # ❌ 直接返回错误，没有尝试本地文件系统
    return 'SYSTEM ERROR: Data Access Failed...'
```

**修复方案**：
1. 如果MinIO下载失败，尝试从本地文件系统读取
2. 检查Docker卷挂载的目录（如 `/app/uploads`、`/app/data`）
3. 支持多种路径格式

### Bug #3: 路径格式不一致

**问题**：
- 上传时可能生成：`file://local://data-sources/...`
- Agent工具期望：`file://data-sources/...` 或容器内绝对路径

**修复方案**：
- 统一路径格式规范
- 支持路径格式转换和验证

---

## 4. 修复计划

### 4.1 修复文件上传Fallback逻辑

**目标**：确保MinIO失败时，文件实际保存到本地

**步骤**：
1. 在MinIO上传失败时，保存文件到Docker卷挂载的目录
2. 使用正确的路径格式保存到数据库
3. 确保路径在容器内可访问

### 4.2 增强Agent工具的文件读取能力

**目标**：支持从MinIO和本地文件系统读取文件

**步骤**：
1. 添加本地文件系统Fallback逻辑
2. 支持多种路径格式解析
3. 改进错误处理和日志记录

### 4.3 强化错误处理机制

**目标**：确保AI在文件读取失败时不会生成幻觉数据

**步骤**：
1. 验证System Prompt的反幻觉规则
2. 确保工具返回的错误信息被正确处理
3. 添加额外的验证检查

---

## 5. Docker卷映射检查

### 5.1 当前配置

**文件**：`docker-compose.yml`

```62:68:docker-compose.yml
    volumes:
      - ./backend:/app
      # 挂载 Agent 目录到容器根目录，供 agent_service.py 导入 sql_agent 等模块
      - ./Agent:/Agent
      - backend_uploads:/app/uploads
      # 挂载本地 scripts 目录到容器内的 /app/data，供 Agent 读取本地数据文件
      - ./scripts:/app/data
```

**分析**：
- ✅ `backend_uploads:/app/uploads` - 命名卷，用于上传文件
- ✅ `./scripts:/app/data` - 本地目录映射，用于读取数据文件
- ⚠️ **问题**：文件上传到MinIO，不在这些卷中

### 5.2 建议的卷映射

**方案1：使用命名卷存储上传文件**
- 文件保存到 `backend_uploads:/app/uploads`
- 路径格式：`local:///app/uploads/{tenant_id}/{file_id}.xlsx`

**方案2：使用本地目录映射**
- 文件保存到 `./uploads:/app/uploads`
- 路径格式：`local:///app/uploads/{tenant_id}/{file_id}.xlsx`

---

## 6. 修复代码实现

### 6.1 修复文件上传逻辑

**文件**：`backend/src/app/api/v1/endpoints/data_sources.py`

**修改点**：239-244行

### 6.2 修复Agent工具读取逻辑

**文件**：`backend/src/app/services/agent/tools.py`

**修改点**：232-313行

### 6.3 验证System Prompt

**文件**：`backend/src/app/services/agent/prompts.py`

**检查点**：反幻觉规则是否足够严格

---

## 7. 测试验证计划

1. **测试场景1**：MinIO正常，文件上传成功
   - 验证文件能正确上传到MinIO
   - 验证Agent能正确下载和读取文件

2. **测试场景2**：MinIO失败，Fallback到本地
   - 验证文件保存到本地目录
   - 验证路径格式正确
   - 验证Agent能从本地读取文件

3. **测试场景3**：MinIO服务在Agent运行时不可用
   - 验证Agent能Fallback到本地文件系统
   - 验证不会生成幻觉数据

---

## 8. 总结

**核心问题**：
1. 文件上传Fallback未实现（只修改字符串，未保存文件）
2. Agent工具缺少本地文件系统Fallback
3. 路径格式不一致导致解析失败

**修复优先级**：
1. 🔴 **高优先级**：修复文件上传Fallback逻辑，确保文件实际保存
2. 🔴 **高优先级**：增强Agent工具的文件读取能力，支持本地Fallback
3. 🟡 **中优先级**：统一路径格式规范
4. 🟡 **中优先级**：强化错误处理机制

**预期效果**：
- 文件上传失败时，文件保存到本地，Agent能正常读取
- MinIO不可用时，Agent能从本地文件系统读取
- AI不会生成幻觉数据，而是正确报告错误

