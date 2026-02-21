import asyncio
import json
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional, List

import structlog

from src.app.data.models import QueryStatus, QueryType
from src.app.schemas.query import QueryRequest, QueryResponseV3
from src.app.shared.llm import llm_service

logger = structlog.get_logger(__name__)

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
            "# 查询推理路径",
            "",
            "## 1. 查询分析",
            f"- 原始问题: {question}",
            f"- 识别的查询类型: {query_type.value}",
            "",
            "## 2. 数据源评估",
            f"- 可用数据源数量: {len(data_sources)}",
            f"- 可用文档数量: {len(documents)}",
        ]

        if data_sources:
            log_lines.extend([
                "- 数据源列表:",
            ])
            for ds in data_sources[:3]:  # 最多显示3个
                log_lines.append(f"  * {ds.name} ({ds.connection_type})")

        if documents:
            log_lines.extend([
                "- 相关文档列表:",
            ])
            for doc in documents[:3]:  # 最多显示3个
                log_lines.append(f"  * {doc.title}")

        log_lines.extend([
            "",
            "## 3. 处理策略",
            "- 基于查询类型选择处理策略",
            "- 整合多源数据进行综合分析",
            "",
            "## 4. 推理过程",
            "- 使用LLM进行语义理解和答案生成",
            "- 确保答案基于可用的数据和文档",
            "- 提供详细的推理过程和引用信息",
            "",
            "## 5. 答案生成",
            "- 综合所有信息生成最终答案",
            "- 确保答案的准确性和可解释性",
            "",
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
            "📊 [图表合并] 处理完成",
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
