# -*- coding: utf-8 -*-
"""
Query Stream V2 Endpoint - 流式查询端点
======================================

流式响应端点，使用 Server-Sent Events (SSE) 协议。

API: POST /api/v2/query/stream

特性:
    - 实时流式输出
    - 处理步骤推送
    - 可取消的长时间查询

作者: BMad Master
版本: 2.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, AsyncGenerator, Callable
import logging
import json
import time
import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime

# 缓存服务导入
from src.app.services.cache_service import (
    get_cache_manager,
    TenantCacheKeyGenerator
)

# 数据库依赖导入
from src.app.data.database import SessionLocal

logger = logging.getLogger(__name__)

# ============================================================================
# 会话状态管理
# ============================================================================

@dataclass
class StreamSessionState:
    """流式会话状态"""
    session_id: str
    tenant_id: str
    user_id: str
    query: str
    status: str = "running"  # running, paused, completed, error
    accumulated_answer: str = ""
    current_progress: int = 0
    processing_steps: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    abort_controller: Optional[asyncio.Event] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "query": self.query,
            "status": self.status,
            "accumulated_answer": self.accumulated_answer,
            "current_progress": self.current_progress,
            "processing_steps": self.processing_steps,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

# 全局会话状态存储 (生产环境应使用 Redis)
_active_sessions: Dict[str, StreamSessionState] = {}


def get_session_state(session_id: str) -> Optional[StreamSessionState]:
    """获取会话状态"""
    return _active_sessions.get(session_id)


def set_session_state(state: StreamSessionState):
    """设置会话状态"""
    _active_sessions[state.session_id] = state


def remove_session_state(session_id: str):
    """移除会话状态"""
    _active_sessions.pop(session_id, None)

# ============================================================================
# 图表配置提取函数
# ============================================================================

def extract_chart_config_from_answer(answer: str) -> Optional[str]:
    """从 AI 回答中提取图表配置 JSON

    Args:
        answer: AI 的文本回答

    Returns:
        JSON 字符串格式的图表配置，如果没有则返回 None
    """
    if not answer or not answer.strip():
        return None

    # 策略0 (最高优先级): 尝试匹配 [CHART_START]...[CHART_END] 格式
    # 这是 V1 API 和 AI 生成图表时使用的标准格式
    chart_marker_pattern = r'\[CHART_START\]([\s\S]*?)\[CHART_END\]'
    marker_match = re.search(chart_marker_pattern, answer)
    if marker_match:
        json_str = marker_match.group(1).strip()
        try:
            parsed = json.loads(json_str)
            # ECharts 配置通常包含 series, xAxis, yAxis, title 等字段
            if any(key in parsed for key in ['series', 'xAxis', 'yAxis', 'title', 'legend', 'grid', 'tooltip']):
                logger.info(f"[图表提取] 成功从 [CHART_START]...[CHART_END] 格式提取 ECharts 配置")
                return json.dumps(parsed, ensure_ascii=False)
            # 简化格式图表配置
            elif any(key in parsed for key in ['chart_type', 'data', 'x_axis', 'y_axis']):
                logger.info(f"[图表提取] 成功从 [CHART_START]...[CHART_END] 格式提取简化图表配置")
                return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError as e:
            logger.warning(f"[图表提取] [CHART_START] JSON 解析失败: {e}")

    # 策略1: 尝试匹配 ```json ... ``` 代码块
    json_pattern = r'```(?:json|JSON)\s*([\s\S]*?)\s*```'
    match = re.search(json_pattern, answer)

    if match:
        json_str = match.group(1).strip()
        # 处理双大括号问题（Python f-string 模板格式）
        json_str = json_str.replace('{{', '{').replace('}}', '}')
        # 验证是否为有效 JSON
        try:
            parsed = json.loads(json_str)
            # 验证是否是图表配置
            if any(key in parsed for key in ['chart_type', 'series', 'data', 'title', 'x_axis', 'y_axis']):
                return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            pass

    # 策略2: 尝试匹配任意代码块中的 JSON
    code_block_pattern = r'```\s*([\s\S]*?)\s*```'
    for match in re.finditer(code_block_pattern, answer):
        json_str = match.group(1).strip()
        # 检查是否像 JSON（以 { 或 [ 开头）
        if json_str.startswith('{') or json_str.startswith('['):
            # 处理双大括号
            json_str = json_str.replace('{{', '{').replace('}}', '}')
            try:
                parsed = json.loads(json_str)
                if any(key in parsed for key in ['chart_type', 'series', 'data', 'title']):
                    return json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError:
                pass

    return None


# ============================================================================
# 性能监控辅助函数
# ============================================================================

def log_performance(
    step: str,
    tenant_id: str,
    user_id: str,
    duration_ms: float,
    metadata: Optional[Dict[str, Any]] = None
):
    """记录性能指标"""
    logger.info(
        "Performance metric",
        extra={
            "metric_type": "query_performance",
            "step": step,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "duration_ms": round(duration_ms, 2),
            "metadata": metadata or {}
        }
    )

# ============================================================================
# 路由器
# ============================================================================

router = APIRouter(prefix="/query", tags=["query-v2-stream"])

# ============================================================================
# 请求模型
# ============================================================================

class StreamQueryRequestV2(BaseModel):
    """流式查询请求模型"""
    query: str = Field(..., description="自然语言查询", min_length=1)
    connection_id: Optional[str] = Field(None, description="数据源连接 ID")
    session_id: Optional[str] = Field(None, description="会话 ID")
    max_results: int = Field(100, ge=1, le=1000, description="最大结果数")
    include_chart: bool = Field(False, description="是否生成图表")

# ============================================================================
# 端点
# ============================================================================

@router.post("/stream")
async def create_stream_query_v2(
    request: StreamQueryRequestV2,
    tenant_id: str = "default_tenant",
    user_id: str = "default_user"
):
    """
    流式查询端点 (Server-Sent Events)

    返回 SSE 格式的流式响应。

    ## 事件类型
    - `step`: 处理步骤更新
    - `progress`: 进度更新 (0-100)
    - `data`: 部分数据
    - `error`: 错误信息
    - `done`: 完成信号

    ## 使用示例
    ```javascript
    const eventSource = new EventSource('/api/v2/query/stream?query=xxx');

    eventSource.addEventListener('step', (e) => {
        console.log('Step:', e.data);
    });

    eventSource.addEventListener('done', (e) => {
        console.log('Final result:', e.data);
        eventSource.close();
    });
    ```
    """
    # 记录请求开始时间
    request_start_time = time.time()

    async def event_generator() -> AsyncGenerator[str, None]:
        """SSE 事件生成器"""

        def send_event(event_type: str, data: Dict[str, Any]):
            """发送 SSE 事件（同步生成器）"""
            event_data = json.dumps(data, ensure_ascii=False)
            yield f"event: {event_type}\n"
            yield f"data: {event_data}\n\n"

        try:
            # 步骤时间记录
            step_timings: Dict[str, float] = {}
            overall_start = time.time()  # 初始化总开始时间

            # 初始化会话状态
            session_id = request.session_id or f"stream_{int(time.time() * 1000)}"
            abort_event = asyncio.Event()
            session_state = StreamSessionState(
                session_id=session_id,
                tenant_id=tenant_id,
                user_id=user_id,
                query=request.query,
                status="running",
                abort_controller=abort_event
            )
            set_session_state(session_state)

            # 发送开始事件（包含 session_id）
            for event in send_event("start", {
                "query": request.query,
                "tenant_id": tenant_id,
                "session_id": session_id,
                "timestamp": time.time()
            }):
                yield event

            # 步骤 1: 接收查询（保留，作为唯一的初始化步骤）
            step_start = time.time()
            step_timings["receive_query"] = (time.time() - step_start) * 1000

            for event in send_event("step", {
                "step": 1,
                "message": "理解问题",
                "detail": f"正在分析: {request.query[:50]}...",
                "status": "running"
            }):
                yield event

            for event in send_event("progress", {"value": 10}):
                yield event

            # 🔧 删除了步骤 2（租户隔离验证）和步骤 3（AgentV2 处理）
            # 这些是内部步骤，对用户无价值

            # 缓存检查（内部处理，不发送步骤）
            step_start = time.time()
            cache_manager = get_cache_manager()
            cache_hit = False
            cached_data = None

            if cache_manager is not None:
                cache_key = TenantCacheKeyGenerator.generate_v2_query_key(
                    tenant_id, user_id, request.query, request.session_id
                )
                cached_data = await cache_manager.cache.get(cache_key)
                cache_hit = cached_data is not None

            step_timings["cache_check"] = (time.time() - step_start) * 1000

            if cache_hit and cached_data:
                # 缓存命中 - 流式返回缓存结果
                step_timings["agent_execution"] = 0

                # 从缓存数据中提取答案
                cached_answer = cached_data.get("answer", "")
                processing_steps = cached_data.get("processing_steps", [])

                for event in send_event("progress", {"value": 80}):
                    yield event

                # 分块发送答案
                step_start = time.time()
                chunk_size = 200
                for i in range(0, len(cached_answer), chunk_size):
                    chunk = cached_answer[i:i+chunk_size]
                    progress = 80 + int((i / len(cached_answer)) * 15)

                    for event in send_event("data", {
                        "chunk": chunk,
                        "progress": progress
                    }):
                        yield event

                step_timings["answer_streaming"] = (time.time() - step_start) * 1000

                # 计算总处理时间
                total_processing_time_ms = (time.time() - overall_start) * 1000

                # 完成事件
                log_performance(
                    step="stream_query_cache_hit",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    duration_ms=total_processing_time_ms,
                    metadata={
                        "query_length": len(request.query),
                        "answer_length": len(cached_answer),
                        "step_timings": step_timings,
                        "cache_hit": True
                    }
                )

                for event in send_event("done", {
                    "success": True,
                    "answer": cached_answer,
                    "processing_steps": processing_steps,
                    "tenant_id": tenant_id,
                    "processing_time_ms": round(total_processing_time_ms, 2),
                    "step_timings": {k: round(v, 2) for k, v in step_timings.items()},
                    "from_cache": True
                }):
                    yield event

                for event in send_event("progress", {"value": 100}):
                    yield event

            else:
                # 缓存未命中 - 执行 AgentV2 查询
                step_start = time.time()
                try:
                    from AgentV2.core import get_default_factory

                    agent_factory = get_default_factory()

                    # 获取数据库会话用于查询数据源配置
                    db_session = SessionLocal()
                    try:
                        agent = agent_factory.get_or_create_agent(
                            tenant_id=tenant_id,
                            user_id=user_id,
                            session_id=request.session_id,
                            connection_id=request.connection_id,
                            db_session=db_session,
                            force_refresh=True  # 🔧 强制刷新以确保使用最新的系统提示词
                        )

                        # 🔧 使用原始用户查询（CHART_GUIDANCE_TEMPLATE 已包含图表生成指令）
                        agent_input = {
                            "messages": [
                                {"role": "user", "content": request.query}
                            ]
                        }

                        # 🔧 删除了 AgentV2 处理步骤的发送，直接进入实际工具调用
                        for event in send_event("progress", {"value": 20}):
                            yield event

                        # 🔧🔧🔧 使用 astream_events 实现真正的 token 级别流式输出
                        # 参考: LangGraph 文档 - Streaming Events
                        # astream_events 可以捕获 LLM 生成过程中的每个 token
                        all_messages = []
                        accumulated_answer = ""
                        step_count = 0
                        processing_step_number = 1  # 🔧 从步骤1开始计数（删除了步骤2、3）
                        last_progress_update = time.time()
                        current_tool_call = None  # 跟踪当前工具调用

                        async for event in agent.astream_events(
                            agent_input,
                            config={"configurable": {"thread_id": request.session_id}},
                            version="v2"
                        ):
                            event_kind = event.get("event", "")
                            event_data = event.get("data", {})

                            # 🔧 处理 LLM 流式输出 (token 级别)
                            if event_kind == "on_chat_model_stream":
                                chunk = event_data.get("chunk")
                                if chunk and hasattr(chunk, "content") and chunk.content:
                                    # 累积答案
                                    accumulated_answer += chunk.content
                                    
                                    # 计算进度 (30% -> 80%)
                                    step_count += 1
                                    progress = 30 + min(int((step_count / 100) * 50), 50)
                                    
                                    # 实时发送每个 token
                                    for sse in send_event("data", {
                                        "chunk": chunk.content,
                                        "progress": progress
                                    }):
                                        yield sse
                                    
                                    # 定期发送进度更新（每 0.5 秒）
                                    now = time.time()
                                    if now - last_progress_update > 0.5:
                                        for sse in send_event("progress", {"value": progress}):
                                            yield sse
                                        last_progress_update = now

                            # 🔧 处理工具调用开始
                            elif event_kind == "on_tool_start":
                                tool_name = event.get("name", "unknown")
                                tool_input = event_data.get("input", {})
                                
                                processing_step_number += 1
                                step_data = {
                                    "step": processing_step_number,
                                    "message": f"调用工具: {tool_name}",
                                    "status": "running",
                                    "duration": 0
                                }
                                
                                # 根据工具类型添加内容详情
                                if "sql" in tool_name.lower() or "query" in tool_name.lower():
                                    sql_query = tool_input.get("query") or tool_input.get("sql", "")
                                    if sql_query:
                                        step_data["content_type"] = "sql"
                                        step_data["content_data"] = {"sql": sql_query}
                                        step_data["detail"] = f"执行查询: {sql_query[:100]}..."
                                elif "schema" in tool_name.lower():
                                    step_data["message"] = "获取数据库结构"
                                    step_data["detail"] = f"表: {tool_input.get('table_name', 'unknown')}"
                                elif "list" in tool_name.lower() and "table" in tool_name.lower():
                                    step_data["message"] = "列出数据库表"
                                    step_data["detail"] = "正在获取表列表..."
                                elif "chart" in tool_name.lower():
                                    step_data["message"] = "生成图表"
                                    step_data["detail"] = "正在生成可视化图表..."
                                
                                current_tool_call = step_data
                                for sse in send_event("step", step_data):
                                    yield sse

                            # 🔧 处理工具调用结束
                            elif event_kind == "on_tool_end":
                                if current_tool_call:
                                    raw_output = event_data.get("output", "")
                                    
                                    # 🔧 修复：LangGraph 的 on_tool_end 返回的是 ToolMessage 对象
                                    # 需要从 content 属性获取实际的字符串输出
                                    if hasattr(raw_output, 'content'):
                                        tool_output = raw_output.content
                                        logger.info(f"[V2 Stream] on_tool_end: ToolMessage detected, content_len={len(tool_output) if tool_output else 0}")
                                    else:
                                        tool_output = raw_output if isinstance(raw_output, str) else str(raw_output)
                                        logger.info(f"[V2 Stream] on_tool_end: raw output, type={type(raw_output).__name__}")
                                    
                                    current_tool_call["status"] = "completed"
                                    current_tool_call["duration"] = 100  # 估算时间
                                    
                                    # 🔧 增强：根据工具类型提取有用信息到 detail
                                    tool_message = current_tool_call.get("message", "")
                                    if tool_output and isinstance(tool_output, str):
                                        try:
                                            import json as json_module
                                            output_data = json_module.loads(tool_output)
                                            
                                            # 列出数据库表 - 显示表名列表
                                            if "列出数据库表" in tool_message or "list" in tool_message.lower():
                                                if isinstance(output_data, list):
                                                    table_names = [t.get("table_name", t.get("name", str(t))) if isinstance(t, dict) else str(t) for t in output_data[:10]]
                                                    current_tool_call["detail"] = f"找到 {len(output_data)} 张表: {', '.join(table_names)}"
                                                    if len(output_data) > 10:
                                                        current_tool_call["detail"] += "..."
                                            
                                            # 获取数据库结构 - 显示列信息
                                            elif "获取数据库结构" in tool_message or "schema" in tool_message.lower():
                                                if isinstance(output_data, dict):
                                                    columns = output_data.get("columns", [])
                                                    if columns:
                                                        col_names = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in columns[:5]]
                                                        current_tool_call["detail"] = f"包含 {len(columns)} 列: {', '.join(col_names)}"
                                                        if len(columns) > 5:
                                                            current_tool_call["detail"] += "..."
                                        except (json_module.JSONDecodeError, TypeError):
                                            pass
                                    
                                    for sse in send_event("step", current_tool_call):
                                        yield sse
                                    
                                    # 🔧 从工具输出中提取表格数据
                                    if tool_output and isinstance(tool_output, str):
                                        # 尝试解析为 JSON 表格数据
                                        try:
                                            import json as json_module
                                            output_data = json_module.loads(tool_output)
                                            logger.info(f"[V2 Stream] 工具输出解析成功，类型: {type(output_data).__name__}")
                                            
                                            # 检测是否为表格格式（包含 columns 和 data/rows）
                                            if isinstance(output_data, dict):
                                                columns = output_data.get("columns", [])
                                                rows = output_data.get("data", output_data.get("rows", []))
                                                row_count = output_data.get("row_count", len(rows) if isinstance(rows, list) else 0)
                                                logger.info(f"[V2 Stream] 检测表格数据: columns={len(columns)}, rows={len(rows) if rows else 0}, row_count={row_count}")
                                                
                                                if columns and rows:
                                                    # 发送表格数据步骤
                                                    processing_step_number += 1
                                                    table_step = {
                                                        "step": processing_step_number,
                                                        "message": "查询结果",
                                                        "status": "completed",
                                                        "duration": 50,
                                                        "content_type": "table",
                                                        "content_data": {
                                                            "table": {
                                                                "columns": columns,
                                                                "rows": rows[:50],  # 限制前50行
                                                                "row_count": row_count
                                                            }
                                                        }
                                                    }
                                                    for sse in send_event("step", table_step):
                                                        yield sse
                                                    logger.info(f"[V2 Stream] 发送表格数据: {row_count} 行, {len(columns)} 列")
                                            
                                            # 检测是否为列表格式（直接是行数组）
                                            elif isinstance(output_data, list) and len(output_data) > 0:
                                                if isinstance(output_data[0], dict):
                                                    columns = list(output_data[0].keys())
                                                    rows = output_data
                                                    row_count = len(rows)
                                                    
                                                    # 发送表格数据步骤
                                                    processing_step_number += 1
                                                    table_step = {
                                                        "step": processing_step_number,
                                                        "message": "查询结果",
                                                        "status": "completed",
                                                        "duration": 50,
                                                        "content_type": "table",
                                                        "content_data": {
                                                            "table": {
                                                                "columns": columns,
                                                                "rows": rows[:50],
                                                                "row_count": row_count
                                                            }
                                                        }
                                                    }
                                                    for sse in send_event("step", table_step):
                                                        yield sse
                                                    logger.info(f"[V2 Stream] 发送表格数据 (列表): {row_count} 行")
                                        except (json_module.JSONDecodeError, TypeError):
                                            # 不是 JSON 格式，跳过
                                            pass
                                    
                                    current_tool_call = None

                            # 🔧 处理 LLM 调用结束（收集最终消息）
                            elif event_kind == "on_chat_model_end":
                                output = event_data.get("output")
                                if output:
                                    all_messages.append(output)

                        step_timings["agent_execution"] = (time.time() - step_start) * 1000

                        # 从流式消息中提取最终答案
                        answer = accumulated_answer

                        # 🔧 始终尝试提取图表配置（如果存在）
                        # 不再检查 include_chart 标志，因为 AI 可能会根据问题类型自主决定生成图表
                        chart_config = extract_chart_config_from_answer(answer)
                        if chart_config:
                            logger.info(f"[V2 Stream] 成功提取图表配置: {chart_config[:100]}...")

                        # 计算总处理时间
                        total_processing_time_ms = (time.time() - overall_start) * 1000

                        # 完成事件
                        processing_steps = [
                            "接收查询",
                            "租户隔离验证",
                            "AgentV2 处理",
                            "DeepSeek LLM 调用",
                            "返回结果"
                        ]

                        # 记录性能日志
                        log_performance(
                            step="stream_query_complete",
                            tenant_id=tenant_id,
                            user_id=user_id,
                            duration_ms=total_processing_time_ms,
                            metadata={
                                "query_length": len(request.query),
                                "answer_length": len(answer),
                                "step_timings": step_timings,
                                "processing_steps": processing_steps,
                                "connection_id": request.connection_id
                            }
                        )

                        # 存储到缓存（如果缓存管理器可用）
                        if cache_manager is not None and answer:
                            cache_key = TenantCacheKeyGenerator.generate_v2_query_key(
                                tenant_id, user_id, request.query, request.session_id
                            )
                            cache_data = {
                                "answer": answer,
                                "processing_steps": processing_steps,
                                "query": request.query
                            }
                            await cache_manager.cache.set(cache_key, cache_data, ttl=600)
                            logger.debug(f"查询结果已缓存: {cache_key}")

                        for event in send_event("done", {
                            "success": True,
                            "answer": answer,
                            "chart_config": chart_config,  # 🔧 添加图表配置
                            "processing_steps": processing_steps,
                            "tenant_id": tenant_id,
                            "processing_time_ms": round(total_processing_time_ms, 2),
                            "step_timings": {k: round(v, 2) for k, v in step_timings.items()},
                            "connection_id": request.connection_id
                        }):
                            yield event

                        for event in send_event("progress", {"value": 100}):
                            yield event
                    finally:
                        db_session.close()

                except ImportError:
                    # AgentV2 不可用
                    total_processing_time_ms = (time.time() - overall_start) * 1000

                    log_performance(
                        step="stream_query_import_error",
                        tenant_id=tenant_id,
                        user_id=user_id,
                        duration_ms=total_processing_time_ms,
                        metadata={"error": "AgentV2 not available"}
                    )

                    for event in send_event("error", {
                        "error": "AgentV2 not available",
                        "detail": "流式查询功能需要 AgentV2 模块"
                    }):
                        yield event

        except Exception as e:
            total_processing_time_ms = (time.time() - overall_start) * 1000

            log_performance(
                step="stream_query_error",
                tenant_id=tenant_id,
                user_id=user_id,
                duration_ms=total_processing_time_ms,
                metadata={"error": str(e), "error_type": type(e).__name__}
            )

            logger.error(f"Stream query error: {e}")
            for event in send_event("error", {
                "error": str(e),
                "error_type": "internal_error"
            }):
                yield event

        finally:
            # 清理会话状态
            if 'session_state' in locals():
                if session_state.status == "running":
                    session_state.status = "completed"
                session_state.updated_at = time.time()
                # 保留会话状态一段时间以便客户端查询状态
                # 可以在之后的任务中添加定时清理机制

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )


@router.get("/stream/health")
async def stream_health_check():
    """流式端点健康检查"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "streaming": "enabled",
        "protocol": "Server-Sent Events (SSE)"
    }


