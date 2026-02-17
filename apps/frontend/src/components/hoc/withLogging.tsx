/**
 * # 组件日志追踪 HOC
 *
 * ## [MODULE]
 * 高阶组件，为React组件添加生命周期日志追踪
 *
 * ## [INPUT]
 * - WrappedComponent: 被包装的React组件
 * - options: 日志配置选项
 *
 * ## [OUTPUT]
 * - 带有日志追踪的增强组件
 *
 * ## [LINK]
 * **上游依赖**:
 * - react - React核心库
 * - ../../lib/logger.ts - 日志工具
 *
 * **下游依赖**:
 * - 使用此HOC的所有组件
 */

import React, { ComponentType, useEffect, useRef } from 'react'
import logger from '../../lib/logger'

interface LoggingOptions {
  /**
   * 组件名称（默认使用组件显示名称）
   */
  componentName?: string

  /**
   * 是否记录props变化
   */
  logProps?: boolean

  /**
   * 是否记录挂载
   */
  logMount?: boolean

  /**
   * 是否记录卸载
   */
  logUnmount?: boolean

  /**
   * 是否记录更新
   */
  logUpdate?: boolean

  /**
   * 是否记录渲染
   */
  logRender?: boolean

  /**
   * 需要排除的props字段
   */
  excludeProps?: string[]
}

const defaultOptions: LoggingOptions = {
  logMount: true,
  logUnmount: true,
  logUpdate: false,
  logRender: false,
  logProps: true,
  excludeProps: ['dispatch', 'setState', 'updateState'],
}

/**
 * 函数组件日志追踪 Hook
 */
