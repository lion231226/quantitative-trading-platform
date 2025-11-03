import { UseQueryOptions, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useRef, useEffect } from 'react';

// 帮助内容类型定义
export interface HelpContent {
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
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  estimatedReadTime: number; // 预估阅读时间（秒）
  lastViewed?: string;
  viewCount: number;
  helpfulRating: number; // 0-1 之间，表示用户评价的有用性
}

// 用户上下文
export interface UserContext {
  currentComponent: string;
  currentStep: number;
  userAction: string;
  userLevel: 'beginner' | 'intermediate' | 'advanced';
  previousActions: string[];
  timeSpentOnStep: number;
  errorsEncountered: string[];
  learningGoals: string[];
}

// 推荐结果
export interface RecommendationResult {
  content: HelpContent;
  relevanceScore: number;
  reason: string;
  confidence: number;
}

// 搜索结果
export interface SearchResult {
  content: HelpContent;
  matchScore: number;
  matchedFields: string[];
}

// 用户行为追踪
export interface UserBehavior {
  id: string;
  userId: string;
  action: 'view' | 'search' | 'like' | 'dislike' | 'bookmark';
  contentId: string;
  context: UserContext;
  timestamp: string;
  duration?: number; // 对于view动作，表示阅读时长
}

// 查询键常量
export const CONTEXT_HELP_QUERY_KEYS = {
  helpContent: ['helpContent'] as const,
  recommendations: (context: UserContext) => ['helpRecommendations', context] as const,
  search: (query: string) => ['helpSearch', query] as const,
  userBehavior: ['userBehavior'] as const,
  popularContent: ['popularContent'] as const,
} as const;

// 缓存配置
const CACHE_CONFIG = {
  helpContent: {
    staleTime: 60 * 60 * 1000, // 1 hour
    gcTime: 24 * 60 * 60 * 1000, // 24 hours
  },
  recommendations: {
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
  },
  search: {
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  },
};

