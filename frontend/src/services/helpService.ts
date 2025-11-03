import { UseQueryOptions, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useMemo, useRef, useEffect, useState } from 'react';
import { HelpDocument, FAQItem, UserFeedback, UXError } from '@/types/ux.types';

// 查询键常量
export const HELP_QUERY_KEYS = {
  documents: (category?: string) => ['helpDocuments', category] as const,
  faq: (category?: string, search?: string) => ['faq', category, search] as const,
  feedback: () => ['userFeedback'] as const,
  errors: () => ['uxErrors'] as const,
} as const;

/**
 * 帮助文档服务
 */
export class HelpDocumentService {
  private documents: HelpDocument[] = [];
  private searchIndex: Map<string, Set<string>> = new Map();

  constructor() {
    this.initializeDefaultDocuments();
  }

  /**
   * 初始化默认帮助文档
   */
  private initializeDefaultDocuments(): void {
    this.documents = [
      {
        id: 'getting-started',
        title: '快速入门指南',
        content: `# 量化交易策略分析平台 - 快速入门

欢迎使用量化交易策略分析平台！本指南将帮助您快速上手平台的主要功能。

## 1. 平台概述

本平台是一个专业的量化交易策略分析工具，主要提供：
- 单均线策略回测分析
- 实时数据可视化
- 性能指标计算
- 多策略对比分析
- 交互式教程系统

## 2. 基本操作流程

### 2.1 选择策略
1. 在策略选择页面选择您想要分析的单均线策略
2. 设置策略参数（如均线周期、交易规则等）

### 2.2 配置参数
- 初始资金设置
- 交易手续费配置
- 回测时间范围选择
- 基准指数选择（可选）

### 2.3 运行分析
1. 点击"开始分析"按钮
2. 等待系统计算完成
3. 查看分析结果和图表

### 2.4 结果解读
- 总收益率和年化收益率
- 最大回撤和回撤期
- 夏普比率等风险指标
- 交易统计信息

## 3. 常用功能

### 3.1 数据可视化
- 收益曲线图
- 回撤分析图
- 滚动收益率图
- 月度收益热力图

### 3.2 策略对比
- 多策略同时对比
- 基准对比分析
- 相关性分析

### 3.3 性能监控
- 实时性能指标
- 交易执行监控
- 风险指标追踪

## 4. 注意事项

1. **数据质量**：确保使用高质量的历史数据
2. **参数设置**：合理设置策略参数避免过拟合
3. **风险控制**：注意风险管理和仓位控制
4. **市场环境**：考虑不同市场环境下的策略表现

## 5. 获取帮助

- 查看详细教程：使用交互式教程系统
- 阅读FAQ：查看常见问题解答
- 联系支持：通过反馈功能联系我们

祝您使用愉快！`,
        category: 'getting_started',
        tags: ['入门', '基础', '教程'],
        order: 1,
        lastUpdated: new Date().toISOString(),
        author: '系统',
        difficulty: 'beginner',
        estimatedReadTime: 10,
        relatedDocuments: ['strategy-basics', 'risk-management'],
        searchableContent: '快速入门 基础操作 策略选择 参数设置 回测分析 结果解读',
      },
      {
        id: 'strategy-basics',
        title: '单均线策略基础',
        content: `# 单均线策略基础

## 策略原理

单均线策略是最基本的技术分析策略之一，基于移动平均线来判断市场趋势和交易信号。

## 移动平均线类型

### 简单移动平均线（SMA）
- 计算方法：特定时间段内收盘价的算术平均值
- 优点：简单易懂，平滑性好
- 缺点：滞后性较强

### 指数移动平均线（EMA）
- 计算方法：给予近期价格更高权重的平均值
- 优点：反应更迅速，滞后性较小
- 缺点：可能过于敏感

## 交易信号

### 金叉信号（买入）
- 短期均线从下向上穿过长期均线
- 表示上升趋势可能开始

### 死叉信号（卖出）
- 短期均线从上向下穿过长期均线
- 表示下降趋势可能开始

## 参数选择

### 均线周期
- 短期：5-20日，适合短线交易
- 中期：20-60日，适合中线交易
- 长期：60-200日，适合长线交易

### 常用组合
- 5日和20日均线
- 10日和30日均线
- 20日和60日均线

## 策略优缺点

### 优点
- 简单直观，容易理解
- 能够捕捉主要趋势
- 风险相对可控

### 缺点
- 震荡市中容易产生假信号
- 滞后性可能导致错过最佳时机
- 需要配合其他指标使用

## 使用建议

1. **趋势确认**：配合趋势指标使用
2. **参数优化**：根据不同品种调整参数
3. **风险控制**：设置止损止盈
4. **资金管理**：合理分配仓位`,
        category: 'features',
        tags: ['策略', '均线', '技术分析', '交易信号'],
        order: 2,
        lastUpdated: new Date().toISOString(),
        author: '系统',
        difficulty: 'intermediate',
        estimatedReadTime: 8,
        relatedDocuments: ['risk-management', 'performance-analysis'],
        searchableContent: '单均线 移动平均线 SMA EMA 金叉 死叉 交易信号 技术分析',
      },
      {
        id: 'troubleshooting',
        title: '常见问题排除',
        content: `# 常见问题排除

## 数据问题

### 问题：数据显示不完整
**可能原因：**
- 网络连接不稳定
- 数据源暂时不可用
- 选择的时间范围超出可用数据

**解决方案：**
1. 检查网络连接
2. 刷新页面重试
3. 选择较短的时间范围
4. 联系技术支持

### 问题：数据更新缓慢
**可能原因：**
- 大量数据计算
- 服务器负载较高
- 网络延迟

**解决方案：**
1. 缩短分析时间范围
2. 减少同时分析的策略数量
3. 清除浏览器缓存
4. 尝试使用非高峰时段

## 策略分析问题

### 问题：回测结果异常
**可能原因：**
- 参数设置不合理
- 数据质量问题
- 策略逻辑错误

**解决方案：**
1. 检查策略参数设置
2. 验证数据完整性
3. 使用默认参数测试
4. 查看详细日志信息

### 问题：图表无法显示
**可能原因：**
- 浏览器兼容性问题
- JavaScript被禁用
- 图表数据格式错误

**解决方案：**
1. 更新浏览器到最新版本
2. 启用JavaScript
3. 清除浏览器缓存
4. 尝试使用其他浏览器

## 性能问题

### 问题：页面响应缓慢
**可能原因：**
- 数据量过大
- 浏览器内存不足
- 复杂计算任务

**解决方案：**
1. 减少数据量
2. 关闭其他浏览器标签页
3. 重启浏览器
4. 使用性能更好的设备

### 问题：内存使用过高
**可能原因：**
- 大量图表渲染
- 数据缓存积累
- 内存泄漏

**解决方案：**
1. 定期刷新页面
2. 清除浏览器数据
3. 关闭不需要的功能
4. 重启浏览器

## 账户和权限问题

### 问题：无法登录
**可能原因：**
- 用户名或密码错误
- 账户被锁定
- 网络连接问题

**解决方案：**
1. 检查用户名和密码
2. 使用忘记密码功能
3. 联系管理员解锁账户
4. 检查网络连接

### 问题：功能访问受限
**可能原因：**
- 权限级别不足
- 账户过期
- 功能维护中

**解决方案：**
1. 联系管理员申请权限
2. 确认账户状态
3. 查看系统维护通知
4. 升级账户级别

## 其他问题

### 问题：无法导出数据
**可能原因：**
- 浏览器安全设置
- 文件下载限制
- 格式不支持

**解决方案：**
1. 调整浏览器安全设置
2. 使用不同的文件格式
3. 检查下载权限
4. 尝试其他浏览器

### 问题：移动端显示异常
**可能原因：**
- 浏览器兼容性
- 屏幕尺寸适配
- 触摸操作问题

**解决方案：**
1. 使用推荐的移动浏览器
2. 调整屏幕方向
3. 使用桌面版本
4. 更新浏览器版本

## 联系支持

如果以上解决方案无法解决您的问题，请：
1. 详细描述问题现象
2. 提供错误信息截图
3. 说明操作步骤
4. 联系技术支持团队`,
        category: 'troubleshooting',
        tags: ['问题', '故障排除', '常见问题', '解决方案'],
        order: 3,
        lastUpdated: new Date().toISOString(),
        author: '系统',
        difficulty: 'beginner',
        estimatedReadTime: 12,
        relatedDocuments: ['getting-started', 'contact-support'],
        searchableContent: '故障排除 常见问题 解决方案 技术支持 数据问题 性能问题',
      },
    ];

    this.buildSearchIndex();
  }

