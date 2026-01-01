/**
 * # [HOME_PAGE] 应用主页组件
 *
 * ## [MODULE]
 * **文件名**: page.tsx
 * **职责**: Data Agent V4应用主页 - 欢迎页面和功能导航卡片
 * **作者**: Data Agent Team
 * **版本**: 1.0.0
 *
 * ## [INPUT]
 * - 无Props（页面组件）
 *
 * ## [OUTPUT]
 * UI组件:
 * - **欢迎标题**: 显示应用名称和简介
 * - **功能卡片**:
 *   - 数据源管理 - 连接和管理各种数据源
 *   - AI智能分析 - 使用AI技术分析数据
 *   - 文档管理 - 上传和管理文档
 *   - 聊天助手 - AI对话式数据分析
 * - **导航按钮**: 跳转到各功能页面
 *
 * ## [LINK]
 * **上游依赖**:
 * - [../../components/ui/button.tsx](../../components/ui/button.tsx) - 按钮组件
 * - [../../components/ui/card.tsx](../../components/ui/card.tsx) - 卡片组件
 *
 * **下游依赖**:
 * - 无（页面组件是叶子节点）
 *
 * **调用方**:
 * - Next.js路由系统 (/app路径)
 *
 * ## [STATE]
 * - 无（纯展示组件）
 *
 * ## [SIDE-EFFECTS]
 * - 无（纯展示组件）
 */

'use client'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function HomePage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">欢迎使用 Data Agent V4</h1>
          <p className="text-muted-foreground">
            多租户 SaaS 数据智能平台 - 让数据工作更智能
          </p>
        </div>
        <Button>开始使用</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              📊 数据源管理
            </CardTitle>
            <CardDescription>
              连接和管理您的各种数据源
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              支持数据库、API、文件等多种数据源类型
            </p>
            <Button variant="outline" className="w-full">
              管理数据源
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              🤖 AI 智能分析
            </CardTitle>
            <CardDescription>
              使用 AI 技术分析您的数据
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              自动生成数据洞察和分析报告
            </p>
            <Button variant="outline" className="w-full" asChild>
              <a href="/chat-simple">开始分析</a>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              📈 可视化仪表板
            </CardTitle>
            <CardDescription>
              实时监控您的业务指标
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              自定义仪表板和实时数据展示
            </p>
            <Button variant="outline" className="w-full">
              查看仪表板
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>最近活动</CardTitle>
            <CardDescription>
              您最近的操作和系统活动
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center gap-4 p-3 rounded-lg bg-muted/50">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">数据源连接成功</p>
                  <p className="text-xs text-muted-foreground">MySQL 生产数据库</p>
                </div>
                <span className="text-xs text-muted-foreground">2分钟前</span>
              </div>
              <div className="flex items-center gap-4 p-3 rounded-lg bg-muted/50">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">AI 分析完成</p>
                  <p className="text-xs text-muted-foreground">销售数据趋势分析</p>
                </div>
                <span className="text-xs text-muted-foreground">15分钟前</span>
              </div>
              <div className="flex items-center gap-4 p-3 rounded-lg bg-muted/50">
                <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">报告生成中</p>
                  <p className="text-xs text-muted-foreground">月度业务分析报告</p>
                </div>
                <span className="text-xs text-muted-foreground">1小时前</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>快速开始</CardTitle>
            <CardDescription>
              快速上手指南和常用功能
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="p-4 rounded-lg border border-border">
                <h4 className="font-medium mb-2">1. 连接数据源</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  添加您的第一个数据源开始分析
                </p>
                <Button size="sm" className="w-full">
                  添加数据源
                </Button>
              </div>
              <div className="p-4 rounded-lg border border-border">
                <h4 className="font-medium mb-2">2. 创建分析</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  使用 AI 助手分析您的数据
                </p>
                <Button size="sm" variant="outline" className="w-full">
                  开始分析
                </Button>
              </div>
              <div className="p-4 rounded-lg border border-border">
                <h4 className="font-medium mb-2">3. 查看文档</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  了解更多高级功能和用法
                </p>
                <Button size="sm" variant="outline" className="w-full">
                  查看文档
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}