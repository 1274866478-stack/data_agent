import React, { Component, ReactNode } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, reset: () => void) => ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  component?: string;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error(`${this.props.component || 'Component'} Error:`, error, errorInfo);

    this.setState({
      error,
      errorInfo
    });

    // 调用自定义错误处理器
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // 在生产环境中，可以发送错误到监控服务
    if (process.env.NODE_ENV === 'production') {
      this.reportError(error, errorInfo);
    }
  }

  private reportError = (error: Error, errorInfo: React.ErrorInfo) => {
    // 这里可以集成错误监控服务，如 Sentry
    try {
      // 示例：发送错误信息到监控服务
      const errorReport = {
        component: this.props.component || 'Unknown',
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'Unknown'
      };

      console.error('Error Report:', errorReport);

      // 这里可以发送到错误监控服务
      // fetch('/api/errors', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(errorReport)
      // });
    } catch (reportError) {
      console.error('Failed to report error:', reportError);
    }
  };

  private reset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义 fallback，使用它
      if (this.props.fallback && this.state.error) {
        return this.props.fallback(this.state.error, this.reset);
      }

      // 默认错误界面
      return (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-800">
              <AlertTriangle className="h-5 w-5" />
              组件出现错误
            </CardTitle>
            <CardDescription>
              {this.props.component ? `${this.props.component} 组件` : '组件'}遇到了意外错误
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="text-sm">
                <summary className="cursor-pointer font-medium text-red-700">
                  查看错误详情
                </summary>
                <div className="mt-2 p-3 bg-red-100 rounded text-red-800">
                  <div className="font-mono text-xs">
                    <div className="font-bold mb-2">错误信息:</div>
                    <div className="mb-3">{this.state.error.message}</div>

                    {this.state.error.stack && (
                      <>
                        <div className="font-bold mb-1">错误堆栈:</div>
                        <pre className="whitespace-pre-wrap text-xs overflow-auto max-h-40">
                          {this.state.error.stack}
                        </pre>
                      </>
                    )}

                    {this.state.errorInfo?.componentStack && (
                      <>
                        <div className="font-bold mb-1 mt-3">组件堆栈:</div>
                        <pre className="whitespace-pre-wrap text-xs overflow-auto max-h-40">
                          {this.state.errorInfo.componentStack}
                        </pre>
                      </>
                    )}
                  </div>
                </div>
              </details>
            )}

            <div className="flex gap-2">
              <Button onClick={this.reset} size="sm" variant="outline">
                <RefreshCw className="h-4 w-4 mr-2" />
                重试
              </Button>
              <Button
                onClick={() => window.location.reload()}
                size="sm"
                variant="ghost"
              >
                刷新页面
              </Button>
            </div>
          </CardContent>
        </Card>
      );
    }

    return this.props.children;
  }
}

// 用于函数组件的错误边界 Hook（在组件内部使用）
export const useErrorHandler = (componentName?: string) => {
  const [error, setError] = React.useState<Error | null>(null);

  const resetError = React.useCallback(() => {
    setError(null);
  }, []);

  const handleError = React.useCallback((error: Error) => {
    console.error(`${componentName || 'Component'} Error:`, error);
    setError(error);

    // 在生产环境中报告错误
    if (process.env.NODE_ENV === 'production') {
      // 这里可以添加错误报告逻辑
    }
  }, [componentName]);

  // 抛出错误让错误边界捕获
  React.useEffect(() => {
    if (error) {
      throw error;
    }
  }, [error]);

  return { handleError, resetError };
};

// 高阶组件：为组件添加错误边界
export const withErrorBoundary = <P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) => {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
};