  /**
   * 构建搜索索引
   */
  private buildSearchIndex(): void {
    this.searchIndex.clear();

    this.documents.forEach(doc => {
      const searchableContent = `${doc.title} ${doc.content} ${doc.tags.join(' ')} ${doc.searchableContent}`.toLowerCase();
      const words = searchableContent.split(/\s+/);

      words.forEach(word => {
        if (word.length > 2) { // 忽略过短的词
          if (!this.searchIndex.has(word)) {
            this.searchIndex.set(word, new Set());
          }
          this.searchIndex.get(word)!.add(doc.id);
        }
      });
    });
  }

  /**
   * 搜索文档
   */
  searchDocuments(query: string, category?: string): HelpDocument[] {
    if (!query.trim()) {
      return this.getDocumentsByCategory(category);
    }

    const queryWords = query.toLowerCase().split(/\s+/);
    const docScores = new Map<string, number>();

    queryWords.forEach(word => {
      const matchingDocs = this.searchIndex.get(word);
      if (matchingDocs) {
        matchingDocs.forEach(docId => {
          docScores.set(docId, (docScores.get(docId) || 0) + 1);
        });
      }
    });

    // 按相关性排序
    const sortedDocs = Array.from(docScores.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([docId]) => this.documents.find(doc => doc.id === docId))
      .filter(Boolean) as HelpDocument[];

    // 按类别过滤
    if (category) {
      return sortedDocs.filter(doc => doc.category === category);
    }

    return sortedDocs;
  }

