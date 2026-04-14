"""
# [WECHAT_WORK] 企业微信服务

## [HEADER]
**文件名**: wechat_work.py
**职责**: 封装企业微信API调用，实现消息发送、接收、加密解密等核心功能
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2025-03-22): 初始版本 - 企业微信双向通信集成

## [INPUT]
- **corp_id: str** - 企业ID
- **corp_secret: str** - 应用Secret
- **agent_id: int** - 应用ID
- **token: str** - 回调验证Token
- **encoding_aes_key: str** - 消息加密密钥
- **message: WechatMessage** - 消息对象

## [OUTPUT]
- **Dict[str, Any]**: API响应结果
- **str**: 加密/解密后的消息
- **bool**: 操作成功/失败状态

**上游依赖** (已读取源码):
- [./core/config.py](./core/config.py) - 配置管理（企业微信凭证）

**下游依赖**:
- [../api/v1/endpoints/wechat_work.py](../api/v1/endpoints/wechat_work.py) - 企业微信API端点

## [SIDE-EFFECTS]
- **HTTP请求**: 调用企业微信 REST API
- **异步操作**: async/await模式
- **加密解密**: 消息加解密操作

## [POS]
**路径**: backend/src/app/services/wechat_work.py
**模块层级**: Level 1 (服务层)
**依赖深度**: 直接依赖 core.config
"""

import json
import hashlib
import time
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import httpx
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad
import xml.etree.ElementTree as ET

from src.app.core.config import settings

logger = logging.getLogger(__name__)


class WechatWorkCrypto:
    """
    企业微信消息加解密类
    """

    def __init__(self, token: str, encoding_aes_key: str, corp_id: str):
        """
        初始化加解密类

        Args:
            token: 回调验证Token
            encoding_aes_key: 消息加密密钥
            corp_id: 企业ID
        """
        self.token = token
        self.encoding_aes_key = encoding_aes_key + "="
        self.corp_id = corp_id
        self.key = base64.b64decode(self.encoding_aes_key)

    def verify_signature(self, msg_signature: str, timestamp: str, nonce: str, encrypt: str) -> bool:
        """
        验证消息签名

        Args:
            msg_signature: 消息签名
            timestamp: 时间戳
            nonce: 随机数
            encrypt: 加密消息

        Returns:
            bool: 签名是否有效
        """
        try:
            # 按字典序排序
            sorted_params = sorted([self.token, timestamp, nonce, encrypt])
            sorted_str = ''.join(sorted_params)

            # SHA1加密
            sha1 = hashlib.sha1()
            sha1.update(sorted_str.encode('utf-8'))
            signature = sha1.hexdigest()

            return signature == msg_signature
        except Exception as e:
            logger.error(f"签名验证失败: {e}")
            return False

    def decrypt(self, encrypt: str) -> Optional[Dict[str, Any]]:
        """
        解密消息

        Args:
            encrypt: 加密的消息

        Returns:
            Dict: 解密后的消息，包含msg和corp_id
        """
        try:
            # Base64解码
            cipher_text = base64.b64decode(encrypt)

            # AES解密
            aes_cipher = AES.new(self.key, AES.MODE_CBC, self.key[:16])
            decrypted = aes_cipher.decrypt(cipher_text)

            # 去除padding
            decrypted = unpad(decrypted, AES.block_size)

            # 去除前16位随机字符串和后4位长度
            content = decrypted[16:]
            msg_len = int.from_bytes(content[:4], byteorder='big')
            msg = content[4:4 + msg_len].decode('utf-8')
            corp_id = content[4 + msg_len:].decode('utf-8')

            # 验证corp_id
            if corp_id != self.corp_id:
                logger.error(f"Corp ID不匹配: 期望{self.corp_id}, 实际{corp_id}")
                return None

            # 解析XML获取消息内容
            root = ET.fromstring(msg)
            message = {
                'ToUserName': root.find('ToUserName').text if root.find('ToUserName') is not None else '',
                'FromUserName': root.find('FromUserName').text if root.find('FromUserName') is not None else '',
                'CreateTime': root.find('CreateTime').text if root.find('CreateTime') is not None else '',
                'MsgType': root.find('MsgType').text if root.find('MsgType') is not None else '',
                'Content': root.find('Content').text if root.find('Content') is not None else '',
                'MsgId': root.find('MsgId').text if root.find('MsgId') is not None else '',
                'AgentID': root.find('AgentID').text if root.find('AgentID') is not None else '',
            }

            return message
        except Exception as e:
            logger.error(f"消息解密失败: {e}")
            return None

    def encrypt(self, msg: str) -> Optional[str]:
        """
        加密消息

        Args:
            msg: 要加密的消息

        Returns:
            str: 加密后的消息
        """
        try:
            # 生成16位随机字符串
            random_str = self._get_random_str(16)

            # 消息长度（4字节）
            msg_len = len(msg).to_bytes(4, byteorder='big')

            # 构建待加密文本
            text = random_str + msg_len + msg.encode('utf-8') + self.corp_id.encode('utf-8')

            # AES加密
            aes_cipher = AES.new(self.key, AES.MODE_CBC, self.key[:16])
            encrypted = aes_cipher.encrypt(pad(text, AES.block_size))

            # Base64编码
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"消息加密失败: {e}")
            return None

    def _get_random_str(self, length: int = 16) -> bytes:
        """生成随机字符串"""
        import secrets
        return secrets.token_bytes(length)


