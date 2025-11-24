"""
LLM服务集成示例
展示如何使用统一的LLM服务进行各种操作
"""

import asyncio
from typing import List, Dict, Any

from ..services.llm_service import (
    llm_service,
    LLMProvider,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk
)


async def example_zhipu_chat():
    """示例：使用智谱AI进行普通对话"""
    print("=== 智谱AI普通对话示例 ===")

    # 注册提供商（在实际应用中，这会在应用启动时完成）
    llm_service.register_provider(
        tenant_id="demo_tenant",
        provider=LLMProvider.ZHIPU,
        api_key="your_zhipu_api_key_here"
    )

    # 创建对话消息
    messages = [
        LLMMessage(role="user", content="你好！请用一句话介绍人工智能。")
    ]

    try:
        # 调用聊天完成
        response: LLMResponse = await llm_service.chat_completion(
            tenant_id="demo_tenant",
            messages=messages,
            provider=LLMProvider.ZHIPU,
            model="glm-4-flash",
            max_tokens=100,
            temperature=0.7
        )

        print(f"AI回复: {response.content}")
        print(f"使用模型: {response.model}")
        print(f"Token使用: {response.usage}")
        print(f"提供商: {response.provider}")

    except Exception as e:
        print(f"错误: {e}")


async def example_zhipu_thinking_mode():
    """示例：使用智谱AI深度思考模式"""
    print("\n=== 智谱AI深度思考模式示例 ===")

    # 创建复杂问题的对话
    messages = [
        LLMMessage(role="user", content="作为一名营销专家，请为我们的AI数据分析产品设计一个吸引人的口号"),
        LLMMessage(role="assistant", content="当然可以。为了设计一个吸引人的口号，我需要了解一些关于您产品的具体信息。"),
        LLMMessage(role="user", content="我们的产品是一个智能数据分析平台，帮助企业从海量数据中发现商业洞察，支持可视化报表和预测分析。")
    ]

    try:
        # 启用深度思考模式
        response: LLMResponse = await llm_service.chat_completion(
            tenant_id="demo_tenant",
            messages=messages,
            provider=LLMProvider.ZHIPU,
            model="glm-4.6",
            enable_thinking=True,  # 启用思考模式
            max_tokens=300,
            temperature=0.8
        )

        if response.thinking:
            print(f"[思考过程]: {response.thinking}")
        print(f"[正式回复]: {response.content}")

    except Exception as e:
        print(f"错误: {e}")


async def example_zhipu_streaming():
    """示例：使用智谱AI流式输出"""
    print("\n=== 智谱AI流式输出示例 ===")

    messages = [
        LLMMessage(role="user", content="请写一首关于春天的短诗")
    ]

    try:
        # 流式聊天完成
        stream_generator = await llm_service.chat_completion(
            tenant_id="demo_tenant",
            messages=messages,
            provider=LLMProvider.ZHIPU,
            model="glm-4-flash",
            stream=True,
            enable_thinking=True
        )

        print("AI回复（流式）: ", end="", flush=True)
        thinking_content = ""
        main_content = ""

        async for chunk in stream_generator:
            if chunk.type == "thinking":
                thinking_content += chunk.content
                print(f"\n[思考]: {chunk.content}", end="", flush=True)
            elif chunk.type == "content":
                main_content += chunk.content
                print(chunk.content, end="", flush=True)
            elif chunk.type == "error":
                print(f"\n错误: {chunk.content}")
                break

        print("\n")

    except Exception as e:
        print(f"错误: {e}")


