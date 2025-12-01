import {
  CandlestickData,
  KlineConfig,
  LightweightChartConfig,
  TimePeriod,
} from '../types/kline.types';
import { ChartTheme } from '../types/chart.types';
import { MarketColors } from '../types/theme.types';

/**
 * 从主题颜色创建K线图配置
 */
export const createKlineConfigFromTheme = (
  themeColors: MarketColors,
  overrides?: Partial<KlineConfig>,
): KlineConfig => {
  return {
    // 基础配置
    height: 400,
    timePeriod: TimePeriod.DAY_1,

    // 显示配置
    showVolume: true,
    showSignals: true,
    showMovingAverages: true,
    showGrid: true,
    showCrosshair: false,

    // 颜色配置 - 使用主题颜色
    colors: {
      bullish: themeColors.bullish, // 涨颜色
      bearish: themeColors.bearish, // 跌颜色
      volume: themeColors.volume, // 成交量颜色
      grid: themeColors.grid, // 网格颜色
      text: themeColors.text, // 文字颜色
      background: themeColors.background, // 背景颜色
      crosshair: themeColors.border, // 十字线颜色
    },

    // 移动平均线配置
    movingAverages: {
      sma: [20, 50], // 20日和50日SMA
      ema: [12, 26], // 12日和26日EMA
      colors: ['#2196f3', '#ff9800', '#9c27b0', '#00bcd4'], // 移动平均线颜色
    },

    // 交互配置
    interactions: {
      enableZoom: true,
      enablePan: true,
      enableScroll: true,
      wheelSensitivity: 1,
      keyboardShortcuts: true,
    },

    // 性能配置
    performance: {
      enableDataSampling: true,
      maxDataPoints: 1000,
      enableAnimation: true,
      animationDuration: 300,
    },

    ...overrides,
  };
};

/**
 * 创建默认K线图配置
 */
export const createDefaultKlineConfig = (
  overrides?: Partial<KlineConfig>,
): KlineConfig => {
  return {
    // 基础配置
    height: 400,
    timePeriod: TimePeriod.DAY_1,

    // 显示配置
    showVolume: true,
    showSignals: true,
    showMovingAverages: true,
    showGrid: true,
    showCrosshair: false,

    // 颜色配置
    colors: {
      bullish: '#26a69a', // 绿色上涨
      bearish: '#ef5350', // 红色下跌
      volume: '#9e9e9e', // 灰色成交量
      grid: '#e0e0e0', // 浅灰网格
      text: '#424242', // 深灰文字
      background: '#ffffff', // 白色背景
      crosshair: '#757575', // 中灰十字线
    },

    // 移动平均线配置
    movingAverages: {
      sma: [20, 50], // 20日和50日SMA
      ema: [12, 26], // 12日和26日EMA
      colors: ['#2196f3', '#ff9800', '#9c27b0', '#00bcd4'], // 移动平均线颜色
    },

    // 交互配置
    interactions: {
      enableZoom: true,
      enablePan: true,
      enableScroll: true,
      wheelSensitivity: 1,
      keyboardShortcuts: true,
    },

    // 性能配置
    performance: {
      enableDataSampling: true,
      maxDataPoints: 1000,
      enableAnimation: true,
      animationDuration: 300,
    },

    ...overrides,
  };
};

/**
 * 创建Lightweight Charts配置
 */
export const createLightweightChartConfig = (
  klineConfig: KlineConfig,
  width: number,
  height: number,
): LightweightChartConfig => {
  return {
    width,
    height,
    layout: {
      background: {
        type: 'solid',
        color: klineConfig.colors.background,
      },
      textColor: klineConfig.colors.text,
    },
    grid: {
      vertLines: {
        visible: klineConfig.showGrid,
        color: klineConfig.colors.grid,
      },
      horzLines: {
        visible: klineConfig.showGrid,
        color: klineConfig.colors.grid,
      },
    },
    crosshair: {
      mode: klineConfig.showCrosshair ? 'normal' : 'hidden',
      vertLine: {
        width: 1,
        color: klineConfig.colors.crosshair,
        style: 'dashed',
      },
      horzLine: {
        width: 1,
        color: klineConfig.colors.crosshair,
        style: 'dashed',
      },
    },
    rightPriceScale: {
      visible: true,
      borderColor: klineConfig.colors.grid,
      textColor: klineConfig.colors.text,
    },
    timeScale: {
      borderColor: klineConfig.colors.grid,
      textColor: klineConfig.colors.text,
      timeVisible: true,
      secondsVisible: false,
    },
    watermark: {
      visible: false,
      color: 'rgba(0, 0, 0, 0.1)',
      fontSize: 24,
      horzAlign: 'center',
      vertAlign: 'middle',
    },
  };
};

