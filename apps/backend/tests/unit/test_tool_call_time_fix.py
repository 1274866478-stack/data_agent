"""
Tests for tool_call normalization + time aggregation fix.
"""
import json

from backend.src.app.services.agent.agent_service import (
    apply_time_aggregation_fix_to_tool_calls,
)


def test_function_style_tool_call_is_corrected_to_monthly_grouping():
    # OpenAI function-call style payload
    sql = (
        "SELECT order_date, SUM(total_amount) AS total_sales "
        "FROM orders "
        "GROUP BY order_date "
        "ORDER BY order_date"
    )
    tool_calls = [
        {
            "function": {
                "name": "execute_query",
                "arguments": json.dumps({"query": sql}),
            }
        }
    ]

    fixed = apply_time_aggregation_fix_to_tool_calls(
        tool_calls,
        question="2024年销售趋势",
        database_url="/app/uploads/foo.xlsx",  # 推断 duckdb/xlsx
    )

    updated_args = json.loads(fixed[0]["function"]["arguments"])
    corrected_sql = updated_args["query"]

    assert "strftime" in corrected_sql or "DATE_TRUNC('month'" in corrected_sql
    assert "GROUP BY" in corrected_sql
    # 确保 order_date 已被替换为月级表达式
    assert "order_date" not in corrected_sql.split("GROUP BY")[1].split("ORDER BY")[0]
