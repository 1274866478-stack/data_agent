"""
LangGraph SQL Agent with MCP Integration
Uses DeepSeek as LLM and PostgreSQL MCP Server for database operations
"""
import asyncio
import json
import re
from typing import Annotated, Literal, Optional, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient

from config import config
from models import VisualizationResponse, QueryResult, ChartConfig, ChartType
from terminal_viz import render_response
from data_transformer import sql_result_to_echarts_data, sql_result_to_mcp_echarts_data
from chart_service import ChartRequest, generate_chart_simple, ChartResponse

import base64
import os
from datetime import datetime


# System prompt for the SQL Agent
SYSTEM_PROMPT = """你是一个专业的 PostgreSQL 数据库助手，具备数据查询和图表可视化能力。

## 可用的 MCP 工具：

### 数据库工具（postgres 服务器）：
1. list_tables - 查看数据库中有哪些表（必须先调用！）
2. get_schema - 获取表的结构信息（列名、类型）
3. query - 执行 SQL 查询

### 图表工具（echarts 服务器）：
当用户要求画图/可视化时，先查询数据，然后调用以下工具生成图表：

| 工具名 | 用途 | 数据格式 |
|--------|------|----------|
| generate_bar_chart | 柱状图（比较类别） | [{"category": "名称", "value": 数值}] |
| generate_line_chart | 折线图（趋势变化） | [{"time": "时间", "value": 数值}] |
| generate_pie_chart | 饼图（占比分布） | [{"category": "名称", "value": 数值}] |
| generate_scatter_chart | 散点图（相关性） | 见工具说明 |
| generate_radar_chart | 雷达图（多维对比） | 见工具说明 |
| generate_funnel_chart | 漏斗图（转化分析） | 见工具说明 |

## 🔴 图表工具调用格式（重要！）：

### 柱状图示例：
```json
{
  "title": "各部门人数统计",
  "data": [
    {"category": "技术部", "value": 45},
    {"category": "销售部", "value": 30},
    {"category": "市场部", "value": 25}
  ]
}
```

### 折线图示例：
```json
{
  "title": "月度销售趋势",
  "data": [
    {"time": "2024-01", "value": 1000},
    {"time": "2024-02", "value": 1200},
    {"time": "2024-03", "value": 1500}
  ]
}
```

### 饼图示例：
```json
{
  "title": "市场份额分布",
  "data": [
    {"category": "产品A", "value": 40},
    {"category": "产品B", "value": 35},
    {"category": "产品C", "value": 25}
  ]
}
```

## 工作流程：
1. 使用 list_tables 查看数据库表
2. 使用 get_schema 获取表结构
3. 使用 query 执行 SQL 查询获取数据
4. **如果用户要求可视化**：将查询结果转换为上述格式，调用对应图表工具

## 注意事项：
- 这是 PostgreSQL 数据库，使用 PostgreSQL 语法
- 只生成 SELECT 查询，不执行任何修改操作
- 调用图表工具时，必须将 SQL 结果转换为正确的 data 格式
- 用中文回复用户
"""


def create_llm():
    """Create DeepSeek LLM instance using OpenAI-compatible API"""
    return ChatOpenAI(
        model=config.deepseek_model,
        api_key=config.deepseek_api_key,
        base_url=config.deepseek_base_url,
        temperature=0,
    )


def parse_chart_config(content: str) -> Optional[Dict[str, Any]]:
    """从LLM回复中解析JSON图表配置

    Args:
        content: LLM的文本回复

    Returns:
        解析出的JSON配置，如果没有则返回None
    """
    # 尝试匹配 ```json ... ``` 代码块
    json_pattern = r'```json\s*([\s\S]*?)\s*```'
    match = re.search(json_pattern, content)

    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return None


def extract_tool_data(messages: list) -> tuple[Optional[str], list]:
    """从消息历史中提取工具调用的SQL和返回数据

    Args:
        messages: 消息历史列表

    Returns:
        (sql语句, 原始数据列表)
    """
    sql = None
    raw_data = []

    for msg in messages:
        # 提取SQL（从AIMessage的tool_calls中）
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc.get('name') == 'query':
                    sql = tc.get('args', {}).get('sql')

        # 提取数据（从ToolMessage中）
        if isinstance(msg, ToolMessage):
            try:
                data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                if isinstance(data, list):
                    raw_data = data
            except (json.JSONDecodeError, TypeError):
                pass

    return sql, raw_data


