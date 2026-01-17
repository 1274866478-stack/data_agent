"""
测试图表配置提取修复
运行方式: python test_chart_fix.py
"""

import re
import json

def extract_chart_config_from_answer(answer: str):
    """从 AI 回答中提取图表配置 JSON"""
    if not answer or not answer.strip():
        return None

    # 策略0 (最高优先级): 尝试匹配 [CHART_START]...[CHART_END] 格式
    chart_marker_pattern = r'\[CHART_START\]([\s\S]*?)\[CHART_END\]'
    marker_match = re.search(chart_marker_pattern, answer)
    if marker_match:
        json_str = marker_match.group(1).strip()
        try:
            parsed = json.loads(json_str)
            if any(key in parsed for key in ['series', 'xAxis', 'yAxis', 'title', 'legend', 'grid', 'tooltip']):
                print(f"✅ 成功从 [CHART_START]...[CHART_END] 格式提取 ECharts 配置")
                return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")

    return None


# 测试用例 - 模拟 AI 返回的销售趋势数据
test_answer = """
根据2023年月度销售数据分析：

📊 **销售趋势概述**：
- 全年销售额呈上升趋势
- 最高销售额出现在12月：¥2,345,678
- 最低销售额出现在2月：¥890,123

[CHART_START]
{
    "title": {"text": "2023年月度销售趋势"},
    "tooltip": {"trigger": "axis"},
    "legend": {"data": ["销售额"]},
    "xAxis": {"type": "category", "data": ["2023-01", "2023-02", "2023-03", "2023-04", "2023-05", "2023-06", "2023-07", "2023-08", "2023-09", "2023-10", "2023-11", "2023-12"]},
    "yAxis": {"type": "value", "name": "销售额(元)"},
    "series": [{"name": "销售额", "type": "line", "data": [1234567, 890123, 1567890, 1678900, 1789012, 1890123, 1901234, 2012345, 2123456, 2234567, 2345678, 2456789]}]
}
[CHART_END]

💡 **数据洞察**：全年销售额持续增长，年度复合增长率约8.5%。
"""

print("=" * 60)
print("测试图表配置提取函数")
print("=" * 60)
print()

result = extract_chart_config_from_answer(test_answer)

if result:
    print(f"\n📊 提取到的图表配置：")
    print(result[:500] + "..." if len(result) > 500 else result)
    print("\n✅ 测试通过！图表配置提取函数工作正常。")
else:
    print("\n❌ 测试失败！未能提取图表配置。")
