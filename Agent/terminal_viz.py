"""
终端可视化模块 - 使用Rich库在终端显示漂亮的表格和ASCII图表
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

