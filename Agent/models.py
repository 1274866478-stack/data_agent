"""
数据可视化模型定义
定义Agent输出的结构化数据格式，用于终端和Web双重可视化
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
    
    # 元信息
    success: bool = Field(default=True, description="是否成功")
    error: Optional[str] = Field(default=None, description="错误信息")


# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 示例：模拟一个查询结果
    raw_data = [
        {"department": "销售部", "count": 45},
        {"department": "技术部", "count": 62},
        {"department": "市场部", "count": 23},
    ]
    
    # 构建结构化响应
    response = VisualizationResponse(
        answer="各部门员工数量统计如下：销售部45人，技术部62人，市场部23人。",
        sql="SELECT department, COUNT(*) as count FROM employees GROUP BY department",
        data=QueryResult.from_raw_data(raw_data),
        chart=ChartConfig(
            chart_type=ChartType.BAR,
            title="各部门员工分布",
            x_field="department",
            y_field="count"
        )
    )
    
    # 打印JSON格式
    print("=" * 60)
    print("📊 结构化数据示例")
    print("=" * 60)
    print(response.model_dump_json(indent=2, ensure_ascii=False))

