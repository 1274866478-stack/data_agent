"""
测试图表生成功能的脚本
模拟前端请求，测试后端是否能正确生成并返回图表图片
"""
import requests
import json
import sys

# API 配置
API_BASE_URL = "http://localhost:8004/api/v1"

def test_chart_generation():
    """测试图表生成功能"""
    print("=" * 60)
    print("测试图表生成功能")
    print("=" * 60)
    
    # 测试查询（要求生成图表）
    test_query = {
        "query": "查询订单表，按月份统计销售额，并生成趋势图表",
        "connection_id": None,  # 让后端自动选择数据源
        "enable_cache": False,
        "force_refresh": True
    }
    
    print(f"\n发送测试请求:")
    print(f"  查询: {test_query['query']}")
    print(f"  URL: {API_BASE_URL}/query")
    
    try:
        # 发送请求
        response = requests.post(
            f"{API_BASE_URL}/query",
            json=test_query,
            headers={"Content-Type": "application/json"},
            timeout=120  # 图表生成可能需要较长时间
        )
        
        print(f"\n响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # 检查响应结构
            print("\n响应结构:")
            print(f"  - 状态: {data.get('status', 'unknown')}")
            
            # 检查是否有图表数据
            if 'data' in data:
                response_data = data['data']
                
                # 检查多种可能的响应格式
                chart_found = False
                chart_image = None
                
                # 格式1: 直接包含 chart 字段
                if 'chart' in response_data:
                    chart = response_data['chart']
                    if isinstance(chart, dict):
                        chart_image = chart.get('chart_image') or chart.get('chart_data')
                        if chart_image:
                            chart_found = True
                            print(f"\n✓ 找到图表数据 (格式1: chart.chart_image)")
                            print(f"  图表类型: {chart.get('chart_type', 'unknown')}")
                            print(f"  图片数据长度: {len(chart_image) if isinstance(chart_image, str) else 'N/A'}")
                            print(f"  图片数据预览: {chart_image[:100] if isinstance(chart_image, str) else 'N/A'}...")
                
                # 格式2: execution_result 中包含 chart_data
                if not chart_found and 'execution_result' in response_data:
                    exec_result = response_data['execution_result']
                    if isinstance(exec_result, dict):
                        chart_image = exec_result.get('chart_data')
                        if chart_image:
                            chart_found = True
                            print(f"\n✓ 找到图表数据 (格式2: execution_result.chart_data)")
                            print(f"  图片数据长度: {len(chart_image) if isinstance(chart_image, str) else 'N/A'}")
                            print(f"  图片数据预览: {chart_image[:100] if isinstance(chart_image, str) else 'N/A'}...")
                
                # 格式3: nested.chart.chart_image
                if not chart_found and 'nested' in response_data:
                    nested = response_data['nested']
                    if isinstance(nested, dict) and 'chart' in nested:
                        chart = nested['chart']
                        if isinstance(chart, dict):
                            chart_image = chart.get('chart_image')
                            if chart_image:
                                chart_found = True
                                print(f"\n✓ 找到图表数据 (格式3: nested.chart.chart_image)")
                                print(f"  图片数据长度: {len(chart_image) if isinstance(chart_image, str) else 'N/A'}")
                                print(f"  图片数据预览: {chart_image[:100] if isinstance(chart_image, str) else 'N/A'}...")
                
                if chart_found:
                    print("\n" + "=" * 60)
                    print("✓ 测试成功：图表数据已生成并返回！")
                    print("=" * 60)
                    
                    # 验证图片格式
                    if isinstance(chart_image, str):
                        if chart_image.startswith('data:image'):
                            print("✓ 图片格式正确：Base64 data URI")
                        elif chart_image.startswith('http://') or chart_image.startswith('https://'):
                            print("✓ 图片格式正确：HTTP URL")
                        else:
                            print("⚠ 图片格式未知，可能需要检查")
                    
                    return True
                else:
                    print("\n" + "=" * 60)
                    print("✗ 测试失败：响应中未找到图表数据")
                    print("=" * 60)
                    print("\n响应数据预览:")
                    print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
                    return False
            else:
                print("\n响应数据中没有 'data' 字段")
                print(f"完整响应: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                return False
        else:
            print(f"\n请求失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n✗ 请求超时（图表生成可能需要更长时间）")
        return False
    except requests.exceptions.ConnectionError:
        print(f"\n✗ 无法连接到后端服务: {API_BASE_URL}")
        print("请确保后端服务正在运行")
        return False
    except Exception as e:
        print(f"\n✗ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chart_generation()
    sys.exit(0 if success else 1)