class WechatWorkAPI:
    """
    企业微信API客户端
    """

    def __init__(self, corp_id: str, corp_secret: str, agent_id: int):
        """
        初始化API客户端

        Args:
            corp_id: 企业ID
            corp_secret: 应用Secret
            agent_id: 应用ID
        """
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self.agent_id = agent_id
        self.base_url = "https://qyapi.weixin.qq.com"
        self.access_token = None
        self.token_expires_at = 0

    async def get_access_token(self) -> Optional[str]:
        """
        获取access_token

        Returns:
            str: access_token
        """
        try:
            # 检查token是否有效
            if self.access_token and time.time() < self.token_expires_at:
                return self.access_token

            # 获取新token
            url = f"{self.base_url}/cgi-bin/gettoken"
            params = {
                "corpid": self.corp_id,
                "corpsecret": self.corp_secret
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                result = response.json()

                if result.get("errcode") == 0:
                    self.access_token = result["access_token"]
                    # 提前5分钟过期
                    self.token_expires_at = time.time() + result["expires_in"] - 300
                    logger.info("成功获取企业微信access_token")
                    return self.access_token
                else:
                    logger.error(f"获取access_token失败: {result}")
                    return None
        except Exception as e:
            logger.error(f"获取access_token异常: {e}")
            return None

    async def send_message(
        self,
        user_id: str,
        msg_type: str,
        content: Dict[str, Any],
        agent_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        发送消息

        Args:
            user_id: 用户ID
            msg_type: 消息类型 (text, image, voice, video, file, textcard, news, mpnews, markdown)
            content: 消息内容
            agent_id: 应用ID（可选，默认使用初始化的agent_id）

        Returns:
            Dict: 发送结果
        """
        try:
            access_token = await self.get_access_token()
            if not access_token:
                return {"success": False, "error": "无法获取access_token"}

            url = f"{self.base_url}/cgi-bin/message/send?access_token={access_token}"

            # 构建消息体
            data = {
                "touser": user_id,
                "msgtype": msg_type,
                "agentid": agent_id or self.agent_id,
                msg_type: content
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, timeout=10.0)
                result = response.json()

                if result.get("errcode") == 0:
                    logger.info(f"消息发送成功: {user_id}")
                    return {"success": True, "data": result}
                else:
                    logger.error(f"消息发送失败: {result}")
                    return {"success": False, "error": result}

        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            return {"success": False, "error": str(e)}

    async def send_text(self, user_id: str, text: str, agent_id: Optional[int] = None) -> Dict[str, Any]:
        """
        发送文本消息

        Args:
            user_id: 用户ID
            text: 文本内容
            agent_id: 应用ID

        Returns:
            Dict: 发送结果
        """
        return await self.send_message(user_id, "text", {"content": text}, agent_id)

    async def send_markdown(
        self,
        user_id: str,
        content: str,
        agent_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        发送Markdown消息

        Args:
            user_id: 用户ID
            content: Markdown内容
            agent_id: 应用ID

        Returns:
            Dict: 发送结果
        """
        return await self.send_message(user_id, "markdown", {"content": content}, agent_id)

    async def send_text_card(
        self,
        user_id: str,
        title: str,
        description: str,
        url: str = "",
        btn_txt: str = "详情",
        agent_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        发送文本卡片消息

        Args:
            user_id: 用户ID
            title: 标题
            description: 描述
            url: 跳转链接
            btn_txt: 按钮文字
            agent_id: 应用ID

        Returns:
            Dict: 发送结果
        """
        content = {
            "title": title,
            "description": description,
            "url": url,
            "btntxt": btn_txt
        }
        return await self.send_message(user_id, "textcard", content, agent_id)

    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户信息

        Args:
            user_id: 用户ID

        Returns:
            Dict: 用户信息
        """
        try:
            access_token = await self.get_access_token()
            if not access_token:
                return None

            url = f"{self.base_url}/cgi-bin/user/get"
            params = {
                "access_token": access_token,
                "userid": user_id
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                result = response.json()

                if result.get("errcode") == 0:
                    return result
                else:
                    logger.error(f"获取用户信息失败: {result}")
                    return None
        except Exception as e:
            logger.error(f"获取用户信息异常: {e}")
            return None

    async def get_department_list(self, department_id: int = 1) -> Optional[List[Dict[str, Any]]]:
        """
        获取部门列表

        Args:
            department_id: 部门ID，默认为1（根部门）

        Returns:
            List: 部门列表
        """
        try:
            access_token = await self.get_access_token()
            if not access_token:
                return None

            url = f"{self.base_url}/cgi-bin/department/list"
            params = {
                "access_token": access_token,
                "id": department_id
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                result = response.json()

                if result.get("errcode") == 0:
                    return result.get("department", [])
                else:
                    logger.error(f"获取部门列表失败: {result}")
                    return None
        except Exception as e:
            logger.error(f"获取部门列表异常: {e}")
            return None


class WechatWorkService:
    """
    企业微信服务类
    整合API和加解密功能
    """

    def __init__(self):
        """初始化服务"""
        # 从配置获取参数
        corp_id = getattr(settings, 'wechat_work_corp_id', '')
        corp_secret = getattr(settings, 'wechat_work_corp_secret', '')
        agent_id = getattr(settings, 'wechat_work_agent_id', 0)
        token = getattr(settings, 'wechat_work_token', '')
        encoding_aes_key = getattr(settings, 'wechat_work_encoding_aes_key', '')

        if not all([corp_id, corp_secret, agent_id]):
            logger.warning("企业微信配置不完整，部分功能将不可用")

        self.api = WechatWorkAPI(corp_id, corp_secret, agent_id)
        self.crypto = WechatWorkCrypto(token, encoding_aes_key, corp_id) if token and encoding_aes_key else None

    async def check_connection(self) -> bool:
        """
        检查企业微信API连接状态

        Returns:
            bool: 连接是否成功
        """
        try:
            logger.info("正在测试企业微信API连接...")
            access_token = await self.api.get_access_token()
            if access_token:
                logger.info("企业微信API连接成功")
                return True
            else:
                logger.error("企业微信API连接失败: 无法获取access_token")
                return False
        except Exception as e:
            logger.error(f"企业微信API连接异常: {e}")
            return False

    def decrypt_callback_message(
        self,
        msg_signature: str,
        timestamp: str,
        nonce: str,
        encrypt: str
    ) -> Optional[Dict[str, Any]]:
        """
        解密回调消息

        Args:
            msg_signature: 消息签名
            timestamp: 时间戳
            nonce: 随机数
            encrypt: 加密消息

        Returns:
            Dict: 解密后的消息
        """
        if not self.crypto:
            logger.error("加密组件未初始化")
            return None

        # 验证签名
        if not self.crypto.verify_signature(msg_signature, timestamp, nonce, encrypt):
            logger.error("消息签名验证失败")
            return None

        # 解密消息
        message = self.crypto.decrypt(encrypt)
        if message:
            logger.info(f"成功解密消息: {message.get('MsgType')} from {message.get('FromUserName')}")
        return message

    def encrypt_callback_message(self, msg: str, nonce: str, timestamp: str) -> Optional[str]:
        """
        加密回调消息

        Args:
            msg: 原始消息
            nonce: 随机数
            timestamp: 时间戳

        Returns:
            str: 加密后的XML响应
        """
        if not self.crypto:
            logger.error("加密组件未初始化")
            return None

        try:
            encrypt_msg = self.crypto.encrypt(msg)
            if not encrypt_msg:
                return None

            # 生成签名
            sorted_params = sorted([self.crypto.token, timestamp, nonce, encrypt_msg])
            signature = hashlib.sha1(''.join(sorted_params).encode('utf-8')).hexdigest()

            # 构建XML响应
            xml = f"""
            <xml>
                <Encrypt><![CDATA[{encrypt_msg}]]></Encrypt>
                <MsgSignature><![CDATA[{signature}]]></MsgSignature>
                <TimeStamp>{timestamp}</TimeStamp>
                <Nonce><![CDATA[{nonce}]]></Nonce>
            </xml>
            """
            return xml
        except Exception as e:
            logger.error(f"加密回调消息失败: {e}")
            return None

    async def send_message(
        self,
        user_id: str,
        message: str,
        msg_type: str = "text"
    ) -> Dict[str, Any]:
        """
        发送消息到企业微信

        Args:
            user_id: 用户ID
            message: 消息内容
            msg_type: 消息类型

        Returns:
            Dict: 发送结果
        """
        try:
            if msg_type == "text":
                return await self.api.send_text(user_id, message)
            elif msg_type == "markdown":
                return await self.api.send_markdown(user_id, message)
            else:
                return await self.api.send_message(user_id, msg_type, {"content": message})
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return {"success": False, "error": str(e)}

    async def handle_callback_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理回调消息

        Args:
            message: 消息对象

        Returns:
            Dict: 处理结果
        """
        try:
            msg_type = message.get("MsgType", "")
            from_user = message.get("FromUserName", "")
            content = message.get("Content", "")

            logger.info(f"收到企业微信消息: 类型={msg_type}, 发送者={from_user}, 内容={content}")

            # TODO: 在这里添加业务逻辑处理
            # 例如：调用AI服务处理用户消息

            # 示例：简单的回复
            response_content = f"收到您的消息: {content}"
            await self.send_message(from_user, response_content)

            return {
                "success": True,
                "message": "消息已处理",
                "from_user": from_user,
                "content": content
            }
        except Exception as e:
            logger.error(f"处理回调消息失败: {e}")
            return {"success": False, "error": str(e)}


# 全局企业微信服务实例
wechat_work_service = WechatWorkService()
