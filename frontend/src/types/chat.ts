/**
 * # [CHAT_TYPES] 聊天相关TypeScript类型定义
 *
 * ## [MODULE]
 * **文件名**: chat.ts
 * **职责**: 定义聊天功能相关的所有TypeScript类型和接口 - 流式响应事件、处理步骤、ECharts配置、回调函数
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - 无（此文件为类型定义文件，仅导出类型）
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
 * - 无（独立类型定义文件）
 *
 * **下游依赖**:
 * - [../store/chatStore.ts](../store/chatStore.ts) - 聊天状态管理
 * - [../components/chat/ChatInterface.tsx](../components/chat/ChatInterface.tsx) - 聊天界面组件
 * - [../lib/api-client.ts](../lib/api-client.ts) - API客户端
 * - [../utils/stream-parser.ts](../utils/stream-parser.ts) - 流式解析器
 *
 * **调用方**:
 * - 所有需要处理流式响应的组件和服务
 *
 * ## [STATE]
 * - 无（类型定义文件）
 *
 * ## [SIDE-EFFECTS]
 * - 无（类型定义文件）
 */

// 流式响应事件类型定义

export type StreamEventType =
  | 'content'          // 普通对话文本（完整内容）
  | 'content_delta'    // 内容增量（实时流式输出）
  | 'thinking'         // 模型思考过程
  | 'tool_input'       // Agent 生成的 SQL 或参数
  | 'tool_result'      // 工具执行结果 (如查询到的数据库数据)
  | 'chart_config'     // ECharts 图表配置
  | 'processing_step'  // AI处理步骤（用于展示推理过程）
  | 'step_update'      // 步骤更新事件（用于更新正在进行的步骤）
  | 'connection_init'  // SSE 连接初始化事件
  | 'error'            // 错误信息
  | 'done';            // 结束信号

// 步骤内容类型
export type StepContentType = 'text' | 'sql' | 'table' | 'chart' | 'error' | 'answer'

// 表格数据结构
export interface StepTableData {
  columns: string[];
  rows: Record<string, any>[];
  row_count: number;
}

// 图表数据结构
export interface StepChartData {
  echarts_option?: EChartsOption;
  chart_image?: string;
  chart_type?: string;
  title?: string;
  chart_index?: number;  // 图表索引（用于支持多图表）
}

// 步骤内容数据
export interface StepContentData {
  sql?: string;              // SQL语句
  table?: StepTableData;     // 表格数据
  chart?: StepChartData;     // 图表配置
  error?: string;            // 错误信息
  suggestion?: string;        // 🔧 新增：错误修复建议
  text?: string;             // 数据分析文本（用于步骤8）
}

// AI处理步骤定义
export interface ProcessingStep {
  step: number;           // 步骤编号
  step_id?: string;       // 🔧 新增：步骤唯一标识符，用于去重和合并
  title: string;          // 步骤标题
  message?: string;       // 🔧 新增：步骤消息（用于快速识别步骤类型，如"数据分析"）
  description: string;    // 步骤描述
  detail?: string;        // 🔧 新增：步骤详细信息（后端发送的字段名）
  status: 'pending' | 'running' | 'completed' | 'error';  // 步骤状态
  timestamp?: string;     // 时间戳
  duration?: number;      // 耗时（毫秒）
  details?: string;       // 额外详情（如SQL内容、Schema信息等）
  // 新增字段：支持在步骤内渲染不同类型的内容
  content_type?: StepContentType;  // 内容类型
  content_data?: StepContentData;  // 内容数据
  // 🔧 新增：实时内容预览（用于显示正在生成的内容）
  content_preview?: string;        // 正在生成的内容预览
  // 🔧 新增：流式输出标识（用于打字机效果）
  streaming?: boolean;             // 是否正在流式输出中
  // 新增：ECharts 图表配置选项
  echart_option?: Record<string, any>;  // ECharts 图表配置
}

