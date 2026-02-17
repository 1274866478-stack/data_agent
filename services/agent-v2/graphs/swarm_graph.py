"""
Swarm Graph - 多智能体状态图

实现 Router → Planner → Generator → Critic → Repair 编排
"""

from typing import TypedDict, Literal, Dict, Any, Optional
from langgraph.graph import StateGraph, END

# 尝试不同的导入路径
try:
    from ..subagents.router_agent import RouterAgent
    from ..subagents.planner_agent import PlannerAgent
    from ..subagents.generator_agent import GeneratorAgent
    from ..subagents.critic_agent import CriticAgent
    from ..subagents.repair_agent import RepairAgent
except ImportError:
    try:
        from AgentV2.subagents.router_agent import RouterAgent
        from AgentV2.subagents.planner_agent import PlannerAgent
        from AgentV2.subagents.generator_agent import GeneratorAgent
        from AgentV2.subagents.critic_agent import CriticAgent
        from AgentV2.subagents.repair_agent import RepairAgent
    except ImportError:
        # 直接导入（在同一目录下运行时）
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from subagents.router_agent import RouterAgent
        from subagents.planner_agent import PlannerAgent
        from subagents.generator_agent import GeneratorAgent
        from subagents.critic_agent import CriticAgent
        from subagents.repair_agent import RepairAgent


class ChatBiState(TypedDict):
    """Swarm Agent 状态定义"""
    # 输入
    query: str
    tenant_id: str

    # 中间状态
    route_decision: dict              # Router 输出
    query_plan: dict                  # Planner 输出
    dsl_json: dict                    # Generator 输出
    critic_report: dict               # Critic 输出

    # 控制标志
    needs_regeneration: bool
    repair_attempted: bool
    error_count: int
    error_message: str

    # 输出
    final_result: dict
    cube_schema: dict                 # Cube 定义