// 帮助内容数据库
const HELP_CONTENT_DATABASE: HelpContent[] = [
  // 概念类内容
  {
    id: 'ma-concept',
    title: '移动平均线 (MA)',
    content: '移动平均线是技术分析中最常用的指标之一，通过计算特定周期内的平均价格来平滑价格波动，帮助识别趋势方向。简单移动平均线(SMA)给予所有价格相同权重，而指数移动平均线(EMA)给予近期价格更高权重。',
    category: 'concept',
    relatedTerms: ['SMA', 'EMA', '趋势', '技术指标', '价格平滑'],
    priority: 'high',
    context: { component: 'MovingAverageCalculation', action: 'calculate' },
    difficulty: 'beginner',
    estimatedReadTime: 45,
    viewCount: 0,
    helpfulRating: 0,
  },
  {
    id: 'golden-cross',
    title: '金叉信号',
    content: '当短期移动平均线从下向上穿过长期移动平均线时，形成金叉，通常被视为买入信号。这表明短期趋势正在转为上升，市场动能可能增强。金叉的有效性需要结合成交量和市场环境来验证。',
    category: 'concept',
    relatedTerms: ['买入信号', '趋势反转', '移动平均线', '技术分析'],
    priority: 'high',
    context: { component: 'GoldenDeathCrossAnimation', action: 'identify_signal' },
    difficulty: 'beginner',
    estimatedReadTime: 30,
    viewCount: 0,
    helpfulRating: 0,
  },
  {
    id: 'death-cross',
    title: '死叉信号',
    content: '当短期移动平均线从上向下穿过长期移动平均线时，形成死叉，通常被视为卖出信号。这表明短期趋势正在转为下降，投资者应该考虑减仓或止损。死叉信号在下跌市场中通常更可靠。',
    category: 'concept',
    relatedTerms: ['卖出信号', '趋势反转', '移动平均线', '风险控制'],
    priority: 'high',
    context: { component: 'GoldenDeathCrossAnimation', action: 'identify_signal' },
    difficulty: 'beginner',
    estimatedReadTime: 30,
    viewCount: 0,
    helpfulRating: 0,
  },

  // 功能类内容
  {
    id: 'backtesting',
    title: '策略回测',
    content: '回测是使用历史数据验证交易策略有效性的过程。通过模拟过去的市场条件来评估策略的表现，包括收益率、最大回撤、夏普比率等关键指标。回测结果仅供参考，实盘表现可能存在差异。',
    category: 'feature',
    relatedTerms: ['历史数据', '策略验证', '性能评估', '模拟交易'],
    priority: 'medium',
    difficulty: 'intermediate',
    estimatedReadTime: 60,
    viewCount: 0,
    helpfulRating: 0,
  },
  {
    id: 'parameter-optimization',
    title: '参数优化',
    content: '通过系统性地测试不同参数组合来找到策略的最优参数设置。常用的方法包括网格搜索、遗传算法等。需要注意避免过度拟合，即参数在历史数据上表现很好，但在未来数据上表现较差。',
    category: 'feature',
    relatedTerms: ['参数调优', '策略优化', '过度拟合', '网格搜索'],
    priority: 'medium',
    difficulty: 'intermediate',
    estimatedReadTime: 90,
    viewCount: 0,
    helpfulRating: 0,
  },

  // 最佳实践类内容
  {
    id: 'risk-management',
    title: '风险管理',
    content: '风险管理是量化交易中最重要的环节，包括止损设置、仓位控制和资金管理。建议单笔交易风险不超过总资金的2%，设置合理的止损位，避免情绪化交易，保持交易纪律。',
    category: 'best-practice',
    relatedTerms: ['止损', '仓位控制', '资金管理', '交易纪律'],
    priority: 'high',
    difficulty: 'beginner',
    estimatedReadTime: 75,
    viewCount: 0,
    helpfulRating: 0,
  },
  {
    id: 'portfolio-diversification',
    title: '投资组合多样化',
    content: '通过在不同资产类别、行业和地区之间分散投资来降低整体风险。多样化可以减少单一资产对组合表现的影响，提高风险调整后的收益。建议不要将所有资金投入单一策略或资产。',
    category: 'best-practice',
    relatedTerms: ['分散投资', '风险控制', '资产配置', '相关性'],
    priority: 'medium',
    difficulty: 'intermediate',
    estimatedReadTime: 60,
    viewCount: 0,
    helpfulRating: 0,
  },

  // 故障排除类内容
  {
    id: 'common-mistakes',
    title: '常见交易错误',
    content: '新手常犯的错误包括：过度交易、追涨杀跌、没有止损计划、情绪化决策、忽视风险管理、过度依赖单一指标等。了解这些错误有助于建立良好的交易习惯。',
    category: 'troubleshooting',
    relatedTerms: ['交易错误', '新手陷阱', '心理偏差', '交易纪律'],
    priority: 'high',
    difficulty: 'beginner',
    estimatedReadTime: 80,
    viewCount: 0,
    helpfulRating: 0,
  },
  {
    id: 'data-quality-issues',
    title: '数据质量问题',
    content: '在使用市场数据进行回测时，需要注意数据质量问题：缺失数据、错误数据、未来函数、幸存者偏差等。低质量的数据会导致回测结果不可靠，影响策略实盘表现。',
    category: 'troubleshooting',
    relatedTerms: ['数据清洗', '缺失数据', '未来函数', '幸存者偏差'],
    priority: 'medium',
    difficulty: 'advanced',
    estimatedReadTime: 70,
    viewCount: 0,
    helpfulRating: 0,
  }
];

// 本地存储键名
const STORAGE_KEYS = {
  USER_BEHAVIOR: 'help_user_behavior',
  CONTENT_RATINGS: 'help_content_ratings',
  PERSONALIZED_RECOMMENDATIONS: 'help_personalized_recommendations',
} as const;

// 上下文帮助推荐服务
class ContextHelpService {
  private queryClient: any;
  private userBehaviorCache: UserBehavior[] = [];
  private contentRatingsCache: Map<string, number> = new Map();

  constructor(queryClient: any) {
    this.queryClient = queryClient;
    this.loadUserDataFromStorage();
  }

  // 从本地存储加载用户数据
  private loadUserDataFromStorage() {
    try {
      const behaviorData = localStorage.getItem(STORAGE_KEYS.USER_BEHAVIOR);
      if (behaviorData) {
        this.userBehaviorCache = JSON.parse(behaviorData);
      }

      const ratingsData = localStorage.getItem(STORAGE_KEYS.CONTENT_RATINGS);
      if (ratingsData) {
        const ratings = JSON.parse(ratingsData);
        this.contentRatingsCache = new Map(Object.entries(ratings));
      }
    } catch (error) {
      console.warn('Failed to load user data from storage:', error);
    }
  }