export interface StreamEvent {
  type: StreamEventType;
  delta?: string;       // 用于 content 或 thinking 的增量文本
  tool_name?: string;   // 用于 tool_input
  args?: string;        // 用于 tool_input (可能是部分 SQL)
  data?: any;           // 用于 tool_result 和 chart_config (完整的 JSON 数据)
  message?: string;     // 用于 error
  content?: string;     // 兼容后端可能直接返回 content 字段
  thinking?: string;    // 兼容后端可能直接返回 thinking 字段
  tool_input?: string;  // 兼容后端可能直接返回 tool_input 字段
  tool_output?: any;    // 兼容后端可能直接返回 tool_output 字段
  error?: string;       // 兼容后端可能直接返回 error 字段
  finished?: boolean;   // 是否完成
  provider?: string;    // 提供商信息
  tenant_id?: string;   // 租户ID
  // processing_step 事件专用字段
  step?: ProcessingStep | number;  // 处理步骤信息或步骤编号（用于 step_update）
  // step_update 事件专用字段
  description?: string;     // 步骤描述更新
  content_preview?: string; // 内容预览（用于显示正在生成的内容）
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
  [key: string]: any;  // 允许其他 ECharts 配置项
}

// 定义回调函数类型，用于更新 UI
export interface StreamCallbacks {
  onContent: (delta: string) => void;
  onThinking: (delta: string) => void;
  onToolInput: (toolName: string, args: string) => void;
  onToolResult: (data: any) => void;
  onChartConfig: (echartsOption: EChartsOption) => void;  // 处理图表配置
  onProcessingStep: (step: ProcessingStep) => void;       // 处理AI推理步骤
  onStepUpdate?: (step: number, description: string, contentPreview?: string, streaming?: boolean) => void;  // 🔧 步骤更新回调（新增streaming参数）
  onError: (error: string) => void;
  onDone: () => void;
}

// ============================================================================
// V2 流式响应类型定义 (用于 AgentV2 查询流式端点)
// ============================================================================

/**
 * V2 流式事件类型
 * 对应后端 /api/v2/query/stream 端点的 SSE 事件
 */
export type V2StreamEventType = 'start' | 'step' | 'progress' | 'data' | 'error' | 'done';

/**
 * V2 步骤事件数据
 * 🔧 扩展：支持 V1 ProcessingStep 兼容字段
 */
export interface V2StepData {
  step: number;
  step_id?: string;  // 🔧 新增：步骤唯一标识符，用于去重和合并
  message: string;
  detail?: string;
  // 🔧 新增：V1 ProcessingStep 兼容字段
  status?: 'pending' | 'running' | 'completed' | 'error';
  content_type?: 'text' | 'sql' | 'table' | 'chart' | 'error';
  content_data?: {
    sql?: string;
    table?: StepTableData;
    chart?: StepChartData;
    text?: string;
    error?: string;
    suggestion?: string;  // 🔧 新增：错误修复建议
  };
  duration?: number;
  streaming?: boolean;
  content_preview?: string;
}

/**
 * V2 进度事件数据
 */
export interface V2ProgressData {
  value: number;  // 0-100
}

/**
 * V2 数据块事件（答案分块）
 */
export interface V2DataChunk {
  chunk: string;
  progress: number;
}

/**
 * V2 完成事件数据
 */
export interface V2DoneData {
  success: boolean;
  answer: string;
  processing_steps: ProcessingStep[] | string[];  // 🔧 修复：支持步骤对象或字符串数组
  tenant_id: string;
  processing_time_ms?: number;
  chart_config?: string | Record<string, any>;  // 图表配置（JSON字符串或对象）
  connection_id?: string;
}

/**
 * V2 错误事件数据
 */
export interface V2ErrorData {
  error: string;
  detail?: string;
  error_type?: string;
}

/**
 * V2 开始事件数据
 */
export interface V2StartData {
  query: string;
  tenant_id: string;
  session_id: string;
  timestamp: number;
}

/**
 * V2 流式回调函数接口
 * 用于处理 /api/v2/query/stream 端点的 SSE 事件
 */
export interface V2StreamCallbacks {
  /** 开始事件 */
  onStart?: (data: V2StartData) => void;
  /** 步骤更新 */
  onStep?: (data: V2StepData) => void;
  /** 进度更新 (0-100) */
  onProgress?: (data: V2ProgressData) => void;
  /** 数据块（答案分块） */
  onData?: (data: V2DataChunk) => void;
  /** 完成事件 */
  onDone?: (data: V2DoneData) => void;
  /** 错误事件 */
  onError?: (data: V2ErrorData) => void;
}

/**
 * V2 流式会话状态
 */
export type V2SessionStatus = 'running' | 'paused' | 'completed' | 'error' | 'cancelled';

/**
 * V2 流式会话状态数据
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

