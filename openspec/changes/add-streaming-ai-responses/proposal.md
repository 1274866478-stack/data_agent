# Change: 添加AI助手流式响应支持

## Why
当前AI助手的回答是等待完整生成后才返回，用户体验不够流畅。实现流式响应可以让用户实时看到AI生成的内容，提升交互体验和响应感知。

## What Changes
- 修改 `AnswerGenerator` 类，支持流式生成答案
- 更新 `/reasoning/reason` 端点，支持流式响应模式
- 更新 `/reasoning/stream` 端点，使用真正的流式LLM调用而不是模拟
- 确保流式响应与现有功能（推理步骤、数据源引用等）兼容
- 保持向后兼容，非流式模式仍然可用

## Impact
- 受影响的功能：推理服务 (`reasoning_service.py`)、推理API端点 (`reasoning.py`)
- 受影响的代码：
  - `backend/src/app/services/reasoning_service.py` - AnswerGenerator类
  - `backend/src/app/api/v1/endpoints/reasoning.py` - reason_query和stream_reasoning端点
- 用户体验：显著提升，响应更及时
- 性能：可能略微增加服务器资源使用（保持连接），但用户体验提升明显

