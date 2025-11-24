/**
 * 溯源信息显示相关的样式类和工具函数
 */

// 溯源类型相关的颜色映射
export const SOURCE_TYPE_COLORS = {
  sql_query: {
    bg: 'bg-blue-100',
    text: 'text-blue-800',
    border: 'border-blue-200',
    icon: 'text-blue-600'
  },
  sql_results: {
    bg: 'bg-blue-100',
    text: 'text-blue-800',
    border: 'border-blue-200',
    icon: 'text-blue-600'
  },
  rag_retrieval: {
    bg: 'bg-green-100',
    text: 'text-green-800',
    border: 'border-green-200',
    icon: 'text-green-600'
  },
  rag_result: {
    bg: 'bg-green-100',
    text: 'text-green-800',
    border: 'border-green-200',
    icon: 'text-green-600'
  },
  document: {
    bg: 'bg-yellow-100',
    text: 'text-yellow-800',
    border: 'border-yellow-200',
    icon: 'text-yellow-600'
  },
  documents: {
    bg: 'bg-yellow-100',
    text: 'text-yellow-800',
    border: 'border-yellow-200',
    icon: 'text-yellow-600'
  },
  api_response: {
    bg: 'bg-purple-100',
    text: 'text-purple-800',
    border: 'border-purple-200',
    icon: 'text-purple-600'
  },
  api: {
    bg: 'bg-purple-100',
    text: 'text-purple-800',
    border: 'border-purple-200',
    icon: 'text-purple-600'
  }
} as const;

// 验证状态颜色映射
export const VERIFICATION_STATUS_COLORS = {
  verified: {
    bg: 'bg-green-100',
    text: 'text-green-800',
    border: 'border-green-200'
  },
  pending: {
    bg: 'bg-gray-100',
    text: 'text-gray-800',
    border: 'border-gray-200'
  },
  failed: {
    bg: 'bg-red-100',
    text: 'text-red-800',
    border: 'border-red-200'
  },
  unknown: {
    bg: 'bg-gray-50',
    text: 'text-gray-600',
    border: 'border-gray-200'
  }
} as const;

// 相关性评分颜色映射
export const RELEVANCE_COLORS = {
  high: 'text-green-600',
  medium: 'text-yellow-600',
  low: 'text-red-600'
} as const;

// 通用样式类
export const CITATION_CLASSES = {
  // 容器样式
  container: 'space-y-6',
  card: 'transition-all duration-200 hover:shadow-md',

  // 统计卡片样式
  statsCard: 'text-center p-4 rounded-lg border',
  statsValue: 'text-2xl font-bold',
  statsLabel: 'text-sm text-muted-foreground',

  // 进度条样式
  progressBar: 'w-full bg-gray-200 rounded-full h-2 transition-all duration-300',
  progressFill: 'h-2 rounded-full transition-all duration-300',

  // 内容片段样式
  contentSnippet: 'mt-1 text-sm bg-muted p-3 rounded border-l-4 border-blue-500 leading-relaxed',

  // 标签样式
  badge: 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
  badgeSmall: 'text-xs px-2 py-1 rounded-full',

  // 按钮样式
  iconButton: 'p-2 h-auto',
  expandButton: 'transition-transform duration-200',

  // 搜索和过滤样式
  searchContainer: 'relative flex-1',
  searchInput: 'pl-10',
  filterContainer: 'flex flex-col sm:flex-row gap-4',

  // 标签页样式
  tabContainer: 'flex flex-wrap gap-1 mb-4 pb-2 border-b',
  tabButton: 'text-xs h-7 px-2',

  // 动画样式
  animateIn: 'animate-in slide-in-from-top-2',
  fadeOut: 'animate-out fade-out-0'
} as const;

// 获取溯源类型样式类的工具函数
export const getSourceTypeClasses = (type: string) => {
  const defaultColors = SOURCE_TYPE_COLORS.sql_query;
  return SOURCE_TYPE_COLORS[type as keyof typeof SOURCE_TYPE_COLORS] || defaultColors;
};

// 获取验证状态样式类的工具函数
export const getVerificationStatusClasses = (status: string) => {
  const defaultColors = VERIFICATION_STATUS_COLORS.unknown;
  return VERIFICATION_STATUS_COLORS[status as keyof typeof VERIFICATION_STATUS_COLORS] || defaultColors;
};

// 获取相关性评分颜色类的工具函数
export const getRelevanceColorClass = (score: number) => {
  if (score >= 0.8) return RELEVANCE_COLORS.high;
  if (score >= 0.6) return RELEVANCE_COLORS.medium;
  return RELEVANCE_COLORS.low;
};

// 生成引用文本的格式化函数
export const formatCitation = (source: any) => {
  return `[${source.source_type?.toUpperCase() || 'SOURCE'}] ${source.source_name}`;
};

// 格式化文件大小
export const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// 格式化时间戳
export const formatTimestamp = (timestamp: string | Date) => {
  const date = new Date(timestamp);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// 截断文本的工具函数
export const truncateText = (text: string, maxLength: number) => {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
};

// 高亮搜索关键词的函数
export const highlightSearchTerm = (text: string, searchTerm: string) => {
  if (!searchTerm) return text;

  const regex = new RegExp(`(${searchTerm})`, 'gi');
  const parts = text.split(regex);

  return parts.map((part, index) =>
    regex.test(part) ? (
      <mark key={index} className="bg-yellow-200 px-1 rounded">
        {part}
      </mark>
    ) : part
  );
};

// 溯源类型图标映射
export const SOURCE_TYPE_ICONS = {
  sql_query: 'Database',
  sql_results: 'Database',
  rag_retrieval: 'Search',
  rag_result: 'Search',
  document: 'FileText',
  documents: 'FileText',
  api_response: 'Globe',
  api: 'Globe'
} as const;

// 排序选项配置
export const SORT_OPTIONS = [
  { value: 'relevance', label: '按相关性排序' },
  { value: 'confidence', label: '按置信度排序' },
  { value: 'type', label: '按类型排序' },
  { value: 'name', label: '按名称排序' }
] as const;

// 默认过滤选项
export const DEFAULT_FILTER_OPTIONS = {
  sourceType: 'all',
  verificationStatus: 'all',
  minRelevance: 0,
  sortBy: 'relevance'
} as const;