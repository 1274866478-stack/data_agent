from src.app.api.v2.endpoints.query_stream_v2 import sanitize_table_numbers


def test_sanitize_rounds_long_float():
    table = {
        "columns": ["value"],
        "rows": [[2968.3900000000003], {"value": "1.9999"}],
        "row_count": 2,
    }
    sanitized = sanitize_table_numbers(table)
    assert sanitized["rows"][0][0] == 2968.39
    assert sanitized["rows"][1]["value"] == 2


def test_sanitize_keeps_strings():
    table = {
        "columns": ["name", "val"],
        "rows": [{"name": "NY", "val": "abc"}],
        "row_count": 1,
    }
    sanitized = sanitize_table_numbers(table)
    assert sanitized["rows"][0]["name"] == "NY"
    assert sanitized["rows"][0]["val"] == "abc"
