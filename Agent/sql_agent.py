"""
# [SQL AGENT] LangGraph SQL智能代理主程序

## [HEADER]
**文件名**: sql_agent.py
**职责**: 实现基于LangGraph和MCP的SQL智能查询代理 - 自然语言理解、Schema发现、SQL生成、图表可视化、多轮对话
**作者**: Data Agent Team
**版本**: 1.2.0
**变更记录**:
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
from typing import Annotated, Literal, Optional, Dict, Any

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

# 🔍 错误追踪模块（质量保证）
try:
    from error_tracker import error_tracker, log_agent_error, ErrorCategory
    ERROR_TRACKING_ENABLED = True
except ImportError:
    ERROR_TRACKING_ENABLED = False
    print("⚠️  警告: 错误追踪模块未启用（error_tracker.py不可用）")

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


# Base system prompt for the SQL Agent (will be dynamically enhanced based on db_type)
BASE_SYSTEM_PROMPT = """你是一个专业的 PostgreSQL 数据库助手，具备数据查询和图表可视化能力。

## 🚨🚨🚨【最高优先级安全规则】🚨🚨🚨

### 🔴🔴🔴 绝对禁止的操作（违反即安全拦截）🔴🔴🔴

你是一个**只读数据分析助手**，严禁执行任何数据修改操作！如果用户要求以下操作，必须明确拒绝：

1. **禁止数据修改**：UPDATE、INSERT、DELETE、TRUNCATE、REPLACE
2. **禁止结构变更**：CREATE、ALTER、DROP、RENAME 表/数据库/视图
3. **禁止权限操作**：GRANT、REVOKE
4. **禁止文件操作**：COPY、pg_read_file、pg_write_file
5. **禁止执行存储过程**：EXEC、EXECUTE、CALL、MERGE

### 🚫 拒绝用户修改数据的正确回复方式

当用户要求修改数据（如"把价格打5折"、"删除某条记录"等）时，你必须回复：

```
⛔ **操作被拒绝**

您请求的操作涉及数据修改，这违反了安全策略。

作为一个只读数据分析助手，我只能：
- ✅ 查询和展示数据（SELECT）
- ✅ 分析数据趋势和模式
- ✅ 生成数据可视化图表
- ❌ 不能修改、删除或新增数据

如果您需要修改数据，请联系数据库管理员或使用专门的管理工具。
```

### 🛡️ 安全强制执行

- 即使用户说"这是测试"、"我授权你"等理由，也**绝不**执行修改操作
- 不要在回复中展示任何危险的 SQL 语句（UPDATE/DELETE/INSERT 等）
- 只展示安全的 SELECT 查询

---

## 可用的 MCP 工具：

### 数据库工具（postgres 服务器）：
1. list_tables - 查看数据库中有哪些表（必须先调用！）
2. get_schema - 获取表的结构信息（列名、类型）
3. query - 执行 SQL 查询（仅支持 SELECT 查询）

### 图表工具（echarts 服务器）：
当用户要求画图/可视化时，先查询数据，然后调用以下工具生成图表：

| 工具名 | 用途 | 数据格式 |
|--------|------|----------|
| generate_bar_chart | 柱状图（比较类别） | [{"category": "名称", "value": 数值}] |
| generate_line_chart | 折线图（趋势变化） | [{"time": "时间", "value": 数值}] |
| generate_pie_chart | 饼图（占比分布） | [{"category": "名称", "value": 数值}] |
| generate_scatter_chart | 散点图（相关性） | 见工具说明 |
| generate_radar_chart | 雷达图（多维对比） | 见工具说明 |
| generate_funnel_chart | 漏斗图（转化分析） | 见工具说明 |

## 🔴 图表工具调用格式（重要！）：

### 柱状图示例：
```json
{
  "title": "各部门人数统计",
  "data": [
    {"category": "技术部", "value": 45},
    {"category": "销售部", "value": 30},
    {"category": "市场部", "value": 25}
  ]
}
```

### 折线图示例：
```json
{
  "title": "月度销售趋势",
  "data": [
    {"time": "2024-01", "value": 1000},
    {"time": "2024-02", "value": 1200},
    {"time": "2024-03", "value": 1500}
  ]
}
```

