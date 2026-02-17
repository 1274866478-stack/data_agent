"""
Unit tests for monthly gap filling.
"""
from backend.src.app.services.agent.data_transformer import fill_missing_months


def test_fill_missing_months_adds_zeroes():
    data = [
        {"month": "2024-01", "total_sales": 100.0},
        {"month": "2024-03", "total_sales": 200.0},
    ]
    filled = fill_missing_months(data, "month", "total_sales", "2024年销售趋势")
    assert len(filled) == 12
    assert filled[1]["month"] == "2024-02"
    assert filled[1]["total_sales"] == 0.0


def test_fill_missing_months_skips_daily_data():
    data = [
        {"order_date": "2024-01-02", "total_sales": 10.0},
    ]
    filled = fill_missing_months(data, "order_date", "total_sales", "2024年销售趋势")
    assert filled == data
