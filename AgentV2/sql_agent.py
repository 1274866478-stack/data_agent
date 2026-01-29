"""
# [SQL AGENT] LangGraph SQL智能代理主程序

## [HEADER]
**文件名**: sql_agent.py
**职责**: 实现基于LangGraph和MCP的SQL智能查询代理 - 自然语言理解、Schema发现、SQL生成、图表可视化、多轮对话
**作者**: Data Agent Team
**版本**: 1.3.0
**变更记录**:
- v1.3.0 (2026-01-27): 企业级可信智能数据体优化 - 集成 planning、reflection、clarification 节点
- v1.2.0 (2026-01-06): 稳定性增强 - 动态时间上下文注入、JSON解析容错处理
- v1.1.0 (2026-01-06): 安全增强 - 集成 SQLValidator 模块，增强 should_continue 错误重试逻辑
- v1.0.1 (2026-01-02): 修复MCP echarts服务器URL配置（本地开发使用localhost）
- v1.0.0 (2026-01-01): 初始版本 - LangGraph SQL Agent实现

## [INPUT]
### 主函数参数
- **run_agent(question, thread_id, verbose)**:
  - question: str - 用户问题（自然语言查询）
  - thread_id: str - 会话ID（默认"1"）
  - verbose: bool - 是否打印详细过程（默认True）

### 配置依赖
- **config** - 从config.py导入（DeepSeek API配置、数据库URL）
- **ENABLE_ECHARTS_MCP** - 是否启用mcp-echarts服务（默认True）

## [OUTPUT]
### 主函数返回值
- **run_agent()**: VisualizationResponse - 结构化的可视化响应
  - answer: str - AI回复内容
  - sql: str - 生成的SQL语句
  - data: QueryResult - 查询结果数据
  - chart: ChartConfig - 图表配置
  - success: bool - 是否成功

### 辅助函数返回值
- **create_llm()**: ChatOpenAI - DeepSeek LLM实例
- **parse_chart_config()**: Optional[Dict[str, Any]] - 解析出的JSON配置
- **extract_tool_data()**: tuple[Optional[str], list] - (SQL语句, 原始数据列表)
- **extract_chart_tool_call()**: Optional[Dict[str, Any]] - 图表工具调用信息
- **call_mcp_chart_tool()**: Optional[str] - 保存的图片路径
- **build_visualization_response()**: VisualizationResponse - 可视化响应对象
- **_generate_chart_file()**: Optional[str] - 生成的图表文件路径
- **_get_or_create_agent()**: tuple[agent, mcp_client] - 编译好的agent和MCP客户端
- **interactive_mode()**: None - 交互模式循环

## [LINK]
**上游依赖** (已读取源码):
- [./config.py](./config.py) - 配置管理（config对象）
- [./models.py](./models.py) - 数据模型（VisualizationResponse, QueryResult, ChartConfig, ChartType）
- [./sql_validator.py](./sql_validator.py) - SQL安全校验（SQLValidator, SQLValidationError）
- [./terminal_viz.py](./terminal_viz.py) - 终端可视化（render_response）
- [./data_transformer.py](./data_transformer.py) - 数据转换（sql_result_to_echarts_data, sql_result_to_mcp_echarts_data）
- [./chart_service.py](./chart_service.py) - 图表服务（ChartRequest, generate_chart_simple, ChartResponse）
- [backend/src/app/services/agent/tools.py](../../backend/src/app/services/agent/tools.py) - 文件数据源工具（inspect_file, analyze_dataframe）

**外部依赖**:
- [langgraph](https://github.com/langchain-ai/langgraph) - LangGraph智能体框架（StateGraph, MessagesState, START, END）
- [langchain-openai](https://github.com/langchain-ai/langchain-openai) - LangChain OpenAI集成（ChatOpenAI）
- [langchain-core](https://github.com/langchain-ai/langchain-core) - LangChain核心（HumanMessage, SystemMessage, AIMessage, ToolMessage）
- [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) - MCP适配器（MultiServerMCPClient）
- [mcp](https://modelcontextprotocol.io/) - Model Context Protocol（ClientSession, sse_client）

**下游依赖** (已读取源码):
- [./run.py](./run.py) - 启动脚本（调用interactive_mode）
- [backend/src/app/api/v1/endpoints/query.py](../../backend/src/app/api/v1/endpoints/query.py) - 查询API端点（调用run_agent）

**调用方**:
- **run.py**: 启动脚本入口（if __name__ == "__main__"）
- **查询API**: 通过API端点调用run_agent函数

## [POS]
**路径**: Agent/sql_agent.py
**模块层级**: Level 1（Agent根目录）
**依赖深度**: 直接依赖 5 层（config.py, models.py, terminal_viz.py, data_transformer.py, chart_service.py）
"""
import asyncio
import json
import re
import sys
import os
from typing import Annotated, Literal, Optional, Dict, Any

# Fix Windows GBK encoding issue
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient

from config import config
from models import VisualizationResponse, QueryResult, ChartConfig, ChartType
from terminal_viz import render_response
from data_transformer import sql_result_to_echarts_data, sql_result_to_mcp_echarts_data
from chart_service import ChartRequest, generate_chart_simple, ChartResponse

# 🔧 新增：企业级可信智能数据体节点
from .nodes import (
    PlanningNode,
    ReflectionNode,
    ClarificationNode,
    create_planning_node,
    create_reflection_node,
    create_clarification_node,
    ErrorCategory
)

# 🔥 导入语义层工具
from .tools import (
    resolve_business_term,
    get_semantic_measure,
    list_available_cubes,
    get_cube_measures,
    normalize_status_value,
)

# 数据一致性验证：防止 LLM 幻觉导致的数据不匹配
try:
    from backend.src.app.services.agent.data_validator import (
        validate_sql_data_consistency,
        smart_field_mapping,
        recommend_chart,
    )
    DATA_VALIDATION_ENABLED = True
except ImportError:
    DATA_VALIDATION_ENABLED = False
    print("⚠️  警告: 数据验证模块未启用（data_validator.py不可用）")

# 🔍 错误追踪模块（质量保证）
try:
    from error_tracker import error_tracker, log_agent_error, ErrorCategory
    ERROR_TRACKING_ENABLED = True
except ImportError:
    ERROR_TRACKING_ENABLED = False
    print("⚠️  警告: 错误追踪模块未启用（error_tracker.py不可用）")

    # 提供回退的 ErrorCategory 定义
    from enum import Enum
    class ErrorCategory(str, Enum):
        DANGEROUS_OPERATION = "dangerous_operation"
        SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
        DATABASE_CONNECTION = "database_connection"
        LLM_API_ERROR = "llm_api_error"
        SCHEMA_NOT_FOUND = "schema_not_found"
        EMPTY_RESULT = "empty_result"
        SQL_SYNTAX_ERROR = "sql_syntax_error"
        UNKNOWN = "unknown"

    # 提供 no-op 的回退函数
    def error_tracker(func):
        return func

    def log_agent_error(error, question, sql="", category=None):
        pass

# 🔥 强制导入文件数据源工具（多种路径尝试）
_inspect_file_tool = None
_analyze_dataframe_tool = None

try:
    import sys
    from pathlib import Path
    
    # 尝试多种导入路径
    import_paths = [
        # 路径1: 从项目根目录导入
        (Path(__file__).parent.parent / "backend" / "src", "app.services.agent.tools"),
        # 路径2: 从 backend 目录导入
        (Path(__file__).parent.parent / "backend" / "src" / "app" / "services" / "agent", "tools"),
        # 路径3: 直接导入（如果已经在路径中）
        (None, "src.app.services.agent.tools"),
    ]
    
    for backend_path, import_module in import_paths:
        try:
            if backend_path and str(backend_path) not in sys.path:
                sys.path.insert(0, str(backend_path))
            
            module = __import__(import_module, fromlist=['inspect_file', 'analyze_dataframe'])
            _inspect_file_tool = getattr(module, 'inspect_file', None)
            _analyze_dataframe_tool = getattr(module, 'analyze_dataframe', None)
            
            if _inspect_file_tool and _analyze_dataframe_tool:
                print(f"[OK] 文件数据源工具导入成功 (路径: {import_module})")
                print(f"   - inspect_file: {getattr(_inspect_file_tool, 'name', 'unknown')}")
                print(f"   - analyze_dataframe: {getattr(_analyze_dataframe_tool, 'name', 'unknown')}")
                break
        except (ImportError, AttributeError) as e:
            continue
    
    if not _inspect_file_tool or not _analyze_dataframe_tool:
        raise ImportError("所有导入路径都失败了")
        
except Exception as e:
    import os
    print(f"[WARNING] 文件数据源工具导入失败: {e}")
    print(f"   当前工作目录: {os.getcwd()}")
    print(f"   脚本路径: {Path(__file__).absolute()}")
    print(f"   Python 路径: {sys.path[:3]}")
    print("   提示: 这些工具可能在某些环境下不可用，但会尝试继续运行")

import base64
import os
from datetime import datetime

# 🔒 导入独立的 SQL 安全校验模块
from sql_validator import SQLValidator, SQLValidationError


# ===============================================
# 🔧 SQL 质量优化器（自动修复常见SQL问题）
# ===============================================