  // 保存用户数据到本地存储
  private saveUserDataToStorage() {
    try {
      localStorage.setItem(
        STORAGE_KEYS.USER_BEHAVIOR,
        JSON.stringify(this.userBehaviorCache)
      );

      const ratingsObject = Object.fromEntries(this.contentRatingsCache);
      localStorage.setItem(
        STORAGE_KEYS.CONTENT_RATINGS,
        JSON.stringify(ratingsObject)
      );
    } catch (error) {
      console.warn('Failed to save user data to storage:', error);
    }
  }

  // 上下文分析
  analyzeContext(userContext: UserContext): {
    relevantTopics: string[];
    userIntent: 'learning' | 'troubleshooting' | 'optimization' | 'exploration';
    complexity: 'low' | 'medium' | 'high';
    confidence: number;
  } {
    const relevantTopics: string[] = [];
    let complexityScore = 0;

    // 基于组件名称分析相关主题
    if (userContext.currentComponent.toLowerCase().includes('movingaverage')) {
      relevantTopics.push('移动平均线', 'SMA', 'EMA', '趋势分析');
      complexityScore += 1;
    }
    if (userContext.currentComponent.toLowerCase().includes('cross')) {
      relevantTopics.push('金叉', '死叉', '交易信号', '趋势反转');
      complexityScore += 2;
    }
    if (userContext.currentComponent.toLowerCase().includes('parameter')) {
      relevantTopics.push('参数优化', '策略配置', '回测');
      complexityScore += 3;
    }

    // 基于用户操作分析意图
    let userIntent: 'learning' | 'troubleshooting' | 'optimization' | 'exploration' = 'learning';

    if (userContext.userAction.toLowerCase().includes('error') ||
        userContext.errorsEncountered.length > 0) {
      userIntent = 'troubleshooting';
    } else if (userContext.userAction.toLowerCase().includes('optimize') ||
               userContext.userAction.toLowerCase().includes('improve')) {
      userIntent = 'optimization';
    } else if (userContext.userAction.toLowerCase().includes('explore') ||
               userContext.timeSpentOnStep < 30) {
      userIntent = 'exploration';
    }

    // 分析复杂度
    const complexity = complexityScore <= 2 ? 'low' :
                      complexityScore <= 4 ? 'medium' : 'high';

    // 计算置信度
    let confidence = 0.3; // 基础置信度
    if (userContext.currentComponent) confidence += 0.2;
    if (userContext.userAction) confidence += 0.2;
    if (relevantTopics.length > 0) confidence += 0.2;
    if (userContext.previousActions.length > 0) confidence += 0.1;
    confidence = Math.min(confidence, 1.0);

    return {
      relevantTopics: [...new Set(relevantTopics)],
      userIntent,
      complexity,
      confidence
    };
  }

