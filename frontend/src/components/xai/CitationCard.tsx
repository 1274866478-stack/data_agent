import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Database,
  FileText,
  Globe,
  Link,
  Eye,
  ExternalLink,
  Copy,
  Search
} from 'lucide-react';

interface SourceTrace {
  source_id: string;
  source_type: string;
  source_name: string;
  content_snippet: string;
  relevance_score: number;
  confidence_contribution: number;
  verification_status: string;
  trace_path?: string[];
  extraction_method?: string;
  metadata?: Record<string, any>;
}

interface CitationCardProps {
  source: SourceTrace;
  isExpanded?: boolean;
  onToggleExpand?: (sourceId: string) => void;
  onCopyCitation?: (source: SourceTrace) => void;
  className?: string;
}

export const CitationCard: React.FC<CitationCardProps> = ({
  source,
  isExpanded = false,
  onToggleExpand,
  onCopyCitation,
  className
}) => {
  const getSourceTypeIcon = (type: string) => {
    switch (type) {
      case 'sql_query':
      case 'sql_results':
        return <Database className="h-4 w-4" />;
      case 'rag_retrieval':
      case 'rag_result':
        return <Search className="h-4 w-4" />;
      case 'document':
      case 'documents':
        return <FileText className="h-4 w-4" />;
      case 'api_response':
      case 'api':
        return <Globe className="h-4 w-4" />;
      default:
        return <Link className="h-4 w-4" />;
    }
  };

  const getSourceTypeColor = (type: string) => {
    switch (type) {
      case 'sql_query':
      case 'sql_results':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'rag_retrieval':
      case 'rag_result':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'document':
      case 'documents':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'api_response':
      case 'api':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getRelevanceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getVerificationBadge = (status: string) => {
    switch (status) {
      case 'verified':
        return <Badge className="bg-green-100 text-green-800">已验证</Badge>;
      case 'pending':
        return <Badge variant="secondary">待验证</Badge>;
      case 'failed':
        return <Badge variant="destructive">验证失败</Badge>;
      default:
        return <Badge variant="outline">未知</Badge>;
    }
  };

  const handleCopyCitation = async () => {
    const citation = `[${source.source_type}] ${source.source_name}`;
    if (onCopyCitation) {
      onCopyCitation(source);
    } else {
      try {
        await navigator.clipboard.writeText(citation);
      } catch (err) {
        console.error('Failed to copy citation:', err);
      }
    }
  };

  const handleToggleExpand = () => {
    if (onToggleExpand) {
      onToggleExpand(source.source_id);
    }
  };

  return (
    <Card className={`transition-all duration-200 hover:shadow-md ${className}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getSourceTypeIcon(source.source_type)}
            <div className="flex-1 min-w-0">
              <CardTitle className="text-lg truncate">{source.source_name}</CardTitle>
              <p className="text-sm text-muted-foreground">ID: {source.source_id}</p>
            </div>
            <Badge className={getSourceTypeColor(source.source_type)}>
              {source.source_type}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            {getVerificationBadge(source.verification_status)}
            <Button
              variant="outline"
              size="sm"
              onClick={handleToggleExpand}
              aria-label={isExpanded ? "收起详情" : "展开详情"}
            >
              <Eye className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyCitation}
              aria-label="复制引用"
            >
              <Copy className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          {/* 评分信息 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-muted-foreground">相关性评分:</span>
              <div className="flex items-center gap-2 mt-1">
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${source.relevance_score * 100}%` }}
                  />
                </div>
                <span className={`text-sm font-medium ${getRelevanceColor(source.relevance_score)}`}>
                  {(source.relevance_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            <div>
              <span className="text-sm text-muted-foreground">置信度贡献:</span>
              <div className="flex items-center gap-2 mt-1">
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${source.confidence_contribution * 100}%` }}
                  />
                </div>
                <span className={`text-sm font-medium ${getRelevanceColor(source.confidence_contribution)}`}>
                  {(source.confidence_contribution * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>

          {/* 内容片段 */}
          <div>
            <span className="text-sm text-muted-foreground">内容片段:</span>
            <p className="mt-1 text-sm bg-muted p-3 rounded border-l-4 border-blue-500 leading-relaxed">
              {source.content_snippet}
            </p>
          </div>

          {/* 展开的详细信息 */}
          {isExpanded && (
            <div className="space-y-4 border-t pt-4 animate-in slide-in-from-top-2">
              {source.trace_path && source.trace_path.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2 flex items-center gap-2">
                    <Link className="h-4 w-4" />
                    追踪路径
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {source.trace_path.map((path, idx) => (
                      <Badge key={idx} variant="outline" className="text-xs">
                        {path}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {source.extraction_method && (
                <div>
                  <h4 className="font-medium mb-2">提取方法</h4>
                  <Badge variant="secondary">{source.extraction_method}</Badge>
                </div>
              )}

              {source.metadata && Object.keys(source.metadata).length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">元数据</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
                    {Object.entries(source.metadata).map(([key, value]) => (
                      <div key={key} className="bg-muted p-2 rounded">
                        <span className="font-medium">{key}:</span>
                        <span className="ml-1 break-words">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 原始数据访问链接 */}
              {source.metadata?.original_url && (
                <div>
                  <h4 className="font-medium mb-2">原始数据</h4>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-xs"
                    onClick={() => window.open(source.metadata!.original_url, '_blank')}
                  >
                    <ExternalLink className="h-3 w-3 mr-1" />
                    访问原始数据源
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default CitationCard;