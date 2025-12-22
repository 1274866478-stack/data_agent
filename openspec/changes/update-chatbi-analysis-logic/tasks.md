# Tasks: 升级 ChatBI 数据分析与可视化决策逻辑

## 1. 更新 System Prompt

- [x] 1.1 在 `_stream_response_generator` 方法中定位二次 LLM 调用的 `analysis_messages` 构建位置（约第 1865 行）
- [x] 1.2 替换 system message 内容为新的专家数据分析师提示
  - 包含核心协议（CORE PROTOCOLS）
  - 包含可视化逻辑规则（Trend → Line, Comparison → Bar, Composition → Pie）
  - 包含工具使用指导（TOOL USAGE）
  - 动态注入数据库 Schema 上下文

## 2. 植入数据特征分析逻辑

- [x] 2.1 在 SQL 执行成功后、构建 `analysis_prompt` 之前，添加数据特征分析代码
- [x] 2.2 实现数据形态检测：
  - 计算 `row_count` 和 `col_count`
  - 检测时间列（`has_time_col`）：列名包含 date/time/year/month/day/quarter/week
  - 检测数值列（`has_metric_col`）：列数 >= 2
- [x] 2.3 实现决策规则生成 `analysis_directive`：
  - 规则 1：单行数据 → 禁止画图
  - 规则 2：纯文本无数值 → 禁止画图
  - 规则 3：大数据量（>20行）非时序 → 强制 Top 10
  - 规则 4：时间序列 → 强制折线图
  - 规则 5：分类对比 → 建议柱状图或饼图（根据行数决定）

## 3. 注入决策指令到消息

- [x] 3.1 修改 `analysis_prompt` 构建逻辑，将 `analysis_directive` 追加到用户消息中
- [x] 3.2 使用清晰的 `--- ANALYSIS INSTRUCTIONS ---` 分隔符
- [x] 3.3 确保消息格式保持与现有代码兼容

## 4. 测试验证

- [ ] 4.1 测试单行数据场景（应禁止画图）
- [ ] 4.2 测试大数据量场景（应显示 Top 10）
- [ ] 4.3 测试时间序列场景（应使用折线图）
- [ ] 4.4 测试分类对比场景（应使用柱状图或饼图）
