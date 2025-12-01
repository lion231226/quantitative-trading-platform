import {
  CandlestickData,
  DataValidationResult,
  KlineCacheConfig,
  KlineData,
  TimePeriod,
} from '../types/kline.types';
import { PricePoint } from '../types/chart.types';
import {
  SignalDifference,
  SignalFilter,
  StrategyConfig,
  StrategyParams,
  StrategySignal,
  StrategySignalResult,
  StrategyType,
  strategySignalManager,
} from '../types/strategySignal.types';

// 默认配置
const DEFAULT_CACHE_CONFIG: KlineCacheConfig = {
  enabled: true,
  maxAge: 5 * 60 * 1000, // 5分钟
  maxSize: 100,
  storage: 'memory',
};

// 数据验证器
export class KlineDataValidator {
  /**
   * 验证K线图数据的完整性和有效性
   */
  static validate(data: KlineData): DataValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    if (!data || !data.candlesticks) {
      errors.push('K线数据不能为空');
      return {
        isValid: false,
        errors,
        warnings,
        dataPoints: 0,
        dateRange: { start: '', end: '' },
      };
    }

    const { candlesticks, signals, movingAverages } = data;
    const dataPoints = candlesticks.length;

    // 检查数据点数量
    if (dataPoints === 0) {
      errors.push('至少需要一条K线数据');
    } else if (dataPoints > 50000) {
      warnings.push('数据点数量过多，可能影响性能');
    }

    // 验证每条K线数据
    for (let i = 0; i < candlesticks.length; i++) {
      const candle = candlesticks[i];

      // 检查必填字段
      if (!candle.timestamp) {
        errors.push(`第${i + 1}条K线缺少时间戳`);
      }

      if (typeof candle.open !== 'number' || candle.open <= 0) {
        errors.push(`第${i + 1}条K线开盘价无效`);
      }

      if (typeof candle.high !== 'number' || candle.high <= 0) {
        errors.push(`第${i + 1}条K线最高价无效`);
      }

      if (typeof candle.low !== 'number' || candle.low <= 0) {
        errors.push(`第${i + 1}条K线最低价无效`);
      }

      if (typeof candle.close !== 'number' || candle.close <= 0) {
        errors.push(`第${i + 1}条K线收盘价无效`);
      }

      if (typeof candle.volume !== 'number' || candle.volume < 0) {
        errors.push(`第${i + 1}条K线成交量无效`);
      }

      // 检查价格逻辑
      if (candle.high < candle.low) {
        errors.push(`第${i + 1}条K线最高价不能低于最低价`);
      }

      if (candle.high < candle.open || candle.high < candle.close) {
        errors.push(`第${i + 1}条K线最高价不能低于开盘价和收盘价`);
      }

      if (candle.low > candle.open || candle.low > candle.close) {
        errors.push(`第${i + 1}条K线最低价不能高于开盘价和收盘价`);
      }
    }

    // 检查时间序列是否递增
    for (let i = 1; i < candlesticks.length; i++) {
      const prevTime = new Date(candlesticks[i - 1].timestamp).getTime();
      const currTime = new Date(candlesticks[i].timestamp).getTime();

      if (currTime <= prevTime) {
        errors.push('K线时间序列必须递增');
        break;
      }
    }

    // 检查信号数据
    if (signals) {
      for (let i = 0; i < signals.length; i++) {
        const signal = signals[i];

        if (!signal.timestamp) {
          errors.push(`第${i + 1}个信号缺少时间戳`);
        }

        if (!['buy', 'sell'].includes(signal.type)) {
          errors.push(`第${i + 1}个信号类型无效`);
        }

        if (typeof signal.price !== 'number' || signal.price <= 0) {
          errors.push(`第${i + 1}个信号价格无效`);
        }
      }
    }

    // 计算日期范围
    const dateRange = {
      start: candlesticks.length > 0 ? candlesticks[0].timestamp : '',
      end:
        candlesticks.length > 0
          ? candlesticks[candlesticks.length - 1].timestamp
          : '',
    };

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      dataPoints,
      dateRange,
    };
  }
}

// 数据缓存管理器
export class KlineDataCache {
  private cache = new Map<string, { data: KlineData; timestamp: number }>();
  private config: KlineCacheConfig;

