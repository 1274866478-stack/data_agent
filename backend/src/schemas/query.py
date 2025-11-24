"""
查询相关的Pydantic模型定义
Story 3.1: 租户隔离的查询 API V3格式
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum
import hashlib
import re


class QueryType(str, Enum):
    """查询类型枚举"""
    SQL = "sql"
    DOCUMENT = "document"
    MIXED = "mixed"


class QueryStatus(str, Enum):
    """查询状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class QueryOptions(BaseModel):
    """查询选项配置"""
    max_results: Optional[int] = Field(10, ge=1, le=100, description="最大结果数量")
    include_explainability: Optional[bool] = Field(True, description="是否包含解释性日志")
    cache_enabled: Optional[bool] = Field(True, description="是否启用缓存")
    timeout_seconds: Optional[int] = Field(30, ge=5, le=300, description="查询超时时间（秒）")

    class Config:
        schema_extra = {
            "example": {
                "max_results": 10,
                "include_explainability": True,
                "cache_enabled": True,
                "timeout_seconds": 30
            }
        }


class QueryContext(BaseModel):
    """查询上下文信息"""
    data_source_ids: Optional[List[str]] = Field(None, description="数据源ID列表")
    document_ids: Optional[List[str]] = Field(None, description="文档ID列表")
    time_range: Optional[str] = Field(None, description="时间范围过滤器")
    filters: Optional[Dict[str, Any]] = Field(None, description="自定义过滤器")

    class Config:
        schema_extra = {
            "example": {
                "data_source_ids": ["ds_1", "ds_2"],
                "document_ids": ["doc_1", "doc_2"],
                "time_range": "2024-Q3",
                "filters": {
                    "category": "electronics",
                    "min_price": 1000
                }
            }
        }


class QueryRequest(BaseModel):
    """查询请求模型 - Story 3.1 V3格式"""
    question: str = Field(..., min_length=1, max_length=1000, description="自然语言查询问题")
    context: Optional[QueryContext] = Field(None, description="查询上下文")
    options: Optional[QueryOptions] = Field(None, description="查询选项")

    @validator('question')
    def validate_question(cls, v):
        """增强的查询问题验证 - 防止SQL注入和XSS攻击"""
        # 移除多余的空白字符
        v = v.strip()

        # 检查是否为空
        if not v:
            raise ValueError('查询问题不能为空')

        # 检查长度限制
        if len(v) > 1000:
            raise ValueError('查询问题过长，最多支持1000个字符')

        # 增强的SQL注入检测
        # 1. 危险SQL关键字检测（更全面的列表）
        dangerous_sql_keywords = [
            'DROP', 'DELETE', 'INSERT', 'UPDATE', 'CREATE', 'ALTER',
            'EXEC', 'EXECUTE', 'SP_EXECUTESQL', 'XP_CMDSHELL',
            'TRUNCATE', 'MERGE', 'BULK', 'OPENROWSET', 'OPENDATASOURCE',
            'GRANT', 'REVOKE', 'DENY', 'UNION', 'INTERSECT', 'EXCEPT',
            'INFORMATION_SCHEMA', 'SYSOBJECTS', 'SYSCOLUMNS', 'MASTER'
        ]

        # 2. 特殊字符和模式检测
        dangerous_patterns = [
            r';\s*(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER|EXEC|TRUNCATE)',  # 分号+命令
            r'\b(UNION|INTERSECT|EXCEPT)\s+.*\bSELECT\b',                 # UNION注入
            r'--\s*$',                                                   # SQL注释
            r'/\*.*?\*/',                                                # 多行注释
            r'\'\s*;\s*\w+',                                           # 单引号+分号+命令
            r'"\s*;\s*\w+',                                            # 双引号+分号+命令
            r'\bOR\s+["\']?\d+["\']?\s*=\s*["\']?\d+["\']?',           # OR 1=1
            r'\bAND\s+["\']?\d+["\']?\s*=\s*["\']?\d+["\']?',          # AND 1=1
            r'\b( WAITFOR\s+DELAY\s*["\']?\d+["\']?|SLEEP\s*\()',       # 时间延迟攻击
            r'\b(BENCHMARK|LOAD_FILE|OUTFILE|DUMPFILE)\s*\(',           # MySQL文件操作
            r'\b(CAST|CONVERT|CHAR|ASCII|ORD|HEX)\s*\(',                # 函数混淆
        ]

        # 3. 检测危险SQL关键字
        question_upper = v.upper()
        for keyword in dangerous_sql_keywords:
            # 使用单词边界确保完整单词匹配
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, question_upper):
                raise ValueError(f'查询包含不安全的SQL关键字: {keyword}')

        # 4. 检测危险模式
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                raise ValueError('查询包含不安全的内容模式')

        # 5. 检测脚本注入 (XSS)
        xss_patterns = [
            r'<\s*script[^>]*>',           # <script>标签
            r'javascript\s*:',             # javascript:协议
            r'on\w+\s*=',                 # 事件处理器
            r'<\s*iframe[^>]*>',           # iframe标签
            r'<\s*object[^>]*>',           # object标签
            r'<\s*embed[^>]*>',            # embed标签
        ]

        for pattern in xss_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('查询包含不安全的脚本内容')

        # 6. 查询意图白名单验证
        # 允许的查询模式（用于数据分析的正上下文查询）
        allowed_query_patterns = [
            r'^(销售|数量|金额|总计|平均|最大|最小|最高|最低).*',
            r'^(显示|查询|统计|分析|汇总|对比).*',
            r'^(什么|如何|哪个|多少|几个).*',
            r'^(今年|去年|本月|上月|本季度|上季度).*',
            r'^(产品|商品|客户|用户|订单).*',
        ]

        # 如果查询不匹配任何允许的模式，给出警告但不阻止
        is_allowed_query = any(re.match(pattern, v, re.IGNORECASE) for pattern in allowed_query_patterns)
        if not is_allowed_query:
            # 这里不抛出异常，但可以记录日志用于分析
            pass

        return v

    def get_query_hash(self) -> str:
        """生成查询哈希值用于缓存"""
        content = f"{self.question}:{self.context.dict() if self.context else ''}:{self.options.dict() if self.options else ''}"
        return hashlib.sha256(content.encode()).hexdigest()

    class Config:
        schema_extra = {
            "example": {
                "question": "上个季度销售额最高的笔记本电脑型号是什么？",
                "context": {
                    "time_range": "2024-Q3",
                    "data_source_ids": ["sales_db"]
                },
                "options": {
                    "max_results": 10,
                    "include_explainability": True
                }
            }
        }


