"""
# [PROCESSING_STEPS] 统一处理步骤构建服务

## [HEADER]
**文件名**: processing_steps.py
**职责**: 为不同场景（Agent查询、普通对话）构建统一的处理步骤配置
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-05): 初始版本 - 统一步骤构建器

## [INPUT]
- scenario: QueryScenario - 查询场景类型
- question: str - 用户问题（用于生成描述）
- has_context: bool - 是否有上下文信息
- full_content: str - 完整回复内容（用于步骤6）

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


class QueryScenario(Enum):
    """查询场景枚举"""
    AGENT_SQL = "agent_sql"           # Agent SQL查询（8步）
    GENERAL_CHAT = "general_chat"     # 普通对话（6步）
    DOCUMENT_QUERY = "document_query" # 文档查询（未来扩展）
    MIXED_QUERY = "mixed_query"       # 混合查询（未来扩展）


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


class ProcessingStepBuilder:
    """
    统一处理步骤构建器

    支持多种查询场景的步骤生成：
    - AGENT_SQL: Agent SQL查询（8步）
    - GENERAL_CHAT: 普通对话（6步）
    """

    # 普通对话6步流程模板
    GENERAL_CHAT_STEPS = [
        (1, "理解用户意图", "分析用户问题的核心需求"),
        (2, "检索上下文知识", "获取对话历史和相关上下文"),
        (3, "构建回复策略", "确定回复风格和内容结构"),
        (4, "生成回复内容", "AI正在生成回复..."),
        (5, "安全与合规检查", "检查内容合规性"),
        (6, "优化最终输出", "格式化并优化回复"),
    ]

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
    """便捷函数：构建普通对话步骤"""
    builder = ProcessingStepBuilder()
    return builder.build_general_chat_steps(question, has_context, full_content)


def complete_chat_steps(
    steps: List[StepConfig],
    llm_duration: int,
    full_content: str
) -> List[StepConfig]:
    """便捷函数：完成对话步骤"""
    builder = ProcessingStepBuilder()
    return builder.complete_step_4_and_finish(steps, llm_duration, full_content)
