import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  Calculator,
  ChevronRight,
  Clock,
  Filter,
  Info,
  Search,
  Star,
  TrendingUp,
  X,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

interface GlossaryTerm {
  id: string;
  term: string;
  category: 'basic' | 'strategy' | 'technical' | 'risk' | 'advanced';
  definition: string;
  explanation: string;
  examples: string[];
  relatedTerms: string[];
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  importance: 'low' | 'medium' | 'high';
  readingTime: number; // 阅读时间（秒）
  tags: string[];
  lastUpdated: string;
}

interface InteractiveGlossaryProps {
  onTermSelect?: (term: GlossaryTerm) => void;
  showFavorites?: boolean;
  categories?: string[];
  maxTerms?: number;
}

/**
 * 交互式术语库组件
 * 提供量化交易相关术语的查询、学习和关联功能
 */
export function InteractiveGlossary({
  onTermSelect,
  showFavorites = true,
  categories = ['basic', 'strategy', 'technical', 'risk', 'advanced'],
  maxTerms = 50,
}: InteractiveGlossaryProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('all');
  const [selectedTerm, setSelectedTerm] = useState<GlossaryTerm | null>(null);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const [recentlyViewed, setRecentlyViewed] = useState<GlossaryTerm[]>([]);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // 模拟术语库数据
  const glossaryData: GlossaryTerm[] = useMemo(
    () => [
      {
        id: 'moving-average',
        term: '移动平均线',
        category: 'technical',
        definition:
          '移动平均线是一种技术分析指标，通过计算特定时间段内价格的平均值来平滑价格波动，帮助识别趋势方向。',
        explanation:
          '移动平均线是最基础和最常用的技术分析工具之一。它能够过滤掉价格的短期波动，显示出价格的长期趋势。常见的类型包括简单移动平均线(SMA)和指数移动平均线(EMA)。',
        examples: [
          '20日移动平均线显示中期趋势',
          '当价格上穿50日移动平均线时，可能预示上升趋势开始',
          '200日移动平均线常用于判断长期趋势',
        ],
        relatedTerms: ['SMA', 'EMA', '趋势', '技术分析'],
        difficulty: 'beginner',
        importance: 'high',
        readingTime: 45,
        tags: ['技术指标', '趋势分析', '基础'],
        lastUpdated: '2025-11-02',
      },
      {
        id: 'golden-cross',
        term: '金叉',
        category: 'strategy',
        definition:
          '金叉是指短期移动平均线从下方向上穿越长期移动平均线的技术分析信号，通常被视为买入信号。',
        explanation:
          '金叉是技术分析中的一个重要概念，表明短期上升趋势可能强于长期趋势，市场情绪可能转向看涨。这个信号在量化交易中常用于自动生成买入指令。',
        examples: [
          '10日均线向上穿越20日均线形成金叉',
          '金叉出现后，价格通常会继续上涨一段时间',
          '配合成交量分析可以提高金叉信号的可靠性',
        ],
        relatedTerms: ['死叉', '移动平均线', '买入信号', '技术分析'],
        difficulty: 'intermediate',
        importance: 'high',
        readingTime: 60,
        tags: ['交易信号', '均线策略', '买入'],
        lastUpdated: '2025-11-02',
      },
      {
        id: 'death-cross',
        term: '死叉',
        category: 'strategy',
        definition:
          '死叉是指短期移动平均线从上方向下穿越长期移动平均线的技术分析信号，通常被视为卖出信号。',
        explanation:
          '死叉与金叉相反，表明短期下降趋势可能强于长期趋势，市场情绪可能转向看跌。在量化交易策略中，死叉常用于触发卖出或平仓指令。',
        examples: [
          '10日均线向下跌破20日均线形成死叉',
          '死叉出现后，价格通常会继续下跌一段时间',
          '结合其他技术指标可以验证死叉信号的有效性',
        ],
        relatedTerms: ['金叉', '移动平均线', '卖出信号', '风险控制'],
        difficulty: 'intermediate',
        importance: 'high',
        readingTime: 60,
        tags: ['交易信号', '均线策略', '卖出'],
        lastUpdated: '2025-11-02',
      },
      {
        id: 'SMA',
        term: '简单移动平均线',
        category: 'technical',
        definition:
          '简单移动平均线(Simple Moving Average)是计算特定时期内价格的平均值，给予每个价格点相同的权重。',
        explanation:
          'SMA是最基础的移动平均线类型，计算方法简单：将指定时期内的所有价格相加，然后除以时期数。SMA的优点是计算简单、易于理解，缺点是对近期价格变化的反应较慢。',
        examples: [
          '10日SMA = 最近10天收盘价的总和 ÷ 10',
          '50日SMA常用于判断中期趋势',
          '200日SMA被认为是牛熊分界线',
        ],
        relatedTerms: ['EMA', '移动平均线', '加权平均'],
        difficulty: 'beginner',
        importance: 'medium',
        readingTime: 40,
        tags: ['技术指标', '计算方法', '基础'],
        lastUpdated: '2025-11-02',
      },
      {
        id: 'EMA',
        term: '指数移动平均线',
        category: 'technical',
        definition:
          '指数移动平均线给予近期价格更高的权重，能够更快地响应价格变化。',
        explanation:
          'EMA通过使用指数递减的权重因子，使得近期的价格在计算中占有更大比重。这使得EMA比SMA更敏感，能够更快地反映价格趋势的变化，但也更容易产生假信号。',
        examples: [
          '12日EMA常用于短期趋势分析',
          '26日EMA在MACD指标中使用',
          'EMA比SMA更快响应价格突破',
        ],
        relatedTerms: ['SMA', '移动平均线', 'MACD', '权重'],
        difficulty: 'intermediate',
        importance: 'medium',
        readingTime: 50,
        tags: ['技术指标', '计算方法', '高级'],
        lastUpdated: '2025-11-02',
      },
      {
        id: 'quantitative-trading',
        term: '量化交易',
        category: 'basic',
        definition:
          '量化交易是利用数学模型和计算机算法来执行交易策略的交易方式，旨在消除人为情绪影响。',
        explanation:
          '量化交易通过分析大量历史数据，识别市场模式，并基于预设的规则自动执行交易。这种方法可以提高交易决策的客观性和一致性，降低情绪化交易的风险。',
        examples: [
          '基于均线交叉的自动交易策略',
          '统计套利策略',
          '高频交易算法',
        ],
        relatedTerms: ['算法交易', '交易策略', '回测', '风险管理'],
        difficulty: 'beginner',
        importance: 'high',
        readingTime: 70,
        tags: ['基础概念', '交易方式', '自动化'],
        lastUpdated: '2025-11-02',
      },
      {
        id: 'backtesting',
        term: '回测',
        category: 'advanced',
        definition:
          '回测是使用历史数据测试交易策略效果的过程，用于评估策略的历史表现和可行性。',
        explanation:
          '回测是量化交易中不可或缺的环节，通过模拟策略在过去一段时间内的表现，可以评估策略的盈利能力、风险水平和稳定性。但需要注意的是，过去的表现不代表未来的结果。',
        examples: [
          '使用2020-2023年的数据测试均线策略',
          '计算策略的年化收益率和最大回撤',
          '分析策略在不同市场环境下的表现',
        ],
        relatedTerms: ['策略验证', '历史数据', '风险指标', '过度拟合'],
        difficulty: 'advanced',
        importance: 'high',
        readingTime: 80,
        tags: ['策略验证', '数据分析', '风险评估'],
        lastUpdated: '2025-11-02',
      },
      {
        id: 'risk-management',
        term: '风险管理',
        category: 'risk',
        definition:
          '风险管理是识别、评估和控制交易风险的系统性方法，旨在保护资本并实现长期稳定收益。',
        explanation:
          '风险管理是量化交易成功的核心要素。通过设置止损点、控制仓位大小、分散投资等方式，可以在追求收益的同时控制潜在损失。记住：保住本金比追求高收益更重要。',
        examples: [
          '设置2%的止损规则',
          '单笔交易风险不超过总资金的1%',
          '使用多策略分散风险',
        ],
        relatedTerms: ['止损', '仓位管理', '分散投资', '最大回撤'],
        difficulty: 'intermediate',
        importance: 'high',
        readingTime: 90,
        tags: ['风险控制', '资金管理', '交易纪律'],
        lastUpdated: '2025-11-02',
      },
    ],
    [],
  );

  // 筛选术语
  const filteredTerms = useMemo(() => {
    let filtered = glossaryData;

    // 按分类筛选
    if (selectedCategory !== 'all') {
      filtered = filtered.filter((term) => term.category === selectedCategory);
    }

    // 按难度筛选
    if (selectedDifficulty !== 'all') {
      filtered = filtered.filter(
        (term) => term.difficulty === selectedDifficulty,
      );
    }

    // 按搜索查询筛选
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (term) =>
          term.term.toLowerCase().includes(query) ||
          term.definition.toLowerCase().includes(query) ||
          term.tags.some((tag) => tag.toLowerCase().includes(query)),
      );
    }

    // 限制数量
    return filtered.slice(0, maxTerms);
  }, [
    glossaryData,
    selectedCategory,
    selectedDifficulty,
    searchQuery,
    maxTerms,
  ]);

  // 分类配置
  const categoryConfig = {
    all: { label: '全部', color: 'bg-gray-100 text-gray-800', icon: BookOpen },
    basic: {
      label: '基础概念',
      color: 'bg-blue-100 text-blue-800',
      icon: Info,
    },
    strategy: {
      label: '交易策略',
      color: 'bg-green-100 text-green-800',
      icon: TrendingUp,
    },
    technical: {
      label: '技术指标',
      color: 'bg-purple-100 text-purple-800',
      icon: Calculator,
    },
    risk: {
      label: '风险管理',
      color: 'bg-red-100 text-red-800',
      icon: AlertTriangle,
    },
    advanced: {
      label: '高级概念',
      color: 'bg-yellow-100 text-yellow-800',
      icon: Star,
    },
  };

  // 难度配置
  const difficultyConfig = {
    all: { label: '全部难度', color: 'bg-gray-100 text-gray-800' },
    beginner: { label: '初级', color: 'bg-green-100 text-green-800' },
    intermediate: { label: '中级', color: 'bg-yellow-100 text-yellow-800' },
    advanced: { label: '高级', color: 'bg-red-100 text-red-800' },
  };

  // 处理术语选择
  const handleTermSelect = useCallback(
    (term: GlossaryTerm) => {
      setSelectedTerm(term);
      setIsDetailOpen(true);
      onTermSelect?.(term);

      // 添加到最近查看
      setRecentlyViewed((prev) => {
        const filtered = prev.filter((t) => t.id !== term.id);
        return [term, ...filtered].slice(0, 5);
      });
    },
    [onTermSelect],
  );

  // 处理收藏
  const toggleFavorite = useCallback((termId: string) => {
    setFavorites((prev) => {
      const newFavorites = new Set(prev);
      if (newFavorites.has(termId)) {
        newFavorites.delete(termId);
      } else {
        newFavorites.add(termId);
      }
      return newFavorites;
    });
  }, []);

  // 获取重要度标签
  const getImportanceBadge = (importance: string) => {
    const config = {
      low: { label: '低', variant: 'outline' as const },
      medium: { label: '中', variant: 'secondary' as const },
      high: { label: '高', variant: 'default' as const },
    };
    return config[importance as keyof typeof config] || config.medium;
  };

  return (
    <div className="space-y-6">
      {/* 搜索和筛选 */}
      <Card className="p-6">
        <div className="space-y-4">
          {/* 搜索框 */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="搜索术语、定义或标签..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* 筛选器 */}
          <div className="flex flex-wrap gap-4">
            {/* 分类筛选 */}
            <div className="flex items-center space-x-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">分类:</span>
              <div className="flex flex-wrap gap-2">
                {Object.entries(categoryConfig).map(([key, config]) => (
                  <Button
                    key={key}
                    variant={selectedCategory === key ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedCategory(key)}
                    className="text-xs"
                  >
                    <config.icon className="h-3 w-3 mr-1" />
                    {config.label}
                  </Button>
                ))}
              </div>
            </div>

            {/* 难度筛选 */}
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700">难度:</span>
              <div className="flex gap-2">
                {Object.entries(difficultyConfig).map(([key, config]) => (
                  <Button
                    key={key}
                    variant={selectedDifficulty === key ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSelectedDifficulty(key)}
                    className="text-xs"
                  >
                    {config.label}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* 收藏和最近查看 */}
      {(showFavorites || recentlyViewed.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {showFavorites && (
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">收藏的术语</h3>
                <Star className="h-4 w-4 text-yellow-500" />
              </div>
              {favorites.size === 0 ? (
                <p className="text-sm text-gray-500 text-center py-4">
                  暂无收藏的术语
                </p>
              ) : (
                <div className="space-y-2">
                  {Array.from(favorites).map((termId) => {
                    const term = glossaryData.find((t) => t.id === termId);
                    return term ? (
                      <div
                        key={termId}
                        className="flex items-center justify-between p-2 rounded hover:bg-gray-50 cursor-pointer"
                        onClick={() => handleTermSelect(term)}
                      >
                        <div className="flex items-center space-x-2">
                          <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
                          <span className="text-sm font-medium">
                            {term.term}
                          </span>
                        </div>
                        <ChevronRight className="h-3 w-3 text-gray-400" />
                      </div>
                    ) : null;
                  })}
                </div>
              )}
            </Card>
          )}

          {recentlyViewed.length > 0 && (
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-900">最近查看</h3>
                <Clock className="h-4 w-4 text-blue-500" />
              </div>
              <div className="space-y-2">
                {recentlyViewed.map((term) => (
                  <div
                    key={term.id}
                    className="flex items-center justify-between p-2 rounded hover:bg-gray-50 cursor-pointer"
                    onClick={() => handleTermSelect(term)}
                  >
                    <div>
                      <span className="text-sm font-medium">{term.term}</span>
                      <div className="flex items-center space-x-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {categoryConfig[term.category].label}
                        </Badge>
                        <span className="text-xs text-gray-500">
                          {term.readingTime}秒阅读
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="h-3 w-3 text-gray-400" />
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* 术语列表 */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900">
            术语库 ({filteredTerms.length} 个术语)
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredTerms.map((term) => (
            <Card
              key={term.id}
              className="p-4 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => handleTermSelect(term)}
            >
              <div className="space-y-3">
                {/* 术语头部 */}
                <div className="flex items-start justify-between">
                  <h4 className="font-medium text-gray-900">{term.term}</h4>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleFavorite(term.id);
                      }}
                      className="p-1 h-auto"
                    >
                      <Star
                        className={`h-4 w-4 ${
                          favorites.has(term.id)
                            ? 'text-yellow-500 fill-yellow-500'
                            : 'text-gray-400'
                        }`}
                      />
                    </Button>
                    <Badge
                      {...getImportanceBadge(term.importance)}
                      className="text-xs"
                    >
                      {getImportanceBadge(term.importance).label}
                    </Badge>
                  </div>
                </div>

                {/* 分类和难度 */}
                <div className="flex items-center space-x-2">
                  <Badge
                    variant="outline"
                    className={categoryConfig[term.category].color}
                  >
                    {categoryConfig[term.category].label}
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    {difficultyConfig[term.difficulty].label}
                  </Badge>
                  <div className="flex items-center space-x-1 text-xs text-gray-500">
                    <Clock className="h-3 w-3" />
                    <span>{term.readingTime}秒</span>
                  </div>
                </div>

                {/* 定义 */}
                <p className="text-sm text-gray-600 line-clamp-2">
                  {term.definition}
                </p>

                {/* 标签 */}
                <div className="flex flex-wrap gap-1">
                  {term.tags.slice(0, 3).map((tag) => (
                    <Badge key={tag} variant="outline" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                  {term.tags.length > 3 && (
                    <span className="text-xs text-gray-500">
                      +{term.tags.length - 3}
                    </span>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>

        {filteredTerms.length === 0 && (
          <div className="text-center py-8">
            <BookOpen className="h-12 w-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">未找到匹配的术语</p>
            <p className="text-sm text-gray-400 mt-1">
              尝试调整搜索条件或筛选器
            </p>
          </div>
        )}
      </Card>

      {/* 术语详情对话框 */}
      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          {selectedTerm && (
            <>
              <DialogHeader>
                <div className="flex items-center justify-between">
                  <DialogTitle className="text-xl">
                    {selectedTerm.term}
                  </DialogTitle>
                  <div className="flex items-center space-x-2">
                    <Badge {...getImportanceBadge(selectedTerm.importance)}>
                      {getImportanceBadge(selectedTerm.importance).label}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleFavorite(selectedTerm.id)}
                    >
                      <Star
                        className={`h-4 w-4 ${
                          favorites.has(selectedTerm.id)
                            ? 'text-yellow-500 fill-yellow-500'
                            : 'text-gray-400'
                        }`}
                      />
                    </Button>
                  </div>
                </div>
                <DialogDescription>
                  <div className="flex items-center space-x-3 mt-2">
                    <Badge
                      variant="outline"
                      className={categoryConfig[selectedTerm.category].color}
                    >
                      {categoryConfig[selectedTerm.category].label}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {difficultyConfig[selectedTerm.difficulty].label}
                    </Badge>
                    <div className="flex items-center space-x-1 text-xs text-gray-500">
                      <Clock className="h-3 w-3" />
                      <span>{selectedTerm.readingTime}秒阅读</span>
                    </div>
                  </div>
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-6">
                {/* 定义 */}
                <div>
                  <h4 className="font-semibold text-gray-900 mb-2">定义</h4>
                  <p className="text-gray-700">{selectedTerm.definition}</p>
                </div>

                {/* 详细解释 */}
                <div>
                  <h4 className="font-semibold text-gray-900 mb-2">详细解释</h4>
                  <p className="text-gray-700">{selectedTerm.explanation}</p>
                </div>

                {/* 示例 */}
                <div>
                  <h4 className="font-semibold text-gray-900 mb-2">实际应用</h4>
                  <ul className="space-y-2">
                    {selectedTerm.examples.map((example, index) => (
                      <li key={index} className="flex items-start space-x-2">
                        <span className="text-blue-500 mt-1">•</span>
                        <span className="text-gray-700">{example}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* 相关术语 */}
                {selectedTerm.relatedTerms.length > 0 && (
                  <div>
                    <h4 className="font-semibold text-gray-900 mb-2">
                      相关术语
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedTerm.relatedTerms.map((relatedTerm) => {
                        const relatedTermData = glossaryData.find(
                          (t) => t.term === relatedTerm,
                        );
                        return (
                          <Badge
                            key={relatedTerm}
                            variant="outline"
                            className="cursor-pointer hover:bg-gray-100"
                            onClick={() => {
                              if (relatedTermData) {
                                handleTermSelect(relatedTermData);
                              }
                            }}
                          >
                            {relatedTerm}
                          </Badge>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* 标签 */}
                <div>
                  <h4 className="font-semibold text-gray-900 mb-2">标签</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedTerm.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* 元信息 */}
                <div className="text-sm text-gray-500 border-t pt-4">
                  最后更新: {selectedTerm.lastUpdated}
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
