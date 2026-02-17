"""
反问生成器 - 生成澄清问题

负责：
1. 根据模糊类型生成问题
2. 提供选项
3. 优先级排序
"""

from typing import Dict, List, Any, Optional


class QuestionGenerator:
    """澄清问题生成器"""

    # 问题模板
    QUESTION_TEMPLATES = {
        "multiple_metrics": {
            "question": "请问您关心以下哪个指标？",
            "type": "single_choice",
            "options": ["销售额", "订单量", "用户数", "利润"],
            "required": True,
            "priority": "high"
        },
        "time_range": {
            "question": "请问您想查询的时间范围是？",
            "type": "single_choice",
            "options": [
                "最近7天",
                "最近30天",
                "本月",
                "本季度",
                "本年度",
                "自定义时间"
            ],
            "required": True,
            "priority": "high"
        },
        "comparison_base": {
            "question": "请问您想与哪个时间点对比？",
            "type": "single_choice",
            "options": [
                "去年同期",
                "上月",
                "上周",
                "前一天"
            ],
            "required": False,
            "priority": "medium"
        },
        "aggregation_level": {
            "question": "请问您希望按什么维度统计？",
            "type": "multiple_choice",
            "options": ["按天", "按周", "按月", "按产品", "按地区"],
            "required": False,
            "priority": "medium"
        },
        "missing_context": {
            "question": "请问您指的是？",
            "type": "text_input",
            "placeholder": "请提供更多上下文信息",
            "required": True,
            "priority": "high"
        }
    }

    async def generate_questions(
        self,
        ambiguity_result: Dict[str, Any],
        cube_schema: Optional[Dict[str, Any]] = None,
        max_questions: int = 3
    ) -> List[Dict[str, Any]]:
        """
        生成澄清问题列表

        Args:
            ambiguity_result: AmbiguityDetector 的检测结果
            cube_schema: 可选的 Cube 定义（用于动态生成选项）
            max_questions: 最大问题数量

        Returns:
            问题列表（按优先级排序）
        """
        questions = []
        ambiguity_types = ambiguity_result.get("ambiguity_types", [])

        for ambiguity_type in ambiguity_types:
            if ambiguity_type in self.QUESTION_TEMPLATES:
                template = self.QUESTION_TEMPLATES[ambiguity_type].copy()

                # 如果有 Cube schema，动态生成选项
                if cube_schema and ambiguity_type in ["multiple_metrics", "aggregation_level"]:
                    template["options"] = self._generate_dynamic_options(
                        ambiguity_type,
                        cube_schema
                    )

                questions.append(template)

        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        questions.sort(key=lambda q: priority_order.get(q.get("priority", "low"), 2))

        # 限制数量
        return questions[:max_questions]

    def _generate_dynamic_options(
        self,
        ambiguity_type: str,
        cube_schema: Dict[str, Any]
    ) -> List[str]:
        """根据 Cube 定义动态生成选项"""
        options = []

        if ambiguity_type == "multiple_metrics":
            # 收集所有度量
            for cube_name, cube_def in cube_schema.items():
                measures = cube_def.get("measures", [])
                for measure in measures:
                    options.append(f"{cube_name}.{measure}")

        elif ambiguity_type == "aggregation_level":
            # 收集所有维度
            for cube_name, cube_def in cube_schema.items():
                dimensions = cube_def.get("dimensions", [])
                for dim in dimensions:
                    options.append(dim)

        return options[:10]  # 限制选项数量

    async def refine_query_with_answers(
        self,
        original_query: str,
        answers: Dict[str, Any]
    ) -> str:
        """
        根据用户答案精炼查询

        Args:
            original_query: 原始查询
            answers: 用户答案

        Returns:
            精炼后的查询
        """
        refined = original_query

        # 添加指标信息
        if "metric" in answers:
            refined = f"{answers['metric']}的{refined}"

        # 添加时间范围
        if "time_range" in answers:
            time_range = answers["time_range"]
            refined = f"{time_range}{refined}"

        # 添加对比基准
        if "comparison_base" in answers:
            refined = f"{refined}，与{answers['comparison_base']}对比"

        # 添加聚合维度
        if "aggregation_level" in answers:
            levels = answers["aggregation_level"]
            if isinstance(levels, list):
                refined = f"{refined}，按{'和'.join(levels)}统计"
            else:
                refined = f"{refined}，按{levels}统计"

        return refined
