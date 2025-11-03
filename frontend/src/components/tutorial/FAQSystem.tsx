'use client';

import React, { useState, useMemo } from 'react';
import {
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Search,
  Tag,
  BookOpen,
  MessageCircle,
  ExternalLink,
  Clock,
  Star
} from 'lucide-react';
import { UserContext, HelpContent } from '@/services/contextHelpService';

// FAQ 项目类型
interface FAQItem {
  id: string;
  question: string;
  answer: string;
  category: 'getting-started' | 'concepts' | 'features' | 'troubleshooting' | 'advanced';
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  relatedTopics: string[];
  helpfulCount: number;
  totalVotes: number;
  lastUpdated: string;
  relatedHelpIds?: string[];
  externalLinks?: Array<{
    title: string;
    url: string;
    description?: string;
  }>;
}

// 快速帮助链接类型
interface QuickHelpLink {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  url: string;
  category: 'guide' | 'tutorial' | 'reference' | 'support';
  priority: 'high' | 'medium' | 'low';
  estimatedReadTime: number;
}

interface FAQSystemProps {
  /** 当前用户上下文，用于个性化推荐 */
  userContext?: UserContext;
  /** 是否显示搜索功能 */
  showSearch?: boolean;
  /** 是否显示分类筛选 */
  showCategoryFilter?: boolean;
  /** 是否显示难度筛选 */
  showDifficultyFilter?: boolean;
  /** 是否显示统计信息 */
  showStats?: boolean;
  /** 默认展开的分类 */
  defaultExpandedCategory?: string;
  /** 最大显示项目数 */
  maxItems?: number;
  /** 自定义样式类名 */
  className?: string;
  /** FAQ 点击回调 */
  onFAQClick?: (faq: FAQItem) => void;
  /** 帮助链接点击回调 */
  onHelpLinkClick?: (link: QuickHelpLink) => void;
}