class KnowledgeCitation(BaseModel):
    """知识引用模型"""
    document_id: str = Field(..., description="文档ID")
    document_title: str = Field(..., description="文档标题")
    content_snippet: str = Field(..., description="相关内容片段")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="相关性得分")
    page_number: Optional[int] = Field(None, description="页码")
    section: Optional[str] = Field(None, description="章节")

    class Config:
        schema_extra = {
            "example": {
                "document_id": "doc_123",
                "document_title": "2024年销售报告",
                "content_snippet": "笔记本电脑在2024年第三季度的销售额达到历史新高...",
                "relevance_score": 0.95,
                "page_number": 15,
                "section": "产品分析"
            }
        }


class DataSourceReference(BaseModel):
    """数据源引用模型"""
    data_source_id: str = Field(..., description="数据源ID")
    data_source_name: str = Field(..., description="数据源名称")
    query_executed: str = Field(..., description="执行的SQL查询")
    rows_affected: int = Field(..., description="影响的行数")
    execution_time_ms: int = Field(..., description="执行时间（毫秒）")

    class Config:
        schema_extra = {
            "example": {
                "data_source_id": "ds_456",
                "data_source_name": "销售数据库",
                "query_executed": "SELECT model, SUM(amount) FROM sales WHERE quarter = '2024-Q3' GROUP BY model ORDER BY SUM(amount) DESC LIMIT 1",
                "rows_affected": 1,
                "execution_time_ms": 150
            }
        }


