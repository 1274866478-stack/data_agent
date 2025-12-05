"""
LangGraph SQL Agent with MCP Integration
Uses DeepSeek as LLM and PostgreSQL MCP Server for database operations
"""
import asyncio
from typing import Annotated, Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient

from config import config


# System prompt for the SQL Agent
SYSTEM_PROMPT = """你是一个专业的SQL数据库助手。你可以帮助用户查询PostgreSQL数据库。

你的工作流程：
1. 首先使用 list_tables 工具查看数据库中有哪些表
2. 使用 get_schema 工具获取相关表的结构信息
3. 根据用户的问题，生成正确的SQL查询
4. 使用 query 工具执行SQL查询
5. 将查询结果以友好的方式呈现给用户

注意事项：
- 只生成SELECT查询，不要执行任何修改数据的操作
- 如果不确定表结构，先查看schema
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


# MCP client 配置 (新版 API 不再需要单独的 create 函数)


async def run_agent(question: str, thread_id: str = "1"):
    """Run the SQL Agent with a question"""
    # 新版 API: 不使用 async with, 直接调用
    mcp_client = MultiServerMCPClient({
        "postgres": {
            "transport": "stdio",
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-postgres",
                config.database_url
            ],
        }
    })

    # 直接获取工具
    tools = await mcp_client.get_tools()
    llm = create_llm()
    llm_with_tools = llm.bind_tools(tools)

    # Define nodes
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

    tool_node = ToolNode(tools)

    # Build graph
    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue)
    builder.add_edge("tools", "agent")

    checkpointer = MemorySaver()
    agent = builder.compile(checkpointer=checkpointer)

    # Run the agent
    config_dict = {"configurable": {"thread_id": thread_id}}

    print(f"\n{'='*60}")
    print(f"问题: {question}")
    print(f"{'='*60}\n")

    step_count = 0

    # 使用 stream_mode="updates" 只获取增量更新
    async for step in agent.astream(
        {"messages": [HumanMessage(content=question)]},
        config_dict,
        stream_mode="updates",
    ):
        step_count += 1
        print(f"\n{'─'*60}")
        print(f"📍 第 {step_count} 步")
        print(f"{'─'*60}")

        # 打印原始 step 内容
        print(f"📦 Step 类型: {type(step)}")
        print(f"📦 Step keys: {step.keys() if isinstance(step, dict) else 'N/A'}")

        for node_name, node_output in step.items():
            print(f"\n🔹 节点名称: {node_name}")
            print(f"🔹 输出类型: {type(node_output)}")

            if "messages" in node_output:
                messages = node_output["messages"]
                print(f"🔹 消息数量: {len(messages)}")

                for i, msg in enumerate(messages):
                    print(f"\n  📨 消息 {i+1}:")
                    print(f"     类型: {type(msg).__name__}")

                    # 根据消息类型打印不同内容
                    if isinstance(msg, HumanMessage):
                        print(f"     👤 用户说: {msg.content[:100]}...")

                    elif isinstance(msg, AIMessage):
                        print(f"     🤖 AI 消息:")
                        if msg.content:
                            print(f"        内容: {msg.content[:200]}{'...' if len(msg.content) > 200 else ''}")
                        if msg.tool_calls:
                            print(f"        🔧 工具调用: {len(msg.tool_calls)} 个")
                            for tc in msg.tool_calls:
                                print(f"           - 工具名: {tc['name']}")
                                print(f"             参数: {tc['args']}")

                    elif hasattr(msg, 'content'):
                        # ToolMessage
                        print(f"     � 工具返回:")
                        content_preview = str(msg.content)[:300]
                        print(f"        {content_preview}{'...' if len(str(msg.content)) > 300 else ''}")
            else:
                print(f"🔹 输出内容: {node_output}")

    print(f"\n{'='*60}")
    print(f"✅ 完成! 共 {step_count} 步")
    print(f"{'='*60}")


async def interactive_mode():
    """Run the agent in interactive mode"""
    print("\n" + "="*60)
    print("🤖 SQL Agent 交互模式")
    print("输入 'exit' 或 'quit' 退出")
    print("="*60 + "\n")

    thread_id = "interactive_session"

    while True:
        try:
            question = input("\n📝 请输入你的问题: ").strip()

            if question.lower() in ["exit", "quit", "q"]:
                print("\n👋 再见!")
                break

            if not question:
                continue

            await run_agent(question, thread_id)

        except KeyboardInterrupt:
            print("\n\n👋 再见!")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")


if __name__ == "__main__":
    # Validate configuration
    config.validate_config()

    # Run interactive mode
    asyncio.run(interactive_mode())