// FAQ 数据库
const FAQ_DATABASE: FAQItem[] = [
  {
    id: 'faq-001',
    question: '什么是移动平均线？',
    answer: '移动平均线（Moving Average，MA）是技术分析中最常用的指标之一。它通过计算特定时间段内的平均价格来平滑价格波动，帮助识别趋势方向。常见的类型包括简单移动平均线（SMA）和指数移动平均线（EMA）。SMA给予所有价格相同权重，而EMA给予近期价格更高权重，因此对价格变化更敏感。',
    category: 'concepts',
    difficulty: 'beginner',
    relatedTopics: ['SMA', 'EMA', '技术指标', '趋势分析'],
    helpfulCount: 45,
    totalVotes: 48,
    lastUpdated: '2025-11-01',
    relatedHelpIds: ['ma-concept'],
  },
  {
    id: 'faq-002',
    question: '金叉和死叉是什么意思？',
    answer: '金叉和死叉是移动平均线交易信号：\n\n• 金叉：当短期移动平均线从下向上穿过长期移动平均线时形成，通常被视为买入信号，表明短期趋势转为上升。\n\n• 死叉：当短期移动平均线从上向下穿过长期移动平均线时形成，通常被视为卖出信号，表明短期趋势转为下降。\n\n需要注意的是，这些信号应该结合成交量、市场环境和其他技术指标来确认，避免假信号。',
    category: 'concepts',
    difficulty: 'beginner',
    relatedTopics: ['交易信号', '趋势反转', '技术分析'],
    helpfulCount: 38,
    totalVotes: 42,
    lastUpdated: '2025-11-01',
    relatedHelpIds: ['golden-cross', 'death-cross'],
  },
  {
    id: 'faq-003',
    question: '如何开始使用单均线策略？',
    answer: '开始使用单均线策略的步骤：\n\n1. **理解原理**：学习移动平均线的基本概念和计算方法\n2. **选择参数**：根据交易品种和时间周期选择合适的均线周期（如20日、50日）\n3. **设置规则**：确定金叉买入、死叉卖出的具体规则\n4. **风险控制**：设置止损位和仓位管理规则\n5. **回测验证**：使用历史数据测试策略效果\n6. **小资金实践**：用少量资金进行实盘验证\n7. **持续优化**：根据实际表现调整参数和规则',
    category: 'getting-started',
    difficulty: 'beginner',
    relatedTopics: ['策略入门', '参数设置', '风险管理'],
    helpfulCount: 52,
    totalVotes: 56,
    lastUpdated: '2025-11-01',
  },
  {
    id: 'faq-004',
    question: '回测结果可靠吗？为什么实盘表现和回测不一样？',
    answer: '回测结果是策略的历史表现参考，但不保证未来收益。实盘和回测的差异主要原因：\n\n• **交易成本**：回测可能忽略手续费、滑点等实际交易成本\n• **市场环境变化**：历史数据无法完全反映未来市场状况\n• **流动性限制**：大宗交易可能影响价格，回测通常不考虑\n• **心理因素**：实盘交易中的情绪波动会影响决策\n• **过度拟合**：参数过度优化导致历史表现好但未来表现差\n\n建议：结合多个时间段回测、考虑交易成本、保持参数简单、定期重新评估策略。',
    category: 'troubleshooting',
    difficulty: 'intermediate',
    relatedTopics: ['回测', '过度拟合', '交易成本', '风险管理'],
    helpfulCount: 41,
    totalVotes: 45,
    lastUpdated: '2025-11-01',
    relatedHelpIds: ['backtesting', 'parameter-optimization'],
  },
  {
    id: 'faq-005',
    question: '如何设置合适的止损和止盈？',
    answer: '设置止损和止盈的方法：\n\n**止损设置原则：**\n• 基于技术位：支撑位、阻力位、均线等\n• 基于波动率：ATR（平均真实波幅）的倍数\n• 基于资金比例：单笔损失不超过总资金的1-2%\n• 固定点数：根据品种特性设置固定点数\n\n**止盈设置原则：**\n• 风险收益比：通常设置为1:1.5或1:2\n• 技术目标位：重要的阻力位或前期高点\n• 追踪止损：盈利后移动止损位锁定利润\n• 分批止盈：达到不同目标时分批平仓\n\n**重要提醒：** 严格执行止损，不要随意修改；止盈可以适当灵活，但要避免贪婪。',
    category: 'features',
    difficulty: 'intermediate',
    relatedTopics: ['风险管理', '止损', '止盈', '资金管理'],
    helpfulCount: 47,
    totalVotes: 50,
    lastUpdated: '2025-11-01',
    relatedHelpIds: ['risk-management'],
  },
  {
    id: 'faq-006',
    question: '什么是过度拟合？如何避免？',
    answer: '过度拟合是指策略参数过度优化，在历史数据上表现很好，但在未来数据上表现较差的现象。\n\n**过度拟合的特征：**\n• 参数过多且复杂\n• 在特定时间段表现异常好\n• 略微改变参数就大幅影响表现\n• 缺乏理论依据，纯粹数据挖掘\n\n**避免方法：**\n• **保持简单**：使用较少的参数和清晰的逻辑\n• **样本外测试**：保留部分数据不参与优化\n• **时间序列验证**：使用不同时间段进行测试\n• **参数稳定**：选择在一定范围内表现稳定的参数\n• **理论支撑**：基于合理的交易逻辑而非纯粹数据挖掘\n• **定期重估**：定期检查策略是否仍然有效',
    category: 'advanced',
    difficulty: 'advanced',
    relatedTopics: ['过度拟合', '参数优化', '策略验证', '样本外测试'],
    helpfulCount: 33,
    totalVotes: 37,
    lastUpdated: '2025-11-01',
    relatedHelpIds: ['parameter-optimization'],
  },
  {
    id: 'faq-007',
    question: '如何处理策略亏损期？',
    answer: '策略亏损期是正常现象，处理方法：\n\n**1. 分析原因**\n• 检查是否符合历史回测中的最大回撤\n• 分析亏损的具体原因（市场环境、执行问题等）\n• 确认是否违反了交易规则\n\n**2. 控制情绪**\n• 保持冷静，避免情绪化决策\n• 坚持交易计划和纪律\n• 适当减少交易频率或规模\n\n**3. 策略调整**\n• 如果是市场环境变化，暂时减少交易\n• 如果是策略失效，考虑重新评估或停止使用\n• 不要频繁修改参数\n\n**4. 风险管理**\n• 严格执行止损\n• 控制总体风险敞口\n• 保留足够资金应对亏损期\n\n记住：任何策略都有亏损期，关键是控制风险、保持纪律。',
    category: 'troubleshooting',
    difficulty: 'intermediate',
    relatedTopics: ['心理管理', '风险控制', '纪律', '资金管理'],
    helpfulCount: 39,
    totalVotes: 43,
    lastUpdated: '2025-11-01',
    relatedHelpIds: ['common-mistakes', 'risk-management'],
  },
  {
    id: 'faq-008',
    question: '如何选择合适的移动平均线周期？',
    answer: '选择移动平均线周期需要考虑以下因素：\n\n**1. 交易时间周期**\n• 短周期交易（日内）：5-20周期\n• 中长周期交易（日线）：20-200周期\n\n**2. 市场特性**\n• 高波动市场：较短周期\n• 低波动市场：较长周期\n\n**3. 常用周期参考**\n• 10-20周期：短期交易，适合活跃交易者\n• 50周期：中期趋势，比较平衡\n• 200周期：长期趋势，适合趋势跟踪\n\n**4. 选择方法**\n• 回测不同周期的表现\n• 考虑交易频率和信号质量\n• 结合个人交易风格\n• 避免过度优化\n\n**建议**：新手建议从20-50周期开始，熟悉后再根据表现调整。',
    category: 'features',
    difficulty: 'intermediate',
    relatedTopics: ['参数选择', '周期设置', '交易风格', '回测'],
    helpfulCount: 44,
    totalVotes: 47,
    lastUpdated: '2025-11-01',
    relatedHelpIds: ['ma-concept'],
  }
];