# ============================================================================
# 会话管理端点
# ============================================================================

@router.get("/stream/session/{session_id}")
async def get_session_status(session_id: str):
    """
    获取流式会话状态

    Args:
        session_id: 会话ID

    Returns:
        会话状态信息
    """
    session_state = get_session_state(session_id)

    if session_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在或已过期"
        )

    return session_state.to_dict()


@router.post("/stream/session/{session_id}/pause")
async def pause_stream_session(session_id: str):
    """
    暂停流式查询

    Args:
        session_id: 会话ID

    Returns:
        操作结果
    """
    session_state = get_session_state(session_id)

    if session_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在或已过期"
        )

    if session_state.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只能暂停正在运行的会话，当前状态: {session_state.status}"
        )

    # 更新状态为暂停
    session_state.status = "paused"
    session_state.updated_at = time.time()
    set_session_state(session_state)

    # 设置中止事件以停止流式输出
    if session_state.abort_controller:
        session_state.abort_controller.set()

    logger.info(f"会话 {session_id} 已暂停")

    return {
        "success": True,
        "session_id": session_id,
        "status": "paused",
        "accumulated_answer": session_state.accumulated_answer,
        "current_progress": session_state.current_progress
    }


@router.post("/stream/session/{session_id}/resume")
async def resume_stream_session(
    session_id: str,
    tenant_id: str = "default_tenant",
    user_id: str = "default_user"
):
    """
    恢复暂停的流式查询

    注意: 由于流式查询的特性，完整恢复需要重新发起查询。
    此端点返回已累积的内容，客户端可决定是否重新查询。

    Args:
        session_id: 会话ID
        tenant_id: 租户ID
        user_id: 用户ID

    Returns:
        已累积的内容和建议操作
    """
    session_state = get_session_state(session_id)

    if session_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在或已过期"
        )

    if session_state.status != "paused":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只能恢复已暂停的会话，当前状态: {session_state.status}"
        )

    # 更新状态
    session_state.status = "running"
    session_state.updated_at = time.time()
    set_session_state(session_state)

    logger.info(f"会话 {session_id} 已恢复")

    return {
        "success": True,
        "session_id": session_id,
        "status": "running",
        "message": "由于流式查询的特性，完整恢复需要重新发起查询",
        "accumulated_answer": session_state.accumulated_answer,
        "current_progress": session_state.current_progress,
        "recommendation": "使用相同参数重新发起 /stream 查询以获得完整结果"
    }


@router.delete("/stream/session/{session_id}")
async def cancel_stream_session(session_id: str):
    """
    取消流式查询

    Args:
        session_id: 会话ID

    Returns:
        操作结果
    """
    session_state = get_session_state(session_id)

    if session_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话 {session_id} 不存在或已过期"
        )

    # 更新状态为已取消
    session_state.status = "cancelled"
    session_state.updated_at = time.time()

    # 设置中止事件
    if session_state.abort_controller:
        session_state.abort_controller.set()

    # 从活动会话中移除
    remove_session_state(session_id)

    logger.info(f"会话 {session_id} 已取消")

    return {
        "success": True,
        "session_id": session_id,
        "status": "cancelled",
        "accumulated_answer": session_state.accumulated_answer
    }
