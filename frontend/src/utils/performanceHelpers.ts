import {
  MetricDisplayConfig,
  MetricFormatConfig,
  PerformanceChartData,
  PerformanceMetrics,
  ReturnDataPoint,
} from '@/types/performance.types';
import {
  PagePerformanceMetrics,
  PerformanceThreshold,
  UXMetrics,
} from '@/types/ux.types';
import { useCallback, useEffect, useRef } from 'react';

/**
 * 绩效指标格式化配置
 */
export const METRIC_DISPLAY_CONFIGS: Record<
  keyof PerformanceMetrics,
  MetricDisplayConfig
> = {
  strategyId: {
    key: 'strategyId',
    label: '策略ID',
    format: { decimals: 0 },
    importance: 'low',
    category: 'returns',
  },
  totalReturn: {
    key: 'totalReturn',
    label: '总收益率',
    format: { decimals: 2, formatAsPercentage: true, colorCode: 'positive' },
    importance: 'high',
    category: 'returns',
  },
  annualizedReturn: {
    key: 'annualizedReturn',
    label: '年化收益率',
    format: { decimals: 2, formatAsPercentage: true, colorCode: 'positive' },
    importance: 'high',
    category: 'returns',
  },
  maxDrawdown: {
    key: 'maxDrawdown',
    label: '最大回撤',
    format: { decimals: 2, formatAsPercentage: true, colorCode: 'negative' },
    importance: 'high',
    category: 'risk',
  },
  maxDrawdownPeriod: {
    key: 'maxDrawdownPeriod',
    label: '最大回撤期',
    format: { decimals: 0, suffix: '天' },
    importance: 'medium',
    category: 'risk',
  },
  volatility: {
    key: 'volatility',
    label: '波动率',
    format: { decimals: 2, formatAsPercentage: true },
    importance: 'medium',
    category: 'risk',
  },
  sharpeRatio: {
    key: 'sharpeRatio',
    label: '夏普比率',
    format: { decimals: 3 },
    importance: 'high',
    category: 'efficiency',
  },
  sortinoRatio: {
    key: 'sortinoRatio',
    label: '索提诺比率',
    format: { decimals: 3 },
    importance: 'medium',
    category: 'efficiency',
  },
  winRate: {
    key: 'winRate',
    label: '胜率',
    format: { decimals: 2, formatAsPercentage: true, colorCode: 'positive' },
    importance: 'high',
    category: 'trading',
  },
  profitLossRatio: {
    key: 'profitLossRatio',
    label: '盈亏比',
    format: { decimals: 2 },
    importance: 'medium',
    category: 'trading',
  },
  totalTrades: {
    key: 'totalTrades',
    label: '总交易次数',
    format: { decimals: 0 },
    importance: 'medium',
    category: 'trading',
  },
  profitableTrades: {
    key: 'profitableTrades',
    label: '盈利交易',
    format: { decimals: 0 },
    importance: 'low',
    category: 'trading',
  },
  averageTrade: {
    key: 'averageTrade',
    label: '平均交易',
    format: { decimals: 2, formatAsCurrency: true },
    importance: 'low',
    category: 'trading',
  },
  expectancy: {
    key: 'expectancy',
    label: '期望值',
    format: { decimals: 2, formatAsCurrency: true },
    importance: 'medium',
    category: 'trading',
  },
  calmarRatio: {
    key: 'calmarRatio',
    label: '卡尔玛比率',
    format: { decimals: 3 },
    importance: 'medium',
    category: 'efficiency',
  },
  calculationDate: {
    key: 'calculationDate',
    label: '计算日期',
    format: {},
    importance: 'low',
    category: 'returns',
  },
  periodStart: {
    key: 'periodStart',
    label: '期间开始',
    format: {},
    importance: 'low',
    category: 'returns',
  },
  periodEnd: {
    key: 'periodEnd',
    label: '期间结束',
    format: {},
    importance: 'low',
    category: 'returns',
  },
  dataPoints: {
    key: 'dataPoints',
    label: '数据点',
    format: { decimals: 0 },
    importance: 'low',
    category: 'returns',
  },
};

/**
 * 格式化绩效指标值
 */
