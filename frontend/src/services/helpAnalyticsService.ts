import {
  UseQueryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef } from 'react';

// 使用统计类型
export interface HelpUsageStats {
  contentId: string;
  totalViews: number;
  uniqueUsers: number;
  averageReadTime: number;
  completionRate: number;
  userRatings: {
    helpful: number;
    notHelpful: number;
    averageRating: number;
  };
  searchAppearances: number;
  clickThroughRate: number;
  lastViewed: string;
  trending: boolean;
  performanceMetrics: {
    loadTime: number;
    errorRate: number;
    bounceRate: number;
  };
}

// 用户行为分析
export interface UserBehaviorAnalysis {
  userId: string;
  sessionId: string;
  totalSessions: number;
  averageSessionDuration: number;
  mostViewedCategories: string[];
  searchQueries: Array<{
    query: string;
    timestamp: string;
    resultsCount: number;
    selectedResult?: string;
  }>;
  learningPath: Array<{
    contentId: string;
    timestamp: string;
    timeSpent: number;
    completed: boolean;
    rating?: number;
  }>;
  skillProgress: {
    [skill: string]: number; // 0-1 之间
  };
  preferences: {
    preferredDifficulty: string;
    preferredFormat: string;
    preferredCategory: string;
  };
}

// 内容性能指标
export interface ContentPerformanceMetrics {
  contentId: string;
  engagement: {
    views: number;
    uniqueViews: number;
    averageTimeSpent: number;
    bounceRate: number;
  };
  quality: {
    userRating: number;
    helpfulVotes: number;
    totalVotes: number;
    reportedIssues: number;
  };
  effectiveness: {
    searchClickThroughRate: number;
    recommendationAcceptanceRate: number;
    completionRate: number;
  };
  trends: {
    dailyViews: number[];
    weeklyGrowth: number;
    monthlyGrowth: number;
    seasonalPattern: number[];
  };
}

// 推荐效果分析
export interface RecommendationAnalytics {
  recommendationId: string;
  userId: string;
  context: string;
  recommendedContent: string[];
  acceptedContent: string;
  timestamp: string;
  feedback: {
    rating: number;
    reason: string;
  };
  algorithmVersion: string;
  confidence: number;
}

// A/B 测试结果
export interface ABTestResult {
  testId: string;
  testName: string;
  variants: Array<{
    id: string;
    name: string;
    traffic: number; // 0-1 之间
    conversions: number;
    conversionRate: number;
    avgRating: number;
    avgTimeSpent: number;
  }>;
  winner: string;
  confidence: number;
  startDate: string;
  endDate: string;
  status: 'running' | 'completed' | 'paused';
}

// 查询键常量
export const HELP_ANALYTICS_QUERY_KEYS = {
  usageStats: (contentId?: string) => ['helpUsageStats', contentId] as const,
  userBehavior: (userId: string) => ['userBehaviorAnalysis', userId] as const,
  contentPerformance: (contentId: string) =>
    ['contentPerformance', contentId] as const,
  recommendationAnalytics: () => ['recommendationAnalytics'] as const,
  abTestResults: () => ['abTestResults'] as const,
  trendingContent: () => ['trendingContent'] as const,
  contentOptimization: () => ['contentOptimization'] as const,
} as const;

// 本地存储键名
const STORAGE_KEYS = {
  USAGE_STATS: 'help_usage_stats',
  USER_BEHAVIOR: 'help_user_behavior_analysis',
  CONTENT_PERFORMANCE: 'help_content_performance',
  RECOMMENDATION_ANALYTICS: 'help_recommendation_analytics',
  AB_TESTS: 'help_ab_tests',
} as const;

// 帮助分析服务
class HelpAnalyticsService {
  private queryClient: any;
  private usageStatsCache: Map<string, HelpUsageStats> = new Map();
  private userBehaviorCache: Map<string, UserBehaviorAnalysis> = new Map();
  private contentPerformanceCache: Map<string, ContentPerformanceMetrics> =
    new Map();
  private sessionStartTime: number = Date.now();
  private currentSession: string;

