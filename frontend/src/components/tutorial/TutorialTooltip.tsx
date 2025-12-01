'use client';

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import * as Tooltip from '@radix-ui/react-tooltip';
import { BookOpen, HelpCircle, Lightbulb, Search, X } from 'lucide-react';
import { debounce } from 'lodash';

// 帮助内容类型
interface HelpContent {
  id: string;
  title: string;
  content: string;
  category: 'concept' | 'feature' | 'troubleshooting' | 'best-practice';
  relatedTerms: string[];
  priority: 'high' | 'medium' | 'low';
  context?: {
    component?: string;
    step?: number;
    action?: string;
  };
}

// 上下文分析结果
interface ContextAnalysis {
  currentComponent: string;
  currentStep: number;
  userAction: string;
  relevantTopics: string[];
  confidence: number;
}

interface TutorialTooltipProps {
  /** 当前组件名称，用于上下文分析 */
  componentName?: string;
  /** 当前教程步骤 */
  currentStep?: number;
  /** 用户正在执行的操作 */
  userAction?: string;
  /** 是否显示智能推荐 */
  showSmartRecommendations?: boolean;
  /** 自定义帮助内容 */
  customHelpContent?: HelpContent[];
  /** 触发模式 */
  trigger?: 'hover' | 'click' | 'focus';
  /** 延迟显示时间 (ms) */
  delayShow?: number;
  /** 最大推荐数量 */
  maxRecommendations?: number;
  /** 针对用户水平的内容过滤 */
  userLevel?: 'beginner' | 'intermediate' | 'advanced';
}

