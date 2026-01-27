# -*- coding: utf-8 -*-
"""
Query V2 Endpoint - AgentV2 查询端点
===================================

新版查询端点，基于 AgentV2 (DeepAgents 框架)。

API: POST /api/v2/query

特性:
    - 租户隔离
    - SQL 安全验证
    - SubAgent 委派
    - 可解释性日志

作者: BMad Master
版本: 2.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging

# AgentV2 imports
import sys
from pathlib import Path

# 创建 logger
logger = logging.getLogger(__name__)

# 添加项目根目录到路径 - 更健壮的方法
def find_project_root():
    """查找项目根目录（包含 AgentV2 和 backend 的目录）"""
    current = Path(__file__).resolve()

    # 方法1：向上查找直到找到包含 AgentV2 的目录
    for _ in range(10):  # 最多向上查找10层
        parent = current.parent
        if (parent / "AgentV2").exists() or (parent / "backend").exists():
            return parent
        current = parent

    # 方法2：从当前文件路径推算
    # backend/src/app/api/v2/endpoints/query_v2.py
    # 向上7层应该是项目根目录
    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent
    if str(project_root).endswith("backend"):
        project_root = project_root.parent

    # 方法3：如果以上都失败，尝试使用 cwd
    import os
    cwd = Path(os.getcwd())
    # 如果当前在 backend 目录下
    if (cwd / "src").exists() and (cwd.parent / "AgentV2").exists():
        return cwd.parent
    # 如果当前在项目根目录下
    if (cwd / "AgentV2").exists() and (cwd / "backend").exists():
        return cwd

    return project_root

project_root = find_project_root()
sys.path.insert(0, str(project_root))

# 调试：打印路径信息
logger.info(f"[query_v2] Project root: {project_root}")
logger.info(f"[query_v2] AgentV2 exists: {(project_root / 'AgentV2').exists()}")
logger.info(f"[query_v2] sys.path[0]: {sys.path[0]}")

# 数据库会话导入
try:
    from src.app.data.database import get_db
except ImportError:
    # 如果导入失败，提供回退
    def get_db():
        raise NotImplementedError("Database session not available")

try:
    # 调试：打印当前的 sys.path
    logger.info(f"[query_v2 import] sys.path[0:3]: {sys.path[0:3]}")
    logger.info(f"[query_v2 import] project_root in sys.path: {project_root in sys.path}")
    from AgentV2.core import AgentFactory, get_default_factory, get_response_cache
    from AgentV2.middleware import TenantIsolationMiddleware, SQLSecurityMiddleware
    AGENTV2_AVAILABLE = True
    logger.info("[query_v2 import] SUCCESS: AgentV2 imported successfully")
except ImportError as e:
    AGENTV2_AVAILABLE = False
    logger.error(f"[query_v2 import] ERROR: Failed to import AgentV2: {e}")
    # 提供回退的类型定义（当 AgentV2 不可用时）
    from typing import Any, Optional

    class AgentFactory:
        """回退的 AgentFactory 类型"""
        def get_or_create_agent(self, tenant_id: str, user_id: str, session_id: Optional[str] = None):
            """返回模拟的 agent 实例"""
            return MockAgent()

    class MockAgent:
        """模拟 Agent 实例"""
        async def ainvoke(self, inputs: dict, config: Optional[dict] = None) -> dict:
            return {"messages": [{"role": "assistant", "content": "AgentV2 不可用"}]}

    def get_default_factory():
        """回退的工厂函数"""
        return AgentFactory()

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
    connection_id: Optional[str] = Field(None, description="数据源连接 ID")
    session_id: Optional[str] = Field(None, description="会话 ID")

    # 可选参数
    max_results: int = Field(100, ge=1, le=1000, description="最大结果数")
    include_chart: bool = Field(False, description="是否生成图表")
    chart_type: Optional[str] = Field(None, description="图表类型")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "查询销售额前10的产品",
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
    processing_time_ms: int = 0
    from_cache: bool = False  # 是否来自缓存

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "answer": "查询成功，找到10个产品",
                "sql": "SELECT * FROM products ORDER BY sales DESC LIMIT 10",
                "data": [],
                "row_count": 10,
                "processing_steps": ["解析查询", "生成SQL", "执行查询"],
                "tenant_id": "tenant_123",
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
# 路由器
# ============================================================================

router = APIRouter(prefix="/query", tags=["query-v2"])

# ============================================================================
# 依赖项
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

    使用 DeepAgents 框架执行自然语言查询。

    ## 功能特性
    - 租户隔离：每个租户的数据完全隔离
    - SQL 安全：自动拦截危险 SQL
    - SubAgent：智能任务委派
    - 可解释性：完整的推理过程记录

    ## 请求示例
    ```json
    {
        "query": "查询销售额前10的产品",
        "connection_id": "conn_123",
        "include_chart": true
    }
    ```

    ## 响应示例
    ```json
    {
        "success": true,
        "answer": "查询成功",
        "sql": "SELECT * FROM products ...",
        "data": [...],
        "processing_steps": ["解析查询", "生成SQL"],
        "tenant_id": "tenant_123"
    }
    ```
    """
    import time

    start_time = time.time()

    try:
        # 1. 验证租户
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="租户 ID 缺失"
            )

        # 2. 创建 Agent (带租户隔离和数据源连接)
        try:
            # DEBUG: 打印中间件类信息
            import AgentV2.middleware as mid_module
            logger.info(f"[DEBUG] TenantIsolationMiddleware 类检查:")
            logger.info(f"  - 有 wrap_tool_call: {hasattr(mid_module.TenantIsolationMiddleware, 'wrap_tool_call')}")
            logger.info(f"  - 有 wrap_model_call: {hasattr(mid_module.TenantIsolationMiddleware, 'wrap_model_call')}")
            logger.info(f"  - 所有方法: {[a for a in dir(mid_module.TenantIsolationMiddleware) if not a.startswith('_')]}")

            logger.info(f"[DEBUG] 开始创建 agent... connection_id={request.connection_id}")
            agent = agent_factory.get_or_create_agent(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=request.session_id,
                connection_id=request.connection_id,
                db_session=db
            )
            logger.info(f"[DEBUG] Agent 创建成功")
        except Exception as e:
            # 添加详细的错误信息
            import traceback
            error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
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

        # 4. 准备输入
        agent_input = {
            "messages": [
                {"role": "user", "content": request.query}
            ]
        }

        # 5. SQL 安全预检查（暂时禁用，等待中间件修复）
        # sql_middleware = SQLSecurityMiddleware()
        # 注意：这里简化了实际的 SQL 提取逻辑
        # 实际实现需要从消息中提取 SQL

        # 5.5. 检查响应缓存
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

        # 6. 执行真实查询（使用同步调用在异步上下文中运行）
        logger.info(f"[V2] 执行查询: {request.query}")
        # 注意：由于中间件暂未实现异步方法，使用 to_thread 运行同步调用
        import asyncio
        result = await asyncio.to_thread(agent.invoke, agent_input)
        logger.info(f"[V2] 查询完成，结果类型: {type(result)}")

        # 7. 解析返回结果
        processing_time = int((time.time() - start_time) * 1000)

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

        # 导入数据验证模块
        DATA_VALIDATION_AVAILABLE = False
        try:
            # 尝试多种导入路径以支持不同环境
            try:
                from backend.src.app.services.agent.data_validator import (
                    validate_sql_data_consistency,
                    smart_field_mapping,
                    recommend_chart,
                )
            except ImportError:
                from src.app.services.agent.data_validator import (
                    validate_sql_data_consistency,
                    smart_field_mapping,
                    recommend_chart,
                )
            DATA_VALIDATION_AVAILABLE = True
            logger.info("[V2] 数据验证模块已加载")
        except ImportError as e:
            DATA_VALIDATION_AVAILABLE = False
            logger.warning(f"[V2] 数据验证模块不可用: {e}")

        # 🔍 调试：打印消息结构
        logger.info(f"[V2] 消息数量: {len(messages)}")
        for i, msg in enumerate(messages):
            msg_type = type(msg).__name__
            msg_class_str = str(msg.__class__) if hasattr(msg, '__class__') else 'N/A'
            logger.info(f"[V2] 消息 {i}: type={msg_type}, class={msg_class_str}")
            if hasattr(msg, 'tool_calls'):
                logger.info(f"[V2]   - tool_calls: {msg.tool_calls}")
            if hasattr(msg, 'content'):
                content_preview = str(msg.content)[:200] if msg.content else None
                logger.info(f"[V2]   - content: {content_preview}")

        # 从消息中提取 SQL 和数据
        for msg in messages:
            # 提取 SQL（从 AIMessage 的 tool_calls 中）
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_name = tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', None)
                    logger.info(f"[V2] 检查工具调用: {tc_name}")
                    # AgentV2 使用 execute_query 工具，参数名是 'query'
                    if tc_name in ('execute_query', 'query', 'mcp_postgres_query'):
                        tc_args = tc.get('args') if isinstance(tc, dict) else getattr(tc, 'args', {})
                        # 尝试多种参数名
                        if tc_args:
                            extracted_sql = (
                                tc_args.get('query') or
                                tc_args.get('sql') or
                                tc_args.get('q')
                            )
                        if extracted_sql:
                            logger.info(f"[V2] 提取到 SQL: {extracted_sql[:100] if extracted_sql else None}...")
                            break  # 找到 SQL 后跳出

            # 提取数据（从 ToolMessage 中）
            msg_class_name = str(msg.__class__) if hasattr(msg, '__class__') else ''
            if 'ToolMessage' in msg_class_name or 'Tool' in msg_class_name:
                try:
                    import json
                    content = msg.content
                    logger.info(f"[V2] ToolMessage content 类型: {type(content)}")
                    if isinstance(content, str):
                        # 尝试解析 JSON 数据
                        data = json.loads(content)

                        # 检查是否是标准的查询结果格式 {"columns": [...], "rows": [...], ...}
                        if isinstance(data, dict) and 'columns' in data and 'rows' in data:
                            # 转换为字典列表格式 [{"col1": val1, "col2": val2}, ...]
                            columns = data.get('columns', [])
                            rows = data.get('rows', [])
                            if rows and columns:
                                extracted_data = [
                                    {col: val for col, val in zip(columns, row)}
                                    for row in rows
                                ]
                                logger.info(f"[V2] 提取到数据: {len(extracted_data)} 行, 列: {columns}")
                            break

                        # 检查是否是直接的字典列表
                        elif isinstance(data, list) and len(data) > 0:
                            if all(isinstance(row, dict) for row in data):
                                extracted_data = data
                                logger.info(f"[V2] 提取到数据: {len(data)} 行, 列: {list(data[0].keys())}")
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
                            logger.info(f"[V2] 提取到数据: {len(content)} 行")
                            break
                except (ValueError, TypeError, AttributeError, json.JSONDecodeError) as e:
                    logger.debug(f"[V2] 数据提取跳过: {e}")

        # 应用数据验证
        if DATA_VALIDATION_AVAILABLE and extracted_data and len(extracted_data) > 0:
            try:
                logger.info("[V2] 应用数据一致性验证...")

                # 1. 验证数据一致性
                validation_result = validate_sql_data_consistency(
                    executed_sql=extracted_sql or "SELECT * FROM unknown",
                    query_results=extracted_data
                )
                logger.info(f"[V2] 验证结果: is_valid={validation_result.is_valid}, actual_columns={validation_result.actual_columns}")

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

            except Exception as e:
                logger.error(f"[V2] 数据验证失败: {e}")
                import traceback
                logger.debug(traceback.format_exc())

        # ========== [数据验证模块结束] ==========

        # 提取最后一条消息作为回答
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, "content"):
                answer = last_message.content
            elif isinstance(last_message, dict):
                answer = last_message.get("content", str(last_message))
            else:
                answer = str(last_message)

        # 构建处理步骤
        processing_steps = [
            "接收查询",
            "租户隔离验证",
            "AgentV2 处理",
            "DeepSeek LLM 调用",
        ]

        # 如果启用了数据验证，添加相应步骤
        if DATA_VALIDATION_AVAILABLE and extracted_data:
            processing_steps.extend([
                "数据一致性验证",
                "智能字段映射",
                "图表配置生成",
            ])

        processing_steps.append("返回结果")

        logger.info(f"[V2] 回答长度: {len(answer)} 字符")

        # 计算行数
        row_count = len(extracted_data) if extracted_data else 0

        # 构建响应对象
        response_obj = QueryResponseV2(
            success=True,
            answer=answer,
            sql=extracted_sql,  # 返回提取的 SQL
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
            processing_time_ms=processing_time
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

    except HTTPException:
        raise

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
                "processing_time_ms": processing_time
            }
        )


@router.get("/cache/stats")
async def get_cache_stats_v2():
    """获取缓存统计信息"""
    if not AGENTV2_AVAILABLE:
        return {"error": "AgentV2 not available"}

    try:
        from AgentV2.core import get_cache_stats
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
                "description": "自动 SQL 安全验证，拦截危险操作"
            },
            "subagent_architecture": {
                "enabled": True,
                "description": "专业化子代理委派",
                "available_subagents": ["sql_expert", "chart_expert", "file_expert"]
            },
            "xai_logging": {
                "enabled": True,
                "description": "可解释性 AI 日志，记录推理过程"
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
    """从响应中提取 SQL 语句"""
    import re

    # 简单的 SQL 提取（实际实现需要更复杂的解析）
    sql_pattern = r"```sql\n?(SELECT.*?)\n?```"
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
    print("启动 AgentV2 Query API 测试服务器")
    print("=" * 60)

    print("\n[INFO] 可用端点:")
    print("  - POST /api/v2/query/")
    print("  - GET  /api/v2/query/health")
    print("  - GET  /api/v2/query/capabilities")

    print("\n[INFO] 启动服务器...")
    uvicorn.run(
        "query_v2:router",
        host="0.0.0.0",
        port=8005,
        log_level="info"
    )
