# AI分析功能质量保证策略

**项目**: Data Agent V4
**模块**: Agent (LangGraph SQL智能代理)
**创建时间**: 2025-01-06
**维护者**: QA Team

---

## 目标

确保AI分析功能能够对所有合理的用户问题给出准确、稳定的回复，将错误率控制在可接受范围内（目标：<5%）。

---

## 一、测试金字塔策略

### 1. 单元测试（70%覆盖）

#### 1.1 SQL生成与验证
```python
# Agent/tests/test_sql_validator.py
def test_sql_injection_prevention():
    """测试SQL注入防护"""
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "admin'--"
    ]
    # 验证所有输入都被正确处理

def test_sql_syntax_validation():
    """测试SQL语法验证"""
    valid_sqls = [
        "SELECT * FROM users",
        "SELECT COUNT(*) FROM orders WHERE status='active'"
    ]
    invalid_sqls = [
        "SELCT * FROM users",  # 拼写错误
        "SELECT * FORM users"  # 关键词错误
    ]
    # 验证能正确识别有效/无效SQL

def test_database_dialect_adaptation():
    """测试多数据库方言适配"""
    test_cases = [
        ("postgresql", "LIMIT 10", True),
        ("mysql", "LIMIT 10", True),
        ("postgresql", "TOP 10", False),  # SQL Server语法
    ]
    # 验证不同数据库的SQL方言
```

#### 1.2 数据转换准确性
```python
# Agent/tests/test_data_transformer.py
def test_chart_data_transformation():
    """测试查询结果到图表数据的转换"""
    sql_result = [
        {"month": "2024-01", "count": 100},
        {"month": "2024-02", "count": 150}
    ]
    chart_config = transform_to_chart(sql_result, "line")
    assert chart_config["xAxis"]["data"] == ["2024-01", "2024-02"]
    assert chart_config["series"][0]["data"] == [100, 150]

def test_empty_result_handling():
    """测试空结果处理"""
    result = transform_to_chart([], "bar")
    assert result is not None
    assert "error" not in result

def test_data_type_conversion():
    """测试数据类型转换"""
    test_data = [
        {"date": datetime(2024, 1, 1), "value": Decimal("123.45")}
    ]
    # 验证能正确转换为JSON可序列化的格式
```

#### 1.3 Prompt工程测试
```python
# Agent/tests/test_prompt_generator.py
def test_schema_injection():
    """测试Schema信息注入"""
    schema = {
        "users": ["id", "name", "email"],
        "orders": ["id", "user_id", "amount"]
    }
    prompt = generate_sql_prompt("统计每个用户的订单数", schema)
    # 验证Schema信息被正确注入到Prompt中
    assert "users" in prompt
    assert "orders" in prompt
    assert "user_id" in prompt

def test_error_context_enhancement():
    """测试错误上下文增强"""
    error = "column 'username' does not exist"
    enhanced_prompt = enhance_error_prompt(error, schema)
    # 验证提供了正确的列名建议
    assert "name" in enhanced_prompt or "email" in enhanced_prompt
```

---

### 2. 集成测试（20%覆盖）

#### 2.1 MCP工具链集成
```python
# Agent/tests/integration/test_mcp_tools.py
@pytest.mark.integration
async def test_postgres_mcp_connection():
    """测试PostgreSQL MCP连接"""
    agent = await create_test_agent()
    result = await agent.invoke({"messages": ["列出所有表"]})
    assert "tables" in str(result).lower()

@pytest.mark.integration
async def test_echarts_mcp_generation():
    """测试ECharts图表生成"""
    agent = await create_test_agent()
    result = await agent.invoke({
        "messages": ["画一个订单趋势图"]
    })
    # 验证生成了HTML文件
    assert os.path.exists("charts/chart_line_*.html")
```

#### 2.2 LangGraph工作流测试
```python
# Agent/tests/integration/test_langgraph_workflow.py
@pytest.mark.integration
async def test_multi_step_reasoning():
    """测试多步推理流程"""
    question = "对比2023年和2024年的销售额，并画图"
    agent = await create_test_agent()

    # 追踪执行路径
    execution_log = []
    result = await agent.stream({"messages": [question]})

    async for step in result:
        execution_log.append(step)

    # 验证执行路径：schema获取 -> SQL生成 -> 查询 -> 图表生成
    assert any("get_schema" in str(s) for s in execution_log)
    assert any("query" in str(s) for s in execution_log)
    assert any("generate" in str(s) for s in execution_log)

@pytest.mark.integration
async def test_error_recovery_flow():
    """测试错误自动修复流程"""
    # 故意使用错误的列名
    question = "查询username字段"  # 实际字段是name
    result = await agent.invoke({"messages": [question]})

    # 验证Agent能自动修复错误
    assert "error" not in str(result).lower()
    # 或验证给出了有用的提示
```

---

### 3. 端到端测试（10%覆盖）