  // 智能推荐算法
  generateRecommendations(
    userContext: UserContext,
    maxResults: number = 5
  ): RecommendationResult[] {
    const contextAnalysis = this.analyzeContext(userContext);
    const scored = HELP_CONTENT_DATABASE.map(content => {
      let score = 0;
      let reason = '';

      // 1. 基于优先级的基础评分
      if (content.priority === 'high') score += 3;
      else if (content.priority === 'medium') score += 2;
      else score += 1;

      // 2. 基于上下文匹配的评分
      if (content.context?.component === userContext.currentComponent) {
        score += 8;
        reason = '组件完全匹配';
      }

      if (content.context?.action === userContext.userAction) {
        score += 6;
        reason = reason ? `${reason}, 操作匹配` : '操作匹配';
      }

      // 3. 基于相关主题匹配的评分
      const topicMatches = contextAnalysis.relevantTopics.filter(topic =>
        content.relatedTerms.some(term =>
          term.toLowerCase().includes(topic.toLowerCase()) ||
          topic.toLowerCase().includes(term.toLowerCase())
        )
      ).length;
      score += topicMatches * 2;

      if (topicMatches > 0) {
        reason = reason ? `${reason}, 主题相关` : '主题相关';
      }

      // 4. 基于用户意图的评分
      if (contextAnalysis.userIntent === 'troubleshooting' && content.category === 'troubleshooting') {
        score += 5;
        reason = reason ? `${reason}, 问题解决` : '问题解决';
      } else if (contextAnalysis.userIntent === 'learning' && content.category === 'concept') {
        score += 4;
        reason = reason ? `${reason}, 学习相关` : '学习相关';
      } else if (contextAnalysis.userIntent === 'optimization' && content.category === 'feature') {
        score += 4;
        reason = reason ? `${reason}, 优化功能` : '优化功能';
      }

      // 5. 基于用户水平的内容适配评分
      if (userContext.userLevel === 'beginner' && content.difficulty === 'beginner') score += 3;
      else if (userContext.userLevel === 'intermediate' && content.difficulty !== 'advanced') score += 2;
      else if (userContext.userLevel === 'advanced') score += 1;

      // 6. 基于个性化历史行为的评分
      const userRating = this.contentRatingsCache.get(content.id);
      if (userRating !== undefined) {
        score += userRating * 5; // 用户评价权重很高
        reason = reason ? `${reason}, 基于你的偏好` : '基于你的偏好';
      }

      // 7. 基于流行度的评分
      if (content.viewCount > 0) {
        score += Math.log(content.viewCount + 1) * 0.5;
      }

      // 8. 基于复杂度匹配的评分
      if (contextAnalysis.complexity === 'low' && content.difficulty === 'beginner') score += 2;
      else if (contextAnalysis.complexity === 'medium' && content.difficulty === 'intermediate') score += 2;
      else if (contextAnalysis.complexity === 'high' && content.difficulty === 'advanced') score += 2;

      // 计算置信度
      const confidence = Math.min(contextAnalysis.confidence + (score / 30), 1.0);

      return {
        content,
        relevanceScore: score,
        reason: reason || '通用推荐',
        confidence
      };
    });

    // 排序并返回最高分的结果
    return scored
      .sort((a, b) => b.relevanceScore - a.relevanceScore)
      .slice(0, maxResults);
  }

  // 搜索功能
  searchHelpContent(query: string, maxResults: number = 10): SearchResult[] {
    if (!query.trim()) return [];

    const searchLower = query.toLowerCase();
    const results: SearchResult[] = [];

    HELP_CONTENT_DATABASE.forEach(content => {
      let matchScore = 0;
      const matchedFields: string[] = [];

      // 标题匹配 (权重最高)
      if (content.title.toLowerCase().includes(searchLower)) {
        matchScore += 10;
        matchedFields.push('title');
      }

      // 内容匹配
      const contentMatches = (content.content.toLowerCase().match(new RegExp(searchLower, 'g')) || []).length;
      if (contentMatches > 0) {
        matchScore += contentMatches * 2;
        matchedFields.push('content');
      }

      // 相关术语匹配
      const termMatches = content.relatedTerms.filter(term =>
        term.toLowerCase().includes(searchLower)
      ).length;
      if (termMatches > 0) {
        matchScore += termMatches * 5;
        matchedFields.push('terms');
      }

      // 分类匹配
      if (content.category.toLowerCase().includes(searchLower)) {
        matchScore += 3;
        matchedFields.push('category');
      }

      if (matchScore > 0) {
        results.push({
          content,
          matchScore,
          matchedFields
        });
      }
    });

    return results
      .sort((a, b) => b.matchScore - a.matchScore)
      .slice(0, maxResults);
  }

  // 记录用户行为
  recordUserBehavior(behavior: Omit<UserBehavior, 'id' | 'timestamp'>): void {
    const fullBehavior: UserBehavior = {
      ...behavior,
      id: `${Date.now()}-${Math.random()}`,
      timestamp: new Date().toISOString(),
    };

    this.userBehaviorCache.push(fullBehavior);

    // 保持最近1000条记录
    if (this.userBehaviorCache.length > 1000) {
      this.userBehaviorCache = this.userBehaviorCache.slice(-1000);
    }

    // 异步保存到本地存储
    setTimeout(() => this.saveUserDataToStorage(), 100);

    // 更新缓存
    this.queryClient.setQueryData(
      CONTEXT_HELP_QUERY_KEYS.userBehavior,
      this.userBehaviorCache
    );
  }

