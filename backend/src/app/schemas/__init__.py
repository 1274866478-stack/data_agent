"""
# [SCHEMAS] Pydantic schemas 模块初始化

## [HEADER]
**文件名**: __init__.py
**职责**: 导出所有API请求和响应的Pydantic模型 - 组织和暴露schemas模块的所有数据模型
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - Schemas模块初始化

## [INPUT]
- **from .query import**: 从query.py模块导入所有Schema类

## [OUTPUT]
### 导出的Schema类
- **QueryRequest** - 查询请求模型
- **QueryResponseV3** - 查询响应模型V3
- **QueryStatusResponse** - 查询状态响应模型
- **QueryCacheResponse** - 查询缓存响应模型
- **QueryHistoryResponse** - 查询历史响应模型
- **ErrorResponse** - 错误响应模型

### __all__ 列表
- 包含所有导出的Schema类名称（字符串列表）

## [LINK]
**上游依赖** (已读取源码):
- [./query.py](./query.py) - 查询相关Schema模型

**下游依赖** (已读取源码):
- [../api/v1/endpoints/query.py](../api/v1/endpoints/query.py) - 查询API（from src.app.schemas import QueryRequest, QueryResponseV3）
- [../api/v1/endpoints/llm.py](../api/v1/endpoints/llm.py) - LLM服务API（from src.app.schemas import ...）
- [../services/llm_service.py](../services/llm_service.py) - LLM服务层（from src.app.schemas import ...）

**调用方**:
- **API端点**: 通过from src.app.schemas import ...导入Schema类
- **服务层**: 通过from src.app.schemas import ...导入Schema类
- **测试文件**: 通过from src.app.schemas import ...导入Schema类进行测试

## [POS]
**路径**: backend/src/app/schemas/__init__.py
**模块层级**: Level 3（Backend → src/app → schemas）
**依赖深度**: 直接依赖 1 层（query.py）
"""

from .query import (
    QueryRequest,
    QueryResponseV3,
    QueryStatusResponse,
    QueryCacheResponse,
    QueryHistoryResponse,
    ErrorResponse
)

__all__ = [
    "QueryRequest",
    "QueryResponseV3",
    "QueryStatusResponse",
    "QueryCacheResponse",
    "QueryHistoryResponse",
    "ErrorResponse"
]