#### 3.1 真实场景测试
```python
# Agent/tests/e2e/test_real_scenarios.py
@pytest.mark.e2e
async def test_complete_analysis_workflow():
    """完整分析工作流"""
    # 1. 连接数据库
    agent = create_production_agent(DATABASE_URL)

    # 2. 数据探索
    result1 = await agent.invoke({"messages": ["数据库里有什么数据？"]})
    assert result1 is not None

    # 3. 数据分析
    result2 = await agent.invoke({"messages": ["统计最近7天的用户活跃度"]})
    assert "error" not in str(result2).lower()

    # 4. 可视化
    result3 = await agent.invoke({"messages": ["画出趋势图"]})
    assert os.path.exists("charts/chart_*.html")

@pytest.mark.e2e
async def test_multi_database_support():
    """多数据库支持测试"""
    databases = [
        ("postgresql://...", "PostgreSQL"),
        ("mysql://...", "MySQL")
    ]

    for db_url, db_type in databases:
        agent = create_production_agent(db_url)
        result = await agent.invoke({"messages": ["列出表"]})
        assert result is not None
```

---

## 二、测试用例库（Golden Test Set）

### 分类A：数据探索（基础问题）
| ID | 问题 | 期望行为 | 优先级 |
|----|------|----------|--------|
| A01 | "数据库里有哪些表？" | 返回表列表 | P0 |
| A02 | "用户表有哪些字段？" | 返回Schema信息 | P0 |
| A03 | "数据库中有多少条记录？" | 执行COUNT查询 | P0 |
| A04 | "最新的10条记录是什么？" | LIMIT查询 | P1 |

### 分类B：数据分析（中等复杂度）
| ID | 问题 | 期望行为 | 优先级 |
|----|------|----------|--------|
| B01 | "统计每个用户的订单数量" | JOIN + GROUP BY | P0 |
| B02 | "找出销售额最高的前10个商品" | ORDER BY + LIMIT | P0 |
| B03 | "计算最近30天的日均订单量" | DATE函数 + AVG | P1 |
| B04 | "对比本月和上月的GMV" | 时间窗口对比 | P1 |

### 分类C：可视化（图表生成）
| ID | 问题 | 期望行为 | 优先级 |
|----|------|----------|--------|
| C01 | "画出每月订单趋势图" | 折线图 | P0 |
| C02 | "用饼图展示产品类别分布" | 饼图 | P0 |
| C03 | "生成销售额柱状图" | 柱状图 | P0 |
| C04 | "画出用户增长漏斗图" | 漏斗图 | P1 |

### 分类D：边界情况（鲁棒性）
| ID | 问题 | 期望行为 | 优先级 |
|----|------|----------|--------|
| D01 | "给我数据" （模糊问题） | 请求澄清 | P0 |
| D02 | "统计不存在的字段" | 友好错误提示 | P0 |
| D03 | "查询100万条记录" | 限制或警告 | P1 |
| D04 | "DROP TABLE users" | 拒绝危险操作 | P0 |

### 分类E：多轮对话（上下文理解）
| ID | 对话序列 | 期望行为 | 优先级 |
|----|----------|----------|--------|
| E01 | Q1:"统计订单数" → Q2:"画出来" | 基于上文生成图表 | P0 |
| E02 | Q1:"查询用户" → Q2:"只看活跃的" | 追加过滤条件 | P1 |
| E03 | Q1:"销售趋势" → Q2:"改成按周统计" | 修改聚合粒度 | P1 |

---

## 三、自动化测试框架

### 3.1 测试脚本结构
```
Agent/tests/
├── __init__.py
├── conftest.py                    # Pytest配置
├── fixtures/                      # 测试固件
│   ├── sample_databases.py
│   ├── mock_schemas.py
│   └── golden_test_cases.json
├── unit/
│   ├── test_sql_validator.py
│   ├── test_data_transformer.py
│   └── test_prompt_generator.py
├── integration/
│   ├── test_mcp_tools.py
│   └── test_langgraph_workflow.py
├── e2e/
│   ├── test_real_scenarios.py
│   └── test_multi_database.py
└── utils/
    ├── test_helpers.py
    └── assertion_utils.py
```

### 3.2 CI/CD集成
```yaml
# .github/workflows/agent-tests.yml
name: Agent Quality Gate

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd Agent
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run unit tests
        run: pytest Agent/tests/unit -v --cov

      - name: Run integration tests
        run: pytest Agent/tests/integration -v
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}

      - name: Quality Gate
        run: |
          # 测试覆盖率必须 >= 70%
          coverage report --fail-under=70
```

---

## 四、错误监控与分析

### 4.1 错误分类体系
```python
# Agent/models.py
class ErrorCategory(Enum):
    # 用户输入问题
    AMBIGUOUS_QUERY = "用户问题不明确"
    INVALID_REQUEST = "无效请求"

    # 系统错误
    DATABASE_CONNECTION = "数据库连接失败"
    MCP_TOOL_FAILURE = "MCP工具调用失败"
    LLM_API_ERROR = "LLM API错误"

    # 数据问题
    SCHEMA_NOT_FOUND = "表或字段不存在"
    EMPTY_RESULT = "查询无结果"
    DATA_TYPE_MISMATCH = "数据类型不匹配"

    # 安全问题
    SQL_INJECTION_ATTEMPT = "SQL注入尝试"
    DANGEROUS_OPERATION = "危险操作"
```

