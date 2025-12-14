# LangGraph SQL Agent

基于 LangGraph 和 MCP (Model Context Protocol) 的 SQL 智能查询代理。

## 功能特点

- 🤖 使用 DeepSeek LLM 进行自然语言理解
- 🔗 通过 MCP 协议连接 PostgreSQL 数据库
- 💬 支持多轮对话的交互式查询
- 📊 自动获取数据库 schema 并生成 SQL

## 技术栈

- **LLM**: DeepSeek (OpenAI 兼容接口)
- **Agent Framework**: LangGraph
- **Database Protocol**: MCP (Model Context Protocol)
- **MCP Server**: @modelcontextprotocol/server-postgres
- **Database**: PostgreSQL

## 快速开始

### 运行方式

Agent 支持两种运行方式：

#### 方式 1: 集成到后端（推荐）

如果 Agent 已集成到 Data Agent V4 后端项目中：

1. **使用后端环境**：Agent 会自动使用后端的配置和依赖
2. **配置**：在 `backend/.env` 中配置 DeepSeek API 密钥和数据库连接
3. **运行**：通过后端 API 端点 `/api/v1/query` 调用 Agent

#### 方式 2: 独立运行

如果需要独立运行 Agent（例如测试或开发）：

1. **安装依赖**

```bash
# 方式 A: 使用后端环境（推荐）
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 方式 B: 使用 Agent 独立环境
cd Agent
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **配置环境变量**

如果使用后端环境，配置在 `backend/.env`：
```env
DEEPSEEK_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/your_database
```

如果独立运行，在 `Agent/` 目录下创建 `.env` 文件：
```env
DEEPSEEK_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/your_database
```

3. **运行 Agent**

```bash
# 使用运行脚本（推荐）
python run.py                    # 交互模式
python run.py "你的问题"         # 单次查询

# 或直接运行
python sql_agent.py
```

**注意**：
- 如果检测到后端配置，Agent 会优先使用后端配置
- 如果后端配置不可用，Agent 会回退到 Agent 目录下的 `.env` 文件
- 确保已安装 Node.js (用于运行 MCP Server): `node --version`

## 使用示例

```
📝 请输入你的问题: 数据库里有哪些表？

🔧 调用工具: ['list_tables']

💬 回答:
数据库中包含以下表：
1. users - 用户信息表
2. orders - 订单表
3. products - 产品表
...

📝 请输入你的问题: 查询最近10个订单

🔧 调用工具: ['get_schema', 'query']

💬 回答:
以下是最近的10个订单：
| 订单ID | 用户 | 金额 | 时间 |
|--------|------|------|------|
| ...    | ...  | ...  | ...  |
```

## 项目结构

```
Agent/
├── sql_agent.py      # 主程序入口
├── run.py            # 运行脚本（推荐使用）
├── run.bat           # Windows 运行脚本
├── run.sh            # Linux/Mac 运行脚本
├── config.py         # 配置管理（支持后端配置集成）
├── requirements.txt  # Python 依赖（已合并到 backend/requirements.txt）
├── .env              # 环境变量 (需自行创建，独立运行时使用)
├── .env.example      # 环境变量模板
├── venv/             # 独立虚拟环境（可选，推荐使用后端环境）
└── README.md         # 本文件
```

**注意**：
- `venv/` 目录用于独立运行，如果使用后端环境则不需要
- `venv/` 已在 `.gitignore` 中，不会被提交到版本控制

## 注意事项

1. **只读模式**: Agent 只会执行 SELECT 查询，不会修改数据
2. **MCP Server**: 需要 Node.js 环境来运行 PostgreSQL MCP Server
3. **API 费用**: 使用 DeepSeek API 会产生费用

## 集成到主项目

此 Agent 可以集成到 Data Agent V4 主项目中：

```python
from Agent.sql_agent import run_agent

# 在 FastAPI 端点中使用
@app.post("/api/v1/query")
async def natural_language_query(question: str):
    result = await run_agent(question)
    return {"result": result}
```

## 故障排除

### MCP Server 启动失败
确保已安装 Node.js 和 npx：
```bash
npm install -g npx
```

### 数据库连接失败
检查 DATABASE_URL 格式是否正确，数据库是否运行中。

### DeepSeek API 错误
确认 API Key 有效，检查网络连接。