  constructor(queryClient: any) {
    this.queryClient = queryClient;
    this.currentSession = this.generateSessionId();
    this.loadDataFromStorage();
    this.trackSessionStart();
  }

  // 生成会话ID
  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // 从本地存储加载数据
  private loadDataFromStorage() {
    try {
      // 加载使用统计
      const usageStatsData = localStorage.getItem(STORAGE_KEYS.USAGE_STATS);
      if (usageStatsData) {
        const stats = JSON.parse(usageStatsData);
        Object.entries(stats).forEach(([contentId, stat]) => {
          this.usageStatsCache.set(contentId, stat as HelpUsageStats);
        });
      }

      // 加载用户行为分析
      const behaviorData = localStorage.getItem(STORAGE_KEYS.USER_BEHAVIOR);
      if (behaviorData) {
        const behavior = JSON.parse(behaviorData);
        Object.entries(behavior).forEach(([userId, analysis]) => {
          this.userBehaviorCache.set(userId, analysis as UserBehaviorAnalysis);
        });
      }

      // 加载内容性能数据
      const performanceData = localStorage.getItem(
        STORAGE_KEYS.CONTENT_PERFORMANCE,
      );
      if (performanceData) {
        const performance = JSON.parse(performanceData);
        Object.entries(performance).forEach(([contentId, metrics]) => {
          this.contentPerformanceCache.set(
            contentId,
            metrics as ContentPerformanceMetrics,
          );
        });
      }
    } catch (error) {
      console.warn('Failed to load analytics data from storage:', error);
    }
  }

  // 保存数据到本地存储
  private saveDataToStorage() {
    try {
      // 保存使用统计
      const usageStatsObject = Object.fromEntries(this.usageStatsCache);
      localStorage.setItem(
        STORAGE_KEYS.USAGE_STATS,
        JSON.stringify(usageStatsObject),
      );

      // 保存用户行为分析
      const behaviorObject = Object.fromEntries(this.userBehaviorCache);
      localStorage.setItem(
        STORAGE_KEYS.USER_BEHAVIOR,
        JSON.stringify(behaviorObject),
      );

      // 保存内容性能数据
      const performanceObject = Object.fromEntries(
        this.contentPerformanceCache,
      );
      localStorage.setItem(
        STORAGE_KEYS.CONTENT_PERFORMANCE,
        JSON.stringify(performanceObject),
      );
    } catch (error) {
      console.warn('Failed to save analytics data to storage:', error);
    }
  }

  // 跟踪会话开始
  private trackSessionStart() {
    // 发送会话开始事件到分析系统
    this.sendAnalyticsEvent({
      type: 'session_start',
      sessionId: this.currentSession,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      screenResolution: `${screen.width}x${screen.height}`,
    });
  }

  // 发送分析事件
  private sendAnalyticsEvent(event: any) {
    // 这里可以集成实际的分析服务
    console.log('Analytics Event:', event);

    // 模拟异步发送
    setTimeout(() => {
      // 实际实现中，这里会发送到分析服务器
    }, 100);
  }

  // 跟踪内容查看
  trackContentView(contentId: string, userId?: string) {
    const now = Date.now();
    let stats = this.usageStatsCache.get(contentId);

    if (!stats) {
      stats = this.createInitialUsageStats(contentId);
    }

    // 更新基础统计
    stats.totalViews++;
    stats.lastViewed = new Date().toISOString();

    // 更新用户行为
    if (userId) {
      let userAnalysis = this.userBehaviorCache.get(userId);
      if (!userAnalysis) {
        userAnalysis = this.createInitialUserBehaviorAnalysis(userId);
      }

      // 添加到学习路径
      userAnalysis.learningPath.push({
        contentId,
        timestamp: new Date().toISOString(),
        timeSpent: 0, // 将在 trackContentComplete 时更新
        completed: false,
      });

      // 更新最常查看的分类
      this.updateMostViewedCategories(userAnalysis, contentId);

      this.userBehaviorCache.set(userId, userAnalysis);
    }

    this.usageStatsCache.set(contentId, stats);
    this.scheduleSaveToStorage();

    // 发送分析事件
    this.sendAnalyticsEvent({
      type: 'content_view',
      contentId,
      userId,
      sessionId: this.currentSession,
      timestamp: new Date().toISOString(),
    });
  }

