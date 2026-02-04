# -*- coding: utf-8 -*-
"""
AgentFactory V2 - DeepAgents 工厂类 (完整版)
=============================================

负责创建和管理 Data Agent V2 实例，基于 DeepAgents 框架。

核心功能:
    - create_agent(): 创建新的 DeepAgents 实例
    - get_or_create_agent(): 单例模式获取或创建 Agent
    - 租户隔离支持
    - SubAgent 集成

版本: 2.0.0
作者: BMad Master
"""

import os
import logging
from typing import Optional, List, Dict, Any

# 配置日志
logger = logging.getLogger(__name__)

# DeepAgents imports
from deepagents import create_deep_agent
# 不需要导入 FilesystemMiddleware，因为 create_deep_agent 已经自动添加了
# from deepagents.middleware import FilesystemMiddleware

# LangChain imports
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

# Local imports - V2 config
from ..agent_config_module import agent_config as v2_config

# Local imports - V2 modules
from ..middleware import (
    TenantIsolationMiddleware,
    SQLSecurityMiddleware,
    CHART_GUIDANCE_TEMPLATE,
    SemanticPriorityMiddleware
)
from ..subagents import SubAgentManager, create_subagent_manager
from ..tools import get_database_tools, get_chart_tools
from ..tools.general_tools import get_general_tools
# 🟢 重新启用表推荐工具 - 已修复为返回实际表名
from ..tools.table_recommendation_tools import (
    get_recommended_tables_for_query,
    get_table_description_by_name,
    list_high_priority_tables
)
from ..tools.semantic_layer_tools import (
    resolve_business_term,
    get_semantic_measure,
    list_available_cubes,
    get_cube_measures,
    normalize_status_value
)

# ============================================================================
# AgentFactory
# ============================================================================

