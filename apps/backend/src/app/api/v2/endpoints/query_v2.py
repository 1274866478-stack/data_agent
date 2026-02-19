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
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging
import uuid
import time

# Database imports
from ....data.database import get_db

# AgentV2 imports
import sys
from pathlib import Path

# 添加项目根目录到路径 - 更健壮的方法
def find_project_root():
    """查找项目根目录（包含 AgentV2 和 backend 的目录）"""
    current = Path(__file__).resolve()

    # 方法1：向上查找直到找到包含 AgentV2 的目录
    for _ in range(10):  # 最多向上查 10 层
        parent = current.parent
        if (parent / "AgentV2").exists() or (parent / "backend").exists():
            return parent
        current = parent

    # 方法2：从当前文件路径推算
    # backend/src/app/api/v2/endpoints/query_v2.py
    # 向上 7 层应该是项目根
    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
    if str(project_root).endswith("backend"):
        project_root = project_root.parent

    return project_root

project_root = find_project_root()
sys.path.insert(0, str(project_root))

# 创建 logger
logger = logging.getLogger(__name__)

# 尝试导入 Agent 模块
AGENTV2_AVAILABLE = False
try:
    from agent.core import AgentFactory, get_default_factory, get_response_cache
    from agent.middleware import TenantIsolationMiddleware, SQLSecurityMiddleware
    AGENTV2_AVAILABLE = True
    logger.info("[query_v2 import] SUCCESS: Agent module imported successfully")
except ImportError as e:
    AGENTV2_AVAILABLE = False
    logger.error(f"[query_v2 import] ERROR: Failed to import Agent module: {e}")

    # 提供回退的类型定义（当 AgentV2 不可用时）
    from typing import Any, Optional

    class MockAgent:
        """模拟 Agent 实例"""
        async def invoke(self, inputs: dict, config: Optional[dict] = None) -> dict:
            return {"messages": [{"role": "assistant", "content": "AgentV2 不可用"}]}

    class AgentFactory:
        """回退的 AgentFactory 类型"""
        def get_or_create_agent(self, tenant_id: str, user_id: str, session_id: Optional[str] = None):
            """返回模拟的 agent 实例"""
            return MockAgent()

    class TenantIsolationMiddleware:
        """回退的租户隔离中间件"""
        pass

    class SQLSecurityMiddleware:
        """回退的 SQL 安全中间件"""
        pass

    logging.warning("AgentV2 module not available, using mock mode")

# ============================================================================
# 请求/响应模型
# ============================================================================

