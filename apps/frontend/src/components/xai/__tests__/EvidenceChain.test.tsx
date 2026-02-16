import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { EvidenceChain } from '../EvidenceChain'

// Mock the necessary dependencies
jest.mock('@/components/ui/card', () => ({
  Card: ({ children }: { children: React.ReactNode }) => <div data-testid="card">{children}</div>,
  CardContent: ({ children }: { children: React.ReactNode }) => <div data-testid="card-content">{children}</div>,
  CardDescription: ({ children }: { children: React.ReactNode }) => <div data-testid="card-description">{children}</div>,
  CardHeader: ({ children }: { children: React.ReactNode }) => <div data-testid="card-header">{children}</div>,
  CardTitle: ({ children }: { children: React.ReactNode }) => <div data-testid="card-title">{children}</div>
}))

jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, className }: { children: React.ReactNode; className?: string }) =>
    <span data-testid="badge" className={className}>{children}</span>
}))

jest.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, ...props }: any) =>
    <button onClick={onClick} {...props}>{children}</button>
}))

jest.mock('@/components/ui/progress', () => ({
  Progress: ({ value }: { value: number }) =>
    <div data-testid="progress" style={{ width: `${value}%` }}></div>
}))

jest.mock('@/components/ui/collapsible', () => ({
  Collapsible: ({ children, open }: { children: React.ReactNode; open: boolean }) =>
    <div data-testid="collapsible" data-open={open}>{children}</div>,
  CollapsibleContent: ({ children }: { children: React.ReactNode }) => <div data-testid="collapsible-content">{children}</div>,
  CollapsibleTrigger: ({ children }: { children: React.ReactNode }) => <div data-testid="collapsible-trigger">{children}</div>
}))

jest.mock('@/components/ui/tabs', () => ({
  Tabs: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs">{children}</div>,
  TabsContent: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs-content">{children}</div>,
  TabsList: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs-list">{children}</div>,
  TabsTrigger: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs-trigger">{children}</div>
}))

jest.mock('@/components/ui/alert', () => ({
  Alert: ({ children }: { children: React.ReactNode }) => <div data-testid="alert">{children}</div>,
  AlertDescription: ({ children }: { children: React.ReactNode }) => <div data-testid="alert-description">{children}</div>,
  AlertTitle: ({ children }: { children: React.ReactNode }) => <div data-testid="alert-title">{children}</div>
}))

