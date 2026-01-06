# AI分析质量保证集成指南

**版本**: V1.0
**创建日期**: 2025-01-06
**目标读者**: 后端开发者
**预计耗时**: 15分钟

---

## 📋 概述

本指南将帮助你将AI分析质量保证系统集成到生产环境中。集成完成后，系统将自动记录所有AI分析的成功/失败情况，并提供详细的错误统计报告。

---

## ✅ 前置条件检查

在开始之前，请确保：

- [x] 已完成测试框架验证（18/18 tests passed）
- [x] Agent模块已包含 `error_tracker.py` 和 `run_agent_with_tracking()` 函数
- [x] 后端服务正常运行在 http://localhost:8004
- [x] 你有权限修改后端代码

验证命令：
```bash
# 检查测试是否通过
cd Agent
python -m pytest tests/unit/test_golden_cases.py -v

# 检查error_tracker模块是否存在
python -c "from Agent.error_tracker import error_tracker; print('✓ error_tracker 模块正常')"

# 检查run_agent_with_tracking函数是否存在
python -c "from Agent.sql_agent import run_agent_with_tracking; print('✓ run_agent_with_tracking 函数正常')"
```

---

## 🎯 集成方案

### 方案概述

我们将在后端API层集成错误追踪，具体路径：

```
用户请求
  → 前端 (localhost:3000)
    → 后端API (localhost:8004/api/v1/llm/query-with-agent)
      → backend/src/app/api/v1/endpoints/query.py
        → backend/src/app/services/agent_service.py::run_agent_query()
          → Agent/sql_agent.py::run_agent() ← 【修改点：改为 run_agent_with_tracking()】
            → LangGraph SQL Agent
              → 错误自动记录到 Agent/agent_errors.jsonl
```

---

## 📝 详细修改步骤

### 第1步：定位文件 (1分钟)

打开文件：`backend/src/app/services/agent_service.py`

**文件路径**:
```
C:\data_agent\backend\src\app\services\agent_service.py
```

**关键行号**:
- **Line 784-1014**: `run_agent_query()` 函数定义
- **Line 970**: 实际调用 `run_agent()` 的位置（需要修改）

---

### 第2步：修改导入语句 (2分钟)

**位置**: 文件顶部导入区域（约第10-30行）

**原始代码** (查找这一行):
```python
from sql_agent import run_agent
```

**修改为**:
```python
from sql_agent import run_agent_with_tracking
```

**说明**:
- 如果找不到这一行，说明导入可能在其他地方
- 搜索关键词: `from sql_agent import` 或 `import run_agent`
- 确保导入的是 `run_agent_with_tracking` 而不是 `run_agent`

**验证方法**:
```bash
# 在backend目录下搜索导入语句
cd C:\data_agent\backend
grep -n "from sql_agent import" src/app/services/agent_service.py
```

---

### 第3步：修改函数调用 (5分钟)

**位置**: `run_agent_query()` 函数内部，约第970行

**原始代码** (查找这段代码):
```python
result = await run_agent(
    question=enhanced_question,
    database_url=effective_db_url,
    thread_id=thread_id,
    enable_echarts=enable_echarts,
    verbose=verbose,
    db_type=db_type
)
```

**修改为**:
```python
# 🔥 【QA集成】使用带错误追踪的run_agent版本
result = await run_agent_with_tracking(
    question=enhanced_question,
    database_url=effective_db_url,
    thread_id=thread_id,
    enable_echarts=enable_echarts,
    verbose=verbose,
    db_type=db_type,
    # 🔥 【QA集成】添加上下文信息用于错误分析
    context={
        "source": "backend_api",
        "endpoint": "/api/v1/llm/query-with-agent",
        "user_question": question,  # 原始问题（未增强）
        "thread_id": thread_id,
        "db_type": db_type,
    }
)
```

**关键变更**:
1. **函数名**: `run_agent` → `run_agent_with_tracking`
2. **新增参数**: `context` - 提供额外的上下文信息用于错误分析
3. **注释**: 添加清晰的注释说明这是QA集成

**验证方法**:
```bash
# 检查是否正确调用了run_agent_with_tracking
cd C:\data_agent\backend
grep -n "run_agent_with_tracking" src/app/services/agent_service.py
```

---

### 第4步：验证修改 (3分钟)

#### 4.1 语法检查

```bash
cd C:\data_agent\backend
python -c "import src.app.services.agent_service; print('✓ 语法检查通过')"
```

如果出现导入错误：
- 检查是否正确修改了导入语句
- 检查是否有拼写错误

