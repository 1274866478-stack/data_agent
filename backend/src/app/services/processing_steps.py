"""
# [PROCESSING_STEPS] 统一处理步骤构建服务

## [HEADER]
**文件名**: processing_steps.py
**职责**: 为不同场景（Agent查询、普通对话）构建统一的处理步骤配置
**作者**: Data Agent Team
**版本**: 1.1.0
**变更记录**:
- v1.1.0 (2026-01-07): 新增问题分类器和动态步骤模板
- v1.0.0 (2026-01-05): 初始版本 - 统一步骤构建器

## [INPUT]
- scenario: QueryScenario - 查询场景类型
- question: str - 用户问题（用于生成描述）
- has_context: bool - 是否有上下文信息
- full_content: str - 完整回复内容（用于步骤6）
- has_data_source: bool - 是否有可用的数据源（用于问题分类）

## [OUTPUT]
- List[StepConfig]: 处理步骤配置列表

## [LINK]
**上游依赖**:
- 无（独立服务模块）

**下游依赖**:
- [../api/v1/endpoints/llm.py](../api/v1/endpoints/llm.py) - LLM API端点（调用此服务）
- [../api/v1/endpoints/query.py](../api/v1/endpoints/query.py) - 查询API端点

**调用方**:
- stream_chat_with_agent_mode 函数
- _stream_general_chat_generator 函数

## [STATE]
- 无状态服务

## [SIDE-EFFECTS]
- 无副作用
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re


class QueryScenario(Enum):
    """查询场景枚举"""
    AGENT_SQL = "agent_sql"           # Agent SQL查询（8步）
    GENERAL_CHAT = "general_chat"     # 普通对话（6步）
    DOCUMENT_QUERY = "document_query" # 文档查询（未来扩展）
    MIXED_QUERY = "mixed_query"       # 混合查询（未来扩展）


class QuestionType(Enum):
    """
    问题类型枚举（用于动态步骤生成）

    根据用户问题的复杂度和意图，自动选择合适的步骤模板
    """
    SIMPLE_CHAT = "simple_chat"         # 简单对话（你好、谢谢）- 2步
    GENERAL_CHAT = "general_chat"       # 普通对话（需要思考） - 6步
    SCHEMA_QUERY = "schema_query"       # Schema查询（有哪些表） - 3步
    DATA_QUERY = "data_query"           # 数据查询（SQL查询） - 5步
    VISUALIZATION = "visualization"     # 可视化需求（画图表） - 6步


@dataclass
class StepConfig:
    """处理步骤配置"""
    step: int
    title: str
    description: str
    status: str = "running"  # pending/running/completed/error
    duration: Optional[int] = None
    content_type: Optional[str] = None  # sql/table/chart/error/text
    content_data: Optional[Dict] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "step": self.step,
            "title": self.title,
            "description": self.description,
            "status": self.status,
        }
        if self.duration is not None:
            result["duration"] = self.duration
        if self.content_type:
            result["content_type"] = self.content_type
        if self.content_data:
            result["content_data"] = self.content_data
        return result


def classify_question(question: str, has_data_source: bool = False) -> QuestionType:
    """
    根据问题内容分类，确定合适的问题类型

    分类优先级（从高到低）:
    1. 简单问候 → SIMPLE_CHAT
    2. 可视化需求 → VISUALIZATION
    3. Schema查询 → SCHEMA_QUERY
    4. 数据查询 → DATA_QUERY
    5. 默认 → GENERAL_CHAT

    Args:
        question: 用户问题文本
        has_data_source: 是否有可用的数据源连接

    Returns:
        QuestionType: 分类后的问题类型
    """
    import logging
    logger = logging.getLogger(__name__)

    if not question:
        logger.warning(f"[classify_question] Empty question, returning GENERAL_CHAT")
        return QuestionType.GENERAL_CHAT

    question_lower = question.lower()
    question_stripped = question.strip()

    # 1. 简单问候检测（最高优先级）
    simple_patterns = [
        "你好", "您好", "hi", "hello", "嗨",
        "谢谢", "感谢", "thank", "thanks",
        "再见", "拜拜", "bye", "goodbye"
    ]
    # 简单问候：包含关键词且问题较短（小于30字符）
    is_simple = any(p in question_lower for p in simple_patterns)
    if is_simple and len(question_stripped) < 30:
        logger.info(f"[classify_question] ✓ SIMPLE_CHAT: question='{question_stripped}', len={len(question_stripped)}")
        return QuestionType.SIMPLE_CHAT

    # 2. 可视化关键词检测（需要数据源）
    viz_keywords = [
        "画", "图表", "展示", "可视化", "趋势图", "柱状图", "饼图",
        "折线图", "散点图", "雷达图", "漏斗图", "plot", "chart", "graph",
        "可视化", "visualization", "生成图", "做个图"
    ]
    has_viz = any(kw in question for kw in viz_keywords)
    if has_data_source and has_viz:
        logger.info(f"[classify_question] ✓ VISUALIZATION: question='{question_stripped}', has_data_source=True")
        return QuestionType.VISUALIZATION

    # 3. Schema查询关键词
    schema_keywords = [
        "有哪些表", "表结构", "schema", "show tables",
        "数据库表", "所有表", "表列表", "看看有什么表",
        "数据库里有什么", "有哪些数据表"
    ]
    if any(kw in question_lower for kw in schema_keywords):
        logger.info(f"[classify_question] ✓ SCHEMA_QUERY: question='{question_stripped}'")
        return QuestionType.SCHEMA_QUERY

    # 4. 数据查询关键词（需要数据源）
    data_keywords = [
        "统计", "查询", "多少", "数量", "列表", "排行",
        "总数", "平均", "最大", "最小", "汇总", "count",
        "select", "from", "top", "前", "排名"
    ]
    # 🆕 模糊业务查询关键词（生意、销售、业绩等）
    business_keywords = [
        "生意", "销售", "业绩", "营收", "收入", "利润",
        "订单", "客户", "用户", "产品", "怎么样", "如何",
        "最近", "本月", "上月", "今年", "去年", "趋势"
    ]
    has_data_query = any(kw in question for kw in data_keywords) or any(kw in question for kw in business_keywords)
    if has_data_source and has_data_query:
        logger.info(f"[classify_question] ✓ DATA_QUERY: question='{question_stripped}', has_data_source=True")
        return QuestionType.DATA_QUERY

    # 5. 默认为普通对话
    logger.info(f"[classify_question] ✓ GENERAL_CHAT (default): question='{question_stripped[:50]}...', has_data_source={has_data_source}")
    return QuestionType.GENERAL_CHAT


class ProcessingStepBuilder:
    """
    统一处理步骤构建器

    支持多种查询场景的步骤生成：
    - AGENT_SQL: Agent SQL查询（8步）
    - GENERAL_CHAT: 普通对话（6步）
    - 动态步骤：根据问题类型自动选择合适的步骤模板
    """

    # ========== 动态步骤模板（根据问题类型选择） ==========

    # 简单对话：2步
    SIMPLE_CHAT_STEPS = [
        (1, "理解用户意图", "分析用户输入"),
        (2, "生成回复", "AI正在生成回复"),
    ]

    # Schema查询：3步
    SCHEMA_QUERY_STEPS = [
        (1, "理解查询意图", "识别Schema查询需求"),
        (2, "获取数据库结构", "正在加载表和字段信息"),
        (3, "返回结果", "整理并返回表结构"),
    ]

    # 数据查询：5步
    DATA_QUERY_STEPS = [
        (1, "理解用户问题", "分析查询需求"),
        (2, "获取数据库Schema", "加载表结构信息"),
        (3, "生成SQL语句", "AI构造查询语句"),
        (4, "执行SQL查询", "正在查询数据"),
        (5, "返回结果", "整理查询结果"),
    ]

    # 可视化：6步（包含图表生成）
    VISUALIZATION_STEPS = [
        (1, "理解用户问题", "分析可视化需求"),
        (2, "获取数据库Schema", "加载表结构信息"),
        (3, "生成SQL语句", "构造数据查询"),
        (4, "执行SQL查询", "获取图表数据"),
        (5, "生成数据可视化", "创建图表"),
        (6, "返回结果", "图表和数据分析"),
    ]

    # 普通对话6步流程模板（原有模板，保持兼容）
    GENERAL_CHAT_STEPS = [
        (1, "理解用户意图", "分析用户问题的核心需求"),
        (2, "检索上下文知识", "获取对话历史和相关上下文"),
        (3, "构建回复策略", "确定回复风格和内容结构"),
        (4, "生成回复内容", "AI正在生成回复..."),
        (5, "安全与合规检查", "检查内容合规性"),
        (6, "优化最终输出", "格式化并优化回复"),
    ]

    def build_dynamic_steps(
        self,
        question_type: QuestionType,
        question: str = "",
        has_context: bool = False
    ) -> List[StepConfig]:
        """
        根据问题类型动态构建步骤

        Args:
            question_type: 问题类型（通过classify_question获取）
            question: 用户问题（用于生成描述）
            has_context: 是否有上下文信息

        Returns:
            List[StepConfig]: 动态生成的步骤配置列表
        """
        # 选择对应的步骤模板
        if question_type == QuestionType.SIMPLE_CHAT:
            template = self.SIMPLE_CHAT_STEPS
        elif question_type == QuestionType.SCHEMA_QUERY:
            template = self.SCHEMA_QUERY_STEPS
        elif question_type == QuestionType.DATA_QUERY:
            template = self.DATA_QUERY_STEPS
        elif question_type == QuestionType.VISUALIZATION:
            template = self.VISUALIZATION_STEPS
        else:
            template = self.GENERAL_CHAT_STEPS  # 默认使用6步通用模板

        steps = []
        question_preview = question[:30] + "..." if len(question) > 30 else question

        for step, title, base_desc in template:
            # 根据步骤数量动态设置状态
            step_count = len(template)
            if step < step_count:
                status = "completed"
                duration = 100 + (step * 30)
            else:
                status = "running"
                duration = None

            # 自定义描述
            desc = self._customize_desc(step, base_desc, question, question_preview, has_context)

            step_config = StepConfig(
                step=step,
                title=title,
                description=desc,
                status=status,
                duration=duration
            )
            steps.append(step_config)

        return steps

    def _customize_desc(
        self,
        step: int,
        base_desc: str,
        question: str,
        question_preview: str,
        has_context: bool
    ) -> str:
        """
        根据步骤和问题自定义描述

        Args:
            step: 步骤编号
            base_desc: 基础描述
            question: 完整问题
            question_preview: 问题预览
            has_context: 是否有上下文

        Returns:
            str: 自定义后的描述
        """
        # 步骤1：添加问题预览
        if step == 1 and question:
            return f"{base_desc}: {question_preview}"

        # 步骤2：如果是通用对话，根据上下文调整
        if step == 2 and base_desc == "获取对话历史和相关上下文":
            return "获取对话历史和相关上下文" if has_context else "无需额外上下文"

        return base_desc

    def build_general_chat_steps(
        self,
        question: str = "",
        has_context: bool = False,
        full_content: str = ""
    ) -> List[StepConfig]:
        """
        构建普通对话的6个步骤配置

        Args:
            question: 用户问题
            has_context: 是否有上下文信息
            full_content: 完整回复内容（将放入步骤6的content_data）

        Returns:
            List[StepConfig]: 6个步骤配置
        """
        question_preview = question[:50] + "..." if len(question) > 50 else question
        steps = []

        for step, title, desc_template in self.GENERAL_CHAT_STEPS:
            # 确定状态：步骤1-3已完成，步骤4运行中，步骤5-6待定
            if step < 4:
                status = "completed"
                duration = 100 + (step * 20)  # 模拟耗时
            elif step == 4:
                status = "running"
                duration = None
            else:
                status = "pending"
                duration = None

            # 生成描述
            desc = desc_template
            if step == 1 and question:
                desc = f"分析问题: {question_preview}"
            elif step == 2:
                desc = "获取对话历史和相关上下文" if has_context else "无需额外上下文"

            step_config = StepConfig(
                step=step,
                title=title,
                description=desc,
                status=status,
                duration=duration
            )

            # 步骤6包含回复内容
            if step == 6 and full_content:
                step_config.content_type = "text"
                step_config.content_data = {"text": full_content}

            steps.append(step_config)

        return steps

    def update_step_status(
        self,
        steps: List[StepConfig],
        step_number: int,
        status: str,
        duration: Optional[int] = None,
        content_type: Optional[str] = None,
        content_data: Optional[Dict] = None
    ) -> List[StepConfig]:
        """
        更新指定步骤的状态

        Args:
            steps: 步骤列表
            step_number: 要更新的步骤编号
            status: 新状态
            duration: 耗时（毫秒）
            content_type: 内容类型
            content_data: 内容数据

        Returns:
            List[StepConfig]: 更新后的步骤列表
        """
        for step in steps:
            if step.step == step_number:
                step.status = status
                if duration is not None:
                    step.duration = duration
                if content_type:
                    step.content_type = content_type
                if content_data:
                    step.content_data = content_data
                break
        return steps

    def complete_step_4_and_finish(
        self,
        steps: List[StepConfig],
        llm_duration: int,
        full_content: str
    ) -> List[StepConfig]:
        """
        完成步骤4-6（用于LLM生成完成后）

        Args:
            steps: 步骤列表
            llm_duration: LLM生成耗时（毫秒）
            full_content: 完整回复内容

        Returns:
            List[StepConfig]: 更新后的步骤列表
        """
        # 更新步骤4为完成
        self.update_step_status(steps, 4, "completed", llm_duration)

        # 步骤5：安全检查
        self.update_step_status(steps, 5, "completed", 50)

        # 步骤6：最终输出（包含内容）
        self.update_step_status(
            steps, 6, "completed", 30,
            content_type="text",
            content_data={"text": full_content}
        )

        return steps


# 便捷函数
def build_general_chat_steps(
    question: str = "",
    has_context: bool = False,
    full_content: str = ""
) -> List[StepConfig]:
    """便捷函数：构建普通对话步骤（保持向后兼容）"""
    builder = ProcessingStepBuilder()
    return builder.build_general_chat_steps(question, has_context, full_content)


def complete_chat_steps(
    steps: List[StepConfig],
    llm_duration: int,
    full_content: str
) -> List[StepConfig]:
    """便捷函数：完成对话步骤（保持向后兼容）"""
    builder = ProcessingStepBuilder()
    return builder.complete_step_4_and_finish(steps, llm_duration, full_content)


def build_dynamic_steps(
    question: str = "",
    has_data_source: bool = False,
    has_context: bool = False
) -> List[StepConfig]:
    """
    便捷函数：根据问题类型动态构建步骤

    Args:
        question: 用户问题
        has_data_source: 是否有可用的数据源
        has_context: 是否有上下文信息

    Returns:
        List[StepConfig]: 动态生成的步骤配置
    """
    question_type = classify_question(question, has_data_source)
    builder = ProcessingStepBuilder()
    return builder.build_dynamic_steps(question_type, question, has_context)


# 导出所有公共函数和类
__all__ = [
    "QueryScenario",
    "QuestionType",
    "StepConfig",
    "ProcessingStepBuilder",
    "classify_question",
    "build_general_chat_steps",
    "build_dynamic_steps",
    "complete_chat_steps",
]
