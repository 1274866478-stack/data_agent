# -*- coding: utf-8 -*-
"""
澄清节点 (Clarification Node) - LangGraph 节点

这个节点在检测到模糊问题时主动向用户提问，实现交互式澄清功能。

核心功能：
    1. 检测模糊问题
    2. 生成澄清问题
    3. 提供澄清选项
    4. 处理用户回复

作者: Data Agent Team
版本: 1.0.0
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import MessagesState

logger = logging.getLogger(__name__)


class ClarificationType(str, Enum):
    """澄清类型"""
    TIME_RANGE = "time_range"        # 时间范围
    ENTITY = "entity"                # 实体（如地区、产品）
    METRIC = "metric"                # 指标（如收入类型）
    COMPARISON = "comparison"        # 比较（如同比、环比）
    AGGREGATION = "aggregation"      # 聚合方式（如总和、平均）
    OTHER = "other"                  # 其他


@dataclass
class ClarificationOption:
    """澄清选项"""
    value: str                        # 选项值
    label: str                        # 显示标签
    description: str = ""             # 描述
    is_default: bool = False          # 是否默认选项

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "value": self.value,
            "label": self.label,
            "description": self.description,
            "is_default": self.is_default
        }


@dataclass
class ClarificationQuestion:
    """澄清问题"""
    question_id: str                  # 问题 ID
    question_type: ClarificationType  # 问题类型
    question_text: str                # 问题文本
    options: List[ClarificationOption] = field(default_factory=list)
    allow_multiple: bool = False      # 是否允许多选
    allow_custom: bool = True         # 是否允许自定义输入

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "question_id": self.question_id,
            "question_type": self.question_type.value,
            "question_text": self.question_text,
            "options": [opt.to_dict() for opt in self.options],
            "allow_multiple": self.allow_multiple,
            "allow_custom": self.allow_custom
        }


@dataclass
class ClarificationResult:
    """澄清结果"""
    needs_clarification: bool         # 是否需要澄清
    questions: List[ClarificationQuestion] = field(default_factory=list)
    confidence: float = 1.0            # 置信度
    reasoning: str = ""                # 推理过程

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "needs_clarification": self.needs_clarification,
            "questions": [q.to_dict() for q in self.questions],
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "question_count": len(self.questions)
        }


class ClarificationNode:
    """
    澄清节点

    在检测到模糊问题时生成澄清问题，引导用户提供更明确的需求。

    功能：
        1. 分析用户查询的清晰度
        2. 识别模糊点
        3. 生成针对性的澄清问题
        4. 处理用户的澄清回复
    """

    # 置信度阈值
    CONFIDENCE_THRESHOLD = 0.6

    # 模糊关键词模式
    AMBIGUITY_PATTERNS = {
        ClarificationType.TIME_RANGE: [
            "最近", "近期", "这段时间",
            "之前", "以后", "前后"
        ],
        ClarificationType.ENTITY: [
            "哪个", "哪些", "最好的", "最差的",
            "top", "前", "排名"
        ],
        ClarificationType.METRIC: [
            "销售", "收入", "利润", "业绩"
        ],
        ClarificationType.COMPARISON: [
            "增长", "下降", "变化", "趋势"
        ],
        ClarificationType.AGGREGATION: [
            "统计", "分析", "汇总", "总计"
        ],
    }

    # 预定义的澄清问题模板
    QUESTION_TEMPLATES = {
        ClarificationType.TIME_RANGE: ClarificationQuestion(
            question_id="time_range",
            question_type=ClarificationType.TIME_RANGE,
            question_text="请指定时间范围",
            options=[
                ClarificationOption("7d", "最近一周", "过去7天", True),
                ClarificationOption("30d", "最近一月", "过去30天"),
                ClarificationOption("90d", "最近三月", "过去90天"),
                ClarificationOption("1y", "最近一年", "过去365天"),
                ClarificationOption("custom", "自定义", "手动指定时间范围"),
            ]
        ),
        ClarificationType.ENTITY: ClarificationQuestion(
            question_id="entity_type",
            question_type=ClarificationType.ENTITY,
            question_text="请问您想了解哪个方面的数据？",
            options=[
                ClarificationOption("region", "按地区", "各地区的销售情况"),
                ClarificationOption("product", "按产品", "各产品的销售情况"),
                ClarificationOption("category", "按类别", "各类别的销售情况"),
                ClarificationOption("customer", "按客户", "各客户的销售情况"),
            ]
        ),
        ClarificationType.METRIC: ClarificationQuestion(
            question_id="metric_type",
            question_type=ClarificationType.METRIC,
            question_text="请问您想查看哪个指标？",
            options=[
                ClarificationOption("revenue", "总收入", "所有订单的总金额", True),
                ClarificationOption("count", "订单数", "订单的总数量"),
                ClarificationOption("avg_amount", "平均订单金额", "每个订单的平均金额"),
                ClarificationOption("profit", "利润", "收入减去成本"),
            ]
        ),
        ClarificationType.COMPARISON: ClarificationQuestion(
            question_id="comparison_type",
            question_type=ClarificationType.COMPARISON,
            question_text="请问您想进行哪种类型的比较？",
            options=[
                ClarificationOption("yoy", "同比", "与去年同期相比"),
                ClarificationOption("mom", "环比", "与上一周期相比"),
                ClarificationOption("wow", "周环比", "与上周相比"),
                ClarificationOption("trend", "趋势", "时间序列变化"),
            ]
        ),
        ClarificationType.AGGREGATION: ClarificationQuestion(
            question_id="aggregation_type",
            question_type=ClarificationType.AGGREGATION,
            question_text="请问您想如何聚合数据？",
            options=[
                ClarificationOption("sum", "总和", "累加所有值"),
                ClarificationOption("avg", "平均", "计算平均值"),
                ClarificationOption("count", "计数", "计算数量"),
                ClarificationOption("max", "最大值", "找出最大值"),
                ClarificationOption("min", "最小值", "找出最小值"),
            ]
        ),
    }

    def __init__(
        self,
        confidence_threshold: float = 0.6,
        enable_logging: bool = True
    ):
        """初始化澄清节点

        Args:
            confidence_threshold: 置信度阈值（低于此值触发澄清）
            enable_logging: 是否启用日志
        """
        self.confidence_threshold = confidence_threshold
        self.enable_logging = enable_logging

    def __call__(self, state: MessagesState) -> Dict[str, Any]:
        """执行澄清分析

        Args:
            state: LangGraph 消息状态

        Returns:
            更新后的状态，包含澄清结果
        """
        messages = state["messages"]

        # 获取用户问题
        user_query = self._extract_user_query(messages)
        if not user_query:
            logger.warning("[ClarificationNode] 未找到用户查询")
            return {"messages": []}

        # 检查是否已有澄清回复
        if self._has_clarification_response(messages):
            # 处理澄清回复
            return self._process_clarification_response(messages)

        # 分析清晰度
        result = self._analyze_clarity(user_query)

        # 记录结果
        if self.enable_logging:
            self._log_clarification(result)

        # 如果需要澄清，创建澄清消息
        if result.needs_clarification:
            clarification_message = self._create_clarification_message(result)
            return {
                "messages": [clarification_message],
                "__clarification_result__": result.to_dict(),
                "__needs_clarification__": True
            }

        # 不需要澄清，返回空
        return {
            "messages": [],
            "__clarification_result__": result.to_dict(),
            "__needs_clarification__": False
        }

    def _extract_user_query(self, messages: list) -> Optional[str]:
        """提取用户查询

        Args:
            messages: 消息列表

        Returns:
            用户查询字符串
        """
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                # 过滤掉澄清回复
                if not msg.content.startswith("{"):
                    return msg.content
        return None

    def _has_clarification_response(self, messages: list) -> bool:
        """检查是否有澄清回复

        Args:
            messages: 消息列表

        Returns:
            是否有澄清回复
        """
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage) and msg.content.startswith("{"):
                try:
                    json.loads(msg.content)
                    return True
                except json.JSONDecodeError:
                    pass
        return False

    def _process_clarification_response(self, messages: list) -> Dict[str, Any]:
        """处理澄清回复

        Args:
            messages: 消息列表

        Returns:
            更新后的状态
        """
        # 找到澄清回复
        response = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                try:
                    response = json.loads(msg.content)
                    break
                except json.JSONDecodeError:
                    pass

        if not response:
            return {"messages": []}

        # 创建确认消息
        confirm_message = AIMessage(
            content=f"✅ 已收到您的选择：\n\n{json.dumps(response, ensure_ascii=False, indent=2)}\n\n"
                    "正在基于您的选择生成查询..."
        )

        return {
            "messages": [confirm_message],
            "__clarification_response__": response
        }

    def _analyze_clarity(self, query: str) -> ClarificationResult:
        """分析查询清晰度

        Args:
            query: 用户查询

        Returns:
            澄清结果
        """
        query_lower = query.lower()

        # 计算置信度
        confidence = self._calculate_confidence(query)

        result = ClarificationResult(
            needs_clarification=confidence < self.confidence_threshold,
            confidence=confidence
        )

        # 识别模糊点并生成问题
        if confidence < self.confidence_threshold:
            questions = self._generate_questions(query, query_lower)
            result.questions = questions
            result.reasoning = f"查询置信度 {confidence:.1%} 低于阈值 {self.confidence_threshold:.1%}，需要澄清"

        return result

    def _calculate_confidence(self, query: str) -> float:
        """计算查询置信度

        Args:
            query: 用户查询

        Returns:
            置信度 (0-1)
        """
        confidence = 1.0
        query_lower = query.lower()

        # 检查明确的实体（提高置信度）
        if any(city in query for city in ["北京", "上海", "广州", "深圳", "杭州"]):
            confidence += 0.1

        if any(keyword in query_lower for keyword in [
            "订单", "客户", "产品", "销售额"
        ]):
            confidence += 0.1

        # 检查模糊词（降低置信度）
        if any(keyword in query for keyword in ["最好", "最差", "最大", "最小"]):
            confidence -= 0.2

        if any(keyword in query for keyword in ["最近", "近期", "分析"]):
            confidence -= 0.1

        # 检查查询长度（太短降低置信度）
        if len(query.strip()) < 10:
            confidence -= 0.2

        # 限制在 0-1 范围内
        return max(0.0, min(1.0, confidence))

    def _generate_questions(
        self,
        query: str,
        query_lower: str
    ) -> List[ClarificationQuestion]:
        """生成澄清问题

        Args:
            query: 原始查询
            query_lower: 小写查询

        Returns:
            澄清问题列表
        """
        questions = []

        # 检查每个类型的模糊模式
        for clarification_type, patterns in self.AMBIGUITY_PATTERNS.items():
            if any(pattern in query for pattern in patterns):
                # 使用预定义模板
                template = self.QUESTION_TEMPLATES.get(clarification_type)
                if template:
                    questions.append(template)

        return questions

    def _log_clarification(self, result: ClarificationResult) -> None:
        """记录澄清结果

        Args:
            result: 澄清结果
        """
        if result.needs_clarification:
            logger.info("[ClarificationNode] 检测到模糊问题，需要澄清")
            logger.info(f"  置信度: {result.confidence:.1%}")
            logger.info(f"  推理: {result.reasoning}")
            logger.info(f"  澄清问题数: {len(result.questions)}")
        else:
            logger.info("[ClarificationNode] 查询清晰，无需澄清")

    def _create_clarification_message(self, result: ClarificationResult) -> AIMessage:
        """创建澄清消息

        Args:
            result: 澄清结果

        Returns:
            AI 消息
        """
        content = "## 🤔 需要澄清\n\n"
        content += result.reasoning + "\n\n"
        content += "为了更好地回答您的问题，请回答以下问题：\n\n"

        for i, question in enumerate(result.questions, 1):
            content += f"### Q{i}: {question.question_text}\n\n"

            for j, option in enumerate(question.options):
                default_mark = " (默认)" if option.is_default else ""
                content += f"- **{j+1}.** `{option.value}` - {option.label}{default_mark}\n"
                if option.description:
                    content += f"  - {option.description}\n"

            if question.allow_custom:
                content += "- **自定义**: 输入您自己的值\n"

            content += "\n"

        content += "---\n\n"
        content += "**回复格式**: 请按以下格式回复（JSON）：\n"
        content += "```\n"
        content += "{\n"
        content += '  "time_range": "7d",\n'
        content += '  "metric": "revenue",\n'
        content += '  ...\n'
        content += "}\n"
        content += "```\n"

        return AIMessage(content=content)

    def update_with_clarification(
        self,
        original_query: str,
        clarification_response: Dict[str, Any]
    ) -> str:
        """使用澄清回复更新查询

        Args:
            original_query: 原始查询
            clarification_response: 澄清回复

        Returns:
            更新后的查询
        """
        # 构建补充信息
        additions = []

        if "time_range" in clarification_response:
            time_value = clarification_response["time_range"]
            time_map = {
                "7d": "最近一周",
                "30d": "最近一月",
                "90d": "最近三月",
                "1y": "最近一年",
            }
            additions.append(f"时间范围: {time_map.get(time_value, time_value)}")

        if "metric" in clarification_response:
            metric_value = clarification_response["metric"]
            metric_map = {
                "revenue": "总收入",
                "count": "订单数",
                "avg_amount": "平均订单金额",
            }
            additions.append(f"指标: {metric_map.get(metric_value, metric_value)}")

        if "entity" in clarification_response:
            entity_value = clarification_response["entity"]
            entity_map = {
                "region": "按地区",
                "product": "按产品",
            }
            additions.append(f"维度: {entity_map.get(entity_value, entity_value)}")

        if additions:
            return f"{original_query} ({', '.join(additions)})"

        return original_query


def create_clarification_node(
    confidence_threshold: float = 0.6,
    enable_logging: bool = True
) -> ClarificationNode:
    """创建澄清节点

    Args:
        confidence_threshold: 置信度阈值
        enable_logging: 是否启用日志

    Returns:
        ClarificationNode 实例
    """
    return ClarificationNode(
        confidence_threshold=confidence_threshold,
        enable_logging=enable_logging
    )


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("澄清节点测试")
    print("=" * 60)

    node = ClarificationNode()

    # 测试查询
    test_queries = [
        "订单总收入是多少？",  # 清晰
        "最好的销售是什么？",  # 模糊（哪个指标？哪个维度？）
        "最近的分析",  # 模糊（时间范围？分析什么？）
        "比较各地区",  # 模糊（比较什么？）
    ]

    for query in test_queries:
        print(f"\n[测试] 查询: {query}")
        result = node._analyze_clarity(query)
        print(f"  需要澄清: {result.needs_clarification}")
        print(f"  置信度: {result.confidence:.2f}")
        print(f"  问题数: {len(result.questions)}")
        if result.questions:
            for q in result.questions:
                print(f"    - {q.question_text}")