#### 4.2 完整性检查

使用以下命令检查文件内容：

```bash
# Windows PowerShell
cd C:\data_agent\backend
Select-String -Path "src\app\services\agent_service.py" -Pattern "run_agent_with_tracking" -Context 2,2
```

预期输出应包含：
```
  导入行: from sql_agent import run_agent_with_tracking
  调用行: result = await run_agent_with_tracking(
```

---

### 第5步：测试集成 (4分钟)

#### 5.1 启动后端服务

```bash
cd C:\data_agent\backend
uvicorn src.app.main:app --reload --port 8004
```

#### 5.2 测试API请求

打开新的终端窗口，运行测试：

```bash
# 测试基本查询
curl -X POST "http://localhost:8004/api/v1/llm/query-with-agent" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "数据库里有哪些表？",
    "tenant_id": "default_tenant",
    "user_id": "test_user"
  }'
```

#### 5.3 检查错误日志

```bash
cd C:\data_agent\Agent

# 检查成功日志
type agent_success.jsonl

# 检查错误日志
type agent_errors.jsonl
```

**预期结果**:
- 如果查询成功，`agent_success.jsonl` 应该有新记录
- 如果查询失败，`agent_errors.jsonl` 应该有错误记录
- 每条记录包含时间戳、问题、上下文等信息

---

## 🚨 常见问题与解决方案

### Q1: 找不到 `from sql_agent import run_agent`

**原因**: 导入语句可能在不同的位置或格式

**解决方案**:
```bash
# 搜索所有run_agent相关的导入
cd C:\data_agent\backend
grep -rn "run_agent" src/app/services/agent_service.py
```

可能的格式：
```python
from Agent.sql_agent import run_agent  # 绝对导入
from .sql_agent import run_agent       # 相对导入
import sql_agent                       # 模块导入
```

对应的修改：
```python
from Agent.sql_agent import run_agent_with_tracking
from .sql_agent import run_agent_with_tracking
import sql_agent  # 然后调用 sql_agent.run_agent_with_tracking()
```

### Q2: ImportError: cannot import name 'run_agent_with_tracking'

**原因**: Agent模块路径问题

**解决方案**:
```bash
# 检查Python路径
cd C:\data_agent
python -c "import sys; print('\n'.join(sys.path))"

# 检查函数是否存在
python -c "from Agent.sql_agent import run_agent_with_tracking; print('✓ 函数存在')"
```

如果仍然失败：
1. 确保 `Agent` 目录在 Python 路径中
2. 检查 `Agent/__init__.py` 是否存在
3. 尝试绝对导入: `from Agent.sql_agent import run_agent_with_tracking`

### Q3: 测试请求时API返回500错误

**原因**: 可能是其他依赖问题

**解决方案**:
```bash
# 查看详细错误日志
cd C:\data_agent\backend
tail -f logs/app.log  # 如果有日志文件

# 或者检查终端输出
# 查看uvicorn启动终端的错误信息
```

常见错误：
- **数据库连接失败**: 检查 DATABASE_URL 环境变量
- **API密钥缺失**: 检查 ZHIPUAI_API_KEY
- **参数不匹配**: 检查 context 参数的字典格式

### Q4: 查询成功但没有日志记录

**原因**: 错误追踪模块可能未正确导入

**解决方案**:
```bash
# 检查错误追踪模块
cd C:\data_agent\Agent
python -c "from error_tracker import error_tracker; print(error_tracker.log_file)"
```

手动测试错误追踪：
```python
cd Agent
python

>>> from error_tracker import error_tracker
>>> error_tracker.log_success("测试问题", "测试回答", context={"test": True})
>>> # 检查 agent_success.jsonl 是否有新记录
```

---

## ✅ 验收标准

完成集成后，确认以下检查点：

### 功能验收

- [ ] **导入正确**: `from sql_agent import run_agent_with_tracking`
- [ ] **调用正确**: `result = await run_agent_with_tracking(...)`
- [ ] **参数完整**: 包含所有必需参数（question, database_url, thread_id等）
- [ ] **context正确**: 传递了上下文信息字典

### 运行验收

- [ ] **后端启动**: 无导入错误，服务正常启动
- [ ] **API可用**: `/api/v1/llm/query-with-agent` 端点可访问
- [ ] **日志记录**: 查询成功时记录到 `agent_success.jsonl`
- [ ] **错误记录**: 查询失败时记录到 `agent_errors.jsonl`

### 数据验收