class SQLQualityOptimizer:
    """
    SQL质量优化器 - 自动检测并修复常见的SQL质量问题

    检测和修复的问题：
    1. 重复的 WHERE 条件（如 tenant_id 重复）
    2. 多次 COUNT 查询转换为一次 GROUP BY
    3. 优先使用 address LIKE 而非 region_id
    """

    @staticmethod
    def detect_and_fix_duplicate_conditions(sql: str) -> tuple[str, list[str]]:
        """
        检测并修复重复的WHERE条件

        Returns:
            (修复后的SQL, 发现的问题列表)
        """
        issues = []

        # 检测重复的 tenant_id
        import re
        pattern = r"tenant_id\s*=\s*'([^']+)'"
        matches = re.findall(pattern, sql, re.IGNORECASE)

        # 检查是否有重复（相同值出现多次）
        if len(matches) > len(set(matches)):
            unique_matches = list(dict.fromkeys(matches))  # 保持顺序的去重
            issues.append(f"检测到重复的 WHERE 条件: tenant_id 重复 {len(matches)} 次")

            # 构建修复后的SQL：保留第一个出现，删除重复的
            fixed_sql = sql
            for i, match in enumerate(unique_matches):
                if i == 0:
                    continue  # 保留第一个

            # 使用正则表达式替换重复的tenant_id条件
            # 找到所有 tenant_id = 'xxx' 并替换，只保留第一个
            def replace_duplicates(match_obj):
                value = match_obj.group(1)
                # 如果这个值已经被替换过，就删除这个匹配
                if hasattr(replace_duplicates, 'seen_values'):
                    if value in replace_duplicates.seen_values:
                        return ''  # 删除重复的
                    replace_duplicates.seen_values.add(value)
                    return match_obj.group(0)
                else:
                    replace_duplicates.seen_values = {value}
                    return match_obj.group(0)

            # 从右向左替换（避免索引变化）
            tenant_id_pattern = r"tenant_id\s*=\s*'[^']+'(?:\s+AND\s+)?"
            parts = re.split(tenant_id_pattern, sql, flags=re.IGNORECASE)

            # 更简单的方法：直接重建 WHERE 子句
            where_match = re.search(r'WHERE\s+(.+?)(?:GROUP BY|ORDER BY|LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
            if where_match:
                where_clause = where_match.group(1)

                # 提取所有条件
                conditions = [cond.strip() for cond in re.split(r'\s+AND\s+', where_clause)]

                # 去重（保持顺序）
                seen = set()
                unique_conditions = []
                for cond in conditions:
                    # 检查是否是 tenant_id 条件
                    tenant_match = re.match(r"tenant_id\s*=\s*'([^']+)'", cond, re.IGNORECASE)
                    if tenant_match:
                        value = tenant_match.group(1)
                        if value not in seen:
                            seen.add(value)
                            unique_conditions.append(cond)
                        else:
                            issues.append(f"  - 删除重复条件: {cond}")
                    else:
                        unique_conditions.append(cond)

                # 重建 WHERE 子句
                new_where = ' AND '.join(unique_conditions)
                fixed_sql = re.sub(
                    r'WHERE\s+.+?(GROUP BY|ORDER BY|LIMIT|$)',
                    f'WHERE {new_where} \\1',
                    sql,
                    flags=re.IGNORECASE | re.DOTALL,
                    count=1
                )
            else:
                fixed_sql = sql
        else:
            fixed_sql = sql

        return fixed_sql, issues

    @staticmethod
    def is_proportion_query(question: str) -> bool:
        """检测是否是占比类问题"""
        proportion_keywords = ['占比', '比例', '百分比', '分布', '多少%']
        return any(kw in question for kw in proportion_keywords)

    @staticmethod
    def detect_city_in_question(question: str) -> Optional[str]:
        """从问题中提取城市名"""
        common_cities = [
            '北京', '上海', '广州', '深圳', '杭州', '成都', '重庆',
            '武汉', '西安', '苏州', '南京', '天津', '青岛', '大连',
            '厦门', '长沙', '郑州', '东莞', '佛山', '宁波'
        ]
        for city in common_cities:
            if city in question:
                return city
        return None


# Base system prompt for the SQL Agent (will be dynamically enhanced based on db_type)
BASE_SYSTEM_PROMPT = """你是一个专业的数据库助手，具备数据查询和图表可视化能力。

## 🚨🚨🚨【最高优先级规则】每次生成SQL前必须检查！🚨🚨🚨

### ✅ SQL质量强制检查清单（违反任一条即严重错误！）

```
□ 检查1: tenant_id 是否重复？（数一下，必须≤1次！）
□ 检查2: 是否使用 GROUP BY 一次查询？（禁止多次COUNT！）
□ 检查3: 城市查询是否优先使用 address LIKE？（不是region_id！）
□ 检查4: 表名是否正确？（不是data_source_connections等系统表！）
```

### ❌ 绝对禁止的SQL错误模式

**1. 重复WHERE条件**（最常见！）：
```sql
-- ❌ 错误：重复的相同条件
WHERE region_id = '5' AND region_id = '5'

-- ✅ 正确：每个条件只一次
WHERE region_id = '5'
```

**2. WHERE子句位置错误**（极常见！）：
```sql
-- ❌ 错误：WHERE 在 GROUP BY/ORDER BY 之后
SELECT ... GROUP BY year ORDER BY year WHERE status = 'active'
SELECT ... ORDER BY year AND status = 'active'

-- ✅ 正确：WHERE 必须在 GROUP BY/ORDER BY 之前
SELECT ... WHERE status = 'active' GROUP BY year ORDER BY year
```

**3. 禁止在 SQL 中手动添加 tenant_id**：
```sql
-- ❌ 错误：不要手动添加 tenant_id，系统会自动处理
WHERE tenant_id = 'xxx' AND ...

-- ✅ 正确：系统会自动注入租户过滤条件
WHERE status = 'active'
```

**4. 禁止多次COUNT查询**（占比类问题！）：
```sql
-- ❌ 错误：多次查询
SELECT COUNT(*) FROM users WHERE city = '杭州';
SELECT COUNT(*) FROM users;

-- ✅ 正确：一次GROUP BY查询
SELECT
    CASE WHEN city LIKE '%杭州%' THEN '杭州' ELSE '其他' END as category,
    COUNT(*) as value
FROM users
GROUP BY category;
```

**3. 地址字段优先级**（城市查询！）：
```
优先级: address LIKE '%杭州%' > 独立city字段 > region_id关联
```

**4. 禁止查询系统元数据表**：
```sql
-- ❌ 错误
SELECT * FROM data_source_connections WHERE name = '杭州用户'

-- ✅ 正确：查询业务数据表
SELECT * FROM users WHERE city LIKE '%杭州%'
```

---

## 🛡️ 安全规则（只读模式）

你是一个**只读数据分析助手**，严禁执行任何数据修改操作！

**禁止操作**：UPDATE、INSERT、DELETE、TRUNCATE、CREATE、ALTER、DROP、GRANT、REVOKE

**拒绝回复模板**：
```
⛔ **操作被拒绝**
您请求的操作涉及数据修改，这违反了安全策略。
我只能：✅查询和展示数据、✅分析数据趋势、✅生成图表
❌不能修改、删除或新增数据
```

---

## 🛠️ 可用工具

### 🔧 数据库表查询工具
- ✅ **list_tables** - 必须先调用此工具查看可用表名
- ✅ **get_schema** - 获取表结构信息
- ✅ **query** - 执行SQL查询

### 📋 表查询工作流程（必须遵守）
1. **首先**调用 `list_tables()` 查看所有可用表
2. 使用 `list_tables()` 返回的**确切表名**（可能是中文或英文）
3. 如需了解字段信息，调用 `get_schema(表名)`
4. 最后调用 `query()` 执行查询

### 图表工具
- generate_bar_chart - 柱状图：[{"category": "名称", "value": 数值}]
- generate_line_chart - 折线图：[{"time": "时间", "value": 数值}]
- generate_pie_chart - 饼图：[{"category": "名称", "value": 数值}]
- generate_scatter_chart - 散点图：[{"x": 数值, "y": 数值, "label": "名称"}]
- generate_funnel_chart - 漏斗图：[{"category": "名称", "value": 数值}]

### 双轴图/混合图表
当用户要求"双轴图"、"双Y轴"、"折线+柱状"等混合图表时：
- 请使用 **两个独立的图表工具** 分别生成柱状图和折线图
- 例如：先调用 generate_bar_chart(柱状数据)，再调用 generate_line_chart(折线数据)
- ❌ 不要使用 generate_echarts 工具（它需要复杂的JSON配置）

### 🔥 语义层工具（业务术语解析）

**重要**：在生成 SQL 之前，请先使用语义层工具解析业务术语！

1. **resolve_business_term** - 解析业务术语
   - 用途：将"销售额"、"总收入"、"订单数"等业务术语映射到正确的表和字段
   - 输入：术语名称（如"销售额"）
   - 输出：JSON格式的度量定义（包含表名、字段名、SQL表达式）

2. **list_available_cubes** - 列出可用的语义层Cube
   - 输出：所有可用的Cube列表（如Orders、Customers、Products）

3. **get_semantic_measure** - 获取指定Cube的度量详情
   - 输入：cube名称和度量名称
   - 输出：完整的度量定义

4. **get_cube_measures** - 获取指定Cube的所有度量
   - 输入：cube名称
   - 输出：该Cube的所有度量列表

5. **normalize_status_value** - 规范化状态值
   - 用途：将"已完成"映射为"completed"等标准值
   - 输入：原始状态值
   - 输出：规范化后的状态信息

**语义层使用工作流程**：
```
用户查询 → resolve_business_term(术语) → 获取SQL表达式 → 生成完整SQL
```

**关键提示**：
- 项目中没有独立的 `sales` 表，所有销售数据在 `orders` 表中
- "销售额"对应的字段是 `orders.total_amount`
- 使用语义层工具获取正确的表名和字段名

### 工作流程
1. 理解问题并分析需要的数据
2. 使用语义层工具解析业务术语（如需要）
3. 使用 query 工具执行SQL
4. 调用图表工具生成可视化（如需）

---

## 📊 占比类问题（"XX的占比"）

**处理流程**：
1. 使用一次GROUP BY查询获取所有分类数据
2. 调用generate_pie_chart生成饼图
3. 从结果中计算目标分类的占比

**示例**（"杭州客户的占比"）：
```sql
-- ✅ 正确：一次GROUP BY获取所有城市分布
-- 注意：不要手动添加 tenant_id，系统会自动注入租户过滤条件
SELECT
    CASE
        WHEN address LIKE '%杭州%' THEN '杭州'
        WHEN address LIKE '%北京%' THEN '北京'
        WHEN address LIKE '%上海%' THEN '上海'
        ELSE '其他'
    END as category,
    COUNT(*) as value
FROM customers
GROUP BY category;
```

**回答模板**：
```
📊 [客户城市分布]
总客户200人，各城市分布：
- 上海：50人（25%）
- 杭州：34人（17%）
- 北京：40人（20%）
...
💡 杭州客户占17%，排名第3位
```

---

## 🌍 城市查询规则

**优先级**：address LIKE '%城市%' > city字段 > region_id

**常见城市**：北京、上海、广州、深圳、杭州、成都、重庆、武汉、西安、苏州、南京、天津

**处理流程**：
1. 识别城市关键词
2. 查找城市字段（address、city、ship_city等）
3. 执行GROUP BY获取所有城市分布
4. 从结果中计算目标城市占比

---

## 📈 模糊查询（"最近生意怎么样"）

**默认时间范围**：
- "最近" → 30天
- "最近一周" → 7天
- "本月" → 当月1日至今

**必须按日期分组**（生成时间序列数据）：
```sql
SELECT
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as orders,
    SUM(amount) as sales
FROM orders
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date;
```

**必须生成图表**：调用generate_line_chart或generate_bar_chart

---

## 🔍 图表拆分规则

当用户说"把图分开"、"拆分"、"分别显示"时：
1. 必须调用query工具获取数据
2. 根据用户要求调用对应数量的图表工具
3. 禁止只输出SQL文本而不调用工具！

---

## 📋 SQL生成自查清单

每生成一条SQL必须逐项检查：
```
□ 不要手动添加 tenant_id 条件（系统会自动处理）
□ WHERE 子句必须在 GROUP BY/ORDER BY 之前
□ 表名正确（非系统元数据表）
□ 字段名存在（基于get_schema结果）
□ 占比问题用GROUP BY（不是多次COUNT）
□ 城市查询优先用address LIKE（不是region_id）
```

**🚨 任何检查失败，立即重新生成SQL！**

---

## 🔄 智能表名回退规则（当表不存在时）

**当用户询问的表名不存在时，不要直接放弃！**

**处理流程**：
1. 调用 `list_tables()` 查看所有可用表
2. 根据业务语义找到相关表
3. 使用找到的相关表查询数据

**常见业务术语映射**：
```
用户术语          →  可能的表名
─────────────────────────────────────
销售/销售额/收入    → 订单表、订单明细、月度销售汇总、📊月度销售汇总、orders
客户/用户         → 用户表、客户表、客户消费排行、users、customers
产品/商品         → 产品表、商品表、products
订单             → 订单表、订单明细、orders
库存             → 库存表、商品表、inventory
```

**正确示例**：
```
❌ 错误：表不存在就直接放弃
用户：查询2023年销售趋势
AI：很抱歉，sales表不存在...

✅ 正确：查找相关表并使用
用户：查询2023年销售趋势
AI：
1. 调用 list_tables() → 返回 ["产品表", "订单表", "订单明细", "📊月度销售汇总", ...]
2. 识别相关表：订单表、📊月度销售汇总
3. 执行查询：SELECT * FROM 订单表 WHERE YEAR(订单日期) = 2023
```

---

## 📊 图表生成决策规则（🔴 强制执行）

**⚠️ 执行查询后，必须根据数据特征和用户问题类型判断是否生成图表！**

### 必须生成图表的场景

| 用户问题类型 | 数据特征 | 必须调用的图表工具 |
|-------------|----------|-------------------|
| 趋势/变化/增长 | 含时间/日期字段 | `generate_line_chart` |
| 对比/排名/Top N | 含分类字段 + 数值字段 | `generate_bar_chart` |
| 占比/分布 | 含分组 + 计数/百分比 | `generate_pie_chart` |
| 销售趋势/订单趋势 | 时间 + 数值 | `generate_line_chart` |
| XX的排名/XX排行 | 分组 + 数值排序 | `generate_bar_chart` |
| 每月/每年/每日 | 时间序列 | `generate_line_chart` |

### 判断流程
```
查询返回数据 → 分析数据特征 → 匹配上表场景 → 调用对应图表工具 → 生成文字分析
```

### 示例
```
❌ 错误：只输出文字，不生成图表
用户：查询2023年销售趋势
AI：2023年销售额为XXX...（没有任何图表）

✅ 正确：先调用图表工具，再分析
用户：查询2023年销售趋势
AI：
1. 调用 query() 获取数据
2. 调用 generate_line_chart() 生成趋势图
3. 输出文字分析：📊 2023年销售趋势分析...
```

### 图表数据格式
```json
// 折线图/柱状图
[{"time": "2023-01", "value": 1000}, {"time": "2023-02", "value": 1200}]
// 或 [{"category": "产品A", "value": 100}, {"category": "产品B", "value": 200}]

// 饼图
[{"category": "北京", "value": 30}, {"category": "上海", "value": 50}]
```

---

## 💡 数据分析输出要求（🔴 强制执行，不可跳过）

⚠️ **每次查询后，你必须生成详细的数据分析文本！这不是可选项，是必选项！**

分析内容必须包含以下四个部分：

### 1. 数据概要（必填）
- 查询返回了多少条记录
- 涉及的时间范围（如有）
- 主要的数据维度

### 2. 关键发现（必填）
- 数据中的重要趋势（上升/下降/波动）
- 异常值识别（最高/最低/异常点）
- 数据分布特征

### 3. 数值解读（必填）
- 具体数字的含义（如"销售额增长了20%"）
- 关键指标的计算结果
- 数据之间的关联关系

### 4. 业务洞察（必填）
- 数据对业务的启示
- 建议的下一步行动
- 潜在的风险或机会

**❌ 禁止行为**：
- 只输出SQL或图表，不生成文字分析
- 只说"查询完成"、"已生成图表"等无意义回复
- 跳过上述任何一个分析部分

**✅ 正确示例**：
```
📊 [数据分析结果]

根据查询结果，共找到 15 条订单记录：

🔍 **关键发现**：
• 小米品牌的总销售额为 ¥125,000，占总销售额的 32%
• 平均订单金额为 ¥8,333，最高单笔订单为 ¥15,000（2024-05-15）
• 销售额呈现上升趋势，5月份比4月份增长了 25%

💡 **业务洞察**：
小米品牌表现良好，销售额占比超过三成，是核心品牌之一。建议继续关注该品牌的库存和促销活动，同时分析增长驱动因素以复制成功经验。
```
"""

def get_system_prompt(db_type: str = "postgresql") -> str:
    """
    根据数据库类型获取系统提示词，并注入动态时间上下文

    Args:
        db_type: 数据库类型（postgresql, mysql, sqlite, xlsx, csv等）

    Returns:
        str: 系统提示词（包含当前时间信息）
    """
    print(f"🔍 [get_system_prompt] 调用参数 db_type='{db_type}'")

    # 🕒 动态时间上下文（对于"昨天"、"上月"等时间查询至关重要）
    current_time = datetime.now()
    time_context = f"""

## 🕒 当前时间上下文
- **当前时间**: {current_time.strftime("%Y-%m-%d %H:%M:%S")}
- **当前年份**: {current_time.year}
- **当前月份**: {current_time.month}月
- **当前日期**: {current_time.day}日
- **星期**: 星期{['一', '二', '三', '四', '五', '六', '日'][current_time.weekday()]}

在处理时间相关查询时（如"昨天"、"上周"、"上个月"、"今年"等），请以此时间为准进行计算。
"""

    # 🔥🔥🔥 【关键】数据分析输出强制要求（确保 answer 字段始终有内容）
    data_analysis_output_requirement = """

## 🔴🔴🔴 【强制要求】必须生成数据分析文本！

**⚠️ 调用工具后，必须用文字总结查询结果！**

每次查询后，你必须在文本回复中包含：
1. **数据概要**：查询返回了多少条记录
2. **关键发现**：数据中的重要趋势或异常值
3. **数值解读**：具体数字的含义（如"销售额增长了20%"）
4. **业务洞察**：数据对业务的启示

**正确格式示例**：
```
📊 [数据分析结果]

根据查询结果，共找到 15 条订单记录：

🔍 **关键发现**：
• 小米品牌的总销售额为 ¥125,000，占总销售额的 32%
• 平均订单金额为 ¥8,333
• 最高单笔订单为 ¥15,000（2024-05-15）

💡 **业务洞察**：
小米品牌表现良好，销售额占比超过三成，是核心品牌之一。建议继续关注该品牌的库存和促销活动。
```

**❌ 禁止做法**：
- 只调用工具，不生成文本总结
- 只输出"查询完成"、"已生成图表"等无意义回复
- 只展示SQL语句而不解释结果

**✅ 正确做法**：
- 调用 query 工具获取数据
- 调用图表工具生成可视化（如需要）
- **用文字详细分析数据结果**
"""

    try:
        from prompt_generator import generate_database_aware_system_prompt
        result = generate_database_aware_system_prompt(db_type, BASE_SYSTEM_PROMPT)

        # 🔧 检测是否为测试数据库，注入正确的表结构信息
        if 'ecommerce_test_db' in config.database_url:
            test_db_schema = """

## 🧪 测试数据库表结构（重要！使用以下表名和字段）

**核心业务表**：
1. **users** - 用户表（不是customers！）
   - id: 用户ID
   - username: 用户名
   - vip_level: VIP等级（0=普通, 1=银卡, 2=金卡, 3=钻石）
   - total_spent: 累计消费金额
   - gender: 性别
   - registration_date: 注册时间

2. **orders** - 订单表
   - id: 订单ID
   - user_id: 用户ID（关联users.id，不是customer_id！）
   - total_amount: 订单总金额
   - final_amount: 实付金额
   - status: 订单状态（pending/completed/cancelled）
   - order_date: 订单日期（date类型）
   - created_at: 创建时间

3. **products** - 商品表
   - id: 商品ID
   - name: 商品名称
   - category_id: 类别ID（关联categories.id）
   - brand: 品牌
   - price: 价格
   - sales_count: 销量
   - rating: 平均评分
   - review_count: 评价数

4. **reviews** - 评价表
   - id: 评价ID
   - product_id: 商品ID
   - user_id: 用户ID（关联users.id）
   - rating: 评分（1-5）
   - content: 评价内容
   - created_at: 创建时间

5. **categories** - 商品类别表
   - id: 类别ID
   - name: 类别名称
   - parent_id: 父类别ID

6. **order_items** - 订单明细表
   - order_id: 订单ID
   - product_id: 商品ID
   - quantity: 数量
   - price: 单价
   - subtotal: 小计

7. **addresses** - 地址表
   - user_id: 用户ID（关联users.id）
   - city: 城市
   - province: 省份

## ⚠️⚠️⚠️ 重要：查询用户和订单关联时使用 user_id
- ❌ 错误：customer_id, cid
- ✅ 正确：user_id, u.user_id
- 关联方式：FROM orders o JOIN users u ON o.user_id = u.id

## 📋 用户复购分析专用SQL模板
```sql
-- 统计每个用户的下单次数
SELECT user_id, COUNT(*) as order_count
FROM orders
GROUP BY user_id
ORDER BY order_count DESC;

-- 分析复购用户占比
SELECT
    CASE WHEN order_count >= 2 THEN '复购用户' ELSE '单次购买用户' END as user_type,
    COUNT(*) as user_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM (SELECT user_id, COUNT(*) as order_count FROM orders GROUP BY user_id) sub
GROUP BY user_type;

-- 用户订单数量分布（直方图）
SELECT order_count, COUNT(*) as user_count
FROM (SELECT user_id, COUNT(*) as order_count FROM orders GROUP BY user_id) sub
GROUP BY order_count
ORDER BY order_count;
```
   - user_id: 用户ID
   - city: 城市
   - province: 省份
"""
            result = result + test_db_schema

        # 在提示词末尾追加数据分析输出要求和时间上下文
        result = result + data_analysis_output_requirement + time_context
        print(f"🔍 [get_system_prompt] 成功生成提示词，长度={len(result)}")
        # 打印提示词的前200字符，验证是否包含数据库特定信息
        preview = result[:200].replace('\n', ' ')
        print(f"🔍 [get_system_prompt] 提示词预览: {preview}...")
        return result
    except ImportError as e:
        print(f"⚠️ 无法导入 prompt_generator: {e}，使用默认PostgreSQL提示词")
        return BASE_SYSTEM_PROMPT + data_analysis_output_requirement + time_context
    except Exception as e:
        print(f"⚠️ 生成动态提示词失败: {e}，使用默认PostgreSQL提示词")
        return BASE_SYSTEM_PROMPT + data_analysis_output_requirement + time_context


# 默认提示词（向后兼容）
SYSTEM_PROMPT = BASE_SYSTEM_PROMPT


def create_llm():
    """Create DeepSeek LLM instance using OpenAI-compatible API"""
    return ChatOpenAI(
        model=config.deepseek_model,
        api_key=config.deepseek_api_key,
        base_url=config.deepseek_base_url,
        temperature=0,
    )


def parse_chart_config(content: str) -> Optional[Dict[str, Any]]:
    """从LLM回复中解析JSON图表配置（增强版，支持多种格式和容错）

    Args:
        content: LLM的文本回复

    Returns:
        解析出的JSON配置，如果没有则返回None

    支持的格式:
        1. ```json ... ``` 代码块
        2. ```JSON ... ``` 代码块（大写）
        3. 直接的 JSON 对象 {...}
        4. 带有 JavaScript 注释的 JSON（会尝试清理）
    """
    if not content or not content.strip():
        return None

    # 策略1: 尝试匹配 ```json ... ``` 代码块（不区分大小写）
    json_pattern = r'```(?:json|JSON)\s*([\s\S]*?)\s*```'
    match = re.search(json_pattern, content)

    if match:
        json_str = match.group(1).strip()
        result = _try_parse_json(json_str)
        if result is not None:
            return result

    # 策略2: 尝试匹配任意代码块中的 JSON
    code_block_pattern = r'```\s*([\s\S]*?)\s*```'
    for match in re.finditer(code_block_pattern, content):
        json_str = match.group(1).strip()
        # 检查是否像 JSON（以 { 或 [ 开头）
        if json_str.startswith('{') or json_str.startswith('['):
            result = _try_parse_json(json_str)
            if result is not None:
                return result

    # 策略3: 尝试直接匹配 JSON 对象 {...}
    # 使用贪婪但平衡的匹配（简单版本）
    direct_json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    for match in re.finditer(direct_json_pattern, content):
        json_str = match.group(0)
        result = _try_parse_json(json_str)
        if result is not None:
            # 验证是否是图表配置（至少包含一些预期字段）
            if any(key in result for key in ['chart_type', 'data', 'title', 'type']):
                return result

    return None


def _try_parse_json(json_str: str) -> Optional[Dict[str, Any]]:
    """尝试解析 JSON 字符串，支持容错处理

    Args:
        json_str: JSON 字符串

    Returns:
        解析后的字典，失败返回 None
    """
    if not json_str:
        return None

    # 尝试1: 直接解析
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # 尝试2: 清理常见的 LLM 错误后再解析
    cleaned = json_str

    # 移除 JavaScript 风格的单行注释
    cleaned = re.sub(r'//.*$', '', cleaned, flags=re.MULTILINE)

    # 移除 JavaScript 风格的多行注释
    cleaned = re.sub(r'/\*[\s\S]*?\*/', '', cleaned)

    # 移除尾随逗号（JSON 不允许，但 JS 允许）
    cleaned = re.sub(r',\s*}', '}', cleaned)
    cleaned = re.sub(r',\s*]', ']', cleaned)

    # 将 Python 的 None/True/False 转换为 JSON 的 null/true/false
    cleaned = re.sub(r'\bNone\b', 'null', cleaned)
    cleaned = re.sub(r'\bTrue\b', 'true', cleaned)
    cleaned = re.sub(r'\bFalse\b', 'false', cleaned)

    # 将单引号转换为双引号（JSON 要求双引号）
    # 注意：这个替换比较危险，只在其他方法都失败时使用
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 尝试3: 单引号转双引号（最后手段）
    try:
        # 简单的单引号到双引号转换（不处理嵌套引号）
        cleaned_quotes = cleaned.replace("'", '"')
        return json.loads(cleaned_quotes)
    except json.JSONDecodeError:
        pass

    return None


def extract_tool_data(messages: list) -> tuple[Optional[str], list]:
    """从消息历史中提取工具调用的SQL和返回数据

    Args:
        messages: 消息历史列表

    Returns:
        (sql语句, 原始数据列表)
    """
    sql = None
    raw_data = []

    for msg in messages:
        # 提取SQL（从AIMessage的tool_calls中）
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc.get('name') == 'query':
                    sql = tc.get('args', {}).get('sql')

        # 提取数据（从ToolMessage中）
        if isinstance(msg, ToolMessage):
            try:
                data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                if isinstance(data, list):
                    raw_data = data
            except (json.JSONDecodeError, TypeError):
                pass

    return sql, raw_data


def extract_chart_tool_call(messages: list) -> Optional[Dict[str, Any]]:
    """从消息历史中提取图表工具调用信息

    Args:
        messages: 消息历史列表

    Returns:
        包含工具名和参数的字典，如果没有图表工具调用则返回 None
    """
    chart_tools = [
        "generate_bar_chart", "generate_line_chart", "generate_pie_chart",
        "generate_scatter_chart", "generate_radar_chart", "generate_funnel_chart",
        "generate_echarts"
    ]

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_name = tc.get('name', '')
                if tool_name in chart_tools:
                    return {
                        "tool_name": tool_name,
                        "args": tc.get('args', {})
                    }
    return None


async def call_mcp_chart_tool(tool_name: str, args: Dict[str, Any], output_dir: str = "./charts") -> Optional[str]:
    """使用原始 MCP 客户端调用图表工具（绕过 LangChain 适配器的限制）

    Args:
        tool_name: 工具名称
        args: 工具参数
        output_dir: 输出目录

    Returns:
        保存的图片路径，失败返回 None
    """
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    url = "http://localhost:3033/sse"

    try:
        async with sse_client(url) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()

                result = await session.call_tool(tool_name, args)

                if hasattr(result, 'content') and result.content:
                    for item in result.content:
                        if hasattr(item, 'type') and item.type == 'image':
                            if hasattr(item, 'data') and item.data:
                                # 保存 Base64 图片
                                return _save_base64_image(item.data, output_dir, "png")
                        elif hasattr(item, 'text') and item.text:
                            # 可能是 URL 或其他文本
                            text = item.text
                            if text.startswith("http"):
                                return text

                return None

    except Exception as e:
        print(f"[MCP] Chart tool call failed: {e}")
        return None


def _save_base64_image(base64_data: str, output_dir: str, ext: str = "png") -> str:
    """保存 Base64 编码的图片到文件

    Args:
        base64_data: Base64 编码的图片数据
        output_dir: 输出目录
        ext: 文件扩展名

    Returns:
        保存的文件路径
    """
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mcp_chart_{timestamp}.{ext}"
    filepath = os.path.join(output_dir, filename)

    # 解码并保存
    image_data = base64.b64decode(base64_data)
    with open(filepath, "wb") as f:
        f.write(image_data)

    print(f"📊 图表已保存: {filepath}")
    return filepath


async def _generate_default_answer(query_result: QueryResult, sql: str, chart_config: ChartConfig) -> str:
    """
    生成默认的数据分析文本（当 LLM 没有生成分析时使用）

    Args:
        query_result: 查询结果
        sql: SQL 语句
        chart_config: 图表配置

    Returns:
        str: 默认分析文本
    """
    if query_result.row_count == 0:
        return "📊 [查询结果]\n\n未找到符合条件的数据记录。"

    rows = query_result.rows
    columns = query_result.columns
    row_count = query_result.row_count

    # 构建分析文本
    answer_parts = [
        "📊 [数据分析结果]",
        f"\n根据查询结果，共找到 {row_count} 条记录：\n"
    ]

    # 添加前几条数据预览
    preview_count = min(5, row_count)
    answer_parts.append("🔍 **数据预览**（前{}条）：".format(preview_count))

    for i in range(preview_count):
        row_data = []
        for j, col in enumerate(columns):
            if j < len(rows[i]):
                row_data.append(f"{col}: {rows[i][j]}")
        answer_parts.append(f"• {', '.join(row_data)}")

    if row_count > 5:
        answer_parts.append(f"\n... 还有 {row_count - 5} 条记录")

    # 尝试进行数值分析
    numeric_analysis = _analyze_numeric_data(rows, columns)
    if numeric_analysis:
        answer_parts.append("\n🔍 **数值统计**：")
        answer_parts.append(numeric_analysis)

    # 添加图表说明
    if chart_config and chart_config.title:
        chart_type = chart_config.chart_type.value if hasattr(chart_config.chart_type, 'value') else str(chart_config.chart_type)
        answer_parts.append(f"\n📊 已生成 {chart_type} 图表：{chart_config.title}")

    return "\n".join(answer_parts)


def _analyze_numeric_data(rows: list, columns: list) -> str:
    """
    分析数值数据，生成统计摘要

    Args:
        rows: 数据行
        columns: 列名

    Returns:
        str: 数值分析摘要
    """
    if not rows or not columns:
        return ""

    analysis_parts = []

    # 寻找数值列
    for col_idx, col_name in enumerate(columns):
        if col_idx >= len(rows[0]):
            continue

        # 检查该列是否为数值类型
        is_numeric = True
        numeric_values = []

        for row in rows:
            if col_idx < len(row):
                val = row[col_idx]
                if isinstance(val, (int, float)):
                    numeric_values.append(float(val))
                elif isinstance(val, str) and val.replace('.', '').replace('-', '').replace('+', '').isdigit():
                    try:
                        numeric_values.append(float(val))
                    except ValueError:
                        is_numeric = False
                        break
                else:
                    is_numeric = False
                    break

        if is_numeric and numeric_values:
            # 计算统计信息
            count = len(numeric_values)
            total = sum(numeric_values)
            avg = total / count if count > 0 else 0
            max_val = max(numeric_values)
            min_val = min(numeric_values)

            analysis_parts.append(
                f"• {col_name}: 总计={total:.2f}, 平均={avg:.2f}, 最大={max_val}, 最小={min_val}"
            )

    return "\n".join(analysis_parts) if analysis_parts else ""


async def build_visualization_response(
    messages: list,
    final_content: str,
    auto_generate_chart: bool = True
) -> VisualizationResponse:
    """构建完整的可视化响应，并可选生成图表

    Args:
        messages: 完整的消息历史
        final_content: 最终的AI回复内容
        auto_generate_chart: 是否自动生成图表文件

    Returns:
        VisualizationResponse对象
    """
    # 提取SQL和原始数据
    sql, raw_data = extract_tool_data(messages)

    # 🆕 检查是否有 mcp-echarts 图表工具调用
    chart_tool_call = extract_chart_tool_call(messages)
    mcp_chart_path = None

    # 如果 LLM 调用了图表工具，使用原始 MCP 客户端重新获取图片
    if chart_tool_call and ENABLE_ECHARTS_MCP:
        print(f"[MCP] Detected chart tool call: {chart_tool_call['tool_name']}")
        try:
            mcp_chart_path = await call_mcp_chart_tool(
                chart_tool_call['tool_name'],
                chart_tool_call['args']
            )
        except Exception as e:
            print(f"[MCP] Failed to call chart tool: {e}")

    # 解析图表配置
    chart_config_data = parse_chart_config(final_content)

    # 构建QueryResult
    query_result = QueryResult.from_raw_data(raw_data) if raw_data else QueryResult()

    # ========================================================================
    # 🔥 数据一致性验证：防止 LLM 幻觉导致的数据不匹配问题
    # ========================================================================
    # 验证 LLM 生成的字段是否真实存在于查询结果中
    llm_x_field = chart_config_data.get('x_field') if chart_config_data else None
    llm_y_field = chart_config_data.get('y_field') if chart_config_data else None

    actual_columns = []
    if raw_data and len(raw_data) > 0:
        actual_columns = list(raw_data[0].keys())

    # 检测幻觉字段
    hallucinated_fields = []
    if llm_x_field and llm_x_field not in actual_columns:
        hallucinated_fields.append(f"x_field: {llm_x_field}")
    if llm_y_field and llm_y_field not in actual_columns:
        hallucinated_fields.append(f"y_field: {llm_y_field}")

    if hallucinated_fields:
        print(f"⚠️ [数据验证] 检测到 LLM 幻觉字段: {hallucinated_fields}")
        print(f"   实际字段: {actual_columns}，将使用智能字段映射")
        # 清除幻觉配置，强制使用智能映射
        chart_config_data = None

    # 使用智能字段映射（如果有数据）
    if raw_data and DATA_VALIDATION_ENABLED:
        field_mapping = smart_field_mapping(raw_data, sql)
        chart_rec = recommend_chart(raw_data, sql, final_content[:200] if final_content else "")

        # 覆盖 LLM 提供的字段，使用真实数据映射
        if not chart_config_data:
            chart_config_data = {
                'chart_type': chart_rec.chart_type,
                'chart_title': chart_rec.title,
                'x_field': field_mapping.x_field,
                'y_field': field_mapping.y_field,
            }
            print(f"📊 [智能映射] X={field_mapping.x_field}, Y={field_mapping.y_field}, 类型={chart_rec.chart_type}")
        else:
            # 验证 LLM 配置的字段，如果无效则使用智能映射
            if llm_x_field and llm_x_field not in actual_columns:
                chart_config_data['x_field'] = field_mapping.x_field
            if llm_y_field and llm_y_field not in actual_columns:
                chart_config_data['y_field'] = field_mapping.y_field

    # 构建ChartConfig
    chart_path = mcp_chart_path  # 优先使用 mcp-echarts 的图表

    if chart_config_data:
        chart_type_str = chart_config_data.get('chart_type', 'table')
        try:
            chart_type = ChartType(chart_type_str)
        except ValueError:
            chart_type = ChartType.TABLE

        chart_config = ChartConfig(
            chart_type=chart_type,
            title=chart_config_data.get('chart_title', ''),
            x_field=chart_config_data.get('x_field'),
            y_field=chart_config_data.get('y_field')
        )
        answer = chart_config_data.get('answer', final_content)

        # 如果没有 mcp-echarts 图表，尝试使用本地生成（回退方案）
        if not chart_path and auto_generate_chart:
            should_generate = chart_config_data.get('generate_chart', False)
            if should_generate and raw_data:
                chart_path = _generate_chart_file(
                    raw_data=raw_data,
                    chart_type=chart_type_str,
                    title=chart_config.title,
                    x_field=chart_config.x_field,
                    y_field=chart_config.y_field
                )
    else:
        chart_config = ChartConfig()
        answer = final_content

    # 🔥🔥🔥 【关键修复】确保 answer 字段始终有内容
    # 如果 LLM 没有生成分析文本，基于查询结果生成默认分析
    if not answer or not answer.strip():
        answer = _generate_default_answer(query_result, sql or '', chart_config)
        print("[Agent] LLM未生成分析文本，已生成默认数据分析")

    response = VisualizationResponse(
        answer=answer,
        sql=sql or '',
        data=query_result,
        chart=chart_config,
        success=True
    )

    # 将图表路径添加到响应中（如果生成了）
    if chart_path:
        if chart_path.startswith("http"):
            response.answer = f"{answer}\n\n📊 图表链接: {chart_path}"
        else:
            response.answer = f"{answer}\n\n📊 图表已保存: {chart_path}"

    return response


def _generate_chart_file(
    raw_data: list,
    chart_type: str,
    title: str,
    x_field: Optional[str],
    y_field: Optional[str]
) -> Optional[str]:
    """生成图表文件

    Args:
        raw_data: SQL查询的原始数据
        chart_type: 图表类型
        title: 图表标题
        x_field: X轴字段
        y_field: Y轴字段

    Returns:
        生成的图表文件路径，失败返回None
    """
    # 跳过不需要图表的类型
    if chart_type in ('table', 'none'):
        return None

    try:
        # 转换数据格式
        echarts_data, actual_x, actual_y = sql_result_to_echarts_data(
            raw_data, x_field, y_field
        )

        if not echarts_data:
            return None

        # 创建图表请求
        request = ChartRequest(
            type=chart_type,
            data=echarts_data,
            title=title or "查询结果",
            series_name=actual_y or "数值",
            x_axis_name=actual_x,
            y_axis_name=actual_y
        )

        # 生成图表（使用简化版，生成HTML）
        response: ChartResponse = generate_chart_simple(request, output_dir="./charts")

        if response.success:
            return response.image_path
        else:
            print(f"⚠️ 图表生成失败: {response.error}")
            return None

    except Exception as e:
        print(f"⚠️ 图表生成异常: {e}")
        return None


# MCP client 配置
# 是否启用 mcp-echarts（需要先运行: mcp-echarts -t sse -p 3033）
ENABLE_ECHARTS_MCP = True  # 已启用 mcp-echarts

# ============================================================
# 🚀 性能优化：持久化单例模式
# ============================================================
# 全局缓存，避免每次查询都重新初始化
_cached_agent = None
_cached_mcp_client = None
_cached_tools = None
_cached_checkpointer = None
_cached_db_type = "postgresql"  # 缓存当前数据库类型


def _get_mcp_config():
    """获取 MCP 服务器配置"""
    import shutil
    import sys
    
    # Check if npx is available
    npx_command = "npx.cmd" if sys.platform == "win32" else "npx"
    npx_path = shutil.which(npx_command)
    
    if not npx_path:
        error_msg = (
            f"❌ npx 命令不可用。MCP PostgreSQL 服务器需要 Node.js/npm。\n"
            f"   请安装 Node.js 或设置 DISABLE_MCP_TOOLS=true 使用自定义工具。\n"
            f"   当前平台: {sys.platform}, 查找的命令: {npx_command}"
        )
        print(error_msg)
        raise RuntimeError(
            f"npx command not found. Node.js is required for MCP servers. "
            f"Platform: {sys.platform}, Command: {npx_command}. "
            f"Set DISABLE_MCP_TOOLS=true to use custom tools instead."
        )
    
    print(f"✅ npx 可用: {npx_path}")

    # 确保DATABASE_URL包含SSL参数
    db_url = config.database_url
    if "sslmode" not in db_url.lower():
        if "?" in db_url:
            db_url += "&sslmode=require"
        else:
            db_url += "?sslmode=require"
        print(f"🔒 添加SSL参数到数据库连接")

    mcp_config = {
        "postgres": {
            "transport": "stdio",
            "command": npx_command,
            "args": [
                "-y",
                "@modelcontextprotocol/server-postgres",
                db_url
            ],
        }
    }

    if ENABLE_ECHARTS_MCP:
        # 本地开发使用 localhost，Docker环境使用服务名 mcp_echarts
        mcp_config["echarts"] = {
            "transport": "sse",
            "url": "http://localhost:3033/sse",
            "timeout": 30.0,
            "sse_read_timeout": 120.0,
        }

    return mcp_config


async def _get_or_create_agent(db_type: str = "postgresql"):
    """获取或创建持久化的 Agent 实例（单例模式）

    Args:
        db_type: 数据库类型，用于生成特定的系统提示词

    Returns:
        tuple: (agent, mcp_client) - 编译好的agent和MCP客户端
    """
    global _cached_agent, _cached_mcp_client, _cached_tools, _cached_checkpointer, _cached_db_type

    # 检查数据库类型是否变化，如果变化则重置 Agent
    if _cached_agent is not None and _cached_db_type != db_type:
        print(f"🔄 数据库类型变化: {_cached_db_type} -> {db_type}，重置 Agent...")
        await reset_agent()
        _cached_db_type = db_type

    # 如果已缓存，直接返回
    if _cached_agent is not None and _cached_mcp_client is not None:
        return _cached_agent, _cached_mcp_client

    print(f"🔄 首次初始化 Agent（数据库类型: {db_type}，后续查询将复用连接）...")

    # 创建 MCP 客户端
    try:
        mcp_config = _get_mcp_config()
        _cached_mcp_client = MultiServerMCPClient(mcp_config)
    except RuntimeError as e:
        print(f"❌ MCP 配置失败: {e}")
        print("   提示: 设置 DISABLE_MCP_TOOLS=true 可以禁用 MCP 并使用自定义工具")
        raise
    except Exception as e:
        print(f"❌ MCP 客户端创建失败: {e}")
        raise

    # 获取工具
    try:
        _cached_tools = await _cached_mcp_client.get_tools()
        print(f"✅ MCP 工具加载成功，共 {len(_cached_tools)} 个工具")
        
        # 🔥🔥🔥 强制添加文件数据源工具（硬编码方式，不依赖任何条件）
        tool_names_before = [getattr(t, "name", str(t)) for t in _cached_tools]
        print(f"📋 MCP 工具列表: {', '.join(tool_names_before)}")
        
        # 强制添加 inspect_file
        if _inspect_file_tool:
            tool_name = getattr(_inspect_file_tool, "name", "inspect_file")
            if tool_name not in tool_names_before:
                print(f"➕ [强制添加] inspect_file 工具")
                _cached_tools.append(_inspect_file_tool)
            else:
                print(f"ℹ️ inspect_file 工具已存在于 MCP 工具列表中")
        else:
            print(f"⚠️ inspect_file 工具未导入，无法添加")
        
        # 强制添加 analyze_dataframe
        if _analyze_dataframe_tool:
            tool_name = getattr(_analyze_dataframe_tool, "name", "analyze_dataframe")
            if tool_name not in tool_names_before:
                print(f"➕ [强制添加] analyze_dataframe 工具")
                _cached_tools.append(_analyze_dataframe_tool)
            else:
                print(f"ℹ️ analyze_dataframe 工具已存在于 MCP 工具列表中")
        else:
            print(f"⚠️ analyze_dataframe 工具未导入，无法添加")
        
        # 🔥 添加语义层工具
        from langchain_core.tools import StructuredTool

        semantic_tools = [
            StructuredTool.from_function(
                func=resolve_business_term,
                name="resolve_business_term",
                description="解析业务术语（如'总收入'、'销售额'），返回语义层定义。输入: 术语名称，输出: JSON格式的度量定义",
            ),
            StructuredTool.from_function(
                func=get_semantic_measure,
                name="get_semantic_measure",
                description="获取指定 Cube 的度量详情。输入: cube名称和度量名称，输出: 完整度量定义",
            ),
            StructuredTool.from_function(
                func=list_available_cubes,
                name="list_available_cubes",
                description="列出所有可用的语义层 Cube（如 Orders、Customers、Products）",
            ),
            StructuredTool.from_function(
                func=get_cube_measures,
                name="get_cube_measures",
                description="获取指定 Cube 的所有度量。输入: cube名称，输出: 度量列表",
            ),
            StructuredTool.from_function(
                func=normalize_status_value,
                name="normalize_status_value",
                description="规范化状态值（如'已完成'→'completed'）",
            ),
        ]

        # 将语义层工具添加到工具列表
        _cached_tools.extend(semantic_tools)
        print(f"✅ 已添加 {len(semantic_tools)} 个语义层工具")

        # 最终验证
        final_tool_count = len(_cached_tools)
        final_tool_names = [getattr(t, "name", str(t)) for t in _cached_tools]
        semantic_tool_names = [getattr(t, "name", str(t)) for t in semantic_tools]
        print(f"\n{'='*60}")
        print(f"✅ FORCED REGISTRATION: 最终工具列表包含 {final_tool_count} 个工具")
        print(f"   工具名称: {', '.join(final_tool_names)}")
        print(f"   - inspect_file: {'✅' if 'inspect_file' in final_tool_names else '❌'}")
        print(f"   - analyze_dataframe: {'✅' if 'analyze_dataframe' in final_tool_names else '❌'}")
        print(f"   - 语义层工具: {', '.join(semantic_tool_names)}")
        print(f"{'='*60}\n")

    except FileNotFoundError as e:
        error_message = str(e)
        print(
            f"❌ MCP 工具初始化失败：命令未找到\n"
            f"   错误信息: {error_message}\n"
            f"   可能原因: Node.js/npm 未安装或不在 PATH 中\n"
            f"   解决方案: 安装 Node.js 或设置 DISABLE_MCP_TOOLS=true"
        )
        raise RuntimeError(
            f"MCP initialization failed: command not found. "
            f"Error: {error_message}. "
            f"Install Node.js or set DISABLE_MCP_TOOLS=true"
        ) from e
    except Exception as e:
        print(f"❌ MCP 工具加载失败: {e}")
        raise

    # 创建 LLM
    llm = create_llm()
    llm_with_tools = llm.bind_tools(_cached_tools)

    # 获取数据库特定的系统提示词
    system_prompt = get_system_prompt(db_type)

    # 🔴🔴🔴 图表拆分关键词检测（用于强制工具调用）
    CHART_SPLIT_KEYWORDS = ["分开", "拆分", "分别显示", "单独展示", "单独显示", "各自显示", "拆成"]

    # 🔴🔴🔴 图表合并关键词检测（用于强制工具调用）
    CHART_MERGE_KEYWORDS = ["合并", "合在一起", "放到一起", "合并在一张图", "合并到一起", "合并显示", "组合"]

    # 定义节点
    async def call_model(state: MessagesState):
        messages = state["messages"]

        # 🔧 检测是否是图表拆分或合并请求
        last_human_message = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_human_message = msg.content
                break

        is_split_request = False
        is_merge_request = False
        if last_human_message:
            is_split_request = any(keyword in str(last_human_message) for keyword in CHART_SPLIT_KEYWORDS)
            is_merge_request = any(keyword in str(last_human_message) for keyword in CHART_MERGE_KEYWORDS)

        # 如果是拆分或合并请求，增强系统提示词
        enhanced_system_prompt = system_prompt
        chart_count = None  # 🔴 必须在外层初始化，否则后续代码无法访问
        if is_split_request:
            # 🔴 检测用户是否指定了图表数量
            import re
            if last_human_message:
                # 匹配各种图表数量表达方式
                # 注意：模式顺序很重要，更具体的模式应该在前面
                number_patterns = [
                    # 直接 "拆X个" 或 "拆成X个" 或 "拆分成X个"
                    r'拆(?:分)?(?:成)?([一二三四五六七八九十\d]+)个',
                    # "分成X个"
                    r'分成([一二三四五六七八九十\d]+)个',
                    # "分[别成]X个" - 原有模式保留
                    r'分[别成]([一二三四五六七八九十\d]+)个',
                    # "分别显示X个"
                    r'分别显示([一二三四五六七八九十\d]+)个',
                    # "单独展示X个"
                    r'单独展示([一二三四五六七八九十\d]+)个',
                ]
                for pattern in number_patterns:
                    match = re.search(pattern, str(last_human_message))
                    if match:
                        num_str = match.group(1)
                        # 中文数字转阿拉伯数字
                        cn_nums = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                                  '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
                                  '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
                                  '6': 6, '7': 7, '8': 8, '9': 9, '10': 10}
                        chart_count = cn_nums.get(num_str, int(num_str) if num_str.isdigit() else None)
                        if chart_count:
                            print(f"🔍 [匹配成功] 正则模式: {pattern}, 匹配值: {num_str}, 转换结果: {chart_count}")
                            break

            chart_count_instruction = ""
            if chart_count:
                chart_count_instruction = f"""

🔴🔴🔴 **用户明确要求生成 {chart_count} 个图表！你必须生成正好 {chart_count} 个图表！**

**如何生成 {chart_count} 个图表：**
- 如果有2个指标（如订单数量、销售额），每个指标用2种图表类型（折线图+柱状图）= 4个图表
- 如果有1个指标，用{chart_count}种不同图表类型（折线图、柱状图、饼图、散点图等）
- **关键**：同一个数据可以用不同图表类型展示，这是允许的！
"""
                print(f"🔴📊 [拆分请求] 检测到用户要求 {chart_count} 个图表！原始消息: {last_human_message}")
            else:
                print(f"📊 [拆分请求] 未检测到具体图表数量。原始消息: {last_human_message}")

            enhanced_system_prompt = f"""{system_prompt}

## 🚨🚨🚴【当前请求特殊指令 - 必须执行】🚨🚨🚨

用户刚刚请求将图表拆分（说"{'或 '.join(CHART_SPLIT_KEYWORDS)}"）。{chart_count_instruction}

**你必须执行以下操作，不能只输出文本：**

1. **第1步**：调用 `query` 工具执行SQL查询获取数据
2. **第2步**：根据数据特征和用户要求，调用对应数量的图表工具
   - 时间趋势数据 → generate_line_chart（折线图）
   - 分类对比数据 → generate_bar_chart（柱状图）
   - 占比分布数据 → generate_pie_chart（饼图）
   - 同一数据可以用多种图表类型展示！

**禁止行为**：
- ❌ 只输出SQL语句而不调用 query 工具
- ❌ 只输出JSON配置而不调用图表工具
- ❌ 解释SQL而不执行
- ❌ 生成的图表数量少于用户要求！

**正确响应示例**：
```
用户说：把销售额和订单数拆成四个
你的响应：
1. 调用 query 工具执行 SQL 获取数据
2. 调用 generate_line_chart(销售额趋势)
3. 调用 generate_bar_chart(销售额对比)
4. 调用 generate_line_chart(订单数量趋势)
5. 调用 generate_bar_chart(订单数量对比)
```

现在请执行工具调用，生成用户要求数量的图表！
"""
        elif is_merge_request:
            enhanced_system_prompt = f"""{system_prompt}

## 🚨🚨🚨【当前请求特殊指令 - 图表合并】🚨🚨🚨

用户刚刚请求将图表合并（说"{'或 '.join(CHART_MERGE_KEYWORDS)}"）。

**你必须执行以下操作：**

1. **分析历史对话**：从对话历史中找出之前生成的所有图表配置
2. **提取图表数据**：提取每个图表的 xAxis、yAxis、series 等配置
3. **生成合并图表**：调用 `generate_echarts` 工具生成双Y轴合并图表

**合并规则**：
- 数值量级差异>10倍的分配到不同Y轴
- 金额类指标（销售额、收入）→ 左Y轴（yAxisIndex: 0）
- 数量类指标（订单数、人数）→ 右Y轴（yAxisIndex: 1）
- 使用不同图表类型区分（折线图表示趋势，柱状图表示数量）

**禁止行为**：
- ❌ 只输出文本说明而不生成图表
- ❌ 要求用户手动选择图表
- ❌ 解释如何合并而不实际执行

**正确响应示例**：
```
用户说：把它们合并在一起
你的响应：
1. 从历史中提取之前生成的图表配置
2. 调用 generate_echarts 工具，传入合并后的双Y轴图表配置
```

**输出格式**：必须使用 [CHART_START]...[CHART_END] 格式输出完整的图表配置。

现在请执行工具调用生成合并图表！
"""

        # 🔧 优化上下文窗口：根据请求类型限制历史消息数量
        # 这有助于提高 LLM 对重要信息的关注度，避免被过多历史干扰
        MAX_CONTEXT_MESSAGES = 20  # 默认保留最近20条消息
        if is_merge_request:
            # 合并请求需要更多上下文来查找之前的图表配置
            MAX_CONTEXT_MESSAGES = 30
            print(f"📊 [合并请求] 扩展上下文窗口到 {MAX_CONTEXT_MESSAGES} 条消息")
        elif is_split_request:
            # 拆分请求需要中等上下文
            MAX_CONTEXT_MESSAGES = 15
            print(f"📊 [拆分请求] 设置上下文窗口到 {MAX_CONTEXT_MESSAGES} 条消息")

        # 截断历史消息，保留最近的消息（但保留系统消息）
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]
        other_messages = [m for m in messages if not isinstance(m, SystemMessage)]

        if len(other_messages) > MAX_CONTEXT_MESSAGES:
            print(f"📊 [上下文优化] 原始消息数: {len(other_messages)}, 截断到: {MAX_CONTEXT_MESSAGES}")
            # 🔧 智能截断：保留 AIMessage-ToolMessage 配对关系
            # 从后往前扫描，确保每条 AIMessage 后面有完整的 ToolMessage 响应
            from langchain_core.messages import AIMessage
            selected_messages = []
            tool_call_ids_to_include = set()

            # 首先找到最近的 MAX_CONTEXT_MESSAGES 条消息
            temp_selected = other_messages[-MAX_CONTEXT_MESSAGES:]

            # 从后往前扫描，找出所有需要保留的 tool_call_id
            for msg in reversed(temp_selected):
                selected_messages.insert(0, msg)
                if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # 记录这个 AIMessage 的所有 tool_call_id
                    for tc in msg.tool_calls:
                        tool_call_ids_to_include.add(tc.get('id', ''))

            # 🔥 关键修复：检查 selected_messages 中是否有 ToolMessage 的 tool_call_id
            # 不在 tool_call_ids_to_include 中，如果是的话，这表示截断破坏了配对
            # 需要找到完整的消息组重新构建
            clean_messages = []
            pending_tool_calls = {}  # tool_call_id -> AIMessage

            for msg in selected_messages:
                if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # 记录待匹配的工具调用
                    for tc in msg.tool_calls:
                        pending_tool_calls[tc.get('id', '')] = msg
                    clean_messages.append(msg)
                elif isinstance(msg, ToolMessage):
                    # 检查这个 ToolMessage 是否有对应的 AIMessage
                    if msg.tool_call_id in pending_tool_calls:
                        clean_messages.append(msg)
                        del pending_tool_calls[msg.tool_call_id]
                    # 如果 ToolMessage 的 tool_call_id 不在 pending_tool_calls 中，
                    # 说明它的 AIMessage 被截断了，这个 ToolMessage 也要跳过
                else:
                    clean_messages.append(msg)

            other_messages = clean_messages
            messages = system_messages + other_messages

        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=enhanced_system_prompt)] + messages
            print(f"📝 [系统提示词] 添加新的系统消息")
        elif is_split_request or is_merge_request:
            # 替换已有的系统消息
            old_system_count = len([m for m in messages if isinstance(m, SystemMessage)])
            messages = [SystemMessage(content=enhanced_system_prompt)] + [m for m in messages if not isinstance(m, SystemMessage)]
            print(f"📝 [系统提示词] 替换系统消息 (原有: {old_system_count} 个)")
            # 打印增强提示词的关键部分用于调试
            if chart_count:
                print(f"📝 [增强提示词] 包含图表数量指令: {chart_count} 个图表")
            else:
                print(f"📝 [增强提示词] 包含拆分指令 (无具体数量)")

        # 🔧 标准化消息内容：将 ToolMessage 的 list 格式转换为 string
        # MCP 服务器返回的 ToolMessage.content 可能是 list 格式
        # 但 LLM API 只接受 string 格式
        normalized_messages = []
        for msg in messages:
            if isinstance(msg, ToolMessage) and isinstance(msg.content, list):
                # 提取 list 中的 text 内容
                text_parts = []
                image_count = 0
                for item in msg.content:
                    if isinstance(item, dict):
                        item_type = item.get('type', '')
                        if item_type == 'image':
                            # 图表成功生成，记录但不包含完整 base64 数据
                            image_count += 1
                            text_parts.append(f"[图表已生成: image/{item.get('id', 'unknown')}]")
                        else:
                            text = item.get('text', '')
                            if text:
                                # 截断过长的文本
                                if len(text) > 10000:
                                    text = text[:10000] + "...[内容过长已截断]"
                                text_parts.append(text)
                    elif isinstance(item, str):
                        if len(item) > 10000:
                            item = item[:10000] + "...[内容过长已截断]"
                        text_parts.append(item)
                # 创建新的 ToolMessage，content 为字符串
                from langchain_core.messages import ToolMessage as TM
                normalized_content = '\n'.join(text_parts) if text_parts else f"[工具返回了 {image_count} 个图像]"
                normalized_messages.append(TM(content=normalized_content, tool_call_id=msg.tool_call_id))
            else:
                normalized_messages.append(msg)
        messages = normalized_messages

        response = await llm_with_tools.ainvoke(messages)

        # 🔴 记录工具调用数量
        if response.tool_calls:
            tool_names = [tc.get('name') for tc in response.tool_calls]
            chart_tools = [t for t in tool_names if 'chart' in t.lower()]
            print(f"🔧 [工具调用] 总计: {len(response.tool_calls)} 个, 图表工具: {len(chart_tools)} 个 -> {chart_tools}")
            if is_split_request and chart_count:
                if len(chart_tools) < chart_count:
                    print(f"⚠️ [警告] 用户要求 {chart_count} 个图表，但 LLM 只调用了 {len(chart_tools)} 个图表工具！")
        else:
            print(f"🔧 [工具调用] 本次 LLM 调用没有工具调用")

        # 🔧 如果是拆分请求但LLM没有调用工具，强制提取SQL并创建工具调用
        if is_split_request and not response.tool_calls:
            print("🔴 检测到拆分请求但LLM未调用工具，尝试提取SQL强制执行...")
            content = response.content or ""

            # 尝试提取SQL（使用正则表达式）
            import re
            sql_pattern = r'```sql\s*([\s\S]*?)\s*```'
            sql_matches = re.findall(sql_pattern, str(content))

            if sql_matches:
                extracted_sql = sql_matches[0].strip()
                print(f"✅ 提取到SQL: {extracted_sql[:100]}...")

                # 验证SQL安全性
                is_safe, error_msg = SQLValidator.validate(extracted_sql)
                if not is_safe:
                    print(f"❌ 提取的SQL不安全: {error_msg}")
                    return {"messages": [response]}

                # 创建强制工具调用
                import uuid

                # 🔧 使用 LangChain 标准的工具调用格式
                # 必须包含所有必需字段：name, args, id, type
                forced_tool_call = {
                    "name": "query",
                    "args": {"sql": extracted_sql},
                    "id": str(uuid.uuid4()),
                    "type": "tool_call"  # 🔴 必需字段，用于 LangChain 识别
                }

                # 🔴 创建新的响应，带有工具调用和明确的后续指令
                from langchain_core.messages import AIMessage

                # 🔴🔴🔴 关键修复：在 content 中明确告诉 LLM 在看到查询结果后要做什么
                # 这样当查询结果返回时，LLM 会继续调用图表工具
                forced_instruction = f"""好的，我来执行查询拆分图表。

**【重要】查询执行后，你必须：**

1. 分析查询结果中的数据
2. 根据数据特征，为每个指标调用**单独的图表工具**：
   - 时间趋势数据 → 调用 `generate_line_chart`
   - 分类对比数据 → 调用 `generate_bar_chart`
   - 占比分布数据 → 调用 `generate_pie_chart`

3. **必须调用工具生成图表**，不要只解释数据！

执行SQL：
```sql
{extracted_sql}
```
"""
                enhanced_response = AIMessage(
                    content=forced_instruction,
                    tool_calls=[forced_tool_call]
                )
                print("🔧 已创建强制工具调用，包含明确的后续指令")
                print(f"   工具调用格式: {forced_tool_call}")
                return {"messages": [enhanced_response]}
            else:
                print("⚠️ 未能从响应中提取SQL")

        return {"messages": [response]}

    def should_continue(state: MessagesState) -> Literal["tools", "agent", END]:
        """
        增强的路由逻辑：
        - 检测工具错误并路由回 Agent 进行自我修正
        - 检测 SQL 安全问题并阻止执行
        - 限制修复次数防止无限循环
        - 🔥 修复：强制工具执行后回到 agent 节点生成最终分析答案
        """
        messages = state["messages"]
        last_message = messages[-1]

        # 新增: 检查修复次数，防止无限循环
        tool_message_count = sum(1 for m in messages if isinstance(m, ToolMessage))
        if tool_message_count > 10:  # 增加到10次以支持双轴图等复杂场景
            print(f"⚠️ 达到最大工具调用次数限制 ({tool_message_count})，结束执行")
            return END

        # A. 检查工具执行结果是否出错（ToolMessage 返回错误时路由回 Agent 修复）
        if isinstance(last_message, ToolMessage):
            content_str = str(last_message.content).lower()
            # 常见的 SQL/数据库错误关键词
            error_indicators = [
                "error", "exception", "failed", "invalid",
                "relation does not exist", "column does not exist",
                "syntax error", "permission denied", "does not exist",
                "no such table", "undefined column", "ambiguous column",
                # DuckDB 类型不匹配错误 (如 SUBSTRING 用于 TIMESTAMP 列)
                "no function matches", "argument types", "binder error",
                "cannot be applied to", "type mismatch"
            ]
            for indicator in error_indicators:
                if indicator in content_str:
                    # 新增: 如果已经多次修复仍然出错，直接结束
                    if tool_message_count >= 3:
                        print(f"❌ 修复次数已达上限 ({tool_message_count})，停止尝试")
                        return END
                    print(f"🚨 检测到工具执行错误，路由回 Agent 进行自我修正...")
                    return "agent"

            # 🔥 核心修复：工具执行成功后，强制回到 agent 让 LLM 生成最终分析答案
            # 这解决了"工具调用后只返回原始数据而不生成分析文本"的问题
            if tool_message_count < 5:  # 确保不会无限循环
                print(f"✅ 工具执行完成，路由回 Agent 生成最终分析答案...")
                return "agent"

        # B. 检查 AI 是否要调用工具
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            # 🔒 SQL 安全拦截：在工具执行前校验 SQL（使用独立的 SQLValidator 模块）
            for tc in last_message.tool_calls:
                if tc.get('name') == 'query':
                    sql = tc.get('args', {}).get('sql', '')
                    is_safe, error_msg = SQLValidator.validate(sql)
                    if not is_safe:
                        # 记录被拦截的 SQL（截断以保护日志）
                        sanitized_sql = SQLValidator.sanitize_for_logging(sql, 100)
                        print(f"🛑 SQL 安全拦截: {error_msg}")
                        print(f"   被拦截的 SQL: {sanitized_sql}")
                        # 注意：这里返回 "tools" 让 SafeToolNode 处理，它会返回错误消息给 Agent
                        # 这样 Agent 可以看到错误并尝试修正
            return "tools"

        # 🔥 新增：如果最后一条消息是 AIMessage 但没有有意义的 content，继续生成
        if isinstance(last_message, AIMessage):
            content = last_message.content
            # 检查是否没有 content 或 content 太短（少于20个字符）
            if not content or len(content.strip()) < 20:
                print(f"⚠️ AIMessage 没有有意义的 content (长度: {len(content) if content else 0})，需要继续生成...")
                # 但要避免无限循环，检查前面是否已经有多次尝试
                empty_content_count = sum(
                    1 for m in messages
                    if isinstance(m, AIMessage) and (not m.content or len(m.content.strip()) < 20)
                )
                if empty_content_count < 3:  # 最多允许3次空内容尝试
                    return "agent"
                else:
                    print(f"❌ 空内容尝试次数已达上限 ({empty_content_count})，结束执行")

        return END

    # 🔒 创建带安全校验的工具节点（使用独立的 SQLValidator 模块）
    class SafeToolNode:
        """
        带 SQL 安全校验的工具节点包装器

        当 Agent 尝试执行危险 SQL 时，不会真正执行，
        而是返回一个错误消息，让 Agent 有机会修正并重试。
        """
        def __init__(self, tools):
            self._tool_node = ToolNode(tools)

        async def __call__(self, state: MessagesState):
            messages = state["messages"]
            last_message = messages[-1]

            # 在执行 query 工具前进行安全校验
            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                for tc in last_message.tool_calls:
                    if tc.get('name') == 'query':
                        sql = tc.get('args', {}).get('sql', '')
                        is_safe, error_msg = SQLValidator.validate(sql)
                        if not is_safe:
                            # 返回一个错误消息，而不是执行危险的 SQL
                            # 这让 Agent 知道被拦截了，可以尝试生成安全的查询
                            return {
                                "messages": [
                                    ToolMessage(
                                        content=f"🚫 SQL 执行被安全系统拦截: {error_msg}\n\n"
                                                f"请只生成 SELECT 查询语句，不要尝试修改或删除数据。",
                                        tool_call_id=tc.get('id', 'unknown')
                                    )
                                ]
                            }

            # 安全校验通过，执行原始工具
            return await self._tool_node.ainvoke(state)

    tool_node = SafeToolNode(_cached_tools)

    # 🔧 SQL 质量检查节点（在工具执行后检查并修复SQL）
    async def sql_quality_check_node(state: MessagesState):
        """
        SQL 质量检查节点 - 在工具执行后检查 SQL 质量

        功能：
        1. 检测并修复重复的 WHERE 条件
        2. 记录质量问题供后续分析
        3. 返回修复建议给 Agent
        """
        messages = state["messages"]
        last_message = messages[-1]

        # 只检查 ToolMessage（工具执行结果）
        if not isinstance(last_message, ToolMessage):
            return {"messages": []}

        # 获取原始问题（用于上下文）
        original_question = ""
        for msg in messages:
            if isinstance(msg, HumanMessage):
                original_question = msg.content
                break

        # 检查最近的 query 工具调用
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.get('name') == 'query':
                        original_sql = tc.get('args', {}).get('sql', '')

                        # 执行 SQL 质量检查
                        fixed_sql, issues = SQLQualityOptimizer.detect_and_fix_duplicate_conditions(original_sql)

                        if issues:
                            # 发现问题，返回修复建议
                            issue_summary = "\n".join(issues)
                            suggestion = f"""🔧 SQL 质量检查发现问题：

{issue_summary}

建议修复后的 SQL：
```sql
{fixed_sql}
```

请使用修复后的 SQL 重新查询。"""

                            print(f"🔧 [SQL质量检查] 检测到问题并已修复")
                            for issue in issues:
                                print(f"  - {issue}")

                            # 返回错误消息，让 Agent 看到并修正
                            return {
                                "messages": [
                                    ToolMessage(
                                        content=suggestion,
                                        tool_call_id=tc.get('id', 'unknown')
                                    )
                                ]
                            }

        # 没有发现问题，直接返回
        return {"messages": []}

    # ================================================================
    # 🔧 新增：企业级可信智能数据体节点
    # ================================================================

    # 创建节点实例
    planning_node = create_planning_node(enable_logging=True, min_confidence=0.6)
    reflection_node = create_reflection_node(max_retries=3, enable_logging=True)
    clarification_node = create_clarification_node(confidence_threshold=0.6, enable_logging=True)

    # Planning 节点包装
    async def planning_node_wrapper(state: MessagesState) -> Dict:
        """Planning 节点包装器"""
        return planning_node(state)

    # Reflection 节点包装
    async def reflection_node_wrapper(state: MessagesState) -> Dict:
        """Reflection 节点包装器"""
        return reflection_node(state)

    # Clarification 节点包装
    async def clarification_node_wrapper(state: MessagesState) -> Dict:
        """Clarification 节点包装器"""
        return clarification_node(state)

    # 路由函数：决定是否需要澄清
    def should_clarify(state: MessagesState) -> Literal["clarification", "agent"]:
        """检查是否需要澄清"""
        messages = state["messages"]

        # 检查是否有澄清结果
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and hasattr(msg, 'content'):
                # 检查是否是澄清消息
                if "需要澄清" in str(msg.content) or "🤔" in str(msg.content):
                    return "clarification"

        # 检查是否有执行计划中的低置信度
        if "__execution_plan__" in state:
            plan = state["__execution_plan__"]
            if plan.get("confidence", 1.0) < 0.6:
                return "clarification"

        return "agent"

    # 路由函数：决定是否重试
    def should_retry_after_reflection(state: MessagesState) -> Literal["agent", END]:
        """反思后决定是否重试或继续执行"""
        messages = state["messages"]

        # 首先检查是否已经执行了SQL查询
        has_query_result = False
        has_sql_data = False
        has_chart = False  # 🔧 新增：检查是否已生成图表

        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                content = str(msg.content)
                # 检查是否是SQL查询返回的数据（有列名和行）
                if '"columns"' in content or '"rows"' in content:
                    has_sql_data = True
                    break
                # 🔧 检查是否生成了图表（image类型内容）
                if isinstance(msg.content, list):
                    for item in msg.content:
                        if isinstance(item, dict) and item.get('type') == 'image':
                            has_chart = True
                            break
                elif 'image' in content.lower() or '图表已生成' in content:
                    has_chart = True
                    break
                # 检查是否是query工具的调用
                for earlier_msg in messages:
                    if isinstance(earlier_msg, AIMessage) and earlier_msg.tool_calls:
                        for tc in earlier_msg.tool_calls:
                            if tc.get('name') == 'query':
                                has_query_result = True
                                break

        # 检查反思结果
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                content = str(msg.content)
                # 如果有错误且重试次数未超限
                if "🔄 执行失败" in content and "正在重新生成查询" in content:
                    retry_count = state.get("__retry_count__", 0)
                    if retry_count < 3:
                        return "agent"
                    return END

                if "❌ 检测到错误" in content:
                    retry_count = state.get("__retry_count__", 0)
                    if retry_count < 3:
                        return "agent"
                    return END

                # 如果执行成功但还没有SQL数据，继续执行
                if "✅ 执行成功" in content or "查询已成功执行" in content:
                    # 🔧 检查分析是否完整（至少100字）
                    analysis_length = len(content)
                    if has_chart and analysis_length >= 100:
                        print(f"✅ 已生成图表且分析完整({analysis_length}字)，结束执行")
                        return END
                    elif has_chart:
                        print(f"🔄 已生成图表但分析过短({analysis_length}字)，继续生成分析...")
                        return "agent"
                    if not has_sql_data:
                        print("🔄 工具执行成功，但还没有SQL查询结果，继续执行...")
                        return "agent"
                    # 有SQL数据了，可以结束
                    print("✅ 已获取SQL查询结果，结束执行")
                    return END

        # 如果还没有SQL数据且没有错误，继续执行
        if not has_sql_data:
            # 检查是否有任何query工具调用
            query_called = False
            for msg in messages:
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc.get('name') == 'query':
                            query_called = True
                            break

            if not query_called:
                print("🔄 还没有执行SQL查询，继续执行...")
                return "agent"

        return END

    # 构建图
    builder = StateGraph(MessagesState)

    # 添加节点
    builder.add_node("agent", call_model)
    builder.add_node("tools", tool_node)
    builder.add_node("sql_quality_check", sql_quality_check_node)
    builder.add_node("planning", planning_node_wrapper)    # 🔧 新增：计划节点
    builder.add_node("reflection", reflection_node_wrapper)  # 🔧 新增：反思节点
    builder.add_node("clarification", clarification_node_wrapper)  # 🔧 新增：澄清节点

    # 构建边（新的工作流）
    # START → planning → [needs_clarification?] → clarification → agent → tools → reflection → [should_retry?] → agent/END
    builder.add_edge(START, "planning")
    builder.add_conditional_edges("planning", should_clarify)
    builder.add_edge("clarification", "agent")
    builder.add_conditional_edges("agent", should_continue)
    builder.add_edge("tools", "reflection")  # 🔧 修改：工具执行后进入反思节点
    builder.add_conditional_edges("reflection", should_retry_after_reflection)  # 🔧 新增：反思后路由
    builder.add_edge("sql_quality_check", END)  # 🔧 修改：质量检查后结束（进入reflection处理）

    # 持久化 checkpointer
    _cached_checkpointer = MemorySaver()
    _cached_agent = builder.compile(checkpointer=_cached_checkpointer)

    print("✅ Agent 初始化完成！")
    print("📋 工作流: START → planning → clarification → agent → tools → reflection → agent/END")

    return _cached_agent, _cached_mcp_client


