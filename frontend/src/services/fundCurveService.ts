import {
  FundCurveData,
  FundCurveDataPoint,
  PerformanceMetrics,
  TradingSignal,
} from '../types/kline.types';

/**
 * 资金曲线计算服务
 * 提供资金曲线计算、性能指标分析和基准比较功能
 */
export class FundCurveService {
  private static instance: FundCurveService;
  private cache = new Map<string, { data: FundCurveData; timestamp: number }>();
  private readonly CACHE_DURATION = 5 * 60 * 1000; // 5分钟缓存

  private constructor() {}

  /**
   * 获取服务实例（单例模式）
   */
  static getInstance(): FundCurveService {
    if (!FundCurveService.instance) {
      FundCurveService.instance = new FundCurveService();
    }
    return FundCurveService.instance;
  }

  /**
   * 根据交易信号计算资金曲线
   */
  calculateFundCurve(
    signals: TradingSignal[],
    initialCapital: number = 100000,
    positionSize: number = 1,
  ): FundCurveDataPoint[] {
    if (signals.length === 0) return [];

    // 按时间排序
    const sortedSignals = signals.sort((a, b) => a.timestamp - b.timestamp);

    const dataPoints: FundCurveDataPoint[] = [];
    let currentCapital = initialCapital;
    let currentPosition = 0;
    let entryPrice = 0;
    let totalShares = 0;

    sortedSignals.forEach((signal, index) => {
      const price = signal.price;
      const timestamp = signal.timestamp;

      // 更新投资组合价值
      const portfolioValue = currentCapital + currentPosition * price;

      // 记录数据点
      dataPoints.push({
        timestamp,
        value: portfolioValue,
      });

      // 处理交易信号
      if (signal.signalType === 'buy' && currentPosition === 0) {
        // 买入
        const sharesToBuy = Math.floor((currentCapital / price) * positionSize);
        const cost = sharesToBuy * price;
        currentCapital -= cost;
        currentPosition = sharesToBuy;
        entryPrice = price;
        totalShares += sharesToBuy;
      } else if (signal.signalType === 'sell' && currentPosition > 0) {
        // 卖出
        const proceeds = currentPosition * price;
        currentCapital += proceeds;
        currentPosition = 0;
      }
    });

    return dataPoints;
  }

  /**
   * 计算买入持有基准曲线
   */
  calculateBuyAndHoldBaseline(
    initialPrice: number,
    prices: Array<{ timestamp: number; price: number }>,
    initialCapital: number = 100000,
  ): FundCurveDataPoint[] {
    if (prices.length === 0) return [];

    const shares = Math.floor(initialCapital / initialPrice);
    return prices.map(({ timestamp, price }) => ({
      timestamp,
      value: shares * price,
    }));
  }

  /**
   * 计算性能指标
   */
  calculateMetrics(data: FundCurveDataPoint[]): PerformanceMetrics {
    if (data.length < 2) {
      return this.getEmptyMetrics();
    }

    const values = data.map((d) => d.value);
    const firstValue = values[0];
    const lastValue = values[values.length - 1];

    // 基础指标
    const totalReturn = (lastValue - firstValue) / firstValue;
    const returnRate = totalReturn * 100;
    const totalReturnPercent = totalReturn * 100;

    // 最大回撤
    let maxDrawdown = 0;
    let peak = values[0];
    for (let i = 1; i < values.length; i++) {
      if (values[i] > peak) {
        peak = values[i];
      }
      const drawdown = (peak - values[i]) / peak;
      if (drawdown > maxDrawdown) {
        maxDrawdown = drawdown;
      }
    }
    maxDrawdown *= 100;

    // 收益率序列（用于计算波动率）
    const returns = [];
    for (let i = 1; i < values.length; i++) {
      returns.push((values[i] - values[i - 1]) / values[i - 1]);
    }

    // 年化收益率和波动率
    const dataPoints = values.length;
    const annualizedReturn = Math.pow(1 + totalReturn, 252 / dataPoints) - 1;
    const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
    const variance =
      returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) /
      returns.length;
    const volatility = Math.sqrt(variance) * Math.sqrt(252) * 100;

    // 夏普比率（假设无风险利率为2%）
    const riskFreeRate = 0.02;
    const excessReturn = annualizedReturn - riskFreeRate;
    const sharpeRatio =
      volatility !== 0 ? (excessReturn * 100) / volatility : 0;

