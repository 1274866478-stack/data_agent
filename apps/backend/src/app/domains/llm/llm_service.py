"""
# [LLM_SERVICE] 统一LLM服务

## [HEADER]
**文件名**: llm_service.py
**职责**: 提供统一的多提供商LLM服务接口，支持DeepSeek、智谱AI和OpenRouter，实现租户隔离、流式输出、多模态处理和智能参数调整
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 实现多提供商LLM服务架构

## [INPUT]
- **tenant_id: str** - 租户ID（用于提供商注册和隔离）
- **messages: List[LLMMessage]** - 对话消息列表
  - role: 消息角色 ("user", "assistant", "system", "tool")
  - content: 消息内容（字符串或多模态列表）
  - tool_calls: 工具调用（assistant角色）
  - tool_call_id: 工具调用ID（tool角色）
- **provider: Optional[LLMProvider]** - LLM提供商（默认自动选择）
- **model: Optional[str]** - 模型名称（默认各提供商默认模型）
- **max_tokens: Optional[int]** - 最大输出tokens
- **temperature: Optional[float]** - 温度参数（0.0-1.0）
- **stream: bool** - 是否流式输出
- **enable_thinking: Optional[bool]** - 是否启用思考模式（None表示智能判断）
- **tools: Optional[List[Dict[str, Any]]]** - 工具定义列表（DeepSeek）

## [OUTPUT]
- **LLMResponse**: 非流式响应
  - content: str - 回复内容
  - thinking: Optional[str] - 思考过程（智谱AI）
  - usage: Optional[Dict[str, int]] - token使用统计
  - model: str - 使用的模型
  - provider: str - 提供商名称
  - finish_reason: str - 结束原因
  - created_at: str - 创建时间（ISO格式）
- **AsyncGenerator[LLMStreamChunk]**: 流式响应
  - type: str - 块类型 ("thinking", "content", "tool_input", "done", "error")
  - content: str - 内容
  - provider: str - 提供商
  - finished: bool - 是否完成

**上游依赖** (已读取源码):
- [./core/config.py](./core/config.py) - 配置管理（API keys、模型默认值）
- [./multimodal_processor.py](./multimodal_processor.py) - 多模态内容处理器

**下游依赖** (需要反向索引分析):
- [../api/v1/endpoints/llm.py](../api/v1/endpoints/llm.py) - LLM API端点
- [../api/v1/endpoints/query.py](../api/v1/endpoints/query.py) - 查询API端点
- [../services/xai_service.py](../services/xai_service.py) - XAI服务（可能调用）

**调用方**:
- [../api/v1/endpoints/llm.py](../api/v1/endpoints/llm.py) - LLM API端点
- [../services/conversation_service.py](../services/conversation_service.py) - 对话服务
- [../services/agent_service.py](../services/agent_service.py) - Agent服务

## [STATE]
- **提供商管理**: providers字典维护租户和提供商的实例映射
- **租户配置**: tenant_configs字典维护租户API密钥
- **提供商优先级**: DeepSeek → Zhipu → OpenRouter（默认回退）
- **智能模式**:
  - 思考模式自动判断（ZhipuProvider.should_enable_thinking）
  - 对话复杂度分析（analyze_conversation_complexity）
- **多模态支持**: 图片、音频、视频内容处理（OpenRouter）

## [SIDE-EFFECTS]
- **HTTP请求**: 调用DeepSeek、智谱AI、OpenRouter的REST API
- **流式响应**: 异步生成器yield流式数据块
- **缓存**: 智能思考模式判断（基于关键词和复杂度）
- **多模态处理**: 调用multimodal_processor处理非文本内容
- **日志记录**: 详细记录流式响应、工具调用、错误信息

## [POS]
**路径**: backend/src/app/domains/llm_service.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 直接依赖 core.config 和 multimodal_processor
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass

from openai import AsyncOpenAI
from zhipuai import ZhipuAI

from src.app.core.config import settings
from src.app.domains.llm.multimodal import multimodal_processor

logger = logging.getLogger(__name__)

# 🔧 并发控制：智谱 API 全局信号量（防止 429 并发限制错误）
# 限制同时最多 3 个并发请求到智谱 API
_ZHIPU_SEMAPHORE = asyncio.Semaphore(3)

# 🔧 重试配置：429 错误自动重试
_MAX_RETRIES = 3
_RETRY_DELAY = 1.0  # 秒


class LLMProvider(Enum):
    """LLM提供商枚举"""
    DEEPSEEK = "deepseek"
    ZHIPU = "zhipu"
    OPENROUTER = "openrouter"


@dataclass
class LLMMessage:
    """LLM消息结构"""
    role: str  # "user", "assistant", "system", "tool"
    content: Union[str, List[Dict[str, Any]]]  # 支持多模态内容
    thinking: Optional[str] = None  # 思考过程
    tool_calls: Optional[List[Dict[str, Any]]] = None  # 工具调用（assistant角色）
    tool_call_id: Optional[str] = None  # 工具调用ID（tool角色）


@dataclass
class LLMResponse:
    """LLM响应结构"""
    content: str
    thinking: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    finish_reason: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class LLMStreamChunk:
    """LLM流式响应块"""
    type: str  # "thinking", "content", "error"
    content: str
    provider: Optional[str] = None
    finished: bool = False


class BaseLLMProvider(ABC):
    """LLM提供商基类"""

    def __init__(self, api_key: str, tenant_id: str):
        self.api_key = api_key
        self.tenant_id = tenant_id

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMStreamChunk, None]]:
        """聊天完成接口"""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """验证连接"""
        pass


class ZhipuProvider(BaseLLMProvider):
    """智谱AI提供商"""

    def __init__(self, api_key: str, tenant_id: str):
        super().__init__(api_key, tenant_id)
        self.client = ZhipuAI(api_key=api_key)
        self.default_model = getattr(settings, 'zhipuai_default_model', 'glm-4.6')
        self.thinking_indicators = [
            "分析", "比较", "评估", "解释", "设计", "规划",
            "为什么", "如何", "原因", "影响", "建议", "步骤",
            "原理", "机制", "策略", "方案", "优缺点"
        ]

    def should_enable_thinking(self, messages: List[LLMMessage]) -> bool:
        """
        智能判断是否启用思考模式

        🔥 修改说明：所有数据查询类问题默认启用思考模式，确保深入分析

        Args:
            messages: 对话消息列表

        Returns:
            bool: 是否建议启用思考模式（默认True）
        """
        try:
            # 获取用户消息内容
            user_content = ""
            for msg in messages:
                if msg.role == "user":
                    if isinstance(msg.content, str):
                        user_content += msg.content + " "
                    elif isinstance(msg.content, list):
                        for item in msg.content:
                            if item.get("type") == "text":
                                user_content += item.get("text", "") + " "

            user_content = user_content.strip()
            if not user_content:
                return False

            # 🆕 数据查询关键词检测（用于判断是否是数据查询类问题）
            data_query_keywords = [
                '数据', '查询', '统计', '多少', '数量', '列表', '显示',
                '销售', '订单', '客户', '收入', '利润', '金额',
                '最近', '今天', '昨天', '本月', '上月'
            ]

            content_lower = user_content.lower()

            # ✅ 如果是数据查询类问题，直接启用思考模式
            if any(kw in content_lower for kw in data_query_keywords):
                logger.info(f"检测到数据查询类问题，启用思考模式: {user_content[:50]}")
                return True

            # ✅ 包含思考指示词，启用思考模式
            for indicator in self.thinking_indicators:
                if indicator in content_lower:
                    logger.debug(f"检测到思考模式指示词: {indicator}")
                    return True

            # ✅ 问题较长或复杂，启用思考模式
            if len(user_content) > 200:
                return True
            if "？" in user_content or user_content.count("?") > 1:
                return True
            if "步骤" in user_content or "详细" in user_content:
                return True

            # 🆕 默认启用思考模式（确保所有问题都有深入分析）
            logger.info(f"默认启用思考模式: {user_content[:50]}")
            return True  # ✅ 关键修改：默认返回True

        except Exception as e:
            logger.warning(f"思考模式判断失败: {e}，默认启用")
            return True  # ✅ 出错时默认启用

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        enable_thinking: Optional[bool] = None,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMStreamChunk, None]]:
        """智谱AI聊天完成（带并发控制和重试机制）"""
        model = model or self.default_model
        max_tokens = max_tokens or getattr(settings, "llm_max_output_tokens", 8192)
        temperature = temperature if temperature is not None else 0.7

        # 智能思考模式判断
        if enable_thinking is None:
            enable_thinking = self.should_enable_thinking(messages)
            if enable_thinking:
                logger.info("智能启用思考模式")

        # 转换消息格式
        api_messages = []
        for msg in messages:
            api_msg = {"role": msg.role, "content": msg.content}
            api_messages.append(api_msg)

        # 构建请求参数
        params = {
            "model": model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }

        # 🔧 修复：思考模式(thinking参数)仅在流式模式下启用
        # 非流式模式下该参数会导致 [Errno 22] Invalid argument 错误
        if enable_thinking and stream:
            params["thinking"] = {"type": "enabled"}
            logger.debug(f"智谱AI启用思考模式(流式): {model}")
        elif enable_thinking and not stream:
            logger.info(f"思考模式仅在流式模式下支持，已禁用(model={model})")

        # 🔧 流式模式：返回包装的生成器（带信号量控制）
        if stream:
            return self._stream_with_retry(params, model)

        # 🔧 非流式模式：带重试的执行
        retry_count = 0
        last_error = None

        while retry_count <= _MAX_RETRIES:
            # 🔧 使用信号量限制并发
            async with _ZHIPU_SEMAPHORE:
                try:
                    logger.debug(f"[Zhipu] 获取信号量，尝试第 {retry_count + 1} 次调用")
                    response = self.client.chat.completions.create(**params)

                    return LLMResponse(
                        content=response.choices[0].message.content or "",
                        thinking=getattr(response.choices[0].message, 'reasoning_content', None),
                        usage={
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        } if response.usage else None,
                        model=response.model,
                        provider=LLMProvider.ZHIPU.value,
                        finish_reason=response.choices[0].finish_reason,
                        created_at=datetime.fromtimestamp(response.created).isoformat()
                    )

                except Exception as e:
                    last_error = e
                    error_str = str(e)

                    # 🔧 检查是否是 429 并发限制错误
                    is_rate_limit_error = (
                        "429" in error_str or
                        "并发数过高" in error_str or
                        "concurrent" in error_str.lower() or
                        "rate limit" in error_str.lower() or
                        ("error" in error_str.lower() and "1302" in error_str)
                    )

                    if is_rate_limit_error and retry_count < _MAX_RETRIES:
                        retry_count += 1
                        wait_time = _RETRY_DELAY * (2 ** (retry_count - 1))  # 指数退避
                        logger.warning(
                            f"[Zhipu] 检测到 429 并发限制错误，"
                            f"{wait_time} 秒后重试 ({retry_count}/{_MAX_RETRIES})"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # 非并发限制错误或重试次数用尽
                        logger.error(f"Zhipu chat completion failed: {e}")
                        raise

        # 所有重试都失败
        logger.error(f"[Zhipu] 所有重试都失败，最后错误: {last_error}")
        if last_error:
            raise last_error
        else:
            raise Exception("Zhipu API 调用失败：未知错误")

    async def _stream_with_retry(
        self,
        params: Dict[str, Any],
        model: str
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        流式响应（带信号量控制和重试机制）

        此方法会在获取信号量后执行流式响应，并在失败时自动重试
        """
        retry_count = 0
        last_error = None

        while retry_count <= _MAX_RETRIES:
            # 🔧 使用信号量限制并发
            async with _ZHIPU_SEMAPHORE:
                try:
                    logger.debug(f"[Zhipu Stream] 获取信号量，尝试第 {retry_count + 1} 次调用")

                    # 在信号量保护下执行流式响应
                    async for chunk in self._do_stream_response(params, model):
                        yield chunk

                    # 如果成功完成，退出重试循环
                    return

                except Exception as e:
                    last_error = e
                    error_str = str(e)

                    # 🔧 检查是否是 429 并发限制错误
                    is_rate_limit_error = (
                        "429" in error_str or
                        "并发数过高" in error_str or
                        "concurrent" in error_str.lower() or
                        "rate limit" in error_str.lower() or
                        ("error" in error_str.lower() and "1302" in error_str)
                    )

                    if is_rate_limit_error and retry_count < _MAX_RETRIES:
                        retry_count += 1
                        wait_time = _RETRY_DELAY * (2 ** (retry_count - 1))  # 指数退避
                        logger.warning(
                            f"[Zhipu Stream] 检测到 429 并发限制错误，"
                            f"{wait_time} 秒后重试 ({retry_count}/{_MAX_RETRIES})"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # 非并发限制错误或重试次数用尽
                        logger.error(f"[Zhipu Stream] 失败: {e}")
                        yield LLMStreamChunk(
                            type="error",
                            content=f"智谱AI流式响应错误: {str(e)}",
                            provider=LLMProvider.ZHIPU.value,
                            finished=True
                        )
                        return

        # 所有重试都失败
        logger.error(f"[Zhipu Stream] 所有重试都失败，最后错误: {last_error}")
        yield LLMStreamChunk(
            type="error",
            content=f"智谱AI调用失败：{str(last_error) if last_error else '未知错误'}",
            provider=LLMProvider.ZHIPU.value,
            finished=True
        )

    async def _do_stream_response(
        self,
        params: Dict[str, Any],
        model: str
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        实际执行流式响应（不包含信号量控制）

        注意：此方法应该在被信号量保护的情况下调用
        """
        stream_started = False
        thinking_phase = False
        content_phase = False

        try:
            logger.debug(f"[Zhipu] 开始流式响应: {model}")
            response = self.client.chat.completions.create(**params)

            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    stream_started = True

                    # 思考过程
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        if not thinking_phase:
                            thinking_phase = True
                            logger.debug("[Zhipu] 思考过程开始")

                        yield LLMStreamChunk(
                            type="thinking",
                            content=delta.reasoning_content,
                            provider=LLMProvider.ZHIPU.value,
                            finished=False
                        )

                    # 正式内容
                    elif hasattr(delta, 'content') and delta.content:
                        if not content_phase and thinking_phase:
                            content_phase = True
                            logger.debug("[Zhipu] 从思考过程切换到正式回复")

                        yield LLMStreamChunk(
                            type="content",
                            content=delta.content,
                            provider=LLMProvider.ZHIPU.value,
                            finished=False
                        )

            # 发送完成标记
            if stream_started:
                yield LLMStreamChunk(
                    type="content",
                    content="",
                    provider=LLMProvider.ZHIPU.value,
                    finished=True
                )
                logger.debug("[Zhipu] 流式响应完成")

        except Exception as e:
            logger.error(f"[Zhipu] 流式响应失败: {e}")
            raise

    async def validate_connection(self) -> bool:
        """验证智谱AI连接"""
        try:
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return bool(response and response.choices)
        except Exception as e:
            logger.error(f"Zhipu connection validation failed: {e}")
            return False


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek提供商（默认）"""

    def __init__(self, api_key: str, tenant_id: str, base_url: str = None, default_model: str = None):
        super().__init__(api_key, tenant_id)
        base_url = base_url or getattr(settings, 'deepseek_base_url', 'https://api.deepseek.com')
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key
        )
        self.default_model = default_model or getattr(settings, 'deepseek_default_model', 'deepseek-chat')

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMStreamChunk, None]]:
        """DeepSeek聊天完成"""
        try:
            model = model or self.default_model
            max_tokens = max_tokens or getattr(settings, "llm_max_output_tokens", 8192)
            temperature = temperature if temperature is not None else 0.7

            # 转换消息格式
            api_messages = []
            for msg in messages:
                # 兼容直接传入 dict 而不是 LLMMessage 的情况
                if isinstance(msg, dict):
                    role = msg.get("role")
                    # 🔧 修复：dict.get() 在键存在但值为 None 时会返回 None，需要额外处理
                    content_raw = msg.get("content")
                    if content_raw is None:
                        content_raw = ""  # 强制转换 None 为空字符串
                    # 处理工具调用消息
                    tool_calls = msg.get("tool_calls")
                    tool_call_id = msg.get("tool_call_id")
                else:
                    role = getattr(msg, "role", None)
                    # 🔧 修复：getattr() 在属性值为 None 时也会返回 None
                    content_raw = getattr(msg, "content", None)
                    if content_raw is None:
                        content_raw = ""  # 强制转换 None 为空字符串
                    tool_calls = getattr(msg, "tool_calls", None)
                    tool_call_id = getattr(msg, "tool_call_id", None)

                message_dict = {"role": role}
                
                # 处理工具调用消息
                if tool_calls:
                    message_dict["tool_calls"] = tool_calls
                if tool_call_id:
                    message_dict["tool_call_id"] = tool_call_id
                
                # 🔧 修复：处理 content 为 None 的情况
                # DeepSeek 有时会直接生成 tool_calls 而不生成文本，此时 content 为 None
                # 但 DeepSeek API 要求 content 字段必须是字符串，不能是 null
                if content_raw is None:
                    # 如果是 assistant 角色且有 tool_calls，content 可以为空字符串
                    message_dict["content"] = ""
                elif isinstance(content_raw, str):
                    message_dict["content"] = content_raw
                elif isinstance(content_raw, list):
                    # 多模态内容处理
                    content = []
                    for item in content_raw:
                        if item.get("type") == "text":
                            content.append({"type": "text", "text": item.get("text", "")})
                        elif item.get("type") == "image_url":
                            content.append({
                                "type": "image_url",
                                "image_url": item.get("image_url", {})
                            })
                    message_dict["content"] = content
                else:
                    # 兜底：转成字符串（处理非 None 的其他类型）
                    message_dict["content"] = str(content_raw) if content_raw is not None else ""
                
                api_messages.append(message_dict)

            # 🔧 修复：在发送请求前再次清洗消息（终极保险）
            # 确保所有 content 为 None 的消息都被转换为空字符串
            for i, msg in enumerate(api_messages):
                if msg.get("content") is None:
                    logger.warning(f"[DeepSeek] 构建API消息时发现消息 {i} (role={msg.get('role')}) 的 content 为 None，强制转换为空字符串")
                    msg["content"] = ""
            
            # 构建 API 调用参数
            api_kwargs = {
                "model": model,
                "messages": api_messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            # 如果提供了工具，添加到参数中
            if tools:
                api_kwargs["tools"] = tools
                api_kwargs["tool_choice"] = "auto"  # 让模型自动决定是否调用工具

            if stream:
                return self._stream_response(api_messages, model, max_tokens, temperature, tools=tools)
            else:
                response = await self.client.chat.completions.create(**api_kwargs)

                return LLMResponse(
                    content=response.choices[0].message.content or "",
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    } if response.usage else None,
                    model=response.model,
                    provider=LLMProvider.DEEPSEEK.value,
                    finish_reason=response.choices[0].finish_reason,
                    created_at=datetime.fromtimestamp(response.created).isoformat()
                )

        except Exception as e:
            logger.error(f"DeepSeek chat completion failed: {e}")
            if stream:
                error_message = f"DeepSeek API error: {str(e)}"

                async def error_stream():
                    yield LLMStreamChunk(
                        type="error",
                        content=error_message,
                        provider=LLMProvider.DEEPSEEK.value
                    )
                return error_stream()
            else:
                raise

    async def _stream_response(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        max_tokens: int,
        temperature: float,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """处理流式响应"""
        try:
            logger.info(f"[DeepSeek] Starting stream request for model: {model}, tools: {bool(tools)}")
            
            # 🔧 终极修复：强制清洗消息中的所有 None 字段
            # DeepSeek API 对消息格式非常严格：
            # - content 字段必须是字符串（不能是 null）
            # - tool_calls 中的 id、function.name、function.arguments 都不能是 null
            import copy
            sanitized_messages = []
            for i, msg in enumerate(messages):
                # 🔧 使用深拷贝避免任何引用问题
                sanitized_msg = copy.deepcopy(msg)
                
                # 🔧 强制检查并修复 None content（不管原值是什么）
                content = sanitized_msg.get("content")
                if content is None:
                    logger.warning(f"[DeepSeek] 消息 {i} (role={sanitized_msg.get('role')}) 的 content 为 None，强制转换为空字符串")
                    sanitized_msg["content"] = ""
                
                # 🔧 清洗 tool_calls 中的 null 字段
                if sanitized_msg.get("tool_calls"):
                    cleaned_tool_calls = []
                    for tc in sanitized_msg["tool_calls"]:
                        cleaned_tc = {
                            "id": tc.get("id") if tc.get("id") is not None else f"call_{i}_{len(cleaned_tool_calls)}",
                            "type": tc.get("type", "function"),
                            "function": {
                                "name": tc.get("function", {}).get("name") if tc.get("function", {}).get("name") is not None else "",
                                "arguments": tc.get("function", {}).get("arguments") if tc.get("function", {}).get("arguments") is not None else "{}"
                            }
                        }
                        # 记录清洗情况
                        if tc.get("id") is None or tc.get("function", {}).get("name") is None:
                            logger.warning(f"[DeepSeek] 消息 {i} 的 tool_call 存在 null 字段，已清洗: id={cleaned_tc['id']}, name={cleaned_tc['function']['name']}")
                        cleaned_tool_calls.append(cleaned_tc)
                    sanitized_msg["tool_calls"] = cleaned_tool_calls
                
                # 🔧 额外验证：确保 content 真的是字符串或列表
                final_content = sanitized_msg.get("content")
                if final_content is None:
                    logger.error(f"[DeepSeek] 严重错误：消息 {i} 的 content 在修复后仍然是 None！强制设为空字符串")
                    sanitized_msg["content"] = ""
                
                sanitized_messages.append(sanitized_msg)
            
            # 🔧 最终验证：打印每条消息的 content 类型
            for i, msg in enumerate(sanitized_messages):
                content = msg.get("content")
                content_type = type(content).__name__
                content_preview = str(content)[:50] if content else "(empty)"
                logger.info(f"[DeepSeek] 最终消息 {i}: role={msg.get('role')}, content_type={content_type}, preview={content_preview}")
            
            logger.info(f"[DeepSeek] 清洗后的消息数量: {len(sanitized_messages)}")
            
            # AsyncOpenAI 的 create 方法是异步的，必须 await 才能得到流对象
            api_kwargs = {
                "model": model,
                "messages": sanitized_messages,  # 使用清洗后的消息
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True
            }
            
            # 如果提供了工具，添加到参数中
            if tools:
                api_kwargs["tools"] = tools
                api_kwargs["tool_choice"] = "auto"
            
            stream = await self.client.chat.completions.create(**api_kwargs)
            
            # 检查 stream 对象的类型（用于调试）
            logger.info(f"[DeepSeek] Stream object type: {type(stream)}, has __aiter__: {hasattr(stream, '__aiter__')}")

            # 确保流对象存在
            if stream is None:
                logger.error("DeepSeek stream response is None")
                yield LLMStreamChunk(
                    type="error",
                    content="DeepSeek API returned None stream",
                    provider=LLMProvider.DEEPSEEK.value,
                    finished=True
                )
                return

            # 迭代流，确保等待每个 chunk
            has_content = False
            has_tool_calls = False
            tool_calls_accumulator = {}  # 用于收集流式工具调用参数
            chunk_count = 0  # 🔍 调试：计数
            
            async for chunk in stream:
                chunk_count += 1
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    finish_reason = chunk.choices[0].finish_reason
                    
                    # 🔍 调试：每 10 个 chunk 打印一次详情，或者遇到特殊情况时打印
                    if chunk_count <= 3 or chunk_count % 50 == 0 or finish_reason:
                        logger.info(f"[DeepSeek RAW] chunk #{chunk_count}: "
                                   f"finish_reason={finish_reason}, "
                                   f"has_tool_calls={hasattr(delta, 'tool_calls') and bool(delta.tool_calls)}, "
                                   f"has_content={hasattr(delta, 'content') and bool(delta.content)}, "
                                   f"content_preview={repr(delta.content[:50] if hasattr(delta, 'content') and delta.content else None)}")
                    
                    # 🔍 调试：如果检测到 tool_calls，详细打印
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        logger.info(f"[DeepSeek RAW] 🎉 检测到 tool_calls! chunk #{chunk_count}: {delta.tool_calls}")

                    # 处理工具调用
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        has_tool_calls = True
                        for tool_call_delta in delta.tool_calls:
                            index = tool_call_delta.index
                            if index not in tool_calls_accumulator:
                                tool_calls_accumulator[index] = {
                                    "id": tool_call_delta.id if hasattr(tool_call_delta, 'id') else None,
                                    "type": "function",
                                    "function": {
                                        "name": "",
                                        "arguments": ""
                                    }
                                }
                            
                            # 收集工具名称（只有非 None 时才更新）
                            if hasattr(tool_call_delta, 'function') and hasattr(tool_call_delta.function, 'name'):
                                if tool_call_delta.function.name is not None:
                                    tool_calls_accumulator[index]["function"]["name"] = tool_call_delta.function.name
                            
                            # 收集工具参数（可能是分片的，只有非 None 时才追加）
                            if hasattr(tool_call_delta, 'function') and hasattr(tool_call_delta.function, 'arguments'):
                                if tool_call_delta.function.arguments is not None:
                                    tool_calls_accumulator[index]["function"]["arguments"] += tool_call_delta.function.arguments
                            
                            # 收集工具 ID（只有非 None 时才更新）
                            if hasattr(tool_call_delta, 'id') and tool_call_delta.id is not None:
                                tool_calls_accumulator[index]["id"] = tool_call_delta.id

                    # 处理普通内容
                    if hasattr(delta, 'content') and delta.content:
                        has_content = True
                        yield LLMStreamChunk(
                            type="content",
                            content=delta.content,
                            provider=LLMProvider.DEEPSEEK.value,
                            finished=False
                        )
            
            # 如果有工具调用，发送工具调用事件
            if has_tool_calls and tool_calls_accumulator:
                tool_calls_list = [tool_calls_accumulator[i] for i in sorted(tool_calls_accumulator.keys())]
                yield LLMStreamChunk(
                    type="tool_input",
                    content=json.dumps(tool_calls_list, ensure_ascii=False),
                    provider=LLMProvider.DEEPSEEK.value,
                    finished=False
                )

            # 如果没有任何内容，发送完成标记
            if not has_content:
                logger.warning("DeepSeek stream returned no content")
                yield LLMStreamChunk(
                    type="content",
                    content="",
                    provider=LLMProvider.DEEPSEEK.value,
                    finished=True
                )
            else:
                # 发送完成标记
                yield LLMStreamChunk(
                    type="done",
                    content="",
                    provider=LLMProvider.DEEPSEEK.value,
                    finished=True
                )

        except Exception as e:
            logger.error(f"DeepSeek stream response failed: {e}", exc_info=True)
            yield LLMStreamChunk(
                type="error",
                content=f"DeepSeek stream error: {str(e)}",
                provider=LLMProvider.DEEPSEEK.value,
                finished=True
            )

    async def validate_connection(self) -> bool:
        """验证DeepSeek连接"""
        try:
            response = await self.client.chat.completions.create(
                model=self.default_model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return bool(response and response.choices)
        except Exception as e:
            logger.error(f"DeepSeek connection validation failed: {e}")
            return False


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter提供商"""

    def __init__(self, api_key: str, tenant_id: str):
        super().__init__(api_key, tenant_id)
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.default_model = "google/gemini-2.0-flash-exp"

    async def chat_completion(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        tenant_id: Optional[str] = None,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMStreamChunk, None]]:
        """OpenRouter聊天完成"""
        try:
            model = model or self.default_model
            max_tokens = max_tokens or getattr(settings, "llm_max_output_tokens", 8192)
            temperature = temperature if temperature is not None else 0.7

            # 转换消息格式
            api_messages = []
            for msg in messages:
                if isinstance(msg.content, str):
                    api_messages.append({"role": msg.role, "content": msg.content})
                elif isinstance(msg.content, list):
                    # 多模态内容处理
                    content = []

                    # 如果提供了tenant_id，处理多模态内容上传
                    if tenant_id:
                        try:
                            processed_content = await multimodal_processor.process_content_list(
                                msg.content, tenant_id
                            )
                            logger.debug(f"多模态内容处理完成，项目数: {len(processed_content)}")
                        except Exception as e:
                            logger.warning(f"多模态内容处理失败: {e}, 使用原始内容")
                            processed_content = msg.content
                    else:
                        processed_content = msg.content

                    # 转换为OpenRouter格式
                    for item in processed_content:
                        if item.get("type") == "text":
                            content.append({"type": "text", "text": item.get("text", "")})
                        elif item.get("type") == "image_url":
                            content.append({
                                "type": "image_url",
                                "image_url": item.get("image_url", {})
                            })
                        elif item.get("type") == "input_audio":
                            content.append({
                                "type": "input_audio",
                                "input_audio": item.get("input_audio", {})
                            })
                        elif item.get("type") == "video_url":
                            content.append({
                                "type": "video_url",
                                "video_url": item.get("video_url", {})
                            })

                    api_messages.append({"role": msg.role, "content": content})

            if stream:
                return self._stream_response(api_messages, model, max_tokens, temperature)
            else:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=api_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    extra_headers={
                        "HTTP-Referer": getattr(settings, 'openrouter_referer', ''),
                        "X-Title": getattr(settings, 'openrouter_app_name', 'Data Agent')
                    }
                )

                return LLMResponse(
                    content=response.choices[0].message.content or "",
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    } if response.usage else None,
                    model=response.model,
                    provider=LLMProvider.OPENROUTER.value,
                    finish_reason=response.choices[0].finish_reason,
                    created_at=datetime.fromtimestamp(response.created).isoformat()
                )

        except Exception as e:
            logger.error(f"OpenRouter chat completion failed: {e}")
            if stream:
                error_message = f"OpenRouter API error: {str(e)}"

                async def error_stream():
                    yield LLMStreamChunk(
                        type="error",
                        content=error_message,
                        provider=LLMProvider.OPENROUTER.value
                    )
                return error_stream()
            else:
                raise

    async def _stream_response(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        max_tokens: int,
        temperature: float
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """处理流式响应"""
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                extra_headers={
                    "HTTP-Referer": getattr(settings, 'openrouter_referer', ''),
                    "X-Title": getattr(settings, 'openrouter_app_name', 'Data Agent')
                }
            )

            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta

                    if hasattr(delta, 'content') and delta.content:
                        yield LLMStreamChunk(
                            type="content",
                            content=delta.content,
                            provider=LLMProvider.OPENROUTER.value
                        )

        except Exception as e:
            logger.error(f"OpenRouter stream response failed: {e}")
            yield LLMStreamChunk(
                type="error",
                content=f"OpenRouter stream error: {str(e)}",
                provider=LLMProvider.OPENROUTER.value
            )

    async def validate_connection(self) -> bool:
        """验证OpenRouter连接"""
        try:
            response = await self.client.chat.completions.create(
                model=self.default_model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return bool(response and response.choices)
        except Exception as e:
            logger.error(f"OpenRouter connection validation failed: {e}")
            return False


class LLMService:
    """统一LLM服务"""

    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.tenant_configs: Dict[str, Dict[str, Any]] = {}

    def register_provider(
        self,
        tenant_id: str,
        provider: LLMProvider,
        api_key: str
    ) -> BaseLLMProvider:
        """注册提供商"""
        if tenant_id not in self.tenant_configs:
            self.tenant_configs[tenant_id] = {}

        if provider == LLMProvider.DEEPSEEK:
            base_url = getattr(settings, 'deepseek_base_url', 'https://api.deepseek.com')
            default_model = getattr(settings, 'deepseek_default_model', 'deepseek-chat')
            provider_instance = DeepSeekProvider(api_key, tenant_id, base_url, default_model)
        elif provider == LLMProvider.ZHIPU:
            provider_instance = ZhipuProvider(api_key, tenant_id)
        elif provider == LLMProvider.OPENROUTER:
            provider_instance = OpenRouterProvider(api_key, tenant_id)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        key = f"{tenant_id}_{provider.value}"
        self.providers[key] = provider_instance
        self.tenant_configs[tenant_id][provider.value] = api_key

        return provider_instance

    def get_provider(
        self,
        tenant_id: str,
        provider: LLMProvider = None
    ) -> Optional[BaseLLMProvider]:
        """获取提供商"""
        if not provider:
            # 默认优先使用DeepSeek，回退到Zhipu，最后OpenRouter
            for p in [LLMProvider.DEEPSEEK, LLMProvider.ZHIPU, LLMProvider.OPENROUTER]:
                key = f"{tenant_id}_{p.value}"
                if key in self.providers:
                    return self.providers[key]
            return None

        key = f"{tenant_id}_{provider.value}"
        return self.providers.get(key)

    async def chat_completion(
        self,
        tenant_id: str,
        messages: List[LLMMessage],
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        enable_thinking: Optional[bool] = None,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[LLMStreamChunk, None]]:
        """统一聊天完成接口"""
        provider_instance = self.get_provider(tenant_id, provider)

        if not provider_instance:
            # 尝试自动注册默认提供商（优先DeepSeek）
            try:
                if hasattr(settings, 'deepseek_api_key') and settings.deepseek_api_key:
                    provider_instance = self.register_provider(
                        tenant_id, LLMProvider.DEEPSEEK, settings.deepseek_api_key
                    )
                elif hasattr(settings, 'zhipuai_api_key') and settings.zhipuai_api_key:
                    provider_instance = self.register_provider(
                        tenant_id, LLMProvider.ZHIPU, settings.zhipuai_api_key
                    )
                elif hasattr(settings, 'openrouter_api_key') and settings.openrouter_api_key:
                    provider_instance = self.register_provider(
                        tenant_id, LLMProvider.OPENROUTER, settings.openrouter_api_key
                    )
                else:
                    raise ValueError(f"No provider configured for tenant {tenant_id}")
            except Exception as e:
                raise ValueError(f"Failed to initialize provider for tenant {tenant_id}: {e}")

        # 调用具体提供商
        # 注意：chat_completion 是异步函数，即使返回 AsyncGenerator 也需要 await
        # await 一个返回生成器的异步函数会得到生成器对象
        if stream:
            # 流式模式：需要 await 异步函数来获取生成器对象
            return await provider_instance.chat_completion(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream,
                enable_thinking=enable_thinking,
                tenant_id=tenant_id,  # 传递租户ID用于多模态处理
                **kwargs
            )
        else:
            # 非流式模式：需要 await 等待结果
            return await provider_instance.chat_completion(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream,
                enable_thinking=enable_thinking,
                tenant_id=tenant_id,  # 传递租户ID用于多模态处理
                **kwargs
            )

    async def validate_providers(self, tenant_id: str) -> Dict[str, bool]:
        """验证所有提供商连接"""
        results = {}

        for provider in [LLMProvider.DEEPSEEK, LLMProvider.ZHIPU, LLMProvider.OPENROUTER]:
            provider_instance = self.get_provider(tenant_id, provider)
            if provider_instance:
                results[provider.value] = await provider_instance.validate_connection()
            else:
                results[provider.value] = False

        return results

    async def get_available_models(self, tenant_id: str) -> Dict[str, List[str]]:
        """获取可用模型列表"""
        models = {
            "deepseek": ["deepseek-chat", "deepseek-coder"],
            "zhipu": ["glm-4-flash", "glm-4", "glm-4.6", "glm-4v", "glm-4-9b"],
            "openrouter": [
                "google/gemini-2.0-flash-exp",
                "google/gemini-2.5-flash",
                "anthropic/claude-3.5-sonnet",
                "openai/gpt-4o",
                "meta-llama/llama-3.2-90b-vision-instruct"
            ]
        }

        # 根据实际可用的提供商过滤
        available_providers = await self.validate_providers(tenant_id)
        return {
            provider: models_list
            for provider, models_list in models.items()
            if available_providers.get(provider, False)
        }

    def analyze_conversation_complexity(self, messages: List[LLMMessage]) -> Dict[str, Any]:
        """
        分析对话复杂度，用于智能参数调整

        Args:
            messages: 对话消息列表

        Returns:
            Dict: 复杂度分析结果
        """
        try:
            total_chars = 0
            user_messages = 0
            question_marks = 0
            complex_words = 0

            complexity_words = [
                "分析", "解释", "评估", "比较", "设计", "规划", "策略",
                "为什么", "如何", "原因", "影响", "步骤", "原理"
            ]

            for msg in messages:
                if msg.role == "user":
                    user_messages += 1
                    if isinstance(msg.content, str):
                        content = msg.content
                    elif isinstance(msg.content, list):
                        # 处理多模态内容，只计算文本部分
                        content = ""
                        for item in msg.content:
                            if item.get("type") == "text":
                                content += item.get("text", "")
                    else:
                        content = str(msg.content)

                    total_chars += len(content)
                    question_marks += content.count("?") + content.count("？")

                    content_lower = content.lower()
                    for word in complexity_words:
                        if word in content_lower:
                            complex_words += 1

            # 计算复杂度分数
            complexity_score = (
                min(total_chars / 1000, 1.0) * 0.3 +  # 内容长度
                min(user_messages / 5, 1.0) * 0.2 +     # 消息数量
                min(question_marks / 3, 1.0) * 0.3 +    # 问题数量
                min(complex_words / 5, 1.0) * 0.2       # 复杂词汇
            )

            return {
                "complexity_score": complexity_score,
                "total_chars": total_chars,
                "user_messages": user_messages,
                "question_marks": question_marks,
                "complex_words": complex_words,
                "recommend_thinking": complexity_score > 0.4,
                "recommend_temperature": 0.3 + complexity_score * 0.5
            }
        except Exception as e:
            logger.warning(f"对话复杂度分析失败: {e}")
            return {
                "complexity_score": 0.5,
                "recommend_thinking": False,
                "recommend_temperature": 0.7
            }


# 全局LLM服务实例
llm_service = LLMService()
