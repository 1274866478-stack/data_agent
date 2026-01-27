# -*- coding: utf-8 -*-
"""
计划生成节点 (Planning Node) - LangGraph 节点

这个节点在 LLM 执行查询之前生成执行计划，实现"慢思考"机制。

核心功能：
    1. 分析用户问题，识别意图
    2. 生成结构化的执行计划
    3. 检测潜在的模糊点
    4. 为后续步骤提供上下文

作者: Data Agent Team
版本: 1.0.0
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Literal
from enum import Enum
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import MessagesState

logger = logging.getLogger(__name__)


class PlanStepType(str, Enum):
    """计划步骤类型"""
    UNDERSTAND = "understand"       # 理解问题
    CONTEXT = "context"            # 获取上下文（schema、表结构）
    SEMANTIC = "semantic"          # 语义层解析
    SQL_GENERATE = "sql_generate"  # 生成 SQL
    VALIDATE = "validate"          # 验证 SQL
    EXECUTE = "execute"            # 执行查询
    ANALYZE = "analyze"            # 分析结果
    VISUALIZE = "visualize"        # 可视化


@dataclass
class PlanStep:
    """执行计划步骤"""
    step_type: PlanStepType
    description: str
    tool: Optional[str] = None        # 需要调用的工具
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "step_type": self.step_type.value,
            "description": self.description,
            "tool": self.tool,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "status": self.status
        }


@dataclass
class ExecutionPlan:
    """执行计划"""
    query: str                           # 原始查询
    intent: str                          # 查询意图
    steps: List[PlanStep] = field(default_factory=list)
    business_terms: List[str] = field(default_factory_list)  # 识别的业务术语
    confidence: float = 1.0               # 置信度
    needs_clarification: bool = False    # 是否需要澄清
    reasoning: str = ""                  # 推理过程

    def add_step(self, step: PlanStep) -> None:
        """添加步骤"""
        self.steps.append(step)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "query": self.query,
            "intent": self.intent,
            "steps": [step.to_dict() for step in self.steps],
            "business_terms": self.business_terms,
            "confidence": self.confidence,
            "needs_clarification": self.needs_clarification,
            "reasoning": self.reasoning,
            "step_count": len(self.steps)
        }


class PlanningNode:
    """
    计划生成节点

    在 LangGraph 中作为第一个节点执行，生成查询执行计划。

    功能：
        1. 分析用户问题
        2. 识别业务术语
        3. 生成执行步骤
        4. 评估置信度
    """

    # 需要澄清的模糊关键词
    AMBIGUITY_KEYWORDS = [
        "最好", "最差", "最大", "最小", "最多", "最少",
        "分析", "统计", "总结", "报告",
        "趋势", "变化", "增长", "下降",
    ]

    # 业务术语模式
    BUSINESS_TERM_PATTERNS = [
        r'(总收入|净收入|销售额|营收|毛利|GMV|ARPU)',
        r'(订单数|客户数|用户数|商品数)',
        r'(完成|进行中|取消|退款)',
        r'(本月|上月|本周|上周)',
    ]

    def __init__(
        self,
        enable_logging: bool = True,
        min_confidence: float = 0.6
    ):
        """初始化计划节点

        Args:
            enable_logging: 是否启用日志
            min_confidence: 最低置信度阈值（低于此值需要澄清）
        """
        self.enable_logging = enable_logging
        self.min_confidence = min_confidence

    def __call__(self, state: MessagesState) -> Dict[str, Any]:
        """执行计划生成

        Args:
            state: LangGraph 消息状态

        Returns:
            更新后的状态，包含执行计划
        """
        messages = state["messages"]

        # 获取用户问题
        user_query = self._extract_user_query(messages)
        if not user_query:
            logger.warning("[PlanningNode] 未找到用户查询")
            return {"messages": []}

        # 生成执行计划
        plan = self._generate_plan(user_query)

        # 记录计划
        if self.enable_logging:
            self._log_plan(plan)

        # 创建计划消息
        plan_message = self._create_plan_message(plan)

        return {
            "messages": [plan_message],
            "__execution_plan__": plan.to_dict()
        }

    def _extract_user_query(self, messages: list) -> Optional[str]:
        """从消息中提取用户查询

        Args:
            messages: 消息列表

        Returns:
            用户查询字符串
        """
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return msg.content
        return None

    def _generate_plan(self, query: str) -> ExecutionPlan:
        """生成执行计划

        Args:
            query: 用户查询

        Returns:
            执行计划
        """
        # 创建计划对象
        plan = ExecutionPlan(query=query, intent="")

        # 步骤1: 理解问题
        understanding = self._understand_query(query)
        plan.reasoning = understanding["reasoning"]
        plan.intent = understanding["intent"]

        # 步骤2: 识别业务术语
        business_terms = self._identify_business_terms(query)
        plan.business_terms = business_terms

        # 步骤3: 生成执行步骤
        steps = self._generate_steps(query, business_terms)
        plan.steps = steps

        # 步骤4: 评估置信度
        confidence = self._evaluate_confidence(query, business_terms)
        plan.confidence = confidence

        # 步骤5: 判断是否需要澄清
        plan.needs_clarification = confidence < self.min_confidence

        return plan

    def _understand_query(self, query: str) -> Dict[str, str]:
        """理解查询意图

        Args:
            query: 用户查询

        Returns:
            包含 reasoning 和 intent 的字典
        """
        query_lower = query.lower()

        # 分析查询类型
        if any(kw in query_lower for kw in ["有多少", "多少", "数量", "计数"]):
            intent = "count_query"
            reasoning = "用户询问数量或计数，需要使用 COUNT 或 COUNT(DISTINCT)"
        elif any(kw in query_lower for kw in ["总收入", "净收入", "销售额", "营收", "毛利", "总和", "总计"]):
            intent = "sum_query"
            reasoning = "用户询问收入或总额，需要使用 SUM 聚合"
        elif any(kw in query_lower for kw in ["平均", "均值", "avg", "average"]):
            intent = "avg_query"
            reasoning = "用户询问平均值，需要使用 AVG 聚合"
        elif any(kw in query_lower for kw in ["占比", "比例", "百分比", "分布"]):
            intent = "proportion_query"
            reasoning = "用户询问占比或分布，需要使用 GROUP BY + CASE WHEN"
        elif any(kw in query_lower for kw in ["趋势", "变化", "增长", "时间", "最近", "本月", "本周"]):
            intent = "trend_query"
            reasoning = "用户询问趋势分析，需要按时间分组并使用 DATE_TRUNC"
        elif any(kw in query_lower for kw in ["哪个", "最", "top", "前", "排名"]):
            intent = "ranking_query"
            reasoning = "用户询问排名或最值，需要使用 ORDER BY + LIMIT"
        else:
            intent = "general_query"
            reasoning = "一般性查询，需要根据具体情况确定"

        return {
            "intent": intent,
            "reasoning": reasoning
        }

    def _identify_business_terms(self, query: str) -> List[str]:
        """识别业务术语

        Args:
            query: 用户查询

        Returns:
            识别的业务术语列表
        """
        import re
        terms = []

        for pattern in self.BUSINESS_TERM_PATTERNS:
            matches = re.findall(pattern, query)
            terms.extend(matches)

        return list(set(terms))

    def _generate_steps(
        self,
        query: str,
        business_terms: List[str]
    ) -> List[PlanStep]:
        """生成执行步骤

        Args:
            query: 用户查询
            business_terms: 业务术语列表

        Returns:
            执行步骤列表
        """
        steps = []

        # 步骤1: 理解问题
        steps.append(PlanStep(
            step_type=PlanStepType.UNDERSTAND,
            description="理解用户查询意图",
            status="completed"
        ))

        # 步骤2: 获取上下文
        steps.append(PlanStep(
            step_type=PlanStepType.CONTEXT,
            description="获取数据库上下文（表结构）",
            tool="list_tables",
            dependencies=[]
        ))

        # 步骤3: 语义层解析
        if business_terms:
            for term in business_terms:
                steps.append(PlanStep(
                    step_type=PlanStepType.SEMANTIC,
                    description=f"解析业务术语: {term}",
                    tool="resolve_business_term",
                    parameters={"term": term},
                    dependencies=["context"]
                ))

        # 步骤4: 生成 SQL
        steps.append(PlanStep(
            step_type=PlanStepType.SQL_GENERATE,
            description="生成 SQL 查询",
            dependencies=["semantic"] if business_terms else ["context"]
        ))

        # 步骤5: 验证 SQL
        steps.append(PlanStep(
            step_type=PlanStepType.VALIDATE,
            description="验证 SQL 安全性和正确性",
            dependencies=["sql_generate"]
        ))

        # 步骤6: 执行查询
        steps.append(PlanStep(
            step_type=PlanStepType.EXECUTE,
            description="执行 SQL 查询",
            tool="execute_query",
            dependencies=["validate"]
        ))

        # 步骤7: 分析结果
        steps.append(PlanStep(
            step_type=PlanStepType.ANALYZE,
            description="分析查询结果",
            dependencies=["execute"]
        ))

        # 步骤8: 可视化
        steps.append(PlanStep(
            step_type=PlanStepType.VISUALIZE,
            description="生成图表可视化",
            dependencies=["analyze"]
        ))

        return steps

    def _evaluate_confidence(
        self,
        query: str,
        business_terms: List[str]
    ) -> float:
        """评估置信度

        Args:
            query: 用户查询
            business_terms: 业务术语列表

        Returns:
            置信度 (0-1)
        """
        confidence = 1.0

        # 检测模糊关键词
        for keyword in self.AMBIGUITY_KEYWORDS:
            if keyword in query:
                confidence -= 0.1

        # 检测业务术语（提高置信度）
        if business_terms:
            confidence += min(0.2, len(business_terms) * 0.05)

        # 检测查询长度（太短降低置信度）
        if len(query.strip()) < 5:
            confidence -= 0.2

        # 限制在 0-1 范围内
        confidence = max(0.0, min(1.0, confidence))

        return confidence

    def _log_plan(self, plan: ExecutionPlan) -> None:
        """记录执行计划

        Args:
            plan: 执行计划
        """
        logger.info("=" * 60)
        logger.info("[PlanningNode] 执行计划生成完成")
        logger.info(f"查询: {plan.query}")
        logger.info(f"意图: {plan.intent}")
        logger.info(f"推理: {plan.reasoning}")
        logger.info(f"业务术语: {plan.business_terms}")
        logger.info(f"置信度: {plan.confidence:.2f}")
        logger.info(f"需要澄清: {plan.needs_clarification}")
        logger.info(f"执行步骤 ({len(plan.steps)} 步):")
        for i, step in enumerate(plan.steps, 1):
            logger.info(f"  {i}. [{step.step_type.value}] {step.description}")
        logger.info("=" * 60)

    def _create_plan_message(self, plan: ExecutionPlan) -> AIMessage:
        """创建计划消息

        Args:
            plan: 执行计划

        Returns:
            AI 消息
        """
        content = f"""## 📋 执行计划

