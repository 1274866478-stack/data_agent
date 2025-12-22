## MODIFIED Requirements

### Requirement: Streaming Response with Chart Generation

The AI assistant streaming interface SHALL restore the chart generation capability that existed in the non-streaming implementation.

#### Scenario: Generate chart during streaming response
- **WHEN** the user asks "分析销量趋势并画图"
- **AND** the AI is responding via streaming SSE
- **THEN** the system SHALL:
  1. Stream the text response incrementally
  2. Execute SQL queries via `execute_sql` tool
  3. Detect `[CHART_START]...[CHART_END]` markers in response
  4. Extract ECharts JSON configuration
  5. Send chart configuration via `chart_config` SSE event
  6. Remove chart markers from final text content
- **AND** the frontend SHALL render the ECharts chart

#### Scenario: Streaming without chart
- **WHEN** the user asks a simple data query without visualization request
- **THEN** the system SHALL stream text response normally
- **AND** no chart configuration SHALL be sent

### Requirement: System Prompt with Chart Instructions

The system prompt for streaming responses SHALL include chart generation instructions from the original `prompts.py`.

#### Scenario: Prompt includes chart workflow
- **WHEN** the AI receives a data-related question
- **THEN** the system prompt SHALL instruct the AI to:
  1. Query data using `execute_sql`
  2. Analyze the data and summarize insights
  3. If visualization is appropriate, output ECharts JSON in `[CHART_START]...[CHART_END]` format

#### Scenario: Chart format requirement
- **WHEN** the AI generates a chart configuration
- **THEN** it SHALL use the format:
  ```
  [CHART_START]
  { "title": {...}, "xAxis": {...}, "yAxis": {...}, "series": [...] }
  [CHART_END]
  ```

## ADDED Requirements

### Requirement: Chart Configuration SSE Event

The streaming response SHALL support a new event type for chart configurations.

#### Scenario: Send chart config event
- **WHEN** ECharts JSON is detected in the response
- **THEN** the system SHALL send an SSE event:
  ```json
  {
    "type": "chart_config",
    "data": { "echarts_option": {...} },
    "provider": "deepseek",
    "finished": false
  }
  ```

#### Scenario: Frontend receives chart config
- **WHEN** the frontend receives a `chart_config` event
- **THEN** it SHALL store the configuration in `message.metadata.echarts_option`
- **AND** render the ECharts chart in the message display

### Requirement: Restore Data Analysis Behavior

The AI SHALL perform data analysis before presenting results, as it did in the original implementation.

#### Scenario: Analysis with SQL results
- **WHEN** the AI retrieves data via `execute_sql`
- **THEN** the AI SHALL:
  1. Summarize key findings from the data
  2. Identify trends, patterns, or anomalies
  3. Provide actionable insights
- **AND** optionally generate a chart if visualization would help

#### Scenario: Analysis prompt enforcement
- **WHEN** constructing the system prompt
- **THEN** it SHALL include instructions matching the original `prompts.py`:
  - "基于真实数据生成回答"
  - "在文字回复的最后，必须包含 [CHART_START]...[CHART_END] 标记的 ECharts JSON 配置"
