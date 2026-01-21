# Intelligence Flow Dashboard UI/UX 风格迁移计划

本计划旨在将 Intelligence Flow Dashboard 的设计风格（Tiffany Blue 配色 + 现代化布局）应用到 Data Agent V4 前端项目中。

## 核心决策
1.  **全局配色**：采用 Tiffany Blue (`#81d8cf`) 作为主色调，替换原有的蓝色系。
2.  **布局策略**：三栏式布局（Left Context / Center Chat / Right Insights）**仅应用于 AI 助手页面** (`/ai-assistant`)，其他页面保持现有布局或做适配性调整。
3.  **风格目标**：实现"零幻觉"的专业数据分析工具外观，强调清晰度、现代感和微交互。

## 实施阶段

### Phase 1: 设计系统更新 (P0)
**目标**：确立新的色彩系统和排版基础。
- [ ] **Tailwind 配置**：在 `tailwind.config.js` 中引入 `tiffany` 色系。
- [ ] **CSS 变量**：更新 `globals.css` 中的 `--primary`, `--secondary` 等核心变量。
- [ ] **字体与排版**：引入 `Inter` 和 `JetBrains Mono`（如需），优化字体渲染。
- [ ] **动画库**：添加 `pulse-slow`, `shimmer` 等自定义动画 class。

### Phase 2: 布局组件重构 (P0)
**目标**：实现页面特定的三栏布局，同时保持全局导航的兼容性。
- [ ] **Header 组件**：
    - 更新 Logo 区域设计。
    - 集成搜索栏和系统状态指示器（参考设计）。
    - 优化右侧工具栏样式。
- [ ] **ThreeColumnLayout 组件**：
    - 新建 `src/components/layout/ThreeColumnLayout.tsx`。
    - 实现 Left (3/12), Center (5/12), Right (4/12) 的 Grid 布局。
    - 仅在 AI 助手页面使用此布局容器。

### Phase 3: 核心 UI 组件升级 (P1)
**目标**：开发符合新风格的原子组件。
- [ ] **ContextCard** (`src/components/ui/context-card.tsx`)：
    - 用于左侧栏，展示数据库、文件等上下文。
    - 特性：左侧重音色条、Hover 阴影、详细元数据展示。
- [ ] **SchemaMapDisplay** (`src/components/ui/schema-map-display.tsx`)：
    - 可视化展示表结构关联。
- [ ] **ProcessingSteps** (`src/components/chat/ProcessingSteps.tsx`)：
    - **重构**：从卡片式改为垂直时间线样式。
    - 增加脉冲动画连接线，提升"处理中"的视觉反馈。
- [ ] **StatCard & InsightPanel**：
    - 更新统计卡片样式，支持 Tiffany 风格渐变。

### Phase 4: AI 助手页面重构 (P1)
**目标**：组装新组件，完成核心页面的转型。
- [ ] **页面入口** (`src/app/(app)/ai-assistant/page.tsx`)：
    - 应用 `ThreeColumnLayout`。
    - 左侧放置 `ContextCard` 列表和 `SchemaMapDisplay`。
    - 中间放置对话流和输入框（卡片浮动样式）。
    - 右侧放置 `InsightPanel` 和可视化图表。
- [ ] **输入区域优化**：
    - 浮动阴影风格，集成快捷操作按钮。

### Phase 5: 细节打磨 (P2)
**目标**：提升质感和一致性。
- [ ] **暗色模式适配**：确保 Tiffany Blue 在深色背景下的对比度和舒适度。
- [ ] **微交互**：按钮点击反馈、卡片 Hover 上浮、加载状态动画。
- [ ] **滚动条美化**：全局细滚动条样式。

## 验证计划
1.  **视觉回归测试**：对比新旧页面，确保除了设计变更外无布局崩坏。
2.  **功能测试**：AI 对话流、图表渲染、暗色模式切换正常。
3.  **响应式测试**：在移动端回退到单栏或兼容布局。
