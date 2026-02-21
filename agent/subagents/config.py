from __future__ import annotations

"""Subagent configuration models and factory helpers."""

from dataclasses import dataclass
from typing import Any, List, Optional

SQL_EXPERT_PROMPT = """
You are a SQL expert.

Responsibilities:
- Convert user questions into precise SQL queries.
- Use only safe read operations (SELECT).
- Prefer efficient queries and avoid full scans where possible.
- Use schema discovery tools before writing SQL.

Hard rules:
- Never generate INSERT/UPDATE/DELETE/ALTER/DROP/CREATE.
- Always add LIMIT unless user explicitly needs full output.
- If an error occurs, diagnose and propose a corrected query.
""".strip()

CHART_EXPERT_PROMPT = """
You are a data visualization expert.

Responsibilities:
- Choose the right chart type for the data pattern.
- Produce valid ECharts configuration JSON.
- Keep charts readable with clear labels and legends.

Guidelines:
- Time series -> line chart
- Category comparison -> bar chart
- Proportion -> pie chart
- Correlation -> scatter chart
""".strip()

FILE_EXPERT_PROMPT = """
You are a file analysis specialist.

Responsibilities:
- Read and inspect CSV, Excel, JSON, text, and similar files.
- Extract structured data from uploaded files.
- Identify data quality issues and obvious anomalies.
- Summarize findings and suggest next analysis steps.
""".strip()


@dataclass
class SubAgentConfig:
    """Configuration contract for a subagent profile."""

    name: str
    description: str
    system_prompt: str
    tools: List[Any]
    model: Optional[str] = None
    temperature: float = 0.1
    max_iterations: int = 10


def _build_subagent_config(
    *,
    name: str,
    description: str,
    system_prompt: str,
    tools: List[Any],
    model: str,
    temperature: float,
    max_iterations: int,
) -> SubAgentConfig:
    return SubAgentConfig(
        name=name,
        description=description,
        system_prompt=system_prompt.strip(),
        tools=tools,
        model=model,
        temperature=temperature,
        max_iterations=max_iterations,
    )


def create_sql_expert_subagent(
    postgres_tools: List[Any],
    model: str = "deepseek-chat",
) -> SubAgentConfig:
    """Create SQL specialist subagent configuration."""
    return _build_subagent_config(
        name="sql_expert",
        description="SQL query and optimization specialist",
        system_prompt=SQL_EXPERT_PROMPT,
        tools=postgres_tools,
        model=model,
        temperature=0.1,
        max_iterations=5,
    )


def create_chart_expert_subagent(
    echarts_tools: List[Any],
    model: str = "deepseek-chat",
) -> SubAgentConfig:
    """Create chart specialist subagent configuration."""
    return _build_subagent_config(
        name="chart_expert",
        description="Data visualization specialist",
        system_prompt=CHART_EXPERT_PROMPT,
        tools=echarts_tools,
        model=model,
        temperature=0.2,
        max_iterations=3,
    )


def create_file_expert_subagent(
    file_tools: List[Any],
    model: str = "deepseek-chat",
) -> SubAgentConfig:
    """Create file analysis specialist subagent configuration."""
    return _build_subagent_config(
        name="file_expert",
        description="File content analysis specialist",
        system_prompt=FILE_EXPERT_PROMPT,
        tools=file_tools,
        model=model,
        temperature=0.1,
        max_iterations=3,
    )


__all__ = [
    "SubAgentConfig",
    "create_sql_expert_subagent",
    "create_chart_expert_subagent",
    "create_file_expert_subagent",
]
