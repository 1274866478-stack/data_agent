#!/usr/bin/env python3
"""
Agent 集成验证脚本
依次验证集成是否正常工作
"""
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "Agent"))

def print_step(step_num, description):
    """打印验证步骤"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {description}")
    print(f"{'='*60}")

def verify_step_1():
    """验证 1: 检查导入和依赖"""
    print_step(1, "检查导入和依赖")
    
    try:
        # 检查 Agent 服务模块
        from backend.src.app.services.agent_service import is_agent_available
        available = is_agent_available()
        print(f"✅ Agent 服务模块导入成功")
        print(f"   Agent 可用性: {available}")
        
        if available:
            # 尝试导入 Agent 核心模块
            from sql_agent import run_agent
            from models import VisualizationResponse
            from config import config
            print(f"✅ Agent 核心模块导入成功")
            print(f"   - sql_agent.run_agent: {run_agent}")
            print(f"   - models.VisualizationResponse: {VisualizationResponse}")
            print(f"   - config.config: {config}")
            return True
        else:
            print(f"⚠️  Agent 模块不可用（可能是依赖未安装）")
            return False
            
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_step_2():
    """验证 2: 检查依赖安装"""
    print_step(2, "检查依赖安装")
    
    required_packages = [
        'langgraph',
        'langchain',
        'langchain_openai',
        'langchain_community',
        'langchain_mcp_adapters',
        'mcp',
        'pyecharts',
        'rich'
    ]
    
    missing = []
    installed = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            installed.append(package)
            print(f"✅ {package}: 已安装")
        except ImportError:
            missing.append(package)
            print(f"❌ {package}: 未安装")
    
    if missing:
        print(f"\n⚠️  缺少以下依赖包: {', '.join(missing)}")
        print(f"   请运行: pip install {' '.join(missing)}")
        return False
    else:
        print(f"\n✅ 所有依赖包已安装")
        return True

def verify_step_3():
    """验证 3: 检查配置"""
    print_step(3, "检查配置")
    
    try:
        # 检查后端配置
        from backend.src.app.core.config import get_settings
        settings = get_settings()
        
        print(f"✅ 后端配置加载成功")
        
        # 检查 DeepSeek 配置
        has_deepseek = hasattr(settings, 'deepseek_api_key')
        print(f"   DeepSeek 配置存在: {has_deepseek}")
        
        if has_deepseek:
            api_key = getattr(settings, 'deepseek_api_key', None)
            base_url = getattr(settings, 'deepseek_base_url', 'N/A')
            model = getattr(settings, 'deepseek_default_model', 'N/A')
            
            print(f"   DeepSeek API Key: {'已设置' if api_key else '未设置'}")
            print(f"   DeepSeek Base URL: {base_url}")
            print(f"   DeepSeek Model: {model}")
        
        # 检查 Agent 配置
        from config import config as agent_config
        print(f"\n✅ Agent 配置加载成功")
        print(f"   DeepSeek API Key: {'已设置' if agent_config.deepseek_api_key else '未设置'}")
        print(f"   Database URL: {'已设置' if agent_config.database_url else '未设置'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_step_4():
    """验证 4: 检查 LLM 服务"""
    print_step(4, "检查 LLM 服务")
    
    try:
        from backend.src.app.services.llm_service import LLMService, LLMProvider
        
        # 检查 DeepSeek Provider 是否存在
        providers = [p.value for p in LLMProvider]
        print(f"✅ LLM 服务加载成功")
        print(f"   可用提供商: {', '.join(providers)}")
        
        if 'deepseek' in providers:
            print(f"✅ DeepSeek 提供商已注册")
        else:
            print(f"❌ DeepSeek 提供商未注册")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ LLM 服务检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_step_5():
    """验证 5: 检查 API 端点"""
    print_step(5, "检查 API 端点")
    
    try:
        from backend.src.app.api.v1.endpoints.query import router
        
        print(f"✅ Query API 端点加载成功")
        
        # 检查路由
        routes = [route.path for route in router.routes]
        if '/query' in routes or any('/query' in r for r in routes):
            print(f"✅ /query 端点已注册")
        else:
            print(f"⚠️  /query 端点未找到")
        
        return True
        
    except Exception as e:
        print(f"❌ API 端点检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主验证流程"""
    print("\n" + "="*60)
    print("Agent 集成验证脚本")
    print("="*60)
    
    results = []
    
    # 依次执行验证
    results.append(("导入和依赖", verify_step_1()))
    results.append(("依赖安装", verify_step_2()))
    results.append(("配置检查", verify_step_3()))
    results.append(("LLM 服务", verify_step_4()))
    results.append(("API 端点", verify_step_5()))
    
    # 汇总结果
    print(f"\n{'='*60}")
    print("验证结果汇总")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计: {passed}/{total} 项验证通过")
    
    if passed == total:
        print("\n🎉 所有验证通过！集成成功！")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 项验证失败，请检查上述错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())

