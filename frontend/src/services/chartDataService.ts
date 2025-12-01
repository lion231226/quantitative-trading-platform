import {
  UseQueryOptions,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { useEffect, useMemo } from 'react';
import { marketDataAPI, strategyAPI } from '@/lib/api';
import {
  ChartData,
  MovingAverageLine,
  PricePoint,
  TradingSignal,
} from '@/types/chart.types';
import { calculateEMA, calculateSMA } from '@/utils/chartHelpers';

// 查询键常量
export const CHART_QUERY_KEYS = {
  marketData: (symbol: string, startDate: string, endDate: string) =>
    ['marketData', symbol, startDate, endDate] as const,
  strategyResults: (runId: string) => ['strategyResults', runId] as const,
  chartData: (
    symbol: string,
    startDate: string,
    endDate: string,
    config: any,
  ) => ['chartData', symbol, startDate, endDate, config] as const,
} as const;

// 数据缓存配置
const CACHE_CONFIG = {
  marketData: {
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  },
  strategyResults: {
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
  },
};

// 获取市场数据
export function useMarketData(
  symbol: string,
  startDate: string,
  endDate: string,
  options?: Partial<UseQueryOptions<any[], Error>>,
) {
  return useQuery({
    queryKey: CHART_QUERY_KEYS.marketData(symbol, startDate, endDate),
    queryFn: () =>
      marketDataAPI.getHistory({
        symbol,
        start_date: startDate,
        end_date: endDate,
      }),
    staleTime: CACHE_CONFIG.marketData.staleTime,
    gcTime: CACHE_CONFIG.marketData.gcTime,
    enabled: !!(symbol && startDate && endDate),
    ...options,
  });
}

// 获取策略结果
export function useStrategyResults(
  runId: string,
  options?: Partial<UseQueryOptions<any, Error>>,
) {
  return useQuery({
    queryKey: CHART_QUERY_KEYS.strategyResults(runId),
    queryFn: () => strategyAPI.getResults(runId),
    staleTime: CACHE_CONFIG.strategyResults.staleTime,
    gcTime: CACHE_CONFIG.strategyResults.gcTime,
    enabled: !!runId,
    ...options,
  });
}

// 组合图表数据Hook
export function useChartData(
  symbol: string,
  startDate: string,
  endDate: string,
  strategyRunId?: string,
  movingAverageConfig?: { type: 'SMA' | 'EMA'; period: number },
  options?: Partial<UseQueryOptions<ChartData, Error>>,
) {
  const marketDataQuery = useMarketData(symbol, startDate, endDate);
  const strategyResultsQuery = useStrategyResults(strategyRunId || '', {
    enabled: !!strategyRunId,
  });

  const chartData = useMemo<ChartData>(() => {
    const prices: PricePoint[] =
      marketDataQuery.data?.map((item) => ({
        timestamp: item.date,
        open: item.open,
        high: item.high,
        low: item.low,
        close: item.close,
      })) || [];

    const signals: TradingSignal[] = [];
    const movingAverages: MovingAverageLine[] = [];

    // 处理策略结果（如果有）
    if (strategyResultsQuery.data) {
      // 这里需要根据实际的策略结果结构来解析信号
      // 暂时使用示例数据
      const strategyData = strategyResultsQuery.data;
      if (strategyData.signals) {
        signals.push(
          ...strategyData.signals.map((signal: any) => ({
            timestamp: signal.timestamp,
            type: signal.type,
            price: signal.price,
            strategy: signal.strategy || 'Unknown',
          })),
        );
      }
    }

    // 计算移动平均线
    if (movingAverageConfig && prices.length > 0) {
      const closePrices = prices.map((p) => p.close);
      const maValues =
        movingAverageConfig.type === 'SMA'
          ? calculateSMA(closePrices, movingAverageConfig.period)
          : calculateEMA(closePrices, movingAverageConfig.period);

      maValues.forEach((value, index) => {
        if (index + movingAverageConfig.period - 1 < prices.length) {
          movingAverages.push({
            timestamp: prices[index + movingAverageConfig.period - 1].timestamp,
            value,
            type: movingAverageConfig.type,
            period: movingAverageConfig.period,
          });
        }
      });
    }

    return {
      prices,
      signals,
      movingAverages,
    };
  }, [marketDataQuery.data, strategyResultsQuery.data, movingAverageConfig]);

  const isLoading =
    marketDataQuery.isLoading ||
    (strategyRunId ? strategyResultsQuery.isLoading : false);
  const error = marketDataQuery.error || strategyResultsQuery.error;

  return {
    data: chartData,
    isLoading,
    error,
    refetch: () => {
      marketDataQuery.refetch();
      if (strategyRunId) {
        strategyResultsQuery.refetch();
      }
    },
  };
}

// 数据预加载服务
export class ChartDataPreloader {
  constructor(private queryClient: any) {
    // Constructor with dependency injection
  }

  // 预加载市场数据
  async preloadMarketData(symbol: string, startDate: string, endDate: string) {
    return this.queryClient.prefetchQuery({
      queryKey: CHART_QUERY_KEYS.marketData(symbol, startDate, endDate),
      queryFn: () =>
        marketDataAPI.getHistory({
          symbol,
          start_date: startDate,
          end_date: endDate,
        }),
      staleTime: CACHE_CONFIG.marketData.staleTime,
    });
  }

  // 预加载策略结果
  async preloadStrategyResults(runId: string) {
    return this.queryClient.prefetchQuery({
      queryKey: CHART_QUERY_KEYS.strategyResults(runId),
      queryFn: () => strategyAPI.getResults(runId),
      staleTime: CACHE_CONFIG.strategyResults.staleTime,
    });
  }

  // 清除缓存
  clearMarketDataCache(symbol?: string) {
    if (symbol) {
      this.queryClient.invalidateQueries({
        queryKey: ['marketData', symbol],
      });
    } else {
      this.queryClient.invalidateQueries({
        queryKey: ['marketData'],
      });
    }
  }

  clearStrategyResultsCache(runId?: string) {
    if (runId) {
      this.queryClient.invalidateQueries({
        queryKey: ['strategyResults', runId],
      });
    } else {
      this.queryClient.invalidateQueries({
        queryKey: ['strategyResults'],
      });
    }
  }
}

// 实时数据更新Hook（用于未来WebSocket集成）
export function useRealTimeChartData(
  symbol: string,
  enabled: boolean = false,
  onUpdate?: (data: ChartData) => void,
) {
  const queryClient = useQueryClient();

  // 模拟实时更新（将来替换为WebSocket）
  const simulateRealTimeUpdate = () => {
    if (!enabled) return;

    const interval = setInterval(() => {
      // 获取最新数据并更新缓存
      queryClient.invalidateQueries({
        queryKey: ['marketData', symbol],
      });
    }, 30000); // 30秒更新一次

    return () => clearInterval(interval);
  };

  // 在实际实现中，这里会建立WebSocket连接
  useEffect(() => {
    const cleanup = simulateRealTimeUpdate();
    return cleanup;
  }, [symbol, enabled]);

  return {
    startRealTimeUpdates: () => {
      // 实现实时更新逻辑
    },
    stopRealTimeUpdates: () => {
      // 停止实时更新
    },
  };
}

// 数据验证工具
export function validateChartData(data: ChartData): boolean {
  if (!data || !data.prices || data.prices.length === 0) {
    return false;
  }

  // 验证价格数据
  const invalidPrices = data.prices.filter(
    (point) => !point.timestamp || point.close <= 0,
  );
  if (invalidPrices.length > 0) {
    console.warn('Invalid price data found:', invalidPrices);
    return false;
  }

  // 验证信号数据
  if (data.signals) {
    const invalidSignals = data.signals.filter(
      (signal) => !signal.timestamp || !signal.type || signal.price <= 0,
    );
    if (invalidSignals.length > 0) {
      console.warn('Invalid signal data found:', invalidSignals);
    }
  }

  return true;
}

// 数据转换工具
export function transformMarketDataToChartData(marketData: any[]): ChartData {
  return {
    prices: marketData.map((item) => ({
      timestamp: item.date,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
    })),
    signals: [],
    movingAverages: [],
  };
}
