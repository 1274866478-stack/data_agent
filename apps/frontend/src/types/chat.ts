/**
 * # [CHAT_TYPES] 聊天相关TypeScript类型定义
 *
 * ## [MODULE]
 * **文件?*: chat.ts
 * **职责**: 定义聊天功能相关的所有TypeScript类型和接?- 流式响应事件、处理步骤、ECharts配置、回调函?
 * **作?*: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - 无（此文件为类型定义文件，仅导出类型?
 *
 * ## [OUTPUT]
 * - **StreamEventType** - 流式响应事件类型联合
 * - **ProcessingStep** - AI处理步骤接口
 * - **StreamEvent** - 流式响应事件接口
 * - **EChartsOption** - ECharts图表配置接口
 * - **StreamCallbacks** - 流式响应回调函数接口
 *
 * ## [LINK]
 * **上游依赖**:
 * - 无（独立类型定义文件?
 *
 * **下游依赖**:
 * - [../store/chatStore.ts](../store/chatStore.ts) - 聊天状态管?
 * - [../components/chat/ChatInterface.tsx](../components/chat/ChatInterface.tsx) - 聊天界面组件
 * - [../lib/api-client.ts](../lib/api-client.ts) - API客户?
 * - [../utils/stream-parser.ts](../utils/stream-parser.ts) - 流式解析?
 *
 * **调用?*:
 * - 所有需要处理流式响应的组件和服?
 *
 * ## [STATE]
 * - 无（类型定义文件?
 *
 * ## [SIDE-EFFECTS]
 * - 无（类型定义文件?
 */

// 流式响应事件类型定义

export type StreamEventType =
  | 'content'          // 普通对话文本（完整内容?
  | 'content_delta'    // 内容增量（实时流式输出）
  | 'thinking'         // 模型思考过?
  | 'tool_input'       // Agent 生成?SQL 或参?
  | 'tool_result'      // 工具执行结果 (如查询到的数据库数据)
  | 'chart_config'     // ECharts 图表配置
  | 'processing_step'  // AI处理步骤（用于展示推理过程）
  | 'step_update'      // 步骤更新事件（用于更新正在进行的步骤?
  | 'connection_init'  // SSE 连接初始化事?
  | 'error'            // 错误信息
  | 'done';            // 结束信号

// 步骤内容类型
export type StepContentType = 'text' | 'sql' | 'table' | 'chart' | 'error' | 'answer'

// 表格表格分布记录
export interface CellLineage {
  row: number;
  column: string;
  value?: any;
  explanation: string;
  group_keys?: Record<string, any>;
  agg?: string;
}

