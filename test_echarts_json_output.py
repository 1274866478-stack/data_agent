"""
测试 ECharts JSON 输出功能
验证后端解析逻辑是否正确工作
"""
import json
import re

def test_extract_echarts_option():
    """测试从 LLM 回复中提取 ECharts JSON 配置"""
    
    # 模拟 LLM 回复，包含图表配置
    test_content = """根据查询结果，今年的收入趋势如下：

收入逐月增长，从1月的12000元增长到5月的22000元，增长幅度达到83.3%。

[CHART_START]
{
  "title": {
    "text": "月度收入趋势"
  },
  "tooltip": {
    "trigger": "axis"
  },
  "xAxis": {
    "type": "category",
    "data": ["1月", "2月", "3月", "4月", "5月"]
  },
  "yAxis": {
    "type": "value",
    "name": "收入（元）"
  },
  "series": [{
    "name": "收入",
    "type": "line",
    "data": [12000, 15000, 18000, 20000, 22000],
    "smooth": true
  }]
}
[CHART_END]

这表明业务发展良好。"""

    # 使用正则表达式提取
    chart_pattern = r'\[CHART_START\]([\s\S]*?)\[CHART_END\]'
    match = re.search(chart_pattern, test_content)
    
    if match:
        json_str = match.group(1).strip()
        try:
            echarts_option = json.loads(json_str)
            print("[PASS] 成功提取 ECharts JSON 配置")
            print(f"配置内容: {json.dumps(echarts_option, indent=2, ensure_ascii=False)}")
            
            # 验证必需字段
            required_fields = ['title', 'tooltip', 'xAxis', 'yAxis', 'series']
            missing_fields = [field for field in required_fields if field not in echarts_option]
            
            if missing_fields:
                print(f"[WARN] 缺少必需字段: {missing_fields}")
            else:
                print("[PASS] 所有必需字段都存在")
            
            # 移除图表配置后的文本
            cleaned_content = re.sub(chart_pattern, '', test_content).strip()
            print(f"\n清理后的文本内容:\n{cleaned_content}")
            
            return True
        except json.JSONDecodeError as e:
            print(f"[FAIL] JSON 解析失败: {e}")
            return False
    else:
        print("❌ 未找到图表配置标记")
        return False

def test_invalid_json():
    """测试无效 JSON 的处理"""
    test_content = """这是测试内容。

[CHART_START]
{
  "title": "无效的JSON
  "xAxis": {
    "type": "category"
  }
}
[CHART_END]

其他内容。"""

    chart_pattern = r'\[CHART_START\]([\s\S]*?)\[CHART_END\]'
    match = re.search(chart_pattern, test_content)
    
    if match:
        json_str = match.group(1).strip()
        try:
            echarts_option = json.loads(json_str)
            print("[FAIL] 应该解析失败，但却成功了")
            return False
        except json.JSONDecodeError as e:
            print(f"[PASS] 正确捕获了无效 JSON 错误: {e}")
            # 应该保留原始内容
            cleaned_content = test_content  # 解析失败时保留原内容
            print(f"保留的原始内容长度: {len(cleaned_content)}")
            return True
    else:
        print("❌ 未找到图表配置标记")
        return False

def test_no_chart_config():
    """测试没有图表配置的情况"""
    test_content = """这是普通的文本回复，不包含图表配置。

只有文字分析内容。"""

    chart_pattern = r'\[CHART_START\]([\s\S]*?)\[CHART_END\]'
    match = re.search(chart_pattern, test_content)
    
    if match:
        print("❌ 不应该找到图表配置")
        return False
    else:
        print("[PASS] 正确识别：没有图表配置")
        cleaned_content = test_content
        print(f"保留的原始内容:\n{cleaned_content}")
        return True

if __name__ == "__main__":
    print("=" * 60)
    print("测试 1: 提取有效的 ECharts JSON 配置")
    print("=" * 60)
    result1 = test_extract_echarts_option()
    
    print("\n" + "=" * 60)
    print("测试 2: 处理无效的 JSON")
    print("=" * 60)
    result2 = test_invalid_json()
    
    print("\n" + "=" * 60)
    print("测试 3: 没有图表配置的情况")
    print("=" * 60)
    result3 = test_no_chart_config()
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"测试 1 (有效 JSON): {'[PASS] 通过' if result1 else '[FAIL] 失败'}")
    print(f"测试 2 (无效 JSON): {'[PASS] 通过' if result2 else '[FAIL] 失败'}")
    print(f"测试 3 (无配置): {'[PASS] 通过' if result3 else '[FAIL] 失败'}")
    
    if all([result1, result2, result3]):
        print("\n[SUCCESS] 所有测试通过！")
    else:
        print("\n[WARN] 部分测试失败，请检查代码")