### 4.2 错误记录与追踪
```python
# Agent/sql_agent.py
import logging
import json
from datetime import datetime

class ErrorTracker:
    def __init__(self, log_file="agent_errors.jsonl"):
        self.log_file = log_file

    def log_error(self, question, error_type, error_msg, context):
        """记录错误到JSONL文件"""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "error_category": error_type.value,
            "error_message": error_msg,
            "context": context,
            "resolved": False
        }

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(error_entry, ensure_ascii=False) + "\n")

    def get_error_stats(self, days=7):
        """统计最近N天的错误分布"""
        # 读取日志并统计
        pass

# 在Agent中使用
error_tracker = ErrorTracker()

async def run_agent(question: str):
    try:
        result = await agent.invoke({"messages": [question]})
        return result
    except Exception as e:
        error_tracker.log_error(
            question=question,
            error_type=ErrorCategory.LLM_API_ERROR,
            error_msg=str(e),
            context={"user_id": "...", "tenant_id": "..."}
        )
        raise
```

---

## 五、持续改进机制

### 5.1 每周质量报告
```python
# scripts/generate_qa_report.py
def generate_weekly_report():
    """生成每周质量报告"""
    report = {
        "week": "2025-W01",
        "total_queries": 1000,
        "successful_queries": 950,
        "failed_queries": 50,
        "success_rate": "95%",
        "top_errors": [
            {"type": "SCHEMA_NOT_FOUND", "count": 20},
            {"type": "AMBIGUOUS_QUERY", "count": 15},
            {"type": "LLM_API_ERROR", "count": 10}
        ],
        "test_coverage": "75%",
        "new_test_cases_added": 5
    }
    return report
```

### 5.2 失败案例自动收集
```python
# Agent/sql_agent.py
async def run_agent_with_logging(question: str):
    """运行Agent并自动收集失败案例"""
    try:
        result = await agent.invoke({"messages": [question]})

        # 判断是否成功
        if "error" in str(result).lower() or "抱歉" in str(result):
            # 保存到失败案例库
            save_failed_case({
                "question": question,
                "result": result,
                "timestamp": datetime.now()
            })

        return result
    except Exception as e:
        save_failed_case({
            "question": question,
            "exception": str(e),
            "timestamp": datetime.now()
        })
        raise
```

### 5.3 Golden Test Set 自动更新
```python
# scripts/update_golden_tests.py
def update_golden_tests():
    """基于成功案例更新测试集"""
    # 1. 从生产日志中提取高频成功查询
    successful_queries = extract_successful_queries(days=30)

    # 2. 去重和聚类
    unique_patterns = cluster_similar_queries(successful_queries)

    # 3. 添加到Golden Test Set
    for pattern in unique_patterns:
        if pattern not in existing_test_cases:
            add_test_case(pattern)
```

---

## 六、人工审查流程

### 6.1 每日错误复盘（15分钟）
1. **查看错误日志**：`tail -100 agent_errors.jsonl`
2. **识别模式**：是否有重复出现的错误类型？
3. **优先级排序**：哪些错误影响最大用户？
4. **快速修复**：能否在今日内修复？

### 6.2 每周深度分析（1小时）
1. **生成质量报告**：`python scripts/generate_qa_report.py`
2. **团队评审**：讨论Top 5错误类型
3. **改进计划**：制定下周优化目标
4. **更新测试**：添加新发现的边界案例

---

## 七、质量门禁标准

### 发布前检查清单
- [ ] 所有P0测试用例通过率 100%
- [ ] P1测试用例通过率 >= 95%
- [ ] 单元测试覆盖率 >= 70%
- [ ] 集成测试全部通过
- [ ] 无P0级别的已知Bug
- [ ] 错误率 < 5% (最近7天)
- [ ] LLM Token成本在预算内
- [ ] 响应时间 P95 < 10秒

---

## 八、快速开始

### 运行所有测试
```bash
cd Agent
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov

# 运行全部测试
pytest tests/ -v --cov

# 只运行单元测试
pytest tests/unit -v

# 只运行集成测试
pytest tests/integration -v -m integration

# 生成覆盖率报告
pytest tests/ --cov --cov-report=html
open htmlcov/index.html
```

### 添加新测试用例
1. 在 `Agent/tests/fixtures/golden_test_cases.json` 添加测试数据
2. 在对应的测试文件中添加测试函数
3. 运行测试验证：`pytest tests/ -k test_new_feature`
4. 提交PR时自动运行CI测试

---

## 附录：参考资料

- [LangGraph Testing Best Practices](https://langchain-ai.github.io/langgraph/testing/)
- [Pytest Async Testing Guide](https://pytest-asyncio.readthedocs.io/)
- [SQL Injection Prevention Checklist](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)

---

**维护承诺**: 本文档每周更新，确保反映最新的测试策略和质量标准。
