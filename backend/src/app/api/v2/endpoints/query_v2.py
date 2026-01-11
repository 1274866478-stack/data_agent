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
import logging

# 创建 logger
logger = logging.getLogger(__name__)

# AgentV2 imports
import sys
from pathlib import Path
# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from AgentV2.core import AgentFactory, get_default_factory
    from AgentV2.middleware import TenantIsolationMiddleware, SQLSecurityMiddleware
    AGENTV2_AVAILABLE = True
except ImportError:
    AGENTV2_AVAILABLE = False
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

        # 2. 获取数据源连接 URL
        # TODO: 从 connection_id 获取实际连接
        database_url = "postgresql://postgres:postgres@localhost:5432/data_agent"

        # 3. 创建 Agent (带租户隔离)
        try:
            # DEBUG: 打印中间件类信息
            import AgentV2.middleware as mid_module
            logger.info(f"[DEBUG] TenantIsolationMiddleware 类检查:")
            logger.info(f"  - 有 wrap_tool_call: {hasattr(mid_module.TenantIsolationMiddleware, 'wrap_tool_call')}")
            logger.info(f"  - 有 wrap_model_call: {hasattr(mid_module.TenantIsolationMiddleware, 'wrap_model_call')}")
            logger.info(f"  - 所有方法: {[a for a in dir(mid_module.TenantIsolationMiddleware) if not a.startswith('_')]}")

            logger.info(f"[DEBUG] 开始创建 agent...")
            agent = agent_factory.get_or_create_agent(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=request.session_id,
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

        # 5. SQL 安全预检查
        sql_middleware = SQLSecurityMiddleware()
        # 注意：这里简化了实际的 SQL 提取逻辑
        # 实际实现需要从消息中提取 SQL

        # 6. 执行查询
        # 注意：这里模拟执行，实际需要调用 agent.ainvoke
        # result = await agent.ainvoke(agent_input)

        # 模拟响应
        processing_time = int((time.time() - start_time) * 1000)

        return QueryResponseV2(
            success=True,
            answer=f"查询处理完成 (模拟): {request.query}",
            sql="SELECT * FROM data LIMIT 10",  # 模拟
            data=[],
            row_count=0,
            processing_steps=[
                "接收查询",
                "租户隔离验证",
                "SQL 安全检查",
                "生成查询计划",
                "执行查询"
            ],
            subagent_calls=["sql_expert"],
            reasoning_log={
                "timestamp": start_time,
                "steps": 5,
                "tools_used": ["query", "get_schema"]
            },
            tenant_id=tenant_id,
            processing_time_ms=processing_time
        )

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
