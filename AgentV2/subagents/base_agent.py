"""
Agent 基类 - SOTA 多智能体框架

所有子 Agent 的抽象基类，定义统一接口。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    """Agent 基类"""

    def __init__(self, name: str, llm=None):
        """
        初始化 Agent

        Args:
            name: Agent 名称
            llm: LLM 实例 (可选)
        """
        self.name = name
        self.llm = llm

    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 Agent 逻辑

        Args:
            state: 当前状态字典

        Returns:
            更新后的状态字典
        """
        pass

    def _build_prompt(self, template: str, **kwargs) -> str:
        """
        构建 Prompt

        Args:
            template: Prompt 模板
            **kwargs: 模板变量

        Returns:
            格式化后的 Prompt
        """
        return template.format(**kwargs)

    def get_name(self) -> str:
        """获取 Agent 名称"""
        return self.name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
