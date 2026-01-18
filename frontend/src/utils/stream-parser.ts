/**
 * # [STREAM_PARSER] SSE流式响应解析器
 *
 * ## [MODULE]
 * **文件名**: stream-parser.ts
 * **职责**: 解析Server-Sent Events (SSE)格式的流式响应数据，处理粘包问题，分发事件到回调函数
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - **reader: ReadableStreamDefaultReader<Uint8Array>** - fetch API的响应流reader
 * - **callbacks: StreamCallbacks** - 各类事件的回调处理函数
 *   - onContent: 内容增量回调
 *   - onThinking: 思考过程回调
 *   - onToolInput: 工具输入回调
 *   - onToolResult: 工具结果回调
 *   - onChartConfig: 图表配置回调
 *   - onProcessingStep: 处理步骤回调
 *   - onError: 错误回调
 *   - onDone: 完成回调
 * - **signal?: AbortSignal** - 可选的中断信号，用于取消流式读取
 *
 * ## [OUTPUT]
 * - **返回值: Promise<void>** - 异步函数，通过callbacks分发事件
 * - **副作用**: 调用各类回调函数，将解析的事件传递给UI层
 *
 * ## [LINK]
 * **上游依赖**:
 * - [../types/chat.ts](../types/chat.ts) - StreamEvent和StreamCallbacks类型定义
 *
 * **下游依赖**:
 * - [../store/chatStore.ts](../store/chatStore.ts) - 聊天状态管理（调用parseStreamResponse）
 * - [../components/chat/ChatInterface.tsx](../components/chat/ChatInterface.tsx) - 聊天界面组件
 *
 * **调用方**:
 * - chatStore.sendMessage方法
 *
 * ## [STATE]
 * - **buffer: string** - 缓存未处理完的字符串，用于处理粘包问题
 *
 * ## [SIDE-EFFECTS]
 * - 读取并消耗ReadableStream
 * - 调用回调函数（可能触发React状态更新）
 * - 释放reader锁
 * - 记录控制台日志
 */

// 流式响应解析器 - 处理 SSE 格式的流式数据
import { StreamEvent, StreamCallbacks } from '../types/chat';

/**
 * 解析 SSE 流式响应的核心函数
 * 解决了粘包（Chunk Splitting）问题
 * @param reader fetch response 的 reader
 * @param callbacks 各类事件的回调处理
 * @param signal AbortSignal 用于检测取消
 */
