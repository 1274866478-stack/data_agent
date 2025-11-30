'use client';

import React, { useState, useCallback } from 'react';
import { Upload, X, FileText, Table, Database } from 'lucide-react';

interface SupportedFileType {
  extension: string;
  description: string;
  max_size_mb: number;
  icon: React.ReactNode;
  color: string;
}

const FILE_TYPES: SupportedFileType[] = [
  {
    extension: '.csv',
    description: 'CSV文件',
    max_size_mb: 100,
    icon: <FileText className="w-8 h-8" />,
    color: 'bg-blue-100 text-blue-600'
  },
  {
    extension: '.xlsx',
    description: 'Excel文件',
    max_size_mb: 100,
    icon: <Table className="w-8 h-8" />,
    color: 'bg-green-100 text-green-600'
  },
  {
    extension: '.xls',
    description: 'Excel文件',
    max_size_mb: 100,
    icon: <Table className="w-8 h-8" />,
    color: 'bg-green-100 text-green-600'
  },
  {
    extension: '.db',
    description: 'SQLite数据库',
    max_size_mb: 500,
    icon: <Database className="w-8 h-8" />,
    color: 'bg-purple-100 text-purple-600'
  },
  {
    extension: '.sqlite',
    description: 'SQLite数据库',
    max_size_mb: 500,
    icon: <Database className="w-8 h-8" />,
    color: 'bg-purple-100 text-purple-600'
  },
  {
    extension: '.sqlite3',
    description: 'SQLite数据库',
    max_size_mb: 500,
    icon: <Database className="w-8 h-8" />,
    color: 'bg-purple-100 text-purple-600'
  }
];

interface FileUploadDataSourceProps {
  onSuccess?: (dataSource: any) => void;
  onCancel?: () => void;
}

export default function FileUploadDataSource({ onSuccess, onCancel }: FileUploadDataSourceProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const validateFile = (file: File): string | null => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    const fileType = FILE_TYPES.find(t => t.extension === ext);
    
    if (!fileType) {
      const supported = FILE_TYPES.map(t => t.extension).join(', ');
      return `不支持的文件类型。支持的类型: ${supported}`;
    }
    
    const maxSizeBytes = fileType.max_size_mb * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      return `文件大小超过限制。最大允许: ${fileType.max_size_mb}MB`;
    }
    
    return null;
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const error = validateFile(file);
      if (error) {
        setError(error);
      } else {
        setSelectedFile(file);
        setError(null);
        // 自动填充名称
        if (!name) {
          const baseName = file.name.replace(/\.[^/.]+$/, '');
          setName(baseName);
        }
      }
    }
  }, [name]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const error = validateFile(file);
      if (error) {
        setError(error);
      } else {
        setSelectedFile(file);
        setError(null);
        // 自动填充名称
        if (!name) {
          const baseName = file.name.replace(/\.[^/.]+$/, '');
          setName(baseName);
        }
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !name.trim()) {
      setError('请选择文件并填写数据源名称');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('name', name.trim());
      if (description.trim()) {
        formData.append('description', description.trim());
      }

      const response = await fetch('/api/v1/file-upload/upload-file', {
        method: 'POST',
        body: formData,
        headers: {
          // 不设置Content-Type，让浏览器自动设置multipart/form-data边界
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '上传失败');
      }

      const result = await response.json();
      
      if (onSuccess) {
        onSuccess(result.data_source);
      }
    } catch (err: any) {
      setError(err.message || '上传失败，请重试');
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      {/* 文件拖放区域 */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        {!selectedFile ? (
          <>
            <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <p className="text-lg font-medium text-gray-700 mb-2">
              拖拽文件到此处，或点击选择文件
            </p>
            <p className="text-sm text-gray-500 mb-4">
              支持 CSV、Excel、SQLite 等格式
            </p>
            <input
              type="file"
              id="file-upload"
              className="hidden"
              onChange={handleFileSelect}
              accept=".csv,.xlsx,.xls,.db,.sqlite,.sqlite3"
            />
            <label
              htmlFor="file-upload"
              className="inline-block px-6 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 transition-colors"
            >
              选择文件
            </label>
          </>
        ) : (
          <div className="flex items-center justify-between bg-gray-50 p-4 rounded-lg">
            <div className="flex items-center space-x-3">
              <FileText className="w-8 h-8 text-blue-600" />
              <div className="text-left">
                <p className="font-medium text-gray-900">{selectedFile.name}</p>
                <p className="text-sm text-gray-500">{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>
            <button
              onClick={() => setSelectedFile(null)}
              className="p-1 hover:bg-gray-200 rounded-full transition-colors"
            >
              <X className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        )}
      </div>

      {/* 支持的文件类型 */}
      <div className="mt-8">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">支持的文件类型</h3>
        <div className="grid grid-cols-2 gap-4">
          {/* CSV */}
          <div className="flex items-center space-x-3">
            <div className="bg-blue-100 text-blue-600 p-2 rounded">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <p className="font-medium text-gray-900">.csv</p>
              <p className="text-sm text-gray-500">100MB</p>
            </div>
          </div>

          {/* Excel */}
          <div className="flex items-center space-x-3">
            <div className="bg-green-100 text-green-600 p-2 rounded">
              <Table className="w-6 h-6" />
            </div>
            <div>
              <p className="font-medium text-gray-900">.xlsx</p>
              <p className="text-sm text-gray-500">100MB</p>
            </div>
          </div>

          {/* XLS */}
          <div className="flex items-center space-x-3">
            <div className="bg-green-100 text-green-600 p-2 rounded">
              <Table className="w-6 h-6" />
            </div>
            <div>
              <p className="font-medium text-gray-900">.xls</p>
              <p className="text-sm text-gray-500">100MB</p>
            </div>
          </div>

          {/* SQLite */}
          <div className="flex items-center space-x-3">
            <div className="bg-purple-100 text-purple-600 p-2 rounded">
              <Database className="w-6 h-6" />
            </div>
            <div>
              <p className="font-medium text-gray-900">.db, .sqlite, .sqlite3</p>
              <p className="text-sm text-gray-500">500MB</p>
            </div>
          </div>
        </div>
      </div>

      {/* 数据源信息表单 */}
      <div className="mt-8 space-y-4">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
            数据源名称 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="请输入数据源名称"
          />
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
            描述（可选）
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="请输入数据源描述"
          />
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* 操作按钮 */}
      <div className="mt-8 flex justify-end space-x-4">
        <button
          onClick={onCancel}
          disabled={uploading}
          className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          取消
        </button>
        <button
          onClick={handleUpload}
          disabled={!selectedFile || !name.trim() || uploading}
          className="px-6 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploading ? '上传中...' : '创建数据源'}
        </button>
      </div>
    </div>
  );
}
