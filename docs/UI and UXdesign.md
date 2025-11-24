# ChatBI UI/UX 设计规范 (V2.0)

## 系统概述
本文档定义了ChatBI用户界面的设计系统，基于shadcn/ui组件库和Tailwind CSS构建。所有UI组件必须遵循此规范以确保视觉一致性和用户体验的统一性。

## 核心原则

### 1. 基于shadcn/ui组件库
- 优先使用shadcn/ui提供的组件
- 在shadcn/ui基础上进行主题定制
- 保持组件的原生功能和可访问性

### 2. 响应式设计
- 移动优先的设计方法
- 支持桌面、平板、手机三种断点
- 确保跨设备的一致性体验

### 3. 可访问性优先
- 符合WCAG 2.1 AA标准
- 支持键盘导航和屏幕阅读器
- 提供充分的颜色对比度

## 1.0 🎨 设计令牌 (Design Tokens)

### 1.1 核心颜色系统 (基于HSL颜色空间)

#### 浅色主题 (Light Theme)
```css
:root {
  /* 基础色彩 */
  --background: 0 0% 100%;           /* 主背景色 */
  --foreground: 0 0% 0%;             /* 主文本色 */

  /* 卡片和弹出层 */
  --card: 0 0% 97%;                  /* 卡片背景 */
  --card-foreground: 0 0% 0%;        /* 卡片文本 */
  --popover: 0 0% 100%;              /* 弹出层背景 */
  --popover-foreground: 0 0% 0%;     /* 弹出层文本 */

  /* 主要操作色 */
  --primary: 0 0% 0%;                /* 主要按钮背景 */
  --primary-foreground: 0 0% 100%;   /* 主要按钮文本 */

  /* 次要操作色 */
  --secondary: 0 0% 40%;             /* 次要按钮背景 */
  --secondary-foreground: 0 0% 100%; /* 次要按钮文本 */

  /* 静态元素 */
  --muted: 0 0% 96%;                 /* 静态背景 */
  --muted-foreground: 0 0% 40%;      /* 静态文本 */

  /* 强调色 */
  --accent: 0 100% 67%;              /* 强调按钮背景 */
  --accent-foreground: 0 0% 100%;    /* 强调按钮文本 */

  /* 状态颜色 */
  --destructive: 0 84% 60%;          /* 危险操作 */
  --destructive-foreground: 0 0% 100%;

  /* 边框和输入 */
  --border: 0 0% 90%;                /* 边框颜色 */
  --input: 0 0% 90%;                 /* 输入框边框 */
  --ring: 0 0% 0%;                   /* 焦点环颜色 */

  /* 圆角 */
  --radius: 0.5rem;                  /* 默认圆角 */
}
```

#### 深色主题 (Dark Theme)
```css
.dark {
  --background: 0 0% 0%;
  --foreground: 0 0% 100%;
  --card: 0 0% 0%;
  --card-foreground: 0 0% 100%;
  --popover: 0 0% 0%;
  --popover-foreground: 0 0% 100%;
  --primary: 0 0% 100%;
  --primary-foreground: 0 0% 0%;
  --secondary: 0 0% 26%;
  --secondary-foreground: 0 0% 100%;
  --muted: 0 0% 15%;
  --muted-foreground: 0 0% 64%;
  --accent: 0 100% 67%;
  --accent-foreground: 0 0% 100%;
  --destructive: 0 62% 30%;
  --destructive-foreground: 0 0% 100%;
  --border: 0 0% 26%;
  --input: 0 0% 26%;
  --ring: 0 0% 100%;
}
```

### 1.2 Curator特定颜色
```css
:root {
  /* Curator主题色 */
  --curator-primary: #000000;        /* 主要品牌色 */
  --curator-secondary: #666666;      /* 次要文本色 */
  --curator-accent: #FF6B6B;         /* 强调色 */
  --curator-background: #FFFFFF;     /* 背景色 */
  --curator-surface: #F8F9FA;        /* 表面色 */
}
```

### 1.3 间距系统
基于Tailwind CSS的间距系统：
- `spacing-1`: 4px (0.25rem)
- `spacing-2`: 8px (0.5rem)
- `spacing-3`: 12px (0.75rem)
- `spacing-4`: 16px (1rem)
- `spacing-5`: 20px (1.25rem)
- `spacing-6`: 24px (1.5rem)
- `spacing-8`: 32px (2rem)

### 1.4 字体系统
```css
body {
  font-family: 'Inter', system-ui, sans-serif;
  line-height: 1.6;
}
```

## 2.0 🏗️ 布局系统

### 2.1 响应式断点
- **Mobile**: < 768px
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

### 2.2 主要布局结构
```
┌─────────────────────────────────────────┐
│              Header                     │
├─────────────────────────────────────────┤
│ [Sidebar] │        Main Content        │
│   240px   │         Flexible           │
├─────────────────────────────────────────┤
│              Footer                     │
└─────────────────────────────────────────┘
```

## 3.0 🧩 组件规范 (shadcn/ui)

### 3.1 按钮 (Button)
基于shadcn/ui的Button组件，支持以下变体：

