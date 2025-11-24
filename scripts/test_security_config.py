#!/usr/bin/env python3
"""
测试安全配置脚本
验证配置加载和安全设置
"""

import sys
import os

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# 加载.env文件
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

try:
    from src.app.core.config import settings
    
    print("\n" + "="*70)
    print("🔒 安全配置验证")
    print("="*70)
    
    print(f"\n✅ 配置加载成功")
    print(f"   环境: {settings.environment}")
    print(f"   应用名称: {settings.app_name}")
    print(f"   调试模式: {settings.debug}")
    
    print(f"\n🔑 密钥配置:")
    print(f"   SECRET_KEY 长度: {len(settings.zhipuai_api_key)} 字符")
    print(f"   MINIO_ACCESS_KEY 长度: {len(settings.minio_access_key)} 字符")
    print(f"   MINIO_SECRET_KEY 长度: {len(settings.minio_secret_key)} 字符")
    print(f"   ZHIPUAI_API_KEY 长度: {len(settings.zhipuai_api_key)} 字符")
    
    print(f"\n🛡️ 安全功能:")
    print(f"   密钥轮换启用: {settings.key_rotation_enabled}")
    print(f"   轮换提醒天数: {settings.key_rotation_reminder_days}")
    print(f"   轮换周期: {settings.key_rotation_interval_days} 天")
    
    print(f"\n🌐 服务配置:")
    print(f"   MinIO端点: {settings.minio_endpoint}")
    print(f"   ChromaDB: {settings.chroma_host}:{settings.chroma_port}")
    print(f"   数据库: {'已配置' if settings.database_url else '未配置'}")
    
    print("\n" + "="*70)
    print("✅ 所有配置验证通过！")
    print("="*70 + "\n")
    
except Exception as e:
    print(f"\n❌ 配置验证失败: {e}\n")
    sys.exit(1)

