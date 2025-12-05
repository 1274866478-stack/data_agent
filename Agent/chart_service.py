"""
本地图表生成服务 - 模拟 mcp-echarts 的 get-chart 功能
使用 pyecharts 在本地生成图表，保存为 PNG 文件

后续可以替换为真正的 MCP 服务器调用
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

