"""
# [CHART SERVICE] ECharts 图表生成服务

## [HEADER]
**文件名**: chart_service.py
**职责**: 本地图表生成服务 - 使用 PyEcharts 模拟 MCP ECharts 服务，支持多种图表类型（柱状图、折线图、饼图、散点图、漏斗图）的生成，导出为 PNG/HTML 文件
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - 本地图表生成服务

## [INPUT]
### generate_chart() 函数参数
- **request: ChartRequest** - 图表请求对象
  - type: str - 图表类型（"bar", "line", "pie", "scatter", "funnel"）
  - data: List[List[Any]] - 二维数组数据 [[name, value], ...]
  - title: str - 图表标题
  - series_name: str - 系列名称
  - x_axis_name: Optional[str] - X轴名称（默认None）
  - y_axis_name: Optional[str] - Y轴名称（默认None）
- **output_dir: str** - 输出目录路径（默认"./charts"）

### generate_chart_simple() 函数参数
- **request: ChartRequest** - 图表请求对象（同上）
- **output_dir: str** - 输出目录路径（默认"./charts"）

## [OUTPUT]
### EChartType 枚举类
- **BAR = "bar"** - 柱状图
- **LINE = "line"** - 折线图
- **PIE = "pie"** - 饼图
- **SCATTER = "scatter"** - 散点图
- **FUNNEL = "funnel"** - 漏斗图

### ChartRequest 数据类
- **type: str** - 图表类型
- **data: List[List[Any]]** - 二维数组数据
- **title: str** - 图表标题
- **series_name: str** - 系列名称
- **x_axis_name: Optional[str]** - X轴名称
- **y_axis_name: Optional[str]** - Y轴名称

### ChartResponse 数据类
- **success: bool** - 是否成功
- **image_path: Optional[str]** - 本地文件路径（PNG/HTML）
- **image_url: Optional[str]** - 云端URL（预留，阶段2）
- **error: Optional[str]** - 错误信息

### generate_chart() 返回值
- **ChartResponse** - 图表生成响应对象
  - success=True 时包含 image_path
  - success=False 时包含 error

### generate_chart_simple() 返回值
- **ChartResponse** - 图表生成响应对象（仅生成HTML，无需selenium）

## [LINK]
**上游依赖** (已读取源码):
- [pyecharts](https://github.com/pyecharts/pyecharts) - Python ECharts 库（Bar, Line, Pie, Scatter, Funnel）
- [snapshot-selenium](https://github.com/pyecharts/snapshot-selenium) - Selenium 快照库（make_snapshot, snapshot）
- [python-os](https://docs.python.org/3/library/os.html) - 文件系统操作（os.makedirs, os.path）
- [python-dataclasses](https://docs.python.org/3/library/dataclasses.html) - 数据类装饰器（@dataclass）

**下游依赖** (已读取源码):
- [./sql_agent.py](./sql_agent.py) - Agent主程序（调用图表生成服务）
- [./data_transformer.py](./data_transformer.py) - 数据转换模块（准备 ChartRequest）

**调用方**:
- **sql_agent.py**: 在生成图表时调用 generate_chart() 或 generate_chart_simple()

## [POS]
**路径**: Agent/chart_service.py
**模块层级**: Level 1（Agent根目录）
**依赖深度**: 直接依赖 2 层（pyecharts, snapshot-selenium）
"""
import os
from typing import List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class EChartType(Enum):
    """支持的图表类型（与 mcp-echarts 一致）"""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    FUNNEL = "funnel"


@dataclass
class ChartRequest:
    """图表请求参数（与 mcp-echarts get-chart 输入一致）"""
    type: str                    # 图表类型
    data: List[List[Any]]        # 二维数组数据 [[name, value], ...]
    title: str                   # 图表标题
    series_name: str             # 系列名称
    x_axis_name: Optional[str] = None   # X轴名称
    y_axis_name: Optional[str] = None   # Y轴名称


@dataclass  
class ChartResponse:
    """图表响应（模拟 mcp-echarts 返回）"""
    success: bool
    image_path: Optional[str] = None    # 本地路径（阶段1）
    image_url: Optional[str] = None     # 云端URL（阶段2）
    error: Optional[str] = None


