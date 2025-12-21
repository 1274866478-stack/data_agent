# Change: 修复AI幻觉检测在响应转换时失效问题

## Why

虽然我们已经在`agent_service.py`中实现了幻觉检测逻辑，但AI仍然返回假数据（如"张三"、"李四"、"王五"、"赵六"）。

**根本原因分析**：
1. **响应转换时未检查幻觉标志** - `convert_agent_response_to_query_response`函数直接使用`agent_response.answer`，没有检查`metadata.hallucination_detected`标志
2. **检测逻辑可能执行时机不对** - 检测逻辑在流式输出完成后执行，但此时假数据可能已经生成
3. **VisualizationResponse对象未正确设置** - 即使设置了`cleaned_content`，但`VisualizationResponse.answer`可能仍包含原始假数据
4. **检测条件可能过于严格** - 检测逻辑可能因为某些条件未满足而跳过执行

这是一个严重的数据准确性问题，需要从根本上解决响应转换流程，确保幻觉检测结果能正确应用到最终响应中。

## What Changes

### 优先级1：修复响应转换逻辑
- 在`convert_agent_response_to_query_response`函数中检查`metadata.hallucination_detected`标志
- 如果检测到幻觉，强制使用错误消息替换`explanation`字段
- 确保`VisualizationResponse.answer`字段正确设置为拦截后的错误消息

### 优先级2：修复检测逻辑执行时机
- 确保检测逻辑在流式输出完成后立即执行
- 在检测到幻觉时，立即更新`final_content`和`cleaned_content`
- 确保`VisualizationResponse`对象使用拦截后的内容

### 优先级3：增强检测条件
- 放宽检测逻辑的执行条件，确保即使工具调用验证失败也会执行
- 改进检测模式匹配，确保能检测到所有假数据模式
- 添加更详细的日志，帮助诊断为什么检测没有生效

### 优先级4：在响应转换时强制检查
- 在`convert_agent_response_to_query_response`中添加二次检查
- 即使`VisualizationResponse.answer`包含假数据，也要在转换时拦截
- 添加响应级别的幻觉检测作为最后一道防线

## Impact

- **受影响的功能**：AI助手查询功能、响应转换功能
- **受影响的代码**：
  - `backend/src/app/services/agent_service.py` - 响应转换函数（添加幻觉检查）
  - `backend/src/app/services/agent/agent_service.py` - Agent执行逻辑（修复检测时机）
  - `backend/src/app/api/v1/endpoints/query.py` - 查询端点（可能需要添加检查）
- **影响范围**：所有使用AI助手查询的场景
- **预期效果**：
  - 响应转换时强制检查幻觉标志
  - 即使检测逻辑有遗漏，响应转换时也能拦截
  - 用户永远不会收到包含假数据的响应

