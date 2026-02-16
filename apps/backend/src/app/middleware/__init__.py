"""
# [MIDDLEWARE] 中间件模块初始化

## [HEADER]
**文件名**: __init__.py
**职责**: 导出所有中间件组件 - 组织和暴露middleware模块的所有中间件和工具函数
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - Middleware模块初始化

## [INPUT]
- **from .tenant_context import**: 从tenant_context.py模块导入所有中间件和工具

## [OUTPUT]
### 导出的中间件和工具
- **TenantContext** - 租户上下文管理器类
- **tenant_context** - 全局租户上下文实例
- **get_current_tenant** - 获取当前租户对象函数
- **get_current_tenant_id** - 获取当前租户ID函数
- **get_current_tenant_from_request** - 从请求中提取租户函数
- **get_tenant_from_token** - 从token获取租户ID函数
- **tenant_required** - 租户认证依赖装饰器
- **tenant_id_required** - 租户ID依赖装饰器
- **with_tenant_context** - 租户上下文装饰器
- **with_tenant_isolation** - 租户隔离装饰器
- **create_tenant_context_middleware** - 创建中间件函数
- **add_tenant_filter** - 添加租户过滤函数
- **filter_by_tenant** - 按租户过滤数据函数

### __all__ 列表
- 包含所有导出的中间件和工具名称（字符串列表）

## [LINK]
**上游依赖** (已读取源码):
- [./tenant_context.py](./tenant_context.py) - 租户上下文中间件

**下游依赖** (已读取源码):
- [../main.py](../main.py) - FastAPI应用（from src.app.middleware import create_tenant_context_middleware）
- [../api/v1/endpoints/tenants.py](../api/v1/endpoints/tenants.py) - 租户管理API（from src.app.middleware import get_current_tenant, tenant_required）
- [../api/v1/endpoints/data_sources.py](../api/v1/endpoints/data_sources.py) - 数据源管理API（from src.app.middleware import ...）
- [../api/v1/endpoints/documents.py](../api/v1/endpoints/documents.py) - 文档管理API（from src.app.middleware import ...）
- [../api/v1/endpoints/query.py](../api/v1/endpoints/query.py) - 查询API（from src.app.middleware import ...）
- [../services/*.py](../services/) - 服务层（from src.app.middleware import get_current_tenant_id）

**调用方**:
- **FastAPI应用**: 通过from src.app.middleware import create_tenant_context_middleware注册中间件
- **API端点**: 通过from src.app.middleware import get_current_tenant等导入租户工具
- **服务层**: 通过from src.app.middleware import get_current_tenant_id获取租户ID

## [POS]
**路径**: backend/src/app/middleware/__init__.py
**模块层级**: Level 3（Backend → src/app → middleware）
**依赖深度**: 直接依赖 1 层（tenant_context.py）
"""