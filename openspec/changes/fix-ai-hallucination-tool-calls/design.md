# 修复AI助手编造数据问题 - 技术设计

## Context

根据诊断报告，AI助手在回答"列出所有的用户"时返回了编造的假数据（用户1、用户2、用户3、用户4、用户5），而不是从数据库中查询的真实数据。

问题的根本原因是：
1. AI没有真正调用工具查询数据
2. 幻觉检测机制未正确触发或拦截
3. Prompt规则不够强制

## Goals / Non-Goals

### Goals
- 强制AI在生成数据前必须调用工具
- 改进幻觉检测逻辑，确保能正确检测和拦截假数据
- 增强错误处理，确保工具失败时不会生成假数据
- 提供清晰的错误消息给用户

### Non-Goals
- 不改变现有的工具接口
- 不改变现有的API接口
- 不改变现有的数据源连接机制

## Decisions

### Decision 1: 增强幻觉检测模式匹配

**问题**: 当前检测逻辑可能无法正确匹配"用户1"、"用户2"等编号模式。

**解决方案**: 
- 添加更精确的正则表达式来匹配编号模式
- 检测模式包括：
  - "用户1"、"用户2"等简单编号
  - "用户ID: 1"、"用户编号: 1"等带标签的编号
  - "- 用户1"、"* 用户1"等列表格式
  - 连续的编号列表（如"用户1、用户2、用户3"）

**实现位置**: `backend/src/app/services/agent/agent_service.py` (第1360-1448行)

**代码示例**:
```python
# 检测编号模式
numbered_pattern = r'用户[1-9]\d*|用户ID:\s*\d+|用户编号:\s*\d+'
has_numbered_list = bool(re.search(numbered_pattern, final_content))
```

### Decision 2: 强制工具调用验证

**问题**: AI可能跳过工具调用步骤，直接生成答案。

**解决方案**:
- 在Agent执行后，验证是否调用了必要工具
- 对于文件数据源，必须调用`inspect_file`和`analyze_dataframe`
- 对于SQL数据源，必须调用`query`或`execute_sql_safe`
- 如果没有调用必要工具，强制拦截并返回错误消息

**实现位置**: `backend/src/app/services/agent/agent_service.py` (在`run_agent`函数中，收集消息后)

**验证逻辑**:
```python
def verify_tool_calls(all_messages, data_source_type):
    """验证是否调用了必要工具"""
    tool_calls = extract_tool_calls(all_messages)
    
    if data_source_type == "file":
        required_tools = ["inspect_file", "analyze_dataframe"]
        if not all(tool in tool_calls for tool in required_tools):
            return False, "文件数据源必须调用inspect_file和analyze_dataframe工具"
    
    elif data_source_type == "sql":
        required_tools = ["query", "execute_sql_safe"]
        if not any(tool in tool_calls for tool in required_tools):
            return False, "SQL数据源必须调用query或execute_sql_safe工具"
    
    return True, None
```

### Decision 3: 增强Prompt规则

**问题**: 当前Prompt规则可能不够强制，LLM可能选择忽略。

**解决方案**:
- 在System Prompt开头添加最严格的规则
- 使用更强烈的警告语言
- 添加few-shot示例展示正确行为
- 明确禁止在没有调用工具的情况下生成数据

**实现位置**: `backend/src/app/services/agent/prompts.py` (在`get_system_prompt`函数开头)

**示例规则**:
```python
prompt = f"""
🚨🚨🚨 绝对禁止规则（违反将导致回答被系统自动拦截）🚨🚨🚨

1. **禁止在没有调用工具的情况下生成任何具体数据**
   - 如果问题涉及数据查询，必须先调用工具
   - 如果未调用工具，系统将自动拦截你的回答

2. **禁止使用示例数据或编造数据**
   - 必须使用工具返回的真实数据
   - 禁止使用"用户1"、"用户2"、"Alice"、"Bob"等测试数据

3. **工具调用失败时必须明确告知**
   - 如果工具返回错误，必须明确说明
   - 禁止基于错误信息推测或编造数据

{existing_prompt}
"""
```

### Decision 4: 改进错误处理

**问题**: 当工具返回"SYSTEM ERROR"时，AI可能仍然生成答案。

**解决方案**:
- 在检测到"SYSTEM ERROR"时，强制AI停止生成答案
- 返回用户友好的错误消息
- 提供明确的错误原因和解决建议

**实现位置**: 
- `backend/src/app/services/agent/tools.py` (工具返回错误时)
- `backend/src/app/services/agent/agent_service.py` (处理工具返回时)

## Risks / Trade-offs

### Risk 1: 过度拦截
**风险**: 改进后的检测逻辑可能过于严格，导致正常回答被误拦截。

**缓解措施**:
- 仔细设计检测模式，避免误报
- 添加白名单机制，允许某些已知的正常模式
- 记录所有拦截事件，便于分析和调整

### Risk 2: 性能影响
**风险**: 增加工具调用验证和幻觉检测可能影响性能。

**缓解措施**:
- 验证逻辑应该轻量级，只检查必要信息
- 使用缓存机制减少重复检查
- 监控性能指标，必要时优化

### Risk 3: 用户体验
**风险**: 过于严格的验证可能导致用户收到过多错误消息。

**缓解措施**:
- 提供清晰的错误消息和解决建议
- 区分不同类型的错误（工具调用失败 vs 数据不存在）
- 提供友好的错误提示

## Migration Plan

### Phase 1: 修复幻觉检测（优先级1）
1. 改进编号模式检测逻辑
2. 测试检测准确性
3. 验证拦截机制

### Phase 2: 强制工具调用验证（优先级2）
1. 实现工具调用验证函数
2. 在Agent执行后添加验证
3. 测试验证逻辑

### Phase 3: 增强Prompt（优先级3）
1. 修改System Prompt
2. 添加few-shot示例
3. 测试Prompt效果

### Phase 4: 改进错误处理（优先级4）
1. 增强工具错误处理
2. 改进错误消息
3. 测试错误处理

### Phase 5: 增强日志和监控（优先级5）
1. 添加详细日志
2. 添加监控指标
3. 测试日志记录

### Rollback Plan
如果修复导致问题：
1. 回滚代码更改
2. 恢复原始检测逻辑
3. 分析问题原因
4. 重新设计修复方案

## Open Questions

1. **检测模式是否需要可配置？**
   - 当前：硬编码检测模式
   - 备选：通过配置文件管理检测模式
   - **决策**: 先使用硬编码，如果后续需要频繁调整，再改为配置化

2. **是否需要用户反馈机制？**
   - 当前：自动拦截
   - 备选：允许用户报告误拦截
   - **决策**: 先实现自动拦截，后续根据用户反馈决定是否需要反馈机制

3. **错误消息的详细程度？**
   - 当前：提供基本错误信息
   - 备选：提供详细的诊断信息
   - **决策**: 提供清晰的错误信息和解决建议，但不暴露技术细节

