'use client';

import React, { memo, useMemo, useCallback, useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { HelpDocument, FAQItem } from '@/types/ux.types';
import { helpService } from '@/services/helpService';

// 帮助文档组件
interface HelpDocumentViewerProps {
  document: HelpDocument;
  onRelatedDocumentClick?: (documentId: string) => void;
}

export const HelpDocumentViewer = memo<HelpDocumentViewerProps>(({
  document,
  onRelatedDocumentClick,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const formattedContent = useMemo(() => {
    // 简单的Markdown渲染（实际项目中应使用专门的Markdown库）
    return document.content
      .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mb-4">$1</h1>')
      .replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold mb-3">$1</h2>')
      .replace(/^### (.*$)/gim, '<h3 class="text-lg font-medium mb-2">$1</h3>')
      .replace(/^\* (.*$)/gim, '<li class="ml-4">$1</li>')
      .replace(/^\d+\. (.*$)/gim, '<li class="ml-4 list-decimal">$1</li>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n\n/g, '</p><p class="mb-4">')
      .replace(/\n/g, '<br />');
  }, [document.content]);

  const handleRelatedDocumentClick = useCallback((documentId: string) => {
    onRelatedDocumentClick?.(documentId);
  }, [onRelatedDocumentClick]);

  return (
    <Card className="p-6">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-2xl font-bold mb-2">{document.title}</h2>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Badge variant="outline">{document.category}</Badge>
            <Badge variant="secondary">{document.difficulty}</Badge>
            <span>预计阅读时间: {document.estimatedReadTime}分钟</span>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {isExpanded ? '收起' : '展开'}
        </Button>
      </div>

      <div className="flex flex-wrap gap-1 mb-4">
        {document.tags.map(tag => (
          <Badge key={tag} variant="outline" className="text-xs">
            {tag}
          </Badge>
        ))}
      </div>

      <div
        className={cn(
          'prose prose-sm max-w-none',
          !isExpanded && 'line-clamp-6'
        )}
        dangerouslySetInnerHTML={{ __html: `<p class="mb-4">${formattedContent}</p>` }}
      />

      {document.relatedDocuments.length > 0 && (
        <div className="mt-6 pt-4 border-t">
          <h4 className="text-sm font-medium mb-2">相关文档</h4>
          <div className="flex flex-wrap gap-2">
            {document.relatedDocuments.map(docId => (
              <Button
                key={docId}
                variant="outline"
                size="sm"
                onClick={() => handleRelatedDocumentClick(docId)}
              >
                {docId.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </Button>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 pt-4 border-t text-xs text-gray-500">
        最后更新: {new Date(document.lastUpdated).toLocaleDateString()}
      </div>
    </Card>
  );
});

HelpDocumentViewer.displayName = 'HelpDocumentViewer';

// FAQ项目组件
interface FAQItemProps {
  faq: FAQItem;
  onHelpfulClick?: (faqId: string, helpful: boolean) => void;
}

export const FAQItem = memo<FAQItemProps>(({
  faq,
  onHelpfulClick,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [hasVoted, setHasVoted] = useState(false);

  const handleHelpfulClick = useCallback((helpful: boolean) => {
    if (!hasVoted) {
      onHelpfulClick?.(faq.id, helpful);
      setHasVoted(true);
    }
  }, [hasVoted, onHelpfulClick, faq.id]);

  return (
    <Card className="mb-4">
      <div className="p-4">
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-lg font-medium pr-4">{faq.question}</h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? '收起' : '展开'}
          </Button>
        </div>

        {isExpanded && (
          <div className="mb-4 text-gray-700">
            {faq.answer}
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline">{faq.category}</Badge>
            <span className="text-xs text-gray-500">
              {faq.popularity} 人查看
            </span>
          </div>

          {isExpanded && !hasVoted && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">这个回答有帮助吗？</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleHelpfulClick(true)}
              >
                👍 有用 ({faq.helpful})
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleHelpfulClick(false)}
              >
                👎 无用 ({faq.notHelpful})
              </Button>
            </div>
          )}

          {hasVoted && (
            <span className="text-sm text-green-600">感谢您的反馈！</span>
          )}
        </div>
      </div>
    </Card>
  );
});

FAQItem.displayName = 'FAQItem';

// 搜索组件
interface SearchComponentProps {
  onSearch: (query: string) => void;
  placeholder?: string;
  className?: string;
}

export const SearchComponent = memo<SearchComponentProps>(({
  onSearch,
  placeholder = '搜索帮助文档...',
  className,
}) => {
  const [query, setQuery] = useState('');
  const debounceTimerRef = useRef<NodeJS.Timeout>();

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);

    // 防抖搜索
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      onSearch(value);
    }, 300);
  }, [onSearch]);

  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  return (
    <div className={cn('relative', className)}>
      <Input
        type="text"
        value={query}
        onChange={handleInputChange}
        placeholder={placeholder}
        className="pr-10"
      />
      <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400">
        🔍
      </div>
    </div>
  );
});

SearchComponent.displayName = 'SearchComponent';

// 帮助中心组件
interface HelpCenterProps {
  isOpen: boolean;
  onClose: () => void;
  initialCategory?: string;
  initialQuery?: string;
}

export function HelpCenter({
  isOpen,
  onClose,
  initialCategory,
  initialQuery,
}: HelpCenterProps) {
  const [activeTab, setActiveTab] = useState('documents');
  const [searchQuery, setSearchQuery] = useState(initialQuery || '');
  const [selectedCategory, setSelectedCategory] = useState(initialCategory || '');
  const [selectedDocument, setSelectedDocument] = useState<HelpDocument | null>(null);

  const {
    data: documents = [],
    isLoading: documentsLoading,
  } = helpService.useHelpDocuments(selectedCategory);

  const {
    data: searchResults = [],
    isLoading: searchLoading,
  } = helpService.useSearchHelpDocuments(searchQuery, selectedCategory);

  const {
    data: faqs = [],
    isLoading: faqsLoading,
  } = helpService.useFAQ(selectedCategory);

  const {
    data: searchFAQs = [],
    isLoading: searchFAQsLoading,
  } = helpService.useSearchFAQs(searchQuery, selectedCategory);

  const submitFeedbackMutation = helpService.useSubmitFeedback();

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    if (query.trim()) {
      setActiveTab('search');
    }
  }, []);

  const handleDocumentClick = useCallback((document: HelpDocument) => {
    setSelectedDocument(document);
  }, []);

  const handleRelatedDocumentClick = useCallback((documentId: string) => {
    const relatedDoc = documents.find(doc => doc.id === documentId) ||
                      searchResults.find(doc => doc.id === documentId);
    if (relatedDoc) {
      setSelectedDocument(relatedDoc);
    }
  }, [documents, searchResults]);

  const handleFAQFeedback = useCallback((faqId: string, helpful: boolean) => {
    helpService.faqService.recordFAQFeedback(faqId, helpful);
  }, []);

  const handleContactSupport = useCallback(async (feedbackData: any) => {
    try {
      await submitFeedbackMutation.mutateAsync(feedbackData);
      // 显示成功消息
    } catch (error) {
      // 显示错误消息
    }
  }, [submitFeedbackMutation]);

  const categories = useMemo(() => {
    const docCategories = Array.from(new Set(documents.map(doc => doc.category)));
    const faqCategories = helpService.faqService.getFAQCategories();
    return Array.from(new Set([...docCategories, ...faqCategories]));
  }, [documents]);

  const displayDocuments = searchQuery.trim() ? searchResults : documents;
  const displayFAQs = searchQuery.trim() ? searchFAQs : faqs;

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>帮助中心</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* 搜索栏 */}
          <SearchComponent
            onSearch={handleSearch}
            placeholder="搜索帮助文档和FAQ..."
          />

          {/* 类别过滤 */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant={selectedCategory === '' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory('')}
            >
              全部
            </Button>
            {categories.map(category => (
              <Button
                key={category}
                variant={selectedCategory === category ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCategory(category)}
              >
                {category}
              </Button>
            ))}
          </div>

          {/* 标签页 */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="documents">帮助文档</TabsTrigger>
              <TabsTrigger value="faq">常见问题</TabsTrigger>
              <TabsTrigger value="contact">联系支持</TabsTrigger>
            </TabsList>

            <TabsContent value="documents" className="space-y-4">
              {documentsLoading ? (
                <div className="text-center py-8">加载中...</div>
              ) : selectedDocument ? (
                <div>
                  <Button
                    variant="outline"
                    onClick={() => setSelectedDocument(null)}
                    className="mb-4"
                  >
                    ← 返回列表
                  </Button>
                  <HelpDocumentViewer
                    document={selectedDocument}
                    onRelatedDocumentClick={handleRelatedDocumentClick}
                  />
                </div>
              ) : displayDocuments.length > 0 ? (
                <div className="space-y-4">
                  {displayDocuments.map(doc => (
                    <Card
                      key={doc.id}
                      className="p-4 cursor-pointer hover:shadow-md transition-shadow"
                      onClick={() => handleDocumentClick(doc)}
                    >
                      <h3 className="text-lg font-medium mb-2">{doc.title}</h3>
                      <p className="text-gray-600 text-sm mb-2 line-clamp-2">
                        {doc.content.replace(/[#*]/g, '').slice(0, 150)}...
                      </p>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{doc.category}</Badge>
                        <Badge variant="secondary">{doc.difficulty}</Badge>
                        <span className="text-xs text-gray-500">
                          {doc.estimatedReadTime}分钟阅读
                        </span>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  {searchQuery.trim() ? '没有找到相关文档' : '暂无文档'}
                </div>
              )}
            </TabsContent>

            <TabsContent value="faq" className="space-y-4">
              {faqsLoading ? (
                <div className="text-center py-8">加载中...</div>
              ) : displayFAQs.length > 0 ? (
                displayFAQs.map(faq => (
                  <FAQItem
                    key={faq.id}
                    faq={faq}
                    onHelpfulClick={handleFAQFeedback}
                  />
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  {searchQuery.trim() ? '没有找到相关FAQ' : '暂无FAQ'}
                </div>
              )}
            </TabsContent>

            <TabsContent value="contact" className="space-y-4">
              <Card className="p-6">
                <h3 className="text-lg font-medium mb-4">联系技术支持</h3>
                <p className="text-gray-600 mb-6">
                  如果您没有找到需要的帮助信息，可以通过以下方式联系我们：
                </p>

                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="text-2xl">📧</div>
                    <div>
                      <div className="font-medium">邮箱支持</div>
                      <div className="text-sm text-gray-600">support@example.com</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-2xl">💬</div>
                    <div>
                      <div className="font-medium">在线客服</div>
                      <div className="text-sm text-gray-600">工作日 9:00-18:00</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-2xl">📝</div>
                    <div>
                      <div className="font-medium">提交反馈</div>
                      <div className="text-sm text-gray-600">24小时内回复</div>
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-6 border-t">
                  <h4 className="font-medium mb-3">快速反馈</h4>
                  <p className="text-sm text-gray-600 mb-4">
                    描述您遇到的问题，我们会尽快为您解决。
                  </p>
                  <Button onClick={() => {/* 打开反馈表单 */}}>
                    提交反馈
                  </Button>
                </div>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// 帮助按钮组件
interface HelpButtonProps {
  onClick?: () => void;
  className?: string;
}

export function HelpButton({ onClick, className }: HelpButtonProps) {
  const [isHelpCenterOpen, setIsHelpCenterOpen] = useState(false);

  const handleClick = useCallback(() => {
    setIsHelpCenterOpen(true);
    onClick?.();
  }, [onClick]);

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={handleClick}
        className={className}
      >
        <span className="mr-2">?</span>
        帮助
      </Button>

      <HelpCenter
        isOpen={isHelpCenterOpen}
        onClose={() => setIsHelpCenterOpen(false)}
      />
    </>
  );
}

// 上下文帮助组件
interface ContextHelpProps {
  helpId: string;
  title?: string;
  className?: string;
}

export function ContextHelp({ helpId, title, className }: ContextHelpProps) {
  const [isOpen, setIsOpen] = useState(false);

  // 这里可以根据helpId从帮助服务获取特定的帮助内容
  const helpContent = useMemo(() => {
    // 实际实现中应该从服务获取
    return {
      title: title || '帮助信息',
      content: '这里是相关的帮助信息...',
    };
  }, [helpId, title]);

  return (
    <div className={cn('inline-block', className)}>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen(true)}
        className="text-blue-600 hover:text-blue-800"
      >
        <span className="text-sm">?</span>
      </Button>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{helpContent.title}</DialogTitle>
          </DialogHeader>
          <div className="text-sm text-gray-600">
            {helpContent.content}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default {
  HelpDocumentViewer,
  FAQItem,
  SearchComponent,
  HelpCenter,
  HelpButton,
  ContextHelp,
};