/**
 * # 前端统一日志工具
 *
 * ## [MODULE]
 * 前端日志系统，支持批量发送到后端、彩色控制台输出
 *
 * ## [INPUT]
 * - level: 日志级别 (debug | info | warn | error)
 * - module: 模块名称
 * - message: 日志消息
 * - context: 额外上下文信息
 *
 * ## [OUTPUT]
 * - 控制台彩色输出
 * - 批量发送到后端日志系统
 *
 * ## [LINK]
 * **上游依赖**:
 * - process.env.NEXT_PUBLIC_API_URL - 后端API地址
 *
 * **下游依赖**:
 * - 后端 /api/v1/logs/batch 端点
 *
 * **调用方**:
 * - 所有前端模块和组件
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogEntry {
  level: LogLevel
  module: string
  message: string
  timestamp: string
  context?: Record<string, unknown>
  user_id?: string
  tenant_id?: string
  stack_trace?: string
  url?: string
  component?: string
}

interface LoggerConfig {
  enabled: boolean
  minLevel: LogLevel
  consoleEnabled: boolean
  remoteEnabled: boolean
  batchSize: number
  flushInterval: number
  sendTimeout: number
}

const LogLevelPriority: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
}

const ConsoleColors = {
  debug: '#9ca3af', // gray-400
  info: '#3b82f6',  // blue-500
  warn: '#f59e0b',  // amber-500
  error: '#ef4444', // red-500
}

const ConsoleIcons = {
  debug: '🔍',
  info: 'ℹ️',
  warn: '⚠️',
  error: '❌',
}

class Logger {
  private config: LoggerConfig
  private logBuffer: LogEntry[] = []
  private flushTimer: ReturnType<typeof setInterval> | null = null
  private userId: string | null = null
  private tenantId: string | null = null
  private isSending = false

  constructor() {
    this.config = {
      enabled: process.env.NODE_ENV !== 'test',
      minLevel: process.env.NODE_ENV === 'development' ? 'debug' : 'info',
      consoleEnabled: true,
      remoteEnabled: process.env.NODE_ENV === 'production',
      batchSize: 20,
      flushInterval: 5000, // 5秒
      sendTimeout: 10000, // 10秒
    }

    // 启动定时刷新
    if (typeof window !== 'undefined') {
      this.startFlushTimer()
    }
  }

  /**
   * 设置用户ID
   */
  setUserId(userId: string): void {
    this.userId = userId
  }

  /**
   * 设置租户ID
   */
  setTenantId(tenantId: string): void {
    this.tenantId = tenantId
  }

  /**
   * 设置配置
   */
  setConfig(config: Partial<LoggerConfig>): void {
    this.config = { ...this.config, ...config }
  }

  /**
   * 记录日志
   */
  private log(
    level: LogLevel,
    module: string,
    message: string,
    context?: Record<string, unknown>
  ): void {
    if (!this.config.enabled) return

    // 检查最低日志级别
    if (LogLevelPriority[level] < LogLevelPriority[this.config.minLevel]) {
      return
    }

    const entry: LogEntry = {
      level,
      module,
      message,
      timestamp: new Date().toISOString(),
      context,
      user_id: this.userId || undefined,
      tenant_id: this.tenantId || undefined,
      url: typeof window !== 'undefined' ? window.location.href : undefined,
    }

    // 控制台输出
    if (this.config.consoleEnabled) {
      this.logToConsole(entry)
    }

    // 添加到缓冲区
    if (this.config.remoteEnabled) {
      this.logBuffer.push(entry)

      // 达到批量大小时立即发送
      if (this.logBuffer.length >= this.config.batchSize) {
        this.flush()
      }
    }
  }

  /**
   * 输出到控制台
   */
  private logToConsole(entry: LogEntry): void {
    const icon = ConsoleIcons[entry.level]
    const color = ConsoleColors[entry.level]
    const prefix = `%c[${icon} ${entry.module}]`

    const styles = [
      `color: ${color}`,
      'font-weight: bold',
      'font-size: 12px',
    ].join(';')

    const contextStr = entry.context ? `\n  Context: ${JSON.stringify(entry.context, null, 2)}` : ''

    switch (entry.level) {
      case 'debug':
        console.debug(prefix, styles, entry.message, contextStr)
        break
      case 'info':
        console.info(prefix, styles, entry.message, contextStr)
        break
      case 'warn':
        console.warn(prefix, styles, entry.message, contextStr)
        break
      case 'error':
        console.error(prefix, styles, entry.message, contextStr)
        if (entry.stack_trace) {
          console.error('  Stack:', entry.stack_trace)
        }
        break
    }
  }

  /**
   * 启动定时刷新
   */
  private startFlushTimer(): void {
    if (this.flushTimer) return

    this.flushTimer = setInterval(() => {
      if (this.logBuffer.length > 0) {
        this.flush()
      }
    }, this.config.flushInterval)
  }

  /**
   * 停止定时刷新
   */
  private stopFlushTimer(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer)
      this.flushTimer = null
    }
  }

  /**
   * 发送日志到后端
   */
  private async flush(): Promise<void> {
    if (this.logBuffer.length === 0 || this.isSending) return

    this.isSending = true
    const logsToSend = [...this.logBuffer]
    this.logBuffer = []

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), this.config.sendTimeout)

      const response = await fetch(`${apiUrl}/logs/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          logs: logsToSend,
          user_id: this.userId,
          tenant_id: this.tenantId,
        }),
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        // 发送失败，重新加入缓冲区
        this.logBuffer.unshift(...logsToSend)
      }
    } catch (error) {
      // 发送失败，重新加入缓冲区
      this.logBuffer.unshift(...logsToSend)

      if (process.env.NODE_ENV === 'development') {
        console.warn('[Logger] Failed to send logs to backend:', error)
      }
    } finally {
      this.isSending = false
    }
  }

  /**
   * 强制刷新缓冲区
   */
  async forceFlush(): Promise<void> {
    await this.flush()
  }

  /**
   * 清空缓冲区
   */
  clear(): void {
    this.logBuffer = []
  }

  /**
   * 销毁日志器
   */
  destroy(): void {
    this.stopFlushTimer()
    this.forceFlush()
  }

  // ========== 公共日志方法 ==========

  debug(module: string, message: string, context?: Record<string, unknown>): void {
    this.log('debug', module, message, context)
  }

  info(module: string, message: string, context?: Record<string, unknown>): void {
    this.log('info', module, message, context)
  }

  warn(module: string, message: string, context?: Record<string, unknown>): void {
    this.log('warn', module, message, context)
  }

  error(module: string, message: string, error?: Error | unknown, context?: Record<string, unknown>): void {
    let errorContext = context
    let stackTrace: string | undefined

    if (error instanceof Error) {
      stackTrace = error.stack
      errorContext = {
        ...context,
        error_name: error.name,
        error_message: error.message,
      }
    } else if (error) {
      errorContext = {
        ...context,
        error: String(error),
      }
    }

    this.log('error', module, message, errorContext)

    // 记录最后一个错误的堆栈
    if (stackTrace) {
      const lastEntry = this.logBuffer[this.logBuffer.length - 1]
      if (lastEntry) {
        lastEntry.stack_trace = stackTrace
      }
    }
  }

  // ========== 组件专用方法 ==========

  /**
   * 组件挂载日志
   */
  componentMount(componentName: string, props?: Record<string, unknown>): void {
    this.debug('ComponentMount', `${componentName} mounted`, props)
  }

  /**
   * 组件卸载日志
   */
  componentUnmount(componentName: string): void {
    this.debug('ComponentUnmount', `${componentName} unmounted`)
  }

  /**
   * 组件更新日志
   */
  componentUpdate(componentName: string, changes?: Record<string, unknown>): void {
    this.debug('ComponentUpdate', `${componentName} updated`, changes)
  }

  /**
   * API请求日志
   */
  apiRequest(method: string, url: string, body?: unknown): void {
    this.debug('ApiRequest', `${method} ${url}`, body ? { body } : undefined)
  }

  /**
   * API响应日志
   */
  apiResponse(method: string, url: string, status: number, duration: number): void {
    this.info('ApiResponse', `${method} ${url} - ${status} (${duration}ms)`, {
      method,
      url,
      status,
      duration_ms: duration,
    })
  }

  /**
   * API错误日志
   */
  apiError(method: string, url: string, error: Error | unknown): void {
    this.error('ApiError', `${method} ${url} failed`, error)
  }

  // ========== 性能监控方法 ==========

  /**
   * 开始性能计时
   */
  startTimer(operationName: string): () => void {
    const startTime = performance.now()
    this.debug('Performance', `Started: ${operationName}`)

    return () => {
      const duration = performance.now() - startTime
      this.info('Performance', `Completed: ${operationName} (${duration.toFixed(2)}ms)`, {
        operation: operationName,
        duration_ms: duration,
      })
    }
  }
}

// 创建全局实例
const logger = new Logger()

// 页面卸载时发送剩余日志
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    logger.forceFlush()
  })

  // 页面隐藏时发送日志（提高可靠性）
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      navigator.sendBeacon(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004/api/v1'}/logs/batch`,
        JSON.stringify({
          logs: (logger as any).logBuffer,
          user_id: (logger as any).userId,
          tenant_id: (logger as any).tenantId,
        })
      )
    }
  })
}

export default logger

// 导出类型
export type { LogLevel, LogEntry, LoggerConfig }