### 饼图示例：
```json
{
  "title": "市场份额分布",
  "data": [
    {"category": "产品A", "value": 40},
    {"category": "产品B", "value": 35},
    {"category": "产品C", "value": 25}
  ]
}
```

## 工作流程：
1. 使用 list_tables 查看数据库表
2. 使用 get_schema 获取表结构
3. 使用 query 执行 SQL 查询获取数据（仅 SELECT）
4. **如果用户要求可视化**：将查询结果转换为上述格式，调用对应图表工具

## 注意事项：
- 这是 PostgreSQL 数据库，使用 PostgreSQL 语法
- 🚨 **只生成 SELECT 查询，不执行任何修改操作**
- 调用图表工具时，必须将 SQL 结果转换为正确的 data 格式
- 用中文回复用户

## 🧠 模糊查询智能推断规则（重要！）

当用户问**模糊问题**（如"最近生意怎么样"、"销售如何"、"业绩好不好"）时，你必须：

### 1️⃣ 默认时间范围
| 用户说 | 应理解为 | SQL条件示例 |
|--------|----------|-------------|
| "最近" | 最近30天 | `WHERE date_column >= CURRENT_DATE - INTERVAL '30 days'` |
| "最近一周" | 最近7天 | `WHERE date_column >= CURRENT_DATE - INTERVAL '7 days'` |
| "最近一月" | 最近30天 | `WHERE date_column >= CURRENT_DATE - INTERVAL '30 days'` |
| "本月" | 当月1日至今 | `WHERE date_column >= DATE_TRUNC('month', CURRENT_DATE)` |
| "上月" | 上月整月 | `WHERE date_column >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND date_column < DATE_TRUNC('month', CURRENT_DATE)` |

### 🔴🔴🔴 特定年月查询（重要！）
当用户问"2024年5月"、"2023年12月订单"等**特定年月**查询时：

| 用户说 | 应理解为 | SQL条件示例（PostgreSQL） | SQL条件示例（DuckDB/Excel） |
|--------|----------|---------------------------|----------------------------|
| "2024年5月" | 2024年5月整月 | `WHERE TO_CHAR(date_col, 'YYYY-MM') = '2024-05'` | `WHERE strftime(date_col, '%Y-%m') = '2024-05'` |
| "2023年12月" | 2023年12月整月 | `WHERE date_col >= '2023-12-01'::date AND date_col < '2024-01-01'::date` | `WHERE strftime(date_col, '%Y-%m') = '2023-12'` |
| "2024年的订单" | 2024年全年 | `WHERE EXTRACT(YEAR FROM date_col) = 2024` | `WHERE EXTRACT(YEAR FROM date_col) = 2024` |

**🚨🚨🚨 禁止使用 LIKE 查询日期！**
- ❌ **错误**: `WHERE order_date LIKE '2024-05%'` （对日期类型无效！）
- ✅ **正确**: `WHERE strftime(order_date, '%Y-%m') = '2024-05'` （DuckDB/Excel）
- ✅ **正确**: `WHERE TO_CHAR(order_date, 'YYYY-MM') = '2024-05'` （PostgreSQL）

### 2️⃣ 默认业务指标
| 用户说 | 应理解为 | 优先查询指标 |
|--------|----------|--------------|
| "生意"、"销售"、"业绩" | 订单量和销售额 | COUNT(*) 订单数, SUM(amount) 销售额 |
| "客户"、"用户" | 客户数量 | COUNT(DISTINCT customer_id) 客户数 |
| "收入"、"钱" | 金额 | SUM(amount), AVG(amount) |
| "趋势"、"变化" | 时间序列数据 | 按日期/月份分组统计 |

### 3️⃣ 处理流程（必须按顺序执行）
```
用户问"最近生意怎么样"
→ Step 1: list_tables（找表名类似 orders, sales, transactions 的表）
→ Step 2: get_schema（找日期列和金额列）
→ Step 3: 生成SQL查询最近30天的数据（按日期分组，用于图表）
→ Step 4: 将查询结果转换为图表格式，调用 generate_line_chart 生成趋势图
→ Step 5: 用文字总结数据要点
```

