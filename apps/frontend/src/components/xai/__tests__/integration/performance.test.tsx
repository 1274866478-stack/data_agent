/**
 * XAI组件性能测试
 * 专门测试组件在大数据量下的性能表现
 */

import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { EvidenceChain, ReasoningQualityScore } from '../..'

// Mock dependencies (same as integration test)
jest.mock('@/components/ui/card', () => ({
  Card: ({ children }: { children: React.ReactNode }) => <div data-testid="card">{children}</div>,
  CardContent: ({ children }: { children: React.ReactNode }) => <div data-testid="card-content">{children}</div>,
  CardDescription: ({ children }: { children: React.ReactNode }) => <div data-testid="card-description">{children}</div>,
  CardHeader: ({ children }: { children: React.ReactNode }) => <div data-testid="card-header">{children}</div>,
  CardTitle: ({ children }: { children: React.ReactNode }) => <div data-testid="card-title">{children}</div>,
}))

jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children }: { children: React.ReactNode }) => <span data-testid="badge">{children}</span>,
}))

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick }: any) => <button onClick={onClick}>{children}</button>,
}))

jest.mock('@/components/ui/progress', () => ({
  Progress: ({ value }: { value: number }) => <div data-testid="progress" data-value={value}></div>,
}))

jest.mock('@/components/ui/tabs', () => ({
  Tabs: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs">{children}</div>,
  TabsContent: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs-content">{children}</div>,
  TabsList: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs-list">{children}</div>,
  TabsTrigger: ({ children, value }: { children: React.ReactNode; value: string }) =>
    <button data-value={value}>{children}</button>,
}))

jest.mock('@/components/ui/collapsible', () => ({
  Collapsible: ({ children }: { children: React.ReactNode }) => <div data-testid="collapsible">{children}</div>,
  CollapsibleContent: ({ children }: { children: React.ReactNode }) => <div data-testid="collapsible-content">{children}</div>,
  CollapsibleTrigger: ({ children }: { children: React.ReactNode }) => <button>{children}</button>,
}))

jest.mock('@/components/ui/alert', () => ({
  Alert: ({ children }: { children: React.ReactNode }) => <div data-testid="alert">{children}</div>,
  AlertDescription: ({ children }: { children: React.ReactNode }) => <div data-testid="alert-description">{children}</div>,
  AlertTitle: ({ children }: { children: React.ReactNode }) => <div data-testid="alert-title">{children}</div>,
}))

jest.mock('lucide-react', () => ({
  CheckCircle2: () => <div data-testid="check-circle-icon"></div>,
  AlertTriangle: () => <div data-testid="alert-triangle-icon"></div>,
  Clock: () => <div data-testid="clock-icon"></div>,
  Search: () => <div data-testid="search-icon"></div>,
  FileText: () => <div data-testid="file-text-icon"></div>,
  Database: () => <div data-testid="database-icon"></div>,
  Brain: () => <div data-testid="brain-icon"></div>,
  GitBranch: () => <div data-testid="git-branch-icon"></div>,
  ChevronDown: () => <div data-testid="chevron-down-icon"></div>,
  ChevronUp: () => <div data-testid="chevron-up-icon"></div>,
  BarChart3: () => <div data-testid="bar-chart-icon"></div>,
  Info: () => <div data-testid="info-icon"></div>,
  Link: () => <div data-testid="link-icon"></div>,
  Star: () => <div data-testid="star-icon"></div>,
  TrendingUp: () => <div data-testid="trending-up-icon"></div>,
  Award: () => <div data-testid="award-icon"></div>,
  Target: () => <div data-testid="target-icon"></div>,
  PieChart: () => <div data-testid="pie-chart-icon"></div>,
  LineChart: () => <div data-testid="line-chart-icon"></div>,
  Download: () => <div data-testid="download-icon"></div>,
  RefreshCw: () => <div data-testid="refresh-cw-icon"></div>,
  Eye: () => <div data-testid="eye-icon"></div>,
  EyeOff: () => <div data-testid="eye-off-icon"></div>,
}))