async def reset_agent():
    """重置 Agent 缓存（用于重新连接或配置变更）"""
    global _cached_agent, _cached_mcp_client, _cached_tools, _cached_checkpointer, _cached_db_type

    # 🔥 关闭 MCP 客户端连接
    if _cached_mcp_client is not None:
        try:
            # 尝试关闭 MCP 客户端
            if hasattr(_cached_mcp_client, 'close'):
                await _cached_mcp_client.close()
            elif hasattr(_cached_mcp_client, '__aenter__'):
                # 如果是 async context manager，尝试清理
                await _cached_mcp_client.__aexit__(None, None, None)
            print("🔄 MCP 客户端已关闭")
        except Exception as e:
            print(f"⚠️ 关闭MCP客户端时出错: {e}")

    _cached_agent = None
    _cached_mcp_client = None
    _cached_tools = None
    _cached_checkpointer = None
    _cached_db_type = "postgresql"  # 重置为默认值
    print("🔄 Agent 缓存已重置")


async def run_agent(question: str, thread_id: str = "1", verbose: bool = True, db_type: str = "postgresql") -> VisualizationResponse:
    """Run the SQL Agent with a question

    Args:
        question: 用户问题
        thread_id: 会话ID
        verbose: 是否打印详细过程
        db_type: 数据库类型（postgresql, mysql, sqlite, xlsx, csv等）

    Returns:
        VisualizationResponse: 结构化的可视化响应
    """
    # 🚀 使用持久化的 Agent（传递 db_type 参数）
    agent, mcp_client = await _get_or_create_agent(db_type=db_type)

    # Run the agent
    config_dict = {"configurable": {"thread_id": thread_id}}

    if verbose:
        print(f"\n{'='*60}")
        print(f"问题: {question}")
        print(f"{'='*60}\n")

    step_count = 0
    all_messages = []  # 收集所有消息
    final_content = ""

    # 使用 stream_mode="updates" 只获取增量更新
    async for step in agent.astream(
        {"messages": [HumanMessage(content=question)]},
        config_dict,
        stream_mode="updates",
    ):
        step_count += 1

        if verbose:
            print(f"\n{'─'*60}")
            print(f"� 第 {step_count} 步")
            print(f"{'─'*60}")

        for node_name, node_output in step.items():
            if verbose:
                print(f"\n🔹 节点名称: {node_name}")

            if "messages" in node_output:
                messages = node_output["messages"]
                # 🔧 处理 LangGraph Overwrite 对象和 None 值
                if messages is not None:
                    if hasattr(messages, 'value'):
                        messages = messages.value
                    all_messages.extend(messages)  # 收集消息

                    for msg in messages:
                        if verbose:
                            print(f"  📨 消息类型: {type(msg).__name__}")

                        # 根据消息类型处理
                        if isinstance(msg, AIMessage):
                            if msg.content:
                                final_content = msg.content  # 保存最后的AI回复
                                if verbose:
                                    preview = msg.content[:200] + ('...' if len(msg.content) > 200 else '')
                                    print(f"     🤖 AI: {preview}")
                            if msg.tool_calls and verbose:
                                for tc in msg.tool_calls:
                                    print(f"     🔧 调用工具: {tc['name']}")

                        elif isinstance(msg, ToolMessage) and verbose:
                            preview = str(msg.content)[:200] + ('...' if len(str(msg.content)) > 200 else '')
                            print(f"     📦 工具返回: {preview}")

    # 构建可视化响应（异步，支持 mcp-echarts 图表生成）
    viz_response = await build_visualization_response(all_messages, final_content)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"✅ 完成! 共 {step_count} 步")
        print(f"{'='*60}")
        
        # 打印结构化数据摘要
        print(f"\n📊 结构化数据摘要:")
        print(f"   - SQL: {viz_response.sql[:50]}..." if viz_response.sql else "   - SQL: 无")
        print(f"   - 数据行数: {viz_response.data.row_count}")
        print(f"   - 推荐图表: {viz_response.chart.chart_type.value}")
        print(f"   - 图表标题: {viz_response.chart.title or '无'}")
    
    return viz_response


