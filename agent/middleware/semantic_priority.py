# -*- coding: utf-8 -*-
"""
语义层优先中间件 - 拦截查询并引导 LLM 使用语义层

这个中间件在 LLM 调用前拦截用户查询，检测业务术语，
并在上下文中注入语义层使用引导，优先调用语义层工具而非直接生成 SQL。

核心原理：
    1. 检测用户查询中的业务术语
    2. 在 LLM 上下文中注入语义层使用引导
    3. 优先调用语义层工具而非直接生成 SQL

作者: Data Agent Team
版本: 1.0.0
"""

import re
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# LangChain/LangGraph imports for deepagents compatibility
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelCallResult
from langgraph.prebuilt.tool_node import ToolCallRequest
from langchain_core.messages.tool import ToolMessage
from langgraph.types import Command


@dataclass
class SemanticDetectionResult:
    """语义检测结果

    Attributes:
        detected_terms: 检测到的业务术语列表
        confidence: 检测置信度 (0-1)
        needs_semantic_layer: 是否需要使用语义层
        guidance: 生成的引导文本
    """
    detected_terms: List[str]
    confidence: float
    needs_semantic_layer: bool
    guidance: str


class SemanticPriorityMiddleware(AgentMiddleware):
    """
    语义层优先中间件

    继承 AgentMiddleware 以与 deepagents 正确集成。

    工作原理:
        1. 检测用户查询中的业务术语
        2. 在 LLM 上下文中注入语义层使用引导
        3. 优先调用语义层工具而非直接生成 SQL

    使用示例:
        middleware = SemanticPriorityMiddleware()
        enhanced_input = middleware.before_agent_execution({
            "query": "订单总收入是多少？",
            "tenant_id": "xxx"
        })
    """

    # 业务术语关键词模式（按类别分组）
    BUSINESS_TERM_PATTERNS = {
        "financial": [
            r'(总收入|净收入|销售额|营收|毛利|净利润|利润|收入)',
            r'(GMV|ARPU|ROI|LTV|CAC|EBITDA)',  # 行业缩写
            r'(营业额|流水|业绩|收益)',  # 同义词
        ],
        "count": [
            r'(订单数|客户数|用户数|商品数|产品数)',
            r'(数量|个数|人数|笔数)',
        ],
        "status": [
            r'(完成|进行中|取消|退款|已发货|待处理)',
            r'(已完成|已取消|已退款|已发货)',
            r'(活跃|非活跃)',
        ],
        "time": [
            r'(月|季度|年|本周|上周|本月|上月|今年|去年)',
            r'(同比|环比|日均|月均)',
            r'(最近|近期|当前|现在)',
            r'(今天|昨天|前天|明天)',
            r'(本周|上周|下周|这周|那周)',
        ],
        "analytics": [
            r'(趋势|分析|统计|汇总|总计)',
            r'(占比|比例|百分比|分布)',
            r'(增长率|增长|下降|波动)',
        ],
        "location": [
            r'(城市|地区|区域|省份|国家)',
            r'(北京|上海|广州|深圳|杭州|成都|重庆|武汉|西安)',
        ],
    }

    # 需要语义层优先处理的关键词
    SEMANTIC_PRIORITY_KEYWORDS = [
        '总收入', '净收入', '销售额', '营收', '毛利', '净利润',
        'GMV', 'ARPU', 'ROI',
        '订单数', '客户数', '用户数',
        '转化率', '完成率', '成功率',
        '平均订单金额', '客单价', 'ARPU',
    ]

    def __init__(
        self,
        enable_detection: bool = True,
        min_confidence: float = 0.3,
        enable_logging: bool = True
    ):
        """初始化语义层优先中间件

        Args:
            enable_detection: 是否启用术语检测
            min_confidence: 最小置信度阈值
            enable_logging: 是否启用日志
        """
        self.enable_detection = enable_detection
        self.min_confidence = min_confidence
        self.enable_logging = enable_logging

    @property
    def name(self) -> str:
        """返回中间件名称"""
        return "SemanticPriorityMiddleware"

    def before_agent_execution(
        self,
        agent_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """在 LLM 调用前注入语义层引导

        Args:
            agent_input: Agent 输入，包含 query, tenant_id 等字段

        Returns:
            增强后的 Agent 输入

        输入示例:
            {"query": "订单总收入是多少？", "tenant_id": "xxx"}

        输出示例:
            {
                "query": "订单总收入是多少？",
                "tenant_id": "xxx",
                "__semantic_guidance__": "检测到业务术语: 总收入。请先调用 resolve_business_term..."
            }
        """
        if not self.enable_detection:
            return agent_input

        query = agent_input.get("query", "")
        if not query:
            return agent_input

        # 检测业务术语
        detection_result = self._detect_business_terms(query)

        if detection_result.needs_semantic_layer:
            guidance = self._generate_semantic_guidance(detection_result)

            # 注入引导信息
            agent_input["__semantic_guidance__"] = guidance
            agent_input["__detected_terms__"] = detection_result.detected_terms
            agent_input["__semantic_confidence__"] = detection_result.confidence

            if self.enable_logging:
                logger.info(
                    f"[SemanticPriority] 检测到业务术语: {detection_result.detected_terms}, "
                    f"置信度: {detection_result.confidence:.2f}"
                )

        return agent_input

    def _detect_business_terms(self, query: str) -> SemanticDetectionResult:
        """检测查询中的业务术语

        Args:
            query: 用户查询

        Returns:
            语义检测结果
        """
        detected = set()
        total_matches = 0
        max_matches = 0

        # 按类别检测
        for category, patterns in self.BUSINESS_TERM_PATTERNS.items():
            category_matches = 0
            for pattern in patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        detected.update(match)
                    else:
                        detected.add(match)
                    category_matches += 1

            total_matches += category_matches
            max_matches = max(max_matches, category_matches)

        # 检查优先级关键词
        for keyword in self.SEMANTIC_PRIORITY_KEYWORDS:
            if keyword in query:
                detected.add(keyword)

        detected_list = list(detected)

        # 计算置信度
        if detected_list:
            confidence = min(1.0, 0.5 + (total_matches * 0.1))
        else:
            confidence = 0.0

        # 判断是否需要语义层
        needs_semantic = confidence >= self.min_confidence and len(detected_list) > 0

        return SemanticDetectionResult(
            detected_terms=detected_list,
            confidence=confidence,
            needs_semantic_layer=needs_semantic,
            guidance=""  # 将在 _generate_semantic_guidance 中生成
        )

    def _generate_semantic_guidance(
        self,
        detection_result: SemanticDetectionResult
    ) -> str:
        """生成语义层使用引导

        Args:
            detection_result: 语义检测结果

        Returns:
            引导文本
        """
        terms = detection_result.detected_terms
        confidence = detection_result.confidence

        guidance = f"""
🎯 检测到业务术语: {', '.join(terms)} (置信度: {confidence:.1%})

⚠️ 重要：请按以下步骤操作：

1. **首先调用 list_tables() 获取实际表名**
   - 必须在调用语义层工具之前完成
   - 获取数据库中的实际表名（如 "订单表"、"用户表"）

2. **然后调用 resolve_business_term 解析业务术语**
   - 输入: 业务术语（如 "总收入"）
   - 输出: 语义定义（包含 cube、actual_table_name、SQL 表达式）

3. **使用 actual_table_name 构建查询**
   - ❌ 不要使用 `cube` 字段（如 "Orders"）作为表名
   - ✅ 必须使用 `actual_table_name` 字段（如 "订单表"）作为表名

4. **可用的语义层工具**:
   - `resolve_business_term(term)` - 解析业务术语
   - `get_semantic_measure(cube, measure)` - 获取度量详情
   - `normalize_status_value(status)` - 规范化状态值
   - `list_available_cubes()` - 列出可用的 Cube
   - `get_cube_measures(cube)` - 获取 Cube 的所有度量

📋 使用示例：

用户: "2023年的销售趋势"
正确流程:
    1. list_tables() → ["订单表", "用户表", "产品表"]
    2. get_schema("订单表") → [订单日期, 金额, 状态...]
    3. resolve_business_term("销售") → {{"cube": "Orders", "actual_table_name": "订单表", "sql": "SUM(total_amount)"}}
    4. 使用: SELECT SUM(total_amount) FROM 订单表 WHERE EXTRACT(YEAR FROM 订单日期) = 2023

用户: "已完成的订单有多少？"
正确流程:
    1. list_tables() → ["订单表", ...]
    2. normalize_status_value("已完成") → {{"normalized": "completed", ...}}
    3. 使用: SELECT COUNT(*) FROM 订单表 WHERE status = 'completed'

🚨 关键提醒：
- resolve_business_term 返回的 `cube` 是语义层名称（如 "Orders"）
- resolve_business_term 返回的 `actual_table_name` 才是实际表名（如 "订单表"）
- 生成 SQL 时必须使用 `actual_table_name`，绝对不能使用 `cube`！
"""

        return guidance

    def after_agent_execution(
        self,
        agent_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """在 LLM 调用后处理结果（可选）

        Args:
            agent_output: Agent 输出

        Returns:
            处理后的 Agent 输出
        """
        # 这里可以添加后处理逻辑
        # 例如：检查 LLM 是否真正调用了语义层工具
        return agent_output

    def get_semantic_context(self, query: str) -> Dict[str, Any]:
        """获取查询的语义上下文

        Args:
            query: 用户查询

        Returns:
            语义上下文字典
        """
        detection_result = self._detect_business_terms(query)

        return {
            "has_business_terms": len(detection_result.detected_terms) > 0,
            "detected_terms": detection_result.detected_terms,
            "confidence": detection_result.confidence,
            "needs_semantic_layer": detection_result.needs_semantic_layer,
            "recommended_tools": self._get_recommended_tools(detection_result)
        }

    def _get_recommended_tools(
        self,
        detection_result: SemanticDetectionResult
    ) -> List[str]:
        """根据检测结果推荐工具

        Args:
            detection_result: 语义检测结果

        Returns:
            推荐的工具列表
        """
        tools = ["resolve_business_term"]

        # 检测到状态值，添加状态规范化工具
        status_keywords = {'完成', '进行中', '取消', '活跃'}
        if any(term in status_keywords or any(kw in term for kw in status_keywords)
               for term in detection_result.detected_terms):
            tools.append("normalize_status_value")

        # 检测到 Cube 相关术语，添加列出 Cube 工具
        if detection_result.confidence > 0.7:
            tools.extend(["list_available_cubes", "get_cube_measures"])

        return tools

    def enhance_system_prompt(self, base_prompt: str, query: str) -> str:
        """增强系统提示词，添加语义层引导

        Args:
            base_prompt: 基础系统提示词
            query: 用户查询

        Returns:
            增强后的系统提示词
        """
        detection_result = self._detect_business_terms(query)

        if not detection_result.needs_semantic_layer:
            return base_prompt

        guidance = self._generate_semantic_guidance(detection_result)

        return f"""{base_prompt}

{guidance}
"""

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """
        包装工具调用以注入语义层引导

        这是 deepagents 中间件接口的要求。

        Args:
            request: The tool call request being processed
            handler: The handler function to call

        Returns:
            The raw ToolMessage, or a Command
        """
        # 在工具调用前可以注入语义层引导（如果有）
        # 目前直接调用处理器，不做额外处理
        # 因为语义层引导主要在 before_agent_execution 中完成
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        """
        包装工具调用以注入语义层引导（异步版本）

        这是 deepagents 中间件接口的异步要求。

        Args:
            request: The tool call request being processed
            handler: The async handler function to call

        Returns:
            The raw ToolMessage, or a Command
        """
        # 在工具调用前可以注入语义层引导（如果有）
        # 目前直接调用处理器，不做额外处理
        # 因为语义层引导主要在 before_agent_execution 中完成
        return await handler(request)

    def wrap_model_call(self, request: ModelRequest, handler) -> Any:
        """
        包装模型调用以注入语义层引导

        这是 deepagents 中间件接口的要求。

        Args:
            request: The model call request being processed
            handler: The handler function to call

        Returns:
            The model call result
        """
        # 在模型调用前可以注入语义层引导（如果有）
        # 目前直接调用处理器，不做额外处理
        # 因为语义层引导主要在 before_agent_execution 中完成
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelCallResult]]
    ) -> ModelCallResult:
        """
        包装模型调用以注入语义层引导（异步版本）

        这是 deepagents 中间件接口的异步要求。

        Args:
            request: The model call request being processed
            handler: The async handler function to call

        Returns:
            The model call result
        """
        # 在模型调用前可以注入语义层引导（如果有）
        # 目前直接调用处理器，不做额外处理
        # 因为语义层引导主要在 before_agent_execution 中完成
        return await handler(request)

    @classmethod
    def create_default(cls) -> 'SemanticPriorityMiddleware':
        """创建默认配置的中间件实例"""
        return cls(
            enable_detection=True,
            min_confidence=0.3,
            enable_logging=True
        )


