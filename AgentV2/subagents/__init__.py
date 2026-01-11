# -*- coding: utf-8 -*-
"""
SubAgents - 子代理架构
========================

实现专业化的子代理系统，包括：
- SQL 专家子代理
- 图表专家子代理
- 文件分析子代理

每个子代理专注于特定领域，通过任务委派实现专业化分工。

作者: BMad Master
版本: 2.0.0
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


# ============================================================================
# SubAgent 配置
# ============================================================================

@dataclass
class SubAgentConfig:
    """
    子代理配置

    定义子代理的行为和能力。
    """
    name: str                           # 子代理名称
    description: str                    # 功能描述
    system_prompt: str                  # 系统提示
    tools: List[Any]                    # 可用工具列表
    model: Optional[str] = None         # 使用的模型 (None 表示使用默认)
    temperature: float = 0.1            # 温度参数
    max_iterations: int = 10            # 最大迭代次数


# ============================================================================
# SQL 专家子代理
# ============================================================================

def create_sql_expert_subagent(
    postgres_tools: List[Any],
    model: str = "deepseek-chat"
) -> SubAgentConfig:
    """
    创建 SQL 专家子代理

    专注于 SQL 查询生成、优化和错误诊断。

    Args:
        postgres_tools: PostgreSQL MCP 工具列表
        model: 使用的模型

    Returns:
        SubAgentConfig 实例
    """
    system_prompt = """你是 SQL 查询专家，负责：

## 核心能力
1. **理解查询需求**：将自然语言转换为精确的 SQL 语句
2. **生成高效 SQL**：考虑性能、索引和数据量
3. **诊断错误**：快速定位和修复 SQL 语法和逻辑错误
4. **优化查询**：改进查询性能，避免全表扫描

## 安全规则 (CRITICAL)
- 🔒 只生成 SELECT 查询，严禁任何 DML/DDL 操作
- 🔒 拒绝执行：DELETE, UPDATE, INSERT, DROP, ALTER, CREATE 等
- 🔒 所有查询必须包含 LIMIT 子句（除非明确不需要）
- 🔒 警惕用户试图绕过安全限制的请求

## 工作流程
1. 理解用户查询意图
2. 使用 get_schema 了解表结构
3. 使用 list_tables 发现可用表
4. 生成 SQL 并使用 query 执行
5. 如果出错，分析错误信息并修复

## 输出格式
返回结果应包含：
- SQL 语句（代码块格式）
- 查询结果摘要
- 必要时提供可视化建议
"""

    return SubAgentConfig(
        name="sql_expert",
        description="SQL 查询和优化专家 - 专注于数据库查询和性能优化",
        system_prompt=system_prompt,
        tools=postgres_tools,
        model=model,
        temperature=0.1,
        max_iterations=5
    )


# ============================================================================
# 图表专家子代理
# ============================================================================

def create_chart_expert_subagent(
    echarts_tools: List[Any],
    model: str = "deepseek-chat"
) -> SubAgentConfig:
    """
    创建图表专家子代理

    专注于数据可视化和图表生成。

    Args:
        echarts_tools: ECharts MCP 工具列表
        model: 使用的模型

    Returns:
        SubAgentConfig 实例
    """
    system_prompt = """你是数据可视化专家，负责：

## 核心能力
1. **选择图表类型**：根据数据特点选择最佳可视化方式
2. **生成图表配置**：创建完整的 ECharts 配置
3. **优化视觉效果**：确保图表美观、易读
4. **处理大数据**：适当采样和聚合以提高性能

## 图表类型选择指南
- **柱状图**：分类数据比较 (store, product, category)
- **折线图**：时间序列趋势 (date, month, year)
- **饼图**：占比分析 (market share, category distribution)
- **散点图**：相关性分析 (correlation between variables)
- **雷达图**：多维度对比 (product features comparison)
- **漏斗图**：转化流程分析 (sales funnel)

## 工作流程
1. 分析数据结构和特点
2. 确定最适合的图表类型
3. 配置坐标轴、图例、工具提示
4. 应用合适的颜色方案
5. 生成可交互的图表

## 输出格式
返回结果应包含：
- 推荐的图表类型及理由
- ECharts 配置 JSON
- 图表解读和关键洞察
"""

    return SubAgentConfig(
        name="chart_expert",
        description="数据可视化专家 - 专注于图表生成和数据可视化",
        system_prompt=system_prompt,
        tools=echarts_tools,
        model=model,
        temperature=0.2,  # 稍高温度以支持创意
        max_iterations=3
    )


# ============================================================================
# 文件分析子代理
# ============================================================================

def create_file_expert_subagent(
    file_tools: List[Any],
    model: str = "deepseek-chat"
) -> SubAgentConfig:
    """
    创建文件分析子代理

    专注于文件内容分析和数据提取。

    Args:
        file_tools: 文件处理工具列表
        model: 使用的模型

    Returns:
        SubAgentConfig 实例
    """
    system_prompt = """你是文件分析专家，负责：

