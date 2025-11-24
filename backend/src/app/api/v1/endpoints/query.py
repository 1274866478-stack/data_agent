"""
查询API端点
Story 3.1: 租户隔离的查询 API V3格式
"""

import asyncio
import uuid
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query as QueryParam
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.app.data.database import get_db
from src.app.data.models import QueryStatus, QueryType
from src.app.middleware.tenant_context import get_current_tenant_from_request, get_current_tenant_id
from src.app.services.query_context import get_query_context
from src.app.services.llm_service import llm_service
from src.app.core.jwt_utils import get_current_user_from_token
from fastapi import Request
from src.app.schemas.query import (
    QueryRequest, QueryResponseV3, QueryStatusResponse,
    QueryCacheResponse, QueryHistoryResponse, ErrorResponse
)
from src.app.core.config import get_settings
import structlog

logger = structlog.get_logger(__name__)
settings = get_settings()
router = APIRouter()


async def get_current_user_info_from_request(
    request: Request,
    tenant=Depends(get_current_tenant_from_request)
) -> Dict[str, Any]:
    """
    从请求中获取当前用户信息

    Args:
        request: FastAPI请求对象
        tenant: 当前租户对象

    Returns:
        Dict[str, Any]: 用户信息，包含user_id

    Raises:
        HTTPException: 获取用户信息失败
    """
    try:
        # 从Authorization header中提取token
        authorization = request.headers.get("Authorization")
        if not authorization:
            # 如果没有JWT token，回退到API key或公共访问
            return {
                "user_id": tenant.id,  # 使用tenant.id作为fallback
                "auth_type": "tenant_fallback",
                "tenant_id": tenant.id
            }

        # 验证JWT token并提取用户信息
        user_info = await get_current_user_from_token(authorization)

        # 确保用户信息和租户信息匹配
        if user_info.get("tenant_id") != tenant.id:
            logger.warning(
                "User tenant mismatch",
                user_tenant=user_info.get("tenant_id"),
                request_tenant=tenant.id
            )
            # 使用租户ID确保数据隔离
            user_info["tenant_id"] = tenant.id

        return {
            "user_id": user_info.get("user_id", tenant.id),
            "auth_type": "jwt",
            "tenant_id": tenant.id,
            "email": user_info.get("email"),
            "is_verified": user_info.get("is_verified", False),
            "raw_info": user_info
        }

    except Exception as e:
        logger.error(f"Failed to extract user info: {e}")
        # 发生错误时，使用tenant.id作为fallback确保系统正常运行
        return {
            "user_id": tenant.id,
            "auth_type": "error_fallback",
            "tenant_id": tenant.id,
            "error": str(e)
        }


