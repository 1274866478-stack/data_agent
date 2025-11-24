"""
智谱AI配置验证工具
用于验证智谱AI API连接和配置
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from src.app.core.config import settings
from src.app.services.zhipu_client import ZhipuAIService

logger = logging.getLogger(__name__)


async def validate_zhipu_config():
    """验证智谱AI配置"""
    print("🔍 开始验证智谱AI配置...")

    issues = []

    # 1. 验证API密钥
    api_key = settings.zhipuai_api_key
    if not api_key:
        issues.append("❌ ZHIPUAI_API_KEY 未设置")
        return False, issues
    elif api_key in ('dev_placeholder', 'test_key'):
        issues.append("⚠️  使用开发占位符API密钥，仅适用于开发环境")
    elif len(api_key) < 40:
        issues.append("❌ API密钥长度不足，可能是无效密钥")
    else:
        print("✅ API密钥格式检查通过")

    # 2. 验证模型配置
    model = settings.zhipuai_default_model
    if not model:
        issues.append("❌ ZHIPUAI_DEFAULT_MODEL 未设置")
    else:
        print(f"✅ 默认模型: {model}")

    # 3. 测试API连接
    print("\n🔌 测试智谱AI API连接...")
    try:
        zhipu_service = ZhipuAIService()
        connection_ok = await zhipu_service.check_connection()

        if connection_ok:
            print("✅ 智谱AI API连接成功")
        else:
            issues.append("❌ 智谱AI API连接失败，请检查网络和API密钥")
            return False, issues

    except Exception as e:
        issues.append(f"❌ 连接测试异常: {e}")
        return False, issues

    # 4. 测试SQL生成功能
    print("\n🧪 测试SQL生成功能...")
    try:
        test_schema = """
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100),
            created_at TIMESTAMP
        );
        """

        generated_sql = await zhipu_service.generate_sql_from_natural_language(
            query="查询所有用户",
            schema=test_schema,
            db_type="postgresql"
        )

        if generated_sql and "SELECT" in generated_sql.upper():
            print(f"✅ SQL生成测试成功: {generated_sql[:50]}...")
        else:
            issues.append("⚠️  SQL生成功能可能存在问题")

    except Exception as e:
        issues.append(f"⚠️  SQL生成测试失败: {e}")

    # 5. 获取模型信息
    print("\n📊 获取模型信息...")
    try:
        model_info = await zhipu_service.get_model_info()
        if model_info and model_info.get("status") == "available":
            print(f"✅ 模型 {model} 可用")
        else:
            issues.append(f"⚠️  模型 {model} 可能不可用")
    except Exception as e:
        issues.append(f"⚠️  获取模型信息失败: {e}")

    # 结果总结
    print(f"\n📋 验证完成:")
    print(f"- 总共发现 {len(issues)} 个问题")

    critical_issues = [issue for issue in issues if issue.startswith("❌")]
    warning_issues = [issue for issue in issues if issue.startswith("⚠️")]

    if critical_issues:
        print(f"- 严重问题: {len(critical_issues)} 个")
        for issue in critical_issues:
            print(f"  {issue}")
        return False, issues
    elif warning_issues:
        print(f"- 警告问题: {len(warning_issues)} 个")
        for issue in warning_issues:
            print(f"  {issue}")
        print("✅ 配置基本可用，但建议解决警告问题")
        return True, issues
    else:
        print("✅ 所有验证通过，智谱AI配置正常")
        return True, issues


async def main():
    """主函数"""
    try:
        success, issues = await validate_zhipu_config()

        if success:
            print("\n🎉 智谱AI配置验证通过！")
            sys.exit(0)
        else:
            print("\n💥 智谱AI配置验证失败！")
            print("\n🔧 修复建议:")
            print("1. 确保设置了有效的智谱AI API密钥")
            print("2. 检查网络连接是否正常")
            print("3. 确认智谱AI服务可用")
            print("4. 查看详细错误日志")
            sys.exit(1)

    except Exception as e:
        print(f"\n💥 配置验证过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 运行异步验证
    asyncio.run(main())