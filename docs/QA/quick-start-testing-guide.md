# Agent测试快速开始指南

**创建时间**: 2025-01-06
**适用对象**: 开发人员、QA工程师

---

## 快速开始（3分钟）

### 1. 运行基础测试
```bash
# Windows
cd C:\data_agent
scripts\run_agent_tests.bat unit

# Linux/Mac
cd /path/to/data_agent
chmod +x scripts/run_agent_tests.sh
./scripts/run_agent_tests.sh unit
```

### 2. 查看测试结果
测试通过后会显示：
```
========================================
  ✓ 测试通过
========================================

测试覆盖率: 75%
通过: 25/25
```

### 3. 生成错误报告
```bash
cd Agent
python error_tracker.py
```

---

## 测试类型说明

### 单元测试（推荐日常使用）
```bash
scripts\run_agent_tests.bat unit
```
- **运行时间**: ~30秒
- **用途**: 验证核心逻辑正确性
- **适用场景**: 每次代码修改后

### 黄金测试用例（验收测试）
```bash
scripts\run_agent_tests.bat golden
```
- **运行时间**: ~1分钟
- **用途**: 确保常见问题能正确处理
- **适用场景**: 发布前验收

### 集成测试（需要真实环境）
```bash
# 需要先设置环境变量
set DEEPSEEK_API_KEY=your_key_here
set DATABASE_URL=postgresql://...

scripts\run_agent_tests.bat integration
```
- **运行时间**: ~3分钟
- **用途**: 验证与外部服务的集成
- **适用场景**: 部署前验证

### 快速测试（最快）
```bash
scripts\run_agent_tests.bat quick
```
- **运行时间**: ~10秒
- **用途**: 快速检查是否有明显错误
- **适用场景**: 开发过程中频繁运行

---

## 添加新测试用例

### 方法1: 在代码中添加
编辑 `Agent/tests/unit/test_golden_cases.py`:

```python
@pytest.mark.parametrize("question,expected_keywords", [
    ("你的新问题", ["期望关键词1", "期望关键词2"]),
])
def test_your_new_case(self, question, expected_keywords):
    # 测试逻辑
    pass
```

### 方法2: 在配置文件中添加
编辑 `Agent/tests/conftest.py` 中的 `golden_test_cases` fixture:

```python
{
    "id": "A99",
    "category": "your_category",
    "question": "你的测试问题",
    "expected_keywords": ["期望", "关键词"]
}
```

---

## 查看测试覆盖率

### 生成HTML报告
```bash
cd Agent
pytest tests/ --cov --cov-report=html
```

### 打开报告
```bash
# Windows
start htmlcov\index.html

# Linux
xdg-open htmlcov/index.html

# Mac
open htmlcov/index.html
```

报告中会显示：
- ✅ 绿色：代码已覆盖
- ❌ 红色：代码未覆盖
- 📊 百分比：覆盖率统计

---

## 错误监控与分析

### 查看错误日志
```bash
# 查看最近的错误
tail -n 50 agent_errors.jsonl

# Windows
powershell "Get-Content agent_errors.jsonl -Tail 50"
```

### 生成错误报告
```python
from Agent.error_tracker import error_tracker

# 生成最近7天的报告
report = error_tracker.generate_report(days=7)
print(report)

# 保存到文件
with open("error_report.md", "w", encoding="utf-8") as f:
    f.write(report)
```

### 查看统计数据
```python
from Agent.error_tracker import error_tracker

# 获取统计
stats = error_tracker.get_error_stats(days=7)

print(f"成功率: {stats['success_rate']}")
print(f"总错误: {stats['total_errors']}")
print(f"Top错误: {stats['top_error_questions'][:3]}")
```

---

## 集成到Agent代码

### 在sql_agent.py中集成错误追踪
```python
from error_tracker import log_agent_error, error_tracker

async def run_agent(question: str):
    try:
        import time
        start_time = time.time()

        result = await agent.invoke({"messages": [question]})

        # 记录成功
        elapsed = time.time() - start_time
        error_tracker.log_success(
            question=question,
            response=str(result),
            execution_time=elapsed
        )

        return result

    except Exception as e:
        # 记录错误
        log_agent_error(
            question=question,
            error=e,
            context={
                "user_id": "...",
                "tenant_id": "..."
            }
        )
        raise
```

---

## CI/CD集成（可选）

### GitHub Actions示例
创建 `.github/workflows/agent-tests.yml`:

```yaml
name: Agent Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Run Tests
        run: |
          cd Agent
          pip install pytest pytest-cov
          pytest tests/unit -v --cov

      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        if: always()
```

---

## 常见问题

### Q1: 测试失败了怎么办？

**A**: 按照以下步骤排查：
1. 查看错误信息中的具体失败原因
2. 运行 `pytest tests/ -v -x` 在第一个失败处停止
3. 使用 `pytest tests/unit/test_xxx.py::test_function -v` 单独运行失败的测试
4. 检查是否缺少依赖：`pip install -r requirements.txt`

### Q2: 如何跳过慢速测试？

**A**: 使用标记过滤：
```bash
# 跳过集成测试
pytest tests/ -m "not integration"

# 跳过E2E测试
pytest tests/ -m "not e2e"

# 只运行快速测试
pytest tests/unit -m "not slow"
```

### Q3: 测试覆盖率太低怎么办？

**A**:
1. 运行 `pytest --cov --cov-report=html` 查看未覆盖的代码
2. 为未覆盖的函数添加单元测试
3. 目标：核心功能覆盖率 >= 70%

### Q4: 如何调试失败的测试？

**A**: 使用pytest的调试功能：
```bash
# 显示详细输出
pytest tests/ -v -s

# 在失败时进入调试器
pytest tests/ --pdb

# 只运行上次失败的测试
pytest tests/ --lf
```

---

## 每日工作流程建议

### 开发中（每次代码修改后）
```bash
# 快速测试
scripts\run_agent_tests.bat quick
```

### 提交前（每次commit前）
```bash
# 单元测试
scripts\run_agent_tests.bat unit

# 如果通过，提交代码
git add .
git commit -m "feat: 新功能"
```

### 发布前（准备部署）
```bash
# 运行所有测试
scripts\run_agent_tests.bat all

# 检查错误报告
python Agent/error_tracker.py

# 生成覆盖率报告
cd Agent
pytest tests/ --cov --cov-report=html
```

---

## 进阶使用

### 自定义测试配置
编辑 `Agent/pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# 添加自定义标记
markers =
    unit: 单元测试
    integration: 集成测试
    e2e: 端到端测试
    slow: 慢速测试 (>5s)

# 覆盖率配置
addopts =
    --strict-markers
    --cov=.
    --cov-branch
```

### 并行运行测试
```bash
# 安装pytest-xdist
pip install pytest-xdist

# 使用4个CPU核心并行运行
pytest tests/ -n 4
```

### 生成测试报告
```bash
# 安装pytest-html
pip install pytest-html

# 生成HTML测试报告
pytest tests/ --html=report.html --self-contained-html
```

---

## 相关文档

- [完整QA策略文档](./ai-analysis-qa-strategy.md) - 详细的质量保证策略
- [错误分类体系](./ai-analysis-qa-strategy.md#四错误监控与分析) - 错误类型说明
- [Pytest官方文档](https://docs.pytest.org/) - Pytest使用指南

---

**提示**: 测试不是负担，而是质量保证的第一道防线。养成良好的测试习惯，能大幅减少生产环境的问题。