class QueryService:
    """查询处理服务，包含AI服务重试机制"""

    def __init__(self, query_context):
        self.query_context = query_context

    async def retry_with_exponential_backoff(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        retry_on: tuple = (Exception,)
    ) -> Any:
        """
        指数退避重试机制

        Args:
            func: 要重试的异步函数
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            backoff_factor: 退避因子
            retry_on: 需要重试的异常类型

        Returns:
            Any: 函数执行结果

        Raises:
            Exception: 重试次数耗尽后的最后一个异常
        """
        last_exception = None

        for attempt in range(max_retries + 1):  # +1 因为第一次不算重试
            try:
                if attempt > 0:
                    delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                    logger.info(
                        f"AI service retry attempt {attempt}/{max_retries} after {delay:.2f}s delay",
                        tenant_id=self.query_context.tenant_id
                    )
                    await asyncio.sleep(delay)

                result = await func()

                if attempt > 0:
                    logger.info(
                        f"AI service succeeded on attempt {attempt + 1}",
                        tenant_id=self.query_context.tenant_id
                    )

                return result

            except retry_on as e:
                last_exception = e

                if attempt < max_retries:
                    logger.warning(
                        f"AI service attempt {attempt + 1} failed: {e}, will retry",
                        tenant_id=self.query_context.tenant_id,
                        attempt=attempt + 1,
                        max_retries=max_retries + 1
                    )
                else:
                    logger.error(
                        f"AI service failed after {max_retries + 1} attempts: {e}",
                        tenant_id=self.query_context.tenant_id
                    )

            except Exception as e:
                # 对于不需要重试的异常，直接抛出
                logger.error(
                    f"AI service encountered non-retryable error: {e}",
                    tenant_id=self.query_context.tenant_id
                )
                raise

        # 重试次数耗尽，抛出最后一个异常
        raise last_exception

    async def call_llm_with_retry(self, messages: list, **kwargs) -> Any:
        """
        带重试机制的LLM服务调用

        Args:
            messages: 消息列表
            **kwargs: 其他LLM参数

        Returns:
            Any: LLM响应结果
        """
        async def llm_call():
            return await llm_service.chat_completion(
                messages=messages,
                tenant_id=self.query_context.tenant_id,
                **kwargs
            )

        # 定义需要重试的异常类型
        retryable_exceptions = (
            ConnectionError,
            TimeoutError,
            OSError,
            # 可以根据实际LLM服务的异常类型进行调整
        )

        return await self.retry_with_exponential_backoff(
            func=llm_call,
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0,
            backoff_factor=2.0,
            retry_on=retryable_exceptions
        )

    async def analyze_query_type(self, question: str, context: Optional[Dict[str, Any]] = None) -> QueryType:
        """
        分析查询类型
        Story要求：自动分析查询类型（SQL/文档/混合）

        Args:
            question: 查询问题
            context: 查询上下文

        Returns:
            QueryType: 查询类型
        """
        question_lower = question.lower()

        # SQL查询关键词
        sql_keywords = ['销售', '收入', '数量', '统计', '汇总', '计算', '对比', '分析', '数据']
        # 文档查询关键词
        doc_keywords = ['什么是', '如何', '为什么', '解释', '说明', '介绍', '文档', '报告']

        has_sql_keywords = any(keyword in question_lower for keyword in sql_keywords)
        has_doc_keywords = any(keyword in question_lower for keyword in doc_keywords)

        # 检查上下文
        has_data_sources = context and context.get('data_source_ids')
        has_documents = context and context.get('document_ids')

        if has_sql_keywords or has_data_sources:
            if has_doc_keywords or has_documents:
                return QueryType.MIXED
            return QueryType.SQL
        elif has_doc_keywords or has_documents:
            return QueryType.DOCUMENT
        else:
            return QueryType.MIXED  # 默认为混合查询

    async def process_query(
        self,
        query_id: str,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理查询请求
        Story要求：完整的查询处理流程

        Args:
            query_id: 查询ID
            question: 查询问题
            context: 查询上下文
            options: 查询选项

        Returns:
            Dict[str, Any]: 查询结果
        """
        start_time = datetime.utcnow()

        try:
            # 更新状态为处理中
            self.query_context.update_query_status(
                query_id=query_id,
                status=QueryStatus.PROCESSING
            )

            # 分析查询类型
            query_type = await self.analyze_query_type(question, context)

            # 获取租户数据源和文档
            data_sources = self.query_context.get_tenant_data_sources()
            documents = self.query_context.get_tenant_documents()

            # 构建LLM请求
            messages = [
                {
                    "role": "system",
                    "content": f"""你是一个数据分析助手。请根据用户的问题，使用提供的数据源和文档信息来回答。

查询类型: {query_type.value}

可用数据源数量: {len(data_sources)}
可用文档数量: {len(documents)}

请按照以下格式回答：
1. 提供准确的答案
2. 引用相关的数据源和文档
3. 提供详细的推理过程
4. 使用Markdown格式化答案"""
                },
                {
                    "role": "user",
                    "content": f"问题: {question}\n\n上下文: {context or {}}\n\n请基于可用数据回答这个问题。"
                }
            ]

            # 调用LLM服务（带重试机制）
            try:
                llm_response = await self.call_llm_with_retry(
                    messages=messages,
                    temperature=0.3,
                    max_tokens=1000
                )

                if not llm_response.success:
                    raise Exception(f"LLM service failed: {llm_response.error}")

            except Exception as e:
                # 记录AI服务失败并更新查询状态
                self.query_context.update_query_status(
                    query_id=query_id,
                    status=QueryStatus.ERROR,
                    error_message=f"AI service error: {str(e)}",
                    error_code="AI_SERVICE_ERROR",
                    response_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                )
                raise

            # 构建响应数据
            response_data = {
                "answer": llm_response.content,
                "citations": [],  # TODO: 实现真实的文档引用
                "data_sources": [],  # TODO: 实现真实的数据源引用
                "explainability_log": self._generate_explainability_log(question, query_type, data_sources, documents),
                "response_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                "tokens_used": llm_response.usage.get('total_tokens') if llm_response.usage else 0,
                "query_type": query_type.value
            }

            # 更新查询状态为成功
            self.query_context.update_query_status(
                query_id=query_id,
                status=QueryStatus.SUCCESS,
                response_summary=llm_response.content[:200] + "..." if len(llm_response.content) > 200 else llm_response.content,
                response_data=response_data,
                explainability_log=response_data["explainability_log"],
                response_time_ms=response_data["response_time_ms"],
                tokens_used=response_data["tokens_used"]
            )

            return response_data

        except Exception as e:
            # 更新查询状态为错误
            error_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self.query_context.update_query_status(
                query_id=query_id,
                status=QueryStatus.ERROR,
                response_time_ms=error_time_ms,
                error_message=str(e),
                error_code="QUERY_PROCESSING_ERROR"
            )
            raise

    def _generate_explainability_log(self, question: str, query_type: QueryType,
                                   data_sources: list, documents: list) -> str:
        """
        生成XAI可解释性日志
        Story要求：XAI推理路径日志

        Args:
            question: 查询问题
            query_type: 查询类型
            data_sources: 数据源列表
            documents: 文档列表

        Returns:
            str: 解释性日志
        """
        log_lines = [
            f"# 查询推理路径",
            f"",
            f"## 1. 查询分析",
            f"- 原始问题: {question}",
            f"- 识别的查询类型: {query_type.value}",
            f"",
            f"## 2. 数据源评估",
            f"- 可用数据源数量: {len(data_sources)}",
            f"- 可用文档数量: {len(documents)}",
        ]

        if data_sources:
            log_lines.extend([
                f"- 数据源列表:",
            ])
            for ds in data_sources[:3]:  # 最多显示3个
                log_lines.append(f"  * {ds.name} ({ds.connection_type})")

        if documents:
            log_lines.extend([
                f"- 相关文档列表:",
            ])
            for doc in documents[:3]:  # 最多显示3个
                log_lines.append(f"  * {doc.title}")

        log_lines.extend([
            f"",
            f"## 3. 处理策略",
            f"- 基于查询类型选择处理策略",
            f"- 整合多源数据进行综合分析",
            f"",
            f"## 4. 推理过程",
            f"- 使用LLM进行语义理解和答案生成",
            f"- 确保答案基于可用的数据和文档",
            f"- 提供详细的推理过程和引用信息",
            f"",
            f"## 5. 答案生成",
            f"- 综合所有信息生成最终答案",
            f"- 确保答案的准确性和可解释性",
            f"",
            f"生成时间: {datetime.utcnow().isoformat()}"
        ])

        return "\n".join(log_lines)


# 创建查询服务的依赖注入
async def get_query_service(query_context=Depends(get_query_context)) -> QueryService:
    """获取查询服务实例"""
    return QueryService(query_context)


@router.post("/query", response_model=QueryResponseV3)
async def create_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    tenant=Depends(get_current_tenant_from_request),
    user_info: Dict[str, Any] = Depends(get_current_user_info_from_request),
    db: Session = Depends(get_db),
    query_service: QueryService = Depends(get_query_service)
):
    """
    创建查询请求
    Story 3.1: 核心查询端点，处理自然语言查询
    """
    try:
        query_id = str(uuid.uuid4())
        query_hash = request.get_query_hash()

        # 获取用户ID（从JWT中正确提取）
        user_id = user_info["user_id"]
        logger.info(f"Query request - user_id: {user_id}, tenant_id: {tenant.id}, auth_type: {user_info.get('auth_type')}")

        # 创建查询上下文
        query_context = get_query_context(db, tenant.id, user_id)

        # 检查频率限制
        can_proceed, error_msg = query_context.check_rate_limits()
        if not can_proceed:
            raise HTTPException(status_code=429, detail=error_msg)

        # 检查缓存
        cached_query = query_context.get_cached_query(query_hash)
        if cached_query and request.options.cache_enabled if request.options else True:
            # 返回缓存结果
            response_data = cached_query.response_data or {}
            return QueryResponseV3(
                query_id=query_id,
                answer=response_data.get("answer", "缓存结果"),
                citations=response_data.get("citations", []),
                data_sources=response_data.get("data_sources", []),
                explainability_log=response_data.get("explainability_log", ""),
                response_time_ms=cached_query.response_time_ms or 0,
                tokens_used=cached_query.tokens_used,
                cache_hit=True,
                query_type=QueryType(response_data.get("query_type", "mixed")),
                created_at=datetime.utcnow()
            )

        # 记录查询请求
        query_context.log_query_request(
            query_id=query_id,
            question=request.question,
            context=request.context.dict() if request.context else None,
            options=request.options.dict() if request.options else None,
            query_hash=query_hash
        )

        # 处理查询
        response_data = await query_service.process_query(
            query_id=query_id,
            question=request.question,
            context=request.context.dict() if request.context else None,
            options=request.options.dict() if request.options else None
        )

        # 构建响应
        return QueryResponseV3(
            query_id=query_id,
            answer=response_data["answer"],
            citations=response_data["citations"],
            data_sources=response_data["data_sources"],
            explainability_log=response_data["explainability_log"],
            response_time_ms=response_data["response_time_ms"],
            tokens_used=response_data["tokens_used"],
            cache_hit=False,
            query_type=QueryType(response_data["query_type"]),
            created_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"查询处理失败: {str(e)}")


@router.get("/query/status/{query_id}", response_model=QueryStatusResponse)
async def get_query_status(
    query_id: str,
    tenant=Depends(get_current_tenant_from_request),
    user_info: Dict[str, Any] = Depends(get_current_user_info_from_request),
    db: Session = Depends(get_db)
):
    """
    获取查询状态
    Story 3.1: 查询状态跟踪端点
    """
    try:
        # 创建查询上下文（使用正确的用户ID）
        user_id = user_info["user_id"]
        query_context = get_query_context(db, tenant.id, user_id)

        # 查询状态
        from src.app.data.models import QueryLog
        query_log = db.query(QueryLog).filter(
            QueryLog.id == query_id,
            QueryLog.tenant_id == tenant.id
        ).first()

        if not query_log:
            raise HTTPException(status_code=404, detail="查询不存在")

        # 计算进度百分比
        progress_percentage = None
        if query_log.status == QueryStatus.PROCESSING:
            # 简化的进度计算
            progress_percentage = 50.0  # 处理中的查询默认50%
        elif query_log.status == QueryStatus.SUCCESS:
            progress_percentage = 100.0

        return QueryStatusResponse(
            query_id=query_id,
            status=query_log.status,
            created_at=query_log.created_at,
            updated_at=query_log.updated_at,
            response_time_ms=query_log.response_time_ms,
            error_message=query_log.error_message,
            progress_percentage=progress_percentage
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get query status failed: {e}")
        raise HTTPException(status_code=500, detail=f"获取查询状态失败: {str(e)}")


@router.delete("/query/cache/{query_hash}", response_model=QueryCacheResponse)
async def clear_query_cache(
    query_hash: str,
    tenant=Depends(get_current_tenant_from_request),
    db: Session = Depends(get_db)
):
    """
    清除查询缓存
    Story 3.1: 清除查询缓存
    """
    try:
        # 创建查询上下文
        query_context = get_query_context(db, tenant.id, tenant.id)

        # 清除缓存
        success, message = query_context.clear_query_cache(query_hash)

        return QueryCacheResponse(
            query_hash=query_hash,
            cache_cleared=success,
            message=message
        )

    except Exception as e:
        logger.error(f"Clear query cache failed: {e}")
        raise HTTPException(status_code=500, detail=f"清除缓存失败: {str(e)}")


@router.get("/query/history", response_model=QueryHistoryResponse)
async def get_query_history(
    page: int = QueryParam(1, ge=1, description="页码"),
    page_size: int = QueryParam(10, ge=1, le=100, description="每页大小"),
    tenant=Depends(get_current_tenant_from_request),
    db: Session = Depends(get_db)
):
    """
    获取查询历史
    Story 3.1: 查询历史记录
    """
    try:
        # 创建查询上下文
        query_context = get_query_context(db, tenant.id, tenant.id)

        # 获取查询历史
        history = query_context.get_query_history(page, page_size)

        return QueryHistoryResponse(
            queries=history["queries"],
            total_count=history["total_count"],
            page=history["page"],
            page_size=history["page_size"]
        )

    except Exception as e:
        logger.error(f"Get query history failed: {e}")
        raise HTTPException(status_code=500, detail=f"获取查询历史失败: {str(e)}")


# 错误处理器
@router.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=f"HTTP_{exc.status_code}",
            message=exc.detail,
            timestamp=datetime.utcnow()
        ).dict()
    )


@router.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    logger.error(f"Unhandled exception in query endpoint: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            message="服务器内部错误",
            timestamp=datetime.utcnow()
        ).dict()
    )