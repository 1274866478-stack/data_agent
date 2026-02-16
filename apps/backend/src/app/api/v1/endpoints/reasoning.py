"""
# 推理API端点

## [HEADER]
**文件名**: reasoning.py
**职责**: 提供智能查询理解、推理分析、答案生成、对话管理和使用量监控的RESTful API
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本

## [INPUT]
- query: str - 用户查询文本
- context: Optional[List[Dict[str, Any]]] - 上下文信息
- data_sources: Optional[List[Dict[str, Any]]] - 数据源信息
- conversation_id: Optional[str] - 对话ID
- reasoning_mode: Optional[str] - 推理模式
- provider: Optional[str] - LLM提供商（默认zhipu）
- model: Optional[str] - 模型名称
- stream: bool - 是否启用流式输出
- period: str - 统计周期（daily, weekly, monthly）

## [OUTPUT]
- 查询分析结果: Dict[str, Any]（包含意图、实体、关键词、复杂度）
- 推理结果: ReasoningResponse（包含答案、推理步骤、置信度、质量分数）
- 流式推理响应: StreamingResponse（SSE格式）
- 对话ID: Dict[str, str]
- 对话历史: Dict[str, Any]
- 使用量统计: Dict[str, Any]
- 使用量限制信息: Dict[str, Any]
- 健康检查状态: Dict[str, Any]

## [LINK]
**上游依赖**:
- [../../core/auth.py](../../core/auth.py) - get_current_user_with_tenant依赖注入
- [../../services/reasoning_service.py](../../services/reasoning_service.py) - reasoning_engine推理引擎
- [../../services/conversation_service.py](../../services/conversation_service.py) - conversation_manager对话管理器
- [../../services/usage_monitoring_service.py](../../services/usage_monitoring_service.py) - usage_monitoring_service使用量监控
- [../../data/models.py](../../data/models.py) - Tenant模型

**下游依赖**:
- 无（API端点为最外层）

**调用方**:
- 前端智能问答界面
- 对话式分析工具
- AI推理系统
- 使用量统计仪表板

## [POS]
**路径**: backend/src/app/api/v1/endpoints/reasoning.py
**模块层级**: Level 3（API端点层）
**依赖深度**: 2 层（依赖于services和core层）
"""

import json
import asyncio
from typing import Dict, Any, Optional, List, Union
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.app.services.reasoning_service import (
    reasoning_engine,
    QueryType,
    ReasoningMode,
    QueryAnalysis,
    ReasoningResult
)
from src.app.services.conversation_service import (
    conversation_manager,
    ConversationState
)
from src.app.services.usage_monitoring_service import (
    usage_monitoring_service,
    ProviderType,
    UsageType
)
from src.app.core.auth import get_current_user_with_tenant
from src.app.data.models import Tenant

router = APIRouter(prefix="/reasoning", tags=["Reasoning"])


class ReasoningRequest(BaseModel):
    """推理请求模型"""
    query: str = Field(..., description="用户查询")
    context: Optional[List[Dict[str, Any]]] = Field(None, description="上下文信息")
    data_sources: Optional[List[Dict[str, Any]]] = Field(None, description="数据源信息")
    conversation_id: Optional[str] = Field(None, description="对话ID")
    reasoning_mode: Optional[str] = Field(None, description="推理模式")
    provider: Optional[str] = Field("zhipu", description="LLM提供商")
    model: Optional[str] = Field(None, description="模型名称")
    stream: bool = Field(False, description="是否启用流式输出")


class ReasoningResponse(BaseModel):
    """推理响应模型"""
    answer: str = Field(..., description="生成的答案")
    reasoning_steps: List[Dict[str, Any]] = Field(..., description="推理步骤")
    confidence: float = Field(..., description="置信度")
    quality_score: float = Field(..., description="质量分数")
    sources: List[Dict[str, Any]] = Field(..., description="数据源")
    query_analysis: Dict[str, Any] = Field(..., description="查询分析结果")
    usage_info: Dict[str, Any] = Field(..., description="使用量信息")
    conversation_id: Optional[str] = Field(None, description="对话ID")
    safety_filter_triggered: bool = Field(..., description="安全过滤是否触发")


class ConversationCreateRequest(BaseModel):
    """创建对话请求模型"""
    tenant_id: str = Field(..., description="租户ID")
    user_id: str = Field(..., description="用户ID")
    conversation_id: Optional[str] = Field(None, description="对话ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class ConversationMessageRequest(BaseModel):
    """对话消息请求模型"""
    conversation_id: str = Field(..., description="对话ID")
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    token_count: int = Field(0, description="Token数量")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_query(
    request: ReasoningRequest,
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    分析查询意图和复杂度

    Args:
        request: 推理请求
        current_user: 当前用户

    Returns:
        查询分析结果
    """
    try:
        tenant_id = current_user.id

        # 记录使用量
        await usage_monitoring_service.tracker.record_usage(
            tenant_id=tenant_id,
            provider=ProviderType.ZHIPU,
            model="glm-4-flash",
            usage_type=UsageType.API_CALLS,
            amount=1,
            metadata={"endpoint": "/reasoning/analyze"}
        )

        # 执行查询分析
        query_analysis = await reasoning_engine.query_understanding.analyze_query(
            request.query, request.context
        )

        return {
            "success": True,
            "data": {
                "original_query": query_analysis.original_query,
                "query_type": query_analysis.query_type.value,
                "intent": query_analysis.intent,
                "entities": query_analysis.entities,
                "keywords": query_analysis.keywords,
                "temporal_expressions": query_analysis.temporal_expressions,
                "complexity_score": query_analysis.complexity_score,
                "confidence": query_analysis.confidence,
                "reasoning_mode": query_analysis.reasoning_mode.value,
                "suggested_temperature": query_analysis.suggested_temperature,
                "suggested_max_tokens": query_analysis.suggested_max_tokens,
                "metadata": query_analysis.metadata
            }
        }

    except Exception as e:
        logger.error(f"查询分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询分析失败: {str(e)}")


@router.post("/reason", response_model=ReasoningResponse)
async def reason_query(
    request: ReasoningRequest,
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    执行完整推理过程

    Args:
        request: 推理请求
        current_user: 当前用户

    Returns:
        推理结果
    """
    try:
        tenant_id = current_user.id

        # 检查使用量限制
        can_proceed, warnings = await usage_monitoring_service.tracker.check_usage_limits(
            tenant_id, ProviderType.ZHIPU
        )
        if not can_proceed:
            raise HTTPException(status_code=429, detail="已达到使用量限制")

        # 转换推理模式
        reasoning_mode = None
        if request.reasoning_mode:
            try:
                reasoning_mode = ReasoningMode(request.reasoning_mode)
            except ValueError:
                pass  # 使用默认模式

        # 执行推理
        result = await reasoning_engine.reason(
            query=request.query,
            context=request.context,
            data_sources=request.data_sources,
            tenant_id=tenant_id,
            reasoning_mode=reasoning_mode
        )

        # 记录使用量
        await usage_monitoring_service.tracker.record_usage(
            tenant_id=tenant_id,
            provider=ProviderType.ZHIPU,
            model=request.model or "glm-4-flash",
            usage_type=UsageType.TOKENS,
            amount=result.query_analysis.suggested_max_tokens,
            metadata={"endpoint": "/reasoning/reason", "query_type": result.query_analysis.query_type.value}
        )

        # 如果提供了对话ID，将消息添加到对话历史
        conversation_id = None
        if request.conversation_id:
            await conversation_manager.add_message(
                conversation_id=request.conversation_id,
                role="user",
                content=request.query,
                metadata={"reasoning_result": True}
            )

            # 添加助手回复
            await conversation_manager.add_message(
                conversation_id=request.conversation_id,
                role="assistant",
                content=result.answer,
                metadata={"reasoning_result": True, "confidence": result.confidence}
            )
            conversation_id = request.conversation_id

        # 检查警告
        alerts = await usage_monitoring_service.check_and_alert(tenant_id)

        return ReasoningResponse(
            answer=result.answer,
            reasoning_steps=[
                {
                    "step_number": step.step_number,
                    "description": step.description,
                    "reasoning": step.reasoning,
                    "evidence": step.evidence,
                    "confidence": step.confidence,
                    "timestamp": step.timestamp.isoformat()
                }
                for step in result.reasoning_steps
            ],
            confidence=result.confidence,
            quality_score=result.quality_score,
            sources=result.sources,
            query_analysis={
                "original_query": result.query_analysis.original_query,
                "query_type": result.query_analysis.query_type.value,
                "intent": result.query_analysis.intent,
                "complexity_score": result.query_analysis.complexity_score,
                "reasoning_mode": result.query_analysis.reasoning_mode.value
            },
            usage_info={
                "warnings": warnings,
                "alerts": alerts,
                "processing_time": result.metadata.get("processing_time", 0),
                "model_used": request.model or "glm-4-flash"
            },
            conversation_id=conversation_id,
            safety_filter_triggered=result.safety_filter_triggered
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"推理失败: {e}")
        raise HTTPException(status_code=500, detail=f"推理失败: {str(e)}")


@router.post("/stream")
async def stream_reasoning(
    request: ReasoningRequest,
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    流式推理输出

    Args:
        request: 推理请求
        current_user: 当前用户

    Returns:
        流式响应
    """
    async def generate_stream():
        try:
            tenant_id = current_user.id

            # 检查使用量限制
            can_proceed, warnings = await usage_monitoring_service.tracker.check_usage_limits(
                tenant_id, ProviderType.ZHIPU
            )
            if not canceed:
                yield f"data: {json.dumps({'type': 'error', 'message': '已达到使用量限制'})}\n\n"
                return

            # 发送开始标记
            yield f"data: {json.dumps({'type': 'start', 'query': request.query})}\n\n"

            # 执行推理
            result = await reasoning_engine.reason(
                query=request.query,
                context=request.context,
                data_sources=request.data_sources,
                tenant_id=tenant_id
            )

            # 发送推理步骤
            for step in result.reasoning_steps:
                step_data = {
                    'type': 'reasoning_step',
                    'step': {
                        'step_number': step.step_number,
                        'description': step.description,
                        'reasoning': step.reasoning
                    }
                }
                newline = "\n\n"
                yield f"data: {json.dumps(step_data)}{newline}"

            # 发送答案（分块）
            answer_chunks = [result.answer[i:i+100] for i in range(0, len(result.answer), 100)]
            for chunk in answer_chunks:
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                await asyncio.sleep(0.1)  # 模拟流式效果

            # 发送完成信息
            complete_data = {
                'type': 'complete',
                'confidence': result.confidence,
                'quality_score': result.quality_score,
                'sources': result.sources
            }
            newline = "\n\n"
            yield f"data: {json.dumps(complete_data)}{newline}"

        except Exception as e:
            logger.error(f"流式推理失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.post("/conversations", response_model=Dict[str, str])
async def create_conversation(
    request: ConversationCreateRequest,
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    创建新对话

    Args:
        request: 创建对话请求
        current_user: 当前用户

    Returns:
        对话ID
    """
    try:
        tenant_id = current_user.id

        conversation_id = await conversation_manager.create_conversation(
            tenant_id=tenant_id,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            metadata=request.metadata
        )

        return {"success": True, "conversation_id": conversation_id}

    except Exception as e:
        logger.error(f"创建对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建对话失败: {str(e)}")


@router.post("/conversations/{conversation_id}/messages")
async def add_conversation_message(
    conversation_id: str,
    request: ConversationMessageRequest,
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    添加对话消息

    Args:
        conversation_id: 对话ID
        request: 消息请求
        current_user: 当前用户

    Returns:
        操作结果
    """
    try:
        success = await conversation_manager.add_message(
            conversation_id=conversation_id,
            role=request.role,
            content=request.content,
            token_count=request.token_count,
            metadata=request.metadata
        )

        if success:
            return {"success": True, "message": "消息添加成功"}
        else:
            raise HTTPException(status_code=404, detail="对话不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加消息失败: {str(e)}")


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    获取对话信息

    Args:
        conversation_id: 对话ID
        current_user: 当前用户

    Returns:
        对话信息
    """
    try:
        context = await conversation_manager.get_conversation_context(conversation_id)
        if not context:
            raise HTTPException(status_code=404, detail="对话不存在")

        return {"success": True, "data": context}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取对话失败: {str(e)}")


@router.get("/conversations/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    获取对话历史

    Args:
        conversation_id: 对话ID
        limit: 限制数量
        offset: 偏移量
        current_user: 当前用户

    Returns:
        对话历史
    """
    try:
        history = await conversation_manager.get_conversation_history(
            conversation_id, limit, offset
        )

        return {"success": True, "data": {"messages": history, "total": len(history)}}

    except Exception as e:
        logger.error(f"获取对话历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}")


@router.get("/usage/statistics")
async def get_usage_statistics(
    period: str = "daily",
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    获取使用量统计

    Args:
        period: 统计周期 (daily, weekly, monthly)
        current_user: 当前用户

    Returns:
        使用量统计
    """
    try:
        tenant_id = current_user.id

        statistics = await usage_monitoring_service.tracker.get_usage_statistics(
            tenant_id=tenant_id,
            period=period
        )

        return {"success": True, "data": statistics}

    except Exception as e:
        logger.error(f"获取使用量统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取使用量统计失败: {str(e)}")


@router.get("/usage/limits")
async def get_usage_limits(
    current_user: Tenant = Depends(get_current_user_with_tenant)
):
    """
    获取使用量限制

    Args:
        current_user: 当前用户

    Returns:
        使用量限制信息
    """
    try:
        tenant_id = current_user.id

        current_usage = await usage_monitoring_service.tracker.get_current_usage(tenant_id)
        limits = await usage_monitoring_service.tracker._get_usage_limit(tenant_id)

        if limits:
            return {
                "success": True,
                "data": {
                    "current_usage": current_usage,
                    "limits": {
                        "daily_token_limit": limits.daily_token_limit,
                        "daily_api_limit": limits.daily_api_limit,
                        "monthly_token_limit": limits.monthly_token_limit,
                        "monthly_api_limit": limits.monthly_api_limit,
                        "cost_limit": limits.cost_limit,
                        "active": limits.active
                    }
                }
            }
        else:
            return {"success": True, "data": {"current_usage": current_usage, "limits": None}}

    except Exception as e:
        logger.error(f"获取使用量限制失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取使用量限制失败: {str(e)}")


@router.get("/health")
async def reasoning_health_check():
    """
    推理服务健康检查

    Returns:
        健康状态
    """
    try:
        # 检查各服务组件
        health_status = {
            "reasoning_engine": "healthy",
            "conversation_manager": "healthy",
            "usage_monitoring": "healthy"
        }

        # 检查内存使用
        memory_usage = usage_monitoring_service.tracker.get_memory_usage()
        health_status["memory_usage"] = memory_usage

        # 检查对话管理器状态
        conv_memory = conversation_manager.get_memory_usage()
        health_status["conversation_memory"] = conv_memory

        return {
            "status": "healthy",
            "timestamp": "2025-11-18T00:00:00Z",
            "services": health_status
        }

    except Exception as e:
        logger.error(f"推理服务健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "timestamp": "2025-11-18T00:00:00Z",
            "error": str(e)
        }