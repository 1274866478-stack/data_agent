# Data Agent V4 - UX 优化实施指南

## 概述

本文档记录了基于 UI/UX Pro Max 技能指南实施的前端优化，旨在提升 Data Agent V4 的用户体验和可访问性。

---

## 设计系统更新

### 字体系统

| 用途 | 字体 | Google Fonts |
|------|------|--------------|
| 正文 | Fira Sans | [链接](https://fonts.google.com/share?selection?family=Fira+Sans:wght@300;400;500;600;700) |
| 代码/数据 | Fira Code | [链接](https://fonts.google.com/share?selection?family=Fira+Code:wght@400;500;600) |

**配置位置**:
- `frontend/src/app/layout.tsx:45-64` - 字体变量定义
- `frontend/src/app/globals.css:6` - 字体引入

### 配色方案

```
主色调 (Primary):   #3B82F6 (蓝色)
强调色 (Accent):     #F97316 (橙色 - CTA)
背景 (Light):        #F8FAFC
背景 (Dark):         #0F172A
文字 (Light):        #1E293B
文字 (Dark):         #F8FAFC
```

**配置位置**:
- `frontend/tailwind.config.js:11-68` - 主题颜色定义
- `frontend/src/app/globals.css:10-40` - CSS 变量

---

## 性能优化

### 1. Next.js 15 缓存策略

**文件**: `frontend/src/lib/fetch-cache.ts`

```typescript
// 静态数据缓存
import { cachedFetch, noStoreFetch, apiCacheConfig } from '@/lib/fetch-cache'

// 使用示例
const settings = await cachedFetch('/api/settings')
const liveData = await noStoreFetch('/api/analytics/live')
```

### 2. Bundle 分析

**配置**: `frontend/next.config.js:2-4`

```bash
# 运行分析
ANALYZE=true npm run build
```

### 3. 变量字体

使用 Fira Sans 和 Fira Code 的变量字体，减少加载大小。

---

## 组件库

### 新增组件

| 组件 | 文件 | 用途 |
|------|------|------|
| Skeleton | `components/ui/skeleton.tsx` | 骨架屏加载状态 |
| Tooltip | `components/ui/tooltip.tsx` | 工具提示 |
| EnhancedButton | `components/ui/button-enhanced.tsx` | 增强可访问性按钮 |
| ResponsiveContainer | `components/layout/ResponsiveContainer.tsx` | 响应式布局容器 |

---

## 可访问性改进

### 1. ARIA 支持

**文件**: `frontend/src/lib/accessibility.ts`

```typescript
import {
  useReducedMotion,
  useFocusTrap,
  checkColorContrast,
  ariaProps
} from '@/lib/accessibility'
```

### 2. 焦点状态

所有交互元素具有清晰的焦点环：

```css
*:focus-visible {
  outline: none;
  ring: 2px;
  ring-color: var(--ring);
}
```

### 3. 键盘导航

- Tab 顺序匹配视觉顺序
- Enter/Space 触发按钮
- Escape 关闭模态框
- 箭头键导航列表

### 4. 屏幕阅读器

```tsx
<span className="sr-only">屏幕阅读器专用文本</span>
<a href="#main" className="skip-to-content">跳到主内容</a>
```

---

## UX 改进

### 1. 触摸目标

所有交互元素最小尺寸 44x44px：

```css
.btn-primary {
  min-height: 44px;
  min-width: 44px;
}
```

### 2. 动画时长

遵循 150-300ms 微交互原则：

```typescript
duration: {
  instant: '100ms',
  fast: '150ms',    // 推荐
  normal: '200ms',  // 推荐
  slow: '250ms',    // 推荐
  slower: '300ms',  // 最大值
}
```

### 3. 过渡效果

使用 `transition-all duration-200` 实现平滑过渡。

### 4. 加载状态

骨架屏替代传统 spinner：

```tsx
import { SkeletonCard, SkeletonTable, SkeletonChart } from '@/components/ui/skeleton'

<SkeletonCard showAvatar lines={3} />
<SkeletonTable rows={5} cols={4} />
<SkeletonChart type="bar" />
```

---

## 响应式断点

| 断点 | 屏幕宽度 | 使用场景 |
|------|----------|----------|
| sm | 640px | 大手机 |
| md | 768px | 平板 |
| lg | 1024px | 桌面 |
| xl | 1280px | 大桌面 |
| 2xl | 1536px | 超宽屏 |

**测试设备**:
- 375px (iPhone SE)
- 768px (iPad)
- 1024px (桌面)
- 1440px (大屏)

---

## 设计令牌

**文件**: `frontend/src/lib/design-tokens.ts`

```typescript
import { tokens } from '@/lib/design-tokens'

// 使用示例
const primaryColor = tokens.colors.primary.main
const fastDuration = tokens.duration.fast
```

---

## 预交付检查清单

### 视觉质量
- [ ] 无 emoji 图标 (使用 SVG)
- [ ] 所有图标来自一致图标集 (Lucide)
- [ ] Hover 状态不引起布局抖动
- [ ] 使用主题颜色 (bg-primary) 非 var() 包装

### 交互
- [ ] 所有可点击元素有 `cursor-pointer`
- [ ] Hover 状态提供视觉反馈
- [ ] 过渡平滑 (150-300ms)
- [ ] 焦点状态可见

### 明暗模式
- [ ] 明亮模式文字对比度 4.5:1+
- [ ] 玻璃/透明元素在明亮模式可见
- [ ] 边框在两种模式都可见
- [ ] 测试两种模式

### 布局
- [ ] 浮动元素有适当边距
- [ ] 内容不被固定导航栏隐藏
- [ ] 响应式测试: 375px, 768px, 1024px, 1440px
- [ ] 移动端无横向滚动

### 可访问性
- [ ] 所有图片有 alt 文本
- [ ] 表单输入有 label
- [ ] 颜色非唯一指示器
- [ ] 尊重 `prefers-reduced-motion`

---

## 依赖包

```json
{
  "dependencies": {
    "@next/bundle-analyzer": "^15.0.0",
    "@radix-ui/react-tooltip": "^1.0.0",
    "class-variance-authority": "^0.7.0"
  }
}
```

**安装命令**:
```bash
cd frontend
npm install @next/bundle-analyzer @radix-ui/react-tooltip class-variance-authority
```

---

## 使用示例

### 1. 创建响应式卡片

```tsx
import { ResponsiveContainer, ResponsiveGrid } from '@/components/layout/ResponsiveContainer'
import { Card } from '@/components/ui/card'

function Dashboard() {
  return (
    <ResponsiveContainer>
      <ResponsiveGrid cols={{ mobile: 1, tablet: 2, desktop: 4 }}>
        <Card>...</Card>
        <Card>...</Card>
        <Card>...</Card>
        <Card>...</Card>
      </ResponsiveGrid>
    </ResponsiveContainer>
  )
}
```

### 2. 使用骨架屏

```tsx
import { SkeletonCard } from '@/components/ui/skeleton'

function LoadingState() {
  return (
    <div className="space-y-4">
      <SkeletonCard showAvatar lines={3} />
      <SkeletonCard showAvatar lines={2} />
    </div>
  )
}
```

### 3. 增强按钮

```tsx
import { EnhancedButton, IconButton } from '@/components/ui/button-enhanced'
import { HelpCircle } from 'lucide-react'

function Actions() {
  return (
    <div className="flex gap-2">
      <EnhancedButton
        variant="accent"
        loading={isLoading}
        leftIcon={<Plus />}
      >
        创建
      </EnhancedButton>
      <IconButton
        icon={<HelpCircle />}
        aria-label="帮助"
        variant="ghost"
      />
    </div>
  )
}
```

---

## 文件清单

### 新增文件
- `frontend/src/lib/design-tokens.ts` - 设计令牌
- `frontend/src/lib/fetch-cache.ts` - 缓存策略
- `frontend/src/lib/accessibility.ts` - 可访问性工具
- `frontend/src/components/ui/skeleton.tsx` - 骨架屏
- `frontend/src/components/ui/tooltip.tsx` - 工具提示
- `frontend/src/components/ui/button-enhanced.tsx` - 增强按钮
- `frontend/src/components/layout/ResponsiveContainer.tsx` - 响应式容器

### 修改文件
- `frontend/src/app/layout.tsx` - 字体更新
- `frontend/tailwind.config.js` - 主题颜色和动画
- `frontend/next.config.js` - Bundle 分析配置
- `frontend/src/app/globals.css` - 全局样式和可访问性

---

## 资源链接

- [UI/UX Pro Max 技能指南](../../.claude/skills/ui-ux-pro-max/SKILL.md)
- [Fira Fonts](https://fonts.google.com/specimen/Fira+Sans)
- [WCAG 2.1 标准](https://www.w3.org/WAI/WCAG21/quickref/)
- [Next.js 15 文档](https://nextjs.org/docs)