function useComponentLogging(
  componentName: string,
  props: Record<string, unknown>,
  options: LoggingOptions
) {
  const isFirstMount = useRef(true)
  const prevPropsRef = useRef<Record<string, unknown>>({})

  // 挂载日志
  useEffect(() => {
    if (options.logMount) {
      const safeProps = options.logProps ? filterProps(props, options.excludeProps) : undefined
      logger.componentMount(componentName, safeProps)
    }

    return () => {
      // 卸载日志
      if (options.logUnmount) {
        logger.componentUnmount(componentName)
      }
    }
    // 只在挂载时执行一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 更新日志
  useEffect(() => {
    if (!isFirstMount.current && options.logUpdate) {
      const changes = getPropChanges(prevPropsRef.current, props, options.excludeProps)
      if (Object.keys(changes).length > 0) {
        logger.componentUpdate(componentName, changes)
      }
    }

    prevPropsRef.current = { ...props }
    isFirstMount.current = false
  })

  // 渲染日志（开发环境）
  if (options.logRender && process.env.NODE_ENV === 'development') {
    logger.debug('Render', `${componentName} rendered`)
  }
}

/**
 * 过滤props字段
 */
function filterProps(
  props: Record<string, unknown>,
  exclude?: string[]
): Record<string, unknown> {
  if (!exclude || exclude.length === 0) return props

  const filtered: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(props)) {
    if (!exclude.includes(key)) {
      filtered[key] = value
    }
  }
  return filtered
}

/**
 * 获取props变化
 */
function getPropChanges(
  prevProps: Record<string, unknown>,
  nextProps: Record<string, unknown>,
  exclude?: string[]
): Record<string, { from: unknown; to: unknown }> {
  const changes: Record<string, { from: unknown; to: unknown }> = {}
  const excludeSet = new Set(exclude || [])

  const allKeys = new Set([...Object.keys(prevProps), ...Object.keys(nextProps)])

  for (const key of allKeys) {
    if (excludeSet.has(key)) continue

    const prevValue = prevProps[key]
    const nextValue = nextProps[key]

    if (prevValue !== nextValue) {
      changes[key] = {
        from: prevValue,
        to: nextValue,
      }
    }
  }

  return changes
}

/**
 * 组件日志追踪 HOC
 *
 * @example
 * ```tsx
 * // 基本用法
 * const MyComponentWithLogging = withLogging(MyComponent)
 *
 * // 带配置
 * const MyComponentWithLogging = withLogging(MyComponent, {
 *   componentName: 'MyComponent',
 *   logUpdate: true,
 *   excludeProps: ['dispatch'],
 * })
 * ```
 */
export function withLogging<P extends object>(
  WrappedComponent: ComponentType<P>,
  options: LoggingOptions = {}
): ComponentType<P> {
  const mergedOptions = { ...defaultOptions, ...options }

  function WithLoggingComponent(props: P) {
    const componentName = mergedOptions.componentName || WrappedComponent.displayName || WrappedComponent.name || 'AnonymousComponent'

    useComponentLogging(componentName, props as Record<string, unknown>, mergedOptions)

    return <WrappedComponent {...props} />
  }

  // 复制显示名称
  const wrappedName = WrappedComponent.displayName || WrappedComponent.name || 'Component'
  WithLoggingComponent.displayName = `withLogging(${wrappedName})`

  return WithLoggingComponent
}

/**
 * 类组件日志追踪装饰器（用于类组件）
 *
 * @example
 * ```tsx
 * @withClassLogging({ logUpdate: true })
 * class MyComponent extends React.Component {
 *   // ...
 * }
 * ```
 */
export function withClassLogging(options: LoggingOptions = {}) {
  return function <P extends object>(
    WrappedComponent: ComponentType<P>
  ): ComponentType<P> {
    return withLogging(WrappedComponent, options)
  }
}

/**
 * 创建带日志的自定义Hook
 *
 * @example
 * ```tsx
 * // 创建日志Hook
 * const useMyEffectWithLogging = createLoggedHook('useMyEffect', useEffect)
 *
 * // 使用日志Hook
 * useMyEffectWithLogging(() => {
 *   // ...
 * }, [deps])
 * ```
 */
export function createLoggedHook(
  hookName: string,
  hook: typeof useEffect
): typeof useEffect {
  return (effect: () => void | (() => void), deps?: React.DependencyList) => {
    logger.debug('Hook', `${hookName} called`, { deps })

    return hook(effect, deps)
  }
}

/**
 * 性能监控 HOC
 *
 * 记录组件渲染时间
 *
 * @example
 * ```tsx
 * const MyComponentWithPerf = withPerformanceMonitoring(MyComponent)
 * ```
 */
export function withPerformanceMonitoring<P extends object>(
  WrappedComponent: ComponentType<P>,
  thresholdMs: number = 100
): ComponentType<P> {
  function WithPerformanceMonitoring(props: P) {
    const componentName = WrappedComponent.displayName || WrappedComponent.name || 'AnonymousComponent'
    const renderStart = useRef<number>(performance.now())

    React.useEffect(() => {
      const renderEnd = performance.now()
      const renderTime = renderEnd - renderStart.current

      if (renderTime > thresholdMs) {
        logger.warn('Performance', `${componentName} slow render detected`, {
          component: componentName,
          render_time_ms: renderTime,
          threshold_ms: thresholdMs,
        })
      }

      renderStart.current = performance.now()
    })

    return <WrappedComponent {...props} />
  }

  const wrappedName = WrappedComponent.displayName || WrappedComponent.name || 'Component'
  WithPerformanceMonitoring.displayName = `withPerformanceMonitoring(${wrappedName})`

  return WithPerformanceMonitoring
}

/**
 * 错误边界日志追踪组件
 */
export interface LoggedErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ComponentType<{ error: Error; retry: () => void }>
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
}

interface LoggedErrorBoundaryState {
  hasError: boolean
  error?: Error
}

export class LoggedErrorBoundary extends React.Component<
  LoggedErrorBoundaryProps,
  LoggedErrorBoundaryState
> {
  constructor(props: LoggedErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): LoggedErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // 🔧 修复：添加类型检查，children 可能是字符串等基本类型
    const childrenType = this.props.children as React.ReactElement | null
    const componentType = childrenType?.type as any
    const componentName = componentType?.displayName || componentType?.name || 'UnknownComponent'

    logger.error(componentName, 'Error boundary caught an error', error, {
      componentStack: errorInfo.componentStack,
    })

    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined })
  }

  render() {
    if (this.state.hasError) {
      const Fallback = this.props.fallback

      if (Fallback) {
        return <Fallback error={this.state.error!} retry={this.handleRetry} />
      }

      return (
        <div className="p-4 border border-red-300 rounded-lg bg-red-50">
          <h3 className="text-lg font-semibold text-red-800">Something went wrong</h3>
          <p className="text-red-600">{this.state.error?.message}</p>
          <button
            onClick={this.handleRetry}
            className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

export default withLogging
