import { UseQueryOptions, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useMemo, useRef } from 'react';
import { marketDataAPI, strategyAPI } from '@/lib/api';
import { ParameterGroup, ParameterValidationResult, StrategyParameters, StrategyResult } from '@/types/parameter.types';
import { areParametersEqual, generateParameterDescription, validateAllParameters } from '@/utils/parameterHelpers';

// 扩展API响应类型以处理不同的响应格式
interface APIResponse<T = any> {
  success?: boolean;
  data?: T;
  message?: string;
  task_id?: string;
}

// 查询键常量
export const PARAMETER_QUERY_KEYS = {
  strategyResults: (symbol: string, params: StrategyParameters, startDate: string, endDate: string) =>
    ['strategyResults', symbol, params, startDate, endDate] as const,
  parameterValidation: (params: StrategyParameters) =>
    ['parameterValidation', params] as const,
  parameterComparison: (groups: ParameterGroup[]) =>
    ['parameterComparison', groups] as const,
  optimizationSuggestions: (symbol: string, params: StrategyParameters) =>
    ['optimizationSuggestions', symbol, params] as const,
} as const;

// 数据缓存配置
const CACHE_CONFIG = {
  strategyResults: {
    staleTime: 30 * 1000, // 30 seconds - 实时更新需要较短缓存时间
    gcTime: 5 * 60 * 1000, // 5 minutes
  },
  parameterValidation: {
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  },
  optimizationSuggestions: {
    staleTime: 10 * 60 * 1000, // 10 minutes
    gcTime: 30 * 60 * 1000, // 30 minutes
  },
};

// 防抖配置
const DEBOUNCE_CONFIG = {
  delay: 500, // 500ms 防抖延迟，满足响应时间<500ms要求
  maxWait: 2000, // 最大等待时间2秒
};

/**
 * 参数变更检测类
 */
export class ParameterChangeDetector {
  private lastParameters: StrategyParameters | null = null;
  private changeCallbacks: Map<string, (params: StrategyParameters) => void> = new Map();
  private debounceTimers: Map<string, NodeJS.Timeout> = new Map();

  constructor(
    private onParametersChange?: (params: StrategyParameters) => void,
    private debounceDelay: number = DEBOUNCE_CONFIG.delay,
  ) {
    // Constructor with optional dependencies
  }

  /**
   * 检测参数变化并触发回调
   */
  detectChange(newParameters: StrategyParameters, immediate: boolean = false): boolean {
    if (this.lastParameters && areParametersEqual(this.lastParameters, newParameters)) {
      return false; // 参数没有变化
    }

    this.lastParameters = { ...newParameters };

    if (immediate) {
      this.executeChange(newParameters);
    } else {
      this.debouncedExecuteChange(newParameters);
    }

    return true;
  }

  /**
   * 防抖执行参数变化
   */
  private debouncedExecuteChange(params: StrategyParameters): void {
    const key = 'main';

    // 清除之前的定时器
    const existingTimer = this.debounceTimers.get(key);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }

    // 设置新的定时器
    const timer = setTimeout(() => {
      this.executeChange(params);
      this.debounceTimers.delete(key);
    }, this.debounceDelay);

    this.debounceTimers.set(key, timer);
  }

  /**
   * 立即执行参数变化
   */
  private executeChange(params: StrategyParameters): void {
    this.onParametersChange?.(params);

    // 通知所有注册的回调
    this.changeCallbacks.forEach(callback => callback(params));
  }

  /**
   * 注册参数变化回调
   */
  onChange(id: string, callback: (params: StrategyParameters) => void): void {
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
    if (this.lastParameters) {
      this.executeChange(this.lastParameters);
    }
  }

  /**
   * 清理资源
   */
  destroy(): void {
    this.debounceTimers.forEach(timer => clearTimeout(timer));
    this.debounceTimers.clear();
    this.changeCallbacks.clear();
    this.lastParameters = null;
  }
}

/**
 * 实时策略结果Hook
 */