  // 跟踪内容完成
  trackContentComplete(
    contentId: string,
    timeSpent: number,
    rating?: number,
    userId?: string,
  ) {
    const stats = this.usageStatsCache.get(contentId);
    if (stats) {
      // 更新平均阅读时间
      const totalTimeSpent =
        stats.averageReadTime * (stats.totalViews - 1) + timeSpent;
      stats.averageReadTime = totalTimeSpent / stats.totalViews;

      // 更新完成率
      stats.completionRate =
        (stats.completionRate * (stats.totalViews - 1) + 1) / stats.totalViews;

      // 更新用户评分
      if (rating !== undefined) {
        const totalRatings =
          stats.userRatings.helpful + stats.userRatings.notHelpful;
        const newTotalRatings = totalRatings + 1;
        const newAverageRating =
          (stats.userRatings.averageRating * totalRatings + rating) /
          newTotalRatings;

        stats.userRatings.averageRating = newAverageRating;
        if (rating >= 0.6) {
          stats.userRatings.helpful++;
        } else {
          stats.userRatings.notHelpful++;
        }
      }

      this.usageStatsCache.set(contentId, stats);
    }

    // 更新用户行为
    if (userId) {
      const userAnalysis = this.userBehaviorCache.get(userId);
      if (userAnalysis) {
        const lastPathItem =
          userAnalysis.learningPath[userAnalysis.learningPath.length - 1];
        if (lastPathItem && lastPathItem.contentId === contentId) {
          lastPathItem.timeSpent = timeSpent;
          lastPathItem.completed = true;
          lastPathItem.rating = rating;
        }

        // 更新技能进度
        this.updateSkillProgress(userAnalysis, contentId, rating);

        this.userBehaviorCache.set(userId, userAnalysis);
      }
    }

    this.scheduleSaveToStorage();

    // 发送分析事件
    this.sendAnalyticsEvent({
      type: 'content_complete',
      contentId,
      userId,
      sessionId: this.currentSession,
      timeSpent,
      rating,
      timestamp: new Date().toISOString(),
    });
  }

  // 跟踪搜索行为
  trackSearch(
    query: string,
    resultsCount: number,
    selectedResult?: string,
    userId?: string,
  ) {
    // 更新搜索出现次数
    // 这里需要遍历所有相关的帮助内容并更新搜索出现次数

    // 更新用户搜索历史
    if (userId) {
      let userAnalysis = this.userBehaviorCache.get(userId);
      if (!userAnalysis) {
        userAnalysis = this.createInitialUserBehaviorAnalysis(userId);
      }

      userAnalysis.searchQueries.push({
        query,
        timestamp: new Date().toISOString(),
        resultsCount,
        selectedResult,
      });

      // 保持最近100次搜索
      if (userAnalysis.searchQueries.length > 100) {
        userAnalysis.searchQueries = userAnalysis.searchQueries.slice(-100);
      }

      this.userBehaviorCache.set(userId, userAnalysis);
    }

    this.scheduleSaveToStorage();

    // 发送分析事件
    this.sendAnalyticsEvent({
      type: 'search',
      query,
      resultsCount,
      selectedResult,
      userId,
      sessionId: this.currentSession,
      timestamp: new Date().toISOString(),
    });
  }

  // 跟踪推荐效果
  trackRecommendation(
    recommendationData: Omit<
      RecommendationAnalytics,
      'recommendationId' | 'timestamp'
    >,
  ) {
    const recommendation: RecommendationAnalytics = {
      ...recommendationData,
      recommendationId: this.generateRecommendationId(),
      timestamp: new Date().toISOString(),
    };

    // 这里应该保存推荐分析数据
    // 实际实现中需要专门的存储和查询机制

    // 发送分析事件
    this.sendAnalyticsEvent({
      type: 'recommendation',
      ...recommendation,
      timestamp: new Date().toISOString(),
    });
  }

