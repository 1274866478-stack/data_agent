"""
Critic Agent - 审查员

负责：
1. 业务规则验证 - 检查 DSL 是否符合业务规则
2. 语义验证 - 检查 DSL 是否符合语义层规范
3. 质量评分 - 为 DSL 生成质量分数
"""

from typing import Dict, Any, List
import yaml
import os

from .base_agent import BaseAgent


class CriticAgent(BaseAgent):
    """
    审查员 Agent

    职责:
    1. 验证 DSL 符合语义层规范
    2. 检查业务规则
    3. 检测潜在错误
    4. 提供改进建议
    """

    def __init__(self, name: str = "critic", llm=None, rules_path: str = None):
        super().__init__(name, llm)
        self.business_rules = self._load_rules(rules_path)

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行审查逻辑

        Args:
            state: 当前状态，包含 dsl_json, cube_schema 等

        Returns:
            更新后的状态，包含 critic_report, needs_regeneration
        """
        dsl_json = state.get("dsl_json", {})
        cube_schema = state.get("cube_schema", {})
        query = state.get("query", "")

        # 执行验证
        validation_result = await self._validate_dsl(dsl_json, cube_schema, query)

        # 判断是否需要重新生成
        needs_regeneration = not validation_result["valid"]

        return {
            "critic_report": validation_result,
            "needs_regeneration": needs_regeneration
        }

    async def _validate_dsl(
        self,
        dsl_json: Dict[str, Any],
        cube_schema: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """
        验证 DSL

        Args:
            dsl_json: 要验证的 DSL
            cube_schema: Cube 定义
            query: 原始查询

        Returns:
            验证结果
        """
        errors = []
        warnings = []
        suggestions = []

        # 检查是否有错误
        if "error" in dsl_json:
            return {
                "valid": False,
                "errors": [dsl_json["error"]],
                "warnings": [],
                "score": 0.0
            }

        # 1. 检查 Cube 是否存在
        cube_name = dsl_json.get("cube")
        if not cube_name:
            errors.append("DSL 中缺少 cube 字段")
        elif cube_name not in cube_schema:
            errors.append(f"Cube '{cube_name}' 不存在，可用的 Cube: {list(cube_schema.keys())}")

        # 2. 检查 Measures 是否存在
        if cube_name and cube_name in cube_schema:
            measures = dsl_json.get("measures", [])
            available_measures = cube_schema.get(cube_name, {}).get("measures", [])

            for measure in measures:
                # 处理可能的 "Cube.measure" 格式
                measure_name = measure.split(".")[-1] if "." in measure else measure
                if measure_name not in available_measures:
                    errors.append(f"Measure '{measure}' 在 Cube '{cube_name}' 中不存在")

        # 3. 检查 Dimensions 是否存在
        if cube_name and cube_name in cube_schema:
            dimensions = dsl_json.get("dimensions", [])
            available_dimensions = cube_schema.get(cube_name, {}).get("dimensions", [])

            for dimension in dimensions:
                dim_name = dimension.split(".")[-1] if "." in dimension else dimension
                if dim_name not in available_dimensions:
                    errors.append(f"Dimension '{dimension}' 在 Cube '{cube_name}' 中不存在")

        # 4. 业务规则检查
        rule_violations = self._check_business_rules(dsl_json, query)
        warnings.extend(rule_violations)

        # 5. 最佳实践检查
        best_practice_warnings = self._check_best_practices(dsl_json)
        warnings.extend(best_practice_warnings)

        # 6. 计算分数
        score = self._calculate_score(errors, warnings)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
            "score": score
        }

    def _load_rules(self, rules_path: str = None) -> List[Dict[str, Any]]:
        """加载业务规则"""
        if rules_path is None:
            # 尝试从默认位置加载
            default_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "rules",
                "business_rules.yaml"
            )
            if os.path.exists(default_path):
                rules_path = default_path

        if not rules_path or not os.path.exists(rules_path):
            return []

        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get("rules", [])
        except Exception as e:
            print(f"加载业务规则失败: {e}")
            return []

    def _check_business_rules(
        self,
        dsl_json: Dict[str, Any],
        query: str
    ) -> List[str]:
        """检查业务规则"""
        warnings = []

        for rule in self.business_rules:
            rule_name = rule.get("name", "")

            # 检查模式匹配
            pattern = rule.get("pattern")
            if pattern:
                # 简单检查：将 DSL 转为字符串后检查
                dsl_str = str(dsl_json).lower()
                if pattern.lower() in dsl_str:
                    warnings.append({
                        "rule": rule_name,
                        "issue": rule.get("error_message", "违反业务规则"),
                        "suggestion": rule.get("suggestion", "")
                    })

            # 检查字段验证
            field = rule.get("field")
            if field:
                # 检查 DSL 中是否有该字段
                if field in str(dsl_json):
                    validation = rule.get("validation")
                    if validation:
                        warnings.append({
                            "rule": rule_name,
                            "issue": f"字段 '{field}' 需要验证: {validation}",
                            "suggestion": rule.get("suggestion", "")
                        })

        return warnings

    def _check_best_practices(self, dsl_json: Dict[str, Any]) -> List[str]:
        """检查最佳实践"""
        warnings = []

        # 检查是否有时间维度
        if not dsl_json.get("timeDimension") and not dsl_json.get("dimensions"):
            warnings.append({
                "rule": "best_practice",
                "issue": "DSL 中没有时间维度，可能导致数据聚合问题",
                "suggestion": "考虑添加时间维度以获得更好的分析结果"
            })

        # 检查度量数量
        measures = dsl_json.get("measures", [])
        if len(measures) > 5:
            warnings.append({
                "rule": "best_practice",
                "issue": f"度量数量过多 ({len(measures)} 个)，可能导致查询复杂",
                "suggestion": "考虑将查询拆分为多个子查询"
            })

        # 检查限制
        limit = dsl_json.get("limit")
        if limit and limit > 1000:
            warnings.append({
                "rule": "best_practice",
                "issue": f"限制过大 ({limit})，可能影响性能",
                "suggestion": "建议使用更小的限制值或分页"
            })

        return warnings

    def _calculate_score(
        self,
        errors: List[str],
        warnings: List[str]
    ) -> float:
        """计算质量分数 (0-1)"""
        # 基础分
        score = 1.0

        # 错误扣分
        score -= len(errors) * 0.5

        # 警告扣分
        score -= len(warnings) * 0.1

        # 确保分数在 0-1 之间
        return max(0.0, min(1.0, score))


def load_default_rules() -> List[Dict[str, Any]]:
    """加载默认业务规则"""
    return [
        {
            "name": "dau_must_use_distinct",
            "description": "DAU 计算必须使用 DISTINCT",
            "pattern": "count(user_id)",
            "error_message": "DAU 必须使用 count(DISTINCT user_id)",
            "suggestion": "使用 unique_users 度量"
        },
        {
            "name": "revenue_filter_valid_range",
            "description": "金额不能为负",
            "field": "amount",
            "validation": "value >= 0",
            "error_message": "金额过滤条件无效",
            "suggestion": "检查金额范围设置"
        },
        {
            "name": "time_range_not_too_wide",
            "description": "时间范围不宜过大",
            "check_type": "time_dimension",
            "max_days": 365,
            "error_message": "查询时间跨度过大",
            "suggestion": "缩小时间范围或使用预聚合"
        },
        {
            "name": "join_path_predefined",
            "description": "使用预定义的 Join 路径",
            "check_type": "multi_table",
            "error_message": "不要直接 JOIN，使用语义层预定义的关联",
            "suggestion": "检查语义层定义"
        }
    ]