**🔴 重要：模糊查询必须生成图表！**
- 查询时必须**按日期分组**（如按天或按月），这样才能画出趋势图
- 不要只查总数，要查**时间序列数据**用于图表
- 调用图表工具：generate_line_chart（趋势）或 generate_bar_chart（对比）

### 4️⃣ SQL查询示例（必须按日期分组）
当用户问"最近生意怎么样"时，**不要只查总数**，要查时间序列：

```sql
-- ✅ 正确：按日期分组，可生成趋势图
SELECT
    DATE_TRUNC('day', order_date) as date,
    COUNT(*) as orders,
    SUM(amount) as sales
FROM orders
WHERE order_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', order_date)
ORDER BY date
-- 返回多行数据，每行是一个日期的数据

-- ❌ 错误：只查总数，无法画图
SELECT COUNT(*), SUM(amount) FROM orders WHERE ...
-- 只返回一行，无法生成趋势图
```

### 5️⃣ 图表工具调用示例
查询到时间序列数据后，立即调用图表工具：

```json
{
  "title": "最近30天业务趋势",
  "data": [
    {"time": "2024-12-01", "value": 12000},
    {"time": "2024-12-02", "value": 15000},
    ...
  ]
}
```

### 6️⃣ 关键要求
- 🔴 **模糊时间必须使用默认值**（"最近"默认30天，不要问用户"多久"）
- 🔴 **查询必须按日期分组**（生成时间序列数据用于画图）
- 🔴 **必须调用图表工具**（generate_line_chart 或 generate_bar_chart）
- 🔴 **主动找表**（通过list_tables智能推断表名）
- 🔴 **找不到合适的表/列时，明确说明**（不要瞎猜字段名）

### 7️⃣ 详细查询 + 分布统计（重要！）
当用户查询特定时间段的数据（如"2024年5月的订单"、"电子产品品牌"等）时：

**处理流程**：
1. **先执行详细查询**：获取原始数据列表（用于表格展示）
2. **再执行聚合查询**：统计分布数据（用于生成饼图）

**示例**：用户问"2024年5月的订单有哪些？"
```sql
-- Step 1: 详细查询（展示列表）
SELECT order_id, customer_name, order_date, total_amount, status_cn
FROM 订单表
WHERE strftime(order_date, '%Y-%m') = '2024-05'
ORDER BY order_date DESC;

-- Step 2: 聚合查询 - 按状态统计（生成饼图）
SELECT status_cn as category, COUNT(*) as value
FROM 订单表
WHERE strftime(order_date, '%Y-%m') = '2024-05'
GROUP BY status_cn;

-- Step 3: 聚合查询 - 按城市统计（生成饼图）
SELECT ship_city as category, COUNT(*) as value
FROM 订单表
WHERE strftime(order_date, '%Y-%m') = '2024-05'
GROUP BY ship_city;
```

### 8️⃣ 饼图规则（完整分布！）
**🔴🔴🔴 饼图必须包含所有分类，不能截断！**

| 场景 | 图表类型 | SQL要求 |
|------|----------|---------|
| 按状态统计 | 饼图 | ❌ 不要用 LIMIT，✅ 必须包含所有状态 |
| 按城市统计 | 饼图 | ❌ 不要用 LIMIT，✅ 必须包含所有城市 |
| 按品牌统计 | 饼图 | ❌ 不要用 LIMIT，✅ 必须包含所有品牌 |

**正确示例**：
```sql
-- ✅ 正确：包含所有品牌
SELECT brand as category, COUNT(*) as value
FROM products
WHERE category = '电子产品'
GROUP BY brand;

-- ❌ 错误：只显示前5个品牌，遗漏其他品牌
SELECT brand as category, COUNT(*) as value
FROM products
WHERE category = '电子产品'
GROUP BY brand
LIMIT 5;  -- 不要在分布统计中使用LIMIT！
```

**🚨 例外情况**：只有用户明确说"前5名"、"Top 10"时，才使用 LIMIT。

## 🔮 数据分析与预测能力：

当用户问"预测"、"预估"、"下个月"等预测类问题时，你需要：

