"""
对话管理服务
管理多轮对话、上下文窗口、对话状态等
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from src.app.core.config import settings
from src.app.data.database import get_db
# Note: ChatMessage and ConversationHistory are Pydantic models, not database models

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """对话状态枚举"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class ConversationContext:
    """对话上下文"""
    conversation_id: str
    tenant_id: str
    user_id: str
    state: ConversationState = ConversationState.ACTIVE
    messages: List[Dict[str, Any]] = field(default_factory=list)
    context_window: List[Dict[str, Any]] = field(default_factory=list)
    summary: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 配置参数
    max_context_messages: int = 10
    max_context_tokens: int = 8000
    context_compression_threshold: int = 15
    auto_summary_enabled: bool = True


@dataclass
class MessageTemplate:
    """消息模板"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversationManager:
    """对话管理器"""

    def __init__(self):
        self.conversations: Dict[str, ConversationContext] = {}
        self.context_windows: Dict[str, List[Dict[str, Any]]] = {}
        self.default_config = {
            "max_context_messages": 10,
            "max_context_tokens": 8000,
            "context_compression_threshold": 15,
            "auto_summary_enabled": True,
            "summary_interval_minutes": 30
        }

    async def create_conversation(
        self,
        tenant_id: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        创建新对话

        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            conversation_id: 对话ID，可选
            metadata: 元数据

        Returns:
            对话ID
        """
        try:
            if not conversation_id:
                conversation_id = f"conv_{tenant_id}_{int(time.time())}"

            context = ConversationContext(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                user_id=user_id,
                metadata=metadata or {}
            )

            # 应用默认配置
            for key, value in self.default_config.items():
                if hasattr(context, key):
                    setattr(context, key, value)

            self.conversations[conversation_id] = context

            # 持久化到数据库
            await self._persist_conversation(context)

            logger.info(f"创建新对话: {conversation_id} for tenant: {tenant_id}")
            return conversation_id

        except Exception as e:
            logger.error(f"创建对话失败: {e}")
            raise

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        token_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        添加消息到对话

        Args:
            conversation_id: 对话ID
            role: 角色 ("user", "assistant", "system")
            content: 消息内容
            token_count: Token数量
            metadata: 元数据

        Returns:
            是否成功添加
        """
        try:
            context = self.conversations.get(conversation_id)
            if not context:
                logger.warning(f"对话不存在: {conversation_id}")
                return False

            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "token_count": token_count,
                "metadata": metadata or {}
            }

            # 添加到消息历史
            context.messages.append(message)
            context.updated_at = datetime.utcnow()

            # 更新上下文窗口
            await self._update_context_window(context)

            # 检查是否需要摘要生成
            if context.auto_summary_enabled:
                await self._check_and_generate_summary(context)

            # 持久化消息
            await self._persist_message(conversation_id, message)

            logger.debug(f"添加消息到对话 {conversation_id}: {role} - {len(content)} 字符")
            return True

        except Exception as e:
            logger.error(f"添加消息失败: {e}")
            return False

    async def get_conversation_context(
        self,
        conversation_id: str,
        include_summary: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        获取对话上下文

        Args:
            conversation_id: 对话ID
            include_summary: 是否包含摘要

        Returns:
            对话上下文数据
        """
        try:
            context = self.conversations.get(conversation_id)
            if not context:
                return None

            result = {
                "conversation_id": context.conversation_id,
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                "state": context.state.value,
                "context_window": context.context_window,
                "message_count": len(context.messages),
                "created_at": context.created_at.isoformat(),
                "updated_at": context.updated_at.isoformat(),
                "metadata": context.metadata
            }

            if include_summary and context.summary:
                result["summary"] = context.summary

            return result

        except Exception as e:
            logger.error(f"获取对话上下文失败: {e}")
            return None

    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取对话历史

        Args:
            conversation_id: 对话ID
            limit: 限制数量
            offset: 偏移量

        Returns:
            消息历史列表
        """
        try:
            context = self.conversations.get(conversation_id)
            if not context:
                return []

            messages = context.messages[offset:offset + limit]
            return messages

        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            return []

    async def update_conversation_state(
        self,
        conversation_id: str,
        state: ConversationState
    ) -> bool:
        """
        更新对话状态

        Args:
            conversation_id: 对话ID
            state: 新状态

        Returns:
            是否成功更新
        """
        try:
            context = self.conversations.get(conversation_id)
            if not context:
                return False

            context.state = state
            context.updated_at = datetime.utcnow()

            await self._persist_conversation(context)
            logger.info(f"更新对话状态 {conversation_id}: {state.value}")
            return True

        except Exception as e:
            logger.error(f"更新对话状态失败: {e}")
            return False

    async def clear_conversation(
        self,
        conversation_id: str,
        archive: bool = True
    ) -> bool:
        """
        清空对话

        Args:
            conversation_id: 对话ID
            archive: 是否归档

        Returns:
            是否成功清空
        """
        try:
            context = self.conversations.get(conversation_id)
            if not context:
                return False

            if archive:
                # 归档对话
                await self.update_conversation_state(conversation_id, ConversationState.ARCHIVED)
            else:
                # 完全删除
                del self.conversations[conversation_id]
                if conversation_id in self.context_windows:
                    del self.context_windows[conversation_id]

                # 从数据库删除
                await self._delete_conversation_from_db(conversation_id)

            logger.info(f"清空对话: {conversation_id} (归档: {archive})")
            return True

        except Exception as e:
            logger.error(f"清空对话失败: {e}")
            return False

    async def _update_context_window(self, context: ConversationContext):
        """
        更新上下文窗口

        Args:
            context: 对话上下文
        """
        try:
            messages = context.messages

            # 如果消息数量超过阈值，进行上下文压缩
            if len(messages) > context.context_compression_threshold:
                await self._compress_context(context)
            else:
                # 直接使用最近的N条消息
                context.context_window = messages[-context.max_context_messages:]

            # 检查token限制
            total_tokens = sum(msg.get("token_count", 0) for msg in context.context_window)
            if total_tokens > context.max_context_tokens:
                await self._trim_context_by_tokens(context)

        except Exception as e:
            logger.error(f"更新上下文窗口失败: {e}")

    async def _compress_context(self, context: ConversationContext):
        """
        压缩上下文

        Args:
            context: 对话上下文
        """
        try:
            # 分离系统消息和对话消息
            system_messages = [msg for msg in context.messages if msg["role"] == "system"]
            conversation_messages = [msg for msg in context.messages if msg["role"] != "system"]

            # 保留最近的对话消息
            recent_messages = conversation_messages[-context.max_context_messages:]

            # 合并系统消息和最近对话
            context.context_window = system_messages + recent_messages

            logger.debug(f"压缩对话上下文: {context.conversation_id}")

        except Exception as e:
            logger.error(f"压缩上下文失败: {e}")

    async def _trim_context_by_tokens(self, context: ConversationContext):
        """
        按Token数裁剪上下文

        Args:
            context: 对话上下文
        """
        try:
            current_tokens = sum(msg.get("token_count", 0) for msg in context.context_window)

            # 从最老的消息开始删除
            while current_tokens > context.max_context_tokens and len(context.context_window) > 1:
                removed_message = context.context_window.pop(0)
                current_tokens -= removed_message.get("token_count", 0)

            logger.debug(f"按Token裁剪上下文: {context.conversation_id}")

        except Exception as e:
            logger.error(f"按Token裁剪上下文失败: {e}")

    async def _check_and_generate_summary(self, context: ConversationContext):
        """
        检查并生成摘要

        Args:
            context: 对话上下文
        """
        try:
            # 检查是否需要生成摘要
            time_since_last_update = datetime.utcnow() - context.updated_at

            should_generate = (
                len(context.messages) >= context.context_compression_threshold or
                time_since_last_update.total_seconds() >= self.default_config["summary_interval_minutes"] * 60
            )

            if should_generate and not context.summary:
                await self._generate_conversation_summary(context)

        except Exception as e:
            logger.error(f"检查摘要生成失败: {e}")

    async def _generate_conversation_summary(self, context: ConversationContext):
        """
        生成对话摘要

        Args:
            context: 对话上下文
        """
        try:
            # 这里可以调用LLM服务生成摘要
            # 暂时使用简单的摘要逻辑
            user_messages = [msg["content"] for msg in context.messages if msg["role"] == "user"]

            if user_messages:
                # 简单摘要：取前几个用户问题的关键词
                summary_content = "用户询问了关于: " + ", ".join([
                    msg[:50] + "..." if len(msg) > 50 else msg
                    for msg in user_messages[:3]
                ])
                context.summary = summary_content

            logger.debug(f"生成对话摘要: {context.conversation_id}")

        except Exception as e:
            logger.error(f"生成对话摘要失败: {e}")

    async def _persist_conversation(self, context: ConversationContext):
        """持久化对话到数据库"""
        try:
            # 这里实现数据库持久化逻辑
            # 由于需要数据库模型，暂时跳过实际实现
            pass
        except Exception as e:
            logger.error(f"持久化对话失败: {e}")

    async def _persist_message(self, conversation_id: str, message: Dict[str, Any]):
        """持久化消息到数据库"""
        try:
            # 这里实现消息数据库持久化逻辑
            # 由于需要数据库模型，暂时跳过实际实现
            pass
        except Exception as e:
            logger.error(f"持久化消息失败: {e}")

    async def _delete_conversation_from_db(self, conversation_id: str):
        """从数据库删除对话"""
        try:
            # 这里实现数据库删除逻辑
            # 由于需要数据库模型，暂时跳过实际实现
            pass
        except Exception as e:
            logger.error(f"从数据库删除对话失败: {e}")

    async def get_conversation_statistics(
        self,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取对话统计信息

        Args:
            tenant_id: 租户ID，可选

        Returns:
            统计信息
        """
        try:
            conversations = [
                conv for conv in self.conversations.values()
                if tenant_id is None or conv.tenant_id == tenant_id
            ]

            total_conversations = len(conversations)
            active_conversations = len([c for c in conversations if c.state == ConversationState.ACTIVE])
            total_messages = sum(len(c.messages) for c in conversations)

            return {
                "total_conversations": total_conversations,
                "active_conversations": active_conversations,
                "total_messages": total_messages,
                "average_messages_per_conversation": total_messages / max(total_conversations, 1)
            }

        except Exception as e:
            logger.error(f"获取对话统计失败: {e}")
            return {}

    async def cleanup_old_conversations(self, days: int = 30):
        """
        清理旧对话

        Args:
            days: 保留天数
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            old_conversations = [
                conv_id for conv_id, conv in self.conversations.items()
                if conv.updated_at < cutoff_date
            ]

            for conv_id in old_conversations:
                await self.clear_conversation(conv_id, archive=True)

            logger.info(f"清理了 {len(old_conversations)} 个旧对话")

        except Exception as e:
            logger.error(f"清理旧对话失败: {e}")

    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        try:
            total_messages = sum(len(conv.messages) for conv in self.conversations.values())
            total_context_size = sum(len(conv.context_window) for conv in self.conversations.values())

            return {
                "active_conversations": len(self.conversations),
                "total_messages": total_messages,
                "total_context_size": total_context_size,
                "average_messages_per_conversation": total_messages / max(len(self.conversations), 1)
            }

        except Exception as e:
            logger.error(f"获取内存使用情况失败: {e}")
            return {}


# 全局对话管理器实例
conversation_manager = ConversationManager()