  constructor(config: Partial<KlineCacheConfig> = {}) {
    this.config = { ...DEFAULT_CACHE_CONFIG, ...config };

    // 定期清理过期缓存
    setInterval(() => this.cleanup(), 60 * 1000); // 每分钟清理一次
  }

  /**
   * 生成缓存键
   */
  private generateKey(symbol: string, period: TimePeriod): string {
    return `${symbol}_${period}`;
  }

  /**
   * 存储数据到缓存
   */
  set(symbol: string, period: TimePeriod, data: KlineData): void {
    if (!this.config.enabled) return;

    const key = this.generateKey(symbol, period);
    const timestamp = Date.now();

    // 检查缓存大小限制
    if (this.cache.size >= this.config.maxSize) {
      // 删除最旧的缓存项
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
    }

    this.cache.set(key, { data, timestamp });
  }

  /**
   * 从缓存获取数据
   */
  get(symbol: string, period: TimePeriod): KlineData | null {
    if (!this.config.enabled) return null;

    const key = this.generateKey(symbol, period);
    const cached = this.cache.get(key);

    if (!cached) return null;

    // 检查是否过期
    if (Date.now() - cached.timestamp > this.config.maxAge) {
      this.cache.delete(key);
      return null;
    }

    return cached.data;
  }

  /**
   * 清理过期缓存
   */
  private cleanup(): void {
    const now = Date.now();

    for (const [key, cached] of this.cache.entries()) {
      if (now - cached.timestamp > this.config.maxAge) {
        this.cache.delete(key);
      }
    }
  }

  /**
   * 清空缓存
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * 获取缓存统计信息
   */
  getStats(): { size: number; keys: string[] } {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys()),
    };
  }
}

// 时间周期数据聚合器
export class TimePeriodAggregator {
  /**
   * 将数据聚合到不同时间周期
   */
  static aggregate(
    data: CandlestickData[],
    fromPeriod: TimePeriod,
    toPeriod: TimePeriod,
  ): CandlestickData[] {
    if (fromPeriod === toPeriod || data.length === 0) {
      return data;
    }

    const fromMinutes = this.getPeriodMinutes(fromPeriod);
    const toMinutes = this.getPeriodMinutes(toPeriod);

    if (toMinutes <= fromMinutes) {
      return data;
    }

    const ratio = Math.floor(toMinutes / fromMinutes);
    const result: CandlestickData[] = [];

    for (let i = 0; i < data.length; i += ratio) {
      const chunk = data.slice(i, i + ratio);
      if (chunk.length === 0) continue;

      const aggregated = this.aggregateChunk(chunk);
      result.push(aggregated);
    }

    return result;
  }

  /**
   * 获取时间周期对应的分钟数
   */
  private static getPeriodMinutes(period: TimePeriod): number {
    const periodMap: Record<TimePeriod, number> = {
      [TimePeriod.MINUTE_1]: 1,
      [TimePeriod.MINUTE_5]: 5,
      [TimePeriod.MINUTE_15]: 15,
      [TimePeriod.MINUTE_30]: 30,
      [TimePeriod.HOUR_1]: 60,
      [TimePeriod.HOUR_4]: 240,
      [TimePeriod.DAY_1]: 1440,
      [TimePeriod.DAY_7]: 10080,
      [TimePeriod.MONTH_1]: 43200, // 约等于30天
    };

    return periodMap[period] || 60;
  }

  /**
   * 聚合数据块
   */
  private static aggregateChunk(chunk: CandlestickData[]): CandlestickData {
    const first = chunk[0];
    const last = chunk[chunk.length - 1];

    const open = first.open;
    const close = last.close;
    const high = Math.max(...chunk.map((c) => c.high));
    const low = Math.min(...chunk.map((c) => c.low));
    const volume = chunk.reduce((sum, c) => sum + c.volume, 0);

    return {
      timestamp: last.timestamp, // 使用最后一个时间点作为聚合后的时间
      open,
      high,
      low,
      close,
      volume,
    };
  }
}

// 数据采样器
export class KlineDataSampler {
  /**
   * 智能数据采样，保持关键特征点
   */
  static sample(
    data: CandlestickData[],
    maxPoints: number,
    preserveExtremes: boolean = true,
  ): CandlestickData[] {
    if (data.length <= maxPoints) {
      return data;
    }

    if (preserveExtremes && data.length > 3) {
      return this.preserveImportantPoints(data, maxPoints);
    } else {
      return this.uniformSampling(data, maxPoints);
    }
  }

