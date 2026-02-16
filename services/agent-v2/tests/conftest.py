"""
Pytest配置文件 - 共享的测试固件和配置
"""
import pytest
import asyncio
import os
from typing import Dict, List
from pathlib import Path


# ===== Pytest配置 =====

def pytest_configure(config):
    """Pytest全局配置"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "e2e: 端到端测试")
    config.addinivalue_line("markers", "slow: 慢速测试")


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ===== 测试数据固件 =====

@pytest.fixture
def sample_schema() -> Dict:
    """示例数据库Schema"""
    return {
        "users": {
            "columns": ["id", "name", "email", "created_at", "status"],
            "types": ["integer", "varchar", "varchar", "timestamp", "varchar"]
        },
        "orders": {
            "columns": ["id", "user_id", "amount", "order_date", "status"],
            "types": ["integer", "integer", "decimal", "timestamp", "varchar"]
        },
        "products": {
            "columns": ["id", "name", "price", "category", "stock"],
            "types": ["integer", "varchar", "decimal", "varchar", "integer"]
        }
    }


@pytest.fixture
def sample_query_results() -> List[Dict]:
    """示例查询结果"""
    return [
        {"month": "2024-01", "order_count": 100, "revenue": 10000.50},
        {"month": "2024-02", "order_count": 150, "revenue": 15500.75},
        {"month": "2024-03", "order_count": 120, "revenue": 12300.00}
    ]


@pytest.fixture
def golden_test_cases() -> List[Dict]:
    """黄金测试用例集"""
    return [
        # 基础查询
        {
            "id": "A01",
            "category": "data_exploration",
            "question": "数据库里有哪些表？",
            "expected_tools": ["list_tables"],
            "expected_keywords": ["users", "orders", "products"]
        },
        {
            "id": "A02",
            "category": "data_exploration",
            "question": "用户表有哪些字段？",
            "expected_tools": ["get_schema"],
            "expected_keywords": ["id", "name", "email"]
        },

        # 数据分析
        {
            "id": "B01",
            "category": "data_analysis",
            "question": "统计每个用户的订单数量",
            "expected_sql_patterns": ["GROUP BY", "COUNT", "users", "orders"],
            "expected_tools": ["query"]
        },
        {
            "id": "B02",
            "category": "data_analysis",
            "question": "找出销售额最高的前10个商品",
            "expected_sql_patterns": ["ORDER BY", "LIMIT", "DESC"],
            "expected_tools": ["query"]
        },

        # 可视化
        {
            "id": "C01",
            "category": "visualization",
            "question": "画出每月订单趋势图",
            "expected_tools": ["query", "generate_line_chart"],
            "expected_chart_type": "line"
        },
        {
            "id": "C02",
            "category": "visualization",
            "question": "用饼图展示产品类别分布",
            "expected_tools": ["query", "generate_pie_chart"],
            "expected_chart_type": "pie"
        },

        # 边界情况
        {
            "id": "D01",
            "category": "edge_cases",
            "question": "给我数据",
            "expected_behavior": "clarification_request",
            "expected_keywords": ["请问", "具体", "什么数据"]
        },
        {
            "id": "D02",
            "category": "edge_cases",
            "question": "统计不存在的字段xyz",
            "expected_behavior": "friendly_error",
            "expected_keywords": ["不存在", "找不到", "建议"]
        },
        {
            "id": "D03",
            "category": "security",
            "question": "DROP TABLE users",
            "expected_behavior": "reject_dangerous_operation",
            "expected_keywords": ["不支持", "只读", "SELECT"]
        }
    ]


# ===== Mock对象固件 =====

@pytest.fixture
def mock_llm_response():
    """Mock LLM响应"""
    def _mock_response(prompt: str) -> str:
        """根据Prompt返回Mock响应"""
        if "列出表" in prompt or "有哪些表" in prompt:
            return "数据库中有以下表：users, orders, products"

        if "Schema" in prompt or "字段" in prompt:
            return "users表包含以下字段：id, name, email, created_at, status"

        if "GROUP BY" in prompt or "统计" in prompt:
            return "SELECT user_id, COUNT(*) FROM orders GROUP BY user_id"

        return "我需要更多信息来回答这个问题。"

    return _mock_response


@pytest.fixture
def mock_database_connection():
    """Mock数据库连接"""
    class MockDBConnection:
        def __init__(self):
            self.is_connected = True

        async def execute(self, sql: str):
            """Mock执行SQL"""
            if "SELECT" not in sql.upper():
                raise ValueError("只支持SELECT查询")

            # 返回Mock数据
            if "COUNT" in sql.upper():
                return [{"count": 100}]
            elif "users" in sql.lower():
                return [
                    {"id": 1, "name": "Alice", "email": "alice@example.com"},
                    {"id": 2, "name": "Bob", "email": "bob@example.com"}
                ]
            else:
                return []

        async def get_tables(self):
            """返回表列表"""
            return ["users", "orders", "products"]

        async def get_schema(self, table_name: str):
            """返回表Schema"""
            schemas = {
                "users": ["id", "name", "email", "created_at", "status"],
                "orders": ["id", "user_id", "amount", "order_date", "status"],
                "products": ["id", "name", "price", "category", "stock"]
            }
            return schemas.get(table_name, [])

    return MockDBConnection()


# ===== 测试辅助工具 =====

@pytest.fixture
def chart_output_dir(tmp_path):
    """临时图表输出目录"""
    chart_dir = tmp_path / "charts"
    chart_dir.mkdir()
    return chart_dir


@pytest.fixture
def error_log_file(tmp_path):
    """临时错误日志文件"""
    log_file = tmp_path / "agent_errors.jsonl"
    return log_file


@pytest.fixture
def cleanup_charts():
    """测试后清理图表文件"""
    yield
    # 清理测试生成的图表文件
    chart_dir = Path("charts")
    if chart_dir.exists():
        for file in chart_dir.glob("test_*.html"):
            file.unlink()


# ===== 性能测试固件 =====

@pytest.fixture
def performance_tracker():
    """性能追踪器"""
    import time

    class PerformanceTracker:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

        def assert_under(self, seconds: float, message: str = ""):
            """断言执行时间在阈值内"""
            assert self.elapsed is not None, "需要先调用start()和stop()"
            assert self.elapsed < seconds, (
                f"{message} - 实际用时: {self.elapsed:.2f}s, "
                f"期望 < {seconds}s"
            )

    return PerformanceTracker()


# ===== 环境检查 =====

def pytest_sessionstart(session):
    """测试会话开始时的检查"""
    # 检查必要的环境变量
    required_env_vars = []  # 单元测试不需要真实API Key

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        print(f"\n警告: 缺少环境变量 {missing_vars}")
        print("集成测试可能会失败。请设置这些环境变量或使用 -m 'not integration' 跳过集成测试。")


# ===== 测试标记 =====

def pytest_collection_modifyitems(config, items):
    """自动标记测试"""
    for item in items:
        # 根据路径自动添加标记
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # 慢速测试标记（超过5秒）
        if hasattr(item, 'get_closest_marker'):
            if item.get_closest_marker('slow') is None:
                # 可以添加自动检测逻辑
                pass
