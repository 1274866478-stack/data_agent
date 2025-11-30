# SQL错误处理改进文档

## 改进概述

本次改进增强了系统对PostgreSQL SQL查询错误的处理能力，特别是针对列名和表名错误的智能提示和自动修复功能。

## 改进内容

### 1. 错误信息解析增强

新增 `_parse_sql_error()` 函数，能够智能解析PostgreSQL错误信息，提取以下关键信息：

- **主要错误信息**：提取简洁的错误描述
- **HINT提示**：提取PostgreSQL数据库的建议信息
- **修复建议**：基于错误类型生成具体的修复建议

#### 示例

**原始错误信息：**
```
(psycopg2.errors.UndefinedColumn) column "department_id" does not exist
LINE 3: WHERE department_id = (SELECT id FROM departments WHERE name...
              ^
HINT:  Perhaps you meant to reference the column "employees.department".
```

**解析后的结果：**
- **主要错误**: `column "department_id" does not exist`
- **提示**: `Perhaps you meant to reference the column "employees.department".`
- **建议**: `请使用列名 department 而不是错误的列名。`

### 2. AI修复提示优化

改进了 `_fix_sql_with_ai()` 函数的提示词，使AI能够更好地理解PostgreSQL的HINT信息：

#### 关键改进点

1. **强调HINT的重要性**
   - 明确告诉AI，PostgreSQL的HINT通常会直接给出正确的列名或表名
   - 提供具体的HINT解读示例

2. **提供修复示例**
   ```
   错误SQL:
   SELECT COUNT(*) FROM employees WHERE department_id = 'Sales'
   
   错误信息:
   column "department_id" does not exist
   HINT: Perhaps you meant to reference the column "employees.department"
   
   修复后的SQL:
   SELECT COUNT(*) FROM employees WHERE department = 'Sales'
   ```

3. **明确修复步骤**
   - 从错误信息中找出问题列名
   - 在HINT中查找正确的列名
   - 在Schema中验证列名存在
   - 替换SQL中的错误列名

### 3. 用户友好的错误提示

改进了错误信息的显示格式，使用户能够更清楚地了解问题所在：

#### 非流式响应

```markdown
❌ **查询执行失败**: column "department_id" does not exist

💡 **提示**: Perhaps you meant to reference the column "employees.department".

💡 **建议**: 请使用列名 `department` 而不是错误的列名。
```

#### 流式响应

同样的错误信息格式，通过SSE流式传输给前端。

### 4. 智能重试机制

系统会自动尝试修复失败的SQL查询：

1. **第一次执行失败** → 调用AI修复SQL
2. **第二次执行失败** → 再次调用AI修复SQL
3. **第三次执行失败** → 显示详细错误信息和修复建议

如果经过重试仍然失败，会显示：
```markdown
❌ **查询执行失败**: column "department_id" does not exist

💡 **提示**: Perhaps you meant to reference the column "employees.department".

*已尝试自动修复 2 次，但仍然失败*

**最后尝试的SQL：**
```sql
SELECT COUNT(*) FROM employees WHERE department = '销售部'
```

💡 **建议**: 请使用列名 `department` 而不是错误的列名。
```

## 技术实现

### 核心函数

#### `_parse_sql_error(error_message: str) -> Dict[str, str]`

解析PostgreSQL错误信息，返回包含以下字段的字典：
- `main_error`: 主要错误信息
- `hint`: PostgreSQL的HINT提示
- `suggestion`: 修复建议

#### `_fix_sql_with_ai(original_sql, error_message, schema_context, original_question) -> Optional[str]`

使用智谱AI修复失败的SQL查询，返回修复后的SQL或None。

### 错误类型支持

- ✅ **列不存在错误** (UndefinedColumn)
- ✅ **表不存在错误** (UndefinedTable)
- ✅ **语法错误** (SyntaxError)
- ✅ **其他PostgreSQL错误**

## 测试

新增测试文件 `backend/tests/test_sql_error_parsing.py`，包含以下测试用例：

1. ✅ 列不存在错误解析
2. ✅ 表不存在错误解析
3. ✅ 简单错误解析

运行测试：
```bash
python backend/tests/test_sql_error_parsing.py
```

## 用户体验改进

### 改进前

```
❌ 查询执行失败: (psycopg2.errors.UndefinedColumn) column "department_id" does not exist
LINE 3: WHERE department_id = (SELECT id FROM departments WHERE name...
              ^
HINT:  Perhaps you meant to reference the column "employees.department".
[SQL: SELECT COUNT(*) as total_employees FROM employees WHERE department_id = ...]

💡 建议: 请检查表名和列名是否正确，或查看数据源的schema信息。
```

### 改进后

```
❌ **查询执行失败**: column "department_id" does not exist

💡 **提示**: Perhaps you meant to reference the column "employees.department".

💡 **建议**: 请使用列名 `department` 而不是错误的列名。
```

## 未来改进方向

1. **支持更多数据库类型**
   - MySQL错误信息解析
   - SQLite错误信息解析

2. **错误模式学习**
   - 记录常见错误模式
   - 建立错误-修复知识库

3. **Schema智能提示**
   - 在错误信息中直接显示相似的列名
   - 使用模糊匹配推荐正确的列名

## 相关文件

- `backend/src/app/api/v1/endpoints/llm.py` - 主要实现文件
- `backend/tests/test_sql_error_parsing.py` - 测试文件
- `backend/docs/SQL_ERROR_HANDLING_IMPROVEMENT.md` - 本文档

## 更新日期

2025-11-30