  /**
   * 保持重要点的采样
   */
  private static preserveImportantPoints(
    data: CandlestickData[],
    maxPoints: number,
  ): CandlestickData[] {
    // 始终保留第一个和最后一个数据点
    const result: CandlestickData[] = [data[0], data[data.length - 1]];
    const remainingPoints = maxPoints - 2;

    if (remainingPoints <= 0) {
      return result;
    }

    // 找到重要的转折点（局部高点和低点）
    const importantPoints: CandlestickData[] = [];

    for (let i = 1; i < data.length - 1; i++) {
      const prev = data[i - 1];
      const curr = data[i];
      const next = data[i + 1];

      // 检测局部高点
      if (curr.high > prev.high && curr.high > next.high) {
        importantPoints.push(curr);
      }
      // 检测局部低点
      else if (curr.low < prev.low && curr.low < next.low) {
        importantPoints.push(curr);
      }
    }

    // 如果重要点数量不够，用均匀采样补充
    if (importantPoints.length < remainingPoints) {
      const uniformStep = Math.floor(
        data.length / (remainingPoints - importantPoints.length),
      );
      for (let i = 0; i < data.length; i += uniformStep) {
        if (!result.includes(data[i]) && !importantPoints.includes(data[i])) {
          importantPoints.push(data[i]);
        }
      }
    }

    // 选择最重要的点
    const selected = this.selectTopPoints(importantPoints, remainingPoints);

    // 合并所有选中的点并排序
    const allPoints = [...result, ...selected].sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    );

    return allPoints;
  }

  /**
   * 均匀采样
   */
  private static uniformSampling(
    data: CandlestickData[],
    maxPoints: number,
  ): CandlestickData[] {
    const step = Math.ceil(data.length / maxPoints);
    const result: CandlestickData[] = [];

    for (let i = 0; i < data.length; i += step) {
      result.push(data[i]);
    }

    return result;
  }

  /**
   * 选择最重要的点
   */
  private static selectTopPoints(
    points: CandlestickData[],
    count: number,
  ): CandlestickData[] {
    if (points.length <= count) {
      return points;
    }

    // 按照价格变化幅度排序，选择变化最大的点
    const sorted = points.sort((a, b) => {
      const rangeA = a.high - a.low;
      const rangeB = b.high - b.low;
      return rangeB - rangeA;
    });

    return sorted.slice(0, count);
  }
}

// 扩展K线数据服务主类，集成策略信号管理
export class KlineDataService {
  private cache: KlineDataCache;
  private activeStrategies: Map<string, StrategyParams> = new Map();
  private lastSignalResults: Map<string, StrategySignalResult> = new Map();

  constructor(cacheConfig?: Partial<KlineCacheConfig>) {
    this.cache = new KlineDataCache(cacheConfig);
  }

  /**
   * 获取K线数据（带缓存）
   */
  async getData(
    symbol: string,
    period: TimePeriod,
    fromCache: boolean = true,
  ): Promise<KlineData | null> {
    // 尝试从缓存获取
    if (fromCache) {
      const cached = this.cache.get(symbol, period);
      if (cached) {
        return cached;
      }
    }

    try {
      // TODO: 实际的数据获取逻辑，这里只是示例
      const data = await this.fetchFromAPI(symbol, period);

      if (data) {
        // 验证数据
        const validation = KlineDataValidator.validate(data);
        if (!validation.isValid) {
          console.error('K线数据验证失败:', validation.errors);
          return null;
        }

        // 存储到缓存
        this.cache.set(symbol, period, data);

        return data;
      }

      return null;
    } catch (error) {
      console.error('获取K线数据失败:', error);
      return null;
    }
  }

  /**
   * 从API获取数据（示例实现）
   */
  private async fetchFromAPI(
    symbol: string,
    period: TimePeriod,
  ): Promise<KlineData | null> {
    // TODO: 实现真实的API调用
    // 这里返回模拟数据作为示例
    return {
      candlesticks: this.generateMockData(100),
    };
  }

