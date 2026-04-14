"""
# [ENDPOINT_WECHAT_WORK] 企业微信 API 端点

## [HEADER]
**文件名**: wechat_work.py
**职责**: 企业微信相关的 API 端点
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2025-03-22): 初始版本 - 企业微信API端点

## [INPUT]
- HTTP 请求 (企业微信回调、用户发送消息等)

## [OUTPUT]
- HTTP 响应 (JSON/XML)

## [LINK]
**上游依赖**:
- [../../../services/wechat_work.py](../../../services/wechat_work.py) - 企业微信服务
- [../../../schemas/wechat_work.py](../../../schemas/wechat_work.py) - 数据模型

**下游依赖**:
- None (终端端点)

**调用方**:
- 企业微信服务器 (回调)
- 前端应用 (发送消息)

## [POS]
**路径**: backend/src/app/api/v1/endpoints/wechat_work.py
**模块层级**: Level 3 (API端点层)
"""

import xml.etree.ElementTree as ET
from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import Response, JSONResponse
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import time

from src.app.schemas.wechat_work import (
    WechatWorkSendMessage,
    WechatWorkSendMessageResponse,
    WechatWorkCheckResponse,
    WechatWorkUserInfo,
    WechatWorkDepartment,
)
from src.app.services.wechat_work import wechat_work_service
from src.app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Wechat Work"])


@router.get("/callback", summary="企业微信回调验证")
async def wechat_callback_verify(
    msg_signature: str,
    timestamp: str,
    nonce: str,
    echostr: str
) -> Response:
    """
    企业微信回调验证接口

    用于验证企业微信回调URL的有效性。

    Args:
        msg_signature: 消息签名
        timestamp: 时间戳
        nonce: 随机数
        echostr: 随机字符串

    Returns:
        Response: 原样返回echostr
    """
    try:
        logger.info("收到企业微信验证请求")

        # 解密验证
        message = wechat_work_service.decrypt_callback_message(
            msg_signature, timestamp, nonce, echostr
        )

        if message:
            # 验证成功，返回解密后的内容
            logger.info("企业微信验证成功")
            return Response(content=echostr, media_type="text/plain")
        else:
            logger.error("企业微信验证失败")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="验证失败"
            )
    except Exception as e:
        logger.error(f"企业微信验证异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/callback", summary="企业微信消息回调")
async def wechat_callback(request: Request) -> Response:
    """
    企业微信消息回调接口

    接收企业微信推送的消息，处理后返回响应。

    Returns:
        Response: XML格式的响应
    """
    try:
        # 读取请求体
        body = await request.body()
        logger.info(f"收到企业微信消息回调: {len(body)} bytes")

        # 解析XML
        root = ET.fromstring(body)
        msg_signature = root.find('MsgSignature').text
        timestamp = root.find('TimeStamp').text
        nonce = root.find('Nonce').text
        encrypt = root.find('Encrypt').text

        # 解密消息
        message = wechat_work_service.decrypt_callback_message(
            msg_signature, timestamp, nonce, encrypt
        )

        if not message:
            logger.error("消息解密失败")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="消息解密失败"
            )

        logger.info(f"解密成功: {message.get('MsgType')} from {message.get('FromUserName')}")

        # 处理消息
        result = await wechat_work_service.handle_callback_message(message)

        # 构建响应
        if result.get("success"):
            reply_content = "success"
        else:
            reply_content = "error"

        # 加密响应
        response_xml = wechat_work_service.encrypt_callback_message(
            reply_content,
            nonce,
            timestamp
        )

        if response_xml:
            return Response(content=response_xml, media_type="application/xml")
        else:
            # 加密失败，返回空响应
            return Response(content="", media_type="application/xml")

    except Exception as e:
        logger.error(f"处理企业微信回调异常: {e}")
        # 即使出错也返回success，避免企业微信重复推送
        return Response(content="success", media_type="text/plain")