    return {
      returnRate,
      maxDrawdown,
      sharpeRatio,
      totalReturn: totalReturnPercent,
      annualizedReturn: annualizedReturn * 100,
      volatility,
      winRate: 0, // 需要更详细的交易数据
      profitFactor: 0, // 需要盈亏比数据
      maxConsecutiveWins: 0,
      maxConsecutiveLosses: 0,
    };
  }

  /**
   * 计算相对性能指标（相对于基准）
   */
  calculateRelativeMetrics(
    strategyMetrics: PerformanceMetrics,
    baselineMetrics: PerformanceMetrics,
  ): {
    alpha: number; // Alpha值
    beta: number; // Beta值
    informationRatio: number; // 信息比率
    trackingError: number; // 跟踪误差
  } {
    // 简化的Alpha计算
    const alpha = strategyMetrics.returnRate - baselineMetrics.returnRate;

    // 简化的Beta计算（基于波动率比率）
    const beta =
      baselineMetrics.volatility !== 0
        ? strategyMetrics.volatility / baselineMetrics.volatility
        : 1;

    // 信息比率
    const trackingError = Math.abs(
      strategyMetrics.volatility - baselineMetrics.volatility,
    );
    const informationRatio =
      trackingError !== 0
        ? (strategyMetrics.returnRate - baselineMetrics.returnRate) /
          trackingError
        : 0;

    return {
      alpha,
      beta,
      informationRatio,
      trackingError,
    };
  }

  /**
   * 缓存资金曲线数据
   */
  cacheFundCurve(key: string, data: FundCurveData): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    });
  }

  /**
   * 获取缓存的资金曲线数据
   */
  getCachedFundCurve(key: string): FundCurveData | null {
    const cached = this.cache.get(key);
    if (!cached) return null;

    // 检查缓存是否过期
    if (Date.now() - cached.timestamp > this.CACHE_DURATION) {
      this.cache.delete(key);
      return null;
    }

    return cached.data;
  }

  /**
   * 清除缓存
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * 生成资金曲线缓存键
   */
  generateCacheKey(
    signals: TradingSignal[],
    initialCapital: number,
    positionSize: number,
  ): string {
    // 使用信号的哈希值生成缓存键
    const signalHash = this.hashSignals(signals);
    return `${signalHash}_${initialCapital}_${positionSize}`;
  }

  /**
   * 创建标准化的资金曲线数据
   */
  createFundCurveData(
    id: string,
    name: string,
    dataPoints: FundCurveDataPoint[],
    color: string,
    curveType: 'strategy' | 'baseline' | 'benchmark' = 'strategy',
  ): FundCurveData {
    return {
      id,
      name,
      data: dataPoints,
      color,
      curveType,
      visible: true,
      lineWidth: curveType === 'baseline' ? 1 : 2,
      lineType: curveType === 'baseline' ? 'dashed' : 'solid',
    };
  }

  /**
   * 合并多个资金曲线数据点（时间对齐）
   */
  alignDataPoints(
    curves: FundCurveData[],
  ): Array<{ timestamp: number; values: Record<string, number> }> {
    if (curves.length === 0) return [];

    // 收集所有时间戳
    const allTimestamps = new Set<number>();
    curves.forEach((curve) => {
      curve.data.forEach((point) => allTimestamps.add(point.timestamp));
    });

    // 排序时间戳
    const sortedTimestamps = Array.from(allTimestamps).sort((a, b) => a - b);

    // 为每个时间戳收集各曲线的值
    return sortedTimestamps.map((timestamp) => {
      const values: Record<string, number> = {};
      curves.forEach((curve) => {
        const point = curve.data.find((p) => p.timestamp === timestamp);
        if (point) {
          values[curve.id] = point.value;
        }
      });
      return { timestamp, values };
    });
  }

  /**
   * 私有方法：计算信号哈希值
   */
  private hashSignals(signals: TradingSignal[]): string {
    const signalString = signals
      .map((s) => `${s.timestamp}_${s.signalType}_${s.price}`)
      .join('|');
    return btoa(signalString).slice(0, 16);
  }

  /**
   * 私有方法：获取空的性能指标
   */
  private getEmptyMetrics(): PerformanceMetrics {
    return {
      returnRate: 0,
      maxDrawdown: 0,
      sharpeRatio: 0,
      totalReturn: 0,
      annualizedReturn: 0,
      volatility: 0,
      winRate: 0,
      profitFactor: 0,
      maxConsecutiveWins: 0,
      maxConsecutiveLosses: 0,
    };
  }
}

// 导出服务实例
export const fundCurveService = FundCurveService.getInstance();
export default fundCurveService;