def build_swarm_graph(llm=None, cube_schema: dict = None):
    """
    构建 Swarm Agent 状态图

    Args:
        llm: LLM 实例
        cube_schema: Cube 定义

    Returns:
        编译后的状态图
    """
    # 初始化 Agents
    router = RouterAgent("router", llm)
    planner = PlannerAgent("planner", llm)
    generator = GeneratorAgent("generator", llm)
    critic = CriticAgent("critic", llm)
    repair = RepairAgent("repair", llm)

    # ========== 定义节点 ==========

    async def router_node(state: ChatBiState) -> ChatBiState:
        """路由节点"""
        result = await router.execute(state)
        state.update(result)
        return state

    async def planner_node(state: ChatBiState) -> ChatBiState:
        """规划节点"""
        result = await planner.execute(state)
        state.update(result)
        return state

    async def generator_node(state: ChatBiState) -> ChatBiState:
        """生成节点"""
        # 注入 cube_schema
        state["cube_schema"] = cube_schema or {}
        result = await generator.execute(state)
        state.update(result)
        return state

    async def critic_node(state: ChatBiState) -> ChatBiState:
        """审查节点"""
        # 注入 cube_schema
        state["cube_schema"] = cube_schema or {}
        result = await critic.execute(state)
        state.update(result)
        return state

    async def repair_node(state: ChatBiState) -> ChatBiState:
        """修复节点"""
        # 注入 cube_schema
        state["cube_schema"] = cube_schema or {}
        result = await repair.execute(state)
        state.update(result)
        state["error_count"] += 1
        return state

    async def execute_node(state: ChatBiState) -> ChatBiState:
        """执行节点 - 调用语义层执行查询"""
        dsl_json = state.get("dsl_json", {})

        try:
            # 如果配置了语义层，使用 Cube.js
            from backend.src.app.services.semantic_layer.cube_service import CubeService

            cube_service = CubeService()
            cube_name = dsl_json.get("cube")

            result = await cube_service.execute_query(
                cube_name=cube_name,
                measures=dsl_json.get("measures", []),
                dimensions=dsl_json.get("dimensions", []),
                filters=dsl_json.get("filters", []),
                time_dimension=dsl_json.get("timeDimension"),
                granularity=dsl_json.get("granularity"),
                tenant_id=state.get("tenant_id")
            )

            state["final_result"] = result
            state["error_message"] = ""

        except Exception as e:
            state["error_message"] = str(e)
            state["final_result"] = None

        return state

    async def disambiguation_node(state: ChatBiState) -> ChatBiState:
        """消歧节点 - 生成澄清问题"""
        route_decision = state.get("route_decision", {})
        ambiguity_types = route_decision.get("ambiguity_types", [])
        detected_keywords = route_decision.get("detected_keywords", [])

        # 生成澄清问题
        questions = []

        if "multiple_metrics" in ambiguity_types:
            questions.append({
                "question": "请选择您关心的指标:",
                "type": "multiple_choice",
                "options": ["销售额", "订单量", "客户数", "利润"],
                "required": True
            })

        if "time_range" in ambiguity_types:
            questions.append({
                "question": "请选择时间范围:",
                "type": "multiple_choice",
                "options": ["最近7天", "最近30天", "本月", "本季度", "本年度"],
                "required": True
            })

        state["final_result"] = {
            "needs_clarification": True,
            "questions": questions,
            "detected_keywords": detected_keywords
        }

        return state

    # ========== 定义边路由 ==========

    def should_continue_to_generator(state: ChatBiState) -> Literal["generator", END]:
        """判断是否需要重新生成"""
        if state.get("needs_regeneration", False):
            return "generator"
        return END

    def should_repair(state: ChatBiState) -> Literal["repair", END]:
        """判断是否需要修复"""
        error_count = state.get("error_count", 0)
        max_attempts = 3

        if state.get("error_message") and error_count < max_attempts:
            return "repair"
        return END

    def after_repair(state: ChatBiState) -> Literal["critic", END]:
        """修复后重新审查"""
        return "critic"

    def should_disambiguate(state: ChatBiState) -> Literal["disambiguation", "planner"]:
        """判断是否需要消歧"""
        route_decision = state.get("route_decision", {})
        if route_decision.get("needs_disambiguation", False):
            return "disambiguation"
        return "planner"

    # ========== 构建图 ==========

    builder = StateGraph(ChatBiState)

    # 添加节点
    builder.add_node("router", router_node)
    builder.add_node("disambiguation", disambiguation_node)
    builder.add_node("planner", planner_node)
    builder.add_node("generator", generator_node)
    builder.add_node("critic", critic_node)
    builder.add_node("repair", repair_node)
    builder.add_node("execute", execute_node)

    # 添加边
    builder.set_entry_point("router")

    # Router → 消歧 或 Planner
    builder.add_conditional_edges(
        "router",
        should_disambiguate
    )

    # 消歧 → 结束
    builder.add_edge("disambiguation", END)

    # Planner → Generator
    builder.add_edge("planner", "generator")

    # Generator → Execute 或 Critic
    builder.add_conditional_edges(
        "generator",
        should_continue_to_generator
    )

    # Execute → Repair 或 结束
    builder.add_conditional_edges(
        "execute",
        should_repair
    )

    # Critic → Execute 或 结束
    builder.add_conditional_edges(
        "critic",
        should_continue_to_generator
    )

    # Repair → Critic
    builder.add_conditional_edges(
        "repair",
        after_repair
    )

    return builder.compile()


# ========== 便捷函数 ==========

async def run_swarm_query(
    query: str,
    tenant_id: str,
    llm=None,
    cube_schema: dict = None
) -> Dict[str, Any]:
    """
    运行 Swarm Agent 查询

    Args:
        query: 用户查询
        tenant_id: 租户ID
        llm: LLM 实例
        cube_schema: Cube 定义

    Returns:
        查询结果
    """
    # 构建状态
    state: ChatBiState = {
        "query": query,
        "tenant_id": tenant_id,
        "route_decision": {},
        "query_plan": {},
        "dsl_json": {},
        "critic_report": {},
        "needs_regeneration": False,
        "repair_attempted": False,
        "error_count": 0,
        "error_message": "",
        "final_result": None,
        "cube_schema": cube_schema or {}
    }

    # 构建并执行图
    graph = build_swarm_graph(llm, cube_schema)
    result = await graph.ainvoke(state)

    return result