// 表格数据结构
export interface StepTableData {
  columns: string[];
  rows: Array<Record<string, any> | any[]>; // 兼容对象/数组两种行格?  row_count: number;
  source_label?: string;        // 数据来源标签（用于合并后展示?  merged_from_steps?: number[]; // 合并来源的步骤编?}

// 图表数据结构
export interface StepChartData {
  echarts_option?: EChartsOption;
  chart_image?: string;
  chart_type?: string;
  title?: string;
  chart_index?: number;  // 图表索引（用于支持多图表?
}

// 步骤内容数据
export interface StepContentData {
  sql?: string;              // SQL语句
  table?: StepTableData;     // 表格数据
  chart?: StepChartData;     // 图表配置
  error?: string;            // 错误信息
  suggestion?: string;        // 🔧 新增：错误修复建?
  text?: string;             // 数据分析文本（用于步??
}

// AI处理步骤定义
export interface QueryChainItem {
  step: number;
  sql?: string;
  row_count?: number;
  columns?: string[];
  source?: string;
}

export interface ChartValidation {
  is_valid: boolean;
  required_fields?: string[];
  select_fields?: string[];
  data_fields?: string[];
  missing_in_select?: string[];
  missing_in_data?: string[];
  message?: string;
}
export interface ProcessingStep {
  step: number;           // 步骤编号
  step_id?: string;       // 🔧 新增：步骤唯一标识符，用于去重和合?
  title: string;          // 步骤标题
  message?: string;       // 🔧 新增：步骤消息（用于快速识别步骤类型，?数据分析"?
  description: string;    // 步骤描述
  detail?: string;        // 🔧 新增：步骤详细信息（后端发送的字段名）
  status: 'pending' | 'running' | 'completed' | 'error';  // 步骤状?
  timestamp?: string;     // 时间?
  duration?: number;      // 耗时（毫秒）
  details?: string;       // 额外详情（如SQL内容、Schema信息等）
  // 新增字段：支持在步骤内渲染不同类型的内容
  content_type?: StepContentType;  // 内容类型
  content_data?: StepContentData;  // 内容数据
  // 🔧 新增：实时内容预览（用于显示正在生成的内容）
  content_preview?: string;        // 正在生成的内容预?
  // 🔧 新增：流式输出标识（用于打字机效果）
  streaming?: boolean;             // 是否正在流式输出?
  // 新增：ECharts 图表配置选项
  echart_option?: Record<string, any>;  // ECharts 图表配置
}

export interface StreamEvent {
  type: StreamEventType;
  delta?: string;       // 用于 content ?thinking 的增量文?
  tool_name?: string;   // 用于 tool_input
  args?: string;        // 用于 tool_input (可能是部?SQL)
  data?: any;           // 用于 tool_result ?chart_config (完整?JSON 数据)
  message?: string;     // 用于 error
  content?: string;     // 兼容后端可能直接返回 content 字段
  thinking?: string;    // 兼容后端可能直接返回 thinking 字段
  tool_input?: string;  // 兼容后端可能直接返回 tool_input 字段
  tool_output?: any;    // 兼容后端可能直接返回 tool_output 字段
  error?: string;       // 兼容后端可能直接返回 error 字段
  finished?: boolean;   // 是否完成
  provider?: string;    // 提供商信?
  tenant_id?: string;   // 租户ID
  // processing_step 事件专用字段
  step?: ProcessingStep | number;  // 处理步骤信息或步骤编号（用于 step_update?
  // step_update 事件专用字段
  description?: string;     // 步骤描述更新
  content_preview?: string; // 内容预览（用于显示正在生成的内容?
  streaming?: boolean;      // 🔧 新增：是否正在流式输出中
}

// ECharts 配置接口
export interface EChartsOption {
  title?: { text?: string; subtext?: string };
  tooltip?: any;
  legend?: any;
  xAxis?: any;
  yAxis?: any;
  series?: any[];
  [key: string]: any;  // 允许其他 ECharts 配置?
}

// 定义回调函数类型，用于更?UI
export interface StreamCallbacks {
  onContent: (delta: string) => void;
  onThinking: (delta: string) => void;
  onToolInput: (toolName: string, args: string) => void;
  onToolResult: (data: any) => void;
  onChartConfig: (echartsOption: EChartsOption) => void;  // 处理图表配置
  onProcessingStep: (step: ProcessingStep) => void;       // 处理AI推理步骤
  onStepUpdate?: (step: number, description: string, contentPreview?: string, streaming?: boolean) => void;  // 🔧 步骤更新回调（新增streaming参数?
  onError: (error: string) => void;
  onDone: () => void;
}

// ============================================================================
// V2 流式响应类型定义 (用于 AgentV2 查询流式端点)
// ============================================================================


/**
 * V2 流式会话状?
 */
export type V2SessionStatus = 'running' | 'paused' | 'completed' | 'error' | 'cancelled';

/**
 * V2 流式会话状态数?
 */
export interface V2SessionState {
  session_id: string;
  tenant_id: string;
  user_id: string;
  query: string;
  status: V2SessionStatus;
  accumulated_answer: string;
  current_progress: number;
  processing_steps: Array<{
    step: number;
    title: string;
    description: string;
    status: string;
  }>;
  created_at: number;
  updated_at: number;
}

/**
 * V2 暂停会话响应数据
 */
export interface V2PauseResponse {
  success: boolean;
  session_id: string;
  status: 'paused';
  accumulated_answer: string;
  current_progress: number;
}

/**
 * V2 恢复会话响应数据
 */
export interface V2ResumeResponse {
  success: boolean;
  session_id: string;
  status: 'running';
  message: string;
  accumulated_answer: string;
  current_progress: number;
  recommendation: string;
}

/**
 * V2 取消会话响应数据
 */
export interface V2CancelResponse {
  success: boolean;
  session_id: string;
  status: 'cancelled';
  accumulated_answer: string;
}

/**
 * 日志流式回调函数接口
 * 用于处理日志查询?SSE 事件
 */

/** 日志流开始数?*/