def generate_chart(request: ChartRequest, output_dir: str = "./charts") -> ChartResponse:
    """
    生成图表并保存为 PNG
    
    这个函数模拟了 mcp-echarts 的 get-chart 工具
    后续可以替换为真正的 MCP 调用
    """
    try:
        # 延迟导入，避免未安装时报错
        from pyecharts.charts import Bar, Line, Pie, Scatter, Funnel
        from pyecharts import options as opts
        from pyecharts.render import make_snapshot
        from snapshot_selenium import snapshot
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 解析数据
        labels = [item[0] for item in request.data]
        values = [item[1] for item in request.data]
        
        # 根据类型创建图表
        chart = None
        
        if request.type == "bar":
            chart = (
                Bar()
                .add_xaxis(labels)
                .add_yaxis(request.series_name, values)
                .set_global_opts(
                    title_opts=opts.TitleOpts(title=request.title),
                    xaxis_opts=opts.AxisOpts(name=request.x_axis_name),
                    yaxis_opts=opts.AxisOpts(name=request.y_axis_name),
                )
            )
        elif request.type == "line":
            chart = (
                Line()
                .add_xaxis(labels)
                .add_yaxis(request.series_name, values)
                .set_global_opts(
                    title_opts=opts.TitleOpts(title=request.title),
                    xaxis_opts=opts.AxisOpts(name=request.x_axis_name),
                    yaxis_opts=opts.AxisOpts(name=request.y_axis_name),
                )
            )
        elif request.type == "pie":
            chart = (
                Pie()
                .add(request.series_name, list(zip(labels, values)))
                .set_global_opts(title_opts=opts.TitleOpts(title=request.title))
                .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {d}%"))
            )
        elif request.type == "scatter":
            chart = (
                Scatter()
                .add_xaxis(labels)
                .add_yaxis(request.series_name, values)
                .set_global_opts(title_opts=opts.TitleOpts(title=request.title))
            )
        elif request.type == "funnel":
            chart = (
                Funnel()
                .add(request.series_name, list(zip(labels, values)))
                .set_global_opts(title_opts=opts.TitleOpts(title=request.title))
            )
        else:
            return ChartResponse(success=False, error=f"不支持的图表类型: {request.type}")
        
        # 生成文件名
        import time
        filename = f"chart_{request.type}_{int(time.time())}.png"
        filepath = os.path.join(output_dir, filename)
        
        # 渲染为 PNG（需要 selenium + chromedriver）
        make_snapshot(snapshot, chart.render(), filepath)
        
        return ChartResponse(success=True, image_path=filepath)
        
    except ImportError as e:
        return ChartResponse(
            success=False, 
            error=f"缺少依赖: {e}. 请运行: pip install pyecharts snapshot-selenium"
        )
    except Exception as e:
        return ChartResponse(success=False, error=str(e))


def generate_chart_simple(request: ChartRequest, output_dir: str = "./charts") -> ChartResponse:
    """
    简化版：只生成 HTML 文件（无需 selenium）
    适合快速测试
    """
    try:
        from pyecharts.charts import Bar, Line, Pie
        from pyecharts import options as opts
        
        os.makedirs(output_dir, exist_ok=True)
        
        labels = [item[0] for item in request.data]
        values = [item[1] for item in request.data]
        
        if request.type == "bar":
            chart = Bar()
            chart.add_xaxis(labels)
            chart.add_yaxis(request.series_name, values)
        elif request.type == "line":
            chart = Line()
            chart.add_xaxis(labels)
            chart.add_yaxis(request.series_name, values)
        elif request.type == "pie":
            chart = Pie()
            chart.add(request.series_name, list(zip(labels, values)))
        else:
            return ChartResponse(success=False, error=f"不支持的图表类型: {request.type}")
        
        chart.set_global_opts(title_opts=opts.TitleOpts(title=request.title))
        
        import time
        filename = f"chart_{request.type}_{int(time.time())}.html"
        filepath = os.path.join(output_dir, filename)
        chart.render(filepath)
        
        return ChartResponse(success=True, image_path=filepath)
        
    except ImportError:
        return ChartResponse(success=False, error="请安装 pyecharts: pip install pyecharts")
    except Exception as e:
        return ChartResponse(success=False, error=str(e))