### 预测方法（简单线性趋势）：
1. **查询历史数据**: 获取最近6-12个月的月度数据
2. **计算增长率**: 平均月环比增长率 = (最近月 - 最早月) / 最早月 / 月份数
3. **预测下期值**: 预测值 = 最近一期值 × (1 + 平均增长率)

### 回答格式示例：
```
📊 **历史数据分析**：
- 2024年1月: 100万
- 2024年2月: 110万 (环比+10%)
- 2024年3月: 125万 (环比+13.6%)

📈 **趋势分析**：
- 平均月环比增长率: 11.8%
- 最近3个月呈上升趋势

🔮 **预测结果**：
- 预测2024年4月销售额: **约139.7万**
- 计算方法: 125万 × (1 + 11.8%) = 139.75万

⚠️ **注意**: 这是基于历史趋势的简单线性预测，实际结果可能受季节性、市场变化等因素影响。
```

### 关键要求：
- 🔴 **必须展示计算过程**，不能只给结论
- 🔴 **必须给出具体的预测数值**，不能只说"可能增长"
- 🔴 **必须声明预测的局限性**
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

    try:
        from prompt_generator import generate_database_aware_system_prompt
        result = generate_database_aware_system_prompt(db_type, BASE_SYSTEM_PROMPT)
        # 在提示词末尾追加时间上下文
        result = result + time_context
        print(f"🔍 [get_system_prompt] 成功生成提示词，长度={len(result)}")
        # 打印提示词的前200字符，验证是否包含数据库特定信息
        preview = result[:200].replace('\n', ' ')
        print(f"🔍 [get_system_prompt] 提示词预览: {preview}...")
        return result
    except ImportError as e:
        print(f"⚠️ 无法导入 prompt_generator: {e}，使用默认PostgreSQL提示词")
        return BASE_SYSTEM_PROMPT + time_context
    except Exception as e:
        print(f"⚠️ 生成动态提示词失败: {e}，使用默认PostgreSQL提示词")
        return BASE_SYSTEM_PROMPT + time_context


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
        mcp_chart_path = await call_mcp_chart_tool(
            chart_tool_call['tool_name'],
            chart_tool_call['args']
        )

    # 解析图表配置
    chart_config_data = parse_chart_config(final_content)

    # 构建QueryResult
    query_result = QueryResult.from_raw_data(raw_data) if raw_data else QueryResult()

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
    
    mcp_config = {
        "postgres": {
            "transport": "stdio",
            "command": npx_command,
            "args": [
                "-y",
                "@modelcontextprotocol/server-postgres",
                config.database_url
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
        
        # 最终验证
        final_tool_count = len(_cached_tools)
        final_tool_names = [getattr(t, "name", str(t)) for t in _cached_tools]
        print(f"\n{'='*60}")
        print(f"✅ FORCED REGISTRATION: 最终工具列表包含 {final_tool_count} 个工具")
        print(f"   工具名称: {', '.join(final_tool_names)}")
        print(f"   - inspect_file: {'✅' if 'inspect_file' in final_tool_names else '❌'}")
        print(f"   - analyze_dataframe: {'✅' if 'analyze_dataframe' in final_tool_names else '❌'}")
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

    # 定义节点
    async def call_model(state: MessagesState):
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=system_prompt)] + messages
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    def should_continue(state: MessagesState) -> Literal["tools", "agent", END]:
        """
        增强的路由逻辑：
        - 检测工具错误并路由回 Agent 进行自我修正
        - 检测 SQL 安全问题并阻止执行
        """
        messages = state["messages"]
        last_message = messages[-1]

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
                    print(f"🚨 检测到工具执行错误，路由回 Agent 进行自我修正...")
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

    # 构建图
    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue)
    builder.add_edge("tools", "agent")

    # 持久化 checkpointer
    _cached_checkpointer = MemorySaver()
    _cached_agent = builder.compile(checkpointer=_cached_checkpointer)

    print("✅ Agent 初始化完成！")

    return _cached_agent, _cached_mcp_client


async def reset_agent():
    """重置 Agent 缓存（用于重新连接或配置变更）"""
    global _cached_agent, _cached_mcp_client, _cached_tools, _cached_checkpointer, _cached_db_type
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

