import { UseQueryOptions, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useMemo, useRef } from 'react';
import { marketDataAPI, strategyAPI } from '@/lib/api';
import {
  PerformanceMetrics,
  PerformanceAnalysisRequest,
  PerformanceAnalysisResponse,
  PerformanceReport,
  PerformanceReportConfig,
  CumulativeReturnData,
  DrawdownData,
  RollingReturnData,
  PerformanceComparison,
  PerformanceAPIResponse,
  PerformanceCacheConfig,
  PerformanceError,
  ReturnDataPoint
} from '@/types/performance.types';

// 扩展API响应类型以处理不同的响应格式
interface APIResponse<T = any> {
  success?: boolean;
  data?: T;
  message?: string;
  task_id?: string;
}

// 查询键常量
export const PERFORMANCE_QUERY_KEYS = {
  metrics: (strategyId: string, startDate?: string, endDate?: string, benchmarkId?: string) =>
    ['performanceMetrics', strategyId, startDate, endDate, benchmarkId] as const,
  cumulativeReturns: (strategyId: string, startDate?: string, endDate?: string) =>
    ['cumulativeReturns', strategyId, startDate, endDate] as const,
  drawdown: (strategyId: string, startDate?: string, endDate?: string) =>
    ['drawdown', strategyId, startDate, endDate] as const,
  rollingReturns: (strategyId: string, window: number, startDate?: string, endDate?: string) =>
    ['rollingReturns', strategyId, window, startDate, endDate] as const,
  comparison: (strategyIds: string[], benchmarkId?: string) =>
    ['performanceComparison', strategyIds, benchmarkId] as const,
  report: (config: PerformanceReportConfig) =>
    ['performanceReport', config] as const,
} as const;

// 数据缓存配置
const PERFORMANCE_CACHE_CONFIG: PerformanceCacheConfig = {
  metricsTtl: 5 * 60, // 5 minutes - 绩效指标缓存时间
  chartsTtl: 10 * 60, // 10 minutes - 图表数据缓存时间
  reportsTtl: 30 * 60, // 30 minutes - 报告缓存时间
};

// 防抖配置
const DEBOUNCE_CONFIG = {
  delay: 300, // 300ms 防抖延迟
  maxWait: 2000, // 最大等待时间2秒
};

/**
 * 绩效数据变更检测类
 */
export class PerformanceChangeDetector {
  private lastRequest: PerformanceAnalysisRequest | null = null;
  private changeCallbacks: Map<string, (request: PerformanceAnalysisRequest) => void> = new Map();
  private debounceTimers: Map<string, NodeJS.Timeout> = new Map();

  constructor(
    private onParametersChange?: (request: PerformanceAnalysisRequest) => void,
    private debounceDelay: number = DEBOUNCE_CONFIG.delay,
  ) {
    // Constructor with optional dependencies
  }

  /**
   * 检测请求参数变化并触发回调
   */
  detectChange(newRequest: PerformanceAnalysisRequest, immediate: boolean = false): boolean {
    if (this.lastRequest && this.areParametersEqual(this.lastRequest, newRequest)) {
      return false; // 参数没有变化
    }

    this.lastRequest = { ...newRequest };

    if (immediate) {
      this.executeChange(newRequest);
    } else {
      this.debouncedExecuteChange(newRequest);
    }

    return true;
  }

  /**
   * 比较两个请求参数是否相等
   */
  private areParametersEqual(req1: PerformanceAnalysisRequest, req2: PerformanceAnalysisRequest): boolean {
    return (
      req1.strategyId === req2.strategyId &&
      req1.returnType === req2.returnType &&
      req1.initialCapital === req2.initialCapital &&
      req1.positionSize === req2.positionSize &&
      req1.riskFreeRate === req2.riskFreeRate &&
      req1.includeCosts === req2.includeCosts &&
      req1.startDate === req2.startDate &&
      req1.endDate === req2.endDate &&
      req1.benchmarkId === req2.benchmarkId
    );
  }

  /**
   * 防抖执行参数变化
   */
  private debouncedExecuteChange(request: PerformanceAnalysisRequest): void {
    const key = request.strategyId;

    // 清除之前的定时器
    const existingTimer = this.debounceTimers.get(key);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }

    // 设置新的定时器
    const timer = setTimeout(() => {
      this.executeChange(request);
      this.debounceTimers.delete(key);
    }, this.debounceDelay);

