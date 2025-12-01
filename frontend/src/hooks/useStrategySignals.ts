import { useCallback, useEffect, useRef, useState } from 'react';
import {
  PRESET_STRATEGIES,
  SignalDifference,
  SignalFilter,
  StrategyConfig,
  StrategyParams,
  StrategySignal,
  StrategySignalResult,
  StrategyType,
  strategySignalManager,
} from '../types/strategySignal.types';
import { TimePeriod } from '../types/kline.types';
import { klineDataService } from '../services/klineService';
import { signalRenderer } from '../services/signalRendererService';

// Hook配置
interface UseStrategySignalsConfig {
  symbol: string;
  period: TimePeriod;
  chartId: string;
  autoUpdate?: boolean;
  updateInterval?: number;
  enableAnimation?: boolean;
  theme?: 'light' | 'dark';
}

// Hook返回值
interface UseStrategySignalsReturn {
  // 策略管理
  activeStrategies: Map<string, StrategyParams>;
  activateStrategy: (
    strategyId: string,
    params: StrategyParams,
  ) => Promise<void>;
  deactivateStrategy: (strategyId: string) => Promise<void>;
  updateStrategyParams: (
    strategyId: string,
    params: StrategyParams,
  ) => Promise<SignalDifference | null>;

  // 信号数据
  signals: Map<string, StrategySignalResult>;
  loading: boolean;
  error: string | null;

  // 信号操作
  refreshSignals: () => Promise<void>;
  filterSignals: (filter: SignalFilter) => Map<string, StrategySignal[]>;
  getRecentSignals: (strategyId: string, count?: number) => StrategySignal[];

  // 统计和分析
  getStatistics: (strategyId?: string) => Map<string, any>;
  compareStrategies: (strategyAId: string, strategyBId: string) => any;

  // 性能监控
  getPerformance: (strategyId: string) => any;

  // 预设策略
  presetStrategies: Record<string, StrategyConfig>;
}