  /**
   * 按类别获取文档
   */
  getDocumentsByCategory(category?: string): HelpDocument[] {
    if (category) {
      return this.documents.filter(doc => doc.category === category);
    }
    return this.documents;
  }

  /**
   * 获取单个文档
   */
  getDocumentById(id: string): HelpDocument | undefined {
    return this.documents.find(doc => doc.id === id);
  }

  /**
   * 获取相关文档
   */
  getRelatedDocuments(documentId: string): HelpDocument[] {
    const doc = this.getDocumentById(documentId);
    if (!doc) return [];

    return doc.relatedDocuments
      .map(id => this.getDocumentById(id))
      .filter(Boolean) as HelpDocument[];
  }
}

/**
 * FAQ服务
 */
export class FAQService {
  private faqItems: FAQItem[] = [];

  constructor() {
    this.initializeDefaultFAQs();
  }

  /**
   * 初始化默认FAQ
   */
  private initializeDefaultFAQs(): void {
    this.faqItems = [
      {
        id: 'what-is-quant-trading',
        question: '什么是量化交易？',
        answer: '量化交易是利用数学模型和计算机算法来执行交易策略的方法。它通过分析历史数据、识别市场模式和自动化交易决策，来减少人为情绪影响并提高交易效率。',
        category: '基础概念',
        tags: ['量化交易', '算法交易', '基础'],
        popularity: 156,
        helpful: 89,
        notHelpful: 12,
        lastUpdated: new Date().toISOString(),
        relatedQuestions: ['what-is-moving-average', 'how-to-start-quant-trading'],
      },
      {
        id: 'what-is-moving-average',
        question: '什么是移动平均线？',
        answer: '移动平均线是技术分析中常用的指标，通过计算特定时间段内价格的平均值来平滑价格波动。常见的有简单移动平均线(SMA)和指数移动平均线(EMA)。单均线策略就是基于移动平均线来判断买卖时机的交易策略。',
        category: '技术指标',
        tags: ['移动平均线', '技术分析', '指标'],
        popularity: 203,
        helpful: 167,
        notHelpful: 8,
        lastUpdated: new Date().toISOString(),
        relatedQuestions: ['what-is-quant-trading', 'how-to-choose-MA-period'],
      },
      {
        id: 'how-to-start-quant-trading',
        question: '如何开始量化交易？',
        answer: '开始量化交易需要：1) 学习基础的技术分析和编程知识；2) 选择合适的交易平台和工具；3) 收集高质量的历史数据；4) 开发和测试交易策略；5) 进行严格的风险管理；6) 从小资金开始实盘交易。建议先通过模拟交易积累经验。',
        category: '入门指南',
        tags: ['入门', '学习', '步骤'],
        popularity: 189,
        helpful: 145,
        notHelpful: 15,
        lastUpdated: new Date().toISOString(),
        relatedQuestions: ['what-is-quant-trading', 'risk-management-tips'],
      },
      {
        id: 'how-to-choose-MA-period',
        question: '如何选择移动平均线的周期？',
        answer: '选择MA周期需要考虑：1) 交易时间框架（短线用5-20日，中线用20-60日，长线用60-200日）；2) 市场波动性（高波动市场使用较长周期）；3) 个人交易风格（激进vs保守）；4) 历史回测表现。建议通过回测不同参数组合来找到最优配置。',
        category: '策略配置',
        tags: ['参数选择', '优化', '配置'],
        popularity: 134,
        helpful: 98,
        notHelpful: 18,
        lastUpdated: new Date().toISOString(),
        relatedQuestions: ['what-is-moving-average', 'backtesting-tips'],
      },
      {
        id: 'risk-management-tips',
        question: '量化交易中的风险管理要点？',
        answer: '风险管理要点包括：1) 设置合理的止损点位（通常2-5%）；2) 控制单笔交易仓位（不超过总资金的5-10%）；3) 分散投资降低单一风险；4) 监控最大回撤；5) 保持充足的风险准备金；6) 定期评估和调整策略。记住：保住本金比追求利润更重要。',
        category: '风险管理',
        tags: ['风险', '管理', '止损'],
        popularity: 178,
        helpful: 156,
        notHelpful: 9,
        lastUpdated: new Date().toISOString(),
        relatedQuestions: ['how-to-start-quant-trading', 'position-sizing'],
      },
      {
        id: 'backtesting-tips',
        question: '策略回测需要注意什么？',
        answer: '策略回测注意事项：1) 使用足够长的历史数据（至少3-5年）；2) 包含不同市场环境（牛市、熊市、震荡市）；3) 考虑交易成本和滑点；4) 避免过度拟合历史数据；5) 进行样本外测试；6) 关注最大回撤和夏普比率等风险指标；7) 定期重新评估策略有效性。',
        category: '策略测试',
        tags: ['回测', '测试', '验证'],
        popularity: 145,
        helpful: 123,
        notHelpful: 14,
        lastUpdated: new Date().toISOString(),
        relatedQuestions: ['how-to-choose-MA-period', 'strategy-evaluation'],
      },
      {
        id: 'data-quality-issues',
        question: '如何处理数据质量问题？',
        answer: '处理数据质量问题：1) 选择可靠的数据源（如官方交易所、知名数据供应商）；2) 进行数据清洗（处理缺失值、异常值、重复数据）；3) 验证数据一致性；4) 定期更新数据；5) 建立数据监控机制；6) 对多个数据源进行交叉验证。垃圾进，垃圾出，数据质量直接影响策略效果。',
        category: '数据管理',
        tags: ['数据', '质量', '清洗'],
        popularity: 98,
        helpful: 87,
        notHelpful: 6,
        lastUpdated: new Date().toISOString(),
        relatedQuestions: ['data-sources', 'data-processing'],
      },
      {
        id: 'platform-features',
        question: '平台支持哪些主要功能？',
        answer: '平台主要功能包括：1) 单均线策略回测和分析；2) 实时数据可视化图表；3) 多策略对比分析；4) 详细的性能指标计算；5) 交互式教程系统；6) 风险管理工具；7) 数据导出功能；8) 移动端适配。我们持续更新功能，欢迎反馈建议。',
        category: '平台功能',
        tags: ['功能', '特性', '平台'],
        popularity: 167,
        helpful: 134,
        notHelpful: 11,
        lastUpdated: new Date().toISOString(),
        relatedQuestions: ['getting-started', 'data-sources'],
      },
    ];
  }

