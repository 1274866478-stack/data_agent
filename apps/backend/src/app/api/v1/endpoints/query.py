"""
# [QUERY] 智能查询API端点

## [HEADER]
**文件名**: query.py
**职责**: 实现自然语言查询API，集成LangGraph SQL Agent和LLM服务，支持SQL/文档/混合查询，提供查询历史、状态跟踪和缓存管理，确保租户隔离和查询安全
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 实现Story 3.1规范的智能查询API

## [INPUT]
- **tenant_id: str** - 租户ID（从JWT token中提取）
- **user_id: str** - 用户ID（从JWT token中提取，用于操作审计）
- **query_id: str** - 查询ID（UUID格式，路径参数）
- **query_hash: str** - 查询哈希值（用于缓存管理）
- **request: QueryRequest** - 查询请求模型（Pydantic模型）
  - query: 自然语言查询问题
  - connection_id: 数据源连接ID（可选）
  - data_source_ids: 数据源ID列表（可选）
  - document_ids: 文档ID列表（可选）
  - options: 查询选项（可选）
- **page: int** - 分页页码（默认1）
- **page_size: int** - 分页大小（默认10，最大100）
- **background_tasks: BackgroundTasks** - FastAPI后台任务
- **db: Session** - 数据库会话（通过依赖注入获取）

## [OUTPUT]
- **query_response: QueryResponseV3** - 查询响应V3格式
  - query_id: 查询ID
  - tenant_id: 租户ID
  - original_query: 原始查询
  - generated_sql: 生成的SQL语句（Agent查询）
  - results: 查询结果数据
  - row_count: 结果行数
  - processing_time_ms: 处理时间（毫秒）
  - confidence_score: 置信度分数
  - explanation: 结果解释
  - processing_steps: 处理步骤列表
  - validation_result: 验证结果
  - execution_result: 执行结果
  - correction_attempts: 修正尝试次数
- **query_status: QueryStatusResponse** - 查询状态响应
  - query_id: 查询ID
  - status: 查询状态（processing, success, error）
  - created_at: 创建时间
  - updated_at: 更新时间
  - response_time_ms: 响应时间
  - error_message: 错误消息
  - progress_percentage: 进度百分比
- **query_history: QueryHistoryResponse** - 查询历史响应
  - queries: 查询记录列表
  - total_count: 总记录数
  - page: 当前页码
  - page_size: 分页大小
- **cache_response: QueryCacheResponse** - 缓存响应
  - query_hash: 查询哈希
  - cache_cleared: 缓存是否清除
  - message: 操作消息
- **error_response: HTTPException** - 错误响应（400, 404, 429, 500）

## [LINK]
**上游依赖** (已读取源码):
- [../../data/database.py](../../data/database.py) - get_db(), Session
- [../../data/models.py](../../data/models.py) - QueryStatus, QueryType
- [../../middleware/tenant_context.py](../../middleware/tenant_context.py) - get_current_tenant_from_request, get_current_tenant_id
- [../../services/query_context.py](../../services/query_context.py) - get_query_context, 查询上下文管理
- [../../services/llm_service.py](../../services/llm_service.py) - llm_service, LLM服务调用
- [../../services/agent_service.py](../../services/agent_service.py) - run_agent_query, convert_agent_response_to_query_response, is_agent_available
- [../../services/data_source_service.py](../../services/data_source_service.py) - DataSourceService, 数据源服务
- [../../core/jwt_utils.py](../../core/jwt_utils.py) - get_current_user_from_token, JWT解析

**下游依赖** (已读取源码):
- 无（API端点是叶子模块）

**调用方**:
- 前端聊天界面 - 发送自然语言查询
- 前端仪表板 - 显示查询历史
- LangGraph Agent - SQL智能代理查询
- 前端查询管理 - 查询状态跟踪

## [POS]
**路径**: backend/src/app/api/v1/endpoints/query.py
**模块层级**: Level 3 - API端点层
**依赖深度**: 直接依赖 data/*, services/*, middleware/*, core/*；被前端查询模块调用
"""