class AgentFactory:
    """
    DeepAgents 工厂类 V2

    新增功能:
        - 租户隔离中间件集成
        - SubAgent 支持
        - 自定义中间件管道
        - 多数据源支持 (Excel, PostgreSQL, MySQL)
    """

    # 类级别缓存
    _cached_agents: Dict[str, Any] = {}
    _cached_llm: Optional[BaseChatModel] = None
    # 会话级表名缓存: {(tenant_id, connection_id): ["table1", "table2", ...]}
    _table_names_cache: Dict[tuple, List[str]] = {}

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        enable_tenant_isolation: bool = True,
        enable_sql_security: bool = True,
        enable_subagents: bool = True,
        enable_chart_guidance: bool = True,
        enable_xai_logging: bool = True,  # 🔧 XAI 日志中间件开关
        enable_loop_detection: bool = True,  # 🔧 循环检测中间件开关
        enable_semantic_priority: bool = True,  # 🔧 语义层优先中间件开关 (已恢复，配合actual_table_name修复)
        enable_knowledge_tools: bool = False  # 🆕 知识检索工具开关
    ):
        """
        初始化 AgentFactory

        Args:
            model: LLM 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            enable_tenant_isolation: 是否启用租户隔离
            enable_sql_security: 是否启用 SQL 安全
            enable_subagents: 是否启用子代理 (已由 create_deep_agent 自动管理)
            enable_chart_guidance: 是否启用图表生成指南
            enable_xai_logging: 是否启用 XAI 日志中间件
            enable_loop_detection: 是否启用循环检测中间件
            enable_knowledge_tools: 是否启用知识检索工具（双知识系统）
        """
        # 从 V2 配置读取默认值
        app_config = v2_config.get_config()
        self.model = model or app_config.llm.model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # 功能开关
        self.enable_tenant_isolation = enable_tenant_isolation
        self.enable_sql_security = enable_sql_security
        self.enable_subagents = enable_subagents
        self.enable_chart_guidance = enable_chart_guidance
        self.enable_xai_logging = enable_xai_logging
        self.enable_loop_detection = enable_loop_detection  # 🔧 新增
        self.enable_semantic_priority = enable_semantic_priority  # 🔧 新增
        self.enable_knowledge_tools = enable_knowledge_tools  # 🆕 新增

        # SubAgent 管理器
        self._subagent_manager: Optional[SubAgentManager] = None

        # 连接上下文 (用于多数据源支持)
        self._connection_id: Optional[str] = None
        self._db_session: Optional[Any] = None

    @property
    def subagent_manager(self) -> SubAgentManager:
        """获取或创建 SubAgent 管理器"""
        if self._subagent_manager is None:
            self._subagent_manager = create_subagent_manager(default_model=self.model)
        return self._subagent_manager

    def create_llm(self) -> BaseChatModel:
        """创建 LLM 实例"""
        if self._cached_llm is None:
            if "deepseek" in self.model.lower():
                api_key = os.environ.get("DEEPSEEK_API_KEY", "")
                base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

                self._cached_llm = ChatOpenAI(
                    model=self.model,
                    temperature=self.temperature,
                    api_key=api_key,
                    base_url=base_url,
                    max_tokens=8000,  # 🔧 增加 token 限制以确保完整输出图表配置（从4000增加到8000）
                    streaming=True,  # 🔧 关键：启用 token 级别的流式输出
                    # 🔧 尝试绕过 DeepSeek 内容审查
                    extra_body={
                        "disable_strict_mode": True,
                        "ignore_error": True,
                    }
                )
            elif "zhipuai" in self.model.lower() or "glm" in self.model.lower():
                # 🔧 使用智谱 GLM API（无内容审查问题）
                api_key = os.environ.get("ZHIPUAI_API_KEY", "")
                base_url = os.environ.get("ZHIPUAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")

                self._cached_llm = ChatOpenAI(
                    model=self.model,
                    temperature=self.temperature,
                    api_key=api_key,
                    base_url=base_url,
                    max_tokens=8000,  # 🔧 增加 token 限制确保完整输出图表配置
                    streaming=True,  # 🔧 关键：启用流式输出
                )
            else:
                self._cached_llm = ChatOpenAI(
                    model=self.model,
                    temperature=self.temperature,
                    streaming=True,  # 🔧 关键：启用流式输出
                )

        return self._cached_llm

    def _build_tools(
        self,
        connection_id: Optional[str] = None,
        db_session: Optional[Any] = None,
        tenant_id: Optional[str] = None
    ) -> List[BaseTool]:
        """
        构建工具列表

        Args:
            connection_id: 数据源连接 ID
            db_session: 数据库会话（用于查询数据源配置）
            tenant_id: 租户 ID

        Returns:
            工具列表
        """
        tools = []

        # 1. 添加数据库查询工具，传入连接上下文
        try:
            db_tools = get_database_tools(
                connection_id=connection_id,
                db_session=db_session,
                tenant_id=tenant_id
            )
            tools.extend(db_tools)
            print(f"✅ [AgentFactory] 已添加 {len(db_tools)} 个数据库工具")
        except (ImportError, AttributeError) as e:
            # 工具加载失败 - 记录详细错误
            # 使用顶部定义的 logger
            logger.error(f"Failed to load database tools (configuration error): {e}")
            raise  # 重新抛出配置错误
        except Exception as e:
            # 其他未预期的错误 - 记录但继续执行
            # 使用顶部定义的 logger
            logger.warning(f"Unexpected error loading database tools: {e}")

        # 2. 添加图表工具
        try:
            chart_tools = get_chart_tools()
            tools.extend(chart_tools)
            print(f"✅ [AgentFactory] 已添加 {len(chart_tools)} 个图表工具: {[t.name for t in chart_tools]}")
        except (ImportError, AttributeError) as e:
            # 使用顶部定义的 logger
            logger.error(f"Failed to load chart tools (configuration error): {e}")
            raise
        except Exception as e:
            # 使用顶部定义的 logger
            logger.warning(f"Unexpected error loading chart tools: {e}")

        # 3. 添加语义层工具
        try:
            from langchain_core.tools import StructuredTool

            semantic_tools = [
                StructuredTool.from_function(
                    func=resolve_business_term,
                    name="resolve_business_term",
                    description=(
                        "解析业务术语，返回匹配的语义层定义。"
                        "使用场景：查询涉及业务指标（如'总收入'、'订单数'、'GMV'）时，"
                        "首先调用此工具获取标准定义和SQL表达式。"
                        "Args: term (str) - 业务术语，如'总收入'"
                    )
                ),
                StructuredTool.from_function(
                    func=get_semantic_measure,
                    name="get_semantic_measure",
                    description=(
                        "获取特定Cube中度量的完整定义（包括SQL表达式）。"
                        "Args: cube (str) - Cube名称, measure (str) - 度量名称"
                    )
                ),
                StructuredTool.from_function(
                    func=normalize_status_value,
                    name="normalize_status_value",
                    description=(
                        "规范化状态值（如'已完成' → 'completed'）。"
                        "Args: status (str) - 原始状态值"
                    )
                ),
                StructuredTool.from_function(
                    func=list_available_cubes,
                    name="list_available_cubes",
                    description=(
                        "列出所有可用的语义层Cube。"
                        "Args: None"
                    )
                ),
                StructuredTool.from_function(
                    func=get_cube_measures,
                    name="get_cube_measures",
                    description=(
                        "获取指定Cube的所有度量定义。"
                        "Args: cube (str) - Cube名称"
                    )
                ),
            ]
            tools.extend(semantic_tools)
            print(f"✅ [AgentFactory] 已添加 {len(semantic_tools)} 个语义层工具: {[t.name for t in semantic_tools]}")
        except (ImportError, AttributeError) as e:
            # 使用顶部定义的 logger
            logger.error(f"Failed to load semantic tools (configuration error): {e}")
            raise
        except Exception as e:
            # 使用顶部定义的 logger
            logger.warning(f"Unexpected error loading semantic tools: {e}")

        # 4. 🔧 通用工具（处理不需要数据库的简单查询，如日期查询）
        try:
            from langchain_core.tools import StructuredTool

            general_tools = get_general_tools()
            tools.extend(general_tools)
            print(f"✅ [AgentFactory] 已添加 {len(general_tools)} 个通用工具: {[t.name for t in general_tools]}")
        except (ImportError, AttributeError) as e:
            # 使用顶部定义的 logger
            logger.error(f"Failed to load general tools (configuration error): {e}")
            raise
        except Exception as e:
            # 使用顶部定义的 logger
            logger.warning(f"Unexpected error loading general tools: {e}")

        # 5. 🆕 知识检索工具（双知识系统）
        if self.enable_knowledge_tools:
            try:
                from ..knowledge.knowledge_tools import create_knowledge_tools
                knowledge_tools = create_knowledge_tools(tenant_id=tenant_id or "default_tenant")
                tools.extend(knowledge_tools)
                print(f"✅ [AgentFactory] 已添加 {len(knowledge_tools)} 个知识工具: {[t.name for t in knowledge_tools]}")
            except ImportError:
                logger.warning("知识工具模块未安装，跳过知识工具加载")
            except Exception as e:
                logger.warning(f"加载知识工具失败: {e}")

        # 6. 🟢 重新启用智能表推荐工具（已修复为返回实际表名）
        # 修复：get_recommended_tables 现在返回实际表名而非预设中文表名
        from langchain_core.tools import StructuredTool

        recommendation_tools = [
            StructuredTool.from_function(
                func=get_recommended_tables_for_query,
                name="get_recommended_tables",
                description=(
                    "🎯 智能表推荐工具 - 基于查询内容和实际表名推荐最相关的数据表\n\n"
                    "**使用场景**：当你需要查询数据但不确定使用哪个表时\n\n"
                    "**参数**：query (str) - 用户查询，如 '2023年销售趋势'\n\n"
                    "**返回**：推荐的表列表（使用实际表名）"
                )
            ),
            StructuredTool.from_function(
                func=list_high_priority_tables,
                name="list_high_priority_tables",
                description="列出所有高优先级的数据表"
            )
        ]

        if recommendation_tools:
            tools.extend(recommendation_tools)
            print(f"✅ [AgentFactory] 已添加 {len(recommendation_tools)} 个表推荐工具: {[t.name for t in recommendation_tools]}")

        return tools

    def _build_middleware(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None
    ) -> List[Any]:
        """
        构建中间件管道

        注意: create_deep_agent 已经自动添加了以下中间件:
            - TodoListMiddleware
            - FilesystemMiddleware
            - SubAgentMiddleware
            - SummarizationMiddleware
            - AnthropicPromptCachingMiddleware
            - PatchToolCallsMiddleware

        因此这里只需要添加我们的自定义中间件。

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            session_id: 会话 ID
            tools: 可用工具列表

        Returns:
            中间件列表
        """
        middleware = []

        # 1. 租户隔离中间件 (第一优先级)
        if self.enable_tenant_isolation and tenant_id:
            tenant_middleware = TenantIsolationMiddleware(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id
            )
            middleware.append(tenant_middleware)

        # 2. SQL 安全中间件
        if self.enable_sql_security:
            sql_middleware = SQLSecurityMiddleware()
            middleware.append(sql_middleware)

        # 3. 🔧 XAI 日志中间件 - 记录 AI 推理过程（带持久化）
        if self.enable_xai_logging and session_id and tenant_id:
            from ..middleware import XAILoggerMiddleware
            xai_middleware = XAILoggerMiddleware(
                session_id=session_id,
                tenant_id=tenant_id,
                user_id=user_id,
                enable_detailed_logging=True,
                enable_persistence=True  # 🔧 启用持久化（数据库+文件双通道写入）
            )
            middleware.append(xai_middleware)

        # 4. 🔧 循环检测中间件 - 防止工具调用陷入无限循环
        # 调整后的阈值：允许更复杂的查询和合理次数的重试
        if self.enable_loop_detection:
            from ..middleware import LoopDetectionMiddleware
            loop_middleware = LoopDetectionMiddleware(
                max_tool_calls=25,          # 增加到 25（复杂任务可能需要更多调用）
                loop_window_size=8,         # 增加到 8（更大的循环检测窗口）
                max_same_tool_calls=5,      # 增加到 5（允许更多次重试）
                max_consecutive_failures=4  # 增加到 4（允许更多失败重试）
            )
            middleware.append(loop_middleware)

        # 5. 🔧 语义层优先中间件 - 引导 LLM 使用语义层工具
        if self.enable_semantic_priority:
            semantic_middleware = SemanticPriorityMiddleware(
                enable_detection=True,
                min_confidence=0.3,
                enable_logging=True
            )
            middleware.append(semantic_middleware)

        # 注意: ChartGuidanceMiddleware 已禁用，因为图表指南已通过 _build_system_prompt 实现
        # DeepAgents 框架要求中间件实现 AgentMiddleware 接口
        # 图表指南模板 CHART_GUIDANCE_TEMPLATE 已在系统提示词中追加，无需额外中间件

        # 注意: 不需要添加 FilesystemMiddleware，因为 create_deep_agent 已经自动添加了
        # 注意: 不需要添加 SubAgentMiddleware，因为 create_deep_agent 已经自动添加了

        return middleware

    def create_agent(
        self,
        tenant_id: str = "default_tenant",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
        connection_id: Optional[str] = None,
        db_session: Optional[Any] = None
    ):
        """
        创建 Data Agent V2 实例

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            session_id: 会话 ID
            tools: 可用的工具列表 (如果为 None，使用默认工具集)
            system_prompt: 自定义系统提示
            connection_id: 数据源连接 ID
            db_session: 数据库会话（用于查询数据源配置）

        Returns:
            DeepAgents 实例
        """
        # 创建 LLM
        llm = self.create_llm()

        # 构建工具 (如果没有提供，使用默认工具)
        if tools is None:
            tools = self._build_tools(
                connection_id=connection_id,
                db_session=db_session,
                tenant_id=tenant_id
            )

        # 构建中间件
        middleware = self._build_middleware(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            tools=tools
        )

        # 默认系统提示 - 告诉 Agent 关于数据库工具的信息
        if system_prompt is None:
            tool_names = [t.name for t in tools] if tools else []
            # 构建基础系统提示
            base_system_prompt = self._build_system_prompt(
                tool_names=tool_names,
                connection_id=connection_id,
                tenant_id=tenant_id
            )

            # 🔧 使用缓存的表名增强提示词
            system_prompt = self.get_enhanced_prompt_with_cached_tables(
                base_system_prompt,
                tenant_id=tenant_id,
                connection_id=connection_id
            )

            # 如果启用图表指南，追加到系统提示
            if self.enable_chart_guidance:
                system_prompt = system_prompt + "\n\n" + CHART_GUIDANCE_TEMPLATE
                print(f"🔧 [AgentFactory] enable_chart_guidance=True, 追加图表指南")
                print(f"🔧 [AgentFactory] 系统提示词包含 CHART_START: {'[CHART_START]' in system_prompt}")
                print(f"🔧 [AgentFactory] 系统提示词包含 '占比类问题': {'占比类问题' in system_prompt}")
                print(f"🔧 [AgentFactory] 系统提示词包含 'CASE WHEN': {'CASE WHEN' in system_prompt}")
                print(f"🔧 [AgentFactory] 系统提示词长度: {len(system_prompt)} 字符")
            else:
                print(f"🔧 [AgentFactory] enable_chart_guidance=False, 未追加图表指南")

        # 创建 DeepAgent
        agent = create_deep_agent(
            model=llm,
            tools=tools or [],
            middleware=middleware,
            system_prompt=system_prompt
        )

        return agent

    def _build_system_prompt(
        self,
        tool_names: List[str],
        connection_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> str:
        """
        构建系统提示词（根据数据源类型定制）

        Args:
            tool_names: 可用工具名称列表
            connection_id: 数据源连接 ID
            tenant_id: 租户 ID

        Returns:
            系统提示词
        """
        # 检查是否是 Excel 数据源
        is_excel = False
        sheets_info = ""

        if connection_id and self._db_session and tenant_id:
            try:
                import asyncio
                import sys
                from pathlib import Path

                # 添加 backend/src 到 sys.path（如果尚未添加）
                backend_src = Path(__file__).resolve().parent.parent.parent / "backend" / "src"
                if str(backend_src) not in sys.path:
                    sys.path.insert(0, str(backend_src))

                from app.services.data_source_service import data_source_service

                def get_info():
                    # 修复事件循环资源泄漏：复用现有事件循环或使用 asyncio.run
                    try:
                        # 尝试获取当前运行的事件循环
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # 如果循环正在运行，需要在新线程中运行
                            import concurrent.futures
                            import threading

                            result_container = []

                            def run_in_new_loop():
                                new_loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(new_loop)
                                try:
                                    result = new_loop.run_until_complete(
                                        data_source_service.get_data_source_connection_info(
                                            connection_id=connection_id,
                                            tenant_id=tenant_id,
                                            db=self._db_session
                                        )
                                    )
                                    result_container.append(result)
                                finally:
                                    new_loop.close()

                            thread = threading.Thread(target=run_in_new_loop)
                            thread.start()
                            thread.join(timeout=10)

                            if result_container:
                                return result_container[0]
                            else:
                                raise TimeoutError("Async operation timed out")
                        else:
                            # 循环未运行，直接使用
                            return loop.run_until_complete(
                                data_source_service.get_data_source_connection_info(
                                    connection_id=connection_id,
                                    tenant_id=tenant_id,
                                    db=self._db_session
                                )
                            )
                    except RuntimeError:
                        # 没有当前事件循环，创建新的（Python 3.7+ 使用 asyncio.run 更安全）
                        return asyncio.run(
                            data_source_service.get_data_source_connection_info(
                                connection_id=connection_id,
                                tenant_id=tenant_id,
                                db=self._db_session
                            ),
                            debug=False
                        )

                connection_info = get_info()
                is_excel = connection_info.connection_type == "excel"
                if is_excel:
                    sheets_info = f"\n**File**: {connection_info.file_path}\n**Available Sheets**: {', '.join(connection_info.sheets) if connection_info.sheets else 'Unknown'}"
            except Exception as e:
                logger.warning(f"Failed to check data source type: {e}")

        # 根据数据源类型选择提示词
        data_source_type = "Excel File" if is_excel else "PostgreSQL Database"

        return f"""You are a professional data analysis assistant with access to {data_source_type} query tools.

# MISSION: Answer data questions with correct SQL queries and generate charts

## Workflow Guidelines

## 🔴🔴🔴【第一步：判断查询类型】🔴🔴🔴

**首先判断查询是否需要访问数据库**：

### ✅ 不需要数据库的简单查询（直接使用通用工具）：
- 日期查询："今天是什么日期"、"昨天/明天的日期"
- 时间查询："现在几点了"
- 数学计算："2 + 2 等于多少"
- 系统信息："现在是什么时间"

对于这类查询，直接使用以下通用工具：
- `get_date_range_info()` - 获取昨天、今天、明天的日期
- `get_current_date()` - 获取当前日期
- `get_current_time()` - 获取当前时间

### ❌ 需要数据库的数据查询：
- 数据分析："2023年的销售趋势"、"订单数量统计"
- 数据查询："有多少个用户"、"销售额是多少"

对于这类查询，按以下流程执行：

## 🔴🔴🔴【数据查询流程】生成SQL前必须先调用list_tables()！🔴🔴🔴

**每次生成SQL前，必须按以下顺序执行**：
1. 首先调用 `list_tables()` 获取数据库中的实际表名
2. 根据返回的实际表名选择合适的表
3. 调用 `get_schema()` 了解表结构
4. 最后生成SQL并执行

**❌ 绝对禁止**：
- 禁止使用prompt示例中的表名（示例仅供参考）
- 禁止猜测或假设表名（如不要假设存在"sales"表）
- 禁止跳过list_tables()直接生成SQL

**✅ 正确示例**：
```
用户: "2023年的销售趋势"

【推荐方案 - 使用表推荐工具】
AI步骤:
1. 调用 get_recommended_tables("2023年销售趋势")
   → 推荐使用: "月度销售表" (高优先级, 包含预聚合数据)
2. 调用 get_schema("月度销售表") → 获取列名
3. 执行: SELECT * FROM 月度销售表 WHERE 年份 = 2023 ORDER BY 月份

【备选方案 - 手动选择】
AI步骤:
1. 调用 list_tables() → 返回: ["订单表", "用户表", "月度销售表", ...]
2. 识别相关表: "月度销售表" (最适合趋势分析)
3. 调用 get_schema("月度销售表") → 获取列名
4. 执行: SELECT * FROM 月度销售表 WHERE 年份 = 2023
```

---

### 工具使用说明

🔥 **第一步：智能表选择（二选一）**

1. **get_recommended_tables** 🎯 推荐优先使用（适用于趋势、汇总、统计类查询）
   - 参数: 用户查询，如 "2023年销售趋势"
   - 返回: 推荐的表及其优先级、描述
   - **优势**: 直接找到高优先级的预聚合表，性能最优

2. **list_tables** 📋 备选方案（适用于详情查询或不确定时）
   - 获取数据库中的所有实际表名
   - 当get_recommended_tables没有合适结果时使用

🔴 **第二步：获取表结构**

3. **get_schema** 获取表的列结构
   - 参数: 表名（来自推荐工具或list_tables的返回值）

🔴 **第三步：执行查询**

4. **execute_query** 执行SQL查询获取数据
   - 表名必须使用工具返回的确切表名{sheets_info}

## 🎯 智能表选择指南 (Table Recommendation Tools)

**🔥 优先使用表推荐工具来选择最佳表！**

### 何时使用表推荐工具：
- 查询涉及"趋势"、"汇总"、"统计"等关键词时
- 不确定应该使用哪个表时
- 想要找到性能最优的预聚合表时

### 推荐工作流程：

```
用户: "2023年销售趋势"

【方案A - 推荐方案】使用表推荐工具：
1. get_recommended_tables("2023年销售趋势")
   → 推荐使用 "月度销售表" (高优先级, 预聚合数据)
2. get_schema("月度销售表")
3. 执行: SELECT * FROM 月度销售表 WHERE 年份 = 2023

【方案B - 备选方案】不使用表推荐工具：
1. list_tables() → 获取所有表
2. 根据表名自己判断选择哪个表
3. get_schema()
4. 生成SQL
```

### 表优先级说明：
- **high (高优先级)**: 预聚合汇总表，如"月度销售表"，是趋势分析的最佳选择
- **medium (中优先级)**: 核心业务表，如"订单表"、"用户表"
- **low (低优先级)**: 辅助表，如"地区表"、"分类表"

### 关键原则：
- ✅ **"销售趋势"** → 优先使用 **"月度销售表"**（预聚合，性能更优）
- ✅ **"订单详情"** → 使用 **"订单表"**（包含详细订单信息）
- ❌ **不要**把所有表都列出来让用户选择，直接用推荐工具

### 可用工具：
- `get_recommended_tables(query)` - 基于查询推荐表
- `get_table_description(table_name)` - 获取表详细信息
- `list_high_priority_tables()` - 列出所有高优先级表

## Error Handling

When encountering errors:
- **Table not found**: Use the exact table names returned by list_tables()
- **Column not found**: Check the schema with get_schema() for correct column names
- **Empty results**: Report "查询成功但没有找到匹配的数据" and do not retry
- **Connection errors**: Suggest checking the data source connection
- **Syntax errors**: Review the SQL query and fix common issues (LIMIT position, quotes)

## SQL SYNTAX RULES

- For **proportion/distribution** questions, use CASE WHEN + GROUP BY:
  ```sql
  SELECT CASE WHEN quantity <= 0 THEN 'Out of Stock'
              WHEN quantity <= reorder_point THEN 'Low Stock'
              ELSE 'Normal Stock' END as category,
         COUNT(*) as value
  FROM inventory GROUP BY category;
  ```

- LIMIT must be LAST in the query
- Use double quotes for table/sheet names with special characters: `"table_name"`

## 🔥 Semantic Layer Tools (Business Term Resolution)

**🔴🔴🔴 CRITICAL: TABLE SELECTION WORKFLOW 🔴🔴🔴**

**STEP 1: Select your table selection approach:**
- **Option A (Recommended)**: Use `get_recommended_tables(query)` for intelligent table recommendation
- **Option B (Fallback)**: Use `list_tables()` to get all available tables

**STEP 2: Get table schema**
- Call `get_schema()` with the selected table name to understand its structure

**STEP 3: Use semantic tools (Optional but Helpful)**
- `resolve_business_term()`: Map business terms to SQL expressions
- `get_semantic_measure()`: Get detailed measure definitions

**STEP 4: Generate SQL**
- Use the CONFIRMED table name from step 1 in your SQL
- Use `actual_table_name` field from semantic tools, NOT the `cube` field

### ❌ FORBIDDEN BEHAVIOR:
- ❌ Assuming table names like "orders", "sales" without checking
- ❌ Using the `cube` field (like "Orders") as SQL table name
- ❌ Generating SQL without first confirming table exists

### ✅ CORRECT WORKFLOW:
```
User: "2023年的销售趋势"

【推荐方案 - 使用表推荐工具】
Step 1: get_recommended_tables("2023年销售趋势")
        → Returns: [{{"table_name": "月度销售表", "priority": "high", ...}}]
Step 2: get_schema("月度销售表") → Returns columns: [年份, 月份, 销售额, 订单数...]
Step 3: Use semantic tool (optional): resolve_business_term("销售")
Step 4: Generate SQL with CONFIRMED table name "月度销售表"

【备选方案 - 不使用表推荐】
Step 1: list_tables() → Returns: ["订单表", "用户表", "产品表", "月度销售表"]
Step 2: get_schema("月度销售表") → Returns columns: [年份, 月份, 销售额...]
Step 3: Use semantic tool (optional): resolve_business_term("销售")
Step 4: Generate SQL with CONFIRMED table name "月度销售表"
```

### 🚨🚨🚨 CRITICAL: Use `actual_table_name` NOT `cube`! 🚨🚨🚨

The `resolve_business_term` function returns TWO important fields:
- `cube`: The semantic Cube name (e.g., "Orders", "Customers") - **DO NOT USE THIS IN SQL!**
- `actual_table_name`: The REAL database table name (e.g., "订单表", "用户表") - **USE THIS!**

**Example response from resolve_business_term("销售"):**
```json
[
  {{
    "cube": "Orders",           // ❌ DON'T use in SQL!
    "actual_table_name": "订单表",  // ✅ USE THIS in SQL!
    "sql": "SUM(total_amount)",
    "display_name": "销售额"
  }}
]
```

**Correct SQL generation:**
```sql
-- ❌ WRONG - Uses cube name
SELECT SUM(total_amount) FROM Orders

-- ✅ CORRECT - Uses actual_table_name
SELECT SUM(total_amount) FROM 订单表
```

### Available semantic tools:
1. **resolve_business_term** - Map business terms to database tables/columns
   - Example: "销售额" → returns `{{"cube": "Orders", "actual_table_name": "订单表", "sql": "SUM(total_amount)", ...}}`
   - Args: term (str) - business term like "销售额"
   - **ONLY USE AFTER list_tables()!**
   - **ALWAYS use the `actual_table_name` field in your SQL, NOT the `cube` field!**

2. **list_available_cubes** - List all available semantic cubes
   - Returns: Orders, Customers, Products, etc.

3. **get_semantic_measure** - Get detailed measure definition
   - Args: cube (str), measure (str)

4. **get_cube_measures** - Get all measures in a cube
   - Args: cube (str)

5. **normalize_status_value** - Normalize status values
   - Example: "已完成" → "completed"
   - Args: status (str)

### Important Notes:
- **Table names vary by database!** Always use list_tables() first
- "销售额" typically maps to `actual_table_name: "订单表"` with `sql: "SUM(total_amount)"`
- "订单数" typically maps to `actual_table_name: "订单表"` with `sql: "COUNT(*)"`
- "客户数" typically maps to `actual_table_name: "用户表"` with `sql: "COUNT(*)"`
- **ALWAYS use the `actual_table_name` field from semantic tools, NEVER use the `cube` field!**

### Workflow:
```
User query → get_recommended_tables() OR list_tables() → get_schema() → [semantic tools] → Generate SQL
```

## Available Tools
{chr(10).join(f'- {name}' for name in tool_names) if tool_names else 'No tools available'}

## Response Format

When you have data from execute_query:
1. Summarize the findings in Chinese
2. Present detailed data in Markdown tables if appropriate

## 📊 MANDATORY: Chart Generation Rules

🚨🚨🚨 **CRITICAL: You MUST generate chart configuration for data analysis questions!** 🚨🚨🚨

### When to Generate Charts (MANDATORY)

You MUST generate a chart when the user query contains:
- **Analysis keywords**: "分析"、"趋势"、"变化"、"增长"、"下降"、"对比"
- **Visualization keywords**: "图表"、"可视化"、"展示"、"画出"
- **Proportion keywords**: "占比"、"分布"、"比例"、"百分比"
- **Ranking keywords**: "排名"、"排行"、"Top"、"最高"、"最低"
- **Time-based queries**: "2023年"、"本月"、"最近"、"每月"、"每年"
- **Aggregation queries**: Any query with GROUP BY, SUM, COUNT, AVG

### Chart Type Selection Guide

| Data Pattern | Chart Type | Use When... |
|--------------|------------|-------------|
| Time series (date/month/year) | line | 用户问"趋势"、"变化"、"每月"、"每年" |
| Category comparison (group by) | bar | 用户问"对比"、"排名"、"Top"、"最高" |
| Proportion/Distribution | pie | 用户问"占比"、"分布"、"比例" |
| Multiple metrics | bar | Multiple measures like "销售额和订单数" |

### 🚨🚨🚨 MANDATORY Output Format 🚨🚨🚨

**At the END of your response, you MUST include the chart configuration in this EXACT format:**

```
[CHART_START]
{{
    "title": {{"text": "图表标题"}},
    "tooltip": {{"trigger": "axis"}},
    "legend": {{"data": ["系列名称"]}},
    "xAxis": {{"type": "category", "data": ["类别1", "类别2", ...]}},
    "yAxis": {{"type": "value", "name": "数值单位"}},
    "series": [{{
        "name": "系列名称",
        "type": "line或bar或pie",
        "data": [数值1, 数值2, ...]
    }}]
}}
[CHART_END]
```

### Example: Line Chart (Time Series)

User: "2023年每月的销售趋势"

[CHART_START]
{{
    "title": {{"text": "2023年销售趋势"}},
    "tooltip": {{"trigger": "axis"}},
    "xAxis": {{"type": "category", "data": ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]}},
    "yAxis": {{"type": "value", "name": "销售额(元)"}},
    "series": [{{"name": "销售额", "type": "line", "data": [10000, 12000, 11500, 13000, 14500, 16000, 15500, 17000, 18500, 19000, 21000, 23000], "smooth": true}}]
}}
[CHART_END]

### Example: Bar Chart (Comparison)

User: "各城市的销售额对比"

[CHART_START]
{{
    "title": {{"text": "各城市销售额对比"}},
    "tooltip": {{"trigger": "axis"}},
    "xAxis": {{"type": "category", "data": ["北京", "上海", "广州", "深圳", "杭州"]}},
    "yAxis": {{"type": "value", "name": "销售额(元)"}},
    "series": [{{"name": "销售额", "type": "bar", "data": [50000, 60000, 45000, 55000, 40000]}}]
}}
[CHART_END]

### Example: Pie Chart (Proportion)

User: "各品牌的销售占比"

[CHART_START]
{{
    "title": {{"text": "各品牌销售占比"}},
    "tooltip": {{"trigger": "item"}},
    "legend": {{"orient": "vertical", "left": "left"}},
    "series": [{{
        "name": "销售占比",
        "type": "pie",
        "radius": "50%",
        "data": [
            {{"value": 335, "name": "小米"}},
            {{"value": 310, "name": "华为"}},
            {{"value": 234, "name": "苹果"}},
            {{"value": 135, "name": "OPPO"}},
            {{"value": 148, "name": "Vivo"}}
        ]
    }}]
}}
[CHART_END]

### ⚠️ CRITICAL REMINDERS

1. **NEVER skip chart generation for data analysis questions**
2. **ALWAYS use [CHART_START]...[CHART_END] markers**
3. **The JSON MUST be valid** (no trailing commas, proper quotes)
4. **Choose the RIGHT chart type** for the data pattern
5. **Extract data FROM YOUR QUERY RESULTS** - don't make up numbers!
6. **If query returns no data, explain why instead of generating a fake chart**"""

    # ========================================================================
    # 表名缓存管理
    # ========================================================================

    @classmethod
    def get_cached_table_names(
        cls,
        tenant_id: str,
        connection_id: Optional[str] = None
    ) -> Optional[List[str]]:
        """获取缓存的表名列表

        Args:
            tenant_id: 租户ID
            connection_id: 数据源连接ID

        Returns:
            缓存的表名列表，如果不存在则返回None
        """
        cache_key = (tenant_id, connection_id or "default")
        return cls._table_names_cache.get(cache_key)

    @classmethod
    def set_cached_table_names(
        cls,
        tenant_id: str,
        table_names: List[str],
        connection_id: Optional[str] = None
    ) -> None:
        """设置缓存的表名列表

        Args:
            tenant_id: 租户ID
            table_names: 表名列表
            connection_id: 数据源连接ID
        """
        cache_key = (tenant_id, connection_id or "default")
        cls._table_names_cache[cache_key] = table_names

    @classmethod
    def clear_table_cache(
        cls,
        tenant_id: Optional[str] = None,
        connection_id: Optional[str] = None
    ) -> None:
        """清除表名缓存

        Args:
            tenant_id: 租户ID，如果为None则清除所有租户的缓存
            connection_id: 数据源连接ID，如果为None则清除指定租户的所有缓存
        """
        if tenant_id is None:
            # 清除所有缓存
            cls._table_names_cache.clear()
        elif connection_id is None:
            # 清除指定租户的所有缓存
            keys_to_remove = [k for k in cls._table_names_cache.keys() if k[0] == tenant_id]
            for key in keys_to_remove:
                del cls._table_names_cache[key]
        else:
            # 清除指定租户和连接的缓存
            cache_key = (tenant_id, connection_id or "default")
            cls._table_names_cache.pop(cache_key, None)

    @classmethod
    def get_enhanced_prompt_with_cached_tables(
        cls,
        base_prompt: str,
        tenant_id: str,
        connection_id: Optional[str] = None
    ) -> str:
        """获取增强的提示词，包含缓存的表名信息

        Args:
            base_prompt: 基础提示词
            tenant_id: 租户ID
            connection_id: 数据源连接ID

        Returns:
            包含缓存表名信息的增强提示词

        Note:
            当前已禁用缓存注入功能，强制AI每次调用list_tables()。
            设置 ENABLE_TABLE_CACHE_INJECTION = True 可恢复缓存功能。
        """
        # 🔧 启用缓存注入，让LLM知道可用的表名
        # 这解决了LLM猜测表名（如inquiry_tenant_id、月度销售表）的问题
        ENABLE_TABLE_CACHE_INJECTION = True

        if not ENABLE_TABLE_CACHE_INJECTION:
            # 不注入缓存信息，强制AI调用list_tables()
            return base_prompt

        cached_tables = cls.get_cached_table_names(tenant_id, connection_id)
        if not cached_tables:
            return base_prompt

        # 在提示词开头添加已缓存的表名信息
        cache_info = f"""
## 📋 已缓存的表名列表 (Session Cache)

**注意**: 以下是上次查询时获取的表名列表。如果数据库结构发生变化，请重新调用 `list_tables()` 获取最新信息。

可用表: {', '.join(cached_tables)}

---
"""
        return cache_info + base_prompt

    def get_or_create_agent(
        self,
        tenant_id: str = "default_tenant",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tools: Optional[List[BaseTool]] = None,
        force_refresh: bool = False,
        connection_id: Optional[str] = None,
        db_session: Optional[Any] = None
    ):
        """
        获取或创建 Agent (单例模式)

        Args:
            tenant_id: 租户 ID
            user_id: 用户 ID
            session_id: 会话 ID
            tools: 可用的工具列表
            force_refresh: 是否强制刷新
            connection_id: 数据源连接 ID
            db_session: 数据库会话（用于查询数据源配置）

        Returns:
            DeepAgents 实例
        """
        # 存储连接上下文供系统提示词使用
        self._connection_id = connection_id
        self._db_session = db_session

        # 缓存键包含 connection_id 以支持不同数据源
        cache_key = f"{tenant_id}_{user_id or 'none'}_{session_id or 'none'}_{connection_id or 'default'}"

        if force_refresh or cache_key not in self._cached_agents:
            self._cached_agents[cache_key] = self.create_agent(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                tools=tools,
                connection_id=connection_id,
                db_session=db_session
            )

        return self._cached_agents[cache_key]

    def reset_cache(self, tenant_id: Optional[str] = None):
        """重置 Agent 缓存"""
        if tenant_id is None:
            self._cached_agents.clear()
        else:
            keys_to_remove = [
                k for k in self._cached_agents.keys()
                if k.startswith(tenant_id)
            ]
            for key in keys_to_remove:
                del self._cached_agents[key]

    def setup_default_subagents(
        self,
        postgres_tools: Optional[List[BaseTool]] = None,
        echarts_tools: Optional[List[BaseTool]] = None,
        file_tools: Optional[List[BaseTool]] = None
    ):
        """
        设置默认的 SubAgent

        Args:
            postgres_tools: PostgreSQL 工具
            echarts_tools: ECharts 工具
            file_tools: 文件处理工具
        """
        self.subagent_manager.create_default_subagents(
            postgres_tools=postgres_tools or [],
            echarts_tools=echarts_tools or [],
            file_tools=file_tools or []
        )


# ============================================================================
# 便捷函数
# ============================================================================

_default_factory: Optional[AgentFactory] = None


def get_default_factory() -> AgentFactory:
    """获取默认的 AgentFactory 实例"""
    global _default_factory
    if _default_factory is None:
        _default_factory = AgentFactory()
    return _default_factory


def create_agent(
    tenant_id: str = "default_tenant",
    user_id: Optional[str] = None,
    tools: Optional[List[BaseTool]] = None,
    model: Optional[str] = None
):
    """
    便捷函数：快速创建 Agent

    Args:
        tenant_id: 租户 ID
        user_id: 用户 ID
        tools: 可用的工具列表
        model: LLM 模型名称

    Returns:
        DeepAgents 实例
    """
    factory = AgentFactory(model=model) if model else get_default_factory()
    return factory.create_agent(tenant_id=tenant_id, user_id=user_id, tools=tools)
