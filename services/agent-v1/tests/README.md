# Agent测试套件

Data Agent V4 - AI分析功能的全面测试框架

---

## 快速开始

### 运行测试（30秒）
```bash
# Windows
cd C:\data_agent
scripts\run_agent_tests.bat unit

# 或者直接使用pytest
cd Agent
pytest tests/unit -v
```

### 查看结果
```
✓ 测试通过
==================== 25 passed in 5.23s ====================
```

---

## 目录结构

```
tests/
├── README.md                   # 本文件
├── conftest.py                 # Pytest配置和共享固件
├── unit/                       # 单元测试
│   ├── test_golden_cases.py    # 黄金测试用例集
│   ├── test_sql_validator.py   # SQL验证测试（待添加）
│   └── test_data_transformer.py # 数据转换测试（待添加）
├── integration/                # 集成测试（待添加）
│   ├── test_mcp_tools.py
│   └── test_langgraph_workflow.py
└── e2e/                        # 端到端测试（待添加）
    └── test_real_scenarios.py
```

---

## 测试类型

### 1. 单元测试 (Unit Tests)
- **位置**: `tests/unit/`
- **用途**: 测试单个函数/类的正确性
- **运行**: `pytest tests/unit -v`
- **速度**: 快（~30秒）

### 2. 集成测试 (Integration Tests)
- **位置**: `tests/integration/`
- **用途**: 测试模块间集成和外部服务连接
- **运行**: `pytest tests/integration -v -m integration`
- **速度**: 中（~3分钟）
- **要求**: 需要环境变量（DEEPSEEK_API_KEY, DATABASE_URL）

### 3. 端到端测试 (E2E Tests)
- **位置**: `tests/e2e/`
- **用途**: 测试完整用户场景
- **运行**: `pytest tests/e2e -v -m e2e`
- **速度**: 慢（~5分钟）

---

## 黄金测试用例集

黄金测试用例是一组精心设计的测试，覆盖了所有常见用户问题场景。

### 分类
1. **A类 - 数据探索**: 基础查询（"有哪些表？"）
2. **B类 - 数据分析**: 聚合统计（"统计订单数"）
3. **C类 - 可视化**: 图表生成（"画趋势图"）
4. **D类 - 边界情况**: 模糊问题、错误处理
5. **E类 - 多轮对话**: 上下文理解

### 运行黄金测试
```bash
pytest tests/unit/test_golden_cases.py -v
```

---

## 测试固件（Fixtures）

在 `conftest.py` 中定义了以下可复用的测试固件：

### 数据固件
- `sample_schema`: 示例数据库Schema
- `sample_query_results`: 示例查询结果
- `golden_test_cases`: 黄金测试用例集

### Mock对象
- `mock_llm_response`: Mock LLM响应
- `mock_database_connection`: Mock数据库连接

### 工具固件
- `performance_tracker`: 性能追踪
- `chart_output_dir`: 临时图表目录
- `cleanup_charts`: 自动清理图表

---

## 编写新测试

### 单元测试示例
```python
import pytest

@pytest.mark.unit
def test_your_function(sample_schema):
    """测试描述"""
    # Arrange
    input_data = "test input"

    # Act
    result = your_function(input_data)

    # Assert
    assert result == expected_output
```

### 使用参数化测试
```python
@pytest.mark.parametrize("question,expected", [
    ("问题1", "期望结果1"),
    ("问题2", "期望结果2"),
])
def test_multiple_cases(question, expected):
    result = process(question)
    assert expected in result
```

### 异步测试
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

---

## 测试覆盖率

### 生成覆盖率报告
```bash
# 终端报告
pytest tests/ --cov --cov-report=term-missing

# HTML报告
pytest tests/ --cov --cov-report=html
# 打开 htmlcov/index.html 查看
```

### 覆盖率目标
- 核心功能: >= 80%
- 总体: >= 70%
- 关键路径: 100%

---

## 常用命令

### 运行特定测试
```bash
# 运行单个测试文件
pytest tests/unit/test_golden_cases.py -v

# 运行单个测试函数
pytest tests/unit/test_golden_cases.py::TestGoldenCases::test_all_golden_cases_structure -v

# 运行匹配模式的测试
pytest tests/ -k "golden" -v
```

### 测试标记
```bash
# 只运行单元测试
pytest tests/ -m unit

# 跳过集成测试
pytest tests/ -m "not integration"

# 跳过慢速测试
pytest tests/ -m "not slow"
```

### 调试选项
```bash
# 显示print输出
pytest tests/ -v -s

# 第一个失败后停止
pytest tests/ -x

# 进入调试器
pytest tests/ --pdb

# 重新运行失败的测试
pytest tests/ --lf
```

---

## CI/CD集成

### GitHub Actions示例
```yaml
- name: Run Tests
  run: |
    cd Agent
    pytest tests/unit -v --cov
```

### 本地pre-commit hook
```bash
# 在 .git/hooks/pre-commit 中添加
#!/bin/bash
cd Agent
pytest tests/unit --tb=short -q
```

---

## 常见问题

### Q: 测试失败了怎么办？
**A**:
1. 查看错误消息
2. 运行 `pytest tests/ -v -x` 在第一个失败处停止
3. 使用 `pytest tests/ --pdb` 进入调试器

### Q: 如何跳过需要外部依赖的测试？
**A**: 使用标记
```bash
pytest tests/ -m "not integration"
```

### Q: 如何提高测试速度？
**A**:
1. 只运行单元测试：`pytest tests/unit`
2. 使用并行执行：`pytest tests/ -n 4` （需要pytest-xdist）
3. 使用pytest-xdist缓存：`pytest tests/ --cache`

---

## 相关文档

- [完整QA策略](../../docs/QA/ai-analysis-qa-strategy.md) - 详细的质量保证策略
- [快速开始指南](../../docs/QA/quick-start-testing-guide.md) - 新手教程
- [验证检查清单](../../docs/QA/ai-analysis-verification-checklist.md) - 发布前检查

---

## 贡献指南

### 添加新测试
1. 在合适的目录下创建测试文件（`test_*.py`）
2. 遵循现有的测试风格
3. 添加必要的docstring说明
4. 确保测试可以独立运行
5. 更新本README（如果需要）

### 测试命名规范
- 测试文件: `test_<module_name>.py`
- 测试类: `Test<FeatureName>`
- 测试函数: `test_<specific_behavior>`

### 代码风格
- 遵循PEP8
- 使用类型注解
- 添加清晰的docstring
- AAA模式: Arrange, Act, Assert

---

**维护者**: AI Assistant
**最后更新**: 2025-01-06
**版本**: V1.0