# ===============================================
# 🔍 带错误追踪的包装函数（质量保证）
# ===============================================

async def run_agent_with_tracking(
    question: str,
    thread_id: str = "1",
    verbose: bool = True,
    db_type: str = "postgresql",
    context: Optional[Dict[str, Any]] = None
) -> VisualizationResponse:
    """
    带错误追踪的run_agent包装函数

    在原有run_agent基础上添加：
    - 性能监控（执行时间）
    - 错误自动记录和分类
    - 成功率统计
    - 失败案例收集

    Args:
        question: 用户问题
        thread_id: 会话ID
        verbose: 是否打印详细过程
        db_type: 数据库类型
        context: 额外上下文信息（用户ID、租户ID等）

    Returns:
        VisualizationResponse: 与run_agent相同的返回值
    """
    import time

    if not ERROR_TRACKING_ENABLED:
        # 如果错误追踪未启用，直接调用原函数
        return await run_agent(question, thread_id, verbose, db_type)

    start_time = time.time()
    response = None

    try:
        # 调用原始run_agent函数
        response = await run_agent(question, thread_id, verbose, db_type)

        # 记录成功
        elapsed = time.time() - start_time
        error_tracker.log_success(
            question=question,
            response=response.answer[:500] if response.answer else "无回复",
            context={
                **(context or {}),
                "thread_id": thread_id,
                "db_type": db_type,
                "sql": response.sql[:200] if response.sql else None,
                "chart_type": response.chart.chart_type.value if response.chart else None,
            },
            execution_time=elapsed
        )

        return response

    except Exception as e:
        # 记录错误
        elapsed = time.time() - start_time

        # 自动推断错误类别
        error_category = _categorize_error(e, question)

        log_agent_error(
            question=question,
            error=e,
            category=error_category,
            context={
                **(context or {}),
                "thread_id": thread_id,
                "db_type": db_type,
                "execution_time": elapsed,
            }
        )

        # 重新抛出异常（保持原有行为）
        raise