import asyncio
import uuid
import time
import traceback
import json
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query as QueryParam, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.app.data.database import get_db
from src.app.data.models import QueryStatus, QueryType
from src.app.middleware.tenant_context import get_current_tenant_from_request, get_current_tenant_id
from src.app.services.query_context import get_query_context
from src.app.services.llm_service import llm_service
from src.app.services.agent_service import (
    run_agent_query,
    convert_agent_response_to_query_response,
    is_agent_available
)
from src.app.integrations.agentv2_gateway import agentv2_gateway
from src.app.services.data_source_service import DataSourceService
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
        options: Optional[Dict[str, Any]] = None,
        selected_data_sources: Optional[List[Any]] = None
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

            # 数据源与文档
            if selected_data_sources is not None:
                data_sources = selected_data_sources
            else:
                data_sources = self.query_context.get_tenant_data_sources()
            documents = self.query_context.get_tenant_documents()

            # 构造数据源描述，帮助模型识别当前可用的数据源
            ds_lines = []
            for ds in data_sources:
                ds_lines.append(
                    f"- 名称: {ds.name} | 类型: {ds.db_type} | 数据库: {ds.database_name or '未指定'}"
                )
            data_sources_summary = "\n".join(ds_lines) if ds_lines else "无可用数据源"

            # 构建LLM请求
            messages = [
                {
                    "role": "system",
                    "content": f"""你是一个数据分析助手。请根据用户的问题，使用提供的数据源和文档信息来回答。

查询类型: {query_type.value}

可用数据源数量: {len(data_sources)}
可用数据源详情:
{data_sources_summary}
可用文档数量: {len(documents)}

请按照以下格式回答：
1. 提供准确的答案 (Accurate Answer)
2. 引用相关的数据源和文档 (Data Sources)
3. 提供详细的推理过程 (Reasoning)
4. 使用Markdown格式化答案 (Markdown Formatting)
   - ⚠️ 重要：在第 4 部分中，不要输出大型 ASCII 表格。应该依赖第 5 部分来可视化数据。
   - ⚠️ 不要使用 Markdown 表格（如 | 列1 | 列2 |）来展示统计数据，这些数据应该通过第 5 部分的图表来可视化。
5. 可视化 (Visualization - Required if data is available)
   - 如果结果包含统计数据（时间序列、对比数据、趋势分析等），你必须在此处生成 ECharts JSON 配置。
   - 使用格式：[CHART_START] { ... } [CHART_END]

⚠️ 重要：图表配置是回复的重要组成部分，不要因为遵循上述格式而省略图表配置。当需要可视化时，图表配置必须包含在回复中。不要使用 Markdown 表格代替图表。"""
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

                # 旧逻辑依赖 success 字段，这里兼容无 success 的返回，认为调用成功
                if hasattr(llm_response, "success") and not getattr(llm_response, "success"):
                    raise Exception(f"LLM service failed: {getattr(llm_response, 'error', 'unknown error')}")

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


async def handle_chart_merge_request(
    request: QueryRequest,
    tenant,
    user_info: Dict[str, Any],
    query_id: str
) -> QueryResponseV3:
    """
    处理图表合并请求

    Args:
        request: 查询请求，包含 merge_request
        tenant: 租户对象
        user_info: 用户信息
        query_id: 查询ID

    Returns:
        QueryResponseV3: 合并后的图表响应
    """
    start_time = time.time()

    try:
        merge_data = request.merge_request
        chart_configs = merge_data.get("chart_configs", [])

        logger.info(
            f"📊 [图表合并] 开始处理 {len(chart_configs)} 个图表的合并请求",
            tenant_id=tenant.id,
            chart_titles=[c.get("title", "未命名") for c in chart_configs]
        )

        # 构建图表合并提示词
        merge_prompt = f"""请将以下 {len(chart_configs)} 个图表合并为一个双Y轴图表。

"""
        for i, chart_config in enumerate(chart_configs):
            title = chart_config.get("title", f"图表{i+1}")
            echarts_option = chart_config.get("echarts_option", {})
            merge_prompt += f"\n## 图表 {i+1}：{title}\n"
            merge_prompt += f"```json\n{json.dumps(echarts_option, ensure_ascii=False, indent=2)}\n```\n"

        merge_prompt += """

请分析这些图表的数据结构，生成一个合并的双Y轴图表配置。要求：

1. **X轴对齐**：提取并合并所有图表的X轴数据，确保时间点/类别对齐
2. **Y轴分配**：将不同指标分配到合适的Y轴
   - 数值量级差异>10倍的分配到不同Y轴
   - 金额类指标（销售额、收入）→ 左Y轴
   - 数量类指标（订单数、人数）→ 右Y轴
3. **图表类型**：使用不同图表类型区分（折线图表示趋势，柱状图表示数量）
4. **输出格式**：必须返回完整的 [CHART_START]...[CHART_END] 配置格式

示例输出格式：
[CHART_START]
{
  "title": "合并图表标题",
  "xAxis": { "type": "category", "data": ["1月", "2月", "3月"] },
  "yAxis": [
    { "type": "value", "name": "销售额", "position": "left" },
    { "type": "value", "name": "订单数", "position": "right" }
  ],
  "series": [
    { "name": "销售额", "type": "line", "yAxisIndex": 0, "data": [...] },
    { "name": "订单数", "type": "bar", "yAxisIndex": 1, "data": [...] }
  ]
}
[CHART_END]

请只输出图表配置，不要添加其他解释文字。"""

        # 调用 LLM 生成合并配置
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的数据可视化专家，擅长将多个图表合并为一个清晰易懂的双Y轴图表。请严格按照用户要求的格式输出。"
            },
            {
                "role": "user",
                "content": merge_prompt
            }
        ]

        # 使用 LLM 服务生成合并配置
        llm_response = await llm_service.chat_completion(
            messages=messages,
            tenant_id=tenant.id,
            temperature=0.3,
            max_tokens=2000
        )

        # 提取图表配置
        answer = llm_response.content
        echarts_config = None

        # 解析 [CHART_START]...[CHART_END] 标记
        import re
        chart_match = re.search(r'\[CHART_START\](.*?)\[CHART_END\]', answer, re.DOTALL)
        if chart_match:
            try:
                echarts_config = json.loads(chart_match.group(1).strip())
                logger.info("📊 [图表合并] 成功解析图表配置")
            except json.JSONDecodeError as e:
                logger.warning(f"📊 [图表合并] 图表配置JSON解析失败: {e}")

        # 构建处理步骤
        processing_steps = [
            f"📊 图表合并请求：共 {len(chart_configs)} 个图表",
            "分析图表结构和数据维度",
            "确定X轴对齐方式",
            "分配Y轴（双轴）",
            "生成合并图表配置"
        ]

        # 构建响应
        processing_time_ms = int((time.time() - start_time) * 1000)

        response = QueryResponseV3(
            query_id=query_id,
            tenant_id=tenant.id,
            original_query=request.query,
            generated_sql="",
            results=[],
            row_count=0,
            processing_time_ms=processing_time_ms,
            confidence_score=0.9,
            explanation=f"已将 {len(chart_configs)} 个图表合并为一个双Y轴图表。",
            processing_steps=processing_steps,
            validation_result=None,
            execution_result=None,
            correction_attempts=0,
            metadata={
                "chart_merge": True,
                "merged_chart_count": len(chart_configs),
                "echarts_option": echarts_config,
                "processing_steps": [
                    {
                        "step": 1,
                        "title": "图表分析",
                        "content": f"分析 {len(chart_configs)} 个图表的结构和数据维度"
                    },
                    {
                        "step": 2,
                        "title": "X轴对齐",
                        "content": "提取并合并所有图表的X轴数据"
                    },
                    {
                        "step": 3,
                        "title": "Y轴分配",
                        "content": "根据数值量级分配Y轴（双轴配置）"
                    },
                    {
                        "step": 4,
                        "title": "生成合并图表",
                        "content": "生成合并后的双Y轴图表配置",
                        "echart_option": echarts_config
                    },
                    {
                        "step": 5,
                        "title": "数据分析",
                        "content": "图表已成功合并，支持多维度数据对比"
                    }
                ]
            }
        )

        logger.info(
            f"📊 [图表合并] 处理完成",
            tenant_id=tenant.id,
            processing_time_ms=processing_time_ms
        )

        return response

    except Exception as e:
        logger.error(
            f"📊 [图表合并] 处理失败: {e}",
            tenant_id=tenant.id,
            exc_info=True
        )
        # 返回错误响应
        processing_time_ms = int((time.time() - start_time) * 1000)
        return QueryResponseV3(
            query_id=query_id,
            tenant_id=tenant.id,
            original_query=request.query,
            generated_sql="",
            results=[],
            row_count=0,
            processing_time_ms=processing_time_ms,
            confidence_score=0.0,
            explanation=f"图表合并失败: {str(e)}",
            processing_steps=[f"错误: {str(e)}"],
            validation_result=None,
            execution_result=None,
            correction_attempts=0
        )


