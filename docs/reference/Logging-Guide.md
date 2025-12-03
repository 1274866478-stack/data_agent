# 日志记录指南

Data Agent V4使用结构化日志系统,确保日志格式统一、易于解析和分析。

---

## 📋 目录

- [日志系统概述](#日志系统概述)
- [使用方法](#使用方法)
- [日志级别](#日志级别)
- [结构化日志](#结构化日志)
- [性能监控](#性能监控)
- [最佳实践](#最佳实践)
- [常见错误](#常见错误)

---

## 🔧 日志系统概述

### 核心组件

- **StructuredFormatter**: JSON格式日志输出
- **RequestLogger**: API请求日志记录
- **performance_logger**: 性能监控上下文管理器
- **get_logger()**: 获取日志记录器

### 日志输出

- **控制台**: 开发环境使用结构化JSON,生产环境使用简单格式
- **文件**: `logs/app.log` - 所有日志的JSON格式记录

---

## 🚀 使用方法

### 基础用法

```python
from src.app.core.logging import get_logger

logger = get_logger(__name__)

# 记录不同级别的日志
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

### 带上下文的日志

```python
logger.info(
    "用户登录成功",
    extra={
        "event_type": "user_login",
        "user_id": "user_123",
        "ip_address": "192.168.1.1",
        "timestamp": datetime.now().isoformat()
    }
)
```

### 记录异常

```python
try:
    risky_operation()
except Exception as e:
    logger.error(
        f"操作失败: {str(e)}",
        exc_info=True,  # 包含完整的堆栈跟踪
        extra={
            "event_type": "operation_error",
            "operation": "risky_operation",
            "error_type": type(e).__name__
        }
    )
```

---

## 📊 日志级别

### 级别说明

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| **DEBUG** | 详细的调试信息 | 变量值、函数调用 |
| **INFO** | 一般信息 | 操作成功、状态变更 |
| **WARNING** | 警告信息 | 配置缺失、性能问题 |
| **ERROR** | 错误信息 | 操作失败、异常 |
| **CRITICAL** | 严重错误 | 系统崩溃、数据丢失 |

### 使用示例

```python
# DEBUG - 调试信息
logger.debug(f"处理数据: {data}")

# INFO - 正常操作
logger.info("数据源连接成功", extra={"data_source_id": ds_id})

# WARNING - 潜在问题
logger.warning("API调用接近速率限制", extra={"remaining": 10})

# ERROR - 错误但可恢复
logger.error("文件上传失败", exc_info=True)

# CRITICAL - 严重错误
logger.critical("数据库连接池耗尽", extra={"pool_size": 0})
```

---

## 📝 结构化日志

### JSON格式输出

所有日志自动格式化为JSON:

```json
{
  "timestamp": "2025-01-15T10:30:00.123456",
  "level": "INFO",
  "logger": "app.services.tenant",
  "message": "租户创建成功",
  "module": "tenant_service",
  "function": "create_tenant",
  "line": 42,
  "app_name": "Data Agent",
  "app_version": "1.0.0",
  "event_type": "tenant_created",
  "tenant_id": "user_123",
  "email": "user@example.com"
}
```

### 自定义字段

使用`extra`参数添加自定义字段:

```python
logger.info(
    "数据分析完成",
    extra={
        "event_type": "analysis_complete",
        "tenant_id": tenant_id,
        "data_source_id": ds_id,
        "rows_processed": 1000,
        "duration_ms": 1500,
        "result_count": 42
    }
)
```

---

## ⏱️ 性能监控

### 使用performance_logger

```python
from src.app.core.logging import performance_logger

# 方式1: 上下文管理器
with performance_logger("database_query"):
    result = await db.execute(query)

# 方式2: 自定义logger
with performance_logger("complex_operation", logger=custom_logger):
    process_data()
```

### 输出示例

```json
// 操作开始
{
  "timestamp": "2025-01-15T10:30:00.000000",
  "level": "INFO",
  "message": "Starting operation: database_query",
  "event_type": "operation_start",
  "operation": "database_query"
}

// 操作完成
{
  "timestamp": "2025-01-15T10:30:01.500000",
  "level": "INFO",
  "message": "Operation completed: database_query in 1.500s",
  "event_type": "operation_end",
  "operation": "database_query",
  "duration_ms": 1500
}
```

---

## ✅ 最佳实践

### 1. 使用get_logger获取logger

```python
# ✅ 正确
from src.app.core.logging import get_logger
logger = get_logger(__name__)

# ❌ 错误 - 不要直接使用logging
import logging
logger = logging.getLogger(__name__)
```

### 2. 使用有意义的消息

```python
# ✅ 正确 - 描述性消息
logger.info("租户创建成功", extra={"tenant_id": tenant_id})

# ❌ 错误 - 模糊消息
logger.info("成功")
```

### 3. 包含上下文信息

```python
# ✅ 正确 - 包含关键上下文
logger.error(
    "数据源连接失败",
    extra={
        "data_source_id": ds_id,
        "db_type": "postgresql",
        "error_code": "CONNECTION_TIMEOUT"
    }
)

# ❌ 错误 - 缺少上下文
logger.error("连接失败")
```

### 4. 使用event_type分类

```python
# 使用event_type便于日志分析
logger.info(
    "API请求完成",
    extra={
        "event_type": "api_request",  # 事件类型
        "method": "POST",
        "path": "/api/v1/tenants",
        "status_code": 201
    }
)
```

### 5. 避免敏感信息

```python
# ✅ 正确 - 脱敏处理
logger.info(
    "用户认证成功",
    extra={
        "user_id": user_id,
        "email": mask_email(email)  # user@example.com -> u***@example.com
    }
)

# ❌ 错误 - 记录敏感信息
logger.info(f"用户密码: {password}")  # 永远不要记录密码!
```

### 6. 使用性能监控

```python
# ✅ 正确 - 监控关键操作
with performance_logger("vector_search"):
    results = await chromadb.query(...)

# ❌ 错误 - 手动计算时间
start = time.time()
results = await chromadb.query(...)
logger.info(f"查询耗时: {time.time() - start}s")
```

---

## ❌ 常见错误

### 1. 使用print()

```python
# ❌ 错误 - 不要使用print
print("处理完成")

# ✅ 正确 - 使用logger
logger.info("处理完成")
```

### 2. 字符串拼接

```python
# ❌ 错误 - 字符串拼接
logger.info("用户 " + user_id + " 登录成功")

# ✅ 正确 - 使用f-string和extra
logger.info(f"用户登录成功", extra={"user_id": user_id})
```

### 3. 过度日志

```python
# ❌ 错误 - 循环中记录过多日志
for item in items:
    logger.debug(f"处理项目: {item}")  # 可能产生数千条日志

# ✅ 正确 - 批量记录
logger.info(f"开始处理 {len(items)} 个项目")
# ... 处理 ...
logger.info(f"处理完成", extra={"processed": len(items)})
```

### 4. 忽略异常信息

```python
# ❌ 错误 - 丢失堆栈跟踪
try:
    risky_operation()
except Exception as e:
    logger.error(f"错误: {str(e)}")

# ✅ 正确 - 包含堆栈跟踪
try:
    risky_operation()
except Exception as e:
    logger.error(f"错误: {str(e)}", exc_info=True)
```

---

## 📚 相关资源

- [日志系统实现](../src/app/core/logging.py)
- [配置审计日志](../src/app/core/config_audit.py)
- [Python logging文档](https://docs.python.org/3/library/logging.html)

---

**最后更新:** 2025-11-17

