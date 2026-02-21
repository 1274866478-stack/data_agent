from __future__ import annotations

"""Swarm graph orchestration for Router -> Planner -> Generator -> Critic -> Repair."""

from typing import Any, Dict, List, Literal, TypedDict

from langgraph.graph import END, StateGraph

try:
    from ..core.cube_executor import execute_cube_query
except ImportError:  # pragma: no cover - script mode fallback
    from core.cube_executor import execute_cube_query

try:
    from ..subagents import CriticAgent, GeneratorAgent, PlannerAgent, RepairAgent, RouterAgent
except ImportError:  # pragma: no cover - script mode fallback
    from subagents import CriticAgent, GeneratorAgent, PlannerAgent, RepairAgent, RouterAgent

MAX_REGENERATION_ATTEMPTS = 2
MAX_REPAIR_ATTEMPTS = 3


class ChatBiState(TypedDict):
    query: str
    tenant_id: str
    route_decision: Dict[str, Any]
    query_plan: Dict[str, Any]
    dsl_json: Dict[str, Any]
    critic_report: Dict[str, Any]
    needs_regeneration: bool
    regeneration_count: int
    repair_attempted: bool
    error_count: int
    error_message: str
    final_result: Dict[str, Any] | None
    cube_schema: Dict[str, Any]


def _apply_updates(state: ChatBiState, updates: Dict[str, Any]) -> ChatBiState:
    state.update(updates)
    return state


def _attach_cube_schema(state: ChatBiState, schema: Dict[str, Any] | None) -> None:
    state["cube_schema"] = schema or {}


def _build_disambiguation_questions(ambiguity_types: List[str]) -> List[Dict[str, Any]]:
    questions: List[Dict[str, Any]] = []

    if "multiple_metrics" in ambiguity_types:
        questions.append(
            {
                "question": "请选择你关注的指标：",
                "type": "multiple_choice",
                "options": ["销售额", "订单量", "客户数", "利润"],
                "required": True,
            }
        )

    if "time_range" in ambiguity_types:
        questions.append(
            {
                "question": "请选择时间范围：",
                "type": "multiple_choice",
                "options": ["最近7天", "最近30天", "本月", "本季度", "本年度"],
                "required": True,
            }
        )

    return questions


def build_swarm_graph(llm: Any = None, cube_schema: Dict[str, Any] | None = None):
    router = RouterAgent("router", llm)
    planner = PlannerAgent("planner", llm)
    generator = GeneratorAgent("generator", llm)
    critic = CriticAgent("critic", llm)
    repair = RepairAgent("repair", llm)

    async def router_node(state: ChatBiState) -> ChatBiState:
        return _apply_updates(state, await router.execute(state))

    async def planner_node(state: ChatBiState) -> ChatBiState:
        return _apply_updates(state, await planner.execute(state))

    async def generator_node(state: ChatBiState) -> ChatBiState:
        _attach_cube_schema(state, cube_schema)
        return _apply_updates(state, await generator.execute(state))

    async def critic_node(state: ChatBiState) -> ChatBiState:
        _attach_cube_schema(state, cube_schema)
        _apply_updates(state, await critic.execute(state))

        if state.get("needs_regeneration", False):
            state["regeneration_count"] = state.get("regeneration_count", 0) + 1
            if state["regeneration_count"] >= MAX_REGENERATION_ATTEMPTS:
                state["error_message"] = "DSL validation failed after max regeneration attempts"
                state["final_result"] = {
                    "error": state["error_message"],
                    "critic_report": state.get("critic_report", {}),
                }
        return state

    async def repair_node(state: ChatBiState) -> ChatBiState:
        _attach_cube_schema(state, cube_schema)
        _apply_updates(state, await repair.execute(state))
        state["error_count"] = state.get("error_count", 0) + 1
        return state

    async def execute_node(state: ChatBiState) -> ChatBiState:
        dsl_json = state.get("dsl_json", {})
        try:
            result = await execute_cube_query(
                dsl_json=dsl_json,
                tenant_id=state.get("tenant_id"),
            )
            state["final_result"] = result
            state["error_message"] = ""
        except Exception as exc:
            state["error_message"] = str(exc)
            state["final_result"] = None
        return state

    async def disambiguation_node(state: ChatBiState) -> ChatBiState:
        route_decision = state.get("route_decision", {})
        ambiguity_types = route_decision.get("ambiguity_types", [])
        detected_keywords = route_decision.get("detected_keywords", [])
        questions = _build_disambiguation_questions(ambiguity_types)

        state["final_result"] = {
            "needs_clarification": True,
            "questions": questions,
            "detected_keywords": detected_keywords,
        }
        return state

    def after_critic(state: ChatBiState) -> Literal["generator", "execute", END]:
        if state.get("needs_regeneration", False):
            if state.get("regeneration_count", 0) >= MAX_REGENERATION_ATTEMPTS:
                return END
            return "generator"
        return "execute"

    def should_repair(state: ChatBiState) -> Literal["repair", END]:
        if state.get("error_message") and state.get("error_count", 0) < MAX_REPAIR_ATTEMPTS:
            return "repair"
        return END

    def after_repair(state: ChatBiState) -> Literal["critic", END]:
        _ = state
        return "critic"

    def should_disambiguate(state: ChatBiState) -> Literal["disambiguation", "planner"]:
        if state.get("route_decision", {}).get("needs_disambiguation", False):
            return "disambiguation"
        return "planner"

    builder = StateGraph(ChatBiState)
    builder.add_node("router", router_node)
    builder.add_node("disambiguation", disambiguation_node)
    builder.add_node("planner", planner_node)
    builder.add_node("generator", generator_node)
    builder.add_node("critic", critic_node)
    builder.add_node("repair", repair_node)
    builder.add_node("execute", execute_node)

    builder.set_entry_point("router")
    builder.add_conditional_edges("router", should_disambiguate)
    builder.add_edge("disambiguation", END)
    builder.add_edge("planner", "generator")
    builder.add_edge("generator", "critic")
    builder.add_conditional_edges("execute", should_repair)
    builder.add_conditional_edges("critic", after_critic)
    builder.add_conditional_edges("repair", after_repair)

    return builder.compile()


def create_initial_state(
    query: str,
    tenant_id: str,
    cube_schema: Dict[str, Any] | None = None,
) -> ChatBiState:
    return {
        "query": query,
        "tenant_id": tenant_id,
        "route_decision": {},
        "query_plan": {},
        "dsl_json": {},
        "critic_report": {},
        "needs_regeneration": False,
        "regeneration_count": 0,
        "repair_attempted": False,
        "error_count": 0,
        "error_message": "",
        "final_result": None,
        "cube_schema": cube_schema or {},
    }


async def run_swarm_query(
    query: str,
    tenant_id: str,
    llm: Any = None,
    cube_schema: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    state = create_initial_state(query=query, tenant_id=tenant_id, cube_schema=cube_schema)
    graph = build_swarm_graph(llm=llm, cube_schema=cube_schema)
    return await graph.ainvoke(state)
