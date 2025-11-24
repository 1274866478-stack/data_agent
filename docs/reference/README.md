# API参考示例

此目录包含从项目根目录移动的API示例文件，已修复安全问题并作为参考保留。

## 文件说明

- **openrouterAPI.py** - OpenRouter多模态API调用示例
- **zhipu_stream_example.py** - 智谱AI流式调用完整实现示例
- **GLM_API.py** - 智谱API调用方式和示例

## 安全说明

所有示例文件已修复硬编码API密钥问题：
- 移除了所有硬编码的API密钥
- 改为从环境变量读取敏感信息
- 添加了适当的错误处理

## 使用方式

```bash
# 设置环境变量
export ZHIPUAI_API_KEY="your_api_key_here"
export OPENROUTER_API_KEY="your_api_key_here"

# 运行示例
python openrouterAPI.py
python zhipu_stream_example.py
python GLM_API.py
```

**注意**: 这些文件仅用于学习和参考，实际项目集成请使用 `src/app/services/` 下的服务。