export function formatMetricValue(
  value: number | string | undefined,
  config: MetricFormatConfig,
): string {
  if (value === undefined || value === null) {
    return '—';
  }

  const numValue = typeof value === 'string' ? parseFloat(value) : value;

  if (isNaN(numValue)) {
    return '—';
  }

  let formattedValue: string;

  // 处理百分比格式
  if (config.formatAsPercentage) {
    formattedValue = `${(numValue * 100).toFixed(config.decimals || 2)}%`;
  }
  // 处理货币格式
  else if (config.formatAsCurrency) {
    formattedValue = `¥${numValue.toLocaleString('zh-CN', {
      minimumFractionDigits: config.decimals || 2,
      maximumFractionDigits: config.decimals || 2,
    })}`;
  }
  // 处理普通数字格式
  else {
    formattedValue = numValue.toLocaleString('zh-CN', {
      minimumFractionDigits: config.decimals || 0,
      maximumFractionDigits: config.decimals || 0,
    });
  }

  // 添加前缀和后缀
  if (config.prefix) {
    formattedValue = config.prefix + formattedValue;
  }
  if (config.suffix) {
    formattedValue = formattedValue + config.suffix;
  }

  return formattedValue;
}

/**
 * 获取绩效指标的颜色类名
 */
export function getMetricColorClass(
  value: number | undefined,
  config: MetricFormatConfig,
): string {
  if (value === undefined || value === null || !config.colorCode) {
    return 'text-gray-600';
  }

  const numValue = typeof value === 'string' ? parseFloat(value) : value;

  if (isNaN(numValue)) {
    return 'text-gray-600';
  }

  switch (config.colorCode) {
    case 'positive':
      return numValue >= 0 ? 'text-green-600' : 'text-red-600';
    case 'negative':
      return numValue <= 0 ? 'text-green-600' : 'text-red-600';
    case 'neutral':
      return 'text-blue-600';
    default:
      return 'text-gray-600';
  }
}

/**
 * 格式化日期字符串
 */
export function formatDate(dateString: string): string {
  if (!dateString) return '—';

  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  } catch (error) {
    return dateString;
  }
}

/**
 * 格式化日期时间字符串
 */
export function formatDateTime(dateString: string): string {
  if (!dateString) return '—';

  try {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch (error) {
    return dateString;
  }
}

/**
 * 计算两个日期之间的天数
 */
export function calculateDaysBetween(
  startDate: string,
  endDate: string,
): number {
  try {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = Math.abs(end.getTime() - start.getTime());
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  } catch (error) {
    return 0;
  }
}

/**
 * 生成绩效图表数据
 */
export function generatePerformanceChartData(
  labels: string[],
  data: number[],
  label: string = '绩效数据',
  color: string = '#10b981',
): PerformanceChartData {
  return {
    labels,
    datasets: [
      {
        label,
        data,
        borderColor: color,
        backgroundColor: `${color}20`, // 添加透明度
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
      },
    ],
  };
}

/**
 * 生成累计收益图表数据
 */
export function generateCumulativeReturnChartData(
  timestamps: string[],
  cumulativeReturns: number[],
): PerformanceChartData {
  const labels = timestamps.map((ts) => {
    const date = new Date(ts);
    return date.toLocaleDateString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
    });
  });

  return generatePerformanceChartData(
    labels,
    cumulativeReturns,
    '累计收益',
    '#10b981',
  );
}

/**
 * 生成回撤图表数据
 */
export function generateDrawdownChartData(
  timestamps: string[],
  drawdownData: number[],
): PerformanceChartData {
  const labels = timestamps.map((ts) => {
    const date = new Date(ts);
    return date.toLocaleDateString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
    });
  });

  return generatePerformanceChartData(labels, drawdownData, '回撤', '#ef4444');
}

/**
 * 采样数据以提高性能
 */
export function sampleDataForPerformance<
  T extends { timestamp: string; value?: number },
>(data: T[], maxPoints: number = 1000): T[] {
  if (!data || data.length <= maxPoints) {
    return data;
  }

  const step = Math.ceil(data.length / maxPoints);
  return data.filter((_, index) => index % step === 0);
}

