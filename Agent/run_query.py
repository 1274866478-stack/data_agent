"""
直接运行查询并生成可视化图片
不需要终端交互，直接在代码里写好问题
"""
import asyncio
import matplotlib.pyplot as plt
import matplotlib
from sql_agent import run_agent

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False


def save_chart(result, filename="output.png"):
    """根据查询结果生成并保存图片"""
    
    if not result.success:
        print(f"❌ 查询失败: {result.error}")
        return False
    
    data = result.data
    chart = result.chart
    
    if data.row_count == 0:
        print("⚠️ 没有数据可以可视化")
        return False
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 根据图表类型生成不同的图
    chart_type = chart.chart_type.value
    
    if chart_type == "bar" and chart.x_field and chart.y_field:
        # 柱状图
        x_idx = data.columns.index(chart.x_field) if chart.x_field in data.columns else 0
        y_idx = data.columns.index(chart.y_field) if chart.y_field in data.columns else 1
        
        x_values = [str(row[x_idx]) for row in data.rows]
        y_values = [float(row[y_idx]) for row in data.rows]
        
        bars = ax.bar(x_values, y_values, color='steelblue')
        ax.set_xlabel(chart.x_field)
        ax.set_ylabel(chart.y_field)
        
        # 在柱子上显示数值
        for bar, val in zip(bars, y_values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                   f'{val:.0f}', ha='center', va='bottom', fontsize=10)
    
    elif chart_type == "pie" and len(data.columns) >= 2:
        # 饼图
        labels = [str(row[0]) for row in data.rows]
        values = [float(row[1]) for row in data.rows]
        
        ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
    
    elif chart_type == "line" and chart.x_field and chart.y_field:
        # 折线图
        x_idx = data.columns.index(chart.x_field) if chart.x_field in data.columns else 0
        y_idx = data.columns.index(chart.y_field) if chart.y_field in data.columns else 1
        
        x_values = [str(row[x_idx]) for row in data.rows]
        y_values = [float(row[y_idx]) for row in data.rows]
        
        ax.plot(x_values, y_values, marker='o', linewidth=2, markersize=8)
        ax.set_xlabel(chart.x_field)
        ax.set_ylabel(chart.y_field)
    
    else:
        # 默认：表格形式显示
        ax.axis('off')
        table = ax.table(
            cellText=data.rows[:20],  # 最多显示20行
            colLabels=data.columns,
            cellLoc='center',
            loc='center'
        )
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.5)
    
    # 设置标题
    title = chart.title or "查询结果"
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    # 保存图片
    plt.tight_layout()
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"✅ 图片已保存: {filename}")
    return True


async def main():
    # ============================================
    # 👇 在这里修改你的问题
    # ============================================
    question = "各分类的产品平均价格是多少"
    
    print(f"🔍 正在查询: {question}")
    print("-" * 50)
    
    # 运行Agent
    result = await run_agent(question, verbose=False)
    
    # 显示结果摘要
    print(f"📊 SQL: {result.sql}")
    print(f"📈 数据行数: {result.data.row_count}")
    print(f"💬 回答: {result.answer[:100]}..." if len(result.answer) > 100 else f"💬 回答: {result.answer}")
    print("-" * 50)
    
    # 保存图片
    save_chart(result, "output.png")


if __name__ == "__main__":
    asyncio.run(main())