  // 创建初始使用统计
  private createInitialUsageStats(contentId: string): HelpUsageStats {
    return {
      contentId,
      totalViews: 0,
      uniqueUsers: 0,
      averageReadTime: 0,
      completionRate: 0,
      userRatings: {
        helpful: 0,
        notHelpful: 0,
        averageRating: 0,
      },
      searchAppearances: 0,
      clickThroughRate: 0,
      lastViewed: '',
      trending: false,
      performanceMetrics: {
        loadTime: 0,
        errorRate: 0,
        bounceRate: 0,
      },
    };
  }

  // 创建初始用户行为分析
  private createInitialUserBehaviorAnalysis(
    userId: string,
  ): UserBehaviorAnalysis {
    return {
      userId,
      sessionId: this.currentSession,
      totalSessions: 1,
      averageSessionDuration: 0,
      mostViewedCategories: [],
      searchQueries: [],
      learningPath: [],
      skillProgress: {},
      preferences: {
        preferredDifficulty: 'beginner',
        preferredFormat: 'text',
        preferredCategory: 'concepts',
      },
    };
  }

  // 更新最常查看的分类
  private updateMostViewedCategories(
    userAnalysis: UserBehaviorAnalysis,
    contentId: string,
  ) {
    // 这里需要根据contentId推断分类
    // 简化实现，实际应该有分类映射
    const category = this.inferContentCategory(contentId);

    const categoryIndex = userAnalysis.mostViewedCategories.indexOf(category);
    if (categoryIndex === -1) {
      userAnalysis.mostViewedCategories.push(category);
    } else {
      // 移到最前面
      userAnalysis.mostViewedCategories.splice(categoryIndex, 1);
      userAnalysis.mostViewedCategories.unshift(category);
    }

    // 保持前5个分类
    userAnalysis.mostViewedCategories = userAnalysis.mostViewedCategories.slice(
      0,
      5,
    );
  }

  // 更新技能进度
  private updateSkillProgress(
    userAnalysis: UserBehaviorAnalysis,
    contentId: string,
    rating?: number,
  ) {
    const skills = this.inferContentSkills(contentId);
    const scoreAdjustment = rating ? rating : 0.5; // 默认中等评分

    skills.forEach((skill) => {
      const currentProgress = userAnalysis.skillProgress[skill] || 0;
      const newProgress = Math.min(1, currentProgress + scoreAdjustment * 0.1);
      userAnalysis.skillProgress[skill] = newProgress;
    });
  }

  // 推断内容分类（简化实现）
  private inferContentCategory(contentId: string): string {
    if (contentId.includes('concept') || contentId.includes('ma-'))
      return 'concepts';
    if (contentId.includes('troubleshooting') || contentId.includes('error'))
      return 'troubleshooting';
    if (contentId.includes('feature') || contentId.includes('parameter'))
      return 'features';
    if (contentId.includes('getting-started')) return 'getting-started';
    if (contentId.includes('advanced')) return 'advanced';
    return 'concepts'; // 默认分类
  }

  // 推断内容技能（简化实现）
  private inferContentSkills(contentId: string): string[] {
    const skills: string[] = [];

    if (contentId.includes('ma') || contentId.includes('moving')) {
      skills.push('moving_average');
    }
    if (contentId.includes('cross') || contentId.includes('signal')) {
      skills.push('signal_analysis');
    }
    if (contentId.includes('risk') || contentId.includes('management')) {
      skills.push('risk_management');
    }
    if (contentId.includes('parameter') || contentId.includes('optimization')) {
      skills.push('parameter_optimization');
    }

    return skills.length > 0 ? skills : ['general_trading'];
  }

