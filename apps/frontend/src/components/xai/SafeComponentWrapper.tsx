import React, { Suspense, ReactNode } from 'react';
import { ErrorBoundary } from './ErrorBoundary';
import { Card, CardContent } from '../ui/card';
import { Loader2, AlertTriangle } from 'lucide-react';

interface SafeComponentWrapperProps {
  children: ReactNode;
  fallback?: ReactNode;
  errorFallback?: (error: Error, reset: () => void) => ReactNode;
  loadingFallback?: ReactNode;
  componentName?: string;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

// 通用加载组件
export const LoadingFallback: React.FC<{ message?: string }> = ({
  message = '加载中...'
}) => (
  <Card className="border-blue-200 bg-blue-50">
    <CardContent className="py-8">
      <div className="flex flex-col items-center justify-center space-y-3">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <p className="text-sm text-blue-700">{message}</p>
      </div>
    </CardContent>
  </Card>
);

// 通用错误降级组件
export const ErrorFallback: React.FC<{
  error: Error;
  reset: () => void;
  componentName?: string;
}> = ({ error, reset, componentName }) => (
  <Card className="border-red-200 bg-red-50">
    <CardContent className="py-6">
      <div className="flex flex-col items-center space-y-4">
        <AlertTriangle className="h-8 w-8 text-red-500" />
        <div className="text-center">
          <h3 className="text-sm font-medium text-red-800">
            {componentName ? `${componentName} 组件` : '组件'}加载失败
          </h3>
          <p className="text-xs text-red-600 mt-1">
            {error.message || '发生了未知错误'}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={reset}
            className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            重试
          </button>
          <button
            onClick={() => window.location.reload()}
            className="px-3 py-1 text-xs border border-red-300 text-red-700 rounded hover:bg-red-100 transition-colors"
          >
            刷新页面
          </button>
        </div>
      </div>
    </CardContent>
  </Card>
);

// 安全组件包装器
export const SafeComponentWrapper: React.FC<SafeComponentWrapperProps> = ({
  children,
  fallback,
  errorFallback,
  loadingFallback = <LoadingFallback />,
  componentName,
  onError
}) => {
  const defaultErrorFallback = (error: Error, reset: () => void) => (
    <ErrorFallback error={error} reset={reset} componentName={componentName} />
  );

  return (
    <ErrorBoundary
      fallback={errorFallback || defaultErrorFallback}
      onError={onError}
      component={componentName}
    >
      <Suspense fallback={fallback || loadingFallback}>
        {children}
      </Suspense>
    </ErrorBoundary>
  );
};

// 高阶组件：为组件添加安全包装
export const withSafeWrapper = <P extends object>(
  Component: React.ComponentType<P>,
  options?: {
    componentName?: string;
    loadingFallback?: ReactNode;
    errorFallback?: (error: Error, reset: () => void) => ReactNode;
    onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  }
) => {
  const WrappedComponent = (props: P) => (
    <SafeComponentWrapper
      componentName={options?.componentName || Component.displayName || Component.name}
      loadingFallback={options?.loadingFallback}
      errorFallback={options?.errorFallback}
      onError={options?.onError}
    >
      <Component {...props} />
    </SafeComponentWrapper>
  );

  WrappedComponent.displayName = `withSafeWrapper(${Component.displayName || Component.name})`;

  return WrappedComponent;
};

// 数据获取安全的 Hook
export const useSafeAsyncData = <T,>(
  asyncFn: () => Promise<T>,
  dependencies: React.DependencyList = [],
  options?: {
    initialData?: T;
    retryCount?: number;
    retryDelay?: number;
    onError?: (error: Error) => void;
    onSuccess?: (data: T) => void;
  }
) => {
  const [data, setData] = React.useState<T | undefined>(options?.initialData);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<Error | null>(null);
  const [retryCount, setRetryCount] = React.useState(0);

  const execute = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const result = await asyncFn();

      setData(result);
      options?.onSuccess?.(result);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');

      console.error('Async data fetch error:', error);
      setError(error);
      options?.onError?.(error);

      // 自动重试逻辑
      if (retryCount < (options?.retryCount || 0)) {
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          execute();
        }, options?.retryDelay || 1000);
      }
    } finally {
      setLoading(false);
    }
  }, [asyncFn, retryCount, options]);

  React.useEffect(() => {
    execute();
  }, dependencies);

  const reset = React.useCallback(() => {
    setError(null);
    setRetryCount(0);
    setData(options?.initialData);
  }, [options?.initialData]);

  const retry = React.useCallback(() => {
    setRetryCount(0);
    execute();
  }, [execute]);

  return {
    data,
    loading,
    error,
    reset,
    retry,
    retryCount
  };
};