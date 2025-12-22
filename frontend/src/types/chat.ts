// 流式响应事件类型定义

export type StreamEventType = 
  | 'content'       // 普通对话文本
  | 'thinking'      // 模型思考过程
  | 'tool_input'    // Agent 生成的 SQL 或参数
  | 'tool_result'   // 工具执行结果 (如查询到的数据库数据)
  | 'chart_config'  // ECharts 图表配置
  | 'error'         // 错误信息
  | 'done';         // 结束信号

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
  onChartConfig: (echartsOption: EChartsOption) => void;  // 新增：处理图表配置
  onError: (error: string) => void;
  onDone: () => void;
}

