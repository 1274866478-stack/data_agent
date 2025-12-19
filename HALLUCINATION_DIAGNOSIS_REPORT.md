# AI幻觉问题诊断报告

## 📋 问题确认

**AI给出的答案完全错误，属于典型的幻觉数据。**

### 验证结果对比

| 项目 | AI声称的 | 实际数据 | 状态 |
|------|---------|---------|------|
| **工作表名** | `users` | `用户表`（中文） | ❌ 错误 |
| **列名** | `name` | `username` | ❌ 错误 |
| **用户数量** | 5个 | 10个 | ❌ 错误 |
| **用户名字** | 张三、李四、王五、赵六、钱七 | 张伟、李娜、王强、刘芳、陈明、<br>赵丽、周杰、吴敏、孙强、郑红 | ❌ 完全错误 |

## 🔍 根本原因分析

### 1. 文件读取失败

从日志分析，Agent可能根本没有成功调用 `analyze_dataframe` 工具，或者工具调用失败但没有返回明确的错误信息。

**可能的原因：**

1. **文件路径问题**
   - 数据库中的 `connection_string` 可能格式不正确
   - 可能是 `file://data-sources/...` 格式，但文件实际上不在MinIO中
   - 或者路径是 `local://...` 格式，但文件不在容器内的预期位置

2. **工作表名称不匹配**
   - AI声称读取了 `users` 工作表
   - 实际工作表名是 `用户表`（中文）
   - 如果Agent没有先调用 `inspect_file` 查看工作表列表，就会使用错误的工作表名

3. **列名不匹配**
   - AI声称有 `name` 列
   - 实际列名是 `username`
   - 如果文件读取失败，AI可能基于常见的数据结构假设生成了错误的列名

### 2. 系统提示词问题

从日志中发现：
```
4. **严禁使用文件工具（inspect_file, analyze_dataframe）**
```

这说明在某些情况下，系统提示词可能错误地禁止了文件工具的使用。但根据 `prompts.py` 的代码，对于文件数据源应该使用文件工具。

**可能的问题：**
- 数据源类型识别错误（将Excel文件识别为SQL数据库）
- 或者Agent没有正确识别数据源类型

### 3. 工具调用失败但未返回错误

即使 `analyze_dataframe` 工具被调用，如果：
- 文件路径不存在
- MinIO下载失败
- 工作表名称错误
- 列名不存在

工具应该返回 `SYSTEM ERROR`，但AI可能忽略了这些错误，直接生成了幻觉数据。

## 🛠️ 需要检查的关键点

### 1. 数据库中的文件路径

需要检查数据库中 `ecommerce_test_data` 数据源的 `connection_string` 字段：

```sql
SELECT id, name, db_type, connection_string, status 
FROM data_source_connections 
WHERE name = 'ecommerce_test_data';
```

**预期格式：**
- MinIO路径：`file://data-sources/{tenant_id}/{file_id}.xlsx`
- 本地路径：`local:///app/uploads/data-sources/{tenant_id}/{file_id}.xlsx`

### 2. Agent工具调用日志

需要检查Agent是否：
1. 调用了 `inspect_file` 查看文件结构
2. 调用了 `analyze_dataframe` 读取数据
3. 如果调用失败，是否返回了 `SYSTEM ERROR`

### 3. 文件实际位置

需要确认文件是否存在于：
- MinIO：`data-sources` bucket
- 容器内：`/app/uploads/data-sources/{tenant_id}/`
- 或者：`/app/data/ecommerce_test_data.xlsx`

## 🔧 修复建议

### 1. 增强日志记录

在 `analyze_dataframe_func` 中添加更详细的日志：

```python
logger.info(f"🔍 [Debug] 开始分析文件: {file_path}")
logger.info(f"🔍 [Debug] 工作表名称: {sheet_name}")
logger.info(f"🔍 [Debug] 查询代码: {query}")
```

### 2. 强制工作表名称验证

在读取Excel文件前，先验证工作表是否存在：

```python
# 读取所有工作表名称
excel_file = pd.ExcelFile(container_file_path)
available_sheets = excel_file.sheet_names
logger.info(f"📋 可用工作表: {available_sheets}")

if sheet_name and sheet_name not in available_sheets:
    logger.error(f"❌ 工作表 '{sheet_name}' 不存在，可用工作表: {available_sheets}")
    return 'SYSTEM ERROR: ...'
```

### 3. 强制列名验证

在查询前验证列是否存在：

```python
if 'name' not in df.columns and 'username' not in df.columns:
    logger.error(f"❌ 未找到 'name' 或 'username' 列，实际列名: {df.columns.tolist()}")
    return 'SYSTEM ERROR: ...'
```

### 4. 增强系统提示词

确保系统提示词明确要求：
- 对于Excel文件，必须先调用 `inspect_file` 查看工作表列表
- 必须使用实际的工作表名称（可能是中文）
- 必须使用实际的列名（可能是 `username` 而不是 `name`）

## 📊 下一步行动

1. **检查数据库中的文件路径**
   ```bash
   docker exec -it <db_container> psql -U dev -d postgres -c "SELECT connection_string FROM data_source_connections WHERE name = 'ecommerce_test_data';"
   ```

2. **检查文件是否存在于容器内**
   ```bash
   docker exec -it dataagent-backend ls -la /app/uploads/data-sources/
   docker exec -it dataagent-backend ls -la /app/data/
   ```

3. **检查MinIO中的文件**
   - 访问MinIO控制台或使用MinIO客户端检查 `data-sources` bucket

4. **查看完整的Agent执行日志**
   - 查找 `analyze_dataframe` 的调用记录
   - 查找文件读取的错误信息

5. **测试修复后的代码**
   - 确保文件路径正确
   - 确保工作表名称正确（使用 `用户表` 而不是 `users`）
   - 确保列名正确（使用 `username` 而不是 `name`）

