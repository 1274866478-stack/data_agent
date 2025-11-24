"""
智谱AI GLM-4.6 流式调用示例
支持流式输出和深度思考模式

注意：此文件仅用于演示，实际使用请通过环境变量配置API密钥
"""

import os
import sys
from zhipuai import ZhipuAI


def get_zhipu_client():
    """获取智谱AI客户端，API密钥从环境变量读取"""
    api_key = os.getenv("ZHIPUAI_API_KEY")
    if not api_key:
        raise ValueError("ZHIPUAI_API_KEY环境变量未设置")
    return ZhipuAI(api_key=api_key)


class ZhipuStreamClient:
    """智谱AI流式调用客户端封装"""

    def __init__(self, api_key: str = None):
        """
        初始化客户端

        Args:
            api_key: 智谱AI的API密钥，如果不提供则从环境变量读取
        """
        if api_key is None:
            api_key = os.getenv("ZHIPUAI_API_KEY")
            if not api_key:
                raise ValueError("ZHIPUAI_API_KEY环境变量未设置")
        self.client = ZhipuAI(api_key=api_key)
    
    def stream_chat(
        self,
        messages: list,
        model: str = "glm-4-flash",
        enable_thinking: bool = False,
        max_tokens: int = 65536,
        temperature: float = 1.0,
        show_thinking: bool = True
    ):
        """
        流式对话调用
        
        Args:
            messages: 对话消息列表
            model: 模型名称，默认 glm-4-flash
            enable_thinking: 是否启用深度思考模式
            max_tokens: 最大输出tokens
            temperature: 温度参数，控制输出随机性 (0-1)
            show_thinking: 是否显示思考过程
            
        Yields:
            流式输出的文本内容
        """
        # 构建请求参数
        params = {
            "model": model,
            "messages": messages,
            "stream": True,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # 如果启用思考模式，添加thinking参数
        if enable_thinking:
            params["thinking"] = {"type": "enabled"}
        
        try:
            # 发起流式请求
            response = self.client.chat.completions.create(**params)
            
            # 处理流式响应
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    
                    # 输出思考过程（如果有）
                    if show_thinking and hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        yield {
                            'type': 'thinking',
                            'content': delta.reasoning_content
                        }
                    
                    # 输出正式回复内容
                    if hasattr(delta, 'content') and delta.content:
                        yield {
                            'type': 'content',
                            'content': delta.content
                        }
                        
        except Exception as e:
            yield {
                'type': 'error',
                'content': f"调用出错: {str(e)}"
            }


def example_simple_chat():
    """示例1: 简单的流式对话"""
    print("=" * 60)
    print("示例1: 简单流式对话")
    print("=" * 60)

    # 初始化客户端（从环境变量读取API Key）
    client = ZhipuStreamClient()
    
    # 构建对话消息
    messages = [
        {"role": "user", "content": "请用一句话介绍Python编程语言"}
    ]
    
    # 流式获取回复
    print("\n助手回复: ", end='', flush=True)
    for chunk in client.stream_chat(messages, enable_thinking=False):
        if chunk['type'] == 'content':
            print(chunk['content'], end='', flush=True)
        elif chunk['type'] == 'error':
            print(f"\n错误: {chunk['content']}")
    print("\n")


def example_thinking_mode():
    """示例2: 启用深度思考模式的流式对话"""
    print("=" * 60)
    print("示例2: 深度思考模式")
    print("=" * 60)

    client = ZhipuStreamClient()
    
    messages = [
        {"role": "user", "content": "作为一名营销专家，请为我的产品创作一个吸引人的口号"},
        {"role": "assistant", "content": "当然，要创作一个吸引人的口号，请告诉我一些关于您产品的信息"},
        {"role": "user", "content": "智谱AI开放平台"}
    ]
    
    print("\n[思考过程]: ", end='', flush=True)
    thinking_started = False
    content_started = False
    
    for chunk in client.stream_chat(messages, enable_thinking=True, show_thinking=True):
        if chunk['type'] == 'thinking':
            if not thinking_started:
                thinking_started = True
            print(chunk['content'], end='', flush=True)
        elif chunk['type'] == 'content':
            if not content_started:
                print("\n\n[正式回复]: ", end='', flush=True)
                content_started = True
            print(chunk['content'], end='', flush=True)
        elif chunk['type'] == 'error':
            print(f"\n错误: {chunk['content']}")
    print("\n")


def example_multi_turn_chat():
    """示例3: 多轮对话"""
    print("=" * 60)
    print("示例3: 多轮对话")
    print("=" * 60)

    client = ZhipuStreamClient()
    
    # 维护对话历史
    messages = []
    
    # 第一轮对话
    messages.append({"role": "user", "content": "什么是机器学习？"})
    print("\n用户: 什么是机器学习？")
    print("助手: ", end='', flush=True)
    
    assistant_reply = ""
    for chunk in client.stream_chat(messages, enable_thinking=False):
        if chunk['type'] == 'content':
            content = chunk['content']
            assistant_reply += content
            print(content, end='', flush=True)
    
    messages.append({"role": "assistant", "content": assistant_reply})
    
    # 第二轮对话
    print("\n\n用户: 能举个例子吗？")
    messages.append({"role": "user", "content": "能举个例子吗？"})
    print("助手: ", end='', flush=True)
    
    for chunk in client.stream_chat(messages, enable_thinking=False):
        if chunk['type'] == 'content':
            print(chunk['content'], end='', flush=True)
    
    print("\n")


if __name__ == "__main__":
    # 运行示例
    example_simple_chat()
    example_thinking_mode()
    example_multi_turn_chat()

