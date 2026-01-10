"""
# [TERMINAL VIZ] Rich库终端可视化模块

## [HEADER]
**文件名**: terminal_viz.py
**职责**: 使用Rich库在终端显示美观的表格和ASCII图表 - 支持表格渲染、柱状图、饼图，自动根据ChartType选择渲染方式
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - Rich终端可视化

## [INPUT]
### render_table() 函数参数
- **response: VisualizationResponse** - 结构化的可视化响应对象
  - 包含 data.columns, data.rows, data.row_count
  - 包含 chart.title

### render_bar_chart() 函数参数
- **response: VisualizationResponse** - 结构化的可视化响应对象
- **max_width: int** - 柱状图最大宽度（默认40）

### render_pie_chart() 函数参数
- **response: VisualizationResponse** - 结构化的可视化响应对象

### render_response() 函数参数
- **response: VisualizationResponse** - 完整的可视化响应对象
  - 包含 answer, sql, data, chart, success 等字段

## [OUTPUT]
### render_table() 行为
- 渲染 Rich 表格到终端
- 显示前15行数据（超过则添加省略行）
- 支持自定义标题和列样式
- 无返回值（直接打印到控制台）

### render_bar_chart() 行为
- 渲染 ASCII 柱状图到终端
- 自动缩放柱子宽度（基于最大值）
- 彩色显示（6种颜色循环）
- 无返回值（直接打印到控制台）

### render_pie_chart() 行为
- 渲染 ASCII 饼图到终端
- 显示百分比和进度条
- 使用符号和颜色区分类别
- 无返回值（直接打印到控制台）

### render_response() 行为
- 根据 chart.chart_type 自动选择渲染方式：
  - ChartType.BAR → 柱状图 + 表格
  - ChartType.PIE → 饼图 + 表格
  - ChartType.LINE / ChartType.TABLE → 仅表格
- 先显示 AI 回答面板（如有）
- 再显示 SQL 语句（截断到100字符）
- 最后根据类型渲染图表
- 无返回值（直接打印到控制台）

## [LINK]
**上游依赖** (已读取源码):
- [rich](https://rich.readthedocs.io/) - Python终端美化库（Console, Table, Panel, box）
- [./models.py](./models.py) - 数据模型（VisualizationResponse, ChartType, QueryResult, ChartConfig）

**下游依赖** (已读取源码):
- [./sql_agent.py](./sql_agent.py) - Agent主程序（导入并使用 render_response）

**调用方**:
- **sql_agent.py**: 在 run_agent() 和 interactive_mode() 中调用 render_response() 显示结果

## [POS]
**路径**: Agent/terminal_viz.py
**模块层级**: Level 1（Agent根目录）
**依赖深度**: 直接依赖 2 层（rich, 本地models模块）
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from models import VisualizationResponse, ChartType

console = Console()


def render_table(response: VisualizationResponse) -> None:
    """渲染数据表格"""
    data = response.data
    if not data.columns or not data.rows:
        console.print("[yellow]⚠️ 没有数据可显示[/yellow]")
        return
    
    table = Table(title=response.chart.title or "查询结果", box=box.ROUNDED,
                  show_header=True, header_style="bold cyan", title_style="bold magenta")
    for col in data.columns:
        table.add_column(col, style="white")
    for row in data.rows[:15]:
        table.add_row(*[str(cell) for cell in row])
    if data.row_count > 15:
        table.add_row(*["..." for _ in data.columns])
    console.print(table)
    if data.row_count > 15:
        console.print(f"[dim]（显示前15行，共{data.row_count}行）[/dim]")


def render_bar_chart(response: VisualizationResponse, max_width: int = 40) -> None:
    """渲染ASCII柱状图"""
    data, chart = response.data, response.chart
    if not data.columns or not data.rows:
        return
    x_idx, y_idx = 0, 1
    if chart.x_field and chart.x_field in data.columns:
        x_idx = data.columns.index(chart.x_field)
    if chart.y_field and chart.y_field in data.columns:
        y_idx = data.columns.index(chart.y_field)
    labels, values = [], []
    for row in data.rows:
        labels.append(str(row[x_idx]))
        try:
            values.append(float(row[y_idx]))
        except (ValueError, TypeError):
            values.append(0)
    if not values or max(values) == 0:
        return
    max_value, max_label_len = max(values), max(len(l) for l in labels)
    console.print(f"\n[bold magenta]📊 {chart.title or '柱状图'}[/bold magenta]\n")
    colors = ["green", "blue", "cyan", "yellow", "red", "magenta"]
    for i, (label, value) in enumerate(zip(labels, values)):
        bar = "█" * int((value / max_value) * max_width)
        console.print(f"  {label.rjust(max_label_len)} │[{colors[i%6]}]{bar}[/{colors[i%6]}] {value:.0f}")
    console.print()


def render_pie_chart(response: VisualizationResponse) -> None:
    """渲染ASCII饼图"""
    data, chart = response.data, response.chart
    if not data.rows:
        return
    x_idx, y_idx = 0, 1
    if chart.x_field and chart.x_field in data.columns:
        x_idx = data.columns.index(chart.x_field)
    if chart.y_field and chart.y_field in data.columns:
        y_idx = data.columns.index(chart.y_field)
    items, total = [], 0
    for row in data.rows:
        try:
            value = float(row[y_idx])
        except (ValueError, TypeError):
            value = 0
        items.append((str(row[x_idx]), value))
        total += value
    console.print(f"\n[bold magenta]🥧 {chart.title or '占比分布'}[/bold magenta]\n")
    symbols, colors = ["●", "○", "◆", "◇", "■", "□"], ["red", "green", "blue", "yellow", "cyan", "magenta"]
    for i, (label, value) in enumerate(items):
        pct = (value / total * 100) if total > 0 else 0
        console.print(f"  [{colors[i%6]}]{symbols[i%6]}[/{colors[i%6]}] {label}: {pct:.1f}% [{colors[i%6]}]{'█' * int(pct/5)}[/{colors[i%6]}]")
    console.print()


def render_response(response: VisualizationResponse) -> None:
    """根据图表类型自动选择渲染方式"""
    if response.answer:
        console.print(Panel(response.answer, title="💬 回答", border_style="green", padding=(1, 2)))
    if response.sql:
        console.print(f"\n[dim]📝 SQL: {response.sql[:100]}{'...' if len(response.sql) > 100 else ''}[/dim]")
    chart_type = response.chart.chart_type
    if chart_type == ChartType.BAR:
        render_bar_chart(response)
        render_table(response)
    elif chart_type == ChartType.PIE:
        render_pie_chart(response)
        render_table(response)
    elif chart_type in (ChartType.LINE, ChartType.TABLE):
        render_table(response)
    elif response.data.row_count > 0:
        render_table(response)


if __name__ == "__main__":
    from models import QueryResult, ChartConfig
    test_data = [
        {"category_name": "数码配件", "product_count": 5},
        {"category_name": "手机通讯", "product_count": 3},
        {"category_name": "电脑办公", "product_count": 3},
        {"category_name": "女装", "product_count": 1},
    ]
    response = VisualizationResponse(
        answer="统计结果：数码配件5个，手机通讯和电脑办公各3个。",
        sql="SELECT c.name, COUNT(p.id) FROM categories c JOIN products p GROUP BY c.name",
        data=QueryResult.from_raw_data(test_data),
        chart=ChartConfig(chart_type=ChartType.BAR, title="各分类产品数量", x_field="category_name", y_field="product_count")
    )
    console.print("\n" + "="*60 + "\n[bold]🧪 终端可视化测试[/bold]\n" + "="*60 + "\n")
    render_response(response)