  /**
   * 搜索FAQ
   */
  searchFAQs(query: string, category?: string): FAQItem[] {
    if (!query.trim()) {
      return this.getFAQsByCategory(category);
    }

    const queryLower = query.toLowerCase();
    return this.faqItems.filter(faq => {
      const matchesCategory = !category || faq.category === category;
      const matchesQuery =
        faq.question.toLowerCase().includes(queryLower) ||
        faq.answer.toLowerCase().includes(queryLower) ||
        faq.tags.some(tag => tag.toLowerCase().includes(queryLower));

      return matchesCategory && matchesQuery;
    }).sort((a, b) => b.popularity - a.popularity);
  }

  /**
   * 按类别获取FAQ
   */
  getFAQsByCategory(category?: string): FAQItem[] {
    if (category) {
      return this.faqItems.filter(faq => faq.category === category);
    }
    return this.faqItems.sort((a, b) => b.popularity - a.popularity);
  }

  /**
   * 获取热门FAQ
   */
  getPopularFAQs(limit: number = 5): FAQItem[] {
    return this.faqItems
      .sort((a, b) => b.popularity - a.popularity)
      .slice(0, limit);
  }

  /**
   * 记录FAQ反馈
   */
  recordFAQFeedback(faqId: string, helpful: boolean): void {
    const faq = this.faqItems.find(item => item.id === faqId);
    if (faq) {
      if (helpful) {
        faq.helpful++;
      } else {
        faq.notHelpful++;
      }
      faq.lastUpdated = new Date().toISOString();
    }
  }

