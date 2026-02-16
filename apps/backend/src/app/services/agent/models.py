"""
# Agent 数据模型 - 数据可视化与结构化响应

## [HEADER]
**文件名**: models.py
**职责**: 定义Agent输出的结构化数据模型，用于终端和Web双重可视化
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本，定义Pydantic模型

## [INPUT]
- SQL查询结果: List[Dict[str, Any]] - 原始数据库查询返回
- 图表类型: str/ChartType - 图表可视化类型
- 元数据: Dict[str, Any] - 附加元信息

## [OUTPUT]
- VisualizationResponse: 完整的可视化响应对象
- QueryResult: 结构化查询结果
- ChartConfig: 图表配置对象
- ECharts JSON配置: 前端ECharts库所需的配置字典

## [LINK]
**上游依赖**:
- [pydantic](https://docs.pydantic.dev/) - 数据验证和序列化

**下游依赖**:
- [data_transformer.py](data_transformer.py) - 数据转换逻辑
- [response_formatter.py](response_formatter.py) - API响应格式化

**调用方**:
- agent_service.py - Agent服务编排
- response_formatter.py - 响应格式化

## [POS]
**路径**: backend/src/app/services/agent/models.py
**模块层级**: Level 3 (Services → Agent → Models)
**依赖深度**: 2 层
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChartType(str, Enum):
    """图表类型枚举"""
    TABLE = "table"           # 表格（默认）
    BAR = "bar"               # 柱状图
    LINE = "line"             # 折线图
    PIE = "pie"               # 饼图
    SCATTER = "scatter"       # 散点图
    AREA = "area"             # 面积图
    NONE = "none"             # 不需要图表


class QueryResult(BaseModel):
    """SQL查询结果"""
    columns: List[str] = Field(default_factory=list, description="列名列表")
    rows: List[List[Any]] = Field(default_factory=list, description="数据行")
    row_count: int = Field(default=0, description="行数")
    
    @classmethod
    def from_raw_data(cls, raw_data: List[Dict[str, Any]]) -> "QueryResult":
        """从原始查询结果构建QueryResult
        
        Args:
            raw_data: MCP返回的原始数据，如 [{"name": "张三", "age": 25}, ...]
        """
        if not raw_data:
            return cls(columns=[], rows=[], row_count=0)
        
        columns = list(raw_data[0].keys())
        rows = [[row.get(col) for col in columns] for row in raw_data]
        return cls(columns=columns, rows=rows, row_count=len(rows))


class ChartConfig(BaseModel):
    """图表配置"""
    chart_type: ChartType = Field(default=ChartType.TABLE, description="图表类型")
    title: str = Field(default="", description="图表标题")
    x_field: Optional[str] = Field(default=None, description="X轴字段名")
    y_field: Optional[str] = Field(default=None, description="Y轴字段名")
    color_field: Optional[str] = Field(default=None, description="颜色分组字段")
    chart_image: Optional[str] = Field(default=None, description="图表图片（Base64 data URI 或 HTTP URL）")


class VisualizationResponse(BaseModel):
    """完整的可视化响应"""
    # 文本回答
    answer: str = Field(default="", description="LLM的文字回答")
    
    # 查询信息
    sql: str = Field(default="", description="执行的SQL语句")
    
    # 结构化数据
    data: QueryResult = Field(default_factory=QueryResult, description="查询结果数据")
    
    # 图表配置
    chart: ChartConfig = Field(default_factory=ChartConfig, description="图表配置")
    
    # ECharts 配置（可选）
    echarts_option: Optional[Dict[str, Any]] = Field(default=None, description="ECharts 配置选项")
    
    # 元信息
    success: bool = Field(default=True, description="是否成功")
    error: Optional[str] = Field(default=None, description="错误信息")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据（包含幻觉检测信息等）")


# 占位符类型定义（如果其他地方需要）
class AgentRequest(BaseModel):
    """Agent请求参数"""
    question: str
    database_url: Optional[str] = None
    thread_id: str = "default"
    enable_echarts: bool = False


class EChartsOption(BaseModel):
    """ECharts配置选项"""
    option: Dict[str, Any] = Field(default_factory=dict)


