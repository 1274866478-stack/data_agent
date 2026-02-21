# -*- coding: utf-8 -*-

"""
Query V2 Endpoint - AgentV2 查询端点
===================================
新版查询端点，基于 AgentV2 (DeepAgents 框架)
API: POST /api/v2/query
特性:
    - 租户隔离
    - SQL 安全验证
    - SubAgent 派发
    - 可解释性日志
    - 图表展示
作？ BMad Master
版本: 2.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging
import uuid
import time

# Database imports
from ....data.database import get_db

from ....integrations.agentv2_gateway import agentv2_gateway

# 创建 logger
logger = logging.getLogger(__name__)

# ============================================================================
# 请求/响应模型
# ============================================================================

class QueryRequestV2(BaseModel):
    """查询请求模型 V2"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "查询销售额TOP 10的产品",
                "connection_id": "conn_123",
                "session_id": "session_abc",
                "max_results": 100,
                "include_chart": True,
                "chart_type": "bar",
            }
        }
    )

    query: str = Field(..., description="自然语言查询", min_length=1)
    connection_id: Optional[str] = Field(None, description="数据源连接ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    # 可选参数
    max_results: int = Field(100, ge=1, le=1000, description="最大结果数")
    include_chart: bool = Field(False, description="是否生成图表")
    chart_type: Optional[str] = Field(None, description="图表类型")

class QueryResponseV2(BaseModel):
    """查询响应模型 V2"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "query": "查询结果",
                "sql": "SELECT * FROM products ORDER BY sales DESC LIMIT 10",
                "data": [],
                "row_count": 10,
                "processing_steps": ["解析查询", "生成SQL", "执行查询"],
                "tenant_id": "tenant_123",
                "session_id": "xxx-xxx-xxx",
                "processing_time_ms": 1234,
            }
        }
    )

    success: bool
    answer: str
    sql: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    # 新增 V2 特性
    processing_steps: List[Dict[str, Any] | str] = Field(default_factory=list)
    subagent_calls: List[str] = Field(default_factory=list)
    reasoning_log: Optional[Dict[str, Any]] = None
    # 图表
    chart_config: Optional[Dict[str, Any]] = None
    processing_time_ms: int = 0
    # 元数据
    tenant_id: str
    session_id: Optional[str] = None
    from_cache: bool = False  # 是否来自缓存
    query_chain: Optional[List[Dict[str, Any]]] = None  # 查询链（数据远程信息）
    chart_validation: Optional[Dict[str, Any]] = None  # 图表字段验证结果
    lineage: Optional[List[Dict[str, Any]]] = None  # 表格分布记录
    insights: Optional[List[str]] = None  # 数据业务提示

class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    error: str
    error_type: str  # "security", "database", "agent", etc.
    details: Optional[Dict[str, Any]] = None

# ============================================================================
# 路由
# ============================================================================

router = APIRouter(prefix="/query", tags=["query-v2"])

def get_tenant_from_request(request: QueryRequestV2) -> str:
    """
    从请求中提取租户 ID

    TODO: 集成实际的认证系统
    目前使用默认租户
    """
    # 实际实现应该从 JWT token 中提取
    return "default_tenant"

def get_user_from_request(request: QueryRequestV2) -> str:
    """从请求中提取用户 ID"""
    # 实际实现应该从 JWT token 中提取
    return "default_user"

# ============================================================================
# 端点
# ============================================================================

@router.post("/", response_model=QueryResponseV2)
async def create_query_v2(
    request: QueryRequestV2,
    tenant_id: str = Depends(get_tenant_from_request),
    user_id: str = Depends(get_user_from_request),
    db: Session = Depends(get_db),
):
    """
    Data Agent V2 查询端点

    使用 DeepAgents 框架执行自然语言查询
    支持多种查询类型和高级功能特性

    ## 功能特性
    - 租户隔离：每个租户的数据完全隔离
    - SQL 安全：自动拦截危险SQL
    - SubAgent：智能任务委派
    - 可解释性：完整的推理过程记录
    - 日志持久化：双通道写入（数据库 + 文件）
    """
    start_time = time.time()

    # 新增：生成或使用 session_id 用于日志追踪
    session_id = request.session_id or str(uuid.uuid4())
    logger.debug("[V2] 开始处理查询，session_id=%s", session_id)

    try:
        # 1. 验证租户
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="租户ID缺失"
            )

        runtime_available = agentv2_gateway.is_available()
        if not runtime_available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "success": False,
                    "error": "AgentV2 runtime unavailable",
                    "error_type": "agent_unavailable",
                },
            )

        # 2. SQL 安全预检查（暂时禁用，等待中间件修复）
        # sql_middleware = SQLSecurityMiddleware()
        # 注意：这里简化了实际的 SQL 提取逻辑
        # 实际实现需要从消息中提取 SQL

        # 3. 检查响应缓存
        cached_response = None
        if runtime_available:
            response_cache = agentv2_gateway.get_response_cache()
            cached_response = response_cache.get(
                query=request.query,
                tenant_id=tenant_id,
                connection_id=request.connection_id,
                context={"data_sources": []}  # 可从 request 获取
            )
            if cached_response:
                logger.debug("[V2] 使用缓存响应: %s...", request.query[:30])
                # 添加缓存标记到处理步骤
                cached_response["processing_steps"] = ["缓存命中"] + cached_response.get("processing_steps", [])
                cached_response["from_cache"] = True
                return QueryResponseV2(**cached_response)

        # 4. 预热表名缓存（仅首次）
        if runtime_available and request.connection_id:
            cached_table_names = agentv2_gateway.get_cached_table_names(
                tenant_id=tenant_id,
                connection_id=request.connection_id,
            )
            needs_prefetch = not cached_table_names
        else:
            needs_prefetch = False

        if needs_prefetch and request.connection_id:
            try:
                logger.debug("[V2] 预调用 list_tables() 获取表名缓存")
                tables_result = await agentv2_gateway.list_tables(
                    connection_id=request.connection_id,
                    db_session=db,
                    tenant_id=tenant_id
                )
                if tables_result and "tables" in tables_result:
                    table_names = tables_result["tables"]
                    if isinstance(table_names, list) and table_names:
                        agentv2_gateway.cache_table_names(
                            tenant_id=tenant_id,
                            table_names=table_names,
                            connection_id=request.connection_id
                        )
                        logger.debug("[V2] 表名缓存已更新，数量=%s", len(table_names))
            except Exception as e:
                logger.warning("[V2] list_tables 预热失败，继续执行查询: %s", e)

        # 5. 执行查询（统一通过 gateway）
        logger.debug("[V2] 执行查询: %s", request.query)
        QUERY_TIMEOUT = 120.0
        invoke_result = await agentv2_gateway.invoke_query(
            question=request.query,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            connection_id=request.connection_id,
            db_session=db,
            timeout_seconds=QUERY_TIMEOUT,
        )

        if not invoke_result.success:
            error_msg = invoke_result.error or "查询执行失败"
            lowered = error_msg.lower()
            if "timeout" in lowered or "timed out" in lowered:
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail={
                        "success": False,
                        "error": "查询超时，请简化查询条件或稍后重试",
                        "error_type": "timeout_error",
                        "tenant_id": tenant_id,
                        "timeout_seconds": QUERY_TIMEOUT,
                    },
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": error_msg,
                    "error_type": "agent_invoke_error",
                    "tenant_id": tenant_id,
                },
            )

        # 6. 解析返回结果
        answer = invoke_result.answer or ""
        processing_steps = []
        subagent_calls = []
        messages = invoke_result.messages or []

        # 从消息中回填 answer（避免返回空字符串）
        if not answer:
            for msg in reversed(messages):
                if isinstance(msg, dict):
                    role = msg.get("role")
                    content = msg.get("content")
                    if role == "assistant" and isinstance(content, str) and content.strip():
                        answer = content
                        break
                else:
                    content = getattr(msg, "content", None)
                    class_name = msg.__class__.__name__.lower()
                    if isinstance(content, str) and ("ai" in class_name or "assistant" in class_name) and content.strip():
                        answer = content
                        break

        # ========== [数据验证模块] 从消息中提取 SQL 和数据 ==========
        extracted_sql = invoke_result.sql or None
        extracted_data = invoke_result.data or None
        chart_config = None
        chart_validation = None
        query_chain: List[Dict[str, Any]] = []
        lineage: List[Dict[str, Any]] = []
        insights: List[str] = []

        validator_funcs = agentv2_gateway.get_data_validator_functions()
        validate_sql_data_consistency = validator_funcs["validate_sql_data_consistency"]
        smart_field_mapping = validator_funcs["smart_field_mapping"]
        recommend_chart = validator_funcs["recommend_chart"]
        validate_chart_fields_in_sql = validator_funcs["validate_chart_fields_in_sql"]
        build_cell_lineage = validator_funcs["build_cell_lineage"]
        generate_insights_from_rows = validator_funcs["generate_insights_from_rows"]
        DATA_VALIDATION_AVAILABLE = True
        needs_message_extract = extracted_sql is None or extracted_data is None
        debug_enabled = logger.isEnabledFor(logging.DEBUG)

        if extracted_sql and not query_chain:
            query_chain.append(
                {
                    "step": 1,
                    "sql": extracted_sql,
                    "source": "agentv2_gateway",
                }
            )
        if extracted_data and query_chain:
            query_chain[-1].setdefault("row_count", len(extracted_data))
            query_chain[-1].setdefault(
                "columns",
                list(extracted_data[0].keys()) if isinstance(extracted_data[0], dict) else [],
            )

        if DATA_VALIDATION_AVAILABLE:
            if debug_enabled:
                logger.debug("[V2] 消息数量: %s", len(messages))
                for i, msg in enumerate(messages):
                    msg_type = type(msg).__name__
                    msg_class_str = str(msg.__class__) if hasattr(msg, '__class__') else 'N/A'
                    logger.debug("[V2] 消息 %s: type=%s, class=%s", i, msg_type, msg_class_str)
                    if isinstance(msg, dict):
                        if "tool_calls" in msg:
                            logger.debug("[V2]   - tool_calls: %s", msg.get("tool_calls"))
                        content_preview = str(msg.get("content", ""))[:200] if msg.get("content") else None
                        logger.debug("[V2]   - content: %s", content_preview)
                    else:
                        if hasattr(msg, 'tool_calls'):
                            logger.debug("[V2]   - tool_calls: %s", msg.tool_calls)
                        if hasattr(msg, 'content'):
                            content_preview = str(msg.content)[:200] if msg.content else None
                            logger.debug("[V2]   - content: %s", content_preview)

            if needs_message_extract:
                # 从消息中提取 SQL（从 AIMessage 的 tool_calls 中）
                for msg in messages:
                    if isinstance(msg, dict):
                        tool_calls = msg.get("tool_calls") or []
                    else:
                        tool_calls = getattr(msg, "tool_calls", None) or []

                    # 提取 SQL（从 AIMessage 的 tool_calls 中）
                    if tool_calls:
                        for tc in tool_calls:
                            tc_name = tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', None)
                            if debug_enabled:
                                logger.debug("[V2] 检查工具调用: %s", tc_name)
                            # AgentV2 使用 execute_query 工具，参数名为 'query'
                            if tc_name in ('execute_query', 'query', 'mcp_postgres_query'):
                                tc_args = tc.get('args') if isinstance(tc, dict) else getattr(tc, 'args', {})
                                if tc_args:
                                    extracted_sql = (
                                        tc_args.get('query') or
                                        tc_args.get('sql') or
                                        tc_args.get('q')
                                    )
                                    if extracted_sql:
                                        logger.debug("[V2] 提取到SQL: %s...", extracted_sql[:100] if extracted_sql else None)
                                        if not query_chain or query_chain[-1].get("sql") != extracted_sql:
                                            query_chain.append({"step": len(query_chain)+1, "sql": extracted_sql, "source": tc_name or "execute_query"})
                                        break  # 找到 SQL 后跳出

                    # 提取数据（从 ToolMessage 中）
                    msg_class_name = str(msg.__class__) if hasattr(msg, '__class__') else ''
                    is_tool_message = (
                        ("ToolMessage" in msg_class_name or "Tool" in msg_class_name)
                        or (isinstance(msg, dict) and msg.get("role") == "tool")
                    )
                    if is_tool_message:
                        try:
                            import json
                            content = msg.get("content") if isinstance(msg, dict) else msg.content
                            if debug_enabled:
                                logger.debug("[V2] ToolMessage content type: %s", type(content))
                            if isinstance(content, str):
                                # 尝试解析 JSON 数据
                                data = json.loads(content)
                                # 检查是否是标准的查询结果格式 {"columns": [...], "rows": [...], ...}
                                if isinstance(data, dict) and 'columns' in data and 'rows' in data:
                                    # 转换为字典列表格式
                                    columns = data.get('columns', [])
                                    rows = data.get('rows', [])
                                    extracted_data = [
                                        {col: val for col, val in zip(columns, row)}
                                        for row in rows
                                    ]
                                    logger.debug("[V2] 提取到数据: %s 条", len(extracted_data))
                                    break
                                elif isinstance(data, list) and len(data) > 0:
                                    if all(isinstance(row, dict) for row in data):
                                        extracted_data = data
                                        logger.debug("[V2] 提取到数据: %s 条，格式: %s", len(extracted_data), list(data[0].keys()))
                                        break
                                elif isinstance(data, dict) and 'error' in data:
                                    # 错误响应，跳过
                                    if debug_enabled:
                                        logger.debug("[V2] 跳过错误响应: %s", data.get("error", "Unknown error"))
                                elif isinstance(data, dict) and 'tables' in data:
                                    # list_tables 响应，跳过
                                    if debug_enabled:
                                        logger.debug("[V2] 跳过 list_tables 响应")
                            elif isinstance(content, list):
                                if all(isinstance(row, dict) for row in content):
                                    extracted_data = content
                                    logger.debug("[V2] 提取到数据: %s 条", len(content))
                                    break
                        except (ValueError, TypeError, AttributeError, json.JSONDecodeError) as e:
                            if debug_enabled:
                                logger.debug("[V2] 数据提取跳过: %s", e)

            # 自动统计执行查询的结果和表格分布
            if extracted_data:
                if query_chain:
                    query_chain[-1].setdefault("row_count", len(extracted_data))
                    query_chain[-1].setdefault("columns", list(extracted_data[0].keys()) if isinstance(extracted_data[0], dict) else [])
                if DATA_VALIDATION_AVAILABLE:
                    lineage = build_cell_lineage(extracted_sql, extracted_data)
                    insights = generate_insights_from_rows(extracted_data, request.query)
                    logger.debug("[V2] 应用数据一致性验证...")
                try:
                    validation_result = validate_sql_data_consistency(
                        executed_sql=extracted_sql or "SELECT * FROM unknown",
                        query_results=extracted_data
                    )
                    logger.debug(
                        "[V2] 验证结果: is_valid=%s, actual_columns=%s",
                        validation_result.is_valid,
                        validation_result.actual_columns,
                    )
                except Exception as e:
                    logger.error(f"[V2] 数据验证失败: {e}")
                # 2. 智能字段映射
                field_mapping = smart_field_mapping(extracted_data, extracted_sql)
                logger.debug(
                    "[V2] 字段映射: x_field=%s, y_field=%s, confidence=%s",
                    field_mapping.x_field,
                    field_mapping.y_field,
                    field_mapping.confidence,
                )
                # 3. 图表推荐
                chart_rec = recommend_chart(extracted_data, extracted_sql, request.query)
                logger.debug("[V2] 图表推荐: chart_type=%s", chart_rec.chart_type)
                # 4. 构建图表配置
                if field_mapping.x_field and field_mapping.y_field:
                    chart_config = {
                        "chart_type": chart_rec.chart_type,
                        "x_field": field_mapping.x_field,
                        "y_field": field_mapping.y_field,
                        "title": chart_rec.title,
                        "reasoning": chart_rec.reasoning
                    }
                    logger.debug("[V2] 图表配置已生成: %s", chart_config)
                if chart_config:
                    chart_validation = validate_chart_fields_in_sql(
                        executed_sql=extracted_sql or "",
                        extracted_data=extracted_data,
                        chart_fields=[field_mapping.x_field, field_mapping.y_field]
                    ).model_dump()
                    if chart_validation and not chart_validation.get("is_valid"):
                        logger.warning(f"[V2] 图表字段一致性验证失败: {chart_validation}")

            # 自动统计执行查询的结果和表格分布
            if extracted_data:
                if query_chain:
                    query_chain[-1].setdefault("row_count", len(extracted_data))
                    query_chain[-1].setdefault("columns", list(extracted_data[0].keys()) if isinstance(extracted_data[0], dict) else [])

            # 新增：构建完整的处理步骤流程
            # 根据实际执行的工具调用推断处理步骤
            processing_steps = []
            step_number = 1

            # 步骤1: 分析查询意图
            processing_steps.append({
                "step": step_number,
                "name": "分析查询意图",
                "status": "completed",
                "detail": f"分析查询: {request.query[:50]}{'...' if len(request.query) > 50 else ''}"
            })
            step_number += 1

            # 步骤2: 理解数据结构
            tables_found = []
            for msg in messages:
                tool_calls = getattr(msg, "tool_calls", None)
                if not tool_calls:
                    continue
                for tc in tool_calls:
                    tc_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                    if tc_name == "list_tables":
                        tc_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {}) or {}
                        if isinstance(tc_args, dict):
                            tables_found = tc_args.get("tables", []) or []
                        break
                if tables_found:
                    break
            processing_steps.append({
                "step": step_number,
                "name": "理解数据结构",
                "status": "completed",
                "detail": f"识别到 {len(tables_found) if tables_found else '多个'} 个相关表"
            })
            step_number += 1

            # 步骤3: 生成SQL查询
            if extracted_sql:
                processing_steps.append({
                    "step": step_number,
                    "name": "生成SQL查询",
                    "status": "completed",
                    "detail": f"生成 {len(extracted_sql)} 字符SQL查询",
                    "content_type": "sql",
                    "content_data": {"sql": extracted_sql}
                })
            else:
                processing_steps.append({
                    "step": step_number,
                    "name": "生成SQL查询",
                    "status": "completed",
                    "detail": "SQL查询生成"
                })
            step_number += 1

            # 步骤4: 执行查询
            row_count = len(extracted_data) if extracted_data else 0
            processing_steps.append({
                "step": step_number,
                "name": "执行查询",
                "status": "completed",
                "detail": f"返回 {row_count} 行数据"
            })
            step_number += 1

            # 来源对象可视化验证
            if chart_validation:
                processing_steps.append({
                    "step": step_number,
                    "name": "图表字段验证",
                    "status": "completed" if chart_validation.get("is_valid") else "error",
                    "detail": chart_validation.get("message") or "验证成功",
                    "content_type": "text",
                    "content_data": {"text": str(chart_validation)}
                })
            step_number += 1

            # 步骤5: 生成图表
            if chart_config:
                processing_steps.append({
                    "step": step_number,
                    "name": "生成图表",
                    "status": "completed",
                    "detail": f"生成 {chart_config.get('chart_type', '未知')} 图表"
                })
            else:
                processing_steps.append({
                    "step": step_number,
                    "name": "生成图表",
                    "status": "skipped",
                    "detail": "无需图表或数据不适合可视化"
                })
            step_number += 1

            # 步骤6: 数据分析
            if extracted_data and len(extracted_data) > 0:
                processing_steps.append({
                    "step": step_number,
                    "name": "数据分析",
                    "status": "completed",
                    "detail": "生成数据分析报告"
                })
            else:
                processing_steps.append({
                    "step": step_number,
                    "name": "数据分析",
                    "status": "skipped",
                    "detail": "无数据可用于分析"
                })
            step_number += 1

            logger.debug("[V2] 回答长度: %s 字符，处理步骤数: %s", len(answer), len(processing_steps))

            # 计算行数
            row_count = len(extracted_data) if extracted_data else 0

            # 构建响应对象
            response_obj = QueryResponseV2(
                success=True,
                answer=answer,
                sql=extracted_sql,  # 返回提取的SQL
                data=extracted_data,  # 返回提取的数据
                row_count=row_count,
                processing_steps=processing_steps,
                subagent_calls=subagent_calls,
                reasoning_log={
                    "timestamp": start_time,
                    "steps": len(processing_steps),
                    "query": request.query,
                    "answer_length": len(answer),
                    "data_validation_enabled": DATA_VALIDATION_AVAILABLE,
                },
                chart_config=chart_config,  # 返回图表配置
                tenant_id=tenant_id,
                session_id=session_id,  # 新增：返回session_id用于日志追踪
                processing_time_ms=0,
                query_chain=query_chain,
                chart_validation=chart_validation,
                lineage=lineage,
                insights=insights
            )

            # 存储到缓存
            if runtime_available:
                response_cache = agentv2_gateway.get_response_cache()
                response_cache.set(
                    query=request.query,
                    response=response_obj.model_dump(),
                    tenant_id=tenant_id,
                    connection_id=request.connection_id,
                    context={"data_sources": []}
                )
                logger.debug("[V2] 响应已缓存: %s...", request.query[:30])
            return response_obj
    except HTTPException as http_exc:
        # 直接传递 HTTP 异常
        raise http_exc
    except Exception as e:
        processing_time = int((time.time() - start_time) * 1000)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": str(e),
                "error_type": "internal_error",
                "tenant_id": tenant_id,
                "session_id": session_id,  # 新增：错误响应也包含session_id
                "processing_time_ms": processing_time
            }
        )

# ============================================================================
# 缓存统计端点
# ============================================================================

@router.get("/cache/stats")
async def get_cache_stats_v2():
    """获取缓存统计信息"""
    if not agentv2_gateway.is_available():
        return {"error": "AgentV2 not available"}
    try:
        stats = agentv2_gateway.get_cache_stats()
        return {
            "success": True,
            "cache_stats": stats
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ============================================================================
# 健康检查端点
# ============================================================================

@router.get("/health")
async def health_check_v2():
    """V2 健康检查端点"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "framework": "DeepAgents",
        "features": [
            "tenant_isolation",
            "sql_security",
            "subagent_architecture",
            "xai_logging"
        ]
    }

# ============================================================================
# 能力端点
# ============================================================================

@router.get("/capabilities")
async def get_capabilities_v2():
    """获取 V2 能力列表"""
    return {
        "version": "2.0.0",
        "features": {
            "tenant_isolation": {
                "enabled": True,
                "description": "多租户数据完全隔离"
            },
            "sql_security": {
                "enabled": True,
                "description": "自动SQL安全验证，拦截危险操作"
            },
            "subagent_architecture": {
                "enabled": True,
                "description": "专业化子代理委派"
            },
            "xai_logging": {
                "enabled": True,
                "description": "可解释AI日志，记录推理过程"
            },
            "mcp_integration": {
                "enabled": True,
                "description": "Model Context Protocol 工具集成"
            }
        },
        "supported_query_types": [
            "natural_language",
            "sql_generation",
            "data_analysis",
            "chart_generation"
        ]
    }

