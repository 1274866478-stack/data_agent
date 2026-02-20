"""
# [QUERY SCHEMAS] 查询API Pydantic模型

## [HEADER]
**文件名**: query.py
**职责**: 定义查询API的请求和响应Pydantic模型 - 自然语言查询、SQL查询、查询响应、查询状态、缓存控制等
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 查询API数据模型

## [INPUT]
### QueryRequest (查询请求模型)
- **query: str** - 自然语言查询（必需，Field(...)）
- **connection_id: Optional[str]** - 数据源连接ID（可选，默认None）
- **enable_cache: bool** - 是否启用缓存（默认True）
- **force_refresh: bool** - 是否强制刷新（默认False）

### QueryStatusRequest (查询状态请求模型)
- **query_id: str** - 查询ID（必需）

### QueryCacheRequest (查询缓存请求模型)
- **query: str** - 查询文本（必需）
- **connection_id: Optional[str]** - 数据源连接ID（可选）

## [OUTPUT]
### QueryRequest (查询请求模型)
- **Pydantic BaseModel** - 继承自BaseModel
- **所有字段**: 使用Field()定义，包含description

### QueryResponseV3 (查询响应模型V3)
- **query_id: str** - 查询ID
- **tenant_id: str** - 租户ID
- **original_query: str** - 原始查询
- **generated_sql: str** - 生成的SQL
- **results: List[Dict[str, Any]]** - 查询结果（默认空列表）
- **row_count: int** - 结果行数（默认0）
- **processing_time_ms: int** - 处理时间毫秒（默认0）
- **confidence_score: float** - 置信度分数（默认0.0）
- **explanation: str** - 查询解释（默认空字符串）
- **processing_steps: List[Dict[str, Any]]** - 处理步骤（默认空列表）
- **validation_result: Optional[Dict[str, Any]]** - 验证结果（默认None）
- **execution_result: Optional[Dict[str, Any]]** - 执行结果（默认None）
- **correction_attempts: int** - 纠正尝试次数（默认0）
- **timestamp: datetime** - 时间戳（默认utcnow）
- **metadata: Optional[Dict[str, Any]]** - 元数据，包含工具调用状态、推理过程等（默认None）

### QueryStatusResponse (查询状态响应模型)
- **query_id: str** - 查询ID
- **status: str** - 状态
- **progress: float** - 进度（0.0-1.0，默认0.0，使用ge和le约束）
- **message: str** - 消息（默认空字符串）
- **result: Optional[QueryResponseV3]** - 查询结果（默认None）

### QueryCacheResponse (查询缓存响应模型)
- **cache_hit: bool** - 缓存命中
- **cache_key: str** - 缓存键

### QueryHistoryResponse (查询历史响应模型)
- **queries: List[QueryResponseV3]** - 查询列表
- **total_count: int** - 总数量
- **page: int** - 页码
- **page_size: int** - 每页大小

### ErrorResponse (错误响应模型)
- **error: str** - 错误信息
- **detail: str** - 详细信息
- **error_code: str** - 错误代码

## [LINK]
**上游依赖** (已读取源码):
- [pydantic](https://docs.pydantic.dev/) - Pydantic数据验证库（BaseModel, Field）
- [datetime](https://docs.python.org/3/library/datetime.html) - Python标准库datetime模块
- [typing](https://docs.python.org/3/library/typing.html) - Python标准库typing模块（List, Dict, Any, Optional）

**下游依赖** (已读取源码):
- [../api/v1/endpoints/query.py](../api/v1/endpoints/query.py) - 查询API端点（使用所有Schema模型）
- [../api/v1/endpoints/llm.py](../api/v1/endpoints/llm.py) - LLM服务API（使用QueryRequest, QueryResponseV3）
- [../services/llm_service.py](../services/llm_service.py) - LLM服务层（使用Schema模型）

**调用方**:
- **查询API端点**: 接收QueryRequest，返回QueryResponseV3
- **查询状态API**: 返回QueryStatusResponse
- **查询历史API**: 返回QueryHistoryResponse
- **缓存API**: 返回QueryCacheResponse
- **错误处理**: 返回ErrorResponse

## [POS]
**路径**: backend/src/app/schemas/query.py
**模块层级**: Level 3（Backend → src/app → schemas）
**依赖深度**: 无直接依赖（只依赖Pydantic和Python标准库）
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str = Field(..., description="自然语言查询")
    connection_id: Optional[str] = Field(None, description="数据源连接ID")
    session_id: Optional[str] = Field(None, description="会话ID，用于多轮对话上下文管理（如图表拆分）")
    enable_cache: bool = Field(True, description="是否启用缓存")
    force_refresh: bool = Field(False, description="是否强制刷新")
    # 图表合并请求
    merge_request: Optional[Dict[str, Any]] = Field(None, description="图表合并请求配置，包含待合并的图表信息")


class QueryResponseV3(BaseModel):
    """查询响应模型 V3格式"""
    query_id: str = Field(..., description="查询ID")
    tenant_id: str = Field(..., description="租户ID")
    original_query: str = Field(..., description="原始查询")
    generated_sql: str = Field(..., description="生成的SQL")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="查询结果")
    row_count: int = Field(0, description="结果行数")
    processing_time_ms: int = Field(0, description="处理时间(毫秒)")
    confidence_score: float = Field(0.0, description="置信度分数")
    explanation: str = Field("", description="查询解释")
    processing_steps: List[Dict[str, Any]] = Field(default_factory=list, description="处理步骤")
    validation_result: Optional[Dict[str, Any]] = Field(None, description="验证结果")
    execution_result: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    correction_attempts: int = Field(0, description="纠正尝试次数")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")
    # 🔴 第三道防线：添加metadata字段，包含工具调用状态和错误信息
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据，包含工具调用状态、推理过程等信息")


class QueryStatusResponse(BaseModel):
    """查询状态响应模型"""
    query_id: str
    status: str
    progress: float = Field(0.0, ge=0.0, le=1.0)
    message: str = ""
    result: Optional[QueryResponseV3] = None


class QueryCacheResponse(BaseModel):
    """查询缓存响应模型"""
    cache_hit: bool
    cache_key: str
    cached_at: Optional[datetime] = None
    ttl_seconds: Optional[int] = None


class QueryHistoryResponse(BaseModel):
    """查询历史响应模型"""
    queries: List[QueryResponseV3]
    total_count: int
    page: int = 1
    page_size: int = 20


class SOTAQueryRequest(BaseModel):
    """SOTA 鏌ヨ璇锋眰"""
    query: str
    cube_name: Optional[str] = None
    session_id: Optional[str] = None
    enable_few_shot: bool = True
    enable_self_healing: bool = True
    enable_disambiguation: bool = True
    max_repair_attempts: int = 3


class SOTAQueryResponse(BaseModel):
    """SOTA 鏌ヨ鍝嶅簲"""
    query_id: str
    tenant_id: str
    original_query: str
    refined_query: Optional[str] = None
    needs_clarification: bool = False
    clarification_questions: Optional[List[Dict[str, Any]]] = None
    dsl_json: Optional[Dict[str, Any]] = None
    results: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    processing_time_ms: int = 0
    processing_steps: List[Dict[str, Any]] = []
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str
    detail: Optional[str] = None
    query_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

