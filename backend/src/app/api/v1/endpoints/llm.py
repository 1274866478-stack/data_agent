"""
LLM API端点
提供统一的聊天完成、流式输出和多模态支持
"""

import json
import asyncio
from typing import Dict, Any, Optional, List, Union
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.app.services.llm_service import (
    llm_service,
    LLMProvider,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk
)
from src.app.core.auth import get_current_user_with_tenant
from src.app.data.models import Tenant

router = APIRouter(prefix="/llm", tags=["LLM"])


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str = Field(..., description="消息角色：user, assistant, system")
    content: Union[str, List[Dict[str, Any]]] = Field(
        ...,
        description="消息内容，支持文本或多模态内容"
    )
    thinking: Optional[str] = Field(None, description="思考过程（仅assistant角色）")


class ChatCompletionRequest(BaseModel):
    """聊天完成请求模型"""
    messages: List[ChatMessage] = Field(..., description="对话消息列表")
    provider: Optional[str] = Field(
        None,
        description="LLM提供商：zhipu, openrouter，不指定则自动选择"
    )
    model: Optional[str] = Field(None, description="模型名称，不指定则使用默认模型")
    max_tokens: Optional[int] = Field(None, description="最大输出tokens")
    temperature: Optional[float] = Field(None, description="温度参数(0-1)")
    stream: bool = Field(False, description="是否启用流式输出")
    enable_thinking: bool = Field(False, description="是否启用深度思考模式（仅Zhipu支持）")


class ChatCompletionResponse(BaseModel):
    """聊天完成响应模型"""
    content: str = Field(..., description="回复内容")
    thinking: Optional[str] = Field(None, description="思考过程")
    usage: Optional[Dict[str, int]] = Field(None, description="Token使用情况")
    model: Optional[str] = Field(None, description="使用的模型")
    provider: Optional[str] = Field(None, description="使用的提供商")
    finish_reason: Optional[str] = Field(None, description="结束原因")
    created_at: Optional[str] = Field(None, description="创建时间")


class ProviderStatusResponse(BaseModel):
    """提供商状态响应模型"""
    zhipu: bool = Field(..., description="智谱AI可用性")
    openrouter: bool = Field(..., description="OpenRouter可用性")


class AvailableModelsResponse(BaseModel):
    """可用模型响应模型"""
    providers: Dict[str, List[str]] = Field(..., description="各提供商的可用模型")


def _convert_chat_messages(messages: List[ChatMessage]) -> List[LLMMessage]:
    """转换聊天消息格式"""
    llm_messages = []
    for msg in messages:
        llm_messages.append(LLMMessage(
            role=msg.role,
            content=msg.content,
            thinking=msg.thinking
        ))
    return llm_messages


def _convert_response(response: LLMResponse) -> ChatCompletionResponse:
    """转换响应格式"""
    return ChatCompletionResponse(
        content=response.content,
        thinking=response.thinking,
        usage=response.usage,
        model=response.model,
        provider=response.provider,
        finish_reason=response.finish_reason,
        created_at=response.created_at
    )