/**
 * 将K线数据转换为Lightweight Charts格式
 */
export const convertToLightweightChartsData = (
  klineData: CandlestickData[],
) => {
  return klineData.map((candle) => ({
    time: new Date(candle.timestamp).getTime() / 1000, // 转换为秒时间戳
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
  }));
};

/**
 * 将成交量数据转换为Lightweight Charts格式
 */
export const convertVolumeData = (klineData: CandlestickData[]) => {
  return klineData.map((candle) => ({
    time: new Date(candle.timestamp).getTime() / 1000,
    value: candle.volume,
    color: candle.close >= candle.open ? '#26a69a' : '#ef5350',
  }));
};

/**
 * 格式化时间显示
 */
export const formatTimeDisplay = (
  timestamp: number,
  timePeriod: TimePeriod,
): string => {
  const date = new Date(timestamp * 1000); // 从秒时间戳转换

  switch (timePeriod) {
    case TimePeriod.MINUTE_1:
    case TimePeriod.MINUTE_5:
    case TimePeriod.MINUTE_15:
    case TimePeriod.MINUTE_30:
      return date.toLocaleString('zh-CN', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });

    case TimePeriod.HOUR_1:
    case TimePeriod.HOUR_4:
      return date.toLocaleString('zh-CN', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
      });

    case TimePeriod.DAY_1:
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });

    case TimePeriod.DAY_7:
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });

    case TimePeriod.MONTH_1:
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: 'short',
      });

    default:
      return date.toLocaleString();
  }
};

/**
 * 格式化价格显示
 */
export const formatPriceDisplay = (
  price: number,
  decimals: number = 2,
): string => {
  return price.toFixed(decimals);
};

/**
 * 格式化成交量显示
 */
export const formatVolumeDisplay = (volume: number): string => {
  if (volume >= 1e9) {
    return `${(volume / 1e9).toFixed(2)}B`;
  } else if (volume >= 1e6) {
    return `${(volume / 1e6).toFixed(2)}M`;
  } else if (volume >= 1e3) {
    return `${(volume / 1e3).toFixed(2)}K`;
  } else {
    return volume.toString();
  }
};

/**
 * 计算价格变化百分比
 */
export const calculatePriceChange = (
  current: number,
  previous: number,
): number => {
  if (previous === 0) return 0;
  return ((current - previous) / previous) * 100;
};

/**
 * 获取价格变化颜色
 */
export const getPriceChangeColor = (
  change: number,
  config: KlineConfig,
): string => {
  return change >= 0 ? config.colors.bullish : config.colors.bearish;
};

/**
 * 计算数据统计信息
 */
export const calculateDataStatistics = (data: CandlestickData[]) => {
  if (data.length === 0) {
    return {
      count: 0,
      avgVolume: 0,
      maxPrice: 0,
      minPrice: 0,
      priceRange: 0,
      totalVolume: 0,
    };
  }

  const prices = data.flatMap((d) => [d.open, d.high, d.low, d.close]);
  const volumes = data.map((d) => d.volume);

  return {
    count: data.length,
    avgVolume: volumes.reduce((sum, v) => sum + v, 0) / volumes.length,
    maxPrice: Math.max(...prices),
    minPrice: Math.min(...prices),
    priceRange: Math.max(...prices) - Math.min(...prices),
    totalVolume: volumes.reduce((sum, v) => sum + v, 0),
  };
};

/**
 * 验证时间周期是否有效
 */
export const isValidTimePeriod = (period: string): period is TimePeriod => {
  return Object.values(TimePeriod).includes(period as TimePeriod);
};

/**
 * 获取时间周期显示名称
 */
export const getTimePeriodDisplayName = (period: TimePeriod): string => {
  const names: Record<TimePeriod, string> = {
    [TimePeriod.MINUTE_1]: '1分钟',
    [TimePeriod.MINUTE_5]: '5分钟',
    [TimePeriod.MINUTE_15]: '15分钟',
    [TimePeriod.MINUTE_30]: '30分钟',
    [TimePeriod.HOUR_1]: '1小时',
    [TimePeriod.HOUR_4]: '4小时',
    [TimePeriod.DAY_1]: '日线',
    [TimePeriod.DAY_7]: '周线',
    [TimePeriod.MONTH_1]: '月线',
  };

  return names[period] || period;
};

/**
 * 检测数据完整性
 */
