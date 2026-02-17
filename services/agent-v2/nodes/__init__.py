# -*- coding: utf-8 -*-
"""
AgentV2 Nodes Module
====================

LangGraph 节点定义，用于构建复杂的智能体工作流。

Includes:
    - PlanningNode: 计划生成节点（慢思考）
    - ReflectionNode: 反思节点（错误自修复）
    - ClarificationNode: 澄清节点（交互式澄清）
"""

from .planning_node import (
    PlanStepType,
    PlanStep,
    ExecutionPlan,
    PlanningNode,
    create_planning_node
)
from .reflection_node import (
    ErrorCategory,
    ReflectionResult,
    ReflectionNode,
    create_reflection_node
)
from .clarification_node import (
    ClarificationType,
    ClarificationOption,
    ClarificationQuestion,
    ClarificationResult,
    ClarificationNode,
    create_clarification_node
)

__all__ = [
    # Planning Node
    "PlanStepType",
    "PlanStep",
    "ExecutionPlan",
    "PlanningNode",
    "create_planning_node",
    # Reflection Node
    "ErrorCategory",
    "ReflectionResult",
    "ReflectionNode",
    "create_reflection_node",
    # Clarification Node
    "ClarificationType",
    "ClarificationOption",
    "ClarificationQuestion",
    "ClarificationResult",
    "ClarificationNode",
    "create_clarification_node",
]