def extract_chart_tool_call(messages: list) -> Optional[Dict[str, Any]]:
    """从消息历史中提取图表工具调用信息

    Args:
        messages: 消息历史列表

    Returns:
        包含工具名和参数的字典，如果没有图表工具调用则返回 None
    """
    chart_tools = [
        "generate_bar_chart", "generate_line_chart", "generate_pie_chart",
        "generate_scatter_chart", "generate_radar_chart", "generate_funnel_chart",
        "generate_echarts"
    ]

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_name = tc.get('name', '')
                if tool_name in chart_tools:
                    return {
                        "tool_name": tool_name,
                        "args": tc.get('args', {})
                    }
    return None


async def call_mcp_chart_tool(tool_name: str, args: Dict[str, Any], output_dir: str = "./charts") -> Optional[str]:
    """使用原始 MCP 客户端调用图表工具（绕过 LangChain 适配器的限制）

    Args:
        tool_name: 工具名称
        args: 工具参数
        output_dir: 输出目录

    Returns:
        保存的图片路径，失败返回 None
    """
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    url = "http://localhost:3033/sse"

    try:
        async with sse_client(url) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()

                result = await session.call_tool(tool_name, args)

                if hasattr(result, 'content') and result.content:
                    for item in result.content:
                        if hasattr(item, 'type') and item.type == 'image':
                            if hasattr(item, 'data') and item.data:
                                # 保存 Base64 图片
                                return _save_base64_image(item.data, output_dir, "png")
                        elif hasattr(item, 'text') and item.text:
                            # 可能是 URL 或其他文本
                            text = item.text
                            if text.startswith("http"):
                                return text

                return None

    except Exception as e:
        print(f"[MCP] Chart tool call failed: {e}")
        return None


def _save_base64_image(base64_data: str, output_dir: str, ext: str = "png") -> str:
    """保存 Base64 编码的图片到文件

    Args:
        base64_data: Base64 编码的图片数据
        output_dir: 输出目录
        ext: 文件扩展名

    Returns:
        保存的文件路径
    """
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mcp_chart_{timestamp}.{ext}"
    filepath = os.path.join(output_dir, filename)

    # 解码并保存
    image_data = base64.b64decode(base64_data)
    with open(filepath, "wb") as f:
        f.write(image_data)

    print(f"📊 图表已保存: {filepath}")
    return filepath


async def build_visualization_response(
    messages: list,
    final_content: str,
    auto_generate_chart: bool = True
) -> VisualizationResponse:
    """构建完整的可视化响应，并可选生成图表

    Args:
        messages: 完整的消息历史
        final_content: 最终的AI回复内容
        auto_generate_chart: 是否自动生成图表文件

    Returns:
        VisualizationResponse对象
    """
    # 提取SQL和原始数据
    sql, raw_data = extract_tool_data(messages)

    # 🆕 检查是否有 mcp-echarts 图表工具调用
    chart_tool_call = extract_chart_tool_call(messages)
    mcp_chart_path = None

    # 如果 LLM 调用了图表工具，使用原始 MCP 客户端重新获取图片
    if chart_tool_call and ENABLE_ECHARTS_MCP:
        print(f"[MCP] Detected chart tool call: {chart_tool_call['tool_name']}")
        mcp_chart_path = await call_mcp_chart_tool(
            chart_tool_call['tool_name'],
            chart_tool_call['args']
        )

    # 解析图表配置
    chart_config_data = parse_chart_config(final_content)

    # 构建QueryResult
    query_result = QueryResult.from_raw_data(raw_data) if raw_data else QueryResult()

    # 构建ChartConfig
    chart_path = mcp_chart_path  # 优先使用 mcp-echarts 的图表

    if chart_config_data:
        chart_type_str = chart_config_data.get('chart_type', 'table')
        try:
            chart_type = ChartType(chart_type_str)
        except ValueError:
            chart_type = ChartType.TABLE

        chart_config = ChartConfig(
            chart_type=chart_type,
            title=chart_config_data.get('chart_title', ''),
            x_field=chart_config_data.get('x_field'),
            y_field=chart_config_data.get('y_field')
        )
        answer = chart_config_data.get('answer', final_content)

        # 如果没有 mcp-echarts 图表，尝试使用本地生成（回退方案）
        if not chart_path and auto_generate_chart:
            should_generate = chart_config_data.get('generate_chart', False)
            if should_generate and raw_data:
                chart_path = _generate_chart_file(
                    raw_data=raw_data,
                    chart_type=chart_type_str,
                    title=chart_config.title,
                    x_field=chart_config.x_field,
                    y_field=chart_config.y_field
                )
    else:
        chart_config = ChartConfig()
        answer = final_content

    response = VisualizationResponse(
        answer=answer,
        sql=sql or '',
        data=query_result,
        chart=chart_config,
        success=True
    )

    # 将图表路径添加到响应中（如果生成了）
    if chart_path:
        if chart_path.startswith("http"):
            response.answer = f"{answer}\n\n📊 图表链接: {chart_path}"
        else:
            response.answer = f"{answer}\n\n📊 图表已保存: {chart_path}"

    return response