export const detectDataGaps = (
  data: CandlestickData[],
  period: TimePeriod,
): string[] => {
  const gaps: string[] = [];

  if (data.length < 2) return gaps;

  const periodMinutes = getPeriodMinutes(period);

  for (let i = 1; i < data.length; i++) {
    const prevTime = new Date(data[i - 1].timestamp).getTime();
    const currTime = new Date(data[i].timestamp).getTime();
    const diffMinutes = (currTime - prevTime) / (1000 * 60);

    // 如果时间间隔超过周期时间的1.5倍，认为存在数据缺口
    if (diffMinutes > periodMinutes * 1.5) {
      gaps.push(`${data[i - 1].timestamp} - ${data[i].timestamp}`);
    }
  }

  return gaps;
};

/**
 * 获取时间周期对应的分钟数
 */
export const getPeriodMinutes = (period: TimePeriod): number => {
  const periodMap: Record<TimePeriod, number> = {
    [TimePeriod.MINUTE_1]: 1,
    [TimePeriod.MINUTE_5]: 5,
    [TimePeriod.MINUTE_15]: 15,
    [TimePeriod.MINUTE_30]: 30,
    [TimePeriod.HOUR_1]: 60,
    [TimePeriod.HOUR_4]: 240,
    [TimePeriod.DAY_1]: 1440,
    [TimePeriod.DAY_7]: 10080,
    [TimePeriod.MONTH_1]: 43200,
  };

  return periodMap[period] || 60;
};

/**
 * 防抖函数
 */
export const debounce = <T extends (...args: any[]) => void>(
  func: T,
  delay: number,
): ((...args: Parameters<T>) => void) => {
  let timeoutId: NodeJS.Timeout;

  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
};

/**
 * 节流函数
 */
export const throttle = <T extends (...args: any[]) => void>(
  func: T,
  delay: number,
): ((...args: Parameters<T>) => void) => {
  let lastCall = 0;

  return (...args: Parameters<T>) => {
    const now = Date.now();
    if (now - lastCall >= delay) {
      lastCall = now;
      func(...args);
    }
  };
};

/**
 * 性能基准测试结果类型
 */
export interface PerformanceBenchmarkResult {
  chartLibrary: 'Chart.js' | 'Lightweight Charts';
  dataPoints: number;
  renderTime: number;
  memoryUsage: number;
  fps: number;
  timestamp: string;
}

/**
 * 性能基准测试工具
 */
export class PerformanceBenchmarkUtil {
  private startTime: number = 0;
  private endTime: number = 0;
  private memoryBefore: number = 0;
  private memoryAfter: number = 0;

  /**
   * 开始基准测试
   */
  start(): void {
    this.startTime = performance.now();
    this.memoryBefore = this.getMemoryUsage();
  }

  /**
   * 结束基准测试
   */
  end(): number {
    this.endTime = performance.now();
    this.memoryAfter = this.getMemoryUsage();
    return this.getRenderTime();
  }

  /**
   * 获取渲染时间
   */
  getRenderTime(): number {
    return this.endTime - this.startTime;
  }

  /**
   * 获取内存使用量变化
   */
  getMemoryDelta(): number {
    return this.memoryAfter - this.memoryBefore;
  }

  /**
   * 获取当前内存使用量
   */
  private getMemoryUsage(): number {
    if (performance.memory) {
      return performance.memory.usedJSHeapSize;
    }
    return 0;
  }

  /**
   * 创建基准测试结果
   */
  createResult(
    chartLibrary: 'Chart.js' | 'Lightweight Charts',
    dataPoints: number,
  ) {
    return {
      chartLibrary,
      dataPoints,
      renderTime: this.getRenderTime(),
      memoryUsage: this.getMemoryDelta(),
      fps: 1000 / this.getRenderTime(), // 简单FPS计算
      timestamp: new Date().toISOString(),
    };
  }
}

/**
 * 计算移动平均线
 */
export const calculateSMA = (data: number[], period: number): number[] => {
  const result: number[] = [];

  for (let i = period - 1; i < data.length; i++) {
    const sum = data.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
    result.push(sum / period);
  }

  return result;
};

/**
 * 计算指数移动平均线
 */
export const calculateEMA = (data: number[], period: number): number[] => {
  const result: number[] = [];
  const multiplier = 2 / (period + 1);

  // 第一个EMA值使用SMA
  const firstSMA = data.slice(0, period).reduce((a, b) => a + b, 0) / period;
  result.push(firstSMA);

  // 计算后续EMA值
  for (let i = period; i < data.length; i++) {
    const ema =
      (data[i] - result[result.length - 1]) * multiplier +
      result[result.length - 1];
    result.push(ema);
  }

  return result;
};