// 快速帮助链接数据
const QUICK_HELP_LINKS: QuickHelpLink[] = [
  {
    id: 'guide-001',
    title: '新手入门指南',
    description: '从零开始学习量化交易和单均线策略',
    icon: <BookOpen className="w-5 h-5" />,
    url: '/guide/getting-started',
    category: 'guide',
    priority: 'high',
    estimatedReadTime: 300,
  },
  {
    id: 'tutorial-001',
    title: '交互式教程',
    description: '通过实践学习策略原理和应用',
    icon: <HelpCircle className="w-5 h-5" />,
    url: '/tutorial/interactive',
    category: 'tutorial',
    priority: 'high',
    estimatedReadTime: 600,
  },
  {
    id: 'reference-001',
    title: 'API文档',
    description: '详细的技术文档和接口说明',
    icon: <ExternalLink className="w-5 h-5" />,
    url: '/docs/api',
    category: 'reference',
    priority: 'medium',
    estimatedReadTime: 180,
  },
  {
    id: 'support-001',
    title: '联系支持',
    description: '遇到问题？获取专业帮助',
    icon: <MessageCircle className="w-5 h-5" />,
    url: '/support/contact',
    category: 'support',
    priority: 'medium',
    estimatedReadTime: 60,
  },
];

// 分类配置
const CATEGORY_CONFIG = {
  'getting-started': {
    label: '入门指南',
    color: 'green',
    icon: <BookOpen className="w-4 h-4" />,
  },
  'concepts': {
    label: '基本概念',
    color: 'blue',
    icon: <HelpCircle className="w-4 h-4" />,
  },
  'features': {
    label: '功能说明',
    color: 'purple',
    icon: <Star className="w-4 h-4" />,
  },
  'troubleshooting': {
    label: '问题解决',
    color: 'red',
    icon: <MessageCircle className="w-4 h-4" />,
  },
  'advanced': {
    label: '高级话题',
    color: 'yellow',
    icon: <ExternalLink className="w-4 h-4" />,
  },
};