def _categorize_error(error: Exception, question: str) -> ErrorCategory:
    """
    根据错误类型和用户问题自动分类错误

    Args:
        error: 异常对象
        question: 用户问题

    Returns:
        ErrorCategory: 错误类别
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    # 危险操作检测
    dangerous_keywords = ["drop", "delete", "update", "insert", "truncate", "alter"]
    if any(kw in question.lower() for kw in dangerous_keywords):
        return ErrorCategory.DANGEROUS_OPERATION

    # SQL注入尝试
    if "injection" in error_str or "malicious" in error_str:
        return ErrorCategory.SQL_INJECTION_ATTEMPT

    # 数据库连接问题
    if "connection" in error_str or "connect" in error_str or "timeout" in error_str:
        return ErrorCategory.DATABASE_CONNECTION

    # LLM API错误
    if "api" in error_str or "openai" in error_str or "deepseek" in error_str:
        return ErrorCategory.LLM_API_ERROR

    # Schema不存在
    if "not found" in error_str or "does not exist" in error_str or "unknown" in error_str:
        return ErrorCategory.SCHEMA_NOT_FOUND

    # 空结果
    if "empty" in error_str or "no data" in error_str or "no result" in error_str:
        return ErrorCategory.EMPTY_RESULT

    # 数据类型不匹配
    if error_type in ["ValueError", "TypeError"] or "type" in error_str:
        return ErrorCategory.DATA_TYPE_MISMATCH

    # MCP工具失败
    if "mcp" in error_str or "tool" in error_str:
        return ErrorCategory.MCP_TOOL_FAILURE

    # 模糊问题
    if len(question.strip()) < 5:
        return ErrorCategory.AMBIGUOUS_QUERY

    # 默认为未知错误
    return ErrorCategory.UNKNOWN


async def interactive_mode():
    """Run the agent in interactive mode"""
    print("\n" + "="*60)
    print("🤖 SQL Agent 交互模式（可视化版）")
    print("="*60)
    print("命令:")
    print("  exit/quit - 退出程序")
    print("  debug     - 切换调试模式")
    print("  reset     - 重置连接（如遇连接问题）")
    print("="*60)
    print("\n💡 提示: 首次查询需要初始化连接（约5-10秒），后续查询将很快！\n")

    thread_id = "interactive_session"
    verbose = False  # 默认关闭详细输出，只显示漂亮的可视化结果

    while True:
        try:
            question = input("\n📝 请输入你的问题: ").strip()

            if question.lower() in ["exit", "quit", "q"]:
                print("\n👋 再见!")
                break

            if question.lower() == "debug":
                verbose = not verbose
                print(f"\n🔧 调试模式: {'开启' if verbose else '关闭'}")
                continue

            if question.lower() == "reset":
                await reset_agent()
                continue

            if not question:
                continue

            # 计时
            import time
            start_time = time.time()

            # 运行Agent并获取结构化响应
            viz_response = await run_agent(question, thread_id, verbose=verbose)

            # 计算耗时
            elapsed = time.time() - start_time

            # 使用漂亮的可视化渲染
            if not verbose:  # 非调试模式下显示漂亮输出
                render_response(viz_response)

            print(f"\n⏱️  响应时间: {elapsed:.2f} 秒")

        except KeyboardInterrupt:
            print("\n\n👋 再见!")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            print("💡 提示: 输入 'reset' 可重置连接")


if __name__ == "__main__":
    # Validate configuration
    config.validate_config()

    # Run interactive mode
    asyncio.run(interactive_mode())

