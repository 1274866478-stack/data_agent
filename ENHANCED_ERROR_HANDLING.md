# 增强错误处理与幻觉防护

## 修复内容

### 1. 支持 `local://` 路径前缀（预防性修复）

**位置**：`backend/src/app/services/agent/tools.py:232-250`

虽然当前代码使用容器内绝对路径（如 `/app/uploads/data-sources/...`）存储本地文件，但为了兼容未来可能的 `local://` 前缀格式，已添加支持：

```python
# 1. 本地存储路径（local:///app/uploads/...）
if file_path.startswith("local://"):
    container_file_path = file_path[8:]  # 移除 local:// 前缀
    # 验证路径是否存在，如果不存在则尝试在 /app/data 目录查找
```

### 2. 增强工作表名称验证

**位置**：`backend/src/app/services/agent/tools.py:345-365`

在读取 Excel 文件之前，先验证指定的工作表是否存在：

```python
if sheet_name:
    excel_file = pd.ExcelFile(container_file_path, engine='openpyxl')
    available_sheets = excel_file.sheet_names
    
    if sheet_name not in available_sheets:
        return f'SYSTEM ERROR: Sheet "{sheet_name}" not found. Available sheets: {", ".join(available_sheets)}...'
```

**效果**：
- 如果 Agent 尝试读取不存在的表（如 `users` 而实际是 `用户表`），会立即返回错误
- 错误信息包含所有可用工作表名称，帮助 Agent 选择正确的表

### 3. 增强列名验证

**位置**：`backend/src/app/services/agent/tools.py:365-380`

在 Pandas 查询执行前，检查查询代码中引用的列是否存在：

```python
# 提取查询中引用的列名
column_refs = re.findall(r"df\[['\"]([^'\"]+)['\"]\]|df\.(\w+)|df\[(\w+)\]", query)
referenced_columns = [col for match in column_refs for col in match if col]

if referenced_columns:
    missing_columns = [col for col in referenced_columns if col not in df.columns]
    if missing_columns:
        return f'SYSTEM ERROR: Columns {missing_columns} not found. Available columns: {", ".join(df.columns)}...'
```

**效果**：
- 如果 Agent 尝试访问不存在的列（如 `name` 而实际是 `username`），会立即返回错误
- 错误信息包含所有可用列名，帮助 Agent 选择正确的列

### 4. 增强日志记录

**位置**：`backend/src/app/services/agent/tools.py:354-356`

添加了详细的日志记录：

```python
logger.info(f"✅ 成功读取 Excel 文件，行数: {len(df)}, 列数: {len(df.columns)}")
logger.info(f"📊 Excel文件列名: {list(df.columns)}")
```

**效果**：
- 在 Agent 日志中可以清楚地看到实际读取的文件、工作表、列名
- 便于调试和诊断问题

## 预期效果

### 场景1：工作表名称错误

**之前**：
- Agent 尝试读取 `users` 工作表
- 文件实际只有 `用户表` 工作表
- Agent 可能返回空数据或错误，但继续生成幻觉数据

**现在**：
- Agent 尝试读取 `users` 工作表
- 系统立即返回错误：`Sheet "users" not found. Available sheets: 用户表, ...`
- Agent 必须使用正确的表名或返回错误信息

### 场景2：列名错误

**之前**：
- Agent 尝试访问 `name` 列
- 文件实际只有 `username` 列
- Agent 可能返回空数据或错误，但继续生成幻觉数据

**现在**：
- Agent 尝试访问 `name` 列
- 系统立即返回错误：`Columns ['name'] not found. Available columns: username, ...`
- Agent 必须使用正确的列名或返回错误信息

## 下一步

1. **重启后端服务**以应用修复
2. **重新测试查询**，观察 Agent 是否：
   - 正确识别工作表名称（使用 `inspect_file` 工具）
   - 正确识别列名（从实际数据中读取）
   - 在错误时返回明确的错误信息，而不是生成幻觉数据

## 调试建议

如果问题仍然存在，请检查：

1. **Agent 日志**：
   ```bash
   docker logs dataagent-backend | grep -E "📋|📊|❌|⚠️|✅"
   ```

2. **数据库中的文件路径**：
   ```bash
   docker exec dataagent-postgres psql -U postgres -d dataagent -c "SELECT id, name, db_type, LEFT(_connection_string, 100) as conn_preview FROM data_source_connections WHERE db_type IN ('xlsx', 'xls', 'csv') ORDER BY created_at DESC LIMIT 5;"
   ```

3. **实际文件位置**：
   ```bash
   docker exec dataagent-backend ls -la /app/uploads/data-sources/
   docker exec dataagent-backend ls -la /app/data/
   ```