const FAQSystem: React.FC<FAQSystemProps> = ({
  userContext,
  showSearch = true,
  showCategoryFilter = true,
  showDifficultyFilter = false,
  showStats = true,
  defaultExpandedCategory,
  maxItems = 20,
  className = '',
  onFAQClick,
  onHelpLinkClick,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('all');
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    defaultExpandedCategory ? new Set([defaultExpandedCategory]) : new Set()
  );

  // 过滤FAQ项目
  const filteredFAQs = useMemo(() => {
    let filtered = FAQ_DATABASE;

    // 搜索过滤
    if (searchQuery.trim()) {
      const searchLower = searchQuery.toLowerCase();
      filtered = filtered.filter(faq =>
        faq.question.toLowerCase().includes(searchLower) ||
        faq.answer.toLowerCase().includes(searchLower) ||
        faq.relatedTopics.some(topic => topic.toLowerCase().includes(searchLower))
      );
    }

    // 分类过滤
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(faq => faq.category === selectedCategory);
    }

    // 难度过滤
    if (selectedDifficulty !== 'all') {
      filtered = filtered.filter(faq => faq.difficulty === selectedDifficulty);
    }

    // 基于用户上下文优先排序
    if (userContext) {
      filtered.sort((a, b) => {
        const aRelevance = calculateFAQRelevance(a, userContext);
        const bRelevance = calculateFAQRelevance(b, userContext);
        return bRelevance - aRelevance;
      });
    } else {
      // 按有用性排序
      filtered.sort((a, b) => {
        const aScore = a.helpfulCount / a.totalVotes;
        const bScore = b.helpfulCount / b.totalVotes;
        return bScore - aScore;
      });
    }

    return filtered.slice(0, maxItems);
  }, [searchQuery, selectedCategory, selectedDifficulty, userContext, maxItems]);

  // 按分类分组FAQ
  const faqsByCategory = useMemo(() => {
    const grouped: Record<string, FAQItem[]> = {};

    filteredFAQs.forEach(faq => {
      if (!grouped[faq.category]) {
        grouped[faq.category] = [];
      }
      grouped[faq.category].push(faq);
    });

    return grouped;
  }, [filteredFAQs]);

  // 计算FAQ与用户上下文的相关性
  function calculateFAQRelevance(faq: FAQItem, context: UserContext): number {
    let score = 0;

    // 基于相关主题匹配
    const topicMatches = faq.relatedTopics.filter(topic =>
      context.learningGoals.some(goal =>
        goal.toLowerCase().includes(topic.toLowerCase()) ||
        topic.toLowerCase().includes(goal.toLowerCase())
      )
    ).length;
    score += topicMatches * 3;

    // 基于用户水平匹配
    if (context.userLevel === faq.difficulty) score += 2;
    if (context.errorsEncountered.length > 0 && faq.category === 'troubleshooting') score += 5;

    // 基于用户行为匹配
    if (context.previousActions.some(action =>
      faq.relatedTopics.some(topic => action.toLowerCase().includes(topic.toLowerCase()))
    )) {
      score += 2;
    }

    return score;
  }

  // 切换FAQ项目展开状态
  const toggleFAQExpansion = (faqId: string) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(faqId)) {
      newExpanded.delete(faqId);
    } else {
      newExpanded.add(faqId);
    }
    setExpandedItems(newExpanded);
  };

  // 切换分类展开状态
  const toggleCategoryExpansion = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  // 处理FAQ点击
  const handleFAQClick = (faq: FAQItem) => {
    toggleFAQExpansion(faq.id);
    onFAQClick?.(faq);
  };

  // 处理帮助链接点击
  const handleHelpLinkClick = (link: QuickHelpLink) => {
    onHelpLinkClick?.(link);
  };

  // 渲染FAQ项目
  const renderFAQItem = (faq: FAQItem) => {
    const isExpanded = expandedItems.has(faq.id);
    const helpfulPercentage = faq.totalVotes > 0 ? Math.round((faq.helpfulCount / faq.totalVotes) * 100) : 0;
    const categoryConfig = CATEGORY_CONFIG[faq.category];

    return (
      <div key={faq.id} className="border border-gray-200 rounded-lg overflow-hidden">
        <button
          onClick={() => handleFAQClick(faq)}
          className="w-full px-4 py-3 bg-white hover:bg-gray-50 transition-colors text-left"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-${categoryConfig.color}-100 text-${categoryConfig.color}-700`}>
                  {categoryConfig.icon}
                  {categoryConfig.label}
                </span>
                <span className={`px-2 py-1 text-xs rounded ${
                  faq.difficulty === 'beginner' ? 'bg-gray-100 text-gray-600' :
                  faq.difficulty === 'intermediate' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-red-100 text-red-700'
                }`}>
                  {faq.difficulty === 'beginner' ? '初级' :
                   faq.difficulty === 'intermediate' ? '中级' : '高级'}
                </span>
              </div>
              <h4 className="font-medium text-gray-900 text-sm leading-tight">
                {faq.question}
              </h4>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {showStats && (
                <div className="flex items-center gap-1 text-xs text-gray-500">
                  <Star className="w-3 h-3" />
                  {helpfulPercentage}%
                </div>
              )}
              <div className="text-gray-400">
                {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </div>
            </div>
          </div>
        </button>

        {isExpanded && (
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
            <div className="prose prose-sm max-w-none">
              <div className="whitespace-pre-wrap text-gray-700 text-sm leading-relaxed">
                {faq.answer}
              </div>
            </div>

            {/* 相关主题 */}
            {faq.relatedTopics.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200">
                <div className="flex items-center gap-2 mb-2">
                  <Tag className="w-3 h-3 text-gray-500" />
                  <span className="text-xs font-medium text-gray-700">相关主题</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {faq.relatedTopics.map(topic => (
                    <span
                      key={topic}
                      className="px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 统计信息 */}
            {showStats && (
              <div className="mt-3 pt-3 border-t border-gray-200 flex items-center justify-between text-xs text-gray-500">
                <div className="flex items-center gap-3">
                  <span>{faq.helpfulCount}/{faq.totalVotes} 人觉得有用</span>
                  <span>最后更新: {faq.lastUpdated}</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* 搜索和筛选 */}
      <div className="space-y-4">
        {showSearch && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索FAQ..."
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          {showCategoryFilter && (
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">全部分类</option>
              {Object.entries(CATEGORY_CONFIG).map(([key, config]) => (
                <option key={key} value={key}>
                  {config.label}
                </option>
              ))}
            </select>
          )}

          {showDifficultyFilter && (
            <select
              value={selectedDifficulty}
              onChange={(e) => setSelectedDifficulty(e.target.value)}
              className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">全部难度</option>
              <option value="beginner">初级</option>
              <option value="intermediate">中级</option>
              <option value="advanced">高级</option>
            </select>
          )}
        </div>
      </div>

      {/* 快速帮助链接 */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">快速帮助</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {QUICK_HELP_LINKS.map(link => (
            <button
              key={link.id}
              onClick={() => handleHelpLinkClick(link)}
              className="p-4 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 hover:border-blue-300 transition-all text-left group"
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 group-hover:bg-blue-200 transition-colors">
                  {link.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-gray-900 text-sm mb-1">{link.title}</h4>
                  <p className="text-gray-600 text-xs line-clamp-2">{link.description}</p>
                  <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                    <Clock className="w-3 h-3" />
                    <span>{Math.ceil(link.estimatedReadTime / 60)}分钟阅读</span>
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* FAQ列表 */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            常见问题 {filteredFAQs.length > 0 && `(${filteredFAQs.length})`}
          </h3>
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              清除搜索
            </button>
          )}
        </div>

        {Object.entries(faqsByCategory).length > 0 ? (
          <div className="space-y-4">
            {Object.entries(faqsByCategory).map(([category, faqs]) => {
              const categoryConfig = CATEGORY_CONFIG[category as keyof typeof CATEGORY_CONFIG];
              const isCategoryExpanded = expandedCategories.has(category);

              return (
                <div key={category} className="space-y-3">
                  <button
                    onClick={() => toggleCategoryExpansion(category)}
                    className="flex items-center gap-2 text-left w-full group"
                  >
                    <span className={`inline-flex items-center gap-1 px-3 py-1 text-sm font-medium rounded-lg bg-${categoryConfig.color}-100 text-${categoryConfig.color}-700`}>
                      {categoryConfig.icon}
                      {categoryConfig.label}
                      <span className="text-xs opacity-75">({faqs.length})</span>
                    </span>
                    <div className="text-gray-400 group-hover:text-gray-600">
                      {isCategoryExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </div>
                  </button>

                  {isCategoryExpanded && (
                    <div className="space-y-3">
                      {faqs.map(renderFAQItem)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-12">
            <HelpCircle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <h4 className="text-gray-900 font-medium mb-2">未找到相关FAQ</h4>
            <p className="text-gray-600 text-sm">
              {searchQuery ? '尝试使用其他关键词搜索' : '暂无FAQ内容'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default FAQSystem;