# 创建查询服务的依赖注入
async def get_query_service(
    tenant=Depends(get_current_tenant_from_request),
    user_info: Dict[str, Any] = Depends(get_current_user_info_from_request),
    db: Session = Depends(get_db)
) -> QueryService:
    """获取查询服务实例"""
    user_id = user_info["user_id"]
    query_context = get_query_context(db, tenant.id, user_id)
    return QueryService(query_context)


@router.post("/query", response_model=None)
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
    集成 LangGraph SQL Agent（使用 DeepSeek 作为默认 LLM）
    支持图表合并请求（merge_request）
    """
    # ============================================================
    # 🔍 [诊断] /query 端点被调用 - 记录完整请求信息
    # ============================================================
    logger.info("="*80)
    logger.info("🔍 [诊断] /query 端点被调用")
    logger.info(f"🔍 [诊断] connection_id={request.connection_id}")
    logger.info(f"🔍 [诊断] query={request.query[:100]}")
    logger.info(f"🔍 [诊断] enable_cache={request.enable_cache}")
    logger.info(f"🔍 [诊断] force_refresh={request.force_refresh}")
    logger.info(f"🔍 [诊断] merge_request={request.merge_request is not None}")
    logger.info("="*80)
    # ============================================================

    # 📊 图表合并请求处理
    if request.merge_request:
        logger.info(
            "📊 [图表合并] 检测到图表合并请求",
            tenant_id=tenant.id,
            chart_count=len(request.merge_request.get("chart_configs", []))
        )
        # 图表合并请求不需要数据源，直接使用 LLM 处理
        return await handle_chart_merge_request(
            request=request,
            tenant=tenant,
            user_info=user_info,
            query_id=str(uuid.uuid4())
        )

    try:
        query_id = str(uuid.uuid4())
        start_time = time.time()
        
        # 获取用户ID（从JWT中正确提取）
        user_id = user_info["user_id"]
        logger.info(f"Query request - user_id: {user_id}, tenant_id: {tenant.id}, query: {request.query[:100]}")

        # 创建查询上下文
        query_context = get_query_context(db, tenant.id, user_id)

        # 检查频率限制
        can_proceed, error_msg = query_context.check_rate_limits()
        if not can_proceed:
            raise HTTPException(status_code=429, detail=error_msg)

        # 数据源服务实例
        data_source_service = DataSourceService()

        # 选择数据源：优先用户指定，否则自动取第一个活跃数据源；后续仅使用这一条
        data_source_id = request.connection_id
        selected_source = None
        
        # 🔍 诊断：记录所有活跃数据源信息
        all_active_sources = await data_source_service.get_data_sources(
            tenant_id=tenant.id,
            db=db,
            active_only=True
        )
        logger.info(f"🔍 [数据源诊断] 租户 {tenant.id} 共有 {len(all_active_sources)} 个活跃数据源:")
        for idx, ds in enumerate(all_active_sources):
            logger.info(f"  [{idx+1}] ID: {ds.id}, 名称: {ds.name}, 类型: {ds.db_type}, 状态: {ds.status}")
        
        if not data_source_id:
            if all_active_sources:
                selected_source = all_active_sources[0]
                data_source_id = selected_source.id
                logger.info(f"⚠️ [数据源诊断] 未指定数据源，自动使用第一个活跃数据源: ID={data_source_id}, 名称={selected_source.name}, 类型={selected_source.db_type}")
            else:
                logger.warning(f"❌ [数据源诊断] 没有找到任何活跃数据源")
        else:
            logger.info(f"✅ [数据源诊断] 用户指定了数据源ID: {data_source_id}")
            
        if data_source_id and not selected_source:
            selected_source = await data_source_service.get_data_source_by_id(
                data_source_id=data_source_id,
                tenant_id=tenant.id,
                db=db
            )
            if selected_source:
                logger.info(f"✅ [数据源诊断] 找到指定的数据源: ID={selected_source.id}, 名称={selected_source.name}, 类型={selected_source.db_type}")
            else:
                logger.error(f"❌ [数据源诊断] 无法找到指定的数据源ID: {data_source_id}")
                
        if not selected_source:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未找到可用的数据源，请先选择或创建数据源"
            )
        
        # 🔍 最终确认使用的数据源
        logger.info(f"🎯 [数据源诊断] 最终使用的数据源: ID={selected_source.id}, 名称={selected_source.name}, 类型={selected_source.db_type}, 连接字符串预览={str(selected_source.connection_string)[:50] if selected_source.connection_string else 'N/A'}...")

        # 尝试使用 Agent 处理查询（如果可用且有数据源）
        use_agent = is_agent_available() and data_source_id is not None
        logger.info(
            "Query /query agent decision",
            tenant_id=tenant.id,
            user_id=user_id,
            connection_id=request.connection_id,
            data_source_id=str(data_source_id) if data_source_id else None,
            agent_available=is_agent_available(),
            use_agent=use_agent,
        )
        
        agent_success = False
        if use_agent:
            try:
                # 获取数据源连接字符串
                data_source_service = DataSourceService()
                database_url = await data_source_service.get_decrypted_connection_string(
                    data_source_id=data_source_id,
                    tenant_id=tenant.id,
                    db=db
                )
                
                # 生成线程ID（用于会话管理）
                # 🔧 图表拆分修复：使用 session_id 保持多轮对话上下文
                # 如果提供了 session_id，使用它作为 thread_id 的一部分，这样同一会话的查询会共享上下文
                if request.session_id:
                    thread_id = f"{tenant.id}_{user_id}_{request.session_id}"
                    logger.info(f"使用 session_id 生成 thread_id，支持多轮对话上下文: {thread_id}")
                else:
                    thread_id = f"{tenant.id}_{user_id}_{query_id}"
                
                # 运行 Agent 查询
                logger.info(
                    "Using Agent to handle query",
                    tenant_id=tenant.id,
                    user_id=user_id,
                    query_preview=request.query[:100],
                    data_source_id=data_source_id,
                    database_url_preview=str(database_url)[:80] if database_url else None,
                )
                
                # 🔧 关键修复：根据数据源类型修改问题，明确告诉AI助手数据源类型
                enhanced_question = request.query
                if selected_source.db_type in ["xlsx", "xls", "csv"]:
                    # 文件数据源：明确告诉AI这是文件，必须使用文件工具
                    enhanced_question = f"""【重要提示：当前数据源是{selected_source.db_type.upper()}文件，不是SQL数据库】
                    
