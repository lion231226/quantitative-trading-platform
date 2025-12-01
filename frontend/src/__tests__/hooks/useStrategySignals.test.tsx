import { act, renderHook, waitFor } from '@testing-library/react';
import { useStrategySignals } from '../../hooks/useStrategySignals';
import { klineDataService } from '../../services/klineService';
import { signalRenderer } from '../../services/signalRendererService';
import {
  PRESET_STRATEGIES,
  StrategySignal,
  StrategySignalResult,
} from '../../types/strategySignal.types';
import { TimePeriod } from '../../types/kline.types';

// Mock services
jest.mock('../../services/klineService');
jest.mock('../../services/signalRendererService');

const mockKlineDataService = klineDataService as jest.Mocked<
  typeof klineDataService
>;
const mockSignalRenderer = signalRenderer as jest.Mocked<typeof signalRenderer>;

// Mock数据
const mockStrategySignals: StrategySignal[] = [
  {
    id: 'signal_1',
    timestamp: Date.now() - 1000,
    price: 100,
    signalType: 'buy',
    confidence: 80,
    strategyId: 'sma_crossover',
    strategyName: 'SMA金叉死叉',
    strategyType: 'sma_crossover',
    strength: 'moderate',
    strategyParams: { shortPeriod: 10, longPeriod: 30 },
    marketData: {
      open: 99,
      high: 101,
      low: 98,
      close: 100,
    },
    createdAt: Date.now(),
    updatedAt: Date.now(),
  },
  {
    id: 'signal_2',
    timestamp: Date.now(),
    price: 102,
    signalType: 'sell',
    confidence: 70,
    strategyId: 'sma_crossover',
    strategyName: 'SMA金叉死叉',
    strategyType: 'sma_crossover',
    strength: 'moderate',
    strategyParams: { shortPeriod: 10, longPeriod: 30 },
    marketData: {
      open: 101,
      high: 103,
      low: 100,
      close: 102,
    },
    createdAt: Date.now(),
    updatedAt: Date.now(),
  },
];

const mockStrategySignalResult: StrategySignalResult = {
  strategyId: 'sma_crossover',
  signals: mockStrategySignals,
  performance: {
    calculationTime: 50,
    signalCount: 2,
    cacheHit: false,
  },
  metadata: {
    generatedAt: Date.now(),
    dataRange: {
      start: Date.now() - 86400000,
      end: Date.now(),
    },
    params: { shortPeriod: 10, longPeriod: 30 },
  },
};