describe('EvidenceChain Component', () => {
  const mockChains = [
    {
      chain_id: 'chain-1',
      chain_name: '主要证据链',
      description: '分析用户查询的主要证据链',
      overall_confidence: 0.85,
      evidence_count: 5,
      verified_count: 4,
      created_at: '2023-11-16T10:00:00Z',
      chain_type: 'linear' as const
    },
    {
      chain_id: 'chain-2',
      chain_name: '辅助证据链',
      description: '补充分析的证据链',
      overall_confidence: 0.72,
      evidence_count: 3,
      verified_count: 2,
      created_at: '2023-11-16T10:05:00Z',
      chain_type: 'branching' as const
    }
  ]

  const mockEvidenceNodes = {
    'node-1': {
      id: 'node-1',
      content: '销售数据显示季度增长15%',
      source_type: 'sql_results',
      source_name: 'sales_database',
      relevance_score: 0.9,
      confidence_score: 0.85,
      verification_status: 'verified' as const,
      extraction_method: 'SQL_QUERY',
      timestamp: '2023-11-16T10:00:00Z',
      metadata: {
        table: 'sales_data',
        rows_analyzed: 1000
      }
    },
    'node-2': {
      id: 'node-2',
      content: '市场报告确认行业趋势',
      source_type: 'document',
      source_name: 'market_analysis_report.pdf',
      relevance_score: 0.8,
      confidence_score: 0.75,
      verification_status: 'pending' as const,
      timestamp: '2023-11-16T10:01:00Z',
      metadata: {
        document_type: 'PDF',
        pages: 25
      }
    }
  }

  const defaultProps = {
    chains: mockChains,
    evidenceNodes: mockEvidenceNodes,
    query: 'What is the current sales trend?',
    answer: 'Sales have increased by 15% based on the analysis.'
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders without crashing', () => {
    render(<EvidenceChain {...defaultProps} />)

    expect(screen.getByText('证据链分析')).toBeInTheDocument()
    expect(screen.getByText('展示推理过程中的证据链关系和验证状态')).toBeInTheDocument()
  })

  it('displays chain statistics', () => {
    render(<EvidenceChain {...defaultProps} />)

    expect(screen.getByText('2 个证据链')).toBeInTheDocument()
    expect(screen.getByText('2 个证据节点')).toBeInTheDocument()
    expect(screen.getByText('50% 验证率')).toBeInTheDocument()
  })

  it('shows evidence chain list by default', () => {
    render(<EvidenceChain {...defaultProps} />)

    expect(screen.getByText('主要证据链')).toBeInTheDocument()
    expect(screen.getByText('辅助证据链')).toBeInTheDocument()
    expect(screen.getByText('分析用户查询的主要证据链')).toBeInTheDocument()
  })

  it('displays individual evidence nodes', () => {
    render(<EvidenceChain {...defaultProps} />)

    expect(screen.getByText('销售数据显示季度增长15%')).toBeInTheDocument()
    expect(screen.getByText('市场报告确认行业趋势')).toBeInTheDocument()
    expect(screen.getByText('sales_database')).toBeInTheDocument()
    expect(screen.getByText('market_analysis_report.pdf')).toBeInTheDocument()
  })

  it('shows verification badges', () => {
    render(<EvidenceChain {...defaultProps} />)

    expect(screen.getByText('已验证')).toBeInTheDocument()
    expect(screen.getByText('待验证')).toBeInTheDocument()
  })

  it('displays confidence scores', () => {
    render(<EvidenceChain {...defaultProps} />)

    expect(screen.getByText('85%')).toBeInTheDocument()
    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('renders empty state when no data', () => {
    render(<EvidenceChain />)

    expect(screen.getByText('暂无证据链数据')).toBeInTheDocument()
    expect(screen.getByText('当前答案没有详细的证据链分析数据。')).toBeInTheDocument()
  })

  it('shows tab navigation', () => {
    render(<EvidenceChain {...defaultProps} />)

    expect(screen.getByText('证据链视图')).toBeInTheDocument()
    expect(screen.getByText('关系图谱')).toBeInTheDocument()
    expect(screen.getByText('时间线视图')).toBeInTheDocument()
  })

  it('renders graph view with placeholder', () => {
    render(<EvidenceChain {...defaultProps} />)

    // Switch to graph view (simulate tab change)
    const graphTab = screen.getByText('关系图谱')
    graphTab.click()

    expect(screen.getByText('证据链图形化视图')).toBeInTheDocument()
    expect(screen.getByText('图形化视图正在开发中，当前显示简化的节点关系图。')).toBeInTheDocument()
  })

  it('renders timeline view', () => {
    render(<EvidenceChain {...defaultProps} />)

    // Switch to timeline view (simulate tab change)
    const timelineTab = screen.getByText('时间线视图')
    timelineTab.click()

    expect(screen.getByText('sales_database')).toBeInTheDocument()
    expect(screen.getByText('market_analysis_report.pdf')).toBeInTheDocument()
  })

  it('displays chain type icons correctly', () => {
    render(<EvidenceChain {...defaultProps} />)

    // Should render different chain types with their respective icons
    expect(screen.getByText('主要证据链')).toBeInTheDocument()
    expect(screen.getByText('辅助证据链')).toBeInTheDocument()
  })

  it('handles empty evidence nodes', () => {
    render(<EvidenceChain chains={mockChains} evidenceNodes={{}} />)

    expect(screen.getByText('主要证据链')).toBeInTheDocument()
    expect(screen.getByText('辅助证据链')).toBeInTheDocument()
    // Should still show chains but no nodes
  })

  it('displays metadata when available', () => {
    render(<EvidenceChain {...defaultProps} />)

    expect(screen.getByText('table:')).toBeInTheDocument()
    expect(screen.getByText('sales_data')).toBeInTheDocument()
    expect(screen.getByText('rows_analyzed:')).toBeInTheDocument()
    expect(screen.getByText('1000')).toBeInTheDocument()
  })

  it('shows extraction method when provided', () => {
    render(<EvidenceChain {...defaultProps} />)

    expect(screen.getByText('提取方法:')).toBeInTheDocument()
    expect(screen.getByText('SQL_QUERY')).toBeInTheDocument()
  })

  it('handles interaction when allowInteraction is false', () => {
    render(<EvidenceChain {...defaultProps} allowInteraction={false} />)

    // Should still render but interaction elements should be limited
    expect(screen.getByText('证据链分析')).toBeInTheDocument()
  })

  it('shows statistics cards with correct values', () => {
    render(<EvidenceChain {...defaultProps} />)

    expect(screen.getByText('2')).toBeInTheDocument() // Total chains
    expect(screen.getByText('2')).toBeInTheDocument() // Total evidence nodes
    expect(screen.getByText('1')).toBeInTheDocument() // Verified evidence
    expect(screen.getByText('50%')).toBeInTheDocument() // Verification rate
  })
})