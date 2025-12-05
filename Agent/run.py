"""
Simple runner script for SQL Agent
"""
import asyncio
import sys
from sql_agent import run_agent, interactive_mode
from config import config


def main():
    """Main entry point"""
    # Validate configuration
    try:
        config.validate_config()
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        print("请检查 .env 文件中的配置")
        sys.exit(1)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        # Run with provided question
        question = " ".join(sys.argv[1:])
        asyncio.run(run_agent(question))
    else:
        # Run interactive mode
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()

