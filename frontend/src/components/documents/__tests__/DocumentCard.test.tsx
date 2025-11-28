/**
 * DocumentCard组件单元测试
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DocumentCard } from '../DocumentCard';
import { useDocumentStore, DocumentStatus, KnowledgeDocument } from '@/store/documentStore';

// Mock store
jest.mock('@/store/documentStore', () => ({
  useDocumentStore: jest.fn(),
  DocumentStatus: {
    PENDING: 'PENDING',
    INDEXING: 'INDEXING',
    READY: 'READY',
    ERROR: 'ERROR',
  },
}));

// Mock date-fns
jest.mock('date-fns', () => ({
  formatDistanceToNow: () => '3天前',
}));

jest.mock('date-fns/locale', () => ({
  zhCN: {},
}));

describe('DocumentCard', () => {
  const mockDocument = {
    id: 'doc-123',
    tenant_id: 'tenant-1',
    file_name: 'test-document.pdf',
    file_type: 'pdf',
    file_size: 1024 * 1024, // 1MB
    status: 'READY',
    created_at: '2024-01-01T00:00:00Z',
    indexed_at: '2024-01-01T01:00:00Z',
    updated_at: '2024-01-01T01:00:00Z',
    storage_path: '/documents/test.pdf',
    mime_type: 'application/pdf',
  } as any;

  const mockStoreFunctions = {
    deleteDocument: jest.fn(),
    getDocumentPreviewUrl: jest.fn(),
    getDocumentDownloadUrl: jest.fn().mockResolvedValue('http://download.example.com/test.pdf'),
    processDocument: jest.fn(),
    openPreviewModal: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useDocumentStore as unknown as jest.Mock).mockReturnValue(mockStoreFunctions);
    window.confirm = jest.fn().mockReturnValue(true);
  });

  describe('渲染测试', () => {
    it('应该正确渲染文档名称', () => {
      render(<DocumentCard document={mockDocument} />);
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    it('应该显示文件类型', () => {
      render(<DocumentCard document={mockDocument} />);
      expect(screen.getByText('PDF')).toBeInTheDocument();
    });

    it('应该显示文件大小', () => {
      render(<DocumentCard document={mockDocument} />);
      expect(screen.getByText(/1 MB/)).toBeInTheDocument();
    });

    it('应该显示文档ID', () => {
      render(<DocumentCard document={mockDocument} />);
      expect(screen.getByText(/doc-123/)).toBeInTheDocument();
    });
  });

  describe('状态显示测试', () => {
    it('READY状态应该显示处理完成', () => {
      render(<DocumentCard document={{ ...mockDocument, status: 'READY' }} />);
      expect(screen.getByText('处理完成')).toBeInTheDocument();
    });

    it('PENDING状态应该显示等待处理', () => {
      render(<DocumentCard document={{ ...mockDocument, status: 'PENDING' }} />);
      expect(screen.getByText('等待处理')).toBeInTheDocument();
    });

    it('INDEXING状态应该显示正在处理', () => {
      render(<DocumentCard document={{ ...mockDocument, status: 'INDEXING' }} />);
      expect(screen.getByText('正在处理')).toBeInTheDocument();
    });

    it('ERROR状态应该显示处理失败', () => {
      render(<DocumentCard document={{ ...mockDocument, status: 'ERROR' }} />);
      expect(screen.getByText('处理失败')).toBeInTheDocument();
    });

    it('错误状态应该显示错误信息', () => {
      render(
        <DocumentCard
          document={{
            ...mockDocument,
            status: 'ERROR',
            processing_error: '文件解析失败',
          }}
        />
      );
      expect(screen.getByText(/文件解析失败/)).toBeInTheDocument();
    });
  });

  describe('选择功能测试', () => {
    it('showSelection为true时应该显示选择框', () => {
      const onSelectionChange = jest.fn();
      render(
        <DocumentCard
          document={mockDocument}
          showSelection={true}
          onSelectionChange={onSelectionChange}
        />
      );
      expect(screen.getByRole('checkbox')).toBeInTheDocument();
    });

    it('选择状态应该反映isSelected属性', () => {
      render(
        <DocumentCard
          document={mockDocument}
          showSelection={true}
          isSelected={true}
          onSelectionChange={jest.fn()}
        />
      );
      expect(screen.getByRole('checkbox')).toBeChecked();
    });

    it('点击选择框应该调用onSelectionChange', () => {
      const onSelectionChange = jest.fn();
      render(
        <DocumentCard
          document={mockDocument}
          showSelection={true}
          onSelectionChange={onSelectionChange}
        />
      );
      fireEvent.click(screen.getByRole('checkbox'));
      expect(onSelectionChange).toHaveBeenCalledWith(true);
    });
  });

  describe('操作按钮测试', () => {
    it('READY状态应该显示预览按钮', () => {
      render(<DocumentCard document={{ ...mockDocument, status: 'READY' }} />);
      expect(screen.getByText('预览')).toBeInTheDocument();
    });

    it('应该显示下载按钮', () => {
      render(<DocumentCard document={mockDocument} />);
      expect(screen.getByText('下载')).toBeInTheDocument();
    });

    it('应该显示删除按钮', () => {
      render(<DocumentCard document={mockDocument} />);
      expect(screen.getByText('删除')).toBeInTheDocument();
    });

    it('PENDING状态应该显示处理按钮', () => {
      render(<DocumentCard document={{ ...mockDocument, status: 'PENDING' }} />);
      expect(screen.getByText('处理')).toBeInTheDocument();
    });
  });
});