  /**
   * 获取FAQ分类
   */
  getFAQCategories(): string[] {
    return Array.from(new Set(this.faqItems.map(faq => faq.category)));
  }
}

/**
 * 用户反馈服务
 */
export class UserFeedbackService {
  private feedback: UserFeedback[] = [];
  private errors: UXError[] = [];

  /**
   * 提交反馈
   */
  async submitFeedback(feedbackData: Omit<UserFeedback, 'id' | 'timestamp' | 'sessionId'>): Promise<UserFeedback> {
    const feedback: UserFeedback = {
      ...feedbackData,
      id: `feedback_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      sessionId: this.getSessionId(),
    };

    this.feedback.push(feedback);

    // 在实际应用中，这里会发送到服务器
    console.log('[Feedback Service] New feedback submitted:', feedback);

    return feedback;
  }

  /**
   * 记录错误
   */
  recordError(errorData: Omit<UXError, 'id' | 'timestamp' | 'sessionId'>): UXError {
    const error: UXError = {
      ...errorData,
      id: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      sessionId: this.getSessionId(),
    };

    this.errors.push(error);

    // 在实际应用中，这里会发送到错误监控服务
    console.error('[Error Service] New error recorded:', error);

    return error;
  }

  /**
   * 获取用户反馈历史
   */
  getUserFeedback(): UserFeedback[] {
    return this.feedback.sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }

  /**
   * 获取错误历史
   */
  getErrors(): UXError[] {
    return this.errors.sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }

  /**
   * 获取会话ID
   */
  private getSessionId(): string {
    let sessionId = sessionStorage.getItem('ux_session_id');
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('ux_session_id', sessionId);
    }
    return sessionId;
  }
}

// 服务实例
const helpDocumentService = new HelpDocumentService();
const faqService = new FAQService();
const userFeedbackService = new UserFeedbackService();

/**
 * 帮助文档Hook
 */
export function useHelpDocuments(category?: string) {
  return useQuery({
    queryKey: HELP_QUERY_KEYS.documents(category),
    queryFn: () => helpDocumentService.getDocumentsByCategory(category),
    staleTime: 10 * 60 * 1000, // 10分钟
  });
}

/**
 * 搜索帮助文档Hook
 */
export function useSearchHelpDocuments(query: string, category?: string) {
  return useQuery({
    queryKey: ['searchHelpDocuments', query, category],
    queryFn: () => helpDocumentService.searchDocuments(query, category),
    enabled: query.trim().length > 0,
    staleTime: 5 * 60 * 1000, // 5分钟
  });
}

/**
 * FAQ Hook
 */
export function useFAQ(category?: string) {
  return useQuery({
    queryKey: HELP_QUERY_KEYS.faq(category),
    queryFn: () => faqService.getFAQsByCategory(category),
    staleTime: 10 * 60 * 1000, // 10分钟
  });
}

/**
 * 搜索FAQ Hook
 */
export function useSearchFAQs(query: string, category?: string) {
  return useQuery({
    queryKey: ['searchFAQs', query, category],
    queryFn: () => faqService.searchFAQs(query, category),
    enabled: query.trim().length > 0,
    staleTime: 5 * 60 * 1000, // 5分钟
  });
}

/**
 * 提交反馈Hook
 */
export function useSubmitFeedback() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (feedbackData: Omit<UserFeedback, 'id' | 'timestamp' | 'sessionId'>) =>
      userFeedbackService.submitFeedback(feedbackData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: HELP_QUERY_KEYS.feedback() });
    },
  });
}

/**
 * 记录错误Hook
 */
export function useRecordError() {
  return useMutation({
    mutationFn: (errorData: Omit<UXError, 'id' | 'timestamp' | 'sessionId'>) =>
      userFeedbackService.recordError(errorData),
  });
}

// 导出服务
export const helpService = {
  helpDocumentService,
  faqService,
  userFeedbackService,
  useHelpDocuments,
  useSearchHelpDocuments,
  useFAQ,
  useSearchFAQs,
  useSubmitFeedback,
  useRecordError,
  QUERY_KEYS: HELP_QUERY_KEYS,
};