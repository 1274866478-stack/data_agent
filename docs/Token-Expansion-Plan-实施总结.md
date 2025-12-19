# Token Expansion Plan 实施总结

## 任务目标

提升 LLM 输出长度限制，将最大输出 Token 从 4096 提升至 **8192**，并同步调整超时设置以防止长文本生成导致请求断开。

## 已完成的修改

### 1. 配置文件更新 (`backend/src/app/core/config.py`)

#### 1.1 提升最大输出 Token 限制
```python
# 修改前
llm_max_output_tokens: int = 4096

# 修改后
llm_max_output_tokens: int = 8192  # LLM 最大输出 Token 数，设置为 8192 以确保完整的 ECharts JSON 配置输出
```

#### 1.2 增加 LLM 请求超时时间
```python
# 新增配置项
llm_timeout_seconds: int = 300  # LLM 请求超时时间（秒），设置为 300 秒（5分钟）以应对长文本生成
```

#### 1.3 更新各 LLM 提供商的超时配置
```python
# 智谱 AI
zhipuai_timeout: int = 300  # 从 120 秒增加到 300 秒（5分钟）

# OpenRouter
openrouter_timeout: int = 300  # 从 120 秒增加到 300 秒（5分钟）

# DeepSeek
deepseek_timeout: int = 300  # 从 120 秒增加到 300 秒（5分钟）
```

### 2. Agent 服务更新 (`backend/src/app/services/agent/agent_service.py`)

更新了 `create_llm()` 函数中所有 LLM 提供商的配置：

#### 2.1 智谱 AI (Zhipu)
```python
timeout=getattr(settings, "zhipuai_timeout", 300),  # 从 120 秒增加到 300 秒
max_tokens=getattr(settings, "llm_max_output_tokens", 8192),  # 从 4096 增加到 8192
```

#### 2.2 OpenRouter
```python
timeout=getattr(settings, "openrouter_timeout", 300),  # 从 120 秒增加到 300 秒
max_tokens=getattr(settings, "llm_max_output_tokens", 8192),  # 从 4096 增加到 8192
```

#### 2.3 DeepSeek
```python
timeout=getattr(settings, "deepseek_timeout", 300),  # 从 120 秒增加到 300 秒
max_tokens=getattr(settings, "llm_max_output_tokens", 8192),  # 从 4096 增加到 8192
```

### 3. LLM 服务更新 (`backend/src/app/services/llm_service.py`)

更新了默认 max_tokens 值：
```python
# 修改前
max_tokens = max_tokens or 4000

# 修改后
max_tokens = max_tokens or getattr(settings, "llm_max_output_tokens", 8192)
```

### 4. 智谱客户端更新 (`backend/src/app/services/zhipu_client.py`)

#### 4.1 更新初始化中的 max_tokens
```python
# 修改前
self.max_tokens = 4000

# 修改后
self.max_tokens = getattr(settings, "llm_max_output_tokens", 8192)
```

#### 4.2 更新复杂度分析中的默认值
```python
# 修改前
"recommend_max_tokens": 4000

# 修改后
"recommend_max_tokens": getattr(settings, "llm_max_output_tokens", 8192)
```

### 5. LLM API 端点更新 (`backend/src/app/api/v1/endpoints/llm.py`)

更新了复杂度分析相关的默认 max_tokens 值：
```python
# 修改前
max_tokens=complexity.get("recommend_max_tokens", 4000)
max_tokens=complexity_analysis.get("recommend_max_tokens", 6000)

# 修改后
max_tokens=complexity.get("recommend_max_tokens", getattr(settings, "llm_max_output_tokens", 8192))
max_tokens=complexity_analysis.get("recommend_max_tokens", getattr(settings, "llm_max_output_tokens", 8192))
```

## 修改文件清单

1. ✅ `backend/src/app/core/config.py` - 配置文件
2. ✅ `backend/src/app/services/agent/agent_service.py` - Agent 服务
3. ✅ `backend/src/app/services/llm_service.py` - LLM 服务
4. ✅ `backend/src/app/services/zhipu_client.py` - 智谱客户端
5. ✅ `backend/src/app/api/v1/endpoints/llm.py` - LLM API 端点

## 配置说明

### 环境变量支持

所有配置项都支持通过环境变量覆盖：

```bash
# 最大输出 Token 数（默认：8192）
LLM_MAX_OUTPUT_TOKENS=8192

# LLM 请求超时时间（默认：300 秒）
LLM_TIMEOUT_SECONDS=300

# 各提供商的超时时间（默认：300 秒）
ZHIPUAI_TIMEOUT=300
OPENROUTER_TIMEOUT=300
DEEPSEEK_TIMEOUT=300
```

### 配置优先级

1. 环境变量（最高优先级）
2. 配置文件中的默认值
3. 代码中的硬编码默认值（作为最后的回退）

## 影响范围

### 主要影响

1. **Agent 生成的 ECharts JSON 配置**：现在可以生成更长的 JSON 配置，不会被截断
2. **所有 LLM 请求**：默认支持更长的输出
3. **超时处理**：增加了超时时间，避免长文本生成时请求断开

### 性能考虑

- **Token 限制提升**：从 4096 到 8192，增加了 100% 的输出容量
- **超时时间增加**：从 120 秒到 300 秒，增加了 150% 的处理时间
- **成本影响**：更长的输出可能会增加 API 调用成本，但确保了完整输出

## 测试建议

### 1. 功能测试

测试 Agent 生成完整的 ECharts JSON 配置：
```python
# 测试用例：生成包含多个图表的复杂配置
question = "请生成包含柱状图、折线图和饼图的完整 ECharts 配置"
```

### 2. 超时测试

测试长文本生成是否在 300 秒内完成：
```python
# 测试用例：生成超长的分析报告
question = "请生成一份详细的数据分析报告，包含多个图表的配置"
```

### 3. 边界测试

测试不同长度的输出：
- 短输出（< 1000 tokens）
- 中等输出（1000-4000 tokens）
- 长输出（4000-8192 tokens）
- 超长输出（> 8192 tokens，应该被截断）

## 回退方案

如果遇到问题，可以通过环境变量快速回退：

```bash
# 回退到之前的配置
LLM_MAX_OUTPUT_TOKENS=4096
LLM_TIMEOUT_SECONDS=120
ZHIPUAI_TIMEOUT=120
OPENROUTER_TIMEOUT=120
DEEPSEEK_TIMEOUT=120
```

## 注意事项

1. **模型限制**：某些模型可能不支持 8192 tokens 的输出，会自动回退到模型的最大支持值
2. **API 成本**：更长的输出会增加 API 调用成本
3. **响应时间**：更长的输出需要更长的生成时间，超时时间已相应增加
4. **内存使用**：更长的输出可能会增加内存使用，但通常影响不大

## 后续优化建议

1. **动态调整**：根据查询复杂度动态调整 max_tokens
2. **流式输出**：对于超长输出，考虑使用流式输出以改善用户体验
3. **缓存机制**：对于重复的查询，使用缓存减少 API 调用
4. **监控告警**：监控 Token 使用情况和超时率，及时发现问题

## 完成时间

2025-01-XX

## 实施人员

AI Assistant

