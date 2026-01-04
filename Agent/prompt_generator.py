"""
动态系统提示词生成器
根据数据库类型生成特定的系统提示词
"""
from typing import Dict, Any
import sys
from pathlib import Path
import re
import logging

logger = logging.getLogger(__name__)

# 导入数据库规范
backend_path = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

try:
    from app.services.database_spec import get_database_spec
except ImportError:
    # 如果导入失败，提供一个简化版本
    logger.warning("无法导入 database_spec，使用简化版本")
    def get_database_spec(db_type: str):
        return None


def generate_database_aware_system_prompt(db_type: str, base_system_prompt: str = None) -> str:
    """
    生成数据库类型感知的系统提示词

    Args:
        db_type: 数据库类型（如 "postgresql", "mysql", "sqlite", "xlsx"）
        base_system_prompt: 基础系统提示词（可选）

    Returns:
        str: 完整的系统提示词
    """
    try:
        spec = get_database_spec(db_type)
    except Exception as e:
        logger.warning(f"获取数据库规范失败: {e}，使用默认PostgreSQL提示词")
        # 返回原始提示词或PostgreSQL版本
        return base_system_prompt or _get_default_postgresql_prompt()

    # 构建数据库特定说明
    db_specific_instructions = f"""

## 🔴🔴🔴 数据库类型特定说明（必须严格遵守）

**当前数据库类型**: {spec.display_name}
**数据库描述**: {spec.description}

### 📅 日期时间函数（必须使用这些函数）

"""
    for func_desc, func_sql in spec.date_functions.items():
        db_specific_instructions += f"- **{func_desc}**: `{func_sql}`\n"

    db_specific_instructions += "\n### 🔢 聚合函数\n"
    for func_desc, func_sql in spec.aggregation_functions.items():
        db_specific_instructions += f"- **{func_desc}**: `{func_sql}`\n"

    db_specific_instructions += "\n### 📝 字符串函数\n"
    for func_desc, func_sql in spec.string_functions.items():
        db_specific_instructions += f"- **{func_desc}**: `{func_sql}`\n"

    db_specific_instructions += "\n### ⚠️ 语法注意事项\n"
    for i, note in enumerate(spec.syntax_notes, 1):
        db_specific_instructions += f"{i}. {note}\n"

    # 添加函数禁止使用说明
    db_specific_instructions += f"""

### 🚫 禁止使用的函数（此数据库不支持）
"""

    if db_type.lower() in ["mysql"]:
        db_specific_instructions += """- ❌ PostgreSQL 专属函数: TO_CHAR(), DATE_TRUNC()
- ❌ SQLite 专属函数: strftime()
"""
    elif db_type.lower() in ["sqlite", "sqlite3"]:
        db_specific_instructions += """- ❌ PostgreSQL 专属函数: TO_CHAR(), DATE_TRUNC(), EXTRACT()
- ❌ MySQL 专属函数: DATE_FORMAT(), YEAR(), MONTH()
"""
    elif db_type.lower() in ["xlsx", "xls", "csv", "duckdb"]:
        db_specific_instructions += """- ❌ PostgreSQL TO_CHAR()（使用 strftime 或 EXTRACT 替代）
- ❌ MySQL DATE_FORMAT()（使用 strftime 或 EXTRACT 替代）
- ❌ Oracle TO_DATE() → 应使用 TRY_CAST(str AS DATE) 或 str::date
"""
    else:  # PostgreSQL
        db_specific_instructions += """- ❌ MySQL 专属函数: DATE_FORMAT(), YEAR(), MONTH()
- ❌ SQLite 专属函数: strftime()
- ❌ Oracle 专属函数: TO_DATE() → 应使用 TO_CHAR() 或 ::date 类型转换
"""

    db_specific_instructions += f"""

### ✅ 正确示例（针对 {spec.display_name}）

**查询示例：分析2024年的销售额（按月分组）**
```sql
SELECT
    {spec.date_functions.get("年月格式化", "DATE_TRUNC('month', date_column)")} as month,
    {spec.aggregation_functions.get("求和", "SUM(amount)")} as total_sales
FROM orders
WHERE {spec.date_functions.get("年份提取", "EXTRACT(YEAR FROM order_date)")} = 2024
GROUP BY month
ORDER BY month
```

{spec.common_functions_example}
"""

    # 如果提供了基础提示词，在其中插入数据库特定说明
    if base_system_prompt:
        # 使用正则表达式替换原有的数据库类型声明
        prompt = base_system_prompt

        # 替换第一行的数据库助手声明
        prompt = re.sub(
            r"你是一个专业的 PostgreSQL 数据库助手",
            f"你是一个专业的 {spec.display_name} 数据库助手",
            prompt,
            count=1
        )

        # 替换 "这是 PostgreSQL 数据库" 的声明
        prompt = re.sub(
            r"这是 PostgreSQL 数据库，使用 PostgreSQL 语法",
            f"这是 {spec.display_name} 数据库，必须使用 {spec.display_name} 语法",
            prompt
        )

        # 在 "## 可用的 MCP 工具：" 之前插入数据库特定说明
        if "## 可用的 MCP 工具：" in prompt:
            prompt = prompt.replace(
                "## 可用的 MCP 工具：",
                db_specific_instructions + "\n\n## 可用的 MCP 工具："
            )
        else:
            # 如果没有找到这个标记，直接追加到开头
            prompt = db_specific_instructions + "\n\n" + prompt

        return prompt
    else:
        # 如果没有提供基础提示词，使用默认模板
        return _get_default_postgresql_prompt().replace(
            "你是一个专业的 PostgreSQL 数据库助手",
            f"你是一个专业的 {spec.display_name} 数据库助手"
        ).replace(
            "这是 PostgreSQL 数据库，使用 PostgreSQL 语法",
            f"这是 {spec.display_name} 数据库，必须使用 {spec.display_name} 语法"
        )


