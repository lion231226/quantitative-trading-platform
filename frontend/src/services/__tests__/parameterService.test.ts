import {
  DEBOUNCE_CONFIG,
  ParameterChangeDetector,
  ParameterServicePreloader,
  pollStrategyResult,
  transformApiResultToStrategyResult,
} from '../parameterService';
import { StrategyParameters, StrategyResult } from '@/types/parameter.types';

// Mock dependencies
jest.mock('@/lib/api', () => ({
  strategyAPI: {
    run: jest.fn(),
    getTaskStatus: jest.fn(),
    getResults: jest.fn(),
  },
}));

jest.mock('@/utils/parameterHelpers', () => ({
  validateAllParameters: jest.fn(),
  generateParameterDescription: jest.fn(),
  areParametersEqual: jest.fn(),
}));

import { strategyAPI } from '@/lib/api';
import { areParametersEqual, validateAllParameters } from '@/utils/parameterHelpers';

const mockStrategyAPI = strategyAPI as jest.Mocked<typeof strategyAPI>;
const mockValidateAllParameters = validateAllParameters as jest.MockedFunction<typeof validateAllParameters>;
const mockAreParametersEqual = areParametersEqual as jest.MockedFunction<typeof areParametersEqual>;

describe('ParameterChangeDetector', () => {
  let detector: ParameterChangeDetector;
  const mockOnChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    detector = new ParameterChangeDetector(mockOnChange, 100);
  });

  afterEach(() => {
    detector.destroy();
  });

  it('应该检测参数变化', () => {
    const params1: StrategyParameters = { movingAveragePeriod: 20, stopLoss: 5.0, takeProfit: 10.0 };
    const params2: StrategyParameters = { movingAveragePeriod: 25, stopLoss: 5.0, takeProfit: 10.0 };

    // 先调用一次设置lastParameters
    detector.detectChange(params1);
    mockAreParametersEqual.mockClear();

    mockAreParametersEqual.mockReturnValue(false);

    const hasChanged = detector.detectChange(params2);

    expect(hasChanged).toBe(true);
    expect(mockAreParametersEqual).toHaveBeenCalledWith(params1, params2);
  });

  it('应该忽略相同的参数', () => {
    const params: StrategyParameters = { movingAveragePeriod: 20, stopLoss: 5.0, takeProfit: 10.0 };

    // 先设置一次参数
    detector.detectChange(params);
    mockAreParametersEqual.mockClear();
    mockOnChange.mockClear();

    mockAreParametersEqual.mockReturnValue(true);

    const hasChanged = detector.detectChange(params);

    expect(hasChanged).toBe(false);
    expect(mockOnChange).not.toHaveBeenCalled();
  });

  it('应该立即执行变化当immediate为true', (done) => {
    const params: StrategyParameters = { movingAveragePeriod: 20, stopLoss: 5.0, takeProfit: 10.0 };

    mockAreParametersEqual.mockReturnValue(false);

    detector.detectChange(params, true);

    // 立即执行，不需要等待防抖
    expect(mockOnChange).toHaveBeenCalledWith(params);
    done();
  });

  it('应该防抖执行变化', (done) => {
    const params1: StrategyParameters = { movingAveragePeriod: 20, stopLoss: 5.0, takeProfit: 10.0 };
    const params2: StrategyParameters = { movingAveragePeriod: 25, stopLoss: 5.0, takeProfit: 10.0 };
    const params3: StrategyParameters = { movingAveragePeriod: 30, stopLoss: 5.0, takeProfit: 10.0 };

    mockAreParametersEqual.mockReturnValue(false);

    detector.detectChange(params1);
    detector.detectChange(params2);
    detector.detectChange(params3);

    // 应该只执行最后一次调用
    setTimeout(() => {
      expect(mockOnChange).toHaveBeenCalledTimes(1);
      expect(mockOnChange).toHaveBeenCalledWith(params3);
      done();
    }, 150);
  });

  it('应该支持注册和移除回调', () => {
    const callback1 = jest.fn();
    const callback2 = jest.fn();
    const params: StrategyParameters = { movingAveragePeriod: 20, stopLoss: 5.0, takeProfit: 10.0 };

    mockAreParametersEqual.mockReturnValue(false);

    detector.onChange('callback1', callback1);
    detector.onChange('callback2', callback2);
    detector.detectChange(params, true);

    expect(callback1).toHaveBeenCalledWith(params);
    expect(callback2).toHaveBeenCalledWith(params);

    detector.offChange('callback1');
    detector.detectChange({ ...params, movingAveragePeriod: 25 }, true);

    expect(callback1).toHaveBeenCalledTimes(1); // 不再调用
    expect(callback2).toHaveBeenCalledTimes(2); // 仍然调用
  });

  it('应该强制立即执行', () => {
    const params: StrategyParameters = { movingAveragePeriod: 20, stopLoss: 5.0, takeProfit: 10.0 };

    mockAreParametersEqual.mockReturnValue(false);

    detector.detectChange(params, false); // 防抖模式
    detector.flush(); // 强制执行

    expect(mockOnChange).toHaveBeenCalledWith(params);
  });

  it('应该正确清理资源', () => {
    const callback = jest.fn();
    const params: StrategyParameters = { movingAveragePeriod: 20, stopLoss: 5.0, takeProfit: 10.0 };

    mockAreParametersEqual.mockReturnValue(false);

    detector.onChange('callback', callback);
    detector.detectChange(params, false);

    // 销毁后再等待防抖时间
    detector.destroy();

    setTimeout(() => {
      expect(callback).not.toHaveBeenCalled();
    }, 150);
  });
});