@router.post("/send", response_model=WechatWorkSendMessageResponse, summary="发送企业微信消息")
async def send_message(message_data: WechatWorkSendMessage) -> WechatWorkSendMessageResponse:
    """
    发送消息到企业微信

    支持发送文本、Markdown和文本卡片消息。

    Args:
        message_data: 消息数据

    Returns:
        WechatWorkSendMessageResponse: 发送结果
    """
    try:
        logger.info(f"发送企业微信消息: {message_data.user_id}, 类型: {message_data.msg_type}")

        # 根据消息类型发送
        if message_data.msg_type == "textcard":
            result = await wechat_work_service.api.send_text_card(
                user_id=message_data.user_id,
                title=message_data.title or "通知",
                description=message_data.description or message_data.message,
                url=message_data.url or "",
                btn_txt=message_data.btn_txt or "详情"
            )
        elif message_data.msg_type == "markdown":
            result = await wechat_work_service.api.send_markdown(
                user_id=message_data.user_id,
                content=message_data.message
            )
        else:  # text
            result = await wechat_work_service.api.send_text(
                user_id=message_data.user_id,
                text=message_data.message
            )

        if result.get("success"):
            return WechatWorkSendMessageResponse(
                success=True,
                message="消息发送成功",
                data=result.get("data")
            )
        else:
            return WechatWorkSendMessageResponse(
                success=False,
                message="消息发送失败",
                error=result.get("error")
            )

    except Exception as e:
        logger.error(f"发送消息异常: {e}")
        return WechatWorkSendMessageResponse(
            success=False,
            message="发送消息时发生异常",
            error=str(e)
        )


@router.get("/check", response_model=WechatWorkCheckResponse, summary="检查企业微信连接")
async def check_connection() -> WechatWorkCheckResponse:
    """
    检查企业微信API连接状态

    Returns:
        WechatWorkCheckResponse: 连接状态
    """
    try:
        # 检查是否启用
        enabled = getattr(wechat_work_service.api, 'corp_id', None) is not None

        if not enabled:
            return WechatWorkCheckResponse(
                enabled=False,
                connected=False,
                message="企业微信未配置"
            )

        # 检查连接
        connected = await wechat_work_service.check_connection()

        if connected:
            return WechatWorkCheckResponse(
                enabled=True,
                connected=True,
                message="企业微信连接正常"
            )
        else:
            return WechatWorkCheckResponse(
                enabled=True,
                connected=False,
                message="企业微信连接失败"
            )

    except Exception as e:
        logger.error(f"检查连接异常: {e}")
        return WechatWorkCheckResponse(
            enabled=False,
            connected=False,
            message=f"检查连接时发生异常: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=WechatWorkUserInfo, summary="获取用户信息")
async def get_user_info(user_id: str) -> WechatWorkUserInfo:
    """
    获取企业微信用户信息

    Args:
        user_id: 用户ID

    Returns:
        WechatWorkUserInfo: 用户信息
    """
    try:
        logger.info(f"获取用户信息: {user_id}")

        user_info = await wechat_work_service.api.get_user_info(user_id)

        if user_info:
            return WechatWorkUserInfo(
                user_id=user_info.get("userid", ""),
                name=user_info.get("name", ""),
                department=user_info.get("department", []),
                mobile=user_info.get("mobile"),
                email=user_info.get("email"),
                status=user_info.get("status", 1),
                enable=user_info.get("enable", 1),
                avatar=user_info.get("avatar")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/departments", summary="获取部门列表")
async def get_departments(department_id: int = 1) -> list[WechatWorkDepartment]:
    """
    获取企业微信部门列表

    Args:
        department_id: 部门ID，默认为1（根部门）

    Returns:
        List[WechatWorkDepartment]: 部门列表
    """
    try:
        logger.info(f"获取部门列表: {department_id}")

        departments = await wechat_work_service.api.get_department_list(department_id)

        if departments:
            return [
                WechatWorkDepartment(
                    id=dept.get("id"),
                    name=dept.get("name"),
                    parent_id=dept.get("parentid"),
                    order=dept.get("order", 0)
                )
                for dept in departments
            ]
        else:
            return []

    except Exception as e:
        logger.error(f"获取部门列表异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/test/send", summary="测试发送消息")
async def test_send_message(user_id: str, message: str = "这是一条测试消息") -> Dict[str, Any]:
    """
    测试发送企业微信消息

    用于开发调试，快速测试消息发送功能。

    Args:
        user_id: 用户ID
        message: 测试消息内容

    Returns:
        Dict: 发送结果
    """
    try:
        logger.info(f"测试发送消息: {user_id}")

        result = await wechat_work_service.api.send_text(user_id, message)

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
        logger.error(f"测试发送消息异常: {e}")
        return {
            "success": False,
            "message": "测试发送消息时发生异常",
            "error": str(e)
        }
