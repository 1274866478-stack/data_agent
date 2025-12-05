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

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 确保已安装 Node.js (用于运行 MCP Server)
node --version
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```env
DEEPSEEK_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/your_database
```

### 3. 运行 Agent

```bash
python sql_agent.py
```

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
├── config.py         # 配置管理
├── requirements.txt  # Python 依赖
├── .env              # 环境变量 (需自行创建)
├── .env.example      # 环境变量模板
└── README.md         # 本文件
```

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

