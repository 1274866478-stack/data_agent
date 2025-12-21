## MODIFIED Requirements

### Requirement: AI 助手数据准确性
AI 助手在回答用户数据查询时，SHALL 始终基于真实数据源返回的数据，绝对禁止编造、修改或替换数据。

#### Scenario: 响应转换时强制检查幻觉
- **WHEN** Agent返回响应并转换为API响应格式
- **THEN** 响应转换函数必须检查`metadata.hallucination_detected`标志
- **AND** 如果检测到幻觉，必须使用错误消息替换`explanation`字段
- **AND** 必须清除所有可能包含假数据的字段（如`results`、`data`等）
- **AND** 用户必须收到明确的错误提示，而不是假数据

#### Scenario: 检测逻辑执行时机
- **WHEN** Agent完成流式输出
- **THEN** 幻觉检测逻辑必须立即执行
- **AND** 如果检测到幻觉，必须立即更新`VisualizationResponse.answer`字段
- **AND** 必须确保`cleaned_content`和`final_content`都设置为错误消息
- **AND** 必须设置`metadata.hallucination_detected = True`

#### Scenario: 响应级别的二次检查
- **WHEN** 响应转换函数处理Agent响应
- **THEN** 即使`VisualizationResponse.answer`包含假数据，也要进行二次检查
- **AND** 如果检测到假数据模式（如"张三"、"李四"、"王五"、"赵六"），必须拦截
- **AND** 必须使用错误消息替换所有假数据
- **AND** 这是最后一道防线，确保用户永远不会收到假数据

## ADDED Requirements

### Requirement: 响应转换时的幻觉拦截
响应转换函数 SHALL 在转换Agent响应时检查幻觉检测标志，如果检测到幻觉，必须强制拦截并返回错误消息。

#### Scenario: 检查metadata中的幻觉标志
- **WHEN** `convert_agent_response_to_query_response`函数被调用
- **THEN** 函数必须检查`agent_response.metadata.hallucination_detected`标志
- **AND** 如果标志为`True`，必须使用`metadata.hallucination_reason`中的错误消息
- **AND** 必须将`explanation`字段设置为错误消息，而不是原始`answer`
- **AND** 必须清除`results`和`data`字段，防止假数据泄露

#### Scenario: 响应级别的假数据检测
- **WHEN** 响应转换函数处理Agent响应
- **THEN** 函数必须对`agent_response.answer`进行二次检查
- **AND** 如果检测到假数据模式（如"张三"、"李四"、"王五"、"赵六"等），必须拦截
- **AND** 即使`metadata.hallucination_detected`为`False`，也要进行二次检查
- **AND** 这是最后一道防线，确保万无一失