const TutorialTooltip: React.FC<TutorialTooltipProps> = ({
  componentName = '',
  currentStep = 0,
  userAction = '',
  showSmartRecommendations = true,
  customHelpContent = [],
  trigger = 'hover',
  delayShow = 500,
  maxRecommendations = 3,
  userLevel = 'beginner',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [contextAnalysis, setContextAnalysis] =
    useState<ContextAnalysis | null>(null);
  const [recommendations, setRecommendations] = useState<HelpContent[]>([]);
  const [filteredContent, setFilteredContent] = useState<HelpContent[]>([]);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // 模拟帮助内容数据库
  const helpDatabase: HelpContent[] = [
    {
      id: 'ma-concept',
      title: '移动平均线 (MA)',
      content:
        '移动平均线是技术分析中最常用的指标之一，通过计算特定周期内的平均价格来平滑价格波动，帮助识别趋势方向。',
      category: 'concept',
      relatedTerms: ['SMA', 'EMA', '趋势', '技术指标'],
      priority: 'high',
      context: { component: 'MovingAverageCalculation', action: 'calculate' },
    },
    {
      id: 'golden-cross',
      title: '金叉信号',
      content:
        '当短期移动平均线从下向上穿过长期移动平均线时，形成金叉，通常被视为买入信号。这表明短期趋势正在转为上升。',
      category: 'concept',
      relatedTerms: ['买入信号', '趋势反转', '移动平均线'],
      priority: 'high',
      context: {
        component: 'GoldenDeathCrossAnimation',
        action: 'identify_signal',
      },
    },
    {
      id: 'death-cross',
      title: '死叉信号',
      content:
        '当短期移动平均线从上向下穿过长期移动平均线时，形成死叉，通常被视为卖出信号。这表明短期趋势正在转为下降。',
      category: 'concept',
      relatedTerms: ['卖出信号', '趋势反转', '移动平均线'],
      priority: 'high',
      context: {
        component: 'GoldenDeathCrossAnimation',
        action: 'identify_signal',
      },
    },
    {
      id: 'backtesting',
      title: '策略回测',
      content:
        '回测是使用历史数据验证交易策略有效性的过程。通过模拟过去的市场条件来评估策略的表现。',
      category: 'feature',
      relatedTerms: ['历史数据', '策略验证', '性能评估'],
      priority: 'medium',
    },
    {
      id: 'risk-management',
      title: '风险管理',
      content:
        '风险管理是量化交易中最重要的环节，包括止损设置、仓位控制和资金管理，以保护本金并控制损失。',
      category: 'best-practice',
      relatedTerms: ['止损', '仓位控制', '资金管理'],
      priority: 'high',
    },
    {
      id: 'parameter-optimization',
      title: '参数优化',
      content:
        '通过系统性地测试不同参数组合来找到策略的最优参数设置，需要避免过度拟合。',
      category: 'feature',
      relatedTerms: ['参数调优', '策略优化', '过度拟合'],
      priority: 'medium',
    },
    {
      id: 'chart-interpretation',
      title: '图表解读技巧',
      content:
        '学会识别图表中的关键模式，包括趋势线、支撑阻力位、价格形态等，这些都有助于做出更好的交易决策。',
      category: 'best-practice',
      relatedTerms: ['技术分析', '图表模式', '趋势分析'],
      priority: 'medium',
    },
    {
      id: 'common-mistakes',
      title: '常见交易错误',
      content:
        '新手常犯的错误包括过度交易、追涨杀跌、没有止损计划等。了解这些错误有助于避免重复犯错。',
      category: 'troubleshooting',
      relatedTerms: ['交易错误', '新手陷阱', '心理偏差'],
      priority: 'high',
    },
  ];

  // 分析用户上下文
  const analyzeContext = useCallback((): ContextAnalysis => {
    const relevantTopics: string[] = [];

    // 基于组件名称推断相关主题
    if (componentName.toLowerCase().includes('movingaverage')) {
      relevantTopics.push('移动平均线', 'SMA', 'EMA', '趋势分析');
    }
    if (componentName.toLowerCase().includes('cross')) {
      relevantTopics.push('金叉', '死叉', '交易信号', '趋势反转');
    }
    if (componentName.toLowerCase().includes('parameter')) {
      relevantTopics.push('参数优化', '策略配置', '回测');
    }
    if (componentName.toLowerCase().includes('glossary')) {
      relevantTopics.push('术语', '概念', '学习');
    }

    // 基于用户操作推断相关主题
    if (userAction.toLowerCase().includes('calculate')) {
      relevantTopics.push('计算方法', '公式', '技术指标');
    }
    if (userAction.toLowerCase().includes('analyze')) {
      relevantTopics.push('分析技巧', '图表解读', '技术分析');
    }
    if (userAction.toLowerCase().includes('configure')) {
      relevantTopics.push('参数设置', '配置选项', '策略优化');
    }

    // 计算上下文相关性置信度
    let confidence = 0.5; // 基础置信度
    if (componentName) confidence += 0.2;
    if (userAction) confidence += 0.2;
    if (currentStep > 0) confidence += 0.1;
    confidence = Math.min(confidence, 1.0);

    return {
      currentComponent: componentName,
      currentStep,
      userAction,
      relevantTopics: [...new Set(relevantTopics)], // 去重
      confidence,
    };
  }, [componentName, currentStep, userAction]);

  // 智能推荐算法
  const generateRecommendations = useCallback(
    (context: ContextAnalysis): HelpContent[] => {
      if (!showSmartRecommendations) return [];

      const scored = helpDatabase.map((help) => {
        let score = 0;

        // 基于优先级的评分
        if (help.priority === 'high') score += 3;
        else if (help.priority === 'medium') score += 2;
        else score += 1;

        // 基于上下文匹配的评分
        if (help.context?.component === context.currentComponent) {
          score += 5; // 组件完全匹配
        }

        if (help.context?.action === context.userAction) {
          score += 4; // 操作完全匹配
        }

        // 基于相关主题匹配的评分
        const topicMatches = context.relevantTopics.filter((topic) =>
          help.relatedTerms.some(
            (term) =>
              term.toLowerCase().includes(topic.toLowerCase()) ||
              topic.toLowerCase().includes(term.toLowerCase()),
          ),
        ).length;
        score += topicMatches * 2;

        // 基于用户水平的内容过滤
        if (userLevel === 'beginner' && help.category === 'concept') score += 2;
        if (userLevel === 'intermediate' && help.category === 'feature')
          score += 2;
        if (userLevel === 'advanced' && help.category === 'best-practice')
          score += 2;

        return { help, score };
      });

      // 排序并返回最高分的内容
      return scored
        .sort((a, b) => b.score - a.score)
        .slice(0, maxRecommendations)
        .map((item) => item.help);
    },
    [showSmartRecommendations, userLevel, maxRecommendations],
  );

  // 搜索功能
  const performSearch = useCallback((query: string) => {
    if (!query.trim()) {
      setFilteredContent([]);
      return;
    }

    const filtered = helpDatabase.filter((help) => {
      const searchLower = query.toLowerCase();
      return (
        help.title.toLowerCase().includes(searchLower) ||
        help.content.toLowerCase().includes(searchLower) ||
        help.relatedTerms.some((term) =>
          term.toLowerCase().includes(searchLower),
        ) ||
        help.category.toLowerCase().includes(searchLower)
      );
    });

    setFilteredContent(filtered);
  }, []);

  // 防抖搜索
  const debouncedSearch = useMemo(
    () => debounce(performSearch, 300),
    [performSearch],
  );

  // 监听搜索查询变化
  useEffect(() => {
    debouncedSearch(searchQuery);
    return () => {
      if (debouncedSearch && typeof debouncedSearch.cancel === 'function') {
        debouncedSearch.cancel();
      }
    };
  }, [searchQuery, debouncedSearch]);

  // 分析上下文并生成推荐
  useEffect(() => {
    const context = analyzeContext();
    setContextAnalysis(context);

    if (isOpen && showSmartRecommendations) {
      const recs = generateRecommendations(context);
      setRecommendations(recs);
    }
  }, [
    isOpen,
    analyzeContext,
    generateRecommendations,
    showSmartRecommendations,
  ]);

  // 处理工具提示打开
  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    if (open) {
      setSearchQuery('');
      setFilteredContent([]);

      // 延迟聚焦搜索框
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 100);
    }
  };

  // 渲染帮助内容项
  const renderHelpItem = (help: HelpContent) => (
    <div
      key={help.id}
      role="button"
      tabIndex={0}
      aria-label={`${help.title} - ${help.category}`}
      className="p-3 border-b border-gray-100 last:border-b-0 hover:bg-gray-50 transition-colors"
      onClick={() => handleHelpItemClick(help)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleHelpItemClick(help);
        }
      }}
    >
      <div className="flex items-start justify-between mb-2">
        <h4 className="font-medium text-gray-900 text-sm">{help.title}</h4>
        <span
          className={`px-2 py-1 text-xs rounded-full ${
            help.category === 'concept'
              ? 'bg-blue-100 text-blue-700'
              : help.category === 'feature'
                ? 'bg-green-100 text-green-700'
                : help.category === 'troubleshooting'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-purple-100 text-purple-700'
          }`}
        >
          {help.category === 'concept'
            ? '概念'
            : help.category === 'feature'
              ? '功能'
              : help.category === 'troubleshooting'
                ? '问题'
                : '实践'}
        </span>
      </div>
      <p className="text-gray-600 text-sm leading-relaxed">{help.content}</p>
      {help.relatedTerms.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {help.relatedTerms.slice(0, 3).map((term) => (
            <span
              key={term}
              className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded"
            >
              {term}
            </span>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <Tooltip.Provider delayDuration={delayShow}>
      <Tooltip.Root open={isOpen} onOpenChange={handleOpenChange}>
        <Tooltip.Trigger asChild>
          <button
            className={`inline-flex items-center justify-center w-8 h-8 rounded-full transition-colors ${
              trigger === 'hover' ? 'hover:bg-blue-50' : ''
            } ${isOpen ? 'bg-blue-50 text-blue-600' : 'text-gray-400'}`}
            aria-label="帮助"
          >
            <HelpCircle className="w-5 h-5" />
          </button>
        </Tooltip.Trigger>

        <Tooltip.Portal>
          <Tooltip.Content
            className="bg-white rounded-lg shadow-lg border border-gray-200 p-0 max-w-sm w-80 z-50"
            sideOffset={5}
            alignOffset={5}
          >
            {/* 头部 */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <Lightbulb className="w-4 h-4 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">智能帮助</h3>
                  {contextAnalysis && (
                    <p className="text-xs text-gray-500">
                      上下文匹配度:{' '}
                      {Math.round(contextAnalysis.confidence * 100)}%
                    </p>
                  )}
                </div>
              </div>
              <button
                className="text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="关闭"
                onClick={() => setIsOpen(false)}
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* 搜索框 */}
            <div className="p-4 border-b border-gray-200">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  ref={searchInputRef}
                  type="text"
                  placeholder="搜索帮助内容..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  aria-label="搜索帮助内容"
                  aria-describedby="help-search-description"
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                />
                <div id="help-search-description" className="sr-only">
                  输入关键词以搜索相关的教程帮助内容
                </div>
              </div>
            </div>

            {/* 内容区域 */}
            <div className="max-h-80 overflow-y-auto">
              {/* 搜索结果 */}
              {searchQuery && filteredContent.length > 0 && (
                <div>
                  <div className="px-4 py-2 bg-gray-50 text-xs font-medium text-gray-700">
                    搜索结果 ({filteredContent.length})
                  </div>
                  {filteredContent.map(renderHelpItem)}
                </div>
              )}

              {/* 智能推荐 */}
              {!searchQuery && recommendations.length > 0 && (
                <div>
                  <div className="px-4 py-2 bg-blue-50 text-xs font-medium text-blue-700">
                    为你推荐
                  </div>
                  {recommendations.map(renderHelpItem)}
                </div>
              )}

              {/* 自定义内容 */}
              {!searchQuery && customHelpContent.length > 0 && (
                <div>
                  <div className="px-4 py-2 bg-green-50 text-xs font-medium text-green-700">
                    相关提示
                  </div>
                  {customHelpContent.map(renderHelpItem)}
                </div>
              )}

              {/* 无结果提示 */}
              {searchQuery && filteredContent.length === 0 && (
                <div className="p-8 text-center">
                  <BookOpen className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500 text-sm">未找到相关帮助内容</p>
                  <p className="text-gray-400 text-xs mt-1">
                    尝试使用其他关键词搜索
                  </p>
                </div>
              )}

              {/* 默认提示 */}
              {!searchQuery &&
                recommendations.length === 0 &&
                customHelpContent.length === 0 && (
                  <div className="p-4 text-center">
                    <HelpCircle className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                    <p className="text-gray-500 text-sm">
                      输入关键词搜索帮助内容
                    </p>
                  </div>
                )}
            </div>

            {/* 底部链接 */}
            <div className="p-3 border-t border-gray-200 bg-gray-50">
              <button
                className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                onClick={() => {
                  // 这里可以链接到完整的帮助系统或FAQ
                  console.log('Navigate to full help system');
                }}
              >
                查看完整帮助文档 →
              </button>
            </div>

            <Tooltip.Arrow className="fill-white" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
};

export default TutorialTooltip;