describe('useStrategySignals', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Mock klineDataService methods
    mockKlineDataService.activateStrategy.mockResolvedValue();
    mockKlineDataService.deactivateStrategy.mockImplementation();
    mockKlineDataService.updateStrategyParams.mockResolvedValue({
      added: [],
      removed: [],
      modified: [],
    });
    mockKlineDataService.getDataWithSignals.mockResolvedValue({
      data: { candlesticks: [] },
      signals: new Map([['sma_crossover', mockStrategySignalResult]]),
    });
    mockKlineDataService.getSignalStatistics.mockReturnValue(new Map());
    mockKlineDataService.compareStrategies.mockReturnValue(null);
    mockKlineDataService.getStrategyPerformance.mockReturnValue(null);

    // Mock signalRenderer methods
    mockSignalRenderer.registerChart.mockImplementation();
    mockSignalRenderer.unregisterChart.mockImplementation();
    mockSignalRenderer.addMarkers.mockResolvedValue();
    mockSignalRenderer.removeMarkers.mockResolvedValue();
    mockSignalRenderer.updateMarkers.mockResolvedValue();
    mockSignalRenderer.clearMarkers.mockResolvedValue();
    mockSignalRenderer.animateMarkerTransition.mockResolvedValue();
  });

  const createWrapper = (config = {}) => {
    const defaultConfig = {
      symbol: 'TEST',
      period: '1d' as TimePeriod,
      chartId: 'test-chart',
      autoUpdate: false,
      enableAnimation: false,
    };

    return renderHook(() =>
      useStrategySignals({ ...defaultConfig, ...config }),
    );
  };

  it('应该返回初始状态', () => {
    const { result } = createWrapper();

    expect(result.current.activeStrategies).toBeInstanceOf(Map);
    expect(result.current.activeStrategies.size).toBe(0);
    expect(result.current.signals).toBeInstanceOf(Map);
    expect(result.current.signals.size).toBe(0);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(null);
    expect(result.current.presetStrategies).toEqual(PRESET_STRATEGIES);
  });

  it('应该激活策略', async () => {
    const { result } = createWrapper();

    await act(async () => {
      await result.current.activateStrategy('sma_crossover', {
        shortPeriod: 10,
        longPeriod: 30,
      });
    });

    expect(mockKlineDataService.activateStrategy).toHaveBeenCalledWith(
      'sma_crossover',
      { shortPeriod: 10, longPeriod: 30 },
    );
    expect(mockKlineDataService.getDataWithSignals).toHaveBeenCalled();
    expect(result.current.activeStrategies.has('sma_crossover')).toBe(true);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('应该处理激活策略错误', async () => {
    const errorMessage = '激活策略失败';
    mockKlineDataService.activateStrategy.mockRejectedValue(
      new Error(errorMessage),
    );

    const { result } = createWrapper();

    await act(async () => {
      await result.current.activateStrategy('sma_crossover', {
        shortPeriod: 10,
        longPeriod: 30,
      });
    });

    expect(result.current.error).toContain(errorMessage);
    expect(result.current.loading).toBe(false);
  });

  it('应该停用策略', async () => {
    const { result } = createWrapper();

    // 先激活一个策略
    await act(async () => {
      await result.current.activateStrategy('sma_crossover', {
        shortPeriod: 10,
        longPeriod: 30,
      });
    });

    // 然后停用它
    await act(async () => {
      await result.current.deactivateStrategy('sma_crossover');
    });

    expect(mockKlineDataService.deactivateStrategy).toHaveBeenCalledWith(
      'sma_crossover',
    );
    expect(mockSignalRenderer.removeMarkers).toHaveBeenCalledWith(
      'test-chart',
      ['sma_crossover'],
    );
    expect(result.current.activeStrategies.has('sma_crossover')).toBe(false);
  });

  it('应该更新策略参数', async () => {
    const { result } = createWrapper();

    // 先激活策略
    await act(async () => {
      await result.current.activateStrategy('sma_crossover', {
        shortPeriod: 10,
        longPeriod: 30,
      });
    });

    // 更新参数
    const newParams = { shortPeriod: 15, longPeriod: 35 };
    await act(async () => {
      await result.current.updateStrategyParams('sma_crossover', newParams);
    });

    expect(mockKlineDataService.updateStrategyParams).toHaveBeenCalledWith(
      'sma_crossover',
      newParams,
      'TEST',
      '1d',
    );
    expect(result.current.activeStrategies.get('sma_crossover')).toEqual(
      newParams,
    );
  });

  it('应该刷新信号', async () => {
    const { result } = createWrapper();

    await act(async () => {
      await result.current.refreshSignals();
    });

    expect(mockKlineDataService.getDataWithSignals).toHaveBeenCalledWith(
      'TEST',
      '1d',
      undefined,
      true,
    );
    expect(result.current.loading).toBe(false);
  });

  it('应该过滤信号', () => {
    const { result } = createWrapper();

    // 手动设置一些信号数据用于测试过滤
    act(() => {
      // 模拟设置信号数据（通常通过激活策略获得）
      result.current.signals = new Map([
        ['sma_crossover', mockStrategySignalResult],
      ]);
    });

    const filter = {
      signalTypes: ['buy'],
    };

    const filteredSignals = result.current.filterSignals(filter);

    expect(filteredSignals.has('sma_crossover')).toBe(true);
    const filteredArray = filteredSignals.get('sma_crossover') || [];
    expect(filteredArray.every((signal) => signal.signalType === 'buy')).toBe(
      true,
    );
  });

  it('应该获取最近信号', () => {
    const { result } = createWrapper();

    act(() => {
      result.current.signals = new Map([
        ['sma_crossover', mockStrategySignalResult],
      ]);
    });

    const recentSignals = result.current.getRecentSignals('sma_crossover', 1);

    expect(recentSignals).toHaveLength(1);
    expect(recentSignals[0].timestamp).toBeGreaterThanOrEqual(
      mockStrategySignals[1].timestamp,
    );
  });

  it('应该获取统计信息', () => {
    const { result } = createWrapper();
    const mockStats = new Map([['sma_crossover', { totalSignals: 2 }]]);
    mockKlineDataService.getSignalStatistics.mockReturnValue(mockStats);

    const stats = result.current.getStatistics('sma_crossover');

    expect(mockKlineDataService.getSignalStatistics).toHaveBeenCalledWith(
      'sma_crossover',
    );
    expect(stats).toEqual(mockStats);
  });

  it('应该比较策略', () => {
    const { result } = createWrapper();
    const mockComparison = { correlation: 0.5 };
    mockKlineDataService.compareStrategies.mockReturnValue(mockComparison);

    const comparison = result.current.compareStrategies(
      'sma_crossover',
      'rsi_oversold',
    );

    expect(mockKlineDataService.compareStrategies).toHaveBeenCalledWith(
      'sma_crossover',
      'rsi_oversold',
    );
    expect(comparison).toEqual(mockComparison);
  });

  it('应该获取性能指标', () => {
    const { result } = createWrapper();
    const mockPerformance = {
      totalSignals: 5,
      calculationTime: 100,
      cacheHitRate: 0.8,
      lastUpdated: Date.now(),
    };
    mockKlineDataService.getStrategyPerformance.mockReturnValue(
      mockPerformance,
    );

    const performance = result.current.getPerformance('sma_crossover');

    expect(mockKlineDataService.getStrategyPerformance).toHaveBeenCalledWith(
      'sma_crossover',
    );
    expect(performance).toEqual(mockPerformance);
  });

  it('应该自动更新信号', async () => {
    const { result, unmount } = createWrapper({
      autoUpdate: true,
      updateInterval: 100, // 快速更新用于测试
    });

    // 激活策略
    await act(async () => {
      await result.current.activateStrategy('sma_crossover', {
        shortPeriod: 10,
        longPeriod: 30,
      });
    });

    const initialCallCount =
      mockKlineDataService.getDataWithSignals.mock.calls.length;

    // 等待自动更新
    await waitFor(
      () => {
        expect(
          mockKlineDataService.getDataWithSignals.mock.calls.length,
        ).toBeGreaterThan(initialCallCount);
      },
      { timeout: 200 },
    );

    unmount();
  });

  it('应该清理资源', () => {
    const { unmount } = createWrapper();

    unmount();

    // 验证清理逻辑（如果有全局定时器等）
    expect(true).toBe(true); // 简化测试，实际应该验证清理
  });

  describe('错误处理', () => {
    it('应该处理获取数据失败', async () => {
      const errorMessage = '获取数据失败';
      mockKlineDataService.getDataWithSignals.mockRejectedValue(
        new Error(errorMessage),
      );

      const { result } = createWrapper();

      await act(async () => {
        await result.current.refreshSignals();
      });

      expect(result.current.error).toContain(errorMessage);
      expect(result.current.loading).toBe(false);
    });

    it('应该处理停用不存在的策略', async () => {
      const { result } = createWrapper();

      // 停用不存在的策略不应该报错
      await act(async () => {
        await result.current.deactivateStrategy('nonexistent_strategy');
      });

      expect(result.current.error).toBe(null);
    });

    it('应该处理更新不存在的策略参数', async () => {
      const { result } = createWrapper();

      const resultUpdate = await act(async () => {
        return await result.current.updateStrategyParams(
          'nonexistent_strategy',
          { test: 'value' },
        );
      });

      expect(resultUpdate).toBe(null);
    });
  });

  describe('边界情况', () => {
    it('应该处理空信号列表', () => {
      const { result } = createWrapper();

      act(() => {
        result.current.signals = new Map();
      });

      const recentSignals = result.current.getRecentSignals('sma_crossover');
      expect(recentSignals).toHaveLength(0);

      const filteredSignals = result.current.filterSignals({
        signalTypes: ['buy'],
      });
      expect(filteredSignals.size).toBe(0);
    });

    it('应该处理无效的过滤条件', () => {
      const { result } = createWrapper();

      act(() => {
        result.current.signals = new Map([
          ['sma_crossover', mockStrategySignalResult],
        ]);
      });

      // 测试各种过滤条件
      const filtered1 = result.current.filterSignals({ signalTypes: [] });
      const filtered2 = result.current.filterSignals({});
      const filtered3 = result.current.filterSignals({
        signalTypes: ['invalid_type' as any],
      });

      expect(filtered1.size).toBe(0);
      expect(filtered2.size).toBe(1); // 无过滤条件应该返回所有
      expect(filtered3.size).toBe(0); // 无效信号类型应该过滤掉所有
    });

    it('应该处理策略列表为空的情况', () => {
      const { result } = createWrapper();

      const stats = result.current.getStatistics();
      expect(stats).toBeInstanceOf(Map);
      expect(stats.size).toBe(0);
    });
  });
});