  /**
   * 生成模拟数据（仅用于测试）
   */
  private generateMockData(count: number): CandlestickData[] {
    const data: CandlestickData[] = [];
    const now = new Date();
    let lastClose = 100;

    for (let i = count - 1; i >= 0; i--) {
      const timestamp = new Date(
        now.getTime() - i * 24 * 60 * 60 * 1000,
      ).toISOString();

      // 生成随机价格
      const change = (Math.random() - 0.5) * 10;
      const open = lastClose + change;
      const close = open + (Math.random() - 0.5) * 5;
      const high = Math.max(open, close) + Math.random() * 3;
      const low = Math.min(open, close) - Math.random() * 3;
      const volume = Math.floor(Math.random() * 1000000);

      data.push({
        timestamp,
        open: Math.max(1, open),
        high: Math.max(1, high),
        low: Math.max(1, low),
        close: Math.max(1, close),
        volume,
      });

      lastClose = close;
    }

    return data;
  }

  /**
   * 转换价格数据为K线数据
   */
  static convertFromPricePoints(pricePoints: PricePoint[]): CandlestickData[] {
    return pricePoints.map((point) => ({
      ...point,
      volume: 0, // 默认成交量设为0
    }));
  }

  /**
   * 获取缓存统计
   */
  getCacheStats() {
    return this.cache.getStats();
  }

  /**
   * 清空缓存
   */
  clearCache() {
    this.cache.clear();
  }

  // ========== 策略信号管理功能 ==========

  /**
   * 激活策略
   */
  async activateStrategy(
    strategyId: string,
    params: StrategyParams,
  ): Promise<void> {
    this.activeStrategies.set(strategyId, params);
    console.log(`策略 ${strategyId} 已激活，参数:`, params);
  }

  /**
   * 停用策略
   */
  deactivateStrategy(strategyId: string): void {
    this.activeStrategies.delete(strategyId);
    this.lastSignalResults.delete(strategyId);
    console.log(`策略 ${strategyId} 已停用`);
  }

  /**
   * 获取所有激活的策略
   */
  getActiveStrategies(): Map<string, StrategyParams> {
    return new Map(this.activeStrategies);
  }

  /**
   * 获取K线数据并计算策略信号
   */
  async getDataWithSignals(
    symbol: string,
    period: TimePeriod,
    strategyFilter?: string[],
    fromCache: boolean = true,
  ): Promise<{
    data: KlineData;
    signals: Map<string, StrategySignalResult>;
  } | null> {
    // 获取K线数据
    const data = await this.getData(symbol, period, fromCache);
    if (!data) {
      return null;
    }

    const signals = new Map<string, StrategySignalResult>();

    // 为每个激活的策略计算信号
    for (const [strategyId, params] of this.activeStrategies) {
      // 如果指定了策略过滤器，只处理指定的策略
      if (strategyFilter && !strategyFilter.includes(strategyId)) {
        continue;
      }

      try {
        const signalResult = await strategySignalManager.loadSignals(
          strategyId,
          params,
          symbol,
          period,
          data,
        );
        signals.set(strategyId, signalResult);
        this.lastSignalResults.set(strategyId, signalResult);
      } catch (error) {
        console.error(`策略 ${strategyId} 信号计算失败:`, error);
      }
    }

    return { data, signals };
  }

  /**
   * 更新策略参数并重新计算信号
   */
  async updateStrategyParams(
    strategyId: string,
    newParams: StrategyParams,
    symbol: string,
    period: TimePeriod,
  ): Promise<SignalDifference | null> {
    const oldResult = this.lastSignalResults.get(strategyId);
    if (!oldResult) {
      return null;
    }

    // 更新策略参数
    this.activeStrategies.set(strategyId, newParams);

    // 重新计算信号
    const newData = await this.getData(symbol, period, true);
    if (!newData) {
      return null;
    }

    const newResult = await strategySignalManager.loadSignals(
      strategyId,
      newParams,
      symbol,
      period,
      newData,
    );
    this.lastSignalResults.set(strategyId, newResult);

    // 计算差异
    return strategySignalManager.calculateDifference(
      oldResult.signals,
      newResult.signals,
    );
  }