    this.debounceTimers.set(key, timer);
  }

  /**
   * 立即执行参数变化
   */
  private executeChange(request: PerformanceAnalysisRequest): void {
    this.onParametersChange?.(request);

    // 通知所有注册的回调
    this.changeCallbacks.forEach(callback => callback(request));
  }

  /**
   * 注册参数变化回调
   */
  onChange(id: string, callback: (request: PerformanceAnalysisRequest) => void): void {
    this.changeCallbacks.set(id, callback);
  }

  /**
   * 移除参数变化回调
   */
  offChange(id: string): void {
    this.changeCallbacks.delete(id);
  }

  /**
   * 强制立即执行（跳过防抖）
   */
  flush(): void {
    if (this.lastRequest) {
      this.executeChange(this.lastRequest);
    }
  }

  /**
   * 清理资源
   */
  destroy(): void {
    this.debounceTimers.forEach(timer => clearTimeout(timer));
    this.debounceTimers.clear();
    this.changeCallbacks.clear();
    this.lastRequest = null;
  }
}

/**
 * 绩效指标Hook
 */
export function usePerformanceMetrics(
  request: PerformanceAnalysisRequest,
  options?: Partial<UseQueryOptions<PerformanceMetrics, Error>>,
) {
  const queryClient = useQueryClient();
  const changeDetectorRef = useRef<PerformanceChangeDetector>();

  // 创建或获取参数变更检测器
  if (!changeDetectorRef.current) {
    changeDetectorRef.current = new PerformanceChangeDetector(
      (params) => {
        // 参数变化时重新获取绩效指标
        queryClient.invalidateQueries({
          queryKey: ['performanceMetrics', params.strategyId],
        });
      },
      DEBOUNCE_CONFIG.delay,
    );
  }

  const queryKey = PERFORMANCE_QUERY_KEYS.metrics(
    request.strategyId,
    request.startDate,
    request.endDate,
    request.benchmarkId
  );

  const query = useQuery({
    queryKey,
    queryFn: async (): Promise<PerformanceMetrics> => {
      try {
        const response = await marketDataAPI.getPerformanceMetrics(request.strategyId, {
          return_type: request.returnType,
          benchmark_id: request.benchmarkId,
          start_date: request.startDate,
          end_date: request.endDate,
        });

        if (!response.success) {
          throw new Error(response.message || '获取绩效指标失败');
        }

        return response.data;
      } catch (error) {
        console.error('绩效指标获取失败:', error);
        throw error;
      }
    },
    staleTime: PERFORMANCE_CACHE_CONFIG.metricsTtl * 1000,
    gcTime: PERFORMANCE_CACHE_CONFIG.metricsTtl * 2 * 1000,
    enabled: !!request.strategyId,
    ...options,
  });

  // 参数变化检测
  useMemo(() => {
    if (changeDetectorRef.current) {
      changeDetectorRef.current.detectChange(request);
    }
  }, [request]);

  // 组件卸载时清理
  React.useEffect(() => {
    return () => {
      changeDetectorRef.current?.destroy();
    };
  }, []);

  return {
    ...query,
    forceRefresh: () => {
      changeDetectorRef.current?.flush();
    },
  };
}

/**
 * 累计收益数据Hook
 */
export function useCumulativeReturns(
  request: PerformanceAnalysisRequest,
  options?: Partial<UseQueryOptions<CumulativeReturnData, Error>>,
) {
  const queryKey = PERFORMANCE_QUERY_KEYS.cumulativeReturns(
    request.strategyId,
    request.startDate,
    request.endDate
  );

  return useQuery({
    queryKey,
    queryFn: async (): Promise<CumulativeReturnData> => {
      try {
        const response = await marketDataAPI.calculateReturns({
          strategy_id: request.strategyId,
          return_type: request.returnType,
          initial_capital: request.initialCapital,
          position_size: request.positionSize,
          risk_free_rate: request.riskFreeRate,
          include_costs: request.includeCosts,
          start_date: request.startDate,
          end_date: request.endDate,
        });

        if (!response.success) {
          throw new Error(response.message || '获取累计收益数据失败');
        }

        // 转换API响应为图表数据格式
        const data = response.data;
        return {
          labels: data.timestamps || [],
          datasets: [{
            label: '累计收益',
            data: data.cumulative_returns || [],
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            fill: true,
            tension: 0.4,
          }],
        };
      } catch (error) {
        console.error('累计收益数据获取失败:', error);
        throw error;
      }
    },
    staleTime: PERFORMANCE_CACHE_CONFIG.chartsTtl * 1000,
    gcTime: PERFORMANCE_CACHE_CONFIG.chartsTtl * 2 * 1000,
    enabled: !!request.strategyId,
    ...options,
  });
}

