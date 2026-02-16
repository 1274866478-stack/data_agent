# [AGENT] LangGraph SQL 智能代理

## [MODULE]
**模块名称**: LangGraph SQL 智能代理
**职责**: 自然语言SQL查询、图表可视化、Agent工作流编排
**类型**: 独立Python服务

## [BOUNDARY]
**输入**:
- 自然语言查询
- 数据库连接 (MCP)
- 图表配置

**输出**:
- SQL查询结果
- ECharts图表配置
- HTML图表文件

## [PROTOCOL]
1. 使用LangGraph构建Agent工作流
2. MCP协议连接数据库和图表服务
3. DeepSeek LLM进行自然语言理解
4. 自动SQL生成和错误修复

## [STRUCTURE]
```
Agent/
├── sql_agent.py            # 主程序 - LangGraph Agent
├── config.py               # 配置管理
├── models.py               # Pydantic数据模型
├── chart_service.py        # ECharts图表服务
├── data_transformer.py     # 数据转换 (SQL→图表)
├── terminal_viz.py         # 终端可视化
├── run.py                  # 快速启动脚本
├── requirements.txt        # Python依赖
├── .env.example            # 环境变量模板
├── run.sh / run.bat        # 启动脚本
└── charts/                 # 图表输出目录
    └── *.html             # 生成的图表文件
```

## [LINK]
**上游依赖**:
- [../backend/src/app/services/agent/](../backend/src/app/services/agent/_folder.md) - 后端Agent集成

**下游依赖**:
- LangGraph - Agent框架
- DeepSeek API - LLM服务
- MCP Server PostgreSQL - 数据库连接
- MCP Server ECharts - 图表生成
- PyEcharts - 图表渲染

**调用方**:
- 独立运行
- [../backend/src/app/api/v1/endpoints/](../backend/src/app/api/v1/endpoints/_folder.md) - API端点集成

## [STATE]
- LangGraph State: 对话状态
- MemorySaver: 对话历史
- MCP连接: 数据库/图表服务连接

## [THREAD-SAFE**
否 - LangGraph有状态，需要注意并发

## [SIDE-EFFECTS]
- 数据库查询执行
- 图表文件写入
- LLM API调用
