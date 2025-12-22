## 1. 实现流式响应支持
- [ ] 1.1 修改 `AnswerGenerator._generate_main_answer` 方法，支持流式生成
- [ ] 1.2 创建新的 `AnswerGenerator._generate_main_answer_stream` 方法，使用流式LLM调用
- [ ] 1.3 更新 `ReasoningEngine.reason` 方法，支持流式模式参数

## 2. 更新API端点
- [ ] 2.1 修改 `/reasoning/reason` 端点，添加 `stream` 参数支持
- [ ] 2.2 当 `stream=True` 时，返回 `StreamingResponse` 而不是 `ReasoningResponse`
- [ ] 2.3 重构 `/reasoning/stream` 端点，使用真正的流式LLM调用
- [ ] 2.4 确保流式响应包含推理步骤、置信度等元数据

## 3. 流式响应格式
- [ ] 3.1 定义流式响应的事件类型（start, content, reasoning_step, complete, error）
- [ ] 3.2 实现SSE (Server-Sent Events) 格式的响应
- [ ] 3.3 确保每个chunk都包含必要的元数据

## 4. 测试和验证
- [ ] 4.1 测试流式响应的基本功能
- [ ] 4.2 测试与推理步骤的集成
- [ ] 4.3 测试错误处理和连接中断
- [ ] 4.4 验证向后兼容性（非流式模式仍然工作）

