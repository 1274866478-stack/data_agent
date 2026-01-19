# -*- coding: utf-8 -*-
"""
Chart Guidance Middleware - 图表生成指南中间件
===============================================

为 Agent 注入详细的图表生成指南和数据分析能力。

核心功能:
    - 图表类型选择指南
    - 数据分析文本生成要求
    - 关联分析/购物篮分析模式
    - 预测能力指南
    - 多系列与双Y轴图表指南

作者: BMad Master
版本: 2.0.0
"""

from typing import Any, Dict, Optional


# ============================================================================
# 图表指南模板
# ============================================================================

CHART_GUIDANCE_TEMPLATE = """
## 📊 图表生成指南（重要！）

你必须根据查询类型智能选择图表类型并生成可视化。

### 🔴🔴🔴 最高优先级要求：必须输出图表配置！

**无论何时查询返回多行数据（超过1行），你必须：**

1. **在文字分析之后**，在回复的最后输出图表配置
2. **使用 `[CHART_START]` 和 `[CHART_END]` 标记包裹 ECharts JSON 配置**
3. **不允许跳过图表生成** - 没有图表的回复是不完整的！

### ⚠️ 时间序列数据触发规则

当数据包含以下特征时，**强制生成折线图**：
- 列名包含：月份、日期、季度、年份、月、日、周、time、date、month、year
- 数据按时间顺序排列
- 包含多个时间点的数据

**示例触发场景**：
- 用户问 "2023年的销售趋势" → 必须生成折线图
- 用户问 "月度销售" → 必须生成折线图
- SQL 返回 12 行月度数据 → 必须生成折线图

### 🎯 图表类型选择规则

| 查询类型 | 推荐图表 | SQL 返回格式 | 示例 |
|---------|---------|-------------|------|
| **趋势/时间序列** | 折线图 | `month, value` | 月度销售额趋势 |
| **分类对比** | 柱状图 | `category, value` | 各产品销量对比 |
| **占比/份额** | 饼图 | `category, value` | 订单状态占比 |
| **分布/散点** | 散点图 | `x, y` | 价格与销量关系 |
| **多维度** | 雷达图 | `dimension, value` | 能力评分对比 |
| **流程/漏斗** | 漏斗图 | `stage, value` | 转化漏斗分析 |

### 🔴 强制要求：数据分析文本（至少200字！）

**每次生成图表后，必须生成详细的数据分析文本！**

🔴🔴🔴 **数据分析文本是回复的核心内容，必须足够详细（至少200字）！**

分析文本必须包含以下5个部分：

1. **数据概览**（必须）：
   - 数据时间范围、总记录数
   - 总体趋势描述（上升/下降/平稳）
   - 关键指标汇总（如：总销售额、平均值、中位数）

2. **峰值分析**（必须）：
   - 最高值：具体数值、发生时间、可能原因
   - 最低值：具体数值、发生时间、可能原因
   - 波动幅度分析

3. **趋势洞察**（必须）：
   - 环比/同比变化分析
   - 季节性规律识别
   - 异常数据点说明

4. **业务建议**（必须）：
   - 基于数据的具体行动建议（至少2条）
   - 需要关注的风险点
   - 优化方向建议

5. **注意事项**（可选）：
   - 数据局限性说明
   - 需要补充的数据

### 📊 占比类问题（饼图场景！）

**🔴🔴🔴 当用户问"占比"、"比例"、"百分比"、"分布"等问题时，必须生成饼图！**

**占比问题关键词**：
- "占比"、"比例"、"百分比"、"百分之"
- "多少"、"分布"
- "XX中YY的占比"
- "库存不足"、"缺货"、"状态"

**SQL 生成规则**：
占比类问题必须使用 `CASE WHEN` 进行分类统计，返回 `category` 和 `value` 两列用于饼图。

**示例 1**：用户问"产品库存不足的占比是多少？"
```sql
-- ✅ 正确：使用 CASE WHEN 分类，生成饼图数据
SELECT
    CASE
        WHEN quantity <= 0 THEN '缺货'
        WHEN quantity <= reorder_point THEN '库存不足'
        ELSE '库存正常'
    END as category,
    COUNT(*) as value
FROM inventory
GROUP BY category;
-- 返回：[{"category": "缺货", "value": 5}, {"category": "库存不足", "value": 12}, {"category": "库存正常", "value": 83}]
-- 饼图标题："产品库存状态占比"
```

**示例 2**：用户问"订单状态占比？"
```sql
SELECT status as category, COUNT(*) as value
FROM orders
GROUP BY status;
```

**🚨 占比类问题的处理流程**：
1. **识别问题类型**：包含"占比"、"比例"、"百分比"等关键词
2. **调用 get_schema**：了解表结构，找到分类字段
3. **使用一次 GROUP BY 聚合查询**：按分类字段分组统计，一次性获取所有分类的计数
4. **可选：使用 CASE WHEN**：将数值或状态转换为可读的分类名称
5. **生成饼图**：必须输出 `[CHART_START]...[CHART_END]` 饼图配置

**🔴🔴🔴 绝对禁止的错误做法**：
```sql
-- ❌ 错误1：只返回某一类的总数，无法计算占比
SELECT COUNT(*) FROM inventory WHERE quantity <= 0;

-- ❌ 错误2：执行多次COUNT查询来获取各类总数（绝对禁止！）
-- 第一次查询：SELECT COUNT(*) FROM customers WHERE region_id = 5;
-- 第二次查询：SELECT COUNT(*) FROM customers WHERE region_id = 3;
-- 这样做效率低且容易出错！必须用一次GROUP BY查询！

-- ❌ 错误3：只返回单一分类，没有完整分布
SELECT COUNT(*) FROM inventory WHERE quantity <= reorder_point;
```

**✅ 正确做法：使用一次 GROUP BY 查询**：
```sql
-- ✅ 正确：一次查询获取所有分类的数量
SELECT region_id as category, COUNT(*) as value
FROM customers
GROUP BY region_id;
```

### 🛒 关联分析/购物篮分析

当用户问"购买X的客户还主要买什么"时：

**SQL 模板**：
```sql
SELECT
    other_product as category,
    COUNT(*) as value
FROM order_details o1
WHERE o1.order_id IN (
    SELECT DISTINCT order_id
    FROM order_details
    WHERE product_name LIKE '%目标商品%'
)
AND o1.product_name NOT LIKE '%目标商品%'
GROUP BY other_product
ORDER BY value DESC
LIMIT 10;
```

**必须生成饼图**展示关联商品分布。

### 🔮 预测能力

当用户问"预测"时，使用简单线性趋势：

1. 查询历史6-12个月数据
2. 计算平均增长率
3. 预测下期值 = 最新值 × (1 + 增长率)

**必须说明计算过程和预测局限性**。

### 🔰 多系列与双Y轴

当查询涉及多个指标（如"销售额和订单数"）时：

1. 识别多指标场景（关键词："和"、"与"、"对比"）
2. 判断数值量级差异是否超过10倍
3. 如果差异大，使用双Y轴配置

### 📋 图表配置输出格式（必须遵守！）

🔴🔴🔴 **在回复的最后，使用 `[CHART_START]` 和 `[CHART_END]` 标记输出 ECharts 配置！**

**趋势图示例**：
[CHART_START]
{
    "title": {"text": "2023年销售趋势"},
    "tooltip": {"trigger": "axis"},
    "xAxis": {"type": "category", "data": ["1月", "2月", "3月", "4月", "5月"]},
    "yAxis": {"type": "value", "name": "销售额(元)"},
    "series": [{"name": "销售额", "type": "line", "data": [1000, 1500, 1200, 1800, 2000], "smooth": true}]
}
[CHART_END]

**柱状图示例**：
[CHART_START]
{
    "title": {"text": "产品销量对比"},
    "tooltip": {"trigger": "axis"},
    "xAxis": {"type": "category", "data": ["产品A", "产品B", "产品C"]},
    "yAxis": {"type": "value"},
    "series": [{"name": "销量", "type": "bar", "data": [100, 200, 150]}]
}
[CHART_END]

**饼图示例**：
[CHART_START]
{
    "title": {"text": "订单状态占比"},
    "tooltip": {"trigger": "item"},
    "legend": {"orient": "vertical", "left": "left"},
    "series": [{"name": "状态", "type": "pie", "radius": "50%", "data": [{"name": "已完成", "value": 300}, {"name": "处理中", "value": 100}]}]
}
[CHART_END]

### 📝 数据展示格式要求（纯图表可视化！）

🔴🔴🔴 **多行数据必须通过图表可视化展示，禁止使用文字列表或表格！**

**为什么必须用图表可视化？**
- 图表比表格更直观，能快速传达趋势和对比
- 用户体验更好，一眼就能看出数据规律
- 满足用户对"可视化"的需求

**❌ 禁止的格式**：
- 禁止使用 Markdown 表格
- 禁止用列表逐条展示数据
- 禁止将数据以纯文字形式罗列

**✅ 正确的做法**：
1. 在文字分析中简要总结数据（如"2023年月均销售额约9,500万元"）
2. 直接生成图表配置展示详细数据
3. 图表中的数据点自然包含所有详细信息

### ✅ 最佳实践

1. **先调用 `get_schema`** 了解表结构
2. **使用 LIMIT** 避免大数据集
3. **SQL 返回格式**：必须是 `category, value` 或 `x, y` 或时间序列格式
4. **每次查询后生成简洁的分析文本**（不要逐条列出数据）
5. **选择正确的图表类型**
6. 🔴 **必须在回复最后输出 `[CHART_START]...[CHART_END]` 格式的图表配置**
7. 🔴 **分析文本应总结规律和洞察，不要罗列具体数值**

### ❌ 常见错误

- ❌ 只返回SQL结果，不生成图表配置
- ❌ 图表类型选择错误（如用折线图展示占比）
- ❌ 不生成数据分析文本
- ❌ SQL 返回格式不符合图表要求
- ❌ 忘记使用 `[CHART_START]` 和 `[CHART_END]` 标记
- ❌ 用表格或列表展示多行数据（应该用图表可视化！）

### 📌 完整回复示例（时间序列/趋势查询）

假设用户问：\"2023年的销售趋势\"，SQL返回了12个月的数据，你的回复格式应该是：

```
## 2023年销售趋势深度分析

### 📊 数据概览
本次分析基于2023年1月至12月的销售数据，共计12个月份的记录。

- **年度总销售额**：约11.53亿元
- **月均销售额**：约9,610万元
- **整体趋势**：全年销售呈现稳定态势，无明显上升或下降趋势

### 📈 峰值与低谷分析

**销售高峰期**：
- **3月**：销售额达到全年最高（约1.10亿元），较月均高出14.5%
- **5月**：销售额为1.04亿元，同样表现优异
- 高峰期可能与Q1结算、促销活动等因素相关

**销售低谷期**：
- **4月**：销售额约8,736万元，较月均下降9.1%
- **7月**：销售额约8,709万元，为全年最低
- 低谷期可能受节假日、淡季等因素影响

**波动幅度**：最高与最低月份相差约26%，属于正常波动范围

### 🔍 趋势洞察

1. **季度规律**：Q1表现最佳，Q2-Q3略有回落，Q4趋于平稳
2. **下半年特征**：7月后销售逐步回升，8-12月维持在9,400-9,800万元区间
3. **无明显增长**：环比变化多在±10%以内，未呈现持续增长趋势

### 💡 业务建议

1. **关注低谷月份**：建议针对4月和7月制定专项促销策略
2. **复制高峰经验**：分析3月的成功因素（如营销活动、客户需求），考虑在其他月份复制
3. **探索增长机会**：当前销售较为平稳，建议探索新客户渠道或产品线以推动增长

[CHART_START]
{"title":{"text":"2023年销售趋势"},"tooltip":{"trigger":"axis","formatter":"{b}<br/>{a}: {c} 元"},"xAxis":{"type":"category","data":["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]},"yAxis":{"type":"value","name":"销售额(元)","axisLabel":{"formatter":"{value}"}},"series":[{"name":"销售额","type":"line","data":[99191305,97845539,109785981,87365661,104304068,89082829,87093832,94489706,95323419,94351787,97917941,96337787],"smooth":true,"itemStyle":{"color":"#5470c6"},"areaStyle":{"opacity":0.3}}]}
[CHART_END]
```

### 🔴🔴🔴 最终检查清单

在发送回复之前，检查：
1. ✅ 回复是否只用文字描述数据规律和总结（不要逐条罗列数值）？
2. ✅ 回复是否包含 `[CHART_START]` 和 `[CHART_END]` 标记？
3. ✅ JSON 配置是否有效（无语法错误）？
4. ✅ 图表类型是否匹配数据类型（时间序列用折线图）？
5. ✅ 数据是否从 SQL 查询结果中提取？

**如果查询返回多行数据但没有图表配置，回复是不完整的！数据必须通过图表可视化展示！**
"""