/**
 * 计算滚动收益率
 */
export function calculateRollingReturns(
  returns: number[],
  windowSize: number,
): number[] {
  if (!returns || returns.length < windowSize) {
    return [];
  }

  const rollingReturns: number[] = [];

  for (let i = windowSize - 1; i < returns.length; i++) {
    let rollingReturn = 1;
    for (let j = i - windowSize + 1; j <= i; j++) {
      rollingReturn *= 1 + returns[j];
    }
    rollingReturns.push(rollingReturn - 1);
  }

  return rollingReturns;
}

/**
 * 计算最大回撤期间
 */
export function calculateMaxDrawdownPeriod(drawdownData: number[]): number {
  if (!drawdownData || drawdownData.length === 0) {
    return 0;
  }

  let maxDrawdownPeriod = 0;
  let currentDrawdownPeriod = 0;

  for (const drawdown of drawdownData) {
    if (drawdown > 0) {
      currentDrawdownPeriod++;
      maxDrawdownPeriod = Math.max(maxDrawdownPeriod, currentDrawdownPeriod);
    } else {
      currentDrawdownPeriod = 0;
    }
  }

  return maxDrawdownPeriod;
}

/**
 * 计算年化收益率
 */
export function calculateAnnualizedReturn(
  totalReturn: number,
  days: number,
): number {
  if (days <= 0) {
    return 0;
  }

  const years = days / 365.25;
  return Math.pow(1 + totalReturn, 1 / years) - 1;
}

/**
 * 计算夏普比率
 */
export function calculateSharpeRatio(
  returns: number[],
  riskFreeRate: number = 0.02,
): number {
  if (!returns || returns.length === 0) {
    return 0;
  }

  const meanReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
  const variance =
    returns.reduce((sum, r) => sum + Math.pow(r - meanReturn, 2), 0) /
    returns.length;
  const stdDev = Math.sqrt(variance);

  if (stdDev === 0) {
    return 0;
  }

  // 年化夏普比率
  const annualizedMeanReturn = meanReturn * 252; // 假设252个交易日
  const annualizedStdDev = stdDev * Math.sqrt(252);
  const annualizedRiskFreeRate = riskFreeRate;

  return (annualizedMeanReturn - annualizedRiskFreeRate) / annualizedStdDev;
}

/**
 * 计算索提诺比率
 */
export function calculateSortinoRatio(
  returns: number[],
  riskFreeRate: number = 0.02,
): number {
  if (!returns || returns.length === 0) {
    return 0;
  }

  const meanReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;

  // 计算下行偏差
  const negativeReturns = returns.filter((r) => r < meanReturn);
  if (negativeReturns.length === 0) {
    return 0;
  }

  const downsideVariance =
    negativeReturns.reduce((sum, r) => sum + Math.pow(r - meanReturn, 2), 0) /
    negativeReturns.length;
  const downsideDeviation = Math.sqrt(downsideVariance);

  if (downsideDeviation === 0) {
    return 0;
  }

  // 年化索提诺比率
  const annualizedMeanReturn = meanReturn * 252;
  const annualizedDownsideDeviation = downsideDeviation * Math.sqrt(252);
  const annualizedRiskFreeRate = riskFreeRate;

  return (
    (annualizedMeanReturn - annualizedRiskFreeRate) /
    annualizedDownsideDeviation
  );
}

/**
 * 验证绩效数据完整性
 */