#### 主要按钮 (Primary)
```tsx
<Button>主要操作</Button>
```

#### 次要按钮 (Secondary)
```tsx
<Button variant="secondary">次要操作</Button>
```

#### 轮廓按钮 (Outline)
```tsx
<Button variant="outline">轮廓按钮</Button>
```

#### 幽灵按钮 (Ghost)
```tsx
<Button variant="ghost">幽灵按钮</Button>
```

### 3.2 卡片 (Card)
```tsx
<Card>
  <CardHeader>
    <CardTitle>卡片标题</CardTitle>
    <CardDescription>卡片描述</CardDescription>
  </CardHeader>
  <CardContent>
    卡片内容
  </CardContent>
</Card>
```

### 3.3 徽章 (Badge)
```tsx
<Badge variant="default">默认徽章</Badge>
<Badge variant="secondary">次要徽章</Badge>
<Badge variant="destructive">危险徽章</Badge>
<Badge variant="outline">轮廓徽章</Badge>
```

### 3.4 输入框 (Input)
```tsx
<Input type="text" placeholder="请输入内容" />
```

### 3.5 警告框 (Alert)
```tsx
<Alert>
  <AlertTitle>警告标题</AlertTitle>
  <AlertDescription>警告描述内容</AlertDescription>
</Alert>
```

## 4.0 交互与UX规则

### 4.1 状态管理
- **Loading状态**: 使用loading spinner或skeleton组件
- **Error状态**: 使用Alert组件显示错误信息
- **Success状态**: 使用成功色徽章或Alert显示

### 4.2 动画效果
使用Tailwind CSS的transition类：
- `transition-colors`: 颜色变化
- `transition-transform`: 变换效果
- `transition-all`: 所有属性变化
- `duration-200`: 200ms动画时长

### 4.3 悬停效果
```tsx
<Button className="hover:scale-105 transition-transform">
  悬停放大
</Button>
```

## 5.0 🔧 技术实现

### 5.1 核心技术栈
- **框架**: React 18 + Next.js 14
- **语言**: TypeScript
- **样式**: Tailwind CSS + shadcn/ui
- **图标**: Lucide React
- **状态管理**: Zustand

### 5.2 工具函数
```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### 5.3 组件示例
```tsx
import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface DataOverviewCardProps {
  title: string;
  value: string | number;
  description?: string;
  trend?: number;
  className?: string;
}

export function DataOverviewCard({
  title,
  value,
  description,
  trend,
  className
}: DataOverviewCardProps) {
  return (
    <Card className={cn("hover:shadow-md transition-shadow cursor-pointer", className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {trend !== undefined && (
          <Badge variant={trend > 0 ? "default" : "secondary"}>
            {trend > 0 ? '+' : ''}{trend}%
          </Badge>
        )}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </CardContent>
    </Card>
  );
}
```

## 6.0 📱 移动端适配

### 6.1 响应式类名
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  {/* 响应式网格布局 */}
</div>
```

### 6.2 移动端导航
- 使用Drawer组件替代侧边栏
- 简化操作按钮
- 优化触摸交互区域

## 7.0 🎯 特定组件实现

### 7.1 数据源概览卡片
基于`DataSourceOverview.tsx`的实现模式：
- 使用Card组件作为容器
- 集成状态徽章和进度条
- 提供操作按钮和刷新功能
- 支持错误状态和加载状态

### 7.2 聊天界面
- 消息气泡使用Card组件
- 输入框使用Input和Button组合
- 支持Markdown渲染
- 实现消息历史记录

### 7.3 表单组件
- 使用shadcn/ui的Form组件
- 集成验证和错误处理
- 支持多种输入类型
- 提供清晰的标签和帮助文本

## 8.0 🚀 性能优化

### 8.1 代码分割
- 使用动态导入加载组件
- 实现路由级别的代码分割
- 优化Bundle大小

### 8.2 图片优化
- 使用Next.js Image组件
- 实现懒加载
- 提供多种尺寸适配

### 8.3 缓存策略
- 组件级别的React.memo
- 使用useMemo和useCallback
- 实现虚拟滚动

## 9.0 📋 设计检查清单

在开发新组件时，请对照以下清单：

- [ ] 是否使用shadcn/ui组件作为基础？
- [ ] 是否遵循了颜色系统的CSS变量？
- [ ] 是否支持响应式设计？
- [ ] 是否实现了适当的悬停和焦点状态？
- [ ] 是否通过可访问性检查？
- [ ] 是否支持深色模式？
- [ ] 是否使用了cn()函数合并类名？
- [ ] 是否提供适当的loading和error状态？

## 10.0 🔍 未来规划

### 10.1 主题扩展
- 支持自定义主题色彩
- 提供更多预设主题
- 实现主题切换动画

### 10.2 组件增强
- 添加更多业务特定组件
- 优化移动端体验
- 实现更多动画效果

### 10.3 开发工具
- 设计令牌生成器
- 组件预览工具
- 自动化设计检查

---

**文档版本**: 2.0
**最后更新**: 2025-11-16
**维护者**: ChatBI开发团队
**状态**: ✅ 已与实际代码对齐