  // 生成推荐ID
  private generateRecommendationId(): string {
    return `rec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // 计划保存到本地存储（防抖）
  private scheduleSaveToStorage() {
    setTimeout(() => this.saveDataToStorage(), 1000);
  }

  // 获取使用统计
  getUsageStats(contentId?: string): HelpUsageStats[] {
    if (contentId) {
      const stats = this.usageStatsCache.get(contentId);
      return stats ? [stats] : [];
    }
    return Array.from(this.usageStatsCache.values());
  }

  // 获取用户行为分析
  getUserBehaviorAnalysis(userId: string): UserBehaviorAnalysis | null {
    return this.userBehaviorCache.get(userId) || null;
  }

  // 获取内容性能指标
  getContentPerformance(contentId: string): ContentPerformanceMetrics | null {
    const stats = this.usageStatsCache.get(contentId);
    if (!stats) return null;

    return {
      contentId,
      engagement: {
        views: stats.totalViews,
        uniqueViews: stats.uniqueUsers,
        averageTimeSpent: stats.averageReadTime,
        bounceRate: stats.performanceMetrics.bounceRate,
      },
      quality: {
        userRating: stats.userRatings.averageRating,
        helpfulVotes: stats.userRatings.helpful,
        totalVotes: stats.userRatings.helpful + stats.userRatings.notHelpful,
        reportedIssues: 0, // 需要另外跟踪
      },
      effectiveness: {
        searchClickThroughRate: stats.clickThroughRate,
        recommendationAcceptanceRate: 0, // 需要另外跟踪
        completionRate: stats.completionRate,
      },
      trends: {
        dailyViews: [], // 需要历史数据
        weeklyGrowth: 0, // 需要计算
        monthlyGrowth: 0, // 需要计算
        seasonalPattern: [], // 需要历史数据
      },
    };
  }

  // 获取热门内容
  getTrendingContent(limit: number = 10): HelpUsageStats[] {
    return Array.from(this.usageStatsCache.values())
      .filter((stats) => stats.trending)
      .sort((a, b) => {
        // 综合评分算法
        const scoreA =
          a.totalViews * 0.3 +
          a.userRatings.averageRating * a.totalViews * 0.4 +
          a.completionRate * a.totalViews * 0.3;
        const scoreB =
          b.totalViews * 0.3 +
          b.userRatings.averageRating * b.totalViews * 0.4 +
          b.completionRate * b.totalViews * 0.3;
        return scoreB - scoreA;
      })
      .slice(0, limit);
  }

  // 获取内容优化建议
  getContentOptimizationSuggestions(): Array<{
    contentId: string;
    issue: string;
    suggestion: string;
    priority: 'high' | 'medium' | 'low';
    potentialImpact: string;
  }> {
    const suggestions: Array<{
      contentId: string;
      issue: string;
      suggestion: string;
      priority: 'high' | 'medium' | 'low';
      potentialImpact: string;
    }> = [];

    this.usageStatsCache.forEach((stats, contentId) => {
      // 检查低评分内容
      if (stats.userRatings.averageRating < 0.4 && stats.totalViews > 10) {
        suggestions.push({
          contentId,
          issue: '用户评分较低',
          suggestion: '审查内容准确性，添加更多示例，改进表述方式',
          priority: 'high',
          potentialImpact: '提升用户满意度 25-40%',
        });
      }

      // 检查低完成率
      if (stats.completionRate < 0.3 && stats.totalViews > 20) {
        suggestions.push({
          contentId,
          issue: '内容完成率低',
          suggestion: '简化内容结构，增加互动元素，减少阅读时间',
          priority: 'medium',
          potentialImpact: '提升完成率 20-35%',
        });
      }

      // 检查高跳出率
      if (stats.performanceMetrics.bounceRate > 0.8 && stats.totalViews > 15) {
        suggestions.push({
          contentId,
          issue: '用户跳出率高',
          suggestion: '改进内容摘要，确保标题准确反映内容，添加快速导航',
          priority: 'high',
          potentialImpact: '降低跳出率 15-30%',
        });
      }

      // 检查平均阅读时间过短
      if (stats.averageReadTime < 30 && stats.totalViews > 10) {
        suggestions.push({
          contentId,
          issue: '阅读时间过短',
          suggestion: '可能内容不够深入或缺乏吸引力，建议增加案例和实际应用',
          priority: 'medium',
          potentialImpact: '提升参与度 20-25%',
        });
      }
    });

    return suggestions.sort((a, b) => {
      const priorityWeight = { high: 3, medium: 2, low: 1 };
      return priorityWeight[b.priority] - priorityWeight[a.priority];
    });
  }

  // 分析推荐算法效果
  analyzeRecommendationPerformance(): {
    overallAccuracy: number;
    categoryBreakdown: Record<string, number>;
    improvementSuggestions: string[];
  } {
    // 这里需要分析实际推荐数据
    // 简化实现，返回模拟数据
    return {
      overallAccuracy: 0.72,
      categoryBreakdown: {
        concepts: 0.78,
        features: 0.65,
        troubleshooting: 0.81,
        'getting-started': 0.74,
        advanced: 0.62,
      },
      improvementSuggestions: [
        '增加用户行为权重，提升个性化程度',
        '优化上下文分析算法，提高相关性判断',
        '引入时效性因子，优先推荐最新内容',
        '考虑用户学习路径，推荐渐进式内容',
      ],
    };
  }
}

// 创建服务实例
let helpAnalyticsServiceRef: HelpAnalyticsService;

// React Query 集成
export const useHelpAnalyticsService = () => {
  const queryClient = useQueryClient();

  if (!helpAnalyticsServiceRef) {
    helpAnalyticsServiceRef = new HelpAnalyticsService(queryClient);
  }

  return helpAnalyticsServiceRef;
};

// 使用统计 Hook
export const useHelpUsageStats = (
  contentId?: string,
  options?: UseQueryOptions<HelpUsageStats[], Error>,
) => {
  const helpAnalyticsService = useHelpAnalyticsService();

  return useQuery({
    queryKey: HELP_ANALYTICS_QUERY_KEYS.usageStats(contentId),
    queryFn: () => helpAnalyticsService.getUsageStats(contentId),
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
};

// 用户行为分析 Hook
export const useUserBehaviorAnalysis = (
  userId: string,
  options?: UseQueryOptions<UserBehaviorAnalysis | null, Error>,
) => {
  const helpAnalyticsService = useHelpAnalyticsService();

  return useQuery({
    queryKey: HELP_ANALYTICS_QUERY_KEYS.userBehavior(userId),
    queryFn: () => helpAnalyticsService.getUserBehaviorAnalysis(userId),
    staleTime: 2 * 60 * 1000, // 2 minutes
    ...options,
  });
};

// 内容性能指标 Hook
export const useContentPerformance = (
  contentId: string,
  options?: UseQueryOptions<ContentPerformanceMetrics | null, Error>,
) => {
  const helpAnalyticsService = useHelpAnalyticsService();

  return useQuery({
    queryKey: HELP_ANALYTICS_QUERY_KEYS.contentPerformance(contentId),
    queryFn: () => helpAnalyticsService.getContentPerformance(contentId),
    staleTime: 10 * 60 * 1000, // 10 minutes
    ...options,
  });
};

// 热门内容 Hook
export const useTrendingContent = (
  limit: number = 10,
  options?: UseQueryOptions<HelpUsageStats[], Error>,
) => {
  const helpAnalyticsService = useHelpAnalyticsService();

  return useQuery({
    queryKey: HELP_ANALYTICS_QUERY_KEYS.trendingContent(),
    queryFn: () => helpAnalyticsService.getTrendingContent(limit),
    staleTime: 15 * 60 * 1000, // 15 minutes
    ...options,
  });
};

// 内容优化建议 Hook
export const useContentOptimizationSuggestions = (
  options?: UseQueryOptions<
    Array<{
      contentId: string;
      issue: string;
      suggestion: string;
      priority: 'high' | 'medium' | 'low';
      potentialImpact: string;
    }>,
    Error
  >,
) => {
  const helpAnalyticsService = useHelpAnalyticsService();

  return useQuery({
    queryKey: HELP_ANALYTICS_QUERY_KEYS.contentOptimization(),
    queryFn: () => helpAnalyticsService.getContentOptimizationSuggestions(),
    staleTime: 30 * 60 * 1000, // 30 minutes
    ...options,
  });
};

export default HelpAnalyticsService;
