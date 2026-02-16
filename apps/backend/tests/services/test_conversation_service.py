"""
对话管理服务测试
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.app.services.conversation_service import (
    conversation_manager,
    ConversationManager,
    ConversationContext,
    ConversationState,
    MessageTemplate
)


class TestConversationManager:
    """对话管理器测试"""

    @pytest.fixture
    def manager(self):
        return ConversationManager()

    @pytest.mark.asyncio
    async def test_create_conversation(self, manager):
        """测试创建对话"""
        tenant_id = "test_tenant"
        user_id = "test_user"
        conversation_id = await manager.create_conversation(tenant_id, user_id)

        assert conversation_id is not None
        assert conversation_id.startswith("conv_")
        assert conversation_id in manager.conversations

        context = manager.conversations[conversation_id]
        assert context.tenant_id == tenant_id
        assert context.user_id == user_id
        assert context.state == ConversationState.ACTIVE
        assert len(context.messages) == 0

    @pytest.mark.asyncio
    async def test_create_conversation_with_custom_id(self, manager):
        """测试使用自定义ID创建对话"""
        tenant_id = "test_tenant"
        user_id = "test_user"
        custom_id = "custom_conv_123"

        conversation_id = await manager.create_conversation(tenant_id, user_id, custom_id)

        assert conversation_id == custom_id
        assert custom_id in manager.conversations

    @pytest.mark.asyncio
    async def test_add_message_to_conversation(self, manager):
        """测试向对话添加消息"""
        # 先创建对话
        conversation_id = await manager.create_conversation("test_tenant", "test_user")

        # 添加用户消息
        success = await manager.add_message(
            conversation_id=conversation_id,
            role="user",
            content="你好，我想了解AI技术",
            token_count=20
        )

        assert success is True

        context = manager.conversations[conversation_id]
        assert len(context.messages) == 1
        assert context.messages[0]["role"] == "user"
        assert context.messages[0]["content"] == "你好，我想了解AI技术"
        assert context.messages[0]["token_count"] == 20

        # 添加助手回复
        success = await manager.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content="您好！AI技术是一个很广泛的话题...",
            token_count=50,
            metadata={"model": "glm-4"}
        )

        assert success is True
        assert len(context.messages) == 2
        assert context.messages[1]["role"] == "assistant"
        assert context.messages[1]["metadata"]["model"] == "glm-4"

    @pytest.mark.asyncio
    async def test_add_message_to_nonexistent_conversation(self, manager):
        """测试向不存在的对话添加消息"""
        success = await manager.add_message(
            conversation_id="nonexistent_id",
            role="user",
            content="测试消息"
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_get_conversation_context(self, manager):
        """测试获取对话上下文"""
        # 创建对话并添加消息
        conversation_id = await manager.create_conversation("test_tenant", "test_user")
        await manager.add_message(conversation_id, "user", "测试问题")
        await manager.add_message(conversation_id, "assistant", "测试回答")

        context = await manager.get_conversation_context(conversation_id)

        assert context is not None
        assert context["conversation_id"] == conversation_id
        assert context["tenant_id"] == "test_tenant"
        assert context["state"] == ConversationState.ACTIVE.value
        assert context["message_count"] == 2
        assert "context_window" in context
        assert "created_at" in context
        assert "updated_at" in context

    @pytest.mark.asyncio
    async def test_get_conversation_context_nonexistent(self, manager):
        """测试获取不存在对话的上下文"""
        context = await manager.get_conversation_context("nonexistent_id")
        assert context is None

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, manager):
        """测试获取对话历史"""
        conversation_id = await manager.create_conversation("test_tenant", "test_user")

        # 添加多条消息
        messages = [
            ("user", "第一个问题"),
            ("assistant", "第一个回答"),
            ("user", "第二个问题"),
            ("assistant", "第二个回答"),
            ("user", "第三个问题")
        ]

        for role, content in messages:
            await manager.add_message(conversation_id, role, content)

        # 获取历史
        history = await manager.get_conversation_history(conversation_id)

        assert len(history) == 5
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "第一个问题"
        assert history[-1]["content"] == "第三个问题"

        # 测试分页
        history_page = await manager.get_conversation_history(conversation_id, limit=2, offset=1)
        assert len(history_page) == 2
        assert history_page[0]["content"] == "第一个回答"

    @pytest.mark.asyncio
    async def test_update_conversation_state(self, manager):
        """测试更新对话状态"""
        conversation_id = await manager.create_conversation("test_tenant", "test_user")

        # 更新为暂停状态
        success = await manager.update_conversation_state(conversation_id, ConversationState.PAUSED)
        assert success is True

        context = manager.conversations[conversation_id]
        assert context.state == ConversationState.PAUSED

        # 更新为已完成状态
        success = await manager.update_conversation_state(conversation_id, ConversationState.COMPLETED)
        assert success is True

        context = manager.conversations[conversation_id]
        assert context.state == ConversationState.COMPLETED

    @pytest.mark.asyncio
    async def test_update_nonexistent_conversation_state(self, manager):
        """测试更新不存在对话的状态"""
        success = await manager.update_conversation_state("nonexistent_id", ConversationState.ARCHIVED)
        assert success is False

    @pytest.mark.asyncio
    async def test_clear_conversation_archive(self, manager):
        """测试归档清空对话"""
        conversation_id = await manager.create_conversation("test_tenant", "test_user")
        await manager.add_message(conversation_id, "user", "测试消息")

        # 归档对话
        success = await manager.clear_conversation(conversation_id, archive=True)
        assert success is True

        context = manager.conversations[conversation_id]
        assert context.state == ConversationState.ARCHIVED

    @pytest.mark.asyncio
    async def test_clear_conversation_delete(self, manager):
        """测试删除对话"""
        conversation_id = await manager.create_conversation("test_tenant", "test_user")
        await manager.add_message(conversation_id, "user", "测试消息")

        # 删除对话
        success = await manager.clear_conversation(conversation_id, archive=False)
        assert success is True

        assert conversation_id not in manager.conversations

    @pytest.mark.asyncio
    async def test_context_window_compression(self, manager):
        """测试上下文窗口压缩"""
        # 创建对话并设置较低的压缩阈值
        conversation_id = await manager.create_conversation("test_tenant", "test_user")
        context = manager.conversations[conversation_id]
        context.context_compression_threshold = 5  # 5条消息后开始压缩

        # 添加超过阈值的消息数量
        for i in range(10):
            await manager.add_message(
                conversation_id,
                "user" if i % 2 == 0 else "assistant",
                f"消息 {i+1}"
            )

        # 检查上下文窗口是否被压缩
        assert len(context.context_window) <= context.max_context_messages

    @pytest.mark.asyncio
    async def test_get_conversation_statistics(self, manager):
        """测试获取对话统计"""
        # 创建多个对话
        conv1 = await manager.create_conversation("tenant1", "user1")
        conv2 = await manager.create_conversation("tenant1", "user2")
        conv3 = await manager.create_conversation("tenant2", "user1")

        # 添加消息
        await manager.add_message(conv1, "user", "消息1")
        await manager.add_message(conv1, "assistant", "回复1")
        await manager.add_message(conv2, "user", "消息2")

        # 获取所有租户统计
        stats = await manager.get_conversation_statistics()
        assert stats["total_conversations"] == 3
        assert stats["active_conversations"] == 3
        assert stats["total_messages"] == 3

        # 获取特定租户统计
        tenant1_stats = await manager.get_conversation_statistics("tenant1")
        assert tenant1_stats["total_conversations"] == 2
        assert tenant1_stats["total_messages"] == 2

    def test_get_memory_usage(self, manager):
        """测试获取内存使用情况"""
        # 初始状态
        memory = manager.get_memory_usage()
        assert memory["active_conversations"] == 0
        assert memory["total_messages"] == 0

        # 创建对话会影响内存使用
        # 这个测试主要验证方法调用不出错
        assert isinstance(memory, dict)
        assert "active_conversations" in memory
        assert "total_messages" in memory

    @pytest.mark.asyncio
    async def test_cleanup_old_conversations(self, manager):
        """测试清理旧对话"""
        # 创建一个对话
        conversation_id = await manager.create_conversation("test_tenant", "test_user")

        # 手动设置一个旧的时间戳
        context = manager.conversations[conversation_id]
        old_time = datetime.utcnow() - timedelta(days=35)
        context.updated_at = old_time

        # 执行清理
        await manager.cleanup_old_conversations(days=30)

        # 对话应该被归档而不是删除
        context = manager.conversations[conversation_id]
        assert context.state == ConversationState.ARCHIVED


class TestConversationContext:
    """对话上下文测试"""

    def test_conversation_context_creation(self):
        """测试对话上下文创建"""
        now = datetime.utcnow()
        context = ConversationContext(
            conversation_id="test_conv",
            tenant_id="test_tenant",
            user_id="test_user"
        )

        assert context.conversation_id == "test_conv"
        assert context.tenant_id == "test_tenant"
        assert context.user_id == "test_user"
        assert context.state == ConversationState.ACTIVE
        assert context.messages == []
        assert context.context_window == []
        assert context.summary is None
        assert isinstance(context.created_at, datetime)
        assert isinstance(context.updated_at, datetime)

    def test_conversation_context_with_metadata(self):
        """测试带元数据的对话上下文"""
        metadata = {"source": "web", "priority": "high"}
        context = ConversationContext(
            conversation_id="test_conv",
            tenant_id="test_tenant",
            user_id="test_user",
            metadata=metadata
        )

        assert context.metadata == metadata


class TestMessageTemplate:
    """消息模板测试"""

    def test_message_template_creation(self):
        """测试消息模板创建"""
        now = datetime.utcnow()
        template = MessageTemplate(
            role="user",
            content="测试消息",
            token_count=10
        )

        assert template.role == "user"
        assert template.content == "测试消息"
        assert template.token_count == 10
        assert isinstance(template.timestamp, datetime)
        assert template.metadata == {}

    def test_message_template_with_metadata(self):
        """测试带元数据的消息模板"""
        metadata = {"model": "glm-4", "temperature": 0.7}
        template = MessageTemplate(
            role="assistant",
            content="AI回复",
            metadata=metadata
        )

        assert template.metadata == metadata


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_conversation_lifecycle(self):
        """测试完整对话生命周期"""
        manager = ConversationManager()

        # 1. 创建对话
        conv_id = await manager.create_conversation(
            tenant_id="integration_tenant",
            user_id="integration_user",
            metadata={"test": True}
        )
        assert conv_id is not None

        # 2. 添加多轮对话
        user_questions = [
            "什么是机器学习？",
            "机器学习有哪些类型？",
            "如何开始学习机器学习？"
        ]

        for i, question in enumerate(user_questions):
            # 用户问题
            await manager.add_message(conv_id, "user", question, 20)

            # 模拟AI回复
            answer = f"这是关于{question}的回答..."
            await manager.add_message(conv_id, "assistant", answer, 100, {"step": i+1})

        # 3. 检查对话状态
        context = await manager.get_conversation_context(conv_id)
        assert context["message_count"] == 6  # 3个问题 + 3个回答
        assert context["state"] == ConversationState.ACTIVE.value

        # 4. 获取历史
        history = await manager.get_conversation_history(conv_id)
        assert len(history) == 6
        assert history[0]["role"] == "user"
        assert history[-1]["role"] == "assistant"

        # 5. 完成对话
        await manager.update_conversation_state(conv_id, ConversationState.COMPLETED)

        final_context = await manager.get_conversation_context(conv_id)
        assert final_context["state"] == ConversationState.COMPLETED.value

        # 6. 清理对话
        await manager.clear_conversation(conv_id, archive=False)
        assert conv_id not in manager.conversations

    @pytest.mark.asyncio
    async def test_concurrent_conversation_management(self):
        """测试并发对话管理"""
        manager = ConversationManager()

        # 创建多个对话
        conversations = []
        for i in range(5):
            conv_id = await manager.create_conversation(
                tenant_id=f"tenant_{i}",
                user_id=f"user_{i}"
            )
            conversations.append(conv_id)

        # 并发添加消息
        async def add_messages(conv_id, user_id):
            await manager.add_message(conv_id, "user", f"来自{user_id}的问题")
            await manager.add_message(conv_id, "assistant", f"给{user_id}的回答")

        # 并发执行
        tasks = []
        for i, conv_id in enumerate(conversations):
            tasks.append(add_messages(conv_id, f"user_{i}"))

        await asyncio.gather(*tasks)

        # 验证结果
        for conv_id in conversations:
            context = await manager.get_conversation_context(conv_id)
            assert context["message_count"] == 2

        # 验证统计
        stats = await manager.get_conversation_statistics()
        assert stats["total_conversations"] == 5
        assert stats["total_messages"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])