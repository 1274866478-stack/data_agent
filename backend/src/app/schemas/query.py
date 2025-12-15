"""
Query API schemas
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str = Field(..., description="自然语言查询")
    connection_id: Optional[str] = Field(None, description="数据源连接ID")
    enable_cache: bool = Field(True, description="是否启用缓存")
    force_refresh: bool = Field(False, description="是否强制刷新")


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
    processing_steps: List[str] = Field(default_factory=list, description="处理步骤")
    validation_result: Optional[Dict[str, Any]] = Field(None, description="验证结果")
    execution_result: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    correction_attempts: int = Field(0, description="纠正尝试次数")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")


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


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str
    detail: Optional[str] = None
    query_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