export function validatePerformanceMetrics(metrics: PerformanceMetrics): {
  isValid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // 验证必需字段
  if (!metrics.strategyId) {
    errors.push('策略ID不能为空');
  }

  if (typeof metrics.totalReturn !== 'number') {
    errors.push('总收益率必须是数字');
  }

  if (typeof metrics.maxDrawdown !== 'number') {
    errors.push('最大回撤必须是数字');
  }

  if (typeof metrics.volatility !== 'number') {
    errors.push('波动率必须是数字');
  }

  // 验证数据范围
  if (metrics.totalReturn && Math.abs(metrics.totalReturn) > 10) {
    errors.push('总收益率异常（>1000%）');
  }

  if (metrics.maxDrawdown && metrics.maxDrawdown > 1) {
    errors.push('最大回撤异常（>100%）');
  }

  if (
    metrics.volatility &&
    (metrics.volatility < 0 || metrics.volatility > 5)
  ) {
    errors.push('波动率异常（<0% 或 >500%）');
  }

  if (metrics.winRate && (metrics.winRate < 0 || metrics.winRate > 1)) {
    errors.push('胜率异常（<0% 或 >100%）');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * 生成绩效摘要文本
 */
export function generatePerformanceSummary(
  metrics: PerformanceMetrics,
): string {
  const totalReturn = formatMetricValue(
    metrics.totalReturn,
    METRIC_DISPLAY_CONFIGS.totalReturn.format,
  );
  const maxDrawdown = formatMetricValue(
    metrics.maxDrawdown,
    METRIC_DISPLAY_CONFIGS.maxDrawdown.format,
  );
  const sharpeRatio = formatMetricValue(
    metrics.sharpeRatio,
    METRIC_DISPLAY_CONFIGS.sharpeRatio.format,
  );
  const winRate = formatMetricValue(
    metrics.winRate,
    METRIC_DISPLAY_CONFIGS.winRate.format,
  );

  return `策略总收益率 ${totalReturn}，最大回撤 ${maxDrawdown}，夏普比率 ${sharpeRatio}，胜率 ${winRate}`;
}

/**
 * 按重要性分组绩效指标
 */
export function groupMetricsByImportance(metrics: PerformanceMetrics): {
  high: MetricDisplayConfig[];
  medium: MetricDisplayConfig[];
  low: MetricDisplayConfig[];
} {
  const configs = Object.values(METRIC_DISPLAY_CONFIGS);

  return {
    high: configs.filter((config) => config.importance === 'high'),
    medium: configs.filter((config) => config.importance === 'medium'),
    low: configs.filter((config) => config.importance === 'low'),
  };
}

/**
 * 按类别分组绩效指标
 */
export function groupMetricsByCategory(metrics: PerformanceMetrics): {
  returns: MetricDisplayConfig[];
  risk: MetricDisplayConfig[];
  efficiency: MetricDisplayConfig[];
  trading: MetricDisplayConfig[];
} {
  const configs = Object.values(METRIC_DISPLAY_CONFIGS);

  return {
    returns: configs.filter((config) => config.category === 'returns'),
    risk: configs.filter((config) => config.category === 'risk'),
    efficiency: configs.filter((config) => config.category === 'efficiency'),
    trading: configs.filter((config) => config.category === 'trading'),
  };
}
/**
 * 导出绩效数据为CSV格式
 */
export function exportPerformanceToCSV(metrics: PerformanceMetrics): string {
  const headers = [
    '策略ID',
    '总收益率',
    '年化收益率',
    '最大回撤',
    '最大回撤期',
    '波动率',
    '夏普比率',
    'Sortino比率',
    '胜率',
    '盈亏比',
    '总交易次数',
    '盈利交易次数',
    '平均每笔交易',
    '期望值',
    'Calmar比率',
    '计算日期',
  ];

  const values = [
    metrics.strategyId,
    `${(metrics.totalReturn * 100).toFixed(2)}%`,
    `${(metrics.annualizedReturn * 100).toFixed(2)}%`,
    `${(metrics.maxDrawdown * 100).toFixed(2)}%`,
    metrics.maxDrawdownPeriod || '',
    `${(metrics.volatility * 100).toFixed(2)}%`,
    metrics.sharpeRatio.toFixed(3),
    metrics.sortinoRatio.toFixed(3),
    `${(metrics.winRate * 100).toFixed(2)}%`,
    metrics.profitLossRatio.toFixed(2),
    metrics.totalTrades,
    metrics.profitableTrades || '',
    metrics.averageTrade?.toFixed(2) || '',
    metrics.expectancy?.toFixed(2) || '',
    metrics.calmarRatio?.toFixed(3) || '',
    new Date(metrics.calculationDate).toLocaleDateString('zh-CN'),
  ];

  return `${headers.join(',')}\n${values.join(',')}\n`;
}

// ============================================================================
// UX 性能监控和优化功能
// ============================================================================

/**
 * 性能计时器类
 */
export class PerformanceTimer {
  private startTime: number = 0;
  private endTime: number = 0;
  private measurements: Array<{ label: string; duration: number }> = [];

  start(): void {
    this.startTime = performance.now();
  }

  end(): number {
    this.endTime = performance.now();
    return this.endTime - this.startTime;
  }

  measure(label: string): void {
    const duration = this.end();
    this.measurements.push({ label, duration });
    this.startTime = performance.now(); // 重置计时器
  }

  getMeasurements(): Array<{ label: string; duration: number }> {
    return [...this.measurements];
  }

  getTotalTime(): number {
    return this.measurements.reduce((total, m) => total + m.duration, 0);
  }

  clear(): void {
    this.measurements = [];
    this.startTime = 0;
    this.endTime = 0;
  }
}

/**
 * 组件性能监控Hook
 */
export function useComponentPerformanceMonitor(componentName: string) {
  const timerRef = useRef<PerformanceTimer>();
  const renderCountRef = useRef(0);
  const metricsRef = useRef<UXMetrics[]>([]);

  useEffect(() => {
    renderCountRef.current += 1;

    if (!timerRef.current) {
      timerRef.current = new PerformanceTimer();
    }

    timerRef.current.start();

    return () => {
      if (timerRef.current) {
        const renderTime = timerRef.current.end();

        const metric: UXMetrics = {
          id: `${componentName}_${renderCountRef.current}_${Date.now()}`,
          timestamp: new Date().toISOString(),
          componentName,
          actionType: 'render',
          componentRenderTime: renderTime,
          metadata: {
            renderCount: renderCountRef.current,
            memoryUsage: getMemoryUsage(),
          },
        };

        metricsRef.current.push(metric);

        // 记录到控制台（开发环境）
        if (process.env.NODE_ENV === 'development') {
          console.log(
            `[Performance] ${componentName} render #${renderCountRef.current}: ${renderTime.toFixed(2)}ms`,
          );
        }

        // 警告慢渲染
        if (renderTime > 100) {
          console.warn(
            `[Performance Warning] ${componentName} slow render: ${renderTime.toFixed(2)}ms`,
          );
        }
      }
    };
  });

  const getMetrics = useCallback(() => {
    return {
      renderCount: renderCountRef.current,
      metrics: [...metricsRef.current],
      averageRenderTime:
        metricsRef.current.length > 0
          ? metricsRef.current.reduce(
              (sum, m) => sum + (m.componentRenderTime || 0),
              0,
            ) / metricsRef.current.length
          : 0,
      totalRenderTime: metricsRef.current.reduce(
        (sum, m) => sum + (m.componentRenderTime || 0),
        0,
      ),
    };
  }, []);

  const clearMetrics = useCallback(() => {
    metricsRef.current = [];
    renderCountRef.current = 0;
    timerRef.current?.clear();
  }, []);

  return {
    getMetrics,
    clearMetrics,
    renderCount: renderCountRef.current,
  };
}

/**
 * API性能监控Hook
 */
export function useAPIPerformanceMonitor() {
  const requestsRef = useRef<Map<string, { startTime: number; url: string }>>(
    new Map(),
  );

  const startRequest = useCallback((requestId: string, url: string) => {
    requestsRef.current.set(requestId, {
      startTime: performance.now(),
      url,
    });
  }, []);

  const endRequest = useCallback(
    (requestId: string, success: boolean = true, error?: string) => {
      const request = requestsRef.current.get(requestId);
      if (request) {
        const duration = performance.now() - request.startTime;

        requestsRef.current.delete(requestId);

        // 记录API性能
        const metric: UXMetrics = {
          id: `api_${requestId}_${Date.now()}`,
          timestamp: new Date().toISOString(),
          componentName: `API_${request.url.split('/').pop()}`,
          actionType: 'api_call',
          apiResponseTime: duration,
          metadata: {
            url: request.url,
            success,
            error,
          },
        };

        if (process.env.NODE_ENV === 'development') {
          console.log(
            `[API Performance] ${request.url}: ${duration.toFixed(2)}ms (${success ? 'success' : 'error'})`,
          );
        }

        // 警告慢API调用
        if (duration > 1000) {
          console.warn(
            `[API Performance Warning] ${request.url} slow response: ${duration.toFixed(2)}ms`,
          );
        }

        return metric;
      }
      return null;
    },
    [],
  );

  const getActiveRequests = useCallback(() => {
    return Array.from(requestsRef.current.entries()).map(([id, request]) => ({
      id,
      ...request,
      duration: performance.now() - request.startTime,
    }));
  }, []);

  return {
    startRequest,
    endRequest,
    getActiveRequests,
  };
}

/**
 * 用户交互性能监控Hook
 */
export function useInteractionPerformanceMonitor() {
  const interactionsRef = useRef<
    Map<string, { startTime: number; type: string }>
  >(new Map());

  const startInteraction = useCallback(
    (interactionId: string, type: string) => {
      interactionsRef.current.set(interactionId, {
        startTime: performance.now(),
        type,
      });
    },
    [],
  );

  const endInteraction = useCallback((interactionId: string) => {
    const interaction = interactionsRef.current.get(interactionId);
    if (interaction) {
      const duration = performance.now() - interaction.startTime;

      interactionsRef.current.delete(interactionId);

      const metric: UXMetrics = {
        id: `interaction_${interactionId}_${Date.now()}`,
        timestamp: new Date().toISOString(),
        componentName: `Interaction_${interaction.type}`,
        actionType: 'user_interaction',
        userInteractionTime: duration,
        metadata: {
          interactionType: interaction.type,
        },
      };

      if (process.env.NODE_ENV === 'development') {
        console.log(
          `[Interaction Performance] ${interaction.type}: ${duration.toFixed(2)}ms`,
        );
      }

      // 警告慢交互
      if (duration > 500) {
        console.warn(
          `[Interaction Performance Warning] ${interaction.type} slow response: ${duration.toFixed(2)}ms`,
        );
      }

      return metric;
    }
    return null;
  }, []);

  return {
    startInteraction,
    endInteraction,
  };
}

/**
 * 内存使用监控
 */
export function getMemoryUsage(): number | null {
  if ('memory' in performance) {
    const memory = (performance as any).memory;
    return Math.round(memory.usedJSHeapSize / 1048576); // MB
  }
  return null;
}

/**
 * 页面性能分析
 */
export function analyzePagePerformance(): PagePerformanceMetrics | null {
  if (!('performance' in window)) return null;

  const navigation = performance.getEntriesByType(
    'navigation',
  )[0] as PerformanceNavigationTiming;
  const paintEntries = performance.getEntriesByType('paint');

  if (!navigation) return null;

  const domContentLoaded =
    navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart;
  const loadComplete = navigation.loadEventEnd - navigation.loadEventStart;

  const firstPaint =
    paintEntries.find((entry) => entry.name === 'first-paint')?.startTime || 0;
  const firstContentfulPaint =
    paintEntries.find((entry) => entry.name === 'first-contentful-paint')
      ?.startTime || 0;

  // 计算其他指标
  const timeToInteractive = calculateTimeToInteractive(navigation);
  const totalBlockingTime = calculateTotalBlockingTime();
  const cumulativeLayoutShift = calculateCumulativeLayoutShift();

  return {
    domContentLoaded,
    loadComplete,
    firstPaint,
    firstContentfulPaint,
    largestContentfulPaint: 0, // 需要PerformanceObserver
    firstInputDelay: 0, // 需要PerformanceObserver
    timeToInteractive,
    totalBlockingTime,
    cumulativeLayoutShift,
  };
}

// 计算可交互时间
function calculateTimeToInteractive(
  navigation: PerformanceNavigationTiming,
): number {
  // 简化计算，实际需要更复杂的逻辑
  return navigation.loadEventEnd - navigation.navigationStart;
}

// 计算总阻塞时间
function calculateTotalBlockingTime(): number {
  // 简化计算，实际需要PerformanceObserver
  return 0;
}

// 计算累积布局偏移
function calculateCumulativeLayoutShift(): number {
  // 简化计算，实际需要PerformanceObserver
  return 0;
}

/**
 * 性能阈值检查
 */
export function checkPerformanceThresholds(
  metrics: UXMetrics[],
  thresholds: PerformanceThreshold,
): {
  passed: boolean;
  violations: Array<{
    metric: string;
    actual: number;
    threshold: number;
    severity: 'warning' | 'error';
  }>;
} {
  const violations: Array<{
    metric: string;
    actual: number;
    threshold: number;
    severity: 'warning' | 'error';
  }> = [];

  metrics.forEach((metric) => {
    if (
      metric.componentRenderTime &&
      metric.componentRenderTime > thresholds.componentRenderTime
    ) {
      violations.push({
        metric: `${metric.componentName} Render Time`,
        actual: metric.componentRenderTime,
        threshold: thresholds.componentRenderTime,
        severity:
          metric.componentRenderTime > thresholds.componentRenderTime * 2
            ? 'error'
            : 'warning',
      });
    }

    if (
      metric.apiResponseTime &&
      metric.apiResponseTime > thresholds.apiResponseTime
    ) {
      violations.push({
        metric: `${metric.componentName} API Response Time`,
        actual: metric.apiResponseTime,
        threshold: thresholds.apiResponseTime,
        severity:
          metric.apiResponseTime > thresholds.apiResponseTime * 2
            ? 'error'
            : 'warning',
      });
    }

    if (
      metric.userInteractionTime &&
      metric.userInteractionTime > thresholds.userInteractionTime
    ) {
      violations.push({
        metric: `${metric.componentName} User Interaction Time`,
        actual: metric.userInteractionTime,
        threshold: thresholds.userInteractionTime,
        severity:
          metric.userInteractionTime > thresholds.userInteractionTime * 2
            ? 'error'
            : 'warning',
      });
    }

    if (metric.memoryUsage && metric.memoryUsage > thresholds.memoryUsage) {
      violations.push({
        metric: `${metric.componentName} Memory Usage`,
        actual: metric.memoryUsage,
        threshold: thresholds.memoryUsage,
        severity:
          metric.memoryUsage > thresholds.memoryUsage * 1.5
            ? 'error'
            : 'warning',
      });
    }
  });

  return {
    passed: violations.length === 0,
    violations,
  };
}

/**
 * 性能优化建议生成器
 */
export function generateOptimizationRecommendations(
  metrics: UXMetrics[],
  thresholds: PerformanceThreshold,
): Array<{
  category: string;
  recommendation: string;
  priority: 'high' | 'medium' | 'low';
}> {
  const recommendations: Array<{
    category: string;
    recommendation: string;
    priority: 'high' | 'medium' | 'low';
  }> = [];

  const slowRenders = metrics.filter(
    (m) =>
      m.componentRenderTime &&
      m.componentRenderTime > thresholds.componentRenderTime,
  );
  if (slowRenders.length > 0) {
    recommendations.push({
      category: 'Rendering',
      recommendation: `发现 ${slowRenders.length} 个组件渲染缓慢。考虑使用React.memo、useMemo、useCallback进行优化。`,
      priority: 'high',
    });
  }

  const slowAPIs = metrics.filter(
    (m) => m.apiResponseTime && m.apiResponseTime > thresholds.apiResponseTime,
  );
  if (slowAPIs.length > 0) {
    recommendations.push({
      category: 'API',
      recommendation: `发现 ${slowAPIs.length} 个API响应缓慢。考虑实现缓存、请求优化或后端性能改进。`,
      priority: 'high',
    });
  }

  const highMemoryUsage = metrics.filter(
    (m) => m.memoryUsage && m.memoryUsage > thresholds.memoryUsage,
  );
  if (highMemoryUsage.length > 0) {
    recommendations.push({
      category: 'Memory',
      recommendation:
        '检测到高内存使用。考虑优化数据结构、清理未使用的资源和避免内存泄漏。',
      priority: 'medium',
    });
  }

  // 检查重复渲染
  const componentRenders = metrics.reduce(
    (acc, m) => {
      acc[m.componentName] = (acc[m.componentName] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  Object.entries(componentRenders).forEach(([componentName, count]) => {
    if (count > 10) {
      // 如果某个组件渲染超过10次
      recommendations.push({
        category: 'Rendering',
        recommendation: `组件 ${componentName} 渲染次数过多 (${count} 次)。检查props变化和状态更新逻辑。`,
        priority: 'medium',
      });
    }
  });

  return recommendations;
}

/**
 * 性能报告生成器
 */
export function generateUXPerformanceReport(
  metrics: UXMetrics[],
  thresholds: PerformanceThreshold,
): {
  summary: {
    totalMetrics: number;
    averageRenderTime: number;
    averageApiResponseTime: number;
    averageUserInteractionTime: number;
    averageMemoryUsage: number;
    performanceScore: number; // 0-100
  };
  violations: Array<{
    metric: string;
    actual: number;
    threshold: number;
    severity: 'warning' | 'error';
  }>;
  recommendations: Array<{
    category: string;
    recommendation: string;
    priority: 'high' | 'medium' | 'low';
  }>;
  topSlowComponents: Array<{
    componentName: string;
    averageTime: number;
    count: number;
  }>;
} {
  const renderMetrics = metrics.filter(
    (m) => m.componentRenderTime !== undefined,
  );
  const apiMetrics = metrics.filter((m) => m.apiResponseTime !== undefined);
  const interactionMetrics = metrics.filter(
    (m) => m.userInteractionTime !== undefined,
  );
  const memoryMetrics = metrics.filter((m) => m.memoryUsage !== undefined);

  const averageRenderTime =
    renderMetrics.length > 0
      ? renderMetrics.reduce(
          (sum, m) => sum + (m.componentRenderTime || 0),
          0,
        ) / renderMetrics.length
      : 0;

  const averageApiResponseTime =
    apiMetrics.length > 0
      ? apiMetrics.reduce((sum, m) => sum + (m.apiResponseTime || 0), 0) /
        apiMetrics.length
      : 0;

  const averageUserInteractionTime =
    interactionMetrics.length > 0
      ? interactionMetrics.reduce(
          (sum, m) => sum + (m.userInteractionTime || 0),
          0,
        ) / interactionMetrics.length
      : 0;

  const averageMemoryUsage =
    memoryMetrics.length > 0
      ? memoryMetrics.reduce((sum, m) => sum + (m.memoryUsage || 0), 0) /
        memoryMetrics.length
      : 0;

  // 计算性能分数
  const renderScore = Math.max(
    0,
    100 - (averageRenderTime / thresholds.componentRenderTime) * 100,
  );
  const apiScore = Math.max(
    0,
    100 - (averageApiResponseTime / thresholds.apiResponseTime) * 100,
  );
  const interactionScore = Math.max(
    0,
    100 - (averageUserInteractionTime / thresholds.userInteractionTime) * 100,
  );
  const memoryScore = Math.max(
    0,
    100 - (averageMemoryUsage / thresholds.memoryUsage) * 100,
  );

  const performanceScore = Math.round(
    (renderScore + apiScore + interactionScore + memoryScore) / 4,
  );

  // 获取最慢的组件
  const componentStats = metrics.reduce(
    (acc, m) => {
      if (!acc[m.componentName]) {
        acc[m.componentName] = { totalTime: 0, count: 0 };
      }
      acc[m.componentName].totalTime +=
        m.componentRenderTime ||
        m.apiResponseTime ||
        m.userInteractionTime ||
        0;
      acc[m.componentName].count += 1;
      return acc;
    },
    {} as Record<string, { totalTime: number; count: number }>,
  );

  const topSlowComponents = Object.entries(componentStats)
    .map(([componentName, stats]) => ({
      componentName,
      averageTime: stats.totalTime / stats.count,
      count: stats.count,
    }))
    .sort((a, b) => b.averageTime - a.averageTime)
    .slice(0, 10);

  const { violations } = checkPerformanceThresholds(metrics, thresholds);
  const recommendations = generateOptimizationRecommendations(
    metrics,
    thresholds,
  );

  return {
    summary: {
      totalMetrics: metrics.length,
      averageRenderTime,
      averageApiResponseTime,
      averageUserInteractionTime,
      averageMemoryUsage,
      performanceScore,
    },
    violations,
    recommendations,
    topSlowComponents,
  };
}
