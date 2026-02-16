# Agent Service

LangGraph SQL 智能代理服务，V5 版本。

## Scope
提供自然语言到 SQL 的转换能力，支持安全查询执行和数据可视化。

## Members
| File | Description |
|------|-------------|
| `agent_service.py` | 核心代理服务 (LangGraph状态机) |
| `tools.py` | SQL 工具集 (执行, 验证, schema查询) |
| `prompts.py` | 系统提示词和业务逻辑 |
| `models.py` | 数据模型和类型定义 |
| `data_transformer.py` | 数据格式转换 (MCP ECharts) |
| `path_extractor.py` | 推理路径提取 |
| `response_formatter.py` | 响应格式化 |
| `examples.py` | Golden 示例加载 |
| `DIAGNOSIS.md` | 诊断文档 |

## Constraints
- 仅允许 SELECT 查询 (禁止 INSERT/UPDATE/DELETE)
- SQL 执行前必须经过安全验证
- 递归深度限制防止死循环
- 响应必须包含可解释的推理路径
