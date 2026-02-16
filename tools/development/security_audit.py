#!/usr/bin/env python3
"""
安全状态评估脚本
评估当前密钥强度和安全配置
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


def check_key_strength(key: str, key_name: str) -> Tuple[str, List[str]]:
    """检查密钥强度"""
    issues = []
    
    if not key:
        return "CRITICAL", [f"{key_name} 未设置"]
    
    # 检查长度
    if len(key) < 16:
        issues.append(f"{key_name} 长度不足16位 (当前: {len(key)})")
    elif len(key) < 32:
        issues.append(f"{key_name} 长度建议至少32位 (当前: {len(key)})")
    
    # 检查常见弱密码
    weak_passwords = [
        "password", "admin", "123456", "test", "demo", "default",
        "minioadmin", "changeme", "secret", "your-", "placeholder"
    ]
    
    key_lower = key.lower()
    for weak in weak_passwords:
        if weak in key_lower:
            issues.append(f"{key_name} 包含常见弱密码模式: '{weak}'")
    
    # 检查复杂度
    has_upper = bool(re.search(r'[A-Z]', key))
    has_lower = bool(re.search(r'[a-z]', key))
    has_digit = bool(re.search(r'\d', key))
    has_special = bool(re.search(r'[^A-Za-z0-9]', key))
    
    complexity_score = sum([has_upper, has_lower, has_digit, has_special])
    
    if complexity_score < 2:
        issues.append(f"{key_name} 复杂度不足 (建议包含大小写字母、数字、特殊字符)")
    
    # 评级
    if issues:
        if any("CRITICAL" in str(i) or "未设置" in str(i) for i in issues):
            return "CRITICAL", issues
        elif len(issues) >= 3:
            return "WEAK", issues
        else:
            return "MODERATE", issues
    else:
        return "STRONG", []


def audit_env_file(env_path: str = ".env") -> Dict:
    """审计.env文件"""
    
    if not os.path.exists(env_path):
        return {
            "status": "ERROR",
            "message": f"{env_path} 文件不存在",
            "keys": {}
        }
    
    # 读取环境变量
    env_vars = {}
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    # 检查关键密钥
    critical_keys = {
        "ZHIPUAI_API_KEY": env_vars.get("ZHIPUAI_API_KEY", ""),
        "SECRET_KEY": env_vars.get("SECRET_KEY", ""),
        "MINIO_ACCESS_KEY": env_vars.get("MINIO_ACCESS_KEY", ""),
        "MINIO_SECRET_KEY": env_vars.get("MINIO_SECRET_KEY", ""),
    }
    
    results = {}
    overall_status = "STRONG"
    
    for key_name, key_value in critical_keys.items():
        strength, issues = check_key_strength(key_value, key_name)
        results[key_name] = {
            "strength": strength,
            "length": len(key_value) if key_value else 0,
            "issues": issues
        }
        
        # 更新整体状态
        if strength == "CRITICAL":
            overall_status = "CRITICAL"
        elif strength == "WEAK" and overall_status != "CRITICAL":
            overall_status = "WEAK"
        elif strength == "MODERATE" and overall_status == "STRONG":
            overall_status = "MODERATE"
    
    return {
        "status": overall_status,
        "keys": results,
        "total_keys_checked": len(critical_keys),
        "critical_issues": sum(1 for r in results.values() if r["strength"] == "CRITICAL"),
        "weak_issues": sum(1 for r in results.values() if r["strength"] == "WEAK")
    }


def print_audit_report(audit_result: Dict):
    """打印审计报告"""
    print("\n" + "="*70)
    print("🔒 安全状态评估报告")
    print("="*70)
    
    status = audit_result["status"]
    status_emoji = {
        "STRONG": "✅",
        "MODERATE": "⚠️",
        "WEAK": "❌",
        "CRITICAL": "🚨",
        "ERROR": "❌"
    }
    
    print(f"\n整体安全状态: {status_emoji.get(status, '❓')} {status}")
    print(f"检查密钥数量: {audit_result.get('total_keys_checked', 0)}")
    print(f"严重问题: {audit_result.get('critical_issues', 0)}")
    print(f"弱密钥: {audit_result.get('weak_issues', 0)}")
    
    print("\n" + "-"*70)
    print("密钥详情:")
    print("-"*70)
    
    for key_name, details in audit_result.get("keys", {}).items():
        strength = details["strength"]
        length = details["length"]
        issues = details["issues"]
        
        print(f"\n📌 {key_name}")
        print(f"   强度: {status_emoji.get(strength, '❓')} {strength}")
        print(f"   长度: {length} 字符")
        
        if issues:
            print(f"   问题:")
            for issue in issues:
                print(f"      - {issue}")
    
    print("\n" + "="*70)
    
    # 建议
    if status in ["WEAK", "CRITICAL"]:
        print("\n⚠️  建议立即执行:")
        print("   1. 运行 python scripts/generate_keys.py 生成强密钥")
        print("   2. 更新 .env 文件中的弱密钥")
        print("   3. 重启所有服务")
    elif status == "MODERATE":
        print("\n💡 建议:")
        print("   考虑增强密钥复杂度以提高安全性")
    else:
        print("\n✅ 密钥配置良好！")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    result = audit_env_file(".env")
    print_audit_report(result)