# ============================================================================
# 辅助函数
# ============================================================================

def detect_semantic_terms(query: str) -> List[str]:
    """快速检测查询中的语义术语

    Args:
        query: 用户查询

    Returns:
        检测到的术语列表
    """
    middleware = SemanticPriorityMiddleware(enable_logging=False)
    result = middleware._detect_business_terms(query)
    return result.detected_terms


def needs_semantic_layer(query: str, threshold: float = 0.3) -> bool:
    """判断查询是否需要使用语义层

    Args:
        query: 用户查询
        threshold: 置信度阈值

    Returns:
        是否需要语义层
    """
    middleware = SemanticPriorityMiddleware(
        min_confidence=threshold,
        enable_logging=False
    )
    result = middleware._detect_business_terms(query)
    return result.needs_semantic_layer


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("语义层优先中间件测试")
    print("=" * 60)

    middleware = SemanticPriorityMiddleware()

    # 测试查询
    test_queries = [
        "订单总收入是多少？",
        "已完成的订单有多少？",
        "分析最近一周的销售趋势",
        "魔都的客户有多少？",
        "列出数据库中的所有表",
    ]

    for query in test_queries:
        print(f"\n[测试] 查询: {query}")

        context = middleware.get_semantic_context(query)
        print(f"  检测到术语: {context['detected_terms']}")
        print(f"  置信度: {context['confidence']:.2f}")
        print(f"  需要语义层: {context['needs_semantic_layer']}")
        print(f"  推荐工具: {context['recommended_tools']}")

        # 测试增强
        enhanced = middleware.before_agent_execution({"query": query})
        if "__semantic_guidance__" in enhanced:
            print(f"  注入引导: {'是' if enhanced['__semantic_guidance__'] else '否'}")
