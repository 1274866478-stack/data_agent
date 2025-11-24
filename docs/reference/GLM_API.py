## zhipu API GLM-4.6 的调用方式
## 注意：使用环境变量 ZHIPUAI_API_KEY 设置API密钥
curl -X POST "https://open.bigmodel.cn/api/paas/v4/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ZHIPUAI_API_KEY" \
    -d '{
        "model": "glm-4.6",
        "messages": [
        {
            "role": "user",
            "content": "作为一名营销专家，请为我的产品创作一个吸引人的口号"
        },
        {
            "role": "assistant",
            "content": "当然，要创作一个吸引人的口号，请告诉我一些关于您产品的信息"
        },
        {
            "role": "user",
            "content": "智谱AI 开放平台"
        }
            ],
            "thinking": {
            "type": "enabled"
        },
            "max_tokens": 65536,
            "temperature": 1.0
        }'


import os
from zhipuai import ZhipuAI

def get_zhipu_client():
    """获取智谱AI客户端，API密钥从环境变量读取"""
    api_key = os.getenv("ZHIPUAI_API_KEY")
    if not api_key:
        raise ValueError("ZHIPUAI_API_KEY环境变量未设置")
    return ZhipuAI(api_key=api_key)

# 使用示例
client = get_zhipu_client()  # API密钥从环境变量自动读取

response = client.chat.completions.create(
    model="glm-4.6",
    messages=[
        {"role": "user", "content": "作为一名营销专家，请为我的产品创作一个吸引人的口号"},
        {"role": "assistant", "content": "当然，要创作一个吸引人的口号，请告诉我一些关于您产品的信息"},
        {"role": "user", "content": "智谱AI开放平台"}
    ],
    thinking={
        "type": "enabled",    # 启用深度思考模式
    },
    stream=True,              # 启用流式输出
    max_tokens=65536,          # 最大输出tokens
    temperature=1.0           # 控制输出的随机性
)

# 流式获取回复
for chunk in response:
if chunk.choices[0].delta.reasoning_content:
print(chunk.choices[0].delta.reasoning_content, end='', flush=True)

if chunk.choices[0].delta.content:
print(chunk.choices[0].delta.content, end='', flush=True)