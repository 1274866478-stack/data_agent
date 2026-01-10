"""
# [RUN] Agent启动脚本

## [HEADER]
**文件名**: run.py
**职责**: SQL Agent的启动入口 - 支持独立模式和Backend集成模式，配置验证、命令行参数解析、交互模式启动
**作者**: Data Agent Team
**版本**: 1.0.0
**变更记录**:
- v1.0.0 (2026-01-01): 初始版本 - Agent启动脚本

## [INPUT]
### main() 函数输入
- **命令行参数** (sys.argv):
  - 无参数: 启动交互模式（interactive_mode）
  - 有参数: 将参数拼接为问题字符串，执行单次查询（run_agent）

### 环境变量
- **DEEPSEEK_API_KEY**: DeepSeek API密钥（必需）
- **DATABASE_URL**: PostgreSQL数据库连接URL（必需）
- **DEEPSEEK_BASE_URL**: DeepSeek API基础URL（可选，默认https://api.deepseek.com）
- **DEEPSEEK_MODEL**: DeepSeek模型名称（可选，默认deepseek-chat）

## [OUTPUT]
### main() 函数行为
- **配置检测**: 检测Backend配置是否可用，输出配置来源信息
- **配置验证**: 调用 config.validate_config() 验证必需配置
  - 失败时打印错误信息和配置说明，退出码1
- **命令行模式**: 传递问题参数给 run_agent(question)
- **交互模式**: 启动 interactive_mode()，支持多轮对话
- **错误处理**: 配置错误时输出详细的 .env 文件示例

### 控制台输出
- **配置信息**: ℹ️ 检测到后端配置 / 使用 .env 文件 / 未找到 .env 文件
- **配置错误**: ❌ 配置错误 + 详细说明
- **单次查询**: 📝 查询: {question}
- **交互模式**: 💬 进入交互模式 (输入 'exit' 或 'quit' 退出)

## [LINK]
**上游依赖** (已读取源码):
- [python-asyncio](https://docs.python.org/3/library/asyncio.html) - 异步运行时（asyncio.run）
- [python-sys](https://docs.python.org/3/library/sys.html) - 系统参数（sys.argv, sys.exit）
- [python-os](https://docs.python.org/3/library/os.html) - 操作系统接口（os.path）
- [python-pathlib](https://docs.python.org/3/library/pathlib.html) - 路径处理（Path）

**下游依赖** (已读取源码):
- [./sql_agent.py](./sql_agent.py) - Agent主程序（run_agent, interactive_mode）
- [./config.py](./config.py) - 配置管理（config, config.validate_config）

**调用方**:
- **命令行**: python Agent/run.py [question]
- **用户**: 直接运行脚本启动Agent

## [POS]
**路径**: Agent/run.py
**模块层级**: Level 1（Agent根目录）
**依赖深度**: 直接依赖 3 层（Python标准库 + 本地Agent模块）
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