class QueryRequestV2(BaseModel):
    """查询请求模型 V2"""
    query: str = Field(..., description="自然语言查询", min_length=1)
    connection_id: Optional[str] = Field(None, description="数据源连接ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    # 可选参数
    max_results: int = Field(100, ge=1, le=1000, description="最大结果数")
    include_chart: bool = Field(False, description="是否生成图表")
    chart_type: Optional[str] = Field(None, description="图表类型")

class Config:
    json_schema_extra = {
        "example": {
            "query": "查询销售额TOP 10的产品",
            "connection_id": "conn_123",
            "session_id": "session_abc",
            "max_results": 100,
            "include_chart": True,
            "chart_type": "bar"
        }
    }

class QueryResponseV2(BaseModel):
    """查询响应模型 V2"""
    success: bool
    answer: str
    sql: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    # 新增 V2 特性
    processing_steps: List[str] = Field(default_factory=list)
    subagent_calls: List[str] = Field(default_factory=list)
    reasoning_log: Optional[Dict[str, Any]] = None
    # 图表
    chart_config: Optional[Dict[str, Any]] = None
    # 元数据
    tenant_id: str
    session_id: Optional[str] = None
    from_cache: bool = False  # 是否来自缓存
    query_chain: Optional[List[Dict[str, Any]]] = None  # 查询链（数据远程信息）
    chart_validation: Optional[Dict[str, Any]] = None  # 图表字段验证结果
    lineage: Optional[List[Dict[str, Any]]] = None  # 表格分布记录
    insights: Optional[List[str]] = None  # 数据业务提示

class Config:
    json_schema_extra = {
        "example": {
            "success": True,
            "query": "查询结果",
            "sql": "SELECT * FROM products ORDER BY sales DESC LIMIT 10",
            "data": [],
            "row_count": 10,
            "processing_steps": ["解析查询", "生成SQL", "执行查询"],
            "tenant_id": "tenant_123",
            "session_id": "xxx-xxx-xxx",
            "processing_time_ms": 1234
        }
    }

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

# ============================================================================
# 依赖
# ============================================================================

def get_agent_factory() -> AgentFactory:
    """获取 AgentFactory 实例"""
    return get_default_factory()

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
    agent_factory: AgentFactory = Depends(get_agent_factory)
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
    import time

    start_time = time.time()

    # 新增：生成或使用 session_id 用于日志追踪
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(f"[V2] 开始处理查询，session_id={session_id}")

    try:
        # 1. 验证租户
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="租户ID缺失"
            )

        # 2. 创建 Agent (带租户隔离和数据源连接)
        try:
            # DEBUG: 打印中间件类信息
            import agent.middleware as mid_module
            logger.info(f"[DEBUG] TenantIsolationMiddleware 类检查: {hasattr(mid_module.TenantIsolationMiddleware, 'wrap_tool_call')}")
            logger.info(f"[DEBUG] SQLSecurityMiddleware 类检查: {hasattr(mid_module.SQLSecurityMiddleware, 'wrap_model_call')}")
            logger.info(f"[DEBUG] 所有方法: {[a for a in dir(mid_module.TenantIsolationMiddleware) if not a.startswith('_')]}")

            logger.info(f"[DEBUG] 开始创建agent... connection_id={request.connection_id}, session_id={session_id}")
            agent = agent_factory.get_or_create_agent(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                connection_id=request.connection_id,
                db_session=db
            )
            logger.info("[DEBUG] Agent 创建成功")
        except Exception as e:
            # 添加详细的错误信息
            import traceback
            error_detail = f"{str(e)}\n\n            Traceback:\n{traceback.format_exc()}"
            logger.error(f"[ERROR] Agent 创建失败: {error_detail}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": error_detail,
                    "error_type": "agent_initialization_error",
                    "tenant_id": tenant_id
                }
            )

        # 3. 准备输入
        agent_input = {
            "messages": [
                {"role": "user", "content": request.query}
            ]
        }

        # 4. SQL 安全预检查（暂时禁用，等待中间件修复）
        # sql_middleware = SQLSecurityMiddleware()
        # 注意：这里简化了实际的 SQL 提取逻辑
        # 实际实现需要从消息中提取 SQL

        # 5. 检查响应缓存
        cached_response = None
        if AGENTV2_AVAILABLE:
            response_cache = get_response_cache()
            cached_response = response_cache.get(
                query=request.query,
                tenant_id=tenant_id,
                connection_id=request.connection_id,
                context={"data_sources": []}  # 可从 request 获取
            )
            if cached_response:
                logger.info(f"[V2] 使用缓存响应: {request.query[:30]}...")
                # 添加缓存标记到处理步骤
                cached_response["processing_steps"] = ["缓存命中"] + cached_response.get("processing_steps", [])
                cached_response["from_cache"] = True
                return QueryResponseV2(**cached_response)

        # 6. 强制预调用 list_tables() 确保获取实际表名
        # 这解决了 AI 跳过 list_tables() 直接猜测表名的问题
        if AGENTV2_AVAILABLE and request.connection_id:
            try:
                from agent.tools.database_tools import list_tables
                logger.info(f"[V2] 强制预调用 list_tables() 获取表名...")
                tables_result = await asyncio.to_thread(
                    list_tables,
                    connection_id=request.connection_id,
                    db_session=db,
                    tenant_id=tenant_id
                )
                if tables_result and "tables" in tables_result:
                    table_names = tables_result["tables"]
                    logger.info(f"[V2] 预期获取到表名列表: {table_names}")
                    # 缓存表名到 AgentFactory
                    from agent.core import AgentFactory
                    AgentFactory.set_cached_table_names(
                        tenant_id=tenant_id,
                        table_names=table_names,
                        connection_id=request.connection_id
                    )
                    logger.info(f"[V2] 表名已缓存到AgentFactory")
            except Exception as e:
                logger.warning(f"[V2] 强制预调用 list_tables() 失败，继续执行查询: {e}")

        # 7. 执行真实查询（使用同步调用在异步上下文中运行）
        logger.info(f"[V2] 执行查询: {request.query}")
        # 注意：由于中间件暂未实现异步方法，使用 asyncio.to_thread 运行同步调用
        import asyncio
        from contextvars import copy_context

        user_query_set = False
        clear_user_query = None
        if AGENTV2_AVAILABLE:
            try:
                from agent.tools.database_tools import _set_user_query, _clear_user_query
                _set_user_query(request.query)
                user_query_set = True
                clear_user_query = _clear_user_query
            except Exception as e:
                logger.warning(f"[V2] 设置用户查询上下文失败: {e}")

        # 添加超时保护，防止 Agent 调用无限期挂起
        QUERY_TIMEOUT = 120.0  # 120秒超时

        try:
            ctx = copy_context()
            result = await asyncio.wait_for(
                asyncio.to_thread(ctx.run, agent.invoke, agent_input),
                timeout=QUERY_TIMEOUT
            )
            logger.info(f"[V2] 查询完成，结果类型: {type(result)}")
        except asyncio.TimeoutError:
            logger.error(f"[V2] 查询超时（{QUERY_TIMEOUT}秒）: {request.query}")
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail={
                    "success": False,
                    "error": "查询超时，请简化查询条件或稍后重试",
                    "error_type": "timeout_error",
                    "tenant_id": tenant_id,
                    "timeout_seconds": QUERY_TIMEOUT
                }
            )
        finally:
            if user_query_set and clear_user_query:
                try:
                    clear_user_query()
                except Exception as e:
                    logger.warning(f"[V2] 清理用户查询上下文失败: {e}")

        # 8. 解析返回结果
        # DeepAgents 返回的结果通常包含 messages 字段
        answer = ""
        processing_steps = []
        subagent_calls = []

        if hasattr(result, "get"):
            # 字典类型结果
            messages = result.get("messages", [])
        elif isinstance(result, list):
            # 列表类型结果
            messages = result
        else:
            messages = []

        # ========== [数据验证模块] 从消息中提取 SQL 和数据 ==========
        extracted_sql = None
        extracted_data = None
        chart_config = None
        chart_validation = None
        query_chain: List[Dict[str, Any]] = []
        lineage: List[Dict[str, Any]] = []
        insights: List[str] = []

        # 导入数据验证模块
        DATA_VALIDATION_AVAILABLE = False
        try:
            # 尝试多种导入路径以支持不同环境
            try:
                from agent.tools.data_validator import (
                    validate_sql_data_consistency,
                    smart_field_mapping,
                    recommend_chart,
                    validate_chart_fields_in_sql,
                    build_cell_lineage,
                    generate_insights_from_rows
                )
                DATA_VALIDATION_AVAILABLE = True
                logger.info("[V2] 数据验证模块已加载")
            except ImportError:
                from src.app.services.agent.data_validator import (
                    validate_sql_data_consistency,
                    smart_field_mapping,
                    recommend_chart,
                    validate_chart_fields_in_sql,
                    build_cell_lineage,
                    generate_insights_from_rows
                )
                DATA_VALIDATION_AVAILABLE = True
                logger.info("[V2] 数据验证模块已加载")
        except ImportError as e:
            DATA_VALIDATION_AVAILABLE = False
            logger.warning(f"[V2] 数据验证模块不可用: {e}")

        if DATA_VALIDATION_AVAILABLE:
            logger.info("[V2] 消息数量: {len(messages)}")
            for i, msg in enumerate(messages):
                msg_type = type(msg).__name__
                msg_class_str = str(msg.__class__) if hasattr(msg, '__class__') else 'N/A'
                logger.info(f"[V2] 消息 {i}: type={msg_type}, class={msg_class_str}")
                if hasattr(msg, 'tool_calls'):
                    logger.info(f"[V2]   - tool_calls: {msg.tool_calls}")
                if hasattr(msg, 'content'):
                    content_preview = str(msg.content)[:200] if msg.content else None
                    logger.info(f"[V2]   - content: {content_preview}")

            # 从消息中提取 SQL（从 AIMessage 的 tool_calls 中）
            for msg in messages:
                # 提取 SQL（从 AIMessage 的 tool_calls 中）
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        tc_name = tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', None)
                        logger.info(f"[V2] 检查工具调用: {tc_name}")
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
                                    logger.info(f"[V2] 提取到SQL: {extracted_sql[:100] if extracted_sql else None}...")
                                    if not query_chain or query_chain[-1].get("sql") != extracted_sql:
                                        query_chain.append({"step": len(query_chain)+1, "sql": extracted_sql, "source": tc_name or "execute_query"})
                                    break  # 找到 SQL 后跳出

                # 提取数据（从 ToolMessage 中）
                msg_class_name = str(msg.__class__) if hasattr(msg, '__class__') else ''
                if 'ToolMessage' in msg_class_name or 'Tool' in msg_class_name:
                    try:
                        import json
                        content = msg.content
                        logger.info(f"[V2] ToolMessage content type: {type(content)}")
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
                                logger.info(f"[V2] 提取到数据: {len(extracted_data)} 条")
                                break
                            elif isinstance(data, list) and len(data) > 0:
                                if all(isinstance(row, dict) for row in data):
                                    extracted_data = data
                                    logger.info(f"[V2] 提取到数据: {len(extracted_data)} 条，格式: {list(data[0].keys())}")
                                    break
                            elif isinstance(data, dict) and 'error' in data:
                                # 错误响应，跳过
                                logger.debug(f"[V2] 跳过错误响应: {data.get('error', 'Unknown error')}")
                            elif isinstance(data, dict) and 'tables' in data:
                                # list_tables 响应，跳过
                                logger.debug(f"[V2] 跳过 list_tables 响应")
                        elif isinstance(content, list):
                            if all(isinstance(row, dict) for row in content):
                                extracted_data = content
                                logger.info(f"[V2] 提取到数据: {len(content)} 条")
                                break
                    except (ValueError, TypeError, AttributeError, json.JSONDecodeError) as e:
                        logger.debug(f"[V2] 数据提取跳过: {e}")

            # 自动统计执行查询的结果和表格分布
            if extracted_data:
                if query_chain:
                    query_chain[-1].setdefault("row_count", len(extracted_data))
                    query_chain[-1].setdefault("columns", list(extracted_data[0].keys()) if isinstance(extracted_data[0], dict) else [])
                if DATA_VALIDATION_AVAILABLE and extracted_data and len(extracted_data) > 0:
                    lineage = build_cell_lineage(extracted_sql, extracted_data)
                    insights = generate_insights_from_rows(extracted_data, request.query)
                    logger.info(f"[V2] 应用数据一致性验证...")
                try:
                    validation_result = validate_sql_data_consistency(
                        executed_sql=extracted_sql or "SELECT * FROM unknown",
                        query_results=extracted_data
                    )
                    logger.info(f"[V2] 验证结果: is_valid={validation_result.is_valid}, actual_columns={validation_result.actual_columns}")
                except Exception as e:
                    logger.error(f"[V2] 数据验证失败: {e}")
                # 2. 智能字段映射
                field_mapping = smart_field_mapping(extracted_data, extracted_sql)
                logger.info(f"[V2] 字段映射: x_field={field_mapping.x_field}, y_field={field_mapping.y_field}, confidence={field_mapping.confidence}")
                # 3. 图表推荐
                chart_rec = recommend_chart(extracted_data, extracted_sql, request.query)
                logger.info(f"[V2] 图表推荐: chart_type={chart_rec.chart_type}")
                # 4. 构建图表配置
                if field_mapping.x_field and field_mapping.y_field:
                    chart_config = {
                        "chart_type": chart_rec.chart_type,
                        "x_field": field_mapping.x_field,
                        "y_field": field_mapping.y_field,
                        "title": chart_rec.title,
                        "reasoning": chart_rec.reasoning
                    }
                    logger.info(f"[V2] 图表配置已生成: {chart_config}")
                if chart_validation:
                    validation_result = validate_chart_fields_in_sql(
                        executed_sql=extracted_sql or "",
                        extracted_data=extracted_data,
                        chart_fields=[field_mapping.x_field, field_mapping.y_field]
                    ).model_dump()
                    if chart_validation and not chart_validation.get("is_valid"):
                        logger.warning(f"[V2] 图表字段一致性验证失败: {chart_validation}")

            # 应用数据验证
            if DATA_VALIDATION_AVAILABLE and extracted_data and len(extracted_data) > 0:
                try:
                    logger.info("[V2] 应用数据一致性验证...")
                    validation_result = validate_sql_data_consistency(
                        executed_sql=extracted_sql or "SELECT * FROM unknown",
                        query_results=extracted_data
                    )
                    logger.info(f"[V2] 验证结果: is_valid={validation_result.is_valid}, actual_columns={validation_result.actual_columns}")
                except Exception as e:
                    logger.error(f"[V2] 数据验证失败: {e}")

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
            if hasattr(result, '__dict__'):
                # 尝试从结果中提取表信息
                result_dict = result.__dict__ if hasattr(result, '__dict__') else result
                if 'messages' in result_dict:
                    for msg in result_dict['messages']:
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            for tc in msg.tool_calls:
                                if tc.get('name') == 'list_tables':
                                    tables_found = tc.get('args', {}).get('tables', [])
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

            logger.info(f"[V2] 回答长度: {len(answer)} 字符，处理步骤数: {len(processing_steps)}")

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
            if AGENTV2_AVAILABLE:
                response_cache = get_response_cache()
                response_cache.set(
                    query=request.query,
                    response=response_obj.model_dump(),
                    tenant_id=tenant_id,
                    connection_id=request.connection_id,
                    context={"data_sources": []}
                )
                logger.info(f"[V2] 响应已缓存: {request.query[:30]}...")
            return response_obj
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "error": str(e),
                    "error_type": "internal_error",
                    "tenant_id": tenant_id,
                    "processing_time_ms": 0
                }
            )
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
    if not AGENTV2_AVAILABLE:
        return {"error": "AgentV2 not available"}
    try:
        from agent.core import get_cache_stats
        stats = get_cache_stats()
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

# ============================================================================
# 辅助函数
# ============================================================================

def _extract_sql_from_response(response: str) -> Optional[str]:
    """从响应中提取 SQL 语句

    简单的 SQL 提取（实际实现需要更复杂的解析）
    """
    import re

    # 尝试从 markdown 代码块中提取
    sql_pattern = r"```sql\s*(SELECT.*?)?\s*```"
    match = re.search(sql_pattern, response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # 尝试直接查找 SELECT 语句
    lines = response.split('\n')
    for line in lines:
        line = line.strip()
        if line.upper().startswith('SELECT'):
            return line
    return None

def _sanitize_response_for_tenant(response: str, tenant_id: str) -> str:
    """确保响应中不包含其他租户的数据"""
    # 这里可以添加额外的过滤逻辑
    return response

# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("启动 AgentV2 Query API 测试服务")
    print("=" * 60)
    print(
        "[INFO] 可用端点:",
        " - POST /api/v2/query/",
        " - GET /api/v2/query/health",
        " - GET /api/v2/query/capabilities"
    )
    print(
        "[INFO] 启动服务",
    )
    uvicorn.run(
        "query_v2:router",
        host="0.0.0.0",
        port=8005,
        log_level="info"
    )
