# AI助手假设数据库结构问题 - 诊断报告

## 问题描述

用户询问"销售部有多少员工"时,AI助手回答:
> "我们可以假设存在一个部门表(departments)和一个员工表(employees)..."

然后生成了错误的SQL查询,导致执行失败并重复显示错误信息。

## 根本原因

通过运行`backend/scripts/check_data_sources.py`诊断脚本,发现了以下问题:

### 1. 租户不匹配

**数据库中的数据源:**
- `chatbi_test_data` (xlsx) - 租户: `dev-tenant-001` - 状态: ACTIVE
- `ChatBI测试数据库` (postgresql) - 租户: `default_tenant` - 状态: ACTIVE

**用户当前租户:** `dev-tenant-001`

**问题:** 
- 用户的租户(`dev-tenant-001`)下只有一个Excel数据源,没有PostgreSQL数据源
- PostgreSQL数据源属于`default_tenant`,不属于当前用户
- 因此,`_get_data_sources_context()`函数无法获取到PostgreSQL的schema信息
- AI没有看到任何数据库schema,所以只能"假设"数据库结构

### 2. 数据源类型过滤

代码只处理`db_type == "postgresql"`的数据源:
```python
if ds.db_type == "postgresql":
    adapter = PostgreSQLAdapter()
    schema_info = await adapter.get_schema(connection_string)
```

Excel数据源(`db_type == "xlsx"`)被跳过,不会生成schema信息。

## 解决方案

### ✅ 方案1: 为当前租户添加PostgreSQL数据源(推荐 - 已实现前端支持!)

**前端已更新!** 现在支持通过UI添加PostgreSQL连接:

1. 登录前端应用(使用`dev-tenant-001`租户)
2. 进入"数据源管理"页面
3. 点击"添加数据源"按钮
4. **选择"数据库连接"标签页** (新功能!)
5. 填写表单:
   - 数据源名称: 例如 "ChatBI测试数据库"
   - 数据库类型: 选择 "PostgreSQL"
   - 连接字符串: `postgresql://user:password@localhost:5432/chatbi_test`
6. 点击"创建数据源"
7. 等待连接测试完成并激活数据源

**连接字符串示例:**
```
postgresql://username:password@host:port/database

# 本地数据库示例
postgresql://postgres:password@localhost:5432/chatbi_test

# 远程数据库示例
postgresql://user:pass@192.168.1.100:5432/mydb
```

### 方案2: 切换到default_tenant租户

如果您想使用现有的PostgreSQL数据源,需要切换到`default_tenant`租户。

### 方案3: 修改现有PostgreSQL数据源的租户

在数据库中将PostgreSQL数据源的`tenant_id`从`default_tenant`改为`dev-tenant-001`:

```sql
UPDATE data_source_connections
SET tenant_id = 'dev-tenant-001'
WHERE id = '5de0bf75-71cb-4c38-b958-a6f1057ba729';
```

## 已完成的改进

虽然根本原因是租户不匹配,但我们已经完成了以下改进,使系统更加健壮:

### 0. **前端UI改进 - 支持PostgreSQL连接** (🆕 新增!)

**修改文件:** `frontend/src/components/data-sources/DataSourceForm.tsx`

**改进内容:**
- 添加了标签页切换功能,支持"数据库连接"和"文件上传"两种方式
- 数据库连接表单包含:
  - 数据源名称输入
  - 数据库类型选择(PostgreSQL/MySQL/SQLite)
  - 连接字符串输入(带示例提示)
  - 表单验证和错误提示
- 保留了原有的文件上传功能
- 使用Tabs组件提供更好的用户体验

**效果:**
- 用户现在可以直接在前端UI中添加PostgreSQL数据库连接
- 不再需要手动修改数据库或使用API工具
- 支持多种数据库类型(PostgreSQL/MySQL/SQLite)

### 1. 增强Schema信息在Prompt中的可见性

- 添加了明确的步骤,要求AI在生成SQL前先仔细阅读schema
- 使用醒目的标记(🔴🔴🔴、🔥)强调必须严格使用schema中的列名
- 列举了常见错误模式作为警示

### 2. 改进SQL修复逻辑

- 修复成功时,完全替换原始错误的SQL,只显示修复后的SQL和结果
- 修复失败时,只显示一次最终错误,不重复显示中间错误
- 同时支持流式和非流式响应

### 3. 增强无数据源时的提示

当没有数据源时,AI现在会明确告知用户:
```
❌ 绝对不要假设或猜测数据库结构
❌ 不要说"我们可以假设存在一个XXX表"
✅ 正确的回答方式: 提示用户先添加数据源
```

## 测试步骤

1. **添加PostgreSQL数据源到当前租户**
   ```bash
   # 使用前端UI或API添加数据源
   ```

2. **重启后端服务**
   ```bash
   docker-compose restart backend
   ```

3. **测试查询**
   - 询问: "销售部有多少员工"
   - 预期: AI应该基于实际schema生成正确的SQL,或者如果表不存在,明确告知用户

4. **验证Schema获取**
   - 检查后端日志,确认schema信息被成功获取
   - 日志应该显示: `Data sources context retrieved for tenant dev-tenant-001, length: XXX`

## 相关文件

- `backend/src/app/api/v1/endpoints/llm.py` - LLM endpoint和schema获取逻辑
- `backend/scripts/check_data_sources.py` - 数据源诊断脚本
- `backend/docs/SQL_AUTO_FIX_IMPROVEMENTS.md` - SQL修复功能改进文档

## 总结

**问题根源:** 租户不匹配导致无法获取PostgreSQL schema
**立即解决:** 为`dev-tenant-001`租户添加PostgreSQL数据源
**长期改进:** 已完成的prompt和错误处理改进将使系统更加健壮

---

**诊断时间:** 2025-11-30
**诊断工具:** `backend/scripts/check_data_sources.py`