describe('XAI组件性能测试', () => {
  // 性能测试工具函数
  const generateLargeDataset = (size: number): Record<string, any> => {
    const nodes: Record<string, any> = {}

    for (let i = 0; i < size; i++) {
      const childCount = Math.floor(Math.random() * 3) // 0-2个子节点
      const childNodes = []

      for (let j = 0; j < childCount; j++) {
        const childId = `node-${size + i * 3 + j}`
        childNodes.push(childId)
      }

      nodes[`node-${i}`] = {
        id: `node-${i}`,
        source_type: ['document', 'database', 'web_search', 'llm_reasoning'][Math.floor(Math.random() * 4)],
        source_name: `数据源 ${i}`,
        content: `这是测试内容 ${i}`.repeat(10), // 更长的内容
        confidence_score: Math.random(),
        verification_status: ['verified', 'pending', 'failed'][Math.floor(Math.random() * 3)],
        timestamp: new Date(Date.now() - Math.random() * 86400000).toISOString(),
        child_nodes: childNodes,
        metadata: {
          key1: `value${i}`,
          key2: i * 2,
          key3: Math.random() > 0.5 ? 'text' : null
        }
      }
    }

    return nodes
  }

  const generateLargeChains = (size: number): any[] => {
    const chains = []

    for (let i = 0; i < size; i++) {
      chains.push({
        chain_id: `chain-${i}`,
        chain_name: `证据链 ${i}`,
        chain_type: ['linear', 'branching', 'circular'][Math.floor(Math.random() * 3)],
        description: `这是第 ${i} 个证据链的描述`.repeat(3),
        evidence_count: Math.floor(Math.random() * 20) + 1,
        verified_count: Math.floor(Math.random() * 15),
        created_at: new Date(Date.now() - Math.random() * 86400000).toISOString()
      })
    }

    return chains
  }

  beforeEach(() => {
    jest.spyOn(console, 'warn').mockImplementation(() => {})
    jest.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  describe('EvidenceChain性能测试', () => {
    it('应该在1秒内渲染1000个节点', () => {
      const largeNodes = generateLargeDataset(1000)
      const largeChains = generateLargeChains(10)

      const startTime = performance.now()

      render(
        <EvidenceChain
          chains={largeChains}
          evidenceNodes={largeNodes}
          maxNodes={50}
          maxDepth={3}
        />
      )

      const endTime = performance.now()
      const renderTime = endTime - startTime

      expect(renderTime).toBeLessThan(1000) // 1秒内完成
      expect(screen.getByText('证据链分析')).toBeInTheDocument()
    })

    it('应该正确限制显示的节点数量', () => {
      const largeNodes = generateLargeDataset(500)
      const largeChains = generateLargeChains(5)

      render(
        <EvidenceChain
          chains={largeChains}
          evidenceNodes={largeNodes}
          maxNodes={20}
        />
      )

      // 应该显示节点数量限制信息
      expect(screen.getByText(/显示限制/)).toBeInTheDocument()
      expect(screen.getByText(/前 20 个节点/)).toBeInTheDocument()
    })

    it('应该能够快速切换视图模式', () => {
      const nodes = generateLargeDataset(100)
      const chains = generateLargeChains(5)

      render(
        <EvidenceChain
          chains={chains}
          evidenceNodes={nodes}
        />
      )

      const startTime = performance.now()

      // 切换到时间线视图
      const timelineButton = screen.getByText('时间线视图')
      fireEvent.click(timelineButton)

      const endTime = performance.now()
      const switchTime = endTime - startTime

      expect(switchTime).toBeLessThan(100) // 100ms内完成切换
      expect(screen.getByText('证据链时间线')).toBeInTheDocument()
    })

    it('应该限制子节点的渲染数量', () => {
      // 创建有大量子节点的数据
      const nodes: Record<string, any> = {
        'root': {
          id: 'root',
          source_type: 'llm_reasoning',
          source_name: '根节点',
          content: '根节点内容',
          confidence_score: 0.9,
          verification_status: 'verified',
          timestamp: new Date().toISOString(),
          child_nodes: []
        }
      }

      // 添加50个子节点
      for (let i = 0; i < 50; i++) {
        nodes[`child-${i}`] = {
          id: `child-${i}`,
          source_type: 'document',
          source_name: `子节点 ${i}`,
          content: `子节点内容 ${i}`,
          confidence_score: 0.8,
          verification_status: 'verified',
          timestamp: new Date().toISOString(),
          child_nodes: []
        }
        nodes.root.child_nodes.push(`child-${i}`)
      }

      render(
        <EvidenceChain
          chains={[]}
          evidenceNodes={nodes}
        />
      )

      // 应该限制子节点显示数量
      expect(screen.getByText(/还有 .* 个子节点/)).toBeInTheDocument()
    })
  })

  describe('ReasoningQualityScore性能测试', () => {
    it('应该能够处理大量质量指标', () => {
      const largeMetrics = Array.from({ length: 100 }, (_, i) => ({
        id: `metric-${i}`,
        name: `质量指标 ${i}`,
        description: `这是第 ${i} 个质量指标的详细描述`.repeat(5),
        score: Math.random(),
        weight: Math.random(),
        category: ['accuracy', 'completeness', 'clarity', 'reliability', 'efficiency'][Math.floor(Math.random() * 5)],
        status: ['excellent', 'good', 'fair', 'poor'][Math.floor(Math.random() * 4)],
        feedback: `反馈信息 ${i}`.repeat(3),
        improvement_suggestions: [`建议 ${i}-1`, `建议 ${i}-2`]
      }))

      const startTime = performance.now()

      render(
        <ReasoningQualityScore
          query="性能测试查询"
          answer="性能测试回答"
          qualityBreakdown={{
            overall_score: 0.85,
            grade: 'A',
            grade_description: '优秀',
            metrics: largeMetrics,
            category_scores: {},
            strengths: ['优势1', '优势2'],
            weaknesses: ['劣势1'],
            improvement_areas: ['改进1'],
            confidence_level: 0.9
          }}
        />
      )

      const endTime = performance.now()
      const renderTime = endTime - startTime

      expect(renderTime).toBeLessThan(500) // 500ms内完成
      expect(screen.getByText('推理质量评分系统')).toBeInTheDocument()
    })
  })

  describe('内存使用测试', () => {
    it('应该在大量数据渲染后正常清理', () => {
      const largeNodes = generateLargeDataset(200)
      const largeChains = generateLargeChains(10)

      const { unmount } = render(
        <EvidenceChain
          chains={largeChains}
          evidenceNodes={largeNodes}
          maxNodes={50}
        />
      )

      // 执行一些操作
      const expandButtons = screen.getAllByRole('button')
      if (expandButtons.length > 0) {
        fireEvent.click(expandButtons[0])
      }

      // 卸载应该不抛出错误
      expect(() => unmount()).not.toThrow()

      // DOM应该被清理
      expect(document.querySelector('[data-testid="card"]')).toBeNull()
    })

    it('应该处理频繁的数据更新', () => {
      const { rerender } = render(
        <EvidenceChain
          chains={[]}
          evidenceNodes={{}}
        />
      )

      // 模拟频繁的数据更新
      for (let i = 0; i < 10; i++) {
        const newNodes = generateLargeDataset(10)
        const newChains = generateLargeChains(1)

        rerender(
          <EvidenceChain
            chains={newChains}
            evidenceNodes={newNodes}
          />
        )
      }

      // 组件应该仍然正常工作
      expect(screen.getByText('证据链分析')).toBeInTheDocument()
    })
  })

  describe('响应性测试', () => {
    it('应该快速响应用户交互', () => {
      const nodes = generateLargeDataset(50)

      render(
        <EvidenceChain
          chains={[]}
          evidenceNodes={nodes}
        />
      )

      // 测试节点展开/折叠的响应时间
      const expandButtons = screen.getAllByRole('button')
      if (expandButtons.length > 0) {
        const startTime = performance.now()
        fireEvent.click(expandButtons[0])
        const endTime = performance.now()

        const responseTime = endTime - startTime
        expect(responseTime).toBeLessThan(50) // 50ms内响应
      }
    })

    it('应该处理大量的视图切换操作', () => {
      const nodes = generateLargeDataset(100)

      render(
        <EvidenceChain
          chains={[]}
          evidenceNodes={nodes}
        />
      )

      const tabsList = screen.getByTestId('tabs-list')
      const buttons = tabsList.querySelectorAll('button')

      // 快速切换视图
      for (let i = 0; i < 10; i++) {
        buttons.forEach(button => {
          fireEvent.click(button)
        })
      }

      // 应该仍然正常工作
      expect(screen.getByText('证据链分析')).toBeInTheDocument()
    })
  })
})