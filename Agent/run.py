"""
Simple runner script for SQL Agent
Supports both standalone mode and backend integration mode
"""
import asyncio
import sys
import os
from pathlib import Path
from sql_agent import run_agent, interactive_mode
from config import config


def main():
    """Main entry point"""
    # Print configuration source info
    backend_config_available = False
    try:
        backend_src = Path(__file__).parent.parent / "backend" / "src"
        if backend_src.exists():
            backend_config_available = True
            print("ℹ️  检测到后端配置，将优先使用后端配置")
    except Exception:
        pass
    
    if not backend_config_available:
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            print("ℹ️  使用 Agent 目录下的 .env 文件配置")
        else:
            print("⚠️  未找到 .env 文件，将使用环境变量")
    
    # Validate configuration
    try:
        config.validate_config()
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        print("\n配置说明:")
        print("1. 如果 Agent 集成到后端，配置将从 backend/.env 加载")
        print("2. 如果独立运行，请在 Agent 目录下创建 .env 文件")
        print("3. 必需的环境变量:")
        print("   - DEEPSEEK_API_KEY: DeepSeek API 密钥")
        print("   - DATABASE_URL: PostgreSQL 数据库连接字符串")
        print("\n示例 .env 文件:")
        print("DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxx")
        print("DATABASE_URL=postgresql://user:password@localhost:5432/dbname")
        sys.exit(1)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        # Run with provided question
        question = " ".join(sys.argv[1:])
        print(f"\n📝 查询: {question}\n")
        asyncio.run(run_agent(question))
    else:
        # Run interactive mode
        print("\n💬 进入交互模式 (输入 'exit' 或 'quit' 退出)\n")
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()