/**
 * 回撤数据Hook
 */
export function useDrawdownData(
  request: PerformanceAnalysisRequest,
  options?: Partial<UseQueryOptions<DrawdownData, Error>>,
) {
  const queryKey = PERFORMANCE_QUERY_KEYS.drawdown(
    request.strategyId,
    request.startDate,
    request.endDate
  );

  return useQuery({
    queryKey,
    queryFn: async (): Promise<DrawdownData> => {
      try {
        // 首先获取累计收益数据
        const returnsResponse = await marketDataAPI.calculateReturns({
          strategy_id: request.strategyId,
          return_type: request.returnType,
          initial_capital: request.initialCapital,
          position_size: request.positionSize,
          risk_free_rate: request.riskFreeRate,
          include_costs: request.includeCosts,
          start_date: request.startDate,
          end_date: request.endDate,
        });

        if (!returnsResponse.success) {
          throw new Error(returnsResponse.message || '获取收益数据失败');
        }

        // 计算回撤序列
        const cumulativeReturns = returnsResponse.data.cumulative_returns || [];
        const drawdownData = calculateDrawdownSeries(cumulativeReturns);

        return {
          labels: returnsResponse.data.timestamps || [],
          datasets: [{
            label: '回撤',
            data: drawdownData,
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            fill: true,
          }],
        };
      } catch (error) {
        console.error('回撤数据获取失败:', error);
        throw error;
      }
    },
    staleTime: PERFORMANCE_CACHE_CONFIG.chartsTtl * 1000,
    gcTime: PERFORMANCE_CACHE_CONFIG.chartsTtl * 2 * 1000,
    enabled: !!request.strategyId,
    ...options,
  });
}

/**
 * 绩效对比Hook
 */
export function usePerformanceComparison(
  strategyIds: string[],
  benchmarkId?: string,
  startDate?: string,
  endDate?: string,
  options?: Partial<UseQueryOptions<PerformanceComparison, Error>>,
) {
  const queryKey = PERFORMANCE_QUERY_KEYS.comparison(strategyIds, benchmarkId);

  return useQuery({
    queryKey,
    queryFn: async (): Promise<PerformanceComparison> => {
      try {
        const comparisonPromises = strategyIds.map(async (strategyId) => {
          const response = await marketDataAPI.getPerformanceMetrics(strategyId, {
            benchmark_id: benchmarkId,
            start_date: startDate,
            end_date: endDate,
          });

          if (!response.success) {
            throw new Error(`获取策略 ${strategyId} 绩效指标失败`);
          }

          return {
            id: strategyId,
            name: `策略 ${strategyId}`,
            metrics: response.data,
          };
        });

        const strategies = await Promise.all(comparisonPromises);

        return {
          strategies,
          comparisonDate: new Date().toISOString(),
        };
      } catch (error) {
        console.error('绩效对比数据获取失败:', error);
        throw error;
      }
    },
    staleTime: PERFORMANCE_CACHE_CONFIG.metricsTtl * 1000,
    gcTime: PERFORMANCE_CACHE_CONFIG.metricsTtl * 2 * 1000,
    enabled: strategyIds.length > 0,
    ...options,
  });
}

/**
 * 绩效报告Hook
 */
export function usePerformanceReport(
  config: PerformanceReportConfig,
  options?: Partial<UseQueryOptions<PerformanceReport, Error>>,
) {
  const queryKey = PERFORMANCE_QUERY_KEYS.report(config);

  return useQuery({
    queryKey,
    queryFn: async (): Promise<PerformanceReport> => {
      try {
        const response = await marketDataAPI.generateReport(config);

        if (!response.success) {
          throw new Error(response.message || '生成绩效报告失败');
        }

        return response.data;
      } catch (error) {
        console.error('绩效报告生成失败:', error);
        throw error;
      }
    },
    staleTime: PERFORMANCE_CACHE_CONFIG.reportsTtl * 1000,
    gcTime: PERFORMANCE_CACHE_CONFIG.reportsTtl * 2 * 1000,
    enabled: !!config.strategyId,
    ...options,
  });
}

