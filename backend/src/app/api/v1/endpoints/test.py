"""
AI 服务测试 API 端点
专门用于测试智谱 AI API 的各种功能
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
import asyncio

from src.app.services.zhipu_client import zhipu_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatTestRequest(BaseModel):
    """聊天测试请求模型"""
    message: str = Field(..., description="要发送的消息", min_length=1, max_length=2000)
    model: Optional[str] = Field(None, description="使用的模型，默认使用 glm-4")
    max_tokens: Optional[int] = Field(None, description="最大 token 数，默认 100", ge=1, le=4000)
    temperature: Optional[float] = Field(0.7, description="温度参数，控制随机性", ge=0.0, le=2.0)


class EmbeddingTestRequest(BaseModel):
    """嵌入测试请求模型"""
    texts: List[str] = Field(..., description="要生成嵌入的文本列表", min_items=1, max_items=10)
    model: Optional[str] = Field("embedding-2", description="嵌入模型")


class SemanticSearchRequest(BaseModel):
    """语义搜索测试请求"""
    query: str = Field(..., description="搜索查询", min_length=1, max_length=500)
    documents: List[str] = Field(..., description="要搜索的文档列表", min_items=1, max_items=50)
    top_k: Optional[int] = Field(5, description="返回结果数量", ge=1, le=20)


class TextAnalysisRequest(BaseModel):
    """文本分析测试请求"""
    text: str = Field(..., description="要分析的文本", min_length=1, max_length=5000)
    analysis_type: Optional[str] = Field(
        "summary",
        description="分析类型: summary, keywords, sentiment, topics"
    )


@router.post("/zhipu", response_model=Dict[str, Any])
async def test_zhipu_connection():
    """
    测试智谱 AI API 连接

    Returns:
        连接测试结果
    """
    try:
        logger.info("开始测试智谱 AI API 连接")

        is_connected = await zhipu_service.check_connection()

        result = {
            "service": "ZhipuAI",
            "test_type": "connection_test",
            "status": "success" if is_connected else "failed",
            "message": "智谱 API 连接成功" if is_connected else "智谱 API 连接失败",
            "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop() else None
        }

        if is_connected:
            # 如果连接成功，获取模型信息
            try:
                model_info = await zhipu_service.get_model_info()
                result["model_info"] = model_info
            except Exception as e:
                logger.warning(f"获取模型信息失败: {e}")
                result["model_info"] = {"error": str(e)}

        return result

    except Exception as e:
        logger.error(f"智谱 API 连接测试失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"智谱 API 连接测试失败: {str(e)}"
        )


@router.post("/zhipu/chat", response_model=Dict[str, Any])
async def test_zhipu_chat(request: ChatTestRequest):
    """
    测试智谱 AI 聊天功能

    Args:
        request: 聊天测试请求

    Returns:
        聊天响应结果
    """
    try:
        logger.info(f"测试智谱 AI 聊天 - 消息: {request.message[:50]}...")

        messages = [
            {"role": "user", "content": request.message}
        ]

        response = await zhipu_service.chat_completion(
            messages=messages,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        if response:
            result = {
                "service": "ZhipuAI",
                "test_type": "chat_completion",
                "status": "success",
                "request": {
                    "message": request.message,
                    "model": request.model or zhipu_service.default_model,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature
                },
                "response": {
                    "content": response["content"],
                    "role": response["role"],
                    "usage": response["usage"],
                    "model": response["model"],
                    "finish_reason": response.get("finish_reason", "unknown")
                },
                "timestamp": response["created_at"]
            }
        else:
            result = {
                "service": "ZhipuAI",
                "test_type": "chat_completion",
                "status": "failed",
                "message": "聊天完成失败，没有返回响应",
                "request": {
                    "message": request.message,
                    "model": request.model or zhipu_service.default_model
                }
            }

        return result

    except Exception as e:
        logger.error(f"智谱 AI 聊天测试失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"智谱 AI 聊天测试失败: {str(e)}"
        )


@router.post("/zhipu/embedding", response_model=Dict[str, Any])
async def test_zhipu_embedding(request: EmbeddingTestRequest):
    """
    测试智谱 AI 嵌入功能

    Args:
        request: 嵌入测试请求

    Returns:
        嵌入响应结果
    """
    try:
        logger.info(f"测试智谱 AI 嵌入 - 文本数量: {len(request.texts)}")

        embeddings = await zhipu_service.embedding(
            texts=request.texts,
            model=request.model
        )

        if embeddings:
            result = {
                "service": "ZhipuAI",
                "test_type": "embedding_generation",
                "status": "success",
                "request": {
                    "text_count": len(request.texts),
                    "model": request.model,
                    "sample_text": request.texts[0][:50] + "..." if request.texts[0] else ""
                },
                "response": {
                    "embedding_count": len(embeddings),
                    "embedding_dimension": len(embeddings[0]) if embeddings else 0,
                    "sample_embedding_preview": embeddings[0][:5] if embeddings else []
                },
                "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop() else None
            }
        else:
            result = {
                "service": "ZhipuAI",
                "test_type": "embedding_generation",
                "status": "failed",
                "message": "嵌入向量生成失败",
                "request": {
                    "text_count": len(request.texts),
                    "model": request.model
                }
            }

        return result

    except Exception as e:
        logger.error(f"智谱 AI 嵌入测试失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"智谱 AI 嵌入测试失败: {str(e)}"
        )


@router.post("/zhipu/semantic-search", response_model=Dict[str, Any])
async def test_zhipu_semantic_search(request: SemanticSearchRequest):
    """
    测试智谱 AI 语义搜索功能

    Args:
        request: 语义搜索测试请求

    Returns:
        语义搜索结果
    """
    try:
        logger.info(f"测试智谱 AI 语义搜索 - 查询: {request.query[:30]}..., 文档数: {len(request.documents)}")

        search_results = await zhipu_service.semantic_search(
            query=request.query,
            documents=request.documents,
            top_k=request.top_k
        )

        if search_results:
            result = {
                "service": "ZhipuAI",
                "test_type": "semantic_search",
                "status": "success",
                "request": {
                    "query": request.query,
                    "document_count": len(request.documents),
                    "top_k": request.top_k
                },
                "response": search_results,
                "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop() else None
            }
        else:
            result = {
                "service": "ZhipuAI",
                "test_type": "semantic_search",
                "status": "failed",
                "message": "语义搜索失败",
                "request": {
                    "query": request.query,
                    "document_count": len(request.documents)
                }
            }

        return result

    except Exception as e:
        logger.error(f"智谱 AI 语义搜索测试失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"智谱 AI 语义搜索测试失败: {str(e)}"
        )


@router.post("/zhipu/text-analysis", response_model=Dict[str, Any])
async def test_zhipu_text_analysis(request: TextAnalysisRequest):
    """
    测试智谱 AI 文本分析功能

    Args:
        request: 文本分析测试请求

    Returns:
        文本分析结果
    """
    try:
        logger.info(f"测试智谱 AI 文本分析 - 类型: {request.analysis_type}, 文本长度: {len(request.text)}")

        analysis_result = await zhipu_service.text_analysis(
            text=request.text,
            analysis_type=request.analysis_type
        )

        if analysis_result:
            result = {
                "service": "ZhipuAI",
                "test_type": "text_analysis",
                "status": "success",
                "request": {
                    "text_length": len(request.text),
                    "analysis_type": request.analysis_type,
                    "text_preview": request.text[:100] + "..." if len(request.text) > 100 else request.text
                },
                "response": {
                    "analysis": analysis_result,
                    "analysis_length": len(analysis_result)
                },
                "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop() else None
            }
        else:
            result = {
                "service": "ZhipuAI",
                "test_type": "text_analysis",
                "status": "failed",
                "message": "文本分析失败",
                "request": {
                    "analysis_type": request.analysis_type,
                    "text_length": len(request.text)
                }
            }

        return result

    except Exception as e:
        logger.error(f"智谱 AI 文本分析测试失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"智谱 AI 文本分析测试失败: {str(e)}"
        )


@router.get("/zhipu/models", response_model=Dict[str, Any])
async def test_zhipu_models():
    """
    测试获取智谱 AI 模型信息

    Returns:
        可用模型信息
    """
    try:
        logger.info("测试获取智谱 AI 模型信息")

        # 测试默认模型
        default_model_info = await zhipu_service.get_model_info()

        # 可以添加更多模型的测试
        supported_models = ["glm-4", "glm-3-turbo"]
        model_tests = []

        for model in supported_models:
            try:
                model_info = await zhipu_service.get_model_info(model)
                model_tests.append(model_info)
            except Exception as e:
                logger.warning(f"模型 {model} 测试失败: {e}")
                model_tests.append({
                    "model": model,
                    "status": "error",
                    "error": str(e)
                })

        result = {
            "service": "ZhipuAI",
            "test_type": "model_availability",
            "status": "success",
            "default_model": default_model_info,
            "tested_models": model_tests,
            "supported_models": supported_models,
            "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop() else None
        }

        return result

    except Exception as e:
        logger.error(f"智谱 AI 模型信息测试失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"智谱 AI 模型信息测试失败: {str(e)}"
        )


@router.get("/zhipu/comprehensive", response_model=Dict[str, Any])
async def comprehensive_zhipu_test():
    """
    综合测试智谱 AI 的所有功能

    Returns:
        综合测试结果
    """
    try:
        logger.info("开始智谱 AI 综合测试")

        test_results = {}

        # 1. 连接测试
        connection_result = await zhipu_service.check_connection()
        test_results["connection"] = {
            "status": "success" if connection_result else "failed",
            "message": "连接成功" if connection_result else "连接失败"
        }

        if not connection_result:
            # 如果连接失败，直接返回
            return {
                "service": "ZhipuAI",
                "test_type": "comprehensive",
                "overall_status": "failed",
                "message": "基础连接失败，跳过其他测试",
                "results": test_results
            }

        # 并行执行其他测试
        async def run_chat_test():
            return await zhipu_service.chat_completion(
                messages=[{"role": "user", "content": "你好"}],
                max_tokens=50
            )

        async def run_embedding_test():
            return await zhipu_service.embedding(["测试文本"])

        async def run_analysis_test():
            return await zhipu_service.text_analysis(
                "这是一个测试文本，用于分析功能。",
                "summary"
            )

        # 执行测试
        chat_result, embedding_result, analysis_result = await asyncio.gather(
            run_chat_test(),
            run_embedding_test(),
            run_analysis_test(),
            return_exceptions=True
        )

        # 处理结果
        test_results["chat"] = {
            "status": "success" if not isinstance(chat_result, Exception) and chat_result else "failed",
            "message": "聊天测试成功" if not isinstance(chat_result, Exception) and chat_result else "聊天测试失败"
        }

        test_results["embedding"] = {
            "status": "success" if not isinstance(embedding_result, Exception) and embedding_result else "failed",
            "message": "嵌入测试成功" if not isinstance(embedding_result, Exception) and embedding_result else "嵌入测试失败"
        }

        test_results["analysis"] = {
            "status": "success" if not isinstance(analysis_result, Exception) and analysis_result else "failed",
            "message": "分析测试成功" if not isinstance(analysis_result, Exception) and analysis_result else "分析测试失败"
        }

        # 计算总体状态
        successful_count = sum(1 for result in test_results.values() if result["status"] == "success")
        total_count = len(test_results)

        overall_status = "success" if successful_count == total_count else "partial_success" if successful_count > 0 else "failed"

        return {
            "service": "ZhipuAI",
            "test_type": "comprehensive",
            "overall_status": overall_status,
            "successful_tests": successful_count,
            "total_tests": total_count,
            "results": test_results,
            "timestamp": asyncio.get_event_loop().time() if asyncio.get_event_loop() else None
        }

    except Exception as e:
        logger.error(f"智谱 AI 综合测试失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"智谱 AI 综合测试失败: {str(e)}"
        )