**查询意图**: {plan.intent}

**推理过程**: {plan.reasoning}

**识别的业务术语**: {', '.join(plan.business_terms) if plan.business_terms else '无'}

**置信度**: {plan.confidence:.1%}

{'⚠️ 置信度较低，可能需要用户澄清' if plan.confidence < self.min_confidence else '✅ 置信度良好，可以继续执行'}

**执行步骤**:
"""

        for i, step in enumerate(plan.steps, 1):
            status_icon = {
                "completed": "✅",
                "pending": "🔄",
                "in_progress": "⏳",
                "failed": "❌"
            }.get(step.status, "🔄")

            content += f"\n{i}. {status_icon} **{step.description}**\n"
            if step.tool:
                content += f"   - 工具: `{step.tool}`\n"
            if step.dependencies:
                content += f"   - 依赖: {', '.join(step.dependencies)}\n"

        return AIMessage(content=content)


def create_planning_node(
    enable_logging: bool = True,
    min_confidence: float = 0.6
) -> PlanningNode:
    """创建计划节点

    Args:
        enable_logging: 是否启用日志
        min_confidence: 最低置信度阈值

    Returns:
        PlanningNode 实例
    """
    return PlanningNode(
        enable_logging=enable_logging,
        min_confidence=min_confidence
    )


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("计划节点测试")
    print("=" * 60)

    node = PlanningNode()

    # 测试查询
    test_queries = [
        "订单总收入是多少？",
        "分析最近一周的销售趋势",
        "哪个地区的销售额最高？",
        "魔都的客户有多少？",
    ]

    for query in test_queries:
        print(f"\n[测试] 查询: {query}")

        # 模拟状态
        class MockState:
            def __init__(self, query):
                self.messages = [HumanMessage(content=query)]

        state = MockState(query)

        # 生成计划
        plan = node._generate_plan(query)

        print(f"意图: {plan.intent}")
        print(f"推理: {plan.reasoning}")
        print(f"业务术语: {plan.business_terms}")
        print(f"置信度: {plan.confidence:.2f}")
        print(f"需要澄清: {plan.needs_clarification}")
        print(f"步骤数: {len(plan.steps)}")