export async function parseStreamResponse(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
) {
  const decoder = new TextDecoder();
  let buffer = ''; // 缓存未处理完的字符串

  try {
    while (true) {
      // 检查是否被用户手动取消
      if (signal?.aborted) {
        reader.cancel();
        break;
      }

      const { done, value } = await reader.read();
      
      if (done) {
        // 处理缓冲区中剩余的数据
        if (buffer.trim()) {
          processBuffer(buffer, callbacks);
        }
        callbacks.onDone();
        break;
      }

      // 1. 解码当前 chunk 并追加到 buffer
      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;

      // 2. 按双换行符拆分消息 (SSE 标准通常以 \n\n 分隔事件)
      // 注意：有些实现可能只用 \n，这里同时支持两种格式
      const lines = buffer.split(/\n\n|\n(?=data:)/);
      
      // 保留最后一个可能不完整的片段在 buffer 中，等待下一次拼接
      buffer = lines.pop() || ''; 

      // 3. 处理完整的消息行
      for (const line of lines) {
        const trimmedLine = line.trim();
        if (!trimmedLine) continue;

        // 处理 data: 开头的行
        if (trimmedLine.startsWith('data: ')) {
          const dataStr = trimmedLine.slice(6); // 去掉 'data: ' 前缀

          // 处理结束标记
          if (dataStr === '[DONE]') {
            callbacks.onDone();
            return;
          }

          try {
            // 4. 解析 JSON 数据
            const event: StreamEvent = JSON.parse(dataStr);
            // 添加调试日志
            console.log('[StreamParser] 收到事件:', event.type, event);
            dispatchStreamEvent(event, callbacks);
          } catch (e) {
            console.warn('[StreamParser] Failed to parse stream event JSON:', dataStr, e);
            // 继续处理下一行，不中断流
          }
        }
      }
    }
  } catch (error: any) {
    if (error.name === 'AbortError') {
      console.log('[StreamParser] Stream aborted by user');
    } else {
      console.error('[StreamParser] Stream reading error:', error);
      callbacks.onError(error.message || 'Stream reading failed');
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * 处理缓冲区中剩余的数据
 */
function processBuffer(buffer: string, callbacks: StreamCallbacks) {
  const trimmed = buffer.trim();
  if (!trimmed) return;

  if (trimmed.startsWith('data: ')) {
    const dataStr = trimmed.slice(6);
    if (dataStr === '[DONE]') {
      callbacks.onDone();
      return;
    }

    try {
      const event: StreamEvent = JSON.parse(dataStr);
      dispatchStreamEvent(event, callbacks);
    } catch (e) {
      console.warn('[StreamParser] Failed to parse buffer data:', dataStr);
    }
  }
}

/**
 * 分发事件到对应的回调
 */
function dispatchStreamEvent(event: StreamEvent, callbacks: StreamCallbacks) {
  switch (event.type) {
    case 'content':
      // 优先使用 delta，如果没有则使用 content（兼容后端格式）
      const contentDelta = event.delta || event.content || '';
      if (contentDelta) {
        callbacks.onContent(contentDelta);
      }
      break;

    case 'content_delta':
      // 🔧 新增：处理实时内容增量事件
      // 这个事件用于实时显示AI正在生成的内容
      const delta = event.delta || '';
      if (delta) {
        callbacks.onContent(delta);
      }
      break;

    case 'thinking':
      // 优先使用 delta，如果没有则使用 thinking（兼容后端格式）
      const thinkingDelta = event.delta || event.thinking || '';
      if (thinkingDelta) {
        callbacks.onThinking(thinkingDelta);
      }
      break;

    case 'tool_input':
      // 处理 SQL 代码的流式传输
      if (event.tool_name && (event.args || event.tool_input)) {
        callbacks.onToolInput(event.tool_name, event.args || event.tool_input || '');
      }
      break;

    case 'tool_result':
      // 处理查库结果 (通常是一次性返回完整 JSON)
      if (event.data || event.tool_output) {
        callbacks.onToolResult(event.data || event.tool_output);
      }
      break;

    case 'chart_config':
      // 处理 ECharts 图表配置
      if (event.data?.echarts_option) {
        console.log('[StreamParser] Received chart config:', event.data.echarts_option);
        callbacks.onChartConfig(event.data.echarts_option);
      }
      break;

    case 'processing_step':
      // 处理AI推理步骤事件
      if (event.step) {
        console.log('[StreamParser] Received processing step:', event.step);
        // step 可能是 number 或 ProcessingStep，只传递 ProcessingStep 类型
        if (typeof event.step !== 'number') {
          callbacks.onProcessingStep(event.step);
        }
      }
      break;

    case 'step_update':
      // 🔧 处理步骤更新事件（用于更新正在进行的步骤的描述、内容预览和流式状态）
      const stepNum = typeof event.step === 'number'
        ? event.step
        : (typeof event.step === 'string' ? parseInt(event.step || '0') : 0);
      if (stepNum > 0 && callbacks.onStepUpdate) {
        const description = event.description || '';
        const contentPreview = event.content_preview || '';
        const streaming = event.streaming || false;  // 🔧 新增：传递流式输出状态
        callbacks.onStepUpdate(stepNum, description, contentPreview, streaming);
      }
      break;

    case 'error':
      const errorMsg = event.message || event.error || 'Unknown stream error';
      callbacks.onError(errorMsg);
      break;

    case 'done':
      // 通常由外层循环处理，但防止后端显式发送 done 事件
      callbacks.onDone();
      break;

    case 'connection_init':
      // 连接初始化事件，仅用于确保 SSE 连接建立，不需要处理
      console.log('[StreamParser] Connection initialized');
      break;

    default:
      console.warn('[StreamParser] Unknown event type:', event.type);
  }
}