def _generate_chart_file(
    raw_data: list,
    chart_type: str,
    title: str,
    x_field: Optional[str],
    y_field: Optional[str]
) -> Optional[str]:
    """生成图表文件

    Args:
        raw_data: SQL查询的原始数据
        chart_type: 图表类型
        title: 图表标题
        x_field: X轴字段
        y_field: Y轴字段

    Returns:
        生成的图表文件路径，失败返回None
    """
    # 跳过不需要图表的类型
    if chart_type in ('table', 'none'):
        return None

    try:
        # 转换数据格式
        echarts_data, actual_x, actual_y = sql_result_to_echarts_data(
            raw_data, x_field, y_field
        )

        if not echarts_data:
            return None

        # 创建图表请求
        request = ChartRequest(
            type=chart_type,
            data=echarts_data,
            title=title or "查询结果",
            series_name=actual_y or "数值",
            x_axis_name=actual_x,
            y_axis_name=actual_y
        )

        # 生成图表（使用简化版，生成HTML）
        response: ChartResponse = generate_chart_simple(request, output_dir="./charts")

        if response.success:
            return response.image_path
        else:
            print(f"⚠️ 图表生成失败: {response.error}")
            return None

    except Exception as e:
        print(f"⚠️ 图表生成异常: {e}")
        return None


# MCP client 配置
# 是否启用 mcp-echarts（需要先运行: mcp-echarts -t sse -p 3033）
ENABLE_ECHARTS_MCP = True  # 已启用 mcp-echarts

# ============================================================
# 🚀 性能优化：持久化单例模式
# ============================================================
# 全局缓存，避免每次查询都重新初始化
_cached_agent = None
_cached_mcp_client = None
_cached_tools = None
_cached_checkpointer = None


def _get_mcp_config():
    """获取 MCP 服务器配置"""
    mcp_config = {
        "postgres": {
            "transport": "stdio",
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-postgres",
                config.database_url
            ],
        }
    }

    if ENABLE_ECHARTS_MCP:
        mcp_config["echarts"] = {
            "transport": "sse",
            "url": "http://localhost:3033/sse",
            "timeout": 30.0,
            "sse_read_timeout": 120.0,
        }

    return mcp_config


async def _get_or_create_agent():
    """获取或创建持久化的 Agent 实例（单例模式）

    Returns:
        tuple: (agent, mcp_client) - 编译好的agent和MCP客户端
    """
    global _cached_agent, _cached_mcp_client, _cached_tools, _cached_checkpointer

    # 如果已缓存，直接返回
    if _cached_agent is not None and _cached_mcp_client is not None:
        return _cached_agent, _cached_mcp_client

    print("🔄 首次初始化 Agent（后续查询将复用连接）...")

    # 创建 MCP 客户端
    mcp_config = _get_mcp_config()
    _cached_mcp_client = MultiServerMCPClient(mcp_config)

    # 获取工具
    _cached_tools = await _cached_mcp_client.get_tools()

    # 创建 LLM
    llm = create_llm()
    llm_with_tools = llm.bind_tools(_cached_tools)

    # 定义节点
    async def call_model(state: MessagesState):
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    def should_continue(state: MessagesState) -> Literal["tools", END]:
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(_cached_tools)

    # 构建图
    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue)
    builder.add_edge("tools", "agent")

    # 持久化 checkpointer
    _cached_checkpointer = MemorySaver()
    _cached_agent = builder.compile(checkpointer=_cached_checkpointer)

    print("✅ Agent 初始化完成！")

    return _cached_agent, _cached_mcp_client


async def reset_agent():
    """重置 Agent 缓存（用于重新连接或配置变更）"""
    global _cached_agent, _cached_mcp_client, _cached_tools, _cached_checkpointer
    _cached_agent = None
    _cached_mcp_client = None
    _cached_tools = None
    _cached_checkpointer = None
    print("🔄 Agent 缓存已重置")