def _get_default_postgresql_prompt() -> str:
    """获取默认的 PostgreSQL 系统提示词"""
    return """你是一个专业的 PostgreSQL 数据库助手，具备数据查询和图表可视化能力。

## 可用的 MCP 工具：

### 数据库工具（postgres 服务器）：
1. list_tables - 查看数据库中有哪些表（必须先调用！）
2. get_schema - 获取表的结构信息（列名、类型）
3. query - 执行 SQL 查询

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
3. 使用 query 执行 SQL 查询获取数据
4. **如果用户要求可视化**：将查询结果转换为上述格式，调用对应图表工具

## 注意事项：
- 这是 PostgreSQL 数据库，使用 PostgreSQL 语法
- 只生成 SELECT 查询，不执行任何修改操作
- 调用图表工具时，必须将 SQL 结果转换为正确的 data 格式
- 用中文回复用户
"""


def generate_sql_fix_prompt_with_db_type(
    original_sql: str,
    error_message: str,
    schema_context: str,
    original_question: str,
    db_type: str
) -> str:
    """
    生成数据库类型感知的SQL修复提示

    Args:
        original_sql: 原始SQL
        error_message: 错误信息
        schema_context: Schema上下文
        original_question: 用户原始问题
        db_type: 数据库类型

    Returns:
        str: 修复提示词
    """
    try:
        spec = get_database_spec(db_type)
    except Exception as e:
        logger.warning(f"获取数据库规范失败: {e}，使用默认修复提示")
        spec = None

    if spec is None:
        # 回退到原有的修复提示（PostgreSQL版本）
        return _get_default_fix_prompt(original_sql, error_message, schema_context, original_question)

    # 构建数据库特定的修复提示
    prompt = f"""你是一个SQL专家。用户的查询执行失败了，请帮助修复SQL语句。

# 用户原始问题
{original_question}

# 失败的SQL查询
```sql
{original_sql}
```

# 错误信息
{error_message}

# 🔴🔴🔴 当前数据库类型: {spec.display_name}
# 🔴🔴🔴 必须使用 {spec.display_name} 语法！

## 可用的日期时间函数
"""
    for func_desc, func_sql in spec.date_functions.items():
        prompt += f"- {func_desc}: `{func_sql}`\n"

    prompt += f"""
## 🔴🔴🔴 数据库Schema信息（必须使用这里的实际表名和列名）
{schema_context}

## 🔥🔥🔥 修复要求（必须严格遵守）

### 第1步：识别错误
- **主要错误**: {error_message}
- **数据库类型**: {spec.display_name}

### 第2步：使用正确的函数
根据数据库类型，检查并替换不兼容的函数：
"""

    # 添加特定数据库的函数映射指南
    if db_type.lower() in ["mysql"]:
        prompt += """
- ❌ TO_CHAR(date, 'YYYY') → ✅ YEAR(date)
- ❌ TO_CHAR(date, 'YYYY-MM') → ✅ DATE_FORMAT(date, '%Y-%m')
- ❌ DATE_TRUNC('month', date) → ✅ DATE_FORMAT(date, '%Y-%m-01')
- ❌ EXTRACT(YEAR FROM date) → ✅ YEAR(date)
"""
    elif db_type.lower() in ["sqlite", "sqlite3"]:
        prompt += """
- ❌ TO_CHAR(date, 'YYYY') → ✅ CAST(strftime('%Y', date) AS INTEGER)
- ❌ TO_CHAR(date, 'YYYY-MM') → ✅ strftime('%Y-%m', date)
- ❌ DATE_TRUNC('month', date) → ✅ strftime('%Y-%m-01', date)
- ❌ EXTRACT(YEAR FROM date) → ✅ CAST(strftime('%Y', date) AS INTEGER)
"""
    elif db_type.lower() in ["xlsx", "xls", "csv", "duckdb"]:
        prompt += """
- ❌ TO_DATE(str, 'format') → ✅ TRY_CAST(str AS DATE) 或 str::date
- ❌ TO_CHAR(date, 'YYYY') → ✅ EXTRACT(YEAR FROM date) 或 strftime(date, '%Y')
- ❌ DATE_TRUNC 仍然可用，或使用 strftime(date, '%Y-%m-01')
"""
    else:  # PostgreSQL
        prompt += """
- ❌ TO_DATE(str, 'format') → ✅ str::date 或 TO_TIMESTAMP(str, 'YYYY-MM-DD')
- ❌ TO_DATE (不带格式) → ✅ str::date
- PostgreSQL 通常支持大多数标准函数，检查函数名称是否正确
- 确保日期格式字符串正确
"""

    prompt += """
### 第3步：修复SQL
1. 检查所有不兼容的函数
2. 替换为当前数据库支持的函数
3. 确保SQL语法正确
4. 只使用SELECT查询
5. 🔴 极值查询必须使用 LIMIT 1：如果原始问题涉及"最大"、"最小"、"最长"、"最短"等极值，确保SQL使用 ORDER BY + LIMIT 1

### 第4步：返回结果
- **只返回修复后的SQL语句** - 不要包含任何解释或markdown标记
- **如果Schema中没有相关的表或列** - 返回"CANNOT_FIX"
- **不要添加```sql标记** - 直接返回纯SQL语句

---

现在请修复上述失败的SQL查询，直接返回修复后的SQL语句："""

    return prompt


