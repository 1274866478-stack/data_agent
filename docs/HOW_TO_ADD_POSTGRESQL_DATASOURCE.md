# 如何添加PostgreSQL数据源

## 📋 前提条件

1. 前端应用正在运行 (http://localhost:3000)
2. 后端API正在运行 (http://localhost:8004)
3. 您已经登录并有有效的租户ID
4. 您有一个可访问的PostgreSQL数据库

## 🚀 通过前端UI添加(推荐)

### 步骤1: 进入数据源管理页面

1. 登录前端应用
2. 在左侧菜单中点击"数据源管理"
3. 点击右上角的"添加数据源"按钮

### 步骤2: 选择数据库连接

在弹出的表单中,您会看到两个标签页:
- **数据库连接** ← 选择这个!
- 文件上传

点击"数据库连接"标签页。

### 步骤3: 填写连接信息

填写以下字段:

#### 数据源名称 *
```
ChatBI测试数据库
```
或任何您喜欢的名称

#### 数据库类型 *
从下拉菜单中选择:
- **PostgreSQL** ← 选择这个
- MySQL
- SQLite

#### 连接字符串 *
格式: `postgresql://username:password@host:port/database`

**示例:**
```
# 本地数据库
postgresql://postgres:password@localhost:5432/chatbi_test

# 远程数据库
postgresql://user:pass@192.168.1.100:5432/mydb

# 带SSL的连接
postgresql://user:pass@db.example.com:5432/mydb?sslmode=require
```

**您的连接字符串:**
```
postgresql://[用户名]:[密码]@[主机]:[端口]/[数据库名]
```

### 步骤4: 创建数据源

1. 检查所有信息是否正确
2. 点击"创建数据源"按钮
3. 等待系统测试连接
4. 如果连接成功,数据源将被创建并显示在列表中

## 🔧 通过API添加(高级)

如果您更喜欢使用API或需要自动化:

```bash
curl -X POST "http://localhost:8004/api/v1/data-sources/?tenant_id=dev-tenant-001" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ChatBI测试数据库",
    "db_type": "postgresql",
    "connection_string": "postgresql://user:password@localhost:5432/chatbi_test"
  }'
```

## 📊 验证数据源

### 方法1: 通过前端UI

1. 在"数据源管理"页面查看数据源列表
2. 确认新添加的数据源状态为"ACTIVE"
3. 点击数据源查看详细信息

### 方法2: 通过诊断脚本

```bash
python backend/scripts/check_data_sources.py
```

应该看到类似输出:
```
✅ 找到 1 个活跃数据源
   - ChatBI测试数据库 (类型: postgresql, 租户: dev-tenant-001)
```

## 🧪 测试AI查询

添加数据源后,您可以测试AI助手:

1. 进入"AI助手"页面
2. 询问: "销售部有多少员工"
3. AI应该能够:
   - 读取数据库schema
   - 生成正确的SQL查询
   - 执行查询并返回结果

**预期行为:**
- ✅ AI会基于实际的表结构和列名生成SQL
- ✅ 如果表不存在,AI会明确告知而不是假设
- ✅ SQL错误会自动修复(最多2次重试)

## ❌ 常见问题

### 问题1: 连接失败

**错误:** "Connection test failed"

**解决方案:**
1. 检查PostgreSQL服务是否运行
2. 验证连接字符串中的用户名、密码、主机、端口
3. 确认数据库存在
4. 检查防火墙设置
5. 验证PostgreSQL允许远程连接(如果不是localhost)

### 问题2: 租户不匹配

**错误:** AI仍然假设数据库结构

**解决方案:**
1. 运行诊断脚本确认数据源属于正确的租户
2. 检查您当前登录的租户ID
3. 如果租户不匹配,删除数据源并重新创建

### 问题3: Schema获取失败

**错误:** AI没有看到数据库表

**解决方案:**
1. 检查后端日志: `docker-compose logs backend`
2. 确认数据库用户有读取schema的权限
3. 重启后端服务: `docker-compose restart backend`

## 📚 相关文档

- [诊断报告](../backend/docs/DIAGNOSIS_REPORT.md) - 问题根因分析
- [SQL修复改进](../backend/docs/SQL_AUTO_FIX_IMPROVEMENTS.md) - SQL自动修复功能
- [API文档](../backend/docs/API-Documentation.md) - 完整API参考

## 🎉 成功!

如果一切顺利,您现在应该能够:
- ✅ 通过前端UI添加PostgreSQL数据源
- ✅ AI助手能够读取数据库schema
- ✅ AI助手能够生成正确的SQL查询
- ✅ 查询结果正确显示

祝您使用愉快! 🚀