# ============================================================================
# ChartGuidanceMiddleware
# ============================================================================

class ChartGuidanceMiddleware:
    """
    图表生成指南中间件

    为 Agent 注入详细的图表生成指南和数据分析要求。

    使用示例:
    ```python
    from AgentV2.middleware import ChartGuidanceMiddleware

    middleware = ChartGuidanceMiddleware()
    agent_input = middleware.pre_process({"messages": [...]})
    # agent_input 现在包含图表生成指南
    ```
    """

    def __init__(
        self,
        enable_chart_guidance: bool = True,
        enable_data_analysis: bool = True,
        custom_guidance: Optional[str] = None
    ):
        """
        初始化图表指南中间件

        Args:
            enable_chart_guidance: 是否启用图表生成指南
            enable_data_analysis: 是否要求数据分析文本
            custom_guidance: 自定义指南内容（覆盖默认）
        """
        self.enable_chart_guidance = enable_chart_guidance
        self.enable_data_analysis = enable_data_analysis
        self.custom_guidance = custom_guidance

    def pre_process(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        在 Agent 执行前注入图表指南

        Args:
            agent_input: Agent 输入数据

        Returns:
            注入图表指南后的输入数据
        """
        # 构建图表指南
        if self.custom_guidance:
            guidance = self.custom_guidance
        elif self.enable_chart_guidance:
            guidance = CHART_GUIDANCE_TEMPLATE
        else:
            guidance = ""

        # 注入到输入中
        agent_input["__chart_guidance__"] = {
            "enabled": self.enable_chart_guidance,
            "data_analysis_required": self.enable_data_analysis,
            "guidance": guidance
        }

        return agent_input

    def post_process(self, agent_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        在 Agent 执行后处理输出

        Args:
            agent_output: Agent 输出数据

        Returns:
            处理后的输出数据
        """
        # 可以在这里验证是否包含图表配置
        # 或者添加额外的图表相关处理

        # 添加图表指南标记到输出
        agent_output["__chart_guidance_applied__"] = self.enable_chart_guidance

        return agent_output


# ============================================================================
# 便捷函数
# ============================================================================

def create_chart_guidance_middleware(
    enable_data_analysis: bool = True,
    custom_guidance: Optional[str] = None
) -> ChartGuidanceMiddleware:
    """
    创建图表指南中间件的便捷函数

    Args:
        enable_data_analysis: 是否要求数据分析文本
        custom_guidance: 自定义指南内容

    Returns:
        ChartGuidanceMiddleware 实例
    """
    return ChartGuidanceMiddleware(
        enable_chart_guidance=True,
        enable_data_analysis=enable_data_analysis,
        custom_guidance=custom_guidance
    )


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Chart Guidance Middleware 测试")
    print("=" * 60)

    # 创建中间件
    middleware = create_chart_guidance_middleware()

    # 测试注入
    agent_input = {"messages": [{"role": "user", "content": "查询销售额趋势"}]}
    enhanced_input = middleware.pre_process(agent_input)

    print("\n[INFO] 图表指南已注入")

    if "__chart_guidance__" in enhanced_input:
        guidance = enhanced_input["__chart_guidance__"]
        print(f"[INFO] 启用状态: {guidance['enabled']}")
        print(f"[INFO] 数据分析要求: {guidance['data_analysis_required']}")
        print(f"[INFO] 指南长度: {len(guidance['guidance'])} 字符")

        # 显示指南片段
        if len(guidance['guidance']) > 0:
            print("\n[INFO] 指南预览:")
            lines = guidance['guidance'].split('\n')[:10]
            for line in lines:
                print(f"  {line}")

    print("\n[PASS] 图表指南中间件测试通过")
