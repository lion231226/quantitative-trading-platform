'use client';

import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { debounce } from 'lodash';
import { marketDataAPI } from '@/lib/api';
import {
  ComparisonError,
  ComparisonService,
  ComparisonSummary,
  CorrelationMatrix,
  PerformanceMetrics,
  VarietyComparisonRequest,
  VarietyComparisonResult,
  VarietyRanking,
  VarietyResult,
} from '@/types/comparison.types';
import { StrategyConfig } from '@/types/api';

// API端点
const COMPARISON_ENDPOINTS = {
  RUN_COMPARISON: '/api/v1/comparison/run',
  GET_RESULTS: '/api/v1/comparison/results',
  CANCEL_COMPARISON: '/api/v1/comparison/cancel',
  GET_AVAILABLE_METRICS: '/api/v1/comparison/metrics',
  HISTORICAL_COMPARISON: '/api/v1/comparison/historical',
} as const;

// 对比分析服务实现
class ComparisonServiceImplementation implements ComparisonService {
  private baseURL: string;

  constructor(baseURL: string = '') {
    this.baseURL = baseURL;
  }

  async runComparison(
    request: VarietyComparisonRequest,
  ): Promise<VarietyComparisonResult> {
    try {
      const response = await fetch(
        `${this.baseURL}${COMPARISON_ENDPOINTS.RUN_COMPARISON}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(request),
        },
      );

      if (!response.ok) {
        const errorData: ComparisonError = await response.json();
        throw new Error(`对比分析失败: ${errorData.message}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Comparison service error:', error);
      throw error;
    }
  }

  async getComparisonResults(
    requestId: string,
  ): Promise<VarietyComparisonResult> {
    try {
      const response = await fetch(
        `${this.baseURL}${COMPARISON_ENDPOINTS.GET_RESULTS}/${requestId}`,
      );

      if (!response.ok) {
        throw new Error('获取对比结果失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Get comparison results error:', error);
      throw error;
    }
  }

  async cancelComparison(requestId: string): Promise<void> {
    try {
      const response = await fetch(
        `${this.baseURL}${COMPARISON_ENDPOINTS.CANCEL_COMPARISON}/${requestId}`,
        {
          method: 'DELETE',
        },
      );

      if (!response.ok) {
        throw new Error('取消对比分析失败');
      }
    } catch (error) {
      console.error('Cancel comparison error:', error);
      throw error;
    }
  }

  async getAvailableMetrics(): Promise<string[]> {
    try {
      const response = await fetch(
        `${this.baseURL}${COMPARISON_ENDPOINTS.GET_AVAILABLE_METRICS}`,
      );

      if (!response.ok) {
        throw new Error('获取可用指标失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Get available metrics error:', error);
      throw error;
    }
  }

  async getHistoricalComparison(
    symbols: string[],
    days: number,
  ): Promise<VarietyComparisonResult> {
    try {
      const response = await fetch(
        `${this.baseURL}${COMPARISON_ENDPOINTS.HISTORICAL_COMPARISON}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ symbols, days }),
        },
      );

      if (!response.ok) {
        throw new Error('获取历史对比数据失败');
      }

      return await response.json();
    } catch (error) {
      console.error('Get historical comparison error:', error);
      throw error;
    }
  }
}

// 创建服务实例
const comparisonService = new ComparisonServiceImplementation();

// React Query Keys
export const COMPARISON_QUERY_KEYS = {
  comparison: (requestId: string) => ['comparison', requestId],
  availableMetrics: () => ['comparison', 'metrics'],
  historicalComparison: (symbols: string[], days: number) => [
    'comparison',
    'historical',
    symbols,
    days,
  ],
} as const;

// 基础对比分析Hook
export function useVarietyComparison(request: VarietyComparisonRequest) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: COMPARISON_QUERY_KEYS.comparison('current'),
    queryFn: () => comparisonService.runComparison(request),
    enabled: !!request.symbols.length && request.symbols.length > 1,
    staleTime: 5 * 60 * 1000, // 5分钟缓存
    gcTime: 10 * 60 * 1000, // 10分钟垃圾回收
    retry: 2,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    onError: (error) => {
      console.error('Variety comparison error:', error);
    },
    onSuccess: (data) => {
      // 预加载相关数据
      if (data.results?.length > 0) {
        const symbols = data.results.map((r) => r.symbol);
        // 可以在这里预加载其他相关数据
      }
    },
  });
}

// 对比结果查询Hook
export function useComparisonResults(requestId: string) {
  return useQuery({
    queryKey: COMPARISON_QUERY_KEYS.comparison(requestId),
    queryFn: () => comparisonService.getComparisonResults(requestId),
    enabled: !!requestId,
    staleTime: 2 * 60 * 1000, // 2分钟缓存
    refetchInterval: (data) => {
      // 如果还在计算中，每5秒刷新一次
      return data?.summary?.successfulVarieties === 0 ? 5000 : false;
    },
  });
}

// 可用指标查询Hook
export function useAvailableMetrics() {
  return useQuery({
    queryKey: COMPARISON_QUERY_KEYS.availableMetrics(),
    queryFn: () => comparisonService.getAvailableMetrics(),
    staleTime: 60 * 60 * 1000, // 1小时缓存
  });
}

// 历史对比数据Hook
export function useHistoricalComparison(symbols: string[], days: number = 30) {
  return useQuery({
    queryKey: COMPARISON_QUERY_KEYS.historicalComparison(symbols, days),
    queryFn: () => comparisonService.getHistoricalComparison(symbols, days),
    enabled: symbols.length > 1,
    staleTime: 30 * 60 * 1000, // 30分钟缓存
  });
}

// 对比分析变更Hook（用于实时更新）
export function useComparisonMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: VarietyComparisonRequest) =>
      comparisonService.runComparison(request),
    onSuccess: (data) => {
      queryClient.setQueryData(
        COMPARISON_QUERY_KEYS.comparison(data.requestId),
        data,
      );
    },
    onError: (error) => {
      console.error('Comparison mutation error:', error);
    },
  });
}

// 并行对比Hook（用于多品种同时分析）
export function useParallelComparison(requests: VarietyComparisonRequest[]) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: [
      'comparison',
      'parallel',
      requests.map((r) => r.symbols.join(',')).join('|'),
    ],
    queryFn: async () => {
      const promises = requests.map((request) =>
        comparisonService.runComparison(request),
      );
      return Promise.all(promises);
    },
    enabled: requests.length > 0,
    staleTime: 5 * 60 * 1000,
  });
}

// 防抖对比Hook（避免频繁请求）
export function useDebouncedComparison(
  request: VarietyComparisonRequest,
  delay: number = 1000,
) {
  const [debouncedRequest, setDebouncedRequest] = useState(request);

  // 防抖处理
  const debouncedSetRequest = useMemo(
    () => debounce(setDebouncedRequest, delay),
    [delay],
  );

  useEffect(() => {
    debouncedSetRequest(request);
  }, [request, debouncedSetRequest]);

  return useVarietyComparison(debouncedRequest);
}

// 对比数据缓存管理
export function useComparisonCache() {
  const queryClient = useQueryClient();

  const clearComparisonCache = () => {
    queryClient.invalidateQueries({ queryKey: ['comparison'] });
  };

  const prefetchComparison = (request: VarietyComparisonRequest) => {
    queryClient.prefetchQuery({
      queryKey: COMPARISON_QUERY_KEYS.comparison('prefetch'),
      queryFn: () => comparisonService.runComparison(request),
      staleTime: 5 * 60 * 1000,
    });
  };

  const getComparisonData = (requestId: string) => {
    return queryClient.getQueryData<VarietyComparisonResult>(
      COMPARISON_QUERY_KEYS.comparison(requestId),
    );
  };

  return {
    clearComparisonCache,
    prefetchComparison,
    getComparisonData,
  };
}

// 对比分析预加载Hook
export function useComparisonPreloader(varieties: string[]) {
  const { prefetchComparison } = useComparisonCache();

  useEffect(() => {
    if (varieties.length >= 2) {
      // 预加载常用对比组合
      const commonPairs = [];
      for (let i = 0; i < Math.min(varieties.length, 3); i++) {
        for (let j = i + 1; j < Math.min(varieties.length, 4); j++) {
          commonPairs.push([varieties[i], varieties[j]]);
        }
      }

      commonPairs.forEach((pair) => {
        const request: VarietyComparisonRequest = {
          symbols: pair,
          startDate: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000)
            .toISOString()
            .split('T')[0],
          endDate: new Date().toISOString().split('T')[0],
          strategy: {
            name: 'SMA',
            params: { short_window: 5, long_window: 20 },
          },
        };
        prefetchComparison(request);
      });
    }
  }, [varieties, prefetchComparison]);
}

// 对比数据变化检测Hook
export function useComparisonChangeDetector(
  currentResults: VarietyComparisonResult | undefined,
  previousResults: VarietyComparisonResult | undefined,
) {
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (!currentResults || !previousResults) {
      setHasChanges(false);
      return;
    }

    // 检查关键指标是否有变化
    const changes = currentResults.results.some((result, index) => {
      const prevResult = previousResults.results[index];
      if (!prevResult) return true;

      return (
        Math.abs(result.metrics.totalReturn - prevResult.metrics.totalReturn) >
          0.01 ||
        Math.abs(result.metrics.sharpeRatio - prevResult.metrics.sharpeRatio) >
          0.01 ||
        Math.abs(result.metrics.maxDrawdown - prevResult.metrics.maxDrawdown) >
          0.01
      );
    });

    setHasChanges(changes);
  }, [currentResults, previousResults]);

  return hasChanges;
}

// 导出默认服务实例
export { comparisonService };
export default comparisonService;