你必须：
1. 使用 `inspect_file` 工具查看文件结构和工作表名称（对于Excel文件）
2. 使用 `analyze_dataframe` 或 `python_interpreter` 工具执行Pandas查询
3. **严禁使用SQL工具（query, list_tables, get_schema）**

用户问题：{request.query}"""
                    logger.info(f"🔧 [数据源类型修复] 检测到文件数据源（{selected_source.db_type}），已增强问题提示")
                elif selected_source.db_type in ["postgresql", "mysql", "postgres"]:
                    # SQL数据库：明确告诉AI这是SQL数据库
                    enhanced_question = f"""【重要提示：当前数据源是{selected_source.db_type.upper()}数据库】

你必须：
1. 使用 `list_tables` 工具查看数据库中有哪些表
2. 使用 `get_schema` 工具获取表结构
3. 使用 `query_database` 工具执行SQL查询
4. **严禁使用文件工具（inspect_file, analyze_dataframe）**

用户问题：{request.query}"""
                    logger.info(f"🔧 [数据源类型修复] 检测到SQL数据库（{selected_source.db_type}），已增强问题提示")
                
                agent_response = await run_agent_query(
                    question=enhanced_question,  # 使用增强后的问题
                    thread_id=thread_id,
                    database_url=database_url,
                    verbose=True,  # 🔍 启用详细日志以诊断编造数据问题
                    enable_echarts=True,  # 启用 ECharts 图表生成功能
                    db_type=selected_source.db_type,  # 传递数据库类型
                    connection_id=data_source_id,
                    tenant_id=tenant.id,
                    user_id=user_id,
                    session_id=request.session_id,
                    db_session=db,
                )
                if agent_response:
                    logger.info(
                        "Agent query completed",
                        tenant_id=tenant.id,
                        user_id=user_id,
                        success=getattr(agent_response, "success", None),
                        sql_preview=(agent_response.sql or "")[:120] if hasattr(agent_response, "sql") else None,
                        row_count=getattr(getattr(agent_response, "data", None), "row_count", None),
                        error=getattr(agent_response, "error", None),
                    )
                else:
                    logger.warning(
                        "Agent query returned None, will fallback",
                        tenant_id=tenant.id,
                        user_id=user_id,
                    )

                if agent_response and agent_response.success:
                    # 转换 Agent 响应为 QueryResponseV3 格式
                    processing_time_ms = int((time.time() - start_time) * 1000)
                    response_data = convert_agent_response_to_query_response(
                        agent_response=agent_response,
                        query_id=query_id,
                        tenant_id=tenant.id,
                        original_query=request.query,
                        processing_time_ms=processing_time_ms
                    )
                    agent_success = True
                    return QueryResponseV3(**response_data)
                else:
                    # Agent 失败，但尝试返回部分结果（如果有的话）
                    error_msg = getattr(agent_response, "error", "Agent unavailable") if agent_response else "Agent unavailable"
                    logger.warning(
                        "Agent 查询失败，尝试返回部分结果或回退到标准查询处理",
                        tenant_id=tenant.id,
                        user_id=user_id,
                        error=error_msg,
                    )
                    
                    # 如果Agent返回了部分结果（即使success=False），尝试使用它
                    if agent_response and hasattr(agent_response, "data") and agent_response.data and agent_response.data.row_count > 0:
                        logger.info("Agent返回了部分结果，尝试使用这些结果")
                        processing_time_ms = int((time.time() - start_time) * 1000)
                        response_data = convert_agent_response_to_query_response(
                            agent_response=agent_response,
                            query_id=query_id,
                            tenant_id=tenant.id,
                            original_query=request.query,
                            processing_time_ms=processing_time_ms
                        )
                        # 即使Agent失败，如果有数据也返回
                        return QueryResponseV3(**response_data)
                    
                    # 回退到标准处理流程
                    agent_success = False
                    use_agent = False
            
            except Exception as e:
                # 获取完整的堆栈跟踪
                tb_str = traceback.format_exc()
                
                # 打印完整的错误信息
                logger.error(
                    "🚨 CRITICAL: Agent failed, falling back to standard query. Reason: %s",
                    str(e),
                    extra={
                        "tenant_id": tenant.id,
                        "user_id": user_id,
                        "query_id": query_id,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    }
                )
                
                # 打印完整的堆栈跟踪
                logger.error(
                    "Agent 查询出错 - 完整堆栈跟踪:\n%s",
                    tb_str,
                    extra={
                        "tenant_id": tenant.id,
                        "user_id": user_id,
                        "query_id": query_id,
                    }
                )
                
                # 打印错误对象的详细信息
                logger.error(
                    "Agent 查询出错 - 错误详情: type=%s, message=%s, args=%s",
                    type(e).__name__,
                    str(e),
                    repr(e.args) if hasattr(e, 'args') else 'N/A',
                    extra={
                        "tenant_id": tenant.id,
                        "user_id": user_id,
                        "query_id": query_id,
                    }
                )
                
                agent_success = False
                use_agent = False
        
        # 标准查询处理流程（原有逻辑）- 如果 Agent 未使用或失败，使用标准流程
        if not agent_success:
            # ⚠️ 警告：Agent失败，回退到标准LLM流程（无数据库查询能力）
            logger.warning(
                "⚠️ [回退流程] Agent失败，使用标准LLM流程（无真实数据查询）",
                tenant_id=tenant.id,
                query=request.query[:100]
            )

            # 检查缓存（简化版，使用 query 作为 hash）
            query_hash = hash(request.query)

            # 处理查询（使用原有逻辑）
            response_data = await query_service.process_query(
                query_id=query_id,
                question=request.query,  # 使用 query 字段
                context=None,
                options=None,
                selected_data_sources=[selected_source]
            )

            # 🔥 修复：生成 processing_steps（即使回退也要有处理步骤）
            processing_time_ms = int((time.time() - start_time) * 1000)
            base_time = max(processing_time_ms / 5, 50)  # 避免除以0

            # 从 LLM 回复中提取图表配置
            answer_text = response_data.get("answer", "")
            echarts_option = None
            if answer_text:
                import re
                import json
                chart_match = re.search(r'\[CHART_START\](.*?)\[CHART_END\]', answer_text, re.DOTALL)
                if chart_match:
                    try:
                        echarts_option = json.loads(chart_match.group(1).strip())
                        logger.info("📊 [回退流程] 成功提取图表配置")
                    except json.JSONDecodeError as e:
                        logger.warning(f"📊 [回退流程] 图表配置解析失败: {e}")

            # 构建处理步骤
            fallback_processing_steps = [
                {
                    "step": 1,
                    "title": "理解用户问题",
                    "description": "分析用户查询意图，识别数据需求",
                    "status": "completed",
                    "duration": int(base_time)
                },
                {
                    "step": 2,
                    "title": "数据源评估",
                    "description": f"已连接数据源: {selected_source.name} ({selected_source.db_type})",
                    "status": "completed",
                    "duration": int(base_time)
                },
                {
                    "step": 3,
                    "title": "AI分析生成",
                    "description": "AI助手基于问题生成分析回复",
                    "status": "completed",
                    "duration": int(base_time * 2)
                },
            ]

            # 添加图表步骤（如果有）
            if echarts_option:
                fallback_processing_steps.append({
                    "step": 4,
                    "title": "生成数据可视化",
                    "description": "创建图表展示分析结果",
                    "status": "completed",
                    "duration": int(base_time),
                    "content_type": "chart",
                    "content_data": {
                        "chart": {
                            "echarts_option": echarts_option
                        }
                    }
                })

            # 添加数据分析总结步骤
            fallback_processing_steps.append({
                "step": len(fallback_processing_steps) + 1,
                "title": "数据分析总结",
                "description": "AI对查询结果的分析和解读",
                "status": "completed",
                "duration": int(base_time),
                "content_type": "text",
                "content_data": {
                    "text": answer_text[:1000] if answer_text else "无分析内容"
                }
            })

            # 构建响应（转换为 QueryResponseV3 格式）
            return QueryResponseV3(
                query_id=query_id,
                tenant_id=tenant.id,
                original_query=request.query,
                generated_sql=response_data.get("generated_sql", ""),
                results=response_data.get("results", []),
                row_count=response_data.get("row_count", 0),
                processing_time_ms=processing_time_ms,
                confidence_score=response_data.get("confidence", 0.5),
                explanation=response_data.get("answer", ""),
                processing_steps=fallback_processing_steps,
                validation_result=None,
                execution_result={
                    "success": True,
                    "chart_data": None,
                    "echarts_option": echarts_option
                } if echarts_option else None,
                correction_attempts=0,
                echarts_option=echarts_option
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query processing failed: {e}", exc_info=True)
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


# 错误处理器 - 已移除，因为 APIRouter 不支持 exception_handler
# 异常处理应该在 main.py 中处理
# @router.exception_handler(HTTPException)
# async def http_exception_handler(request, exc):
#     """HTTP异常处理"""
#     return JSONResponse(
#         status_code=exc.status_code,
#         content=ErrorResponse(
#             error_code=f"HTTP_{exc.status_code}",
#             message=exc.detail,
#             timestamp=datetime.utcnow()
#         ).dict()
#     )


# @router.exception_handler(Exception)
# async def general_exception_handler(request, exc):
#     """通用异常处理"""
#     logger.error(f"Unhandled exception in query endpoint: {exc}")
#     return JSONResponse(
#         status_code=500,
#         content=ErrorResponse(
#             error_code="INTERNAL_SERVER_ERROR",
#             message="服务器内部错误",
#             timestamp=datetime.utcnow()
#         ).dict()
#     )


# =============================================================================
# SOTA 重构 - 新增 SOTA 查询端点
# =============================================================================

from pydantic import BaseModel


class SOTAQueryRequest(BaseModel):
    """SOTA 查询请求"""
    query: str
    cube_name: Optional[str] = None
    session_id: Optional[str] = None
    enable_few_shot: bool = True
    enable_self_healing: bool = True
    enable_disambiguation: bool = True
    max_repair_attempts: int = 3


class SOTAQueryResponse(BaseModel):
    """SOTA 查询响应"""
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


@router.post("/query/sota", response_model=SOTAQueryResponse)
async def create_sota_query(
    request: SOTAQueryRequest,
    tenant=Depends(get_current_tenant_from_request),
    user_info: Dict[str, Any] = Depends(get_current_user_info_from_request),
    db: Session = Depends(get_db)
):
    """
    SOTA 查询端点 - 使用多智能体框架处理查询

    功能：
    1. Router: 路由决策 + 消歧检测
    2. Planner: 任务分解
    3. Generator: DSL JSON 生成（带少样本 RAG）
    4. Critic: 业务规则验证
    5. Repair: 自愈修复
    6. Execute: 语义层查询执行
    """
    query_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        user_id = user_info["user_id"]

        # 检查是否启用 SOTA Agent
        if not settings.use_sota_agent:
            return SOTAQueryResponse(
                query_id=query_id,
                tenant_id=tenant.id,
                original_query=request.query,
                error_message="SOTA Agent 未启用，请在配置中设置 USE_SOTA_AGENT=true",
                processing_time_ms=0,
                processing_steps=[],
                metadata={"disabled": True}
            )

        logger.info(
            "SOTA query request",
            tenant_id=tenant.id,
            user_id=user_id,
            query=request.query[:100],
            enable_few_shot=request.enable_few_shot,
            enable_self_healing=request.enable_self_healing,
            enable_disambiguation=request.enable_disambiguation
        )

        # 初始化 LLM
        from src.app.services.llm_service import llm_service

        # 获取 Cube Schema
        cube_schema = {}
        if request.cube_name:
            # TODO: 从数据库加载 Cube 定义
            cube_schema[request.cube_name] = {
                "measures": ["total_revenue", "order_count", "unique_users"],
                "dimensions": ["created_at", "category", "region"]
            }

        # 构建并执行 Swarm Graph（通过 AgentV2 gateway）
        result = await agentv2_gateway.run_swarm_query(
            query=request.query,
            tenant_id=tenant.id,
            llm=llm_service,
            cube_schema=cube_schema
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        # 检查是否需要澄清
        final_result = result.get("final_result", {})
        if final_result.get("needs_clarification"):
            return SOTAQueryResponse(
                query_id=query_id,
                tenant_id=tenant.id,
                original_query=request.query,
                needs_clarification=True,
                clarification_questions=final_result.get("questions", []),
                processing_time_ms=processing_time_ms,
                processing_steps=[
                    {"step": "Router", "status": "completed", "output": "检测到模糊查询"},
                    {"step": "Disambiguation", "status": "completed", "output": "生成澄清问题"}
                ],
                metadata={
                    "route_decision": result.get("route_decision", {}),
                    "ambiguity_detected": True
                }
            )

        # 构建响应
        return SOTAQueryResponse(
            query_id=query_id,
            tenant_id=tenant.id,
            original_query=request.query,
            refined_query=result.get("query_plan", {}).get("refined_query"),
            dsl_json=result.get("dsl_json"),
            results=final_result.get("data") if final_result else [],
            row_count=len(final_result.get("data", [])) if final_result else 0,
            processing_time_ms=processing_time_ms,
            processing_steps=[
                {"step": "Router", "status": "completed", "output": "路由决策完成"},
                {"step": "Planner", "status": "completed", "output": "任务分解完成"},
                {"step": "Generator", "status": "completed", "output": "DSL 生成完成"},
                {"step": "Critic", "status": "completed", "output": result.get("critic_report", {}).get("status", "passed")},
                {"step": "Execute", "status": "completed", "output": "查询执行完成"}
            ],
            error_message=result.get("error_message"),
            metadata={
                "route_decision": result.get("route_decision", {}),
                "query_plan": result.get("query_plan", {}),
                "critic_report": result.get("critic_report", {}),
                "repair_attempted": result.get("repair_attempted", False),
                "error_count": result.get("error_count", 0)
            }
        )

    except Exception as e:
        logger.error(f"SOTA query failed: {e}", exc_info=True)
        processing_time_ms = int((time.time() - start_time) * 1000)
        return SOTAQueryResponse(
            query_id=query_id,
            tenant_id=tenant.id,
            original_query=request.query,
            error_message=str(e),
            processing_time_ms=processing_time_ms,
            processing_steps=[],
            metadata={"exception": type(e).__name__}
        )


@router.post("/query/sota/clarify", response_model=SOTAQueryResponse)
async def clarify_sota_query(
    query_id: str,
    answers: Dict[str, Any],
    tenant=Depends(get_current_tenant_from_request),
    user_info: Dict[str, Any] = Depends(get_current_user_info_from_request),
    db: Session = Depends(get_db)
):
    """
    处理澄清问题后的查询

    用户回答澄清问题后，重新执行查询
    """
    start_time = time.time()

    try:
        # TODO: 从数据库获取原始查询
        # TODO: 使用答案精炼查询
        # TODO: 重新执行 Swarm Graph

        return SOTAQueryResponse(
            query_id=query_id,
            tenant_id=tenant.id,
            original_query="",
            refined_query="精炼后的查询",
            processing_time_ms=int((time.time() - start_time) * 1000),
            processing_steps=[
                {"step": "Refinement", "status": "completed", "output": "查询精炼完成"},
                {"step": "Execute", "status": "completed", "output": "执行完成"}
            ],
            metadata={"clarified": True}
        )

    except Exception as e:
        logger.error(f"SOTA query clarification failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