  // 评价帮助内容
  rateHelpContent(contentId: string, rating: number): void {
    if (rating < 0 || rating > 1) return;

    this.contentRatingsCache.set(contentId, rating);

    // 更新内容数据库中的评分
    const content = HELP_CONTENT_DATABASE.find(c => c.id === contentId);
    if (content) {
      content.helpfulRating = rating;
    }

    this.saveUserDataToStorage();
  }

  // 获取热门内容
  getPopularContent(limit: number = 5): HelpContent[] {
    return [...HELP_CONTENT_DATABASE]
      .sort((a, b) => {
        // 综合考虑查看次数和用户评价
        const scoreA = a.viewCount + (a.helpfulRating * 10);
        const scoreB = b.viewCount + (b.helpfulRating * 10);
        return scoreB - scoreA;
      })
      .slice(0, limit);
  }

  // 获取所有帮助内容
  getAllHelpContent(): HelpContent[] {
    return HELP_CONTENT_DATABASE;
  }

  // 根据ID获取帮助内容
  getHelpContentById(id: string): HelpContent | undefined {
    return HELP_CONTENT_DATABASE.find(content => content.id === id);
  }
}

// 创建服务实例
let contextHelpServiceRef: ContextHelpService;

// React Query 集成
export const useContextHelpService = () => {
  const queryClient = useQueryClient();

  if (!contextHelpServiceRef) {
    contextHelpServiceRef = new ContextHelpService(queryClient);
  }

  return contextHelpServiceRef;
};

// 推荐内容 Hook
export const useHelpRecommendations = (
  userContext: UserContext,
  options?: UseQueryOptions<RecommendationResult[], Error>
) => {
  const contextHelpService = useContextHelpService();

  return useQuery({
    queryKey: CONTEXT_HELP_QUERY_KEYS.recommendations(userContext),
    queryFn: () => contextHelpService.generateRecommendations(userContext),
    staleTime: CACHE_CONFIG.recommendations.staleTime,
    gcTime: CACHE_CONFIG.recommendations.gcTime,
    ...options,
  });
};

// 搜索 Hook
export const useHelpSearch = (
  query: string,
  options?: UseQueryOptions<SearchResult[], Error>
) => {
  const contextHelpService = useContextHelpService();

  return useQuery({
    queryKey: CONTEXT_HELP_QUERY_KEYS.search(query),
    queryFn: () => contextHelpService.searchHelpContent(query),
    staleTime: CACHE_CONFIG.search.staleTime,
    gcTime: CACHE_CONFIG.search.gcTime,
    enabled: query.trim().length > 0,
    ...options,
  });
};

// 热门内容 Hook
export const usePopularContent = (
  limit: number = 5,
  options?: UseQueryOptions<HelpContent[], Error>
) => {
  const contextHelpService = useContextHelpService();

  return useQuery({
    queryKey: CONTEXT_HELP_QUERY_KEYS.popularContent,
    queryFn: () => contextHelpService.getPopularContent(limit),
    staleTime: CACHE_CONFIG.helpContent.staleTime,
    gcTime: CACHE_CONFIG.helpContent.gcTime,
    ...options,
  });
};

// 用户行为记录 Hook
export const useRecordUserBehavior = () => {
  const contextHelpService = useContextHelpService();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (behavior: Omit<UserBehavior, 'id' | 'timestamp'>) => {
      contextHelpService.recordUserBehavior(behavior);
      return behavior;
    },
    onSuccess: () => {
      // 刷新相关查询
      queryClient.invalidateQueries({ queryKey: ['helpRecommendations'] });
    },
  });
};

// 内容评价 Hook
export const useRateHelpContent = () => {
  const contextHelpService = useContextHelpService();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ contentId, rating }: { contentId: string; rating: number }) => {
      contextHelpService.rateHelpContent(contentId, rating);
      return { contentId, rating };
    },
    onSuccess: () => {
      // 刷新相关查询
      queryClient.invalidateQueries({ queryKey: ['helpRecommendations'] });
      queryClient.invalidateQueries({ queryKey: ['popularContent'] });
    },
  });
};

export default ContextHelpService;