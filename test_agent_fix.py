#!/usr/bin/env python3
"""
测试脚本：验证Agent修复是否生效
1. 检查文件是否存在
2. 模拟查询请求（可选）
3. 查看日志中的后处理检查记录
"""

import subprocess
import sys

def run_command(cmd):
    """执行命令并返回输出"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def main():
    print("=" * 60)
    print("测试 Agent 修复是否生效")
    print("=" * 60)
    
    # 1. 检查文件是否存在
    print("\n[1/3] 检查文件是否存在...")
    stdout, stderr, code = run_command(
        'docker exec dataagent-backend test -f "/app/uploads/data-sources/default_tenant/c5e67f91-face-4cc7-96b0-7e43fed982f0.xlsx" && echo "文件存在" || echo "文件不存在"'
    )
    if "文件存在" in stdout:
        print("✅ 文件存在")
    else:
        print("❌ 文件不存在")
        print(f"错误: {stderr}")
        return 1
    
    # 2. 检查后端服务状态
    print("\n[2/3] 检查后端服务状态...")
    stdout, stderr, code = run_command(
        'docker ps --filter "name=dataagent-backend" --format "{{.Status}}"'
    )
    if stdout.strip():
        print(f"✅ 后端服务状态: {stdout.strip()}")
    else:
        print("❌ 后端服务未运行")
        return 1
    
    # 3. 查看最近的日志（后处理检查相关）
    print("\n[3/3] 查看最近的日志（查找后处理检查记录）...")
    stdout, stderr, code = run_command(
        'docker logs dataagent-backend --tail 200 2>&1 | findstr /i "文件数据源检查"'
    )
    if stdout.strip():
        print("✅ 找到后处理检查日志:")
        print(stdout)
    else:
        print("⚠️  未找到后处理检查日志（可能还没有新的查询请求）")
        print("\n提示：请在前端进行一次查询，然后再次运行此脚本查看日志")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n下一步：")
    print("1. 在前端界面进行一次查询（例如：'列出所有用户的名称'）")
    print("2. 观察AI的回答是否正确调用了工具")
    print("3. 如果AI仍然产生幻觉数据，请运行以下命令查看详细日志：")
    print("   docker logs dataagent-backend --tail 500 | findstr /i '文件数据源检查'")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