  /**
   * 获取策略信号差异
   */
  async getSignalDifference(
    strategyId: string,
    symbol: string,
    period: TimePeriod,
  ): Promise<SignalDifference | null> {
    const oldResult = this.lastSignalResults.get(strategyId);
    if (!oldResult) {
      return null;
    }

    // 重新获取最新数据并计算信号
    const newData = await this.getData(symbol, period, false); // 不使用缓存以获取最新数据
    if (!newData) {
      return null;
    }

    const params = this.activeStrategies.get(strategyId);
    if (!params) {
      return null;
    }

    const newResult = await strategySignalManager.loadSignals(
      strategyId,
      params,
      symbol,
      period,
      newData,
    );
    this.lastSignalResults.set(strategyId, newResult);

    return strategySignalManager.calculateDifference(
      oldResult.signals,
      newResult.signals,
    );
  }

  /**
   * 过滤策略信号
   */
  filterSignals(strategyId: string, filter: SignalFilter): StrategySignal[] {
    const result = this.lastSignalResults.get(strategyId);
    if (!result) {
      return [];
    }

    return strategySignalManager.optimizeSignals(result.signals, filter);
  }

  /**
   * 获取策略信号统计
   */
  getSignalStatistics(strategyId?: string): Map<string, any> {
    const statistics = new Map<string, any>();

    if (strategyId) {
      // 获取指定策略的统计
      const result = this.lastSignalResults.get(strategyId);
      if (result) {
        statistics.set(
          strategyId,
          strategySignalManager.getStatistics(result.signals),
        );
      }
    } else {
      // 获取所有策略的统计
      for (const [id, result] of this.lastSignalResults) {
        statistics.set(id, strategySignalManager.getStatistics(result.signals));
      }
    }

    return statistics;
  }

  /**
   * 比较两个策略的信号
   */
  compareStrategies(strategyAId: string, strategyBId: string): any {
    const resultA = this.lastSignalResults.get(strategyAId);
    const resultB = this.lastSignalResults.get(strategyBId);

    if (!resultA || !resultB) {
      return null;
    }

    return strategySignalManager.compareSignals(
      resultA.signals,
      resultB.signals,
    );
  }

  /**
   * 获取最近的信号
   */
  getRecentSignals(strategyId: string, count: number = 10): StrategySignal[] {
    const result = this.lastSignalResults.get(strategyId);
    if (!result) {
      return [];
    }

    return result.signals
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, count);
  }

  /**
   * 获取指定时间范围内的信号
   */
  getSignalsByTimeRange(
    strategyId: string,
    startTime: number,
    endTime: number,
  ): StrategySignal[] {
    const result = this.lastSignalResults.get(strategyId);
    if (!result) {
      return [];
    }

    return result.signals.filter(
      (signal) => signal.timestamp >= startTime && signal.timestamp <= endTime,
    );
  }

  /**
   * 清理策略缓存
   */
  clearStrategyCache(strategyId?: string): void {
    if (strategyId) {
      this.lastSignalResults.delete(strategyId);
      strategySignalManager.clearCache();
    } else {
      this.lastSignalResults.clear();
      strategySignalManager.clearCache();
    }
  }

  /**
   * 获取策略性能指标
   */
  getStrategyPerformance(strategyId: string): {
    totalSignals: number;
    calculationTime: number;
    cacheHitRate: number;
    lastUpdated: number;
  } | null {
    const result = this.lastSignalResults.get(strategyId);
    if (!result) {
      return null;
    }

    return {
      totalSignals: result.signals.length,
      calculationTime: result.performance.calculationTime,
      cacheHitRate: result.performance.cacheHit ? 1 : 0, // 简化版本，实际应该跟踪历史
      lastUpdated: result.metadata.generatedAt,
    };
  }

  /**
   * 批量更新多个策略
   */
  async batchUpdateStrategies(
    strategyUpdates: Array<{ strategyId: string; params: StrategyParams }>,
    symbol: string,
    period: TimePeriod,
  ): Promise<Map<string, SignalDifference>> {
    const differences = new Map<string, SignalDifference>();

    for (const { strategyId, params } of strategyUpdates) {
      try {
        const diff = await this.updateStrategyParams(
          strategyId,
          params,
          symbol,
          period,
        );
        if (diff) {
          differences.set(strategyId, diff);
        }
      } catch (error) {
        console.error(`批量更新策略 ${strategyId} 失败:`, error);
      }
    }

    return differences;
  }
}

// 导出单例实例
export const klineDataService = new KlineDataService();
