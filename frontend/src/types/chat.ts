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
  | 'content'          // 普通对话文本
  | 'thinking'         // 模型思考过程
  | 'tool_input'       // Agent 生成的 SQL 或参数
  | 'tool_result'      // 工具执行结果 (如查询到的数据库数据)
  | 'chart_config'     // ECharts 图表配置
  | 'processing_step'  // AI处理步骤（用于展示推理过程）
  | 'error'            // 错误信息
  | 'done';            // 结束信号

// 步骤内容类型
export type StepContentType = 'text' | 'sql' | 'table' | 'chart' | 'error'

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
}

// 步骤内容数据
export interface StepContentData {
  sql?: string;              // SQL语句
  table?: StepTableData;     // 表格数据
  chart?: StepChartData;     // 图表配置
  error?: string;            // 错误信息
  text?: string;             // 数据分析文本（用于步骤8）
}

// AI处理步骤定义
export interface ProcessingStep {
  step: number;           // 步骤编号
  title: string;          // 步骤标题
  description: string;    // 步骤描述
  status: 'pending' | 'running' | 'completed' | 'error';  // 步骤状态
  timestamp?: string;     // 时间戳
  duration?: number;      // 耗时（毫秒）
  details?: string;       // 额外详情（如SQL内容、Schema信息等）
  // 新增字段：支持在步骤内渲染不同类型的内容
  content_type?: StepContentType;  // 内容类型
  content_data?: StepContentData;  // 内容数据
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
  step?: ProcessingStep;  // 处理步骤信息
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
  onError: (error: string) => void;
  onDone: () => void;
}

