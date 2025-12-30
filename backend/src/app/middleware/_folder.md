# [MIDDLEWARE] 中间件层

## [MODULE]
**模块名称**: 中间件层
**职责**: 请求拦截、租户上下文注入、跨域处理
**类型**: FastAPI Middleware

## [BOUNDARY]
**输入**:
- HTTP请求 (Request)
- 响应 (Response)

**输出**:
- 修改后的请求/响应
- 上下文变量

## [PROTOCOL]
1. 在请求处理前后执行逻辑
2. 租户上下文自动注入
3. CORS处理
4. 请求日志记录

## [STRUCTURE]
```
middleware/
├── __init__.py
└── tenant_context.py       # 租户上下文中间件
```

## [LINK]
**上游依赖**:
- [../core/auth.py](../core/auth.py) - 认证信息提取
- [../data/models.py](../data/models.py) - 租户模型

**下游依赖**:
- [../api/](../api/_folder.md) - API路由使用上下文
- [../services/](../services/_folder.md) - 服务层访问租户信息

**调用方**:
- [../../main.py](../../main.py) - 应用注册中间件

## [STATE]
- ContextVar: 租户上下文变量 (异步本地存储)

## [THREAD-SAFE]
是 - 使用 ContextVar 隔离

## [SIDE-EFFECTS**
- 上下文变量设置
- 响应头修改