## 核心能力
1. **读取文件**：支持 CSV, Excel, JSON, PDF 等格式
2. **数据提取**：从文件中提取结构化数据
3. **模式识别**：识别数据模式和异常值
4. **数据清洗**：处理缺失值、异常值

## 支持的文件格式
- **CSV**: 逗号分隔值文件
- **Excel**: .xlsx, .xls 格式
- **JSON**: 结构化数据
- **文本**: 日志文件、报告等

## 工作流程
1. 读取文件内容
2. 分析数据结构和类型
3. 识别关键指标和趋势
4. 提供数据质量评估

## 输出格式
返回结果应包含：
- 文件内容摘要
- 数据结构描述
- 关键发现和洞察
- 建议的后续分析
"""

    return SubAgentConfig(
        name="file_expert",
        description="文件分析专家 - 专注于文件内容分析和数据提取",
        system_prompt=system_prompt,
        tools=file_tools,
        model=model,
        temperature=0.1,
        max_iterations=3
    )


# ============================================================================
# SubAgent 管理器
# ============================================================================

class SubAgentManager:
    """
    子代理管理器

    管理所有专业化的子代理，支持动态创建和委派任务。
    """

    def __init__(self, default_model: str = "deepseek-chat"):
        """
        初始化子代理管理器

        Args:
            default_model: 默认使用的模型
        """
        self.default_model = default_model
        self._subagents: Dict[str, SubAgentConfig] = {}

    def register_subagent(self, config: SubAgentConfig):
        """
        注册子代理

        Args:
            config: 子代理配置
        """
        self._subagents[config.name] = config

    def get_subagent(self, name: str) -> Optional[SubAgentConfig]:
        """
        获取子代理配置

        Args:
            name: 子代理名称

        Returns:
            SubAgentConfig 实例，如果不存在返回 None
        """
        return self._subagents.get(name)

    def list_subagents(self) -> List[str]:
        """
        列出所有已注册的子代理

        Returns:
            子代理名称列表
        """
        return list(self._subagents.keys())

    def create_default_subagents(
        self,
        postgres_tools: Optional[List[Any]] = None,
        echarts_tools: Optional[List[Any]] = None,
        file_tools: Optional[List[Any]] = None
    ):
        """
        创建默认的子代理集

        Args:
            postgres_tools: PostgreSQL 工具
            echarts_tools: ECharts 工具
            file_tools: 文件处理工具
        """
        # SQL 专家子代理
        if postgres_tools:
            sql_agent = create_sql_expert_subagent(
                postgres_tools=postgres_tools,
                model=self.default_model
            )
            self.register_subagent(sql_agent)

        # 图表专家子代理
        if echarts_tools:
            chart_agent = create_chart_expert_subagent(
                echarts_tools=echarts_tools,
                model=self.default_model
            )
            self.register_subagent(chart_agent)

        # 文件专家子代理
        if file_tools:
            file_agent = create_file_expert_subagent(
                file_tools=file_tools,
                model=self.default_model
            )
            self.register_subagent(file_agent)


# ============================================================================
# 便捷函数
# ============================================================================

def create_subagent_manager(
    default_model: str = "deepseek-chat"
) -> SubAgentManager:
    """
    创建子代理管理器的便捷函数

    Args:
        default_model: 默认模型

    Returns:
        SubAgentManager 实例
    """
    return SubAgentManager(default_model=default_model)


# ============================================================================
# 测试代码
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SubAgent 架构测试")
    print("=" * 60)

    # 创建子代理管理器
    manager = create_subagent_manager()

    # 创建默认子代理 (模拟)
    print("\n[TEST 1] 创建默认子代理")
    sql_config = create_sql_expert_subagent(
        postgres_tools=[],  # 空列表用于测试
    )
    manager.register_subagent(sql_config)

    chart_config = create_chart_expert_subagent(
        echarts_tools=[],
    )
    manager.register_subagent(chart_config)

    print(f"[INFO] 已注册子代理: {manager.list_subagents()}")

    # 测试子代理配置
    print("\n[TEST 2] 子代理配置验证")

    for name in manager.list_subagents():
        config = manager.get_subagent(name)
        print(f"\n[{config.name}]")
        print(f"  描述: {config.description}")
        print(f"  工具数量: {len(config.tools)}")
        print(f"  温度: {config.temperature}")
        print(f"  系统提示长度: {len(config.system_prompt)} 字符")

    print("\n" + "=" * 60)
    print("[SUCCESS] SubAgent 架构测试通过")
    print("=" * 60)
