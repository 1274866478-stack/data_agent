# ErrorBoundary 组件文档

## 概述

`ErrorBoundary` 是一个React错误边界组件,用于捕获组件树中的JavaScript错误,防止整个应用崩溃,并显示友好的错误界面。

---

## 功能特性

- ✅ 捕获子组件树中的JavaScript错误
- ✅ 显示友好的错误UI
- ✅ 开发环境显示详细错误信息
- ✅ 支持自定义错误处理函数
- ✅ 支持自定义fallback UI
- ✅ 提供重试和返回首页功能
- ✅ 预留错误监控集成接口

---

## 使用方法

### 基础用法

```tsx
import ErrorBoundary from '@/components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <YourComponent />
    </ErrorBoundary>
  );
}
```

### 自定义错误处理

```tsx
import ErrorBoundary from '@/components/ErrorBoundary';

const handleError = (error: Error, errorInfo: ErrorInfo) => {
  // 发送到错误监控服务
  console.error('Error caught:', error, errorInfo);
  
  // 发送到Sentry
  // Sentry.captureException(error, { contexts: { react: errorInfo } });
};

function App() {
  return (
    <ErrorBoundary onError={handleError}>
      <YourComponent />
    </ErrorBoundary>
  );
}
```

### 自定义Fallback UI

```tsx
import ErrorBoundary from '@/components/ErrorBoundary';

const CustomFallback = (
  <div className="error-container">
    <h1>自定义错误页面</h1>
    <p>请稍后再试</p>
  </div>
);

function App() {
  return (
    <ErrorBoundary fallback={CustomFallback}>
      <YourComponent />
    </ErrorBoundary>
  );
}
```

### 嵌套使用

```tsx
import ErrorBoundary from '@/components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <Header />
      <ErrorBoundary>
        <Sidebar />
      </ErrorBoundary>
      <ErrorBoundary>
        <MainContent />
      </ErrorBoundary>
      <Footer />
    </ErrorBoundary>
  );
}
```

---

## Props

| 属性 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|--------|------|
| `children` | `ReactNode` | ✅ | - | 子组件 |
| `fallback` | `ReactNode` | ❌ | 默认错误UI | 自定义错误UI |
| `onError` | `(error: Error, errorInfo: ErrorInfo) => void` | ❌ | - | 错误处理回调 |

---

## 最佳实践

### 1. 在应用根部使用

```tsx
// src/app/layout.tsx
import ErrorBoundary from '@/components/ErrorBoundary';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <ErrorBoundary>
          {children}
        </ErrorBoundary>
      </body>
    </html>
  );
}
```

### 2. 为关键功能模块单独设置

```tsx
// src/app/dashboard/page.tsx
import ErrorBoundary from '@/components/ErrorBoundary';

export default function DashboardPage() {
  return (
    <div>
      <ErrorBoundary>
        <CriticalDataDisplay />
      </ErrorBoundary>
      
      <ErrorBoundary>
        <UserActions />
      </ErrorBoundary>
    </div>
  );
}
```

### 3. 集成错误监控

```tsx
// src/lib/errorTracking.ts
import * as Sentry from '@sentry/react';

export const reportError = (error: Error, errorInfo: ErrorInfo) => {
  if (process.env.NODE_ENV === 'production') {
    Sentry.captureException(error, {
      contexts: {
        react: {
          componentStack: errorInfo.componentStack,
        },
      },
    });
  }
};

// 使用
<ErrorBoundary onError={reportError}>
  <App />
</ErrorBoundary>
```

---

## 注意事项

### ErrorBoundary无法捕获的错误

- ❌ 事件处理器中的错误 (使用try-catch)
- ❌ 异步代码中的错误 (使用try-catch或Promise.catch)
- ❌ 服务端渲染错误
- ❌ ErrorBoundary自身的错误

### 事件处理器错误处理

```tsx
function MyComponent() {
  const handleClick = () => {
    try {
      // 可能出错的代码
      riskyOperation();
    } catch (error) {
      console.error('Event handler error:', error);
      // 手动处理错误
    }
  };

  return <button onClick={handleClick}>Click me</button>;
}
```

### 异步错误处理

```tsx
function MyComponent() {
  const fetchData = async () => {
    try {
      const data = await api.getData();
      setData(data);
    } catch (error) {
      console.error('Async error:', error);
      setError(error);
    }
  };

  return <button onClick={fetchData}>Fetch Data</button>;
}
```

---

## 开发环境 vs 生产环境

### 开发环境
- 显示详细错误信息
- 显示组件堆栈
- 便于调试

### 生产环境
- 显示友好错误消息
- 隐藏技术细节
- 发送错误到监控服务

---

## 相关资源

- [React Error Boundaries文档](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
- [Sentry React集成](https://docs.sentry.io/platforms/javascript/guides/react/)

---

**最后更新:** 2025-11-17