/**
 * 计算回撤序列
 */
function calculateDrawdownSeries(cumulativeReturns: number[]): number[] {
  if (!cumulativeReturns || cumulativeReturns.length === 0) {
    return [];
  }

  const drawdowns: number[] = [];
  let peak = cumulativeReturns[0];

  for (let i = 0; i < cumulativeReturns.length; i++) {
    const currentValue = cumulativeReturns[i];

    // 更新峰值
    if (currentValue > peak) {
      peak = currentValue;
    }

    // 计算回撤
    const drawdown = peak === 0 ? 0 : (peak - currentValue) / peak;
    drawdowns.push(drawdown);
  }

  return drawdowns;
}

/**
 * 绩效服务预加载器
 */
export class PerformanceServicePreloader {
  constructor(private queryClient: any) {
    // Constructor for dependency injection
  }

  /**
   * 预加载绩效指标
   */
  async preloadPerformanceMetrics(request: PerformanceAnalysisRequest) {
    return this.queryClient.prefetchQuery({
      queryKey: PERFORMANCE_QUERY_KEYS.metrics(
        request.strategyId,
        request.startDate,
        request.endDate,
        request.benchmarkId
      ),
      queryFn: async () => {
        const response = await marketDataAPI.getPerformanceMetrics(request.strategyId, {
          return_type: request.returnType,
          benchmark_id: request.benchmarkId,
          start_date: request.startDate,
          end_date: request.endDate,
        });

        if (!response.success) {
          throw new Error(response.message || '获取绩效指标失败');
        }

        return response.data;
      },
      staleTime: PERFORMANCE_CACHE_CONFIG.metricsTtl * 1000,
    });
  }

  /**
   * 预加载累计收益数据
   */
  async preloadCumulativeReturns(request: PerformanceAnalysisRequest) {
    return this.queryClient.prefetchQuery({
      queryKey: PERFORMANCE_QUERY_KEYS.cumulativeReturns(
        request.strategyId,
        request.startDate,
        request.endDate
      ),
      queryFn: async () => {
        const response = await marketDataAPI.calculateReturns({
          strategy_id: request.strategyId,
          return_type: request.returnType,
          initial_capital: request.initialCapital,
          position_size: request.positionSize,
          risk_free_rate: request.riskFreeRate,
          include_costs: request.includeCosts,
          start_date: request.startDate,
          end_date: request.endDate,
        });

        if (!response.success) {
          throw new Error(response.message || '获取累计收益数据失败');
        }

        const data = response.data;
        return {
          labels: data.timestamps || [],
          datasets: [{
            label: '累计收益',
            data: data.cumulative_returns || [],
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            fill: true,
            tension: 0.4,
          }],
        };
      },
      staleTime: PERFORMANCE_CACHE_CONFIG.chartsTtl * 1000,
    });
  }

  /**
   * 清除缓存
   */
  clearPerformanceCache(strategyId?: string) {
    if (strategyId) {
      this.queryClient.invalidateQueries({
        queryKey: ['performanceMetrics', strategyId],
      });
      this.queryClient.invalidateQueries({
        queryKey: ['cumulativeReturns', strategyId],
      });
      this.queryClient.invalidateQueries({
        queryKey: ['drawdown', strategyId],
      });
    } else {
      this.queryClient.invalidateQueries({
        queryKey: ['performanceMetrics'],
      });
      this.queryClient.invalidateQueries({
        queryKey: ['cumulativeReturns'],
      });
      this.queryClient.invalidateQueries({
        queryKey: ['drawdown'],
      });
    }
  }
}

// 导出performanceService对象（包含所有方法）
export const performanceService = {
  usePerformanceMetrics,
  useCumulativeReturns,
  useDrawdownData,
  usePerformanceComparison,
  usePerformanceReport,
  PerformanceChangeDetector,
  PerformanceServicePreloader,
  // 导出查询配置
  QUERY_KEYS: PERFORMANCE_QUERY_KEYS,
  CACHE_CONFIG: PERFORMANCE_CACHE_CONFIG,
  DEBOUNCE_CONFIG,
};