class QueryResponseV3(BaseModel):
    """查询响应模型 - Story 3.1 V3格式"""
    query_id: str = Field(..., description="查询ID")
    answer: str = Field(..., description="融合答案（Markdown格式）")
    citations: List[KnowledgeCitation] = Field(default=[], description="文档引用列表")
    data_sources: List[DataSourceReference] = Field(default=[], description="数据源引用列表")
    explainability_log: str = Field(..., description="XAI推理路径日志")
    response_time_ms: int = Field(..., description="响应时间（毫秒）")
    tokens_used: Optional[int] = Field(None, description="使用的token数量")
    cache_hit: bool = Field(default=False, description="是否命中缓存")
    query_type: QueryType = Field(..., description="查询类型")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        schema_extra = {
            "example": {
                "query_id": "550e8400-e29b-41d4-a716-446655440000",
                "answer": "# 销售最高的笔记本电脑型号\n\n根据2024年第三季度的销售数据分析，**ThinkPad X1 Carbon** 是销售额最高的笔记本电脑型号，总销售额达到 **￥1,250,000**。",
                "citations": [
                    {
                        "document_id": "doc_123",
                        "document_title": "2024年销售报告",
                        "content_snippet": "笔记本电脑在2024年第三季度的销售额达到历史新高...",
                        "relevance_score": 0.95,
                        "page_number": 15
                    }
                ],
                "data_sources": [
                    {
                        "data_source_id": "ds_456",
                        "data_source_name": "销售数据库",
                        "query_executed": "SELECT model, SUM(amount) FROM sales WHERE quarter = '2024-Q3' GROUP BY model ORDER BY SUM(amount) DESC LIMIT 1",
                        "rows_affected": 1,
                        "execution_time_ms": 150
                    }
                ],
                "explainability_log": "1. 解析用户查询：识别出'上个季度'、'销售额最高'、'笔记本电脑型号'等关键信息\n2. 确定查询类型：混合查询（需要数据库查询和文档检索）\n3. 执行SQL查询：从销售数据库获取2024-Q3的笔记本电脑销售数据\n4. 检索相关文档：查询产品报告和市场分析文档\n5. 融合结果：结合数据查询结果和文档信息生成最终答案",
                "response_time_ms": 2850,
                "tokens_used": 156,
                "cache_hit": False,
                "query_type": "mixed",
                "created_at": "2024-11-17T15:30:00Z"
            }
        }


class QueryStatusResponse(BaseModel):
    """查询状态响应模型"""
    query_id: str = Field(..., description="查询ID")
    status: QueryStatus = Field(..., description="查询状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    response_time_ms: Optional[int] = Field(None, description="响应时间（毫秒）")
    error_message: Optional[str] = Field(None, description="错误信息")
    progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, description="进度百分比")

    class Config:
        schema_extra = {
            "example": {
                "query_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "created_at": "2024-11-17T15:30:00Z",
                "updated_at": "2024-11-17T15:30:15Z",
                "response_time_ms": None,
                "error_message": None,
                "progress_percentage": 75.0
            }
        }


class QueryCacheResponse(BaseModel):
    """查询缓存操作响应模型"""
    query_hash: str = Field(..., description="查询哈希")
    cache_cleared: bool = Field(..., description="是否成功清除缓存")
    message: str = Field(..., description="操作结果消息")

    class Config:
        schema_extra = {
            "example": {
                "query_hash": "a1b2c3d4e5f6...",
                "cache_cleared": True,
                "message": "缓存已成功清除"
            }
        }


class QueryHistoryResponse(BaseModel):
    """查询历史响应模型"""
    queries: List[Dict[str, Any]] = Field(..., description="查询历史列表")
    total_count: int = Field(..., description="总查询数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")

    class Config:
        schema_extra = {
            "example": {
                "queries": [
                    {
                        "query_id": "550e8400-e29b-41d4-a716-446655440000",
                        "question": "上个季度销售额最高的笔记本电脑型号是什么？",
                        "status": "success",
                        "response_time_ms": 2850,
                        "created_at": "2024-11-17T15:30:00Z"
                    }
                ],
                "total_count": 25,
                "page": 1,
                "page_size": 10
            }
        }


# 错误响应模型
class ErrorResponse(BaseModel):
    """通用错误响应模型"""
    error_code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误信息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: datetime = Field(..., description="错误发生时间")

    class Config:
        schema_extra = {
            "example": {
                "error_code": "QUERY_001",
                "message": "查询问题不能为空",
                "details": {
                    "field": "question",
                    "validation_error": "min_length"
                },
                "timestamp": "2024-11-17T15:30:00Z"
            }
        }