async def run_agent(question: str, thread_id: str = "1", verbose: bool = True) -> VisualizationResponse:
    """Run the SQL Agent with a question

    Args:
        question: 用户问题
        thread_id: 会话ID
        verbose: 是否打印详细过程

    Returns:
        VisualizationResponse: 结构化的可视化响应
    """
    # 🚀 使用持久化的 Agent（首次调用会初始化，后续复用）
    agent, mcp_client = await _get_or_create_agent()

    # Run the agent
    config_dict = {"configurable": {"thread_id": thread_id}}

    if verbose:
        print(f"\n{'='*60}")
        print(f"问题: {question}")
        print(f"{'='*60}\n")

    step_count = 0
    all_messages = []  # 收集所有消息
    final_content = ""

    # 使用 stream_mode="updates" 只获取增量更新
    async for step in agent.astream(
        {"messages": [HumanMessage(content=question)]},
        config_dict,
        stream_mode="updates",
    ):
        step_count += 1

        if verbose:
            print(f"\n{'─'*60}")
            print(f"� 第 {step_count} 步")
            print(f"{'─'*60}")

        for node_name, node_output in step.items():
            if verbose:
                print(f"\n🔹 节点名称: {node_name}")

            if "messages" in node_output:
                messages = node_output["messages"]
                all_messages.extend(messages)  # 收集消息

                for msg in messages:
                    if verbose:
                        print(f"  📨 消息类型: {type(msg).__name__}")

                    # 根据消息类型处理
                    if isinstance(msg, AIMessage):
                        if msg.content:
                            final_content = msg.content  # 保存最后的AI回复
                            if verbose:
                                preview = msg.content[:200] + ('...' if len(msg.content) > 200 else '')
                                print(f"     🤖 AI: {preview}")
                        if msg.tool_calls and verbose:
                            for tc in msg.tool_calls:
                                print(f"     🔧 调用工具: {tc['name']}")

                    elif isinstance(msg, ToolMessage) and verbose:
                        preview = str(msg.content)[:200] + ('...' if len(str(msg.content)) > 200 else '')
                        print(f"     📦 工具返回: {preview}")

    # 构建可视化响应（异步，支持 mcp-echarts 图表生成）
    viz_response = await build_visualization_response(all_messages, final_content)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"✅ 完成! 共 {step_count} 步")
        print(f"{'='*60}")
        
        # 打印结构化数据摘要
        print(f"\n📊 结构化数据摘要:")
        print(f"   - SQL: {viz_response.sql[:50]}..." if viz_response.sql else "   - SQL: 无")
        print(f"   - 数据行数: {viz_response.data.row_count}")
        print(f"   - 推荐图表: {viz_response.chart.chart_type.value}")
        print(f"   - 图表标题: {viz_response.chart.title or '无'}")
    
    return viz_response


async def interactive_mode():
    """Run the agent in interactive mode"""
    print("\n" + "="*60)
    print("🤖 SQL Agent 交互模式（可视化版）")
    print("="*60)
    print("命令:")
    print("  exit/quit - 退出程序")
    print("  debug     - 切换调试模式")
    print("  reset     - 重置连接（如遇连接问题）")
    print("="*60)
    print("\n💡 提示: 首次查询需要初始化连接（约5-10秒），后续查询将很快！\n")

    thread_id = "interactive_session"
    verbose = False  # 默认关闭详细输出，只显示漂亮的可视化结果

    while True:
        try:
            question = input("\n📝 请输入你的问题: ").strip()

            if question.lower() in ["exit", "quit", "q"]:
                print("\n👋 再见!")
                break

            if question.lower() == "debug":
                verbose = not verbose
                print(f"\n🔧 调试模式: {'开启' if verbose else '关闭'}")
                continue

            if question.lower() == "reset":
                await reset_agent()
                continue

            if not question:
                continue

            # 计时
            import time
            start_time = time.time()

            # 运行Agent并获取结构化响应
            viz_response = await run_agent(question, thread_id, verbose=verbose)

            # 计算耗时
            elapsed = time.time() - start_time

            # 使用漂亮的可视化渲染
            if not verbose:  # 非调试模式下显示漂亮输出
                render_response(viz_response)

            print(f"\n⏱️  响应时间: {elapsed:.2f} 秒")

        except KeyboardInterrupt:
            print("\n\n👋 再见!")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            print("💡 提示: 输入 'reset' 可重置连接")


if __name__ == "__main__":
    # Validate configuration
    config.validate_config()

    # Run interactive mode
    asyncio.run(interactive_mode())

