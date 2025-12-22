## ADDED Requirements

### Requirement: Smart Visualization Decision
The AI assistant SHALL analyze SQL query result characteristics (row count, column types) before deciding whether to generate a chart.

#### Scenario: Single row result
- **WHEN** the SQL query returns only 1 row of data
- **THEN** the AI MUST NOT call the chart generation tool
- **AND** the AI SHALL explain the single value directly in text

#### Scenario: Text list without metrics
- **WHEN** the SQL query returns a list without numerical metrics (only text columns)
- **AND** the result has fewer than 50 rows
- **THEN** the AI MUST NOT call the chart generation tool
- **AND** the AI SHALL summarize the list content (count, examples)

#### Scenario: Large dataset without time series
- **WHEN** the SQL query returns more than 20 rows
- **AND** no time-related columns are detected
- **THEN** the AI SHALL generate a chart showing only the Top 10 data points
- **AND** the AI SHALL mention in text that only top performers are shown

#### Scenario: Time series data
- **WHEN** the SQL query result contains time-related columns (date, time, year, month, day, quarter, week)
- **AND** more than 1 row is returned
- **THEN** the AI MUST use a line chart for visualization
- **AND** the AI SHALL focus analysis on trends, seasonality, or spikes

#### Scenario: Categorical comparison data
- **WHEN** the SQL query result contains categorical data for comparison
- **AND** no time-related columns are detected
- **AND** the result has 8 or fewer rows
- **THEN** the AI SHOULD use a pie chart for visualization

#### Scenario: Categorical comparison with many items
- **WHEN** the SQL query result contains categorical data for comparison
- **AND** no time-related columns are detected
- **AND** the result has more than 8 rows but 20 or fewer
- **THEN** the AI SHOULD use a bar chart for visualization

### Requirement: Enhanced System Prompt for Data Analysis
The AI assistant's system prompt for the second LLM call (data analysis phase) SHALL include clear protocols for data analysis and visualization.

#### Scenario: System prompt structure
- **WHEN** the AI is about to perform data analysis on SQL results
- **THEN** the system prompt SHALL include:
  - Core protocols for following instructions
  - Rules for meaningful data analysis (not just repeating numbers)
  - Visualization logic mapping (Trend → Line, Comparison → Bar, Composition → Pie)
  - Tool usage guidelines

#### Scenario: Analysis directive injection
- **WHEN** SQL query results are ready for analysis
- **THEN** the system SHALL inject an analysis directive into the user message
- **AND** the directive SHALL be based on detected data characteristics
- **AND** the directive SHALL use constraint markers (🛑 for prohibitions, ⚠️ for warnings, ✅ for recommendations)

## MODIFIED Requirements

### Requirement: Data Analysis Second LLM Call
The system SHALL perform a second LLM call after SQL execution to analyze data and generate appropriate visualizations, with enhanced decision-making based on data characteristics.

#### Scenario: Second LLM call with data feature analysis
- **WHEN** SQL query execution succeeds
- **AND** the result contains data
- **THEN** the system SHALL analyze data shape (row count, column types)
- **AND** the system SHALL generate an analysis directive based on detected features
- **AND** the system SHALL include the directive in the user message sent to the LLM
- **AND** the LLM response SHALL follow the constraints specified in the directive