/**
 * 为K线数据添加移动平均线
 */
export const addMovingAveragesToData = (
  candlestickData: CandlestickData[],
  smaPeriods: number[] = [],
  emaPeriods: number[] = [],
) => {
  const closePrices = candlestickData.map((candle) => candle.close);
  const movingAverages: any = {};

  // 计算SMA
  smaPeriods.forEach((period) => {
    const sma = calculateSMA(closePrices, period);
    movingAverages[`sma_${period}`] = sma.map((value, index) => ({
      timestamp: candlestickData[index + period - 1].timestamp,
      value,
      period,
      type: 'SMA',
    }));
  });

  // 计算EMA
  emaPeriods.forEach((period) => {
    const ema = calculateEMA(closePrices, period);
    movingAverages[`ema_${period}`] = ema.map((value, index) => ({
      timestamp: candlestickData[index].timestamp,
      value,
      period,
      type: 'EMA',
    }));
  });

  return movingAverages;
};

/**
 * 数据采样器类 - 用于大数据集的性能优化
 */
export class KlineDataSampler {
  /**
   * 对K线数据进行采样以减少渲染负担
   * @param data 原始K线数据
   * @param maxPoints 最大数据点数
   * @param preserveImportant 是否保留重要数据点（如最高点、最低点）
   */
  static sample(
    data: CandlestickData[],
    maxPoints: number,
    preserveImportant: boolean = true,
  ): CandlestickData[] {
    if (data.length <= maxPoints) {
      return data;
    }

    if (!preserveImportant) {
      // 简单均匀采样
      const step = Math.ceil(data.length / maxPoints);
      return data.filter((_, index) => index % step === 0);
    }

    // 智能采样 - 保留重要数据点
    return this.intelligentSample(data, maxPoints);
  }

  /**
   * 智能采样算法 - 保留重要的价格转折点
   */
  private static intelligentSample(
    data: CandlestickData[],
    maxPoints: number,
  ): CandlestickData[] {
    if (data.length <= maxPoints) {
      return data;
    }

    // 计算采样步长
    const step = Math.floor(data.length / maxPoints);
    const result: CandlestickData[] = [];

    // 保留第一个数据点
    result.push(data[0]);

    for (let i = step; i < data.length - step; i += step) {
      const chunk = data.slice(
        Math.max(0, i - step),
        Math.min(data.length, i + step),
      );

      if (chunk.length > 0) {
        // 在每个chunk中找到最重要的数据点
        const importantPoint = this.findMostImportantPoint(chunk);
        result.push(importantPoint);
      }
    }

    // 保留最后一个数据点
    if (data.length > 1) {
      result.push(data[data.length - 1]);
    }

    // 如果结果仍然超过最大点数，进行均匀采样
    if (result.length > maxPoints) {
      const finalStep = Math.ceil(result.length / maxPoints);
      return result.filter((_, index) => index % finalStep === 0);
    }

    return result;
  }

  /**
   * 在数据块中找到最重要的数据点
   * 重要点判断标准：价格变化幅度大的点
   */
  private static findMostImportantPoint(
    chunk: CandlestickData[],
  ): CandlestickData {
    if (chunk.length === 1) {
      return chunk[0];
    }

    // 计算每个点的价格变化幅度
    let maxImportance = 0;
    let mostImportantPoint = chunk[0];

    for (let i = 0; i < chunk.length; i++) {
      const point = chunk[i];

      // 计算价格变化幅度（最高价-最低价）
      const priceRange = point.high - point.low;

      // 计算与开盘价的变化幅度
      const openChange = Math.abs(point.close - point.open);

      // 综合重要性评分
      const importance = priceRange + openChange;

      // 如果是chunk的第一个或最后一个点，增加权重
      const positionWeight = i === 0 || i === chunk.length - 1 ? 0.2 : 0;
      const finalImportance = importance + positionWeight;

      if (finalImportance > maxImportance) {
        maxImportance = finalImportance;
        mostImportantPoint = point;
      }
    }

    return mostImportantPoint;
  }

  /**
   * 计算采样统计信息
   */
  static getSamplingStats(
    originalData: CandlestickData[],
    sampledData: CandlestickData[],
  ) {
    return {
      originalCount: originalData.length,
      sampledCount: sampledData.length,
      reductionRatio: (
        ((originalData.length - sampledData.length) / originalData.length) *
        100
      ).toFixed(1),
      preservationRate: (
        (sampledData.length / originalData.length) *
        100
      ).toFixed(1),
    };
  }
}
