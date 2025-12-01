'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ChevronDown,
  Clock,
  Filter,
  Search,
  Star,
  TrendingUp,
  X,
} from 'lucide-react';
import { debounce } from 'lodash';
import {
  HelpContent,
  SearchResult,
  UserContext,
  useHelpSearch,
  usePopularContent,
} from '@/services/contextHelpService';

interface HelpSearchSystemProps {
  /** 当前用户上下文，用于个性化推荐 */
  userContext?: UserContext;
  /** 最大搜索结果数量 */
  maxResults?: number;
  /** 是否显示搜索历史 */
  showSearchHistory?: boolean;
  /** 是否显示热门内容 */
  showPopularContent?: boolean;
  /** 是否支持高级搜索 */
  enableAdvancedSearch?: boolean;
  /** 占位符文本 */
  placeholder?: string;
  /** 搜索框样式类名 */
  className?: string;
  /** 搜索回调函数 */
  onSearch?: (query: string, results: SearchResult[]) => void;
  /** 内容选择回调函数 */
  onContentSelect?: (content: HelpContent) => void;
}

const HelpSearchSystem: React.FC<HelpSearchSystemProps> = ({
  userContext,
  maxResults = 10,
  showSearchHistory = true,
  showPopularContent = true,
  enableAdvancedSearch = false,
  placeholder = '搜索帮助内容、概念、功能...',
  className = '',
  onSearch,
  onContentSelect,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'relevance' | 'popularity' | 'rating'>(
    'relevance',
  );
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  const searchInputRef = useRef<HTMLInputElement>(null);
  const searchResultsRef = useRef<HTMLDivElement>(null);

  // 搜索查询
  const {
    data: searchResults = [],
    isLoading: isSearchLoading,
    error: searchError,
  } = useHelpSearch(searchQuery, {
    enabled: searchQuery.trim().length > 0,
  });

  // 热门内容查询
  const { data: popularContent = [], isLoading: isPopularLoading } =
    usePopularContent(5, {
      enabled: showPopularContent && !searchQuery,
    });

  // 从本地存储加载搜索历史
  useEffect(() => {
    try {
      const history = localStorage.getItem('help_search_history');
      if (history) {
        setSearchHistory(JSON.parse(history));
      }
    } catch (error) {
      console.warn('Failed to load search history:', error);
    }
  }, []);

  // 保存搜索历史到本地存储
  const saveSearchHistory = useCallback(
    (query: string) => {
      if (!query.trim()) return;

      const newHistory = [
        query,
        ...searchHistory.filter((h) => h !== query),
      ].slice(0, 10);
      setSearchHistory(newHistory);

      try {
        localStorage.setItem('help_search_history', JSON.stringify(newHistory));
      } catch (error) {
        console.warn('Failed to save search history:', error);
      }
    },
    [searchHistory],
  );

  // 防抖搜索
  const debouncedSearch = useCallback(
    debounce((query: string) => {
      if (query.trim()) {
        saveSearchHistory(query);
      }
      onSearch?.(query, searchResults);
    }, 300),
    [onSearch, searchResults, saveSearchHistory],
  );

  // 处理搜索查询变化
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newQuery = e.target.value;
    setSearchQuery(newQuery);
    debouncedSearch(newQuery);
  };

  // 处理搜索提交
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      saveSearchHistory(searchQuery);
      debouncedSearch(searchQuery);
    }
  };

  // 处理内容选择
  const handleContentSelect = (content: HelpContent) => {
    onContentSelect?.(content);
    setSearchQuery('');
    setIsSearchFocused(false);
  };

  // 处理历史记录选择
  const handleHistorySelect = (query: string) => {
    setSearchQuery(query);
    searchInputRef.current?.focus();
  };

  // 清除搜索历史
  const clearSearchHistory = () => {
    setSearchHistory([]);
    try {
      localStorage.removeItem('help_search_history');
    } catch (error) {
      console.warn('Failed to clear search history:', error);
    }
  };

  // 过滤和排序搜索结果
  const filteredAndSortedResults = React.useMemo(() => {
    let results = [...searchResults];

    // 分类过滤
    if (selectedCategory !== 'all') {
      results = results.filter(
        (result) => result.content.category === selectedCategory,
      );
    }

    // 难度过滤
    if (selectedDifficulty !== 'all') {
      results = results.filter(
        (result) => result.content.difficulty === selectedDifficulty,
      );
    }

    // 排序
    results.sort((a, b) => {
      switch (sortBy) {
        case 'popularity':
          return b.content.viewCount - a.content.viewCount;
        case 'rating':
          return b.content.helpfulRating - a.content.helpfulRating;
        case 'relevance':
        default:
          return b.matchScore - a.matchScore;
      }
    });

    return results.slice(0, maxResults);
  }, [searchResults, selectedCategory, selectedDifficulty, sortBy, maxResults]);

  // 分类选项
  const categoryOptions = [
    { value: 'all', label: '全部分类' },
    { value: 'concept', label: '概念解释' },
    { value: 'feature', label: '功能说明' },
    { value: 'troubleshooting', label: '问题解决' },
    { value: 'best-practice', label: '最佳实践' },
  ];

  // 难度选项
  const difficultyOptions = [
    { value: 'all', label: '全部难度' },
    { value: 'beginner', label: '初级' },
    { value: 'intermediate', label: '中级' },
    { value: 'advanced', label: '高级' },
  ];

  // 排序选项
  const sortOptions = [
    { value: 'relevance', label: '相关度' },
    { value: 'popularity', label: '热度' },
    { value: 'rating', label: '评分' },
  ];

  // 渲染搜索结果项
  const renderSearchResult = (result: SearchResult) => (
    <div
      key={result.content.id}
      className="p-4 border-b border-gray-100 last:border-b-0 hover:bg-gray-50 cursor-pointer transition-colors"
      onClick={() => handleContentSelect(result.content)}
    >
      <div className="flex items-start justify-between mb-2">
        <h4 className="font-medium text-gray-900 text-sm flex-1">
          {result.content.title}
        </h4>
        <div className="flex items-center gap-2 ml-2">
          <span
            className={`px-2 py-1 text-xs rounded-full ${
              result.content.category === 'concept'
                ? 'bg-blue-100 text-blue-700'
                : result.content.category === 'feature'
                  ? 'bg-green-100 text-green-700'
                  : result.content.category === 'troubleshooting'
                    ? 'bg-red-100 text-red-700'
                    : 'bg-purple-100 text-purple-700'
            }`}
          >
            {result.content.category === 'concept'
              ? '概念'
              : result.content.category === 'feature'
                ? '功能'
                : result.content.category === 'troubleshooting'
                  ? '问题'
                  : '实践'}
          </span>
          <span
            className={`px-2 py-1 text-xs rounded ${
              result.content.difficulty === 'beginner'
                ? 'bg-gray-100 text-gray-600'
                : result.content.difficulty === 'intermediate'
                  ? 'bg-yellow-100 text-yellow-700'
                  : 'bg-red-100 text-red-700'
            }`}
          >
            {result.content.difficulty === 'beginner'
              ? '初级'
              : result.content.difficulty === 'intermediate'
                ? '中级'
                : '高级'}
          </span>
        </div>
      </div>

      <p className="text-gray-600 text-sm leading-relaxed mb-2 line-clamp-2">
        {result.content.content}
      </p>

      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {result.content.estimatedReadTime}秒
          </span>
          <span className="flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            {result.content.viewCount}次查看
          </span>
          {result.content.helpfulRating > 0 && (
            <span className="flex items-center gap-1">
              <Star className="w-3 h-3 fill-yellow-400 text-yellow-400" />
              {Math.round(result.content.helpfulRating * 100)}%
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <span className="text-blue-600 font-medium">
            匹配度: {Math.round(result.matchScore)}
          </span>
        </div>
      </div>

      {result.matchedFields.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {result.matchedFields.map((field) => (
            <span
              key={field}
              className="px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded"
            >
              {field === 'title'
                ? '标题'
                : field === 'content'
                  ? '内容'
                  : field === 'terms'
                    ? '术语'
                    : '分类'}
            </span>
          ))}
        </div>
      )}
    </div>
  );

  // 渲染热门内容项
  const renderPopularContent = (content: HelpContent, index: number) => (
    <div
      key={content.id}
      className="p-3 border-b border-gray-100 last:border-b-0 hover:bg-gray-50 cursor-pointer transition-colors"
      onClick={() => handleContentSelect(content)}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-6 h-6 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
          {index + 1}
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-gray-900 text-sm truncate">
            {content.title}
          </h4>
          <p className="text-gray-600 text-xs mt-1 line-clamp-2">
            {content.content}
          </p>
          <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              {content.viewCount}次查看
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {content.estimatedReadTime}秒
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className={`relative ${className}`}>
      {/* 搜索框 */}
      <div className="relative">
        <form onSubmit={handleSearchSubmit}>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={handleSearchChange}
              onFocus={() => setIsSearchFocused(true)}
              onBlur={() => setTimeout(() => setIsSearchFocused(false), 200)}
              placeholder={placeholder}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </form>

        {/* 高级搜索过滤器 */}
        {enableAdvancedSearch && (
          <div className="mt-2 flex items-center gap-2">
            <button
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              className="flex items-center gap-1 px-3 py-1 text-xs text-gray-600 hover:text-gray-900 transition-colors"
            >
              <Filter className="w-3 h-3" />
              高级搜索
              <ChevronDown
                className={`w-3 h-3 transform transition-transform ${showAdvancedFilters ? 'rotate-180' : ''}`}
              />
            </button>
          </div>
        )}

        {showAdvancedFilters && (
          <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {/* 分类过滤 */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  分类
                </label>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {categoryOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* 难度过滤 */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  难度
                </label>
                <select
                  value={selectedDifficulty}
                  onChange={(e) => setSelectedDifficulty(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {difficultyOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* 排序选项 */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  排序
                </label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {sortOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 搜索结果下拉框 */}
      {isSearchFocused && (
        <div
          ref={searchResultsRef}
          className="absolute top-full left-0 right-0 mt-2 bg-white rounded-lg shadow-lg border border-gray-200 max-h-96 overflow-hidden z-50"
        >
          {isSearchLoading && (
            <div className="p-4 text-center text-gray-500 text-sm">
              正在搜索...
            </div>
          )}

          {searchError && (
            <div className="p-4 text-center text-red-500 text-sm">
              搜索出错，请稍后重试
            </div>
          )}

          {!isSearchLoading && !searchError && searchQuery && (
            <>
              {filteredAndSortedResults.length > 0 ? (
                <div>
                  <div className="px-4 py-2 bg-gray-50 border-b border-gray-200">
                    <span className="text-xs font-medium text-gray-700">
                      搜索结果 ({filteredAndSortedResults.length})
                    </span>
                  </div>
                  <div className="max-h-80 overflow-y-auto">
                    {filteredAndSortedResults.map(renderSearchResult)}
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center">
                  <Search className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500 text-sm">未找到相关帮助内容</p>
                  <p className="text-gray-400 text-xs mt-1">
                    尝试使用其他关键词或调整筛选条件
                  </p>
                </div>
              )}
            </>
          )}

          {!searchQuery && (
            <div className="max-h-80 overflow-y-auto">
              {/* 搜索历史 */}
              {showSearchHistory && searchHistory.length > 0 && (
                <div>
                  <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-700">
                      最近搜索
                    </span>
                    <button
                      onClick={clearSearchHistory}
                      className="text-xs text-gray-500 hover:text-gray-700"
                    >
                      清除
                    </button>
                  </div>
                  {searchHistory.slice(0, 5).map((query, index) => (
                    <div
                      key={index}
                      className="px-4 py-2 hover:bg-gray-50 cursor-pointer text-sm text-gray-700"
                      onClick={() => handleHistorySelect(query)}
                    >
                      <div className="flex items-center gap-2">
                        <Clock className="w-3 h-3 text-gray-400" />
                        {query}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* 热门内容 */}
              {showPopularContent && popularContent.length > 0 && (
                <div>
                  <div className="px-4 py-2 bg-yellow-50 border-b border-gray-200 flex items-center gap-2">
                    <TrendingUp className="w-3 h-3 text-yellow-600" />
                    <span className="text-xs font-medium text-yellow-700">
                      热门内容
                    </span>
                  </div>
                  {popularContent.map((content, index) =>
                    renderPopularContent(content, index),
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default HelpSearchSystem;