describe('pollStrategyResult', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('应该成功获取策略结果', async () => {
    const taskId = 'test-task-123';
    const expectedResult: StrategyResult = {
      totalReturn: 15.5,
      sharpeRatio: 1.8,
      maxDrawdown: -8.2,
      winRate: 65.0,
      totalTrades: 42,
      profitFactor: 1.9,
      volatility: undefined,
      calmarRatio: undefined,
      sortinoRatio: undefined,
      averageTrade: undefined,
      expectancy: undefined,
    };

    mockStrategyAPI.getTaskStatus
      .mockResolvedValueOnce({
        success: true,
        data: { status: 'running' },
      })
      .mockResolvedValue({
        success: true,
        data: { status: 'completed' },
      });

    mockStrategyAPI.getResults.mockResolvedValue({
      success: true,
      data: {
        total_return: 15.5,
        sharpe_ratio: 1.8,
        max_drawdown: -8.2,
        win_rate: 65.0,
        total_trades: 42,
        profit_factor: 1.9,
      },
    });

    const result = await pollStrategyResult(taskId, 2); // 最大尝试2次

    expect(result).toEqual(expectedResult);
    expect(mockStrategyAPI.getTaskStatus).toHaveBeenCalledTimes(2);
    expect(mockStrategyAPI.getResults).toHaveBeenCalledWith(taskId);
  });

  it('应该在策略失败时抛出错误', async () => {
    const taskId = 'test-task-123';

    mockStrategyAPI.getTaskStatus.mockResolvedValue({
      success: true,
      data: {
        status: 'failed',
        error: '策略执行失败',
      },
    });

    await expect(pollStrategyResult(taskId, 1)).rejects.toThrow('策略执行失败: 策略执行失败');
  });

  it('应该在超时时抛出错误', async () => {
    const taskId = 'test-task-123';

    mockStrategyAPI.getTaskStatus.mockResolvedValue({
      success: true,
      data: { status: 'running' },
    });

    await expect(pollStrategyResult(taskId, 1)).rejects.toThrow('策略执行超时');
  });

  it('应该处理API错误', async () => {
    const taskId = 'test-task-123';

    mockStrategyAPI.getTaskStatus.mockRejectedValue(new Error('网络错误'));

    await expect(pollStrategyResult(taskId, 1)).rejects.toThrow('网络错误');
  });
});

describe('transformApiResultToStrategyResult', () => {
  it('应该正确转换API结果', () => {
    const apiData = {
      total_return: 15.5,
      sharpe_ratio: 1.8,
      max_drawdown: -8.2,
      win_rate: 65.0,
      total_trades: 42,
      profit_factor: 1.9,
      volatility: 12.3,
      calmar_ratio: 2.1,
      sortino_ratio: 2.5,
      average_trade: 2.8,
      expectancy: 0.15,
    };

    const result = transformApiResultToStrategyResult(apiData);

    expect(result).toEqual({
      totalReturn: 15.5,
      sharpeRatio: 1.8,
      maxDrawdown: -8.2,
      winRate: 65.0,
      totalTrades: 42,
      profitFactor: 1.9,
      volatility: 12.3,
      calmarRatio: 2.1,
      sortinoRatio: 2.5,
      averageTrade: 2.8,
      expectancy: 0.15,
    });
  });

  it('应该处理缺失的字段', () => {
    const apiData = {
      total_return: 10.0,
      // 缺少其他字段
    };

    const result = transformApiResultToStrategyResult(apiData);

    expect(result).toEqual({
      totalReturn: 10.0,
      sharpeRatio: 0,
      maxDrawdown: 0,
      winRate: 0,
      totalTrades: 0,
      profitFactor: 0,
      volatility: undefined,
      calmarRatio: undefined,
      sortinoRatio: undefined,
      averageTrade: undefined,
      expectancy: undefined,
    });
  });
});

describe('ParameterServicePreloader', () => {
  let preloader: ParameterServicePreloader;
  const mockQueryClient = {
    prefetchQuery: jest.fn(),
    invalidateQueries: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    preloader = new ParameterServicePreloader(mockQueryClient as any);
  });

  it('应该预加载策略结果', async () => {
    const symbol = 'AAPL';
    const params: StrategyParameters = { movingAveragePeriod: 20, stopLoss: 5.0, takeProfit: 10.0 };
    const startDate = '2023-01-01';
    const endDate = '2023-12-31';

    await preloader.preloadStrategyResults(symbol, params, startDate, endDate);

    expect(mockQueryClient.prefetchQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['strategyResults', symbol, params, startDate, endDate],
        queryFn: expect.any(Function),
        staleTime: 30000,
      }),
    );
  });

  it('应该预加载优化建议', async () => {
    const symbol = 'AAPL';
    const params: StrategyParameters = { movingAveragePeriod: 20, stopLoss: 5.0, takeProfit: 10.0 };

    await preloader.preloadOptimizationSuggestions(symbol, params);

    expect(mockQueryClient.prefetchQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['optimizationSuggestions', symbol, params],
        queryFn: expect.any(Function),
        staleTime: 600000,
      }),
    );
  });

  it('应该清除策略缓存', () => {
    preloader.clearStrategyCache('AAPL');

    expect(mockQueryClient.invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['strategyResults', 'AAPL'],
    });
  });

  it('应该清除所有策略缓存', () => {
    preloader.clearStrategyCache();

    expect(mockQueryClient.invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['strategyResults'],
    });
  });
});

describe('DEBOUNCE_CONFIG', () => {
  it('应该导出正确的防抖配置', () => {
    expect(DEBOUNCE_CONFIG.delay).toBe(500);
    expect(DEBOUNCE_CONFIG.maxWait).toBe(2000);
  });
});
