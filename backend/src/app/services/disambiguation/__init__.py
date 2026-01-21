"""
主动消歧服务模块

检测模糊查询并生成澄清问题
"""

from .ambiguity_detector import AmbiguityDetector
from .question_generator import QuestionGenerator

__all__ = ["AmbiguityDetector", "QuestionGenerator"]
