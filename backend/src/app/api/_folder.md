# [API] API路由层

## [MODULE]
**模块名称**: API路由层
**职责**: HTTP请求处理、路由定义、请求验证
**类型**: FastAPI Router

## [BOUNDARY]
**输入**:
- HTTP请求 (Request)
- 认证令牌 (JWT/API Key)
- 查询参数 (Query Params)
- 请求体 (Request Body)

**输出**:
- HTTP响应 (Response)
- JSON数据
- 错误响应 (ErrorResponse)

## [PROTOCOL]
1. 路由注册通过 `api/v1/__init__.py` 集中管理
2. 所有业务路由必须包含租户隔离 (tenant_id)
3. 使用 Pydantic 模型进行请求验证
4. 统一错误处理和响应格式

## [STRUCTURE]
```
api/
├── __init__.py           # 路由注册入口
└── v1/
    ├── __init__.py       # V1 API聚合路由
    └── endpoints/        # 具体端点实现
        ├── health.py     # 健康检查 (无需认证)
        ├── tenants.py    # 租户管理
        ├── data_sources.py
        ├── documents.py
        ├── llm.py
        └── ...
```

## [LINK]
**上游依赖**:
- [../core/config.py](../core/config.py) - 配置管理
- [../core/auth.py](../core/auth.py) - 认证授权
- [../middleware/tenant_context.py](../middleware/tenant_context.py) - 租户上下文

**下游依赖**:
- [../services/](../services/_folder.md) - 业务逻辑服务层
- [../data/models.py](../data/models.py) - 数据模型

**调用方**:
- [../../main.py](../../main.py) - FastAPI应用入口

## [STATE]
无状态 - 每个请求独立处理

## [THREAD-SAFE]
是 - FastAPI路由设计为线程安全

## [SIDE-EFFECTS]
- 数据库写入 (通过服务层)
- MinIO文件操作
- LLM API调用