def _get_default_fix_prompt(
    original_sql: str,
    error_message: str,
    schema_context: str,
    original_question: str
) -> str:
    """获取默认的 SQL 修复提示（PostgreSQL 版本）"""
    return f"""你是一个SQL专家。用户的查询执行失败了，请帮助修复SQL语句。

# 用户原始问题
{original_question}

# 失败的SQL查询
```sql
{original_sql}
```

# 错误信息
{error_message}

# PostgreSQL数据库提示
请检查SQL语法和函数使用是否正确

# 🔴🔴🔴 数据库Schema信息（必须使用这里的实际表名和列名）
{schema_context}

# 🔥🔥🔥 修复要求（必须严格遵守）

## 第1步：理解错误
- **主要错误**: {error_message}

## 第2步：查找正确的表名/列名
**🔴 核心问题：SQL中使用了不存在的表名或列名！**

1. **如果错误是"Table does not exist"**：
   - 这通常意味着SQL中使用了错误的表名（可能是用户想象的中文名）
   - 必须从上面的Schema信息中找到实际存在的表名

2. **如果错误是"Column does not exist"**：
   - 查看PostgreSQL的HINT提示
   - 在Schema中找到正确的列名

## 第3步：修复SQL
1. 仔细阅读上面的Schema信息，找到对应的**实际表名和列名**
2. 将SQL中错误的表名/列名替换为Schema中的实际名称
3. 确保SQL语法正确
4. 只使用SELECT查询
5. 🔴 极值查询必须使用 LIMIT 1

## 第4步：返回结果
- **只返回修复后的SQL语句** - 不要包含任何解释或markdown标记
- **如果Schema中没有相关的表或列** - 返回"CANNOT_FIX"
- **不要添加```sql标记** - 直接返回纯SQL语句

现在请修复上述失败的SQL查询，直接返回修复后的SQL语句："""


if __name__ == "__main__":
    # 测试代码
    print("=== 测试 PostgreSQL 提示词 ===")
    pg_prompt = generate_database_aware_system_prompt("postgresql")
    print(pg_prompt[:500])

    print("\n\n=== 测试 MySQL 提示词 ===")
    mysql_prompt = generate_database_aware_system_prompt("mysql")
    print(mysql_prompt[:500])

    print("\n\n=== 测试 SQLite 提示词 ===")
    sqlite_prompt = generate_database_aware_system_prompt("sqlite")
    print(sqlite_prompt[:500])