查看日志文件内容：

```bash
cd C:\data_agent\Agent

# 成功日志示例
type agent_success.jsonl
# 应该包含：
# {"timestamp": "2025-01-06T...", "question": "...", "answer": "...", "context": {"source": "backend_api", ...}}

# 错误日志示例
type agent_errors.jsonl
# 应该包含：
# {"timestamp": "2025-01-06T...", "question": "...", "error_category": "...", "error_message": "...", ...}
```

---

## 📊 后续使用

### 查看质量报告

```bash
cd C:\data_agent\Agent

# 查看最近7天的质量报告
python -c "from error_tracker import error_tracker; print(error_tracker.generate_report(7))"

# 运行演示系统
python demo_qa_system.py
# 选择选项3 - 生成错误分析报告
```

### 日常监控建议

**每天**:
```bash
# 检查今日成功率
python -c "from error_tracker import error_tracker; stats = error_tracker.get_error_stats(1); print(f'今日成功率: {stats[\"success_rate\"]:.1f}%')"
```

**每周**:
```bash
# 运行完整测试套件
cd C:\data_agent\Agent
pytest tests/unit -v

# 生成周报
python demo_qa_system.py
# 选择选项3 - 生成错误分析报告
```

**每月**:
```bash
# 查看错误趋势
python -c "from error_tracker import error_tracker; print(error_tracker.generate_report(30))"

# 基于错误数据优化Prompt
# 查看Top错误类别，针对性优化
```

---

## 🔧 回滚方案

如果集成后出现问题，可以快速回滚：

### 回滚步骤

1. **恢复导入语句**:
   ```python
   from sql_agent import run_agent  # 改回原来的
   ```

2. **恢复函数调用**:
   ```python
   result = await run_agent(  # 去掉_with_tracking后缀
       question=enhanced_question,
       database_url=effective_db_url,
       thread_id=thread_id,
       enable_echarts=enable_echarts,
       verbose=verbose,
       db_type=db_type
       # 移除 context 参数
   )
   ```

3. **重启服务**:
   ```bash
   # Ctrl+C 停止当前服务
   uvicorn src.app.main:app --reload --port 8004
   ```

### Git回滚（如果使用版本控制）

```bash
cd C:\data_agent\backend
git checkout src/app/services/agent_service.py
```

---

## 📞 获取帮助

### 检查清单

如果遇到问题，按顺序检查：

1. [ ] Python语法是否正确（运行 `python -m py_compile 文件路径`）
2. [ ] 导入路径是否正确（`from Agent.sql_agent import run_agent_with_tracking`）
3. [ ] 函数签名是否匹配（检查参数顺序和类型）
4. [ ] 环境变量是否配置（DATABASE_URL, ZHIPUAI_API_KEY等）
5. [ ] 后端服务是否正常启动（访问 http://localhost:8004/health）

### 调试技巧

```python
# 在agent_service.py中添加调试日志
logger.info(f"🔍 [DEBUG] 调用 run_agent_with_tracking")
logger.info(f"🔍 [DEBUG] question: {enhanced_question[:100]}")
logger.info(f"🔍 [DEBUG] context: {context}")

result = await run_agent_with_tracking(...)

logger.info(f"🔍 [DEBUG] 返回结果: success={result.get('success')}")
```

### 联系方式

- 查看完整文档: `docs/QA/ai-analysis-qa-strategy.md`
- 快速指南: `docs/QA/quick-start-testing-guide.md`
- 验证清单: `docs/QA/ai-analysis-verification-checklist.md`

---

## 🎉 完成确认

完成以上所有步骤后，你已成功集成AI分析质量保证系统！

**最后验证**:

```bash
# 1. 运行测试
cd C:\data_agent\Agent
pytest tests/unit/test_golden_cases.py -v
# 应该看到: 18 passed ✓

# 2. 启动后端
cd C:\data_agent\backend
uvicorn src.app.main:app --reload --port 8004
# 应该看到: Application startup complete ✓

# 3. 测试API
curl -X POST "http://localhost:8004/api/v1/llm/query-with-agent" \
  -H "Content-Type: application/json" \
  -d '{"query": "测试问题", "tenant_id": "default", "user_id": "test"}'
# 应该得到正常响应 ✓

# 4. 检查日志
cd C:\data_agent\Agent
dir agent_success.jsonl agent_errors.jsonl
# 应该看到日志文件已创建/更新 ✓
```

---

**版本**: V1.0
**最后更新**: 2025-01-06
**维护者**: QA Team
