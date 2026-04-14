"""
# [WECHAT_WEBHOOK] 企业微信群机器人服务

## [HEADER]
**文件名**: wechat_webhook.py
**职责**: 企业微信群机器人消息发送（简单Webhook方式）
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2025-03-22): 初始版本 - 群机器人Webhook发送

## [INPUT]
- webhook_url: 群机器人Webhook URL
- message: 消息内容

## [OUTPUT]
- Dict: 发送结果

## [POS]
**路径**: backend/src/app/services/wechat_webhook.py
"""

import logging
import httpx
from typing import Dict, Any, Optional, List
from src.app.core.config import settings

logger = logging.getLogger(__name__)


class WechatWebhookService:
    """
    企业微信群机器人服务
    使用Webhook方式发送消息到企业微信群
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        初始化服务

        Args:
            webhook_url: 群机器人Webhook URL，如果不提供则从配置读取
        """
        self.webhook_url = webhook_url or getattr(settings, 'wechat_webhook_url', None)

    async def send_text(self, content: str, mentioned_list: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        发送文本消息

        Args:
            content: 文本内容
            mentioned_list: @的用户列表，如 ["user1", "user2"] 或 ["@all"] @所有人

        Returns:
            Dict: 发送结果
        """
        if not self.webhook_url:
            return {
                "success": False,
                "error": "未配置群机器人Webhook URL"
            }

        try:
            data = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }

            if mentioned_list:
                data["text"]["mentioned_list"] = mentioned_list

            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=data, timeout=10.0)
                result = response.json()

                if result.get("errcode") == 0:
                    logger.info(f"群机器人消息发送成功")
                    return {"success": True, "data": result}
                else:
                    logger.error(f"群机器人消息发送失败: {result}")
                    return {"success": False, "error": result}

        except Exception as e:
            logger.error(f"群机器人发送消息异常: {e}")
            return {"success": False, "error": str(e)}

    async def send_markdown(self, content: str) -> Dict[str, Any]:
        """
        发送Markdown消息

        Args:
            content: Markdown格式内容

        Returns:
            Dict: 发送结果
        """
        if not self.webhook_url:
            return {
                "success": False,
                "error": "未配置群机器人Webhook URL"
            }

        try:
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": content
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=data, timeout=10.0)
                result = response.json()

                if result.get("errcode") == 0:
                    logger.info(f"群机器人Markdown消息发送成功")
                    return {"success": True, "data": result}
                else:
                    logger.error(f"群机器人Markdown消息发送失败: {result}")
                    return {"success": False, "error": result}

        except Exception as e:
            logger.error(f"群机器人发送Markdown消息异常: {e}")
            return {"success": False, "error": str(e)}

    async def send_image(self, base64_content: str, md5: str) -> Dict[str, Any]:
        """
        发送图片消息

        Args:
            base64_content: 图片base64编码
            md5: 图片MD5值

        Returns:
            Dict: 发送结果
        """
        if not self.webhook_url:
            return {
                "success": False,
                "error": "未配置群机器人Webhook URL"
            }

        try:
            data = {
                "msgtype": "image",
                "image": {
                    "base64": base64_content,
                    "md5": md5
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=data, timeout=10.0)
                result = response.json()

                if result.get("errcode") == 0:
                    logger.info(f"群机器人图片消息发送成功")
                    return {"success": True, "data": result}
                else:
                    logger.error(f"群机器人图片消息发送失败: {result}")
                    return {"success": False, "error": result}

        except Exception as e:
            logger.error(f"群机器人发送图片消息异常: {e}")
            return {"success": False, "error": str(e)}

    async def send_news(self, articles: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        发送图文消息

        Args:
            articles: 图文消息列表，每个元素包含 title, description, url, picurl

        Returns:
            Dict: 发送结果
        """
        if not self.webhook_url:
            return {
                "success": False,
                "error": "未配置群机器人Webhook URL"
            }

        try:
            data = {
                "msgtype": "news",
                "news": {
                    "articles": articles
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=data, timeout=10.0)
                result = response.json()

                if result.get("errcode") == 0:
                    logger.info(f"群机器人图文消息发送成功")
                    return {"success": True, "data": result}
                else:
                    logger.error(f"群机器人图文消息发送失败: {result}")
                    return {"success": False, "error": result}

        except Exception as e:
            logger.error(f"群机器人发送图文消息异常: {e}")
            return {"success": False, "error": str(e)}

    async def send_file(self, key: str, filename: str, file_size: int) -> Dict[str, Any]:
        """
        发送文件消息

        Args:
            key: 媒体文件ID，通过上传素材接口获取
            filename: 文件名
            file_size: 文件大小（字节）

        Returns:
            Dict: 发送结果
        """
        if not self.webhook_url:
            return {
                "success": False,
                "error": "未配置群机器人Webhook URL"
            }

        try:
            data = {
                "msgtype": "file",
                "file": {
                    "media_id": key
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=data, timeout=10.0)
                result = response.json()

                if result.get("errcode") == 0:
                    logger.info(f"群机器人文件消息发送成功")
                    return {"success": True, "data": result}
                else:
                    logger.error(f"群机器人文件消息发送失败: {result}")
                    return {"success": False, "error": result}

        except Exception as e:
            logger.error(f"群机器人发送文件消息异常: {e}")
            return {"success": False, "error": str(e)}


# 全局群机器人服务实例
wechat_webhook_service = WechatWebhookService()
