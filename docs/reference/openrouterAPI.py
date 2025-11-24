"""
OpenRouter API调用示例
注意：此文件仅用于演示，实际使用请通过环境变量配置API密钥
"""

import os
from openai import OpenAI

# 安全的API密钥获取方式
def get_openrouter_client():
    """获取OpenRouter客户端，API密钥从环境变量读取"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY环境变量未设置")

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

def example_multimodal_chat():
    """多模态聊天示例"""
    try:
        client = get_openrouter_client()

        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": os.getenv("SITE_URL", ""),  # 可选：用于openrouter.ai排名
                "X-Title": os.getenv("SITE_NAME", "Data Agent"),  # 可选：网站标题
            },
            model="google/gemini-2.5-flash",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What is in this image, audio and video?"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
                            }
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB",
                                "format": "wav"
                            }
                        },
                        {
                            "type": "video_url",
                            "video_url": {
                                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                            }
                        }
                    ]
                }
            ]
        )
        print(completion.choices[0].message.content)
    except Exception as e:
        print(f"调用失败: {e}")


if __name__ == "__main__":
    example_multimodal_chat()