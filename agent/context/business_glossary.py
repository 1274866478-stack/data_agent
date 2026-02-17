# -*- coding: utf-8 -*-
"""
业务术语表 - 术语规范化和别名映射

这个模块提供业务术语表服务，用于：
1. 城市别名映射（魔都 → 上海）
2. 行业术语映射（GMV → total_amount）
3. 状态值规范化（已完成 → completed）
4. 时间表达式规范化（本月 → DATE_TRUNC('month', CURRENT_DATE)）
5. 从 JSON 配置文件加载术语表（v2.0 新增）

作者: Data Agent Team
版本: 2.0.0
"""

import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class GlossaryEntry:
    """术语表条目

    Attributes:
        term: 标准术语
        aliases: 别名列表
        mapping_type: 映射类型
        target_value: 目标值
        description: 描述
    """
    term: str
    aliases: List[str]
    mapping_type: str
    target_value: Any
    description: str


class BusinessGlossary:
    """
    业务术语表服务

    功能：
        1. 城市别名映射（魔都 → 上海）
        2. 行业术语映射（GMV → total_amount）
        3. 状态值规范化（已完成 → completed）
        4. 时间表达式规范化（本月 → DATE_TRUNC）
    """

    # 城市别名映射
    CITY_ALIASES: Dict[str, str] = {
        "魔都": "上海",
        "申城": "上海",
        "首都": "北京",
        "帝都": "北京",
        "羊城": "广州",
        "鹏城": "深圳",
        "花城": "广州",
        "江城": "武汉",
        "蓉城": "成都",
        "山城": "重庆",
        "西湖": "杭州",
        "姑苏": "苏州",
        "金陵": "南京",
    }

    # 业务指标别名映射
    BUSINESS_METRIC_ALIASES: Dict[str, Dict] = {
        "GMV": {
            "target": "total_amount",
            "cube": "Orders",
            "measure": "total_revenue",
            "description": "商品交易总额 (Gross Merchandise Volume)"
        },
        "ARPU": {
            "target": "avg_revenue_per_user",
            "sql_template": "SUM(total_amount) / COUNT(DISTINCT customer_id)",
            "description": "每用户平均收入 (Average Revenue Per User)"
        },
        "ROI": {
            "target": "return_on_investment",
            "description": "投资回报率 (Return on Investment)"
        },
        "LTV": {
            "target": "lifetime_value",
            "description": "客户生命周期价值 (Lifetime Value)"
        },
        "CAC": {
            "target": "customer_acquisition_cost",
            "description": "客户获取成本 (Customer Acquisition Cost)"
        },
        "AOV": {
            "target": "avg_order_value",
            "description": "平均订单价值 (Average Order Value)"
        },
    }

    # 状态值映射（按表分组）
    STATUS_VALUE_MAPPING: Dict[str, Dict[str, str]] = {
        "Orders": {
            "已完成": "completed",
            "完成": "completed",
            "进行中": "processing",
            "处理中": "processing",
            "已取消": "cancelled",
            "取消": "cancelled",
            "待处理": "pending",
            "待付款": "pending_payment",
            "已退款": "refunded",
            "退款": "refunded",
            "已发货": "shipped",
            "发货": "shipped",
            "已完成": "delivered",
        },
        "Customers": {
            "活跃": "active",
            "非活跃": "inactive",
            "禁用": "disabled",
            "正常": "active",
        },
        "Products": {
            "在售": "available",
            "售罄": "sold_out",
            "下架": "discontinued",
            "缺货": "out_of_stock",
        },
    }

    # 时间表达式映射
    TIME_EXPRESSIONS: Dict[str, str] = {
        # 相对日期
        "今天": "CURRENT_DATE",
        "昨天": "CURRENT_DATE - INTERVAL '1 day'",
        "前天": "CURRENT_DATE - INTERVAL '2 days'",
        "明天": "CURRENT_DATE + INTERVAL '1 day'",
        "后天": "CURRENT_DATE + INTERVAL '2 days'",

        # 周
        "本周": "DATE_TRUNC('week', CURRENT_DATE)",
        "上周": "DATE_TRUNC('week', CURRENT_DATE - INTERVAL '1 week')",
        "下周": "DATE_TRUNC('week', CURRENT_DATE + INTERVAL '1 week')",
        "这周": "DATE_TRUNC('week', CURRENT_DATE)",
        "那周": "DATE_TRUNC('week', CURRENT_DATE)",  # 需要上下文

        # 月
        "本月": "DATE_TRUNC('month', CURRENT_DATE)",
        "上月": "DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')",
        "下月": "DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month')",
        "这个月": "DATE_TRUNC('month', CURRENT_DATE)",
        "上个月": "DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')",

        # 季度
        "本季度": "DATE_TRUNC('quarter', CURRENT_DATE)",
        "上季度": "DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '3 months')",
        "今年": "DATE_TRUNC('year', CURRENT_DATE)",
        "去年": "DATE_TRUNC('year', CURRENT_DATE - INTERVAL '1 year')",

        # 相对时间段
        "最近": "CURRENT_DATE - INTERVAL '30 days'",
        "最近一周": "CURRENT_DATE - INTERVAL '7 days'",
        "最近一月": "CURRENT_DATE - INTERVAL '30 days'",
        "最近三月": "CURRENT_DATE - INTERVAL '90 days'",
        "近期": "CURRENT_DATE - INTERVAL '30 days'",
    }

    # 比较/分析术语
    ANALYTICS_TERMS: Dict[str, str] = {
        "同比": "同比（与去年同期相比）",
        "环比": "环比（与上一周期相比）",
        "趋势": "时间序列分析",
        "占比": "百分比计算",
        "分布": "分组统计",
        "排名": "ORDER BY",
        "Top": "LIMIT",
        "前": "ORDER BY ... LIMIT",
    }

    def __init__(
        self,
        custom_glossary_path: Optional[str] = None,
        enable_auto_discovery: bool = True,
        enable_hot_reload: bool = False
    ):
        """初始化业务术语表

        Args:
            custom_glossary_path: 自定义术语表文件路径（JSON/YAML）
            enable_auto_discovery: 是否启用自动发现新术语
            enable_hot_reload: 是否启用热更新（v2.0 新增）
        """
        self.entries: List[GlossaryEntry] = []
        self.enable_auto_discovery = enable_auto_discovery
        self.enable_hot_reload = enable_hot_reload
        self._config_file_path: Optional[Path] = None
        self._config_mtime: Optional[float] = None
        self._lock = threading.RLock()

        # 默认配置文件路径
        if custom_glossary_path is None:
            # 尝试加载默认的 JSON 配置文件
            default_json = Path(__file__).parent.parent / "business_glossary.json"
            if default_json.exists():
                custom_glossary_path = str(default_json)

        if custom_glossary_path:
            self._config_file_path = Path(custom_glossary_path)
            self._load_custom_glossary(custom_glossary_path)
            if self.enable_hot_reload:
                self._update_mtime()
        else:
            # 回退到内置术语表
            self._load_builtin_glossary()

    def _load_builtin_glossary(self):
        """加载内置术语表"""
        # 城市别名
        for alias, city in self.CITY_ALIASES.items():
            self.entries.append(GlossaryEntry(
                term=city,
                aliases=[alias],
                mapping_type="city_alias",
                target_value=city,
                description=f"城市别名: {alias} → {city}"
            ))

        # 业务指标
        for acronym, definition in self.BUSINESS_METRIC_ALIASES.items():
            self.entries.append(GlossaryEntry(
                term=definition["target"],
                aliases=[acronym],
                mapping_type="business_metric",
                target_value=definition,
                description=definition.get("description", "")
            ))

        logger.info(f"加载内置术语表: {len(self.entries)} 条")

    def _load_custom_glossary(self, path: str) -> bool:
        """加载自定义术语表（JSON/YAML 文件）

        v2.0 更新：
        - 支持 JSON 配置文件中的 id 和 metadata 字段
        - 返回加载状态

        Args:
            path: 文件路径

        Returns:
            是否加载成功
        """
        file_path = Path(path)

        if not file_path.exists():
            logger.warning(f"自定义术语表文件不存在: {path}")
            return False

        try:
            if file_path.suffix == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            elif file_path.suffix in ['.yaml', '.yml']:
                import yaml
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
            else:
                logger.warning(f"不支持的文件格式: {file_path.suffix}")
                return False

            # 解析自定义术语（支持 v2.0 格式）
            entries_added = 0
            for entry_data in data.get('entries', []):
                # 支持从 metadata 中获取 description
                metadata = entry_data.get('metadata', {})
                description = entry_data.get('description', metadata.get('description', ''))

                entry = GlossaryEntry(
                    term=entry_data['term'],
                    aliases=entry_data.get('aliases', []),
                    mapping_type=entry_data.get('mapping_type', 'custom'),
                    target_value=entry_data.get('target_value'),
                    description=description
                )
                self.entries.append(entry)
                entries_added += 1

            logger.info(f"加载自定义术语表: {entries_added} 条 (版本: {data.get('version', '1.0')})")
            return True

        except Exception as e:
            logger.error(f"加载自定义术语表失败: {e}")
            return False

    def normalize_term(
        self,
        term: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """规范化术语

        Args:
            term: 原始术语
            context: 上下文（如表名，用于状态值映射）

        Returns:
            规范化结果

        示例:
            输入: "魔都"
            输出: {"normalized": "上海", "type": "city_alias"}

            输入: "GMV"
            输出: {"normalized": "total_amount", "type": "business_metric", ...}
        """
        term_stripped = term.strip()

        # 1. 检查城市别名
        if term_stripped in self.CITY_ALIASES:
            return {
                "normalized": self.CITY_ALIASES[term_stripped],
                "type": "city_alias",
                "original": term_stripped,
                "description": f"城市别名: {term_stripped} → {self.CITY_ALIASES[term_stripped]}"
            }

        # 2. 检查业务指标别名
        if term_stripped in self.BUSINESS_METRIC_ALIASES:
            metric_info = self.BUSINESS_METRIC_ALIASES[term_stripped]
            return {
                "normalized": metric_info["target"],
                "type": "business_metric",
                "original": term_stripped,
                "cube": metric_info.get("cube"),
                "measure": metric_info.get("measure"),
                "sql_template": metric_info.get("sql_template"),
                "description": metric_info.get("description", "")
            }

        # 3. 检查状态值映射
        if context:
            for table, status_map in self.STATUS_VALUE_MAPPING.items():
                if context.lower() in table.lower() or table.lower() in str(context).lower():
                    if term_stripped in status_map:
                        return {
                            "normalized": status_map[term_stripped],
                            "type": "status_value",
                            "table": table,
                            "original": term_stripped,
                            "description": f"状态值: {term_stripped} → {status_map[term_stripped]}"
                        }

            # 跨所有表检查
            for table, status_map in self.STATUS_VALUE_MAPPING.items():
                if term_stripped in status_map:
                    return {
                        "normalized": status_map[term_stripped],
                        "type": "status_value",
                        "table": table,
                        "original": term_stripped,
                        "description": f"状态值: {term_stripped} → {status_map[term_stripped]}"
                    }

        # 4. 检查时间表达式
        if term_stripped in self.TIME_EXPRESSIONS:
            return {
                "normalized": self.TIME_EXPRESSIONS[term_stripped],
                "type": "time_expression",
                "original": term_stripped,
                "description": f"时间表达式: {term_stripped} → {self.TIME_EXPRESSIONS[term_stripped]}"
            }

        # 未找到映射
        return {
            "normalized": term_stripped,
            "type": "no_mapping",
            "original": term_stripped,
            "description": "未找到映射，保持原值"
        }

    def normalize_query(self, query: str) -> str:
        """规范化查询中的所有术语

        Args:
            query: 原始查询

        Returns:
            规范化后的查询
        """
        normalized = query

        # 替换城市别名
        for alias, city in self.CITY_ALIASES.items():
            normalized = normalized.replace(alias, city)

        # 替换状态值
        for table, status_map in self.STATUS_VALUE_MAPPING.items():
            for original, standard in status_map.items():
                normalized = normalized.replace(original, standard)

        return normalized

    def get_glossary_summary(self) -> Dict[str, Any]:
        """获取术语表摘要

        Returns:
            术语表统计信息
        """
        return {
            "total_entries": len(self.entries),
            "city_aliases": len(self.CITY_ALIASES),
            "business_metrics": len(self.BUSINESS_METRIC_ALIASES),
            "status_mappings": sum(len(m) for m in self.STATUS_VALUE_MAPPING.values()),
            "time_expressions": len(self.TIME_EXPRESSIONS),
        }

    def inject_glossary_to_prompt(
        self,
        query: str,
        max_terms: int = 5
    ) -> str:
        """将相关术语注入到 Prompt

        Args:
            query: 用户查询
            max_terms: 最多注入的术语数

        Returns:
            术语注入文本
        """
        relevant_terms = []

        # 分析查询中的术语
        query_lower = query.lower()

        # 检查城市别名
        for alias in self.CITY_ALIASES.keys():
            if alias in query:
                relevant_terms.append({
                    "type": "city_alias",
                    "original": alias,
                    "normalized": self.CITY_ALIASES[alias]
                })

        # 检查业务指标
        for acronym in self.BUSINESS_METRIC_ALIASES.keys():
            if acronym.lower() in query_lower:
                relevant_terms.append({
                    "type": "business_metric",
                    "original": acronym,
                    "normalized": self.BUSINESS_METRIC_ALIASES[acronym]["target"]
                })

        # 检查时间表达式
        for expr in self.TIME_EXPRESSIONS.keys():
            if expr in query:
                relevant_terms.append({
                    "type": "time_expression",
                    "original": expr,
                    "normalized": self.TIME_EXPRESSIONS[expr]
                })

        # 限制数量并生成注入文本
        relevant_terms = relevant_terms[:max_terms]

        if not relevant_terms:
            return ""

        injection_lines = ["## 术语规范化映射"]
        injection_lines.append("检测到以下术语需要规范化:")

        for term in relevant_terms:
            injection_lines.append(
                f"- {term['original']} → {term['normalized']} ({term['type']})"
            )

        return "\n".join(injection_lines)

    def add_custom_entry(
        self,
        term: str,
        aliases: List[str],
        mapping_type: str,
        target_value: Any,
        description: str = ""
    ):
        """添加自定义术语条目

        Args:
            term: 标准术语
            aliases: 别名列表
            mapping_type: 映射类型
            target_value: 目标值
            description: 描述
        """
        entry = GlossaryEntry(
            term=term,
            aliases=aliases,
            mapping_type=mapping_type,
            target_value=target_value,
            description=description
        )
        self.entries.append(entry)
        logger.info(f"添加自定义术语: {term}")

    def _update_mtime(self):
        """更新配置文件的修改时间"""
        if self._config_file_path and self._config_file_path.exists():
            self._config_mtime = self._config_file_path.stat().st_mtime

    def _check_reload_needed(self) -> bool:
        """检查是否需要重新加载配置文件"""
        if not self.enable_hot_reload or not self._config_file_path:
            return False

        if not self._config_file_path.exists():
            return False

        current_mtime = self._config_file_path.stat().st_mtime
        return current_mtime != self._config_mtime

    def reload_if_needed(self) -> bool:
        """如果配置文件已修改，重新加载

        Returns:
            是否执行了重新加载
        """
        with self._lock:
            if self._check_reload_needed():
                logger.info(f"检测到配置文件变更，重新加载: {self._config_file_path}")
                self.entries.clear()
                self._load_custom_glossary(str(self._config_file_path))
                self._update_mtime()
                return True
        return False

    def reload(self) -> bool:
        """强制重新加载配置文件

        Returns:
            是否加载成功
        """
        with self._lock:
            if not self._config_file_path:
                logger.warning("没有配置文件路径，无法重新加载")
                return False

            if not self._config_file_path.exists():
                logger.warning(f"配置文件不存在: {self._config_file_path}")
                return False

            self.entries.clear()
            success = self._load_custom_glossary(str(self._config_file_path))
            self._update_mtime()
            return success

    def export_glossary(self, output_path: str, format: str = "json"):
        """导出术语表到文件

        Args:
            output_path: 输出文件路径
            format: 文件格式（json/yaml）
        """
        data = {
            "entries": [
                {
                    "term": e.term,
                    "aliases": e.aliases,
                    "mapping_type": e.mapping_type,
                    "target_value": e.target_value,
                    "description": e.description
                }
                for e in self.entries
            ]
        }

        output_file = Path(output_path)

        try:
            if format == "json":
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif format in ["yaml", "yml"]:
                import yaml
                with open(output_file, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True)
            else:
                raise ValueError(f"不支持的格式: {format}")

            logger.info(f"术语表已导出到: {output_path}")

        except Exception as e:
            logger.error(f"导出术语表失败: {e}")


# ============================================================================
# LangChain 工具函数
# ============================================================================

def query_business_glossary(
    term: str,
    context: Optional[str] = None
) -> str:
    """查询业务术语表 - 供 LLM 调用

    Args:
        term: 要查询的术语
        context: 上下文（如表名）

    Returns:
        JSON 格式的规范化结果

    示例:
        >>> query_business_glossary("魔都")
        '{"normalized": "上海", "type": "city_alias", ...}'
    """
    glossary = BusinessGlossary()
    result = glossary.normalize_term(term, context)
    return json.dumps(result, ensure_ascii=False, indent=2)


def get_glossary_summary() -> str:
    """获取术语表摘要 - 供 LLM 调用

    Returns:
        JSON 格式的术语表统计信息
    """
    glossary = BusinessGlossary()
    summary = glossary.get_glossary_summary()
    return json.dumps(summary, ensure_ascii=False, indent=2)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("业务术语表测试")
    print("=" * 60)

    glossary = BusinessGlossary()

    # 测试 1: 城市别名
    print("\n[测试 1] 城市别名规范化: '魔都'")
    result = glossary.normalize_term("魔都")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 测试 2: 业务指标
    print("\n[测试 2] 业务指标规范化: 'GMV'")
    result = glossary.normalize_term("GMV")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 测试 3: 状态值
    print("\n[测试 3] 状态值规范化: '已完成' (context: Orders)")
    result = glossary.normalize_term("已完成", context="Orders")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 测试 4: 时间表达式
    print("\n[测试 4] 时间表达式规范化: '本月'")
    result = glossary.normalize_term("本月")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 测试 5: 查询规范化
    print("\n[测试 5] 查询规范化")
    original = "魔都的客户本月GMV是多少？"
    normalized = glossary.normalize_query(original)
    print(f"原始: {original}")
    print(f"规范化: {normalized}")

    # 测试 6: 术语表摘要
    print("\n[测试 6] 术语表摘要")
    summary = glossary.get_glossary_summary()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