// 自定义Hook：管理策略信号
export function useStrategySignals(
  config: UseStrategySignalsConfig,
): UseStrategySignalsReturn {
  const {
    symbol,
    period,
    chartId,
    autoUpdate = true,
    updateInterval = 30000, // 30秒
    enableAnimation = true,
    theme = 'light',
  } = config;

  // 状态管理
  const [activeStrategies, setActiveStrategies] = useState<
    Map<string, StrategyParams>
  >(new Map());
  const [signals, setSignals] = useState<Map<string, StrategySignalResult>>(
    new Map(),
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<number>(0);

  // Refs
  const intervalRef = useRef<NodeJS.Timeout>();
  const mountedRef = useRef(true);

  // 注册图表到渲染器
  useEffect(() => {
    // 这里需要传入实际的图表实例
    // const chartInstance = getChartInstance(chartId)
    // signalRenderer.registerChart(chartId, chartInstance)

    return () => {
      // signalRenderer.unregisterChart(chartId)
    };
  }, [chartId]);

  // 激活策略
  const activateStrategy = useCallback(
    async (strategyId: string, params: StrategyParams) => {
      try {
        setLoading(true);
        setError(null);

        // 激活策略到数据服务
        await klineDataService.activateStrategy(strategyId, params);

        // 更新本地状态
        setActiveStrategies((prev) => new Map(prev.set(strategyId, params)));

        // 获取信号数据
        await refreshSignals();
      } catch (err) {
        setError(
          `激活策略失败: ${err instanceof Error ? err.message : '未知错误'}`,
        );
        console.error('激活策略失败:', err);
      } finally {
        setLoading(false);
      }
    },
    [symbol, period],
  );

  // 停用策略
  const deactivateStrategy = useCallback(
    async (strategyId: string) => {
      try {
        setLoading(true);
        setError(null);

        // 从数据服务停用策略
        klineDataService.deactivateStrategy(strategyId);

        // 从渲染器移除标记点
        await signalRenderer.removeMarkers(chartId, [strategyId]);

        // 更新本地状态
        setActiveStrategies((prev) => {
          const newMap = new Map(prev);
          newMap.delete(strategyId);
          return newMap;
        });

        setSignals((prev) => {
          const newMap = new Map(prev);
          newMap.delete(strategyId);
          return newMap;
        });
      } catch (err) {
        setError(
          `停用策略失败: ${err instanceof Error ? err.message : '未知错误'}`,
        );
        console.error('停用策略失败:', err);
      } finally {
        setLoading(false);
      }
    },
    [chartId],
  );

  // 更新策略参数
  const updateStrategyParams = useCallback(
    async (strategyId: string, params: StrategyParams) => {
      try {
        setLoading(true);
        setError(null);

        // 获取旧的信号用于差异计算
        const oldSignals = signals.get(strategyId);

        // 更新策略参数
        const difference = await klineDataService.updateStrategyParams(
          strategyId,
          params,
          symbol,
          period,
        );

        // 更新本地状态
        setActiveStrategies((prev) => new Map(prev.set(strategyId, params)));

        // 刷新信号数据
        await refreshSignals();

        // 如果启用动画且有差异，执行动画过渡
        if (enableAnimation && difference && oldSignals) {
          await signalRenderer.animateMarkerTransition(chartId, difference);
        }

        return difference;
      } catch (err) {
        setError(
          `更新策略参数失败: ${err instanceof Error ? err.message : '未知错误'}`,
        );
        console.error('更新策略参数失败:', err);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [signals, symbol, period, chartId, enableAnimation],
  );

  // 刷新信号数据
  const refreshSignals = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const result = await klineDataService.getDataWithSignals(symbol, period);

      if (result && mountedRef.current) {
        const { signals: newSignals } = result;

        // 更新渲染器
        for (const [strategyId, signalResult] of newSignals) {
          const existingSignals = signals.get(strategyId);

          if (existingSignals) {
            // 更新现有标记点
            await signalRenderer.updateMarkers(chartId, signalResult.signals);
          } else {
            // 添加新标记点
            await signalRenderer.addMarkers(chartId, signalResult.signals);
          }
        }

        // 移除不再活跃的策略标记点
        for (const strategyId of signals.keys()) {
          if (!newSignals.has(strategyId)) {
            await signalRenderer.removeMarkers(chartId, [strategyId]);
          }
        }

        setSignals(newSignals);
        setLastUpdate(Date.now());
      }
    } catch (err) {
      setError(
        `刷新信号失败: ${err instanceof Error ? err.message : '未知错误'}`,
      );
      console.error('刷新信号失败:', err);
    } finally {
      setLoading(false);
    }
  }, [symbol, period, signals, chartId]);

  // 过滤信号
  const filterSignals = useCallback(
    (filter: SignalFilter) => {
      const filteredSignals = new Map<string, StrategySignal[]>();

      for (const [strategyId, signalResult] of signals) {
        const filtered = strategySignalManager.optimizeSignals(
          signalResult.signals,
          filter,
        );
        if (filtered.length > 0) {
          filteredSignals.set(strategyId, filtered);
        }
      }

      return filteredSignals;
    },
    [signals],
  );

  // 获取最近信号
  const getRecentSignals = useCallback(
    (strategyId: string, count: number = 10) => {
      const signalResult = signals.get(strategyId);
      if (!signalResult) {
        return [];
      }

      return signalResult.signals
        .sort((a, b) => b.timestamp - a.timestamp)
        .slice(0, count);
    },
    [signals],
  );

  // 获取统计信息
  const getStatistics = useCallback(
    (strategyId?: string) => {
      return klineDataService.getSignalStatistics(strategyId);
    },
    [signals],
  );

  // 比较策略
  const compareStrategies = useCallback(
    (strategyAId: string, strategyBId: string) => {
      return klineDataService.compareStrategies(strategyAId, strategyBId);
    },
    [signals],
  );

  // 获取性能指标
  const getPerformance = useCallback(
    (strategyId: string) => {
      return klineDataService.getStrategyPerformance(strategyId);
    },
    [signals],
  );

  // 自动更新
  useEffect(() => {
    if (autoUpdate && activeStrategies.size > 0) {
      intervalRef.current = setInterval(() => {
        refreshSignals();
      }, updateInterval);

      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    }
  }, [autoUpdate, activeStrategies.size, updateInterval, refreshSignals]);

  // 初始化时刷新一次
  useEffect(() => {
    if (symbol && period && activeStrategies.size > 0) {
      refreshSignals();
    }
  }, [symbol, period, activeStrategies.size, refreshSignals]);

  // 清理函数
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    // 策略管理
    activeStrategies,
    activateStrategy,
    deactivateStrategy,
    updateStrategyParams,

    // 信号数据
    signals,
    loading,
    error,

    // 信号操作
    refreshSignals,
    filterSignals,
    getRecentSignals,

    // 统计和分析
    getStatistics,
    compareStrategies,

    // 性能监控
    getPerformance,

    // 预设策略
    presetStrategies: PRESET_STRATEGIES,
  };
}

// 工具Hook：获取预设策略
export function usePresetStrategies() {
  const [strategies, setStrategies] =
    useState<Record<string, StrategyConfig>>(PRESET_STRATEGIES);

  const getStrategy = useCallback(
    (strategyId: string) => {
      return strategies[strategyId];
    },
    [strategies],
  );

  const addCustomStrategy = useCallback((strategy: StrategyConfig) => {
    setStrategies((prev) => ({
      ...prev,
      [strategy.id]: strategy,
    }));
  }, []);

  const removeCustomStrategy = useCallback((strategyId: string) => {
    setStrategies((prev) => {
      const newStrategies = { ...prev };
      delete newStrategies[strategyId];
      return newStrategies;
    });
  }, []);

  return {
    strategies,
    getStrategy,
    addCustomStrategy,
    removeCustomStrategy,
  };
}

// 工具Hook：管理信号缓存
export function useSignalCache() {
  const [cacheStats, setCacheStats] = useState<any>(null);

  const getCacheStats = useCallback(() => {
    // 从signalCacheService获取统计信息
    const stats = signalRenderer.getMarkerStats('default'); // 示例
    setCacheStats(stats);
  }, []);

  const clearCache = useCallback(() => {
    klineDataService.clearStrategyCache();
  }, []);

  useEffect(() => {
    getCacheStats();
    const interval = setInterval(getCacheStats, 30000); // 每30秒更新一次
    return () => clearInterval(interval);
  }, [getCacheStats]);

  return {
    cacheStats,
    clearCache,
    refreshStats: getCacheStats,
  };
}
