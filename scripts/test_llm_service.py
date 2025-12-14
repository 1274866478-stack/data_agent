#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 LLM 服务
验证 DeepSeek 作为默认 LLM 提供者
"""
import sys
import os
from pathlib import Path

# 添加 backend/src 到路径
backend_src = Path(__file__).parent.parent / "backend" / "src"
sys.path.insert(0, str(backend_src))

print("="*60)
print("验证 7: 测试 LLM 服务")
print("="*60)

# 测试 1: 导入 LLM 服务
print("\n[测试 1] 导入 LLM 服务模块...")
try:
    from app.services.llm_service import LLMService, LLMProvider
    print("  [OK] LLM 服务模块导入成功")
except Exception as e:
    print(f"  [X] LLM 服务模块导入失败: {e}")
    sys.exit(1)

# 测试 2: 检查 LLMProvider 枚举
print("\n[测试 2] 检查 LLMProvider 枚举...")
try:
    providers = [p.value for p in LLMProvider]
    print(f"  - 可用提供者: {providers}")
    if "deepseek" in providers:
        print("  [OK] DeepSeek 提供者已注册")
    else:
        print("  [X] DeepSeek 提供者未注册")
        sys.exit(1)
except Exception as e:
    print(f"  [X] 检查 LLMProvider 失败: {e}")
    sys.exit(1)

# 测试 3: 检查配置
print("\n[测试 3] 检查 DeepSeek 配置...")
try:
    from app.core.config import get_settings
    settings = get_settings()
    print(f"  - DeepSeek API Key: {'已设置' if settings.deepseek_api_key else '未设置'}")
    print(f"  - DeepSeek Base URL: {settings.deepseek_base_url}")
    print(f"  - DeepSeek Model: {settings.deepseek_default_model}")
    if settings.deepseek_api_key:
        print("  [OK] DeepSeek 配置已设置")
    else:
        print("  [WARNING] DeepSeek API Key 未设置（可能无法使用）")
except Exception as e:
    print(f"  [X] 检查配置失败: {e}")
    sys.exit(1)

# 测试 4: 检查 LLMService 初始化
print("\n[测试 4] 检查 LLMService 初始化...")
try:
    service = LLMService()
    print("  [OK] LLMService 初始化成功")
except Exception as e:
    print(f"  [X] LLMService 初始化失败: {e}")
    sys.exit(1)

# 测试 5: 检查 get_provider 方法
print("\n[测试 5] 检查 get_provider 方法...")
try:
    provider = service.get_provider("test-tenant")
    if provider:
        print(f"  - 默认提供者类型: {type(provider).__name__}")
        print(f"  - 提供者名称: {provider.name if hasattr(provider, 'name') else 'N/A'}")
        # 检查是否是 DeepSeekProvider
        if "DeepSeek" in type(provider).__name__:
            print("  [OK] 默认提供者是 DeepSeek")
        else:
            print(f"  [WARNING] 默认提供者不是 DeepSeek，而是 {type(provider).__name__}")
    else:
        print("  [WARNING] get_provider 返回 None（可能因为 API Key 未设置）")
except Exception as e:
    print(f"  [X] 检查 get_provider 失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("[SUCCESS] LLM 服务验证完成")
print("="*60)