async def example_openrouter_multimodal():
    """示例：使用OpenRouter进行多模态对话"""
    print("\n=== OpenRouter多模态示例 ===")

    # 注册OpenRouter提供商
    llm_service.register_provider(
        tenant_id="demo_tenant",
        provider=LLMProvider.OPENROUTER,
        api_key="your_openrouter_api_key_here"
    )

    # 创建多模态消息
    multimodal_content = [
        {"type": "text", "text": "请描述这张图片中的内容"},
        {
            "type": "image_url",
            "image_url": {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
            }
        }
    ]

    messages = [
        LLMMessage(role="user", content=multimodal_content)
    ]

    try:
        # 使用OpenRouter的多模态模型
        response: LLMResponse = await llm_service.chat_completion(
            tenant_id="demo_tenant",
            messages=messages,
            provider=LLMProvider.OPENROUTER,
            model="google/gemini-2.0-flash-exp",
            max_tokens=200,
            temperature=0.7
        )

        print(f"图片描述: {response.content}")
        print(f"使用模型: {response.model}")
        print(f"提供商: {response.provider}")

    except Exception as e:
        print(f"错误: {e}")


async def example_auto_provider_selection():
    """示例：自动选择可用的提供商"""
    print("\n=== 自动提供商选择示例 ===")

    messages = [
        LLMMessage(role="user", content="简单介绍一下机器学习")
    ]

    try:
        # 不指定提供商，让系统自动选择
        response: LLMResponse = await llm_service.chat_completion(
            tenant_id="demo_tenant",
            messages=messages,
            # 不指定provider，系统会自动选择可用的提供商
            max_tokens=150,
            temperature=0.7
        )

        print(f"AI回复: {response.content}")
        print(f"系统选择的提供商: {response.provider}")
        print(f"使用模型: {response.model}")

    except Exception as e:
        print(f"错误: {e}")


async def example_provider_status_check():
    """示例：检查提供商状态"""
    print("\n=== 提供商状态检查示例 ===")

    try:
        # 验证所有提供商连接状态
        status = await llm_service.validate_providers("demo_tenant")

        print("提供商连接状态:")
        for provider, is_available in status.items():
            status_text = "✅ 可用" if is_available else "❌ 不可用"
            print(f"  {provider}: {status_text}")

        # 获取可用模型
        models = await llm_service.get_available_models("demo_tenant")

        print("\n可用模型:")
        for provider, model_list in models.items():
            print(f"  {provider}:")
            for model in model_list:
                print(f"    - {model}")

    except Exception as e:
        print(f"错误: {e}")


async def example_multi_turn_conversation():
    """示例：多轮对话"""
    print("\n=== 多轮对话示例 ===")

    # 维护对话历史
    conversation_history = [
        LLMMessage(role="user", content="什么是机器学习？")
    ]

    try:
        # 第一轮对话
        print("用户: 什么是机器学习？")
        response1: LLMResponse = await llm_service.chat_completion(
            tenant_id="demo_tenant",
            messages=conversation_history,
            provider=LLMProvider.ZHIPU,
            max_tokens=200
        )

        print(f"助手: {response1.content}")

        # 将助手回复添加到对话历史
        conversation_history.append(
            LLMMessage(role="assistant", content=response1.content)
        )

        # 第二轮对话
        user_input = "能给我一个具体的例子吗？"
        conversation_history.append(
            LLMMessage(role="user", content=user_input)
        )

        print(f"\n用户: {user_input}")
        response2: LLMResponse = await llm_service.chat_completion(
            tenant_id="demo_tenant",
            messages=conversation_history,
            provider=LLMProvider.ZHIPU,
            max_tokens=200
        )

        print(f"助手: {response2.content}")

        # 显示对话统计
        total_tokens = (response1.usage.get("total_tokens", 0) +
                       response2.usage.get("total_tokens", 0))
        print(f"\n对话统计: 总共使用了 {total_tokens} 个tokens")

    except Exception as e:
        print(f"错误: {e}")


async def main():
    """运行所有示例"""
    print("🚀 LLM服务集成示例开始\n")

    # 运行各种示例
    await example_zhipu_chat()
    await example_zhipu_thinking_mode()
    await example_zhipu_streaming()
    await example_openrouter_multimodal()
    await example_auto_provider_selection()
    await example_provider_status_check()
    await example_multi_turn_conversation()

    print("\n✅ 所有示例运行完成")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())