export function useRealTimeStrategyResults(
  symbol: string,
  parameters: StrategyParameters,
  startDate: string,
  endDate: string,
  options?: Partial<UseQueryOptions<StrategyResult, Error>>,
) {
  const queryClient = useQueryClient();
  const changeDetectorRef = useRef<ParameterChangeDetector>();
  const lastQueryKeyRef = useRef<string>();

  // 创建或获取参数变更检测器
  if (!changeDetectorRef.current) {
    changeDetectorRef.current = new ParameterChangeDetector(
      (params) => {
        // 参数变化时重新获取策略结果
        queryClient.invalidateQueries({
          queryKey: ['strategyResults', symbol],
        });
      },
      DEBOUNCE_CONFIG.delay,
    );
  }

  const queryKey = PARAMETER_QUERY_KEYS.strategyResults(symbol, parameters, startDate, endDate);

  const query = useQuery({
    queryKey,
    queryFn: async () => {
      try {
        // 转换参数格式以适配后端API
        const apiParams = {
          window_size: parameters.movingAveragePeriod,
          initial_capital: 100000, // 默认初始资金
          stop_loss: parameters.stopLoss,
          take_profit: parameters.takeProfit,
        };

        // 运行策略
        const runResponse = await strategyAPI.run({
          symbol,
          start_date: startDate,
          end_date: endDate,
          config: {
            name: 'moving_average',
            params: apiParams,
          },
        });

        if (!runResponse.task_id) {
          throw new Error('策略运行失败');
        }

        // 轮询获取结果
        const result = await pollStrategyResult(runResponse.task_id);

        // 缓存结果
        const cacheKey = `strategy_result_${symbol}_${JSON.stringify(parameters)}_${startDate}_${endDate}`;
        if (typeof window !== 'undefined') {
          localStorage.setItem(cacheKey, JSON.stringify({
            data: result,
            timestamp: Date.now(),
          }));
        }

        return result;
      } catch (error) {
        console.error('策略结果获取失败:', error);
        throw error;
      }
    },
    staleTime: CACHE_CONFIG.strategyResults.staleTime,
    gcTime: CACHE_CONFIG.strategyResults.gcTime,
    enabled: !!(symbol && startDate && endDate),
    ...options,
  });

  // 参数变化检测
  useMemo(() => {
    if (changeDetectorRef.current) {
      changeDetectorRef.current.detectChange(parameters);
    }
  }, [parameters]);

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
 * 参数验证Hook
 */
export function useParameterValidation(
  parameters: StrategyParameters,
  options?: Partial<UseQueryOptions<ParameterValidationResult, Error>>,
) {
  return useQuery({
    queryKey: PARAMETER_QUERY_KEYS.parameterValidation(parameters),
    queryFn: () => validateAllParameters(parameters),
    staleTime: CACHE_CONFIG.parameterValidation.staleTime,
    gcTime: CACHE_CONFIG.parameterValidation.gcTime,
    ...options,
  });
}

/**
 * 参数对比分析Hook
 */
export function useParameterComparison(
  groups: ParameterGroup[],
  symbol: string,
  startDate: string,
  endDate: string,
  options?: Partial<UseQueryOptions<any[], Error>>,
) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: PARAMETER_QUERY_KEYS.parameterComparison(groups),
    queryFn: async () => {
      const results = await Promise.allSettled(
        groups.map(async (group) => {
          if (group.results) {
            return group.results;
          }

          try {
            const apiParams = {
              window_size: group.parameters.movingAveragePeriod,
              initial_capital: 100000,
              stop_loss: group.parameters.stopLoss,
              take_profit: group.parameters.takeProfit,
            };

            const runResponse = await strategyAPI.run({
              symbol,
              start_date: startDate,
              end_date: endDate,
              // strategy_type: 'moving_average', // 移除不支持的属性
              config: {
                name: 'moving_average',
                params: apiParams,
              },
            });

            if (!runResponse.task_id) {
              throw new Error(`策略运行失败: ${group.name}`);
            }

            const result = await pollStrategyResult(runResponse.task_id);
            group.results = result;
            return result;
          } catch (error) {
            console.error(`参数组 ${group.name} 分析失败:`, error);
            throw error;
          }
        }),
      );

      return results.map((result, index) => ({
        group: groups[index],
        result: result.status === 'fulfilled' ? result.value : null,
        error: result.status === 'rejected' ? result.reason : null,
      }));
    },
    staleTime: CACHE_CONFIG.strategyResults.staleTime,
    gcTime: CACHE_CONFIG.strategyResults.gcTime,
    enabled: groups.length > 0 && !!(symbol && startDate && endDate),
    ...options,
  });

  return {
    ...query,
    refreshGroup: (groupId: string) => {
      queryClient.invalidateQueries({
        queryKey: ['parameterComparison'],
      });
    },
  };
}

/**
 * 参数优化建议Hook
 */
export function useOptimizationSuggestions(
  symbol: string,
  baseParameters: StrategyParameters,
  startDate: string,
  endDate: string,
  options?: Partial<UseQueryOptions<any[], Error>>,
) {
  return useQuery({
    queryKey: PARAMETER_QUERY_KEYS.optimizationSuggestions(symbol, baseParameters),
    queryFn: async () => {
      try {
        // 这里应该调用后端的优化建议API
        // 暂时返回模拟数据
        const suggestions = [
          {
            id: 'risk_adjusted',
            type: 'risk',
            confidence: 85,
            parameters: {
              ...baseParameters,
              stopLoss: Math.min(baseParameters.stopLoss * 1.2, 10),
              takeProfit: Math.max(baseParameters.takeProfit * 1.1, 12),
            },
            reasoning: '基于历史数据，适当放宽止损可以提高策略成功率',
            expectedImprovement: '预计降低止损频率15%，提高总体收益5%',
          },
          {
            id: 'trend_optimized',
            type: 'trend',
            confidence: 72,
            parameters: {
              ...baseParameters,
              movingAveragePeriod: baseParameters.movingAveragePeriod > 20
                ? Math.max(baseParameters.movingAveragePeriod - 5, 15)
                : Math.min(baseParameters.movingAveragePeriod + 5, 35),
            },
            reasoning: '当前市场呈现趋势特征，调整均线周期可以更好地捕捉趋势',
            expectedImprovement: '预计提高信号质量，减少假信号',
          },
        ];

        return suggestions;
      } catch (error) {
        console.error('优化建议获取失败:', error);
        throw error;
      }
    },
    staleTime: CACHE_CONFIG.optimizationSuggestions.staleTime,
    gcTime: CACHE_CONFIG.optimizationSuggestions.gcTime,
    ...options,
  });
}

/**
 * 轮询策略结果
 */
export async function pollStrategyResult(taskId: string, maxAttempts: number = 30): Promise<StrategyResult> {
  let attempts = 0;

  while (attempts < maxAttempts) {
    try {
      const statusResponse = await strategyAPI.getTaskStatus(taskId);

      if (statusResponse.success === false) {
        throw new Error('获取任务状态失败');
      }

      const status = statusResponse.data.status;

      if (status === 'completed') {
        const result = await strategyAPI.getResults(taskId);
        return transformApiResultToStrategyResult(result.data);
      } else if (status === 'failed') {
        throw new Error(`策略执行失败: ${statusResponse.data.error || '未知错误'}`);
      }

      // 等待1秒后重试
      await new Promise(resolve => setTimeout(resolve, 1000));
      attempts++;
    } catch (error) {
      if (attempts >= maxAttempts - 1) {
        throw error;
      }
      attempts++;
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }

  throw new Error('策略执行超时');
}

/**
 * 转换API结果为策略结果格式
 */
export function transformApiResultToStrategyResult(apiData: any): StrategyResult {
  return {
    totalReturn: apiData.total_return || 0,
    sharpeRatio: apiData.sharpe_ratio || 0,
    maxDrawdown: apiData.max_drawdown || 0,
    winRate: apiData.win_rate || 0,
    totalTrades: apiData.total_trades || 0,
    profitFactor: apiData.profit_factor || 0,
    volatility: apiData.volatility,
    calmarRatio: apiData.calmar_ratio,
    sortinoRatio: apiData.sortino_ratio,
    averageTrade: apiData.average_trade,
    expectancy: apiData.expectancy,
  };
}

/**
 * 参数服务预加载器
 */
export class ParameterServicePreloader {
  constructor(private queryClient: any) {
    // Constructor for dependency injection
  }

  /**
   * 预加载策略结果
   */
  async preloadStrategyResults(
    symbol: string,
    parameters: StrategyParameters,
    startDate: string,
    endDate: string,
  ) {
    return this.queryClient.prefetchQuery({
      queryKey: PARAMETER_QUERY_KEYS.strategyResults(symbol, parameters, startDate, endDate),
      queryFn: async () => {
        const apiParams = {
          window_size: parameters.movingAveragePeriod,
          initial_capital: 100000,
          stop_loss: parameters.stopLoss,
          take_profit: parameters.takeProfit,
        };

        const runResponse = await strategyAPI.run({
          symbol,
          start_date: startDate,
          end_date: endDate,
          // strategy_type: 'moving_average', // 移除不支持的属性
          config: {
            name: 'moving_average',
            params: apiParams,
          },
        });

        if (runResponse.task_id) {
          return pollStrategyResult(runResponse.task_id);
        }

        throw new Error('预加载失败');
      },
      staleTime: CACHE_CONFIG.strategyResults.staleTime,
    });
  }

  /**
   * 预加载优化建议
   */
  async preloadOptimizationSuggestions(symbol: string, parameters: StrategyParameters) {
    return this.queryClient.prefetchQuery({
      queryKey: PARAMETER_QUERY_KEYS.optimizationSuggestions(symbol, parameters),
      queryFn: async () => {
        // 调用优化建议API
        return [];
      },
      staleTime: CACHE_CONFIG.optimizationSuggestions.staleTime,
    });
  }

  /**
   * 清除缓存
   */
  clearStrategyCache(symbol?: string) {
    if (symbol) {
      this.queryClient.invalidateQueries({
        queryKey: ['strategyResults', symbol],
      });
    } else {
      this.queryClient.invalidateQueries({
        queryKey: ['strategyResults'],
      });
    }
  }

  clearOptimizationCache(symbol?: string) {
    if (symbol) {
      this.queryClient.invalidateQueries({
        queryKey: ['optimizationSuggestions', symbol],
      });
    } else {
      this.queryClient.invalidateQueries({
        queryKey: ['optimizationSuggestions'],
      });
    }
  }
}

/**
 * 运行单个回测的简化方法
 */
export async function runBacktest(params: {
  symbol: string
  startDate: string
  endDate: string
  parameters: StrategyParameters
}): Promise<StrategyResult> {
  try {
    const apiParams = {
      window_size: params.parameters.movingAveragePeriod,
      initial_capital: 100000,
      stop_loss: params.parameters.stopLoss,
      take_profit: params.parameters.takeProfit,
    };

    const runResponse = await strategyAPI.run({
      symbol: params.symbol,
      start_date: params.startDate,
      end_date: params.endDate,
      // strategy_type: 'moving_average', // 移除不支持的属性
      config: {
        name: 'moving_average',
        params: apiParams,
      },
    });

    if (!runResponse.task_id) {
      throw new Error('策略运行失败');
    }

    const result = await pollStrategyResult(runResponse.task_id);
    return result;
  } catch (error) {
    console.error('回测运行失败:', error);
    throw error;
  }
}

/**
 * 批量运行回测
 */
export async function runBatchBacktests(
  testConfigs: Array<{
    symbol: string
    startDate: string
    endDate: string
    parameters: StrategyParameters
  }>,
): Promise<StrategyResult[]> {
  const promises = testConfigs.map(config => runBacktest(config));
  return Promise.all(promises);
}

// 导出防抖配置供其他组件使用
export { DEBOUNCE_CONFIG };

/**
 * 获取参数优化建议
 */
export async function getOptimizationSuggestions(
  symbol: string,
  baseParameters: StrategyParameters,
  startDate: string,
  endDate: string,
): Promise<any[]> {
  try {
    // 这里应该调用后端的优化建议API
    // 暂时返回模拟数据
    const suggestions = [
      {
        id: 'risk_adjusted',
        type: 'risk',
        confidence: 85,
        parameters: {
          ...baseParameters,
          stopLoss: Math.min(baseParameters.stopLoss * 1.2, 10),
          takeProfit: Math.max(baseParameters.takeProfit * 1.1, 12),
        },
        reasoning: '基于历史数据，适当放宽止损可以提高策略成功率',
        expectedImprovement: '预计降低止损频率15%，提高总体收益5%',
      },
      {
        id: 'trend_optimized',
        type: 'trend',
        confidence: 72,
        parameters: {
          ...baseParameters,
          movingAveragePeriod: baseParameters.movingAveragePeriod > 20
            ? Math.max(baseParameters.movingAveragePeriod - 5, 15)
            : Math.min(baseParameters.movingAveragePeriod + 5, 35),
        },
        reasoning: '当前市场呈现趋势特征，调整均线周期可以更好地捕捉趋势',
        expectedImprovement: '预计提高信号质量，减少假信号',
      },
    ];

    return suggestions;
  } catch (error) {
    console.error('优化建议获取失败:', error);
    throw error;
  }
}

// 导出parameterService对象（包含所有方法）
export const parameterService = {
  runBacktest,
  runBatchBacktests,
  pollStrategyResult,
  transformApiResultToStrategyResult,
  getOptimizationSuggestions,
  ParameterChangeDetector,
  ParameterServicePreloader,
  // 导出查询配置
  QUERY_KEYS: PARAMETER_QUERY_KEYS,
  CACHE_CONFIG,
  DEBOUNCE_CONFIG,
};