async def _stream_response_generator(
    stream_generator,
    tenant_id: str
):
    """流式响应生成器"""
    try:
        async for chunk in stream_generator:
            chunk_data = {
                "type": chunk.type,
                "content": chunk.content,
                "provider": chunk.provider,
                "finished": chunk.finished,
                "tenant_id": tenant_id
            }
            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

        # 发送结束标记
        yield "data: [DONE]\n\n"
    except Exception as e:
        error_data = {
            "type": "error",
            "content": f"Stream error: {str(e)}",
            "provider": "unknown",
            "finished": True,
            "tenant_id": tenant_id
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completion(
    request: ChatCompletionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    聊天完成接口
    支持多提供商、多模态和流式输出
    """
    try:
        # 获取tenant_id，支持开发环境下的默认租户
        tenant_id = getattr(current_user, 'tenant_id', None) or current_user.get('tenant_id', 'default_tenant')

        # 转换提供商
        provider = None
        if request.provider:
            try:
                provider = LLMProvider(request.provider)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid provider: {request.provider}"
                )

        # 转换消息格式
        messages = _convert_chat_messages(request.messages)

        # 调用LLM服务
        if request.stream:
            # 流式响应
            response_generator = await llm_service.chat_completion(
                tenant_id=tenant_id,
                messages=messages,
                provider=provider,
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=request.stream,
                enable_thinking=request.enable_thinking
            )

            return StreamingResponse(
                _stream_response_generator(response_generator, tenant_id),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control"
                }
            )
        else:
            # 非流式响应
            response = await llm_service.chat_completion(
                tenant_id=tenant_id,
                messages=messages,
                provider=provider,
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                stream=request.stream,
                enable_thinking=request.enable_thinking
            )

            if isinstance(response, LLMResponse):
                return _convert_response(response)
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Unexpected response type from LLM service"
                )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat completion failed: {str(e)}"
        )


@router.get("/providers/status", response_model=ProviderStatusResponse)
async def get_provider_status(
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    获取LLM提供商状态
    """
    try:
        tenant_id = current_user.tenant_id
        status = await llm_service.validate_providers(tenant_id)

        return ProviderStatusResponse(
            zhipu=status.get("zhipu", False),
            openrouter=status.get("openrouter", False)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get provider status: {str(e)}"
        )


@router.get("/models", response_model=AvailableModelsResponse)
async def get_available_models(
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    获取可用模型列表
    """
    try:
        tenant_id = current_user.tenant_id
        models = await llm_service.get_available_models(tenant_id)

        return AvailableModelsResponse(providers=models)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get available models: {str(e)}"
        )


@router.post("/test")
async def test_llm_service(
    provider: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    测试LLM服务
    """
    try:
        tenant_id = current_user.tenant_id

        # 转换提供商
        llm_provider = None
        if provider:
            try:
                llm_provider = LLMProvider(provider)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid provider: {provider}"
                )

        # 创建测试消息
        test_messages = [
            LLMMessage(
                role="user",
                content="你好，请回复一条简短的测试消息"
            )
        ]

        # 调用LLM服务
        response = await llm_service.chat_completion(
            tenant_id=tenant_id,
            messages=test_messages,
            provider=llm_provider,
            max_tokens=50
        )

        if isinstance(response, LLMResponse):
            return {
                "success": True,
                "response": _convert_response(response).dict(),
                "message": "LLM service test successful"
            }
        else:
            return {
                "success": False,
                "message": "Unexpected response type"
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"LLM service test failed: {str(e)}"
        }


@router.post("/test/multimodal")
async def test_multimodal(
    current_user: Dict[str, Any] = Depends(get_current_user_with_tenant)
):
    """
    测试多模态功能（需要OpenRouter）
    """
    try:
        tenant_id = current_user.tenant_id

        # 创建多模态测试消息
        multimodal_content = [
            {
                "type": "text",
                "text": "请描述这张图片中的内容"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
                }
            }
        ]

        test_messages = [
            LLMMessage(
                role="user",
                content=multimodal_content
            )
        ]

        # 优先使用OpenRouter进行多模态测试
        response = await llm_service.chat_completion(
            tenant_id=tenant_id,
            messages=test_messages,
            provider=LLMProvider.OPENROUTER,
            max_tokens=200
        )

        if isinstance(response, LLMResponse):
            return {
                "success": True,
                "response": _convert_response(response).dict(),
                "message": "Multimodal test successful"
            }
        else:
            return {
                "success": False,
                "message": "Unexpected response type"
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Multimodal test failed: {str(e)}"
        }


# ===== 新增的高级LLM功能测试端点 =====

@router.get("/test/stream-thinking")
async def test_stream_thinking(
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    测试流式输出和思考模式
    """
    try:
        from src.app.services.llm_service import LLMMessage

        messages = [
            LLMMessage(
                role="user",
                content="请详细分析机器学习的核心概念和实际应用场景"
            )
        ]

        async def stream_generator():
            try:
                async for chunk in llm_service.chat_completion(
                    tenant_id=current_user.id,
                    messages=messages,
                    stream=True,
                    enable_thinking=None  # 自动判断
                ):
                    yield f"data: {json.dumps(chunk.dict(), ensure_ascii=False)}\n\n"

                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {{'type': 'error', 'content': '{str(e)}'}}\n\n"

        return StreamingResponse(
            stream_generator(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream thinking test failed: {str(e)}")


@router.get("/test/intelligent-params")
async def test_intelligent_params(
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    测试智能参数调整功能
    """
    try:
        from src.app.services.llm_service import LLMMessage

        # 测试不同复杂度的问题
        test_cases = [
            {
                "name": "简单问题",
                "messages": [LLMMessage(role="user", content="你好")]
            },
            {
                "name": "复杂问题",
                "messages": [LLMMessage(
                    role="user",
                    content="请详细分析深度学习在计算机视觉领域的应用，包括卷积神经网络的原理、常见的架构设计、训练技巧以及在实际项目中的部署策略，并讨论当前面临的挑战和未来发展方向。"
                )]
            },
            {
                "name": "需要思考的问题",
                "messages": [LLMMessage(
                    role="user",
                    content="为什么Transformer架构能够超越传统的RNN模型？请从注意力机制、并行计算能力、长期依赖处理等多个角度进行深入分析。"
                )]
            }
        ]

        results = []

        for case in test_cases:
            complexity = llm_service.analyze_conversation_complexity(case["messages"])

            # 使用智能参数调用
            response = await llm_service.chat_completion(
                tenant_id=current_user.id,
                messages=case["messages"],
                enable_thinking=None,  # 自动判断
                temperature=complexity.get("recommend_temperature", 0.7),
                max_tokens=complexity.get("recommend_max_tokens", 4000)
            )

            results.append({
                "case_name": case["name"],
                "complexity_analysis": complexity,
                "response_type": type(response).__name__,
                "success": response is not None
            })

        return {
            "success": True,
            "message": "Intelligent parameter adjustment test completed",
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intelligent params test failed: {str(e)}")


@router.get("/test/multimodal-upload")
async def test_multimodal_upload(
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    测试多模态内容处理和MinIO上传
    """
    try:
        from src.app.services.llm_service import LLMMessage
        from src.app.services.multimodal_processor import multimodal_processor

        # 构建包含图片URL的测试消息
        test_image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"

        messages = [
            LLMMessage(
                role="user",
                content=[
                    {
                        "type": "text",
                        "text": "请描述这张图片的内容"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": test_image_url
                        }
                    }
                ]
            )
        ]

        # 测试多模态处理
        processed_content = await multimodal_processor.process_content_list(
            messages[0].content,
            current_user.id
        )

        # 尝试调用OpenRouter（支持多模态）
        response = await llm_service.chat_completion(
            tenant_id=current_user.id,
            messages=messages,
            provider=LLMProvider.OPENROUTER,
            stream=False
        )

        return {
            "success": True,
            "message": "Multimodal upload test completed",
            "original_content_count": len(messages[0].content),
            "processed_content_count": len(processed_content),
            "response_received": response is not None,
            "processed_sample": processed_content[:2] if processed_content else []
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multimodal upload test failed: {str(e)}")


@router.get("/test/tenant-isolation")
async def test_tenant_isolation(
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    测试租户隔离功能
    """
    try:
        from src.app.services.tenant_config_manager import tenant_config_manager, ProviderType

        # 测试租户配置获取
        test_tenant_id = current_user.id
        providers = []

        for provider in [ProviderType.ZHIPU, ProviderType.OPENROUTER]:
            api_key = await tenant_config_manager.get_tenant_api_key(
                test_tenant_id, provider, use_global_fallback=True
            )
            if api_key:
                providers.append(provider.value)

        # 测试模型配置获取
        model_configs = {}
        for provider in [ProviderType.ZHIPU, ProviderType.OPENROUTER]:
            config = await tenant_config_manager.get_tenant_model_config(test_tenant_id, provider)
            model_configs[provider.value] = config

        # 验证租户配置
        validation_results = await tenant_config_manager.validate_tenant_config(test_tenant_id)

        return {
            "success": True,
            "message": "Tenant isolation test completed",
            "tenant_id": test_tenant_id,
            "available_providers": providers,
            "model_configs": model_configs,
            "validation_results": validation_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tenant isolation test failed: {str(e)}")


@router.get("/test/all-features")
async def test_all_features(
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    综合功能测试端点
    """
    try:
        from src.app.services.llm_service import LLMMessage

        # 构建复杂的测试场景
        messages = [
            LLMMessage(
                role="user",
                content="作为一个AI专家，请分析和评估当前大语言模型技术的发展现状，包括技术架构、应用场景、优势和挑战，并预测未来的发展趋势。请提供详细的分析和具体的建议。"
            )
        ]

        # 获取对话复杂度分析
        complexity_analysis = llm_service.analyze_conversation_complexity(messages)

        # 调用聊天完成（启用智能思考模式）
        response = await llm_service.chat_completion(
            tenant_id=current_user.id,
            messages=messages,
            stream=False,
            enable_thinking=None,  # 自动启用思考模式
            temperature=complexity_analysis.get("recommend_temperature", 0.7),
            max_tokens=complexity_analysis.get("recommend_max_tokens", 6000)
        )

        # 获取可用模型列表
        available_models = await llm_service.get_available_models(current_user.id)

        # 验证提供商状态
        provider_status = await llm_service.validate_providers(current_user.id)

        return {
            "success": True,
            "message": "Comprehensive LLM features test completed",
            "complexity_analysis": complexity_analysis,
            "response_received": response is not None,
            "available_models": available_models,
            "provider_status": provider_status,
            "features_tested": [
                "智能思考模式",
                "复杂度分析",
                "智能参数调整",
                "多提供商支持",
                "租户隔离"
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comprehensive test failed: {str(e)}")