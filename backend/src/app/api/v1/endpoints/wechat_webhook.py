"""
# [ENDPOINT_WECHAT_WEBHOOK] 企业微信群机器人 API 端点

## [HEADER]
**文件名**: wechat_webhook.py
**职责**: 企业微信群机器人消息发送 API
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2025-03-22): 初始版本

## [INPUT]
- HTTP 请求 (发送消息)

## [OUTPUT]
- HTTP 响应 (JSON)

## [POS]
**路径**: backend/src/app/api/v1/endpoints/wechat_webhook.py
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging

from src.app.services.wechat_webhook import wechat_webhook_service
from src.app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Wechat Webhook"])


class SendTextRequest(BaseModel):
    """发送文本消息请求"""
    content: str = Field(..., description="消息内容")
    mentioned_list: Optional[List[str]] = Field(None, description="@的用户列表，如 ['user1'] 或 ['@all']")


class SendMarkdownRequest(BaseModel):
    """发送Markdown消息请求"""
    content: str = Field(..., description="Markdown格式内容")


class SendImageRequest(BaseModel):
    """发送图片消息请求"""
    base64: str = Field(..., description="图片base64编码")
    md5: str = Field(..., description="图片MD5值")


class SendNewsRequest(BaseModel):
    """发送图文消息请求"""
    articles: List[Dict[str, str]] = Field(..., description="图文消息列表")


@router.post("/send-text", summary="发送文本消息到企业微信群")
async def send_text(request: SendTextRequest) -> Dict[str, Any]:
    """
    发送文本消息到企业微信群

    支持普通文本和@用户功能。

    示例:
    ```
    POST /api/v1/wechat-webhook/send-text
    {
        "content": "大家好，这是一条测试消息",
        "mentioned_list": ["@all"]  // @所有人
    }
    ```
    """
    try:
        logger.info(f"发送群机器人文本消息: {request.content[:50]}...")

        result = await wechat_webhook_service.send_text(
            content=request.content,
            mentioned_list=request.mentioned_list
        )

        if result.get("success"):
            return {
                "success": True,
                "message": "消息发送成功",
                "data": result.get("data")
            }
        else:
            return {
                "success": False,
                "message": "消息发送失败",
                "error": result.get("error")
            }

    except Exception as e:
        logger.error(f"发送文本消息异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-markdown", summary="发送Markdown消息到企业微信群")
async def send_markdown(request: SendMarkdownRequest) -> Dict[str, Any]:
    """
    发送Markdown消息到企业微信群

    支持Markdown格式化文本。

    示例:
    ```
    POST /api/v1/wechat-webhook/send-markdown
    {
        "content": "## 标题\\n\\n**加粗** 和 *斜体*\\n\\n- 列表项1\\n- 列表项2"
    }
    ```
    """
    try:
        logger.info(f"发送群机器人Markdown消息")

        result = await wechat_webhook_service.send_markdown(request.content)

        if result.get("success"):
            return {
                "success": True,
                "message": "Markdown消息发送成功",
                "data": result.get("data")
            }
        else:
            return {
                "success": False,
                "message": "Markdown消息发送失败",
                "error": result.get("error")
            }

    except Exception as e:
        logger.error(f"发送Markdown消息异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-news", summary="发送图文消息到企业微信群")
async def send_news(request: SendNewsRequest) -> Dict[str, Any]:
    """
    发送图文消息到企业微信群

    示例:
    ```
    POST /api/v1/wechat-webhook/send-news
    {
        "articles": [
            {
                "title": "标题",
                "description": "描述",
                "url": "https://example.com",
                "picurl": "https://example.com/image.jpg"
            }
        ]
    }
    ```
    """
    try:
        logger.info(f"发送群机器人图文消息")

        result = await wechat_webhook_service.send_news(request.articles)

        if result.get("success"):
            return {
                "success": True,
                "message": "图文消息发送成功",
                "data": result.get("data")
            }
        else:
            return {
                "success": False,
                "message": "图文消息发送失败",
                "error": result.get("error")
            }

    except Exception as e:
        logger.error(f"发送图文消息异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", summary="测试群机器人消息")
async def test_webhook() -> Dict[str, Any]:
    """
    测试群机器人消息发送

    发送一条简单的测试消息。
    """
    try:
        test_message = "🤖 测试消息：Data Agent 企业微信集成已就绪！"

        result = await wechat_webhook_service.send_text(test_message)

        if result.get("success"):
            return {
                "success": True,
                "message": "测试消息发送成功",
                "data": result.get("data")
            }
        else:
            return {
                "success": False,
                "message": "测试消息发送失败",
                "error": result.get("error")
            }

    except Exception as e:
        logger.error(f"测试消息发送异常: {e}")
        return {
            "success": False,
            "message": "测试消息发送异常",
            "error": str(e)
        }
