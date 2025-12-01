import {
  DEFAULT_SIGNAL_THEMES,
  SignalMarkerStyle,
  SignalType,
  StrategyConfig,
  StrategyParams,
  StrategySignal,
  StrategySignalUtils,
  StrategyType,
} from '../types/strategySignal.types';
import { TimePeriod } from '../types/kline.types';

// 策略参数验证
export class StrategyValidator {
  /**
   * 验证策略参数的有效性
   */
  static validateParams(
    strategyId: string,
    params: StrategyParams,
  ): {
    isValid: boolean;
    errors: string[];
    warnings: string[];
  } {
    const errors: string[] = [];
    const warnings: string[] = [];

    try {
      const presetStrategies = [
        'sma_crossover',
        'ema_crossover',
        'rsi_oversold',
        'rsi_overbought',
        'macd_crossover',
        'bollinger_bands',
      ];

      if (!presetStrategies.includes(strategyId)) {
        // 自定义策略，进行通用验证
        return this.validateCustomParams(params);
      }

      // 根据策略类型进行特定验证
      switch (strategyId as StrategyType) {
        case 'sma_crossover':
        case 'ema_crossover':
          this.validateMACrossParams(params, errors, warnings);
          break;
        case 'rsi_oversold':
        case 'rsi_overbought':
          this.validateRSIParams(params, errors, warnings);
          break;
        case 'macd_crossover':
          this.validateMACDParams(params, errors, warnings);
          break;
        case 'bollinger_bands':
          this.validateBollingerBandsParams(params, errors, warnings);
          break;
      }
    } catch (error) {
      errors.push(
        `参数验证过程中发生错误: ${error instanceof Error ? error.message : '未知错误'}`,
      );
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
    };
  }

  /**
   * 验证移动平均线交叉策略参数
   */
  private static validateMACrossParams(
    params: StrategyParams,
    errors: string[],
    warnings: string[],
  ): void {
    const shortPeriod = params.shortPeriod;
    const longPeriod = params.longPeriod;

    if (
      !shortPeriod ||
      typeof shortPeriod !== 'number' ||
      shortPeriod < 1 ||
      shortPeriod > 200
    ) {
      errors.push('短期均线周期必须是1-200之间的数字');
    }

    if (
      !longPeriod ||
      typeof longPeriod !== 'number' ||
      longPeriod < 1 ||
      longPeriod > 500
    ) {
      errors.push('长期均线周期必须是1-500之间的数字');
    }

    if (shortPeriod && longPeriod && shortPeriod >= longPeriod) {
      errors.push('短期均线周期必须小于长期均线周期');
    }

    if (shortPeriod && longPeriod && longPeriod / shortPeriod > 10) {
      warnings.push('长期均线周期远大于短期均线周期，可能影响策略效果');
    }
  }

  /**
   * 验证RSI策略参数
   */
  private static validateRSIParams(
    params: StrategyParams,
    errors: string[],
    warnings: string[],
  ): void {
    const period = params.period;
    const threshold = params.oversoldThreshold || params.overboughtThreshold;

    if (!period || typeof period !== 'number' || period < 5 || period > 50) {
      errors.push('RSI周期必须是5-50之间的数字');
    }

    if (threshold) {
      if (typeof threshold !== 'number' || threshold < 1 || threshold > 99) {
        errors.push('阈值必须是1-99之间的数字');
      }

      if (threshold > 70 && params.oversoldThreshold) {
        warnings.push('超卖阈值过高，可能产生过多信号');
      }

      if (threshold < 30 && params.overboughtThreshold) {
        warnings.push('超买阈值过低，可能产生过多信号');
      }
    }
  }

  /**
   * 验证MACD策略参数
   */
  private static validateMACDParams(
    params: StrategyParams,
    errors: string[],
    warnings: string[],
  ): void {
    const fastPeriod = params.fastPeriod;
    const slowPeriod = params.slowPeriod;
    const signalPeriod = params.signalPeriod;

    if (
      !fastPeriod ||
      typeof fastPeriod !== 'number' ||
      fastPeriod < 2 ||
      fastPeriod > 50
    ) {
      errors.push('快线周期必须是2-50之间的数字');
    }

    if (
      !slowPeriod ||
      typeof slowPeriod !== 'number' ||
      slowPeriod < 10 ||
      slowPeriod > 200
    ) {
      errors.push('慢线周期必须是10-200之间的数字');
    }

    if (
      !signalPeriod ||
      typeof signalPeriod !== 'number' ||
      signalPeriod < 2 ||
      signalPeriod > 50
    ) {
      errors.push('信号线周期必须是2-50之间的数字');
    }

    if (fastPeriod && slowPeriod && fastPeriod >= slowPeriod) {
      errors.push('快线周期必须小于慢线周期');
    }
  }

  /**
   * 验证布林带策略参数
   */
  private static validateBollingerBandsParams(
    params: StrategyParams,
    errors: string[],
    warnings: string[],
  ): void {
    const period = params.period;
    const stdDev = params.stdDev;

    if (!period || typeof period !== 'number' || period < 5 || period > 100) {
      errors.push('布林带周期必须是5-100之间的数字');
    }

    if (!stdDev || typeof stdDev !== 'number' || stdDev < 0.5 || stdDev > 5) {
      errors.push('标准差倍数必须是0.5-5之间的数字');
    }

    if (stdDev && stdDev > 3) {
      warnings.push('标准差倍数较大，可能产生较少的交易信号');
    }
  }

  /**
   * 验证自定义策略参数
   */
  private static validateCustomParams(params: StrategyParams): {
    isValid: boolean;
    errors: string[];
    warnings: string[];
  } {
    const errors: string[] = [];
    const warnings: string[] = [];

    if (
      !params ||
      typeof params !== 'object' ||
      Object.keys(params).length === 0
    ) {
      errors.push('自定义策略参数不能为空');
    }

    // 通用参数验证
    for (const [key, value] of Object.entries(params)) {
      if (typeof value === 'number') {
        if (isNaN(value) || !isFinite(value)) {
          errors.push(`参数 ${key} 必须是有效的数字`);
        }
        if (value < 0 && key.toLowerCase().includes('period')) {
          errors.push(`周期参数 ${key} 必须为正数`);
        }
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
    };
  }
}

// 策略性能分析器
export class StrategyPerformanceAnalyzer {
  /**
   * 计算策略收益率
   */
  static calculateReturn(
    signals: StrategySignal[],
    initialCapital: number = 10000,
  ): {
    totalReturn: number;
    returnRate: number;
    maxDrawdown: number;
    sharpeRatio: number;
    winRate: number;
    profitFactor: number;
  } {
    if (signals.length === 0) {
      return {
        totalReturn: 0,
        returnRate: 0,
        maxDrawdown: 0,
        sharpeRatio: 0,
        winRate: 0,
        profitFactor: 0,
      };
    }

    const trades = this.simulateTrades(signals, initialCapital);
    const returns = trades.map((trade) => trade.profit / trade.entryPrice);

    // 计算总收益率
    const totalReturn = trades.reduce((sum, trade) => sum + trade.profit, 0);
    const returnRate = (totalReturn / initialCapital) * 100;

    // 计算最大回撤
    let maxDrawdown = 0;
    let peak = initialCapital;
    let currentCapital = initialCapital;

    for (const trade of trades) {
      currentCapital += trade.profit;
      if (currentCapital > peak) {
        peak = currentCapital;
      }
      const drawdown = ((peak - currentCapital) / peak) * 100;
      maxDrawdown = Math.max(maxDrawdown, drawdown);
    }

    // 计算夏普比率（简化版）
    const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;
    const variance =
      returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) /
      returns.length;
    const stdDev = Math.sqrt(variance);
    const sharpeRatio = stdDev > 0 ? (avgReturn / stdDev) * Math.sqrt(252) : 0; // 年化夏普比率

    // 计算胜率
    const winningTrades = trades.filter((trade) => trade.profit > 0);
    const winRate = (winningTrades.length / trades.length) * 100;

    // 计算盈利因子
    const totalProfit = winningTrades.reduce(
      (sum, trade) => sum + trade.profit,
      0,
    );
    const totalLoss = Math.abs(
      trades
        .filter((trade) => trade.profit < 0)
        .reduce((sum, trade) => sum + trade.profit, 0),
    );
    const profitFactor = totalLoss > 0 ? totalProfit / totalLoss : 0;

    return {
      totalReturn,
      returnRate,
      maxDrawdown,
      sharpeRatio,
      winRate,
      profitFactor,
    };
  }

  /**
   * 模拟交易
   */
  private static simulateTrades(
    signals: StrategySignal[],
    initialCapital: number,
  ): Array<{
    entryPrice: number;
    exitPrice: number;
    profit: number;
    entryTime: number;
    exitTime: number;
  }> {
    const trades: any[] = [];
    let position = null; // { type: 'buy' | 'sell', price: number, time: number }

    for (const signal of signals.sort((a, b) => a.timestamp - b.timestamp)) {
      if (signal.signalType === 'buy' && !position) {
        // 开多仓
        position = {
          type: 'buy',
          price: signal.price,
          time: signal.timestamp,
        };
      } else if (
        signal.signalType === 'sell' &&
        position &&
        position.type === 'buy'
      ) {
        // 平多仓
        trades.push({
          entryPrice: position.price,
          exitPrice: signal.price,
          profit: signal.price - position.price,
          entryTime: position.time,
          exitTime: signal.timestamp,
        });
        position = null;
      }
    }

    // 如果还有未平仓的持仓，按最后价格平仓
    if (position && signals.length > 0) {
      const lastSignal = signals[signals.length - 1];
      trades.push({
        entryPrice: position.price,
        exitPrice: lastSignal.price,
        profit: lastSignal.price - position.price,
        entryTime: position.time,
        exitTime: lastSignal.timestamp,
      });
    }

    return trades;
  }

  /**
   * 生成性能报告
   */
  static generatePerformanceReport(
    strategyId: string,
    signals: StrategySignal[],
    initialCapital: number = 10000,
  ): {
    strategyId: string;
    totalSignals: number;
    signalsByType: Record<SignalType, number>;
    performance: ReturnType<typeof StrategyPerformanceAnalyzer.calculateReturn>;
    recommendations: string[];
  } {
    const signalsByType = {
      buy: signals.filter((s) => s.signalType === 'buy').length,
      sell: signals.filter((s) => s.signalType === 'sell').length,
      hold: signals.filter((s) => s.signalType === 'hold').length,
      stop_loss: signals.filter((s) => s.signalType === 'stop_loss').length,
      take_profit: signals.filter((s) => s.signalType === 'take_profit').length,
    };

    const performance = this.calculateReturn(signals, initialCapital);
    const recommendations = this.generateRecommendations(
      performance,
      signalsByType,
    );

    return {
      strategyId,
      totalSignals: signals.length,
      signalsByType,
      performance,
      recommendations,
    };
  }

  /**
   * 生成优化建议
   */
  private static generateRecommendations(
    performance: ReturnType<typeof StrategyPerformanceAnalyzer.calculateReturn>,
    signalsByType: Record<SignalType, number>,
  ): string[] {
    const recommendations: string[] = [];

    // 基于收益率的建议
    if (performance.returnRate < 0) {
      recommendations.push('策略收益率为负，建议调整参数或考虑其他策略');
    } else if (performance.returnRate < 5) {
      recommendations.push('策略收益率较低，可以考虑优化入场条件');
    }

    // 基于最大回撤的建议
    if (performance.maxDrawdown > 20) {
      recommendations.push('最大回撤过大，建议加强风险管理');
    }

    // 基于胜率的建议
    if (performance.winRate < 40) {
      recommendations.push('胜率较低，建议优化信号生成逻辑');
    }

    // 基于夏普比率的建议
    if (performance.sharpeRatio < 1) {
      recommendations.push('夏普比率较低，策略风险调整后收益不佳');
    }

    // 基于信号频率的建议
    const totalSignals = Object.values(signalsByType).reduce(
      (sum, count) => sum + count,
      0,
    );
    if (totalSignals > 100) {
      recommendations.push('信号频率较高，注意交易成本的影响');
    } else if (totalSignals < 10) {
      recommendations.push('信号频率较低，可能错过较多交易机会');
    }

    // 基于买卖信号平衡的建议
    const buySellRatio = signalsByType.buy / (signalsByType.sell || 1);
    if (buySellRatio > 2 || buySellRatio < 0.5) {
      recommendations.push('买卖信号不平衡，建议检查策略逻辑');
    }

    return recommendations;
  }
}

// 样式工具类
export class StyleManager {
  /**
   * 生成策略特定样式
   */
  static generateStrategyStyle(
    strategyType: StrategyType,
    theme: 'light' | 'dark' = 'light',
  ): Record<SignalType, SignalMarkerStyle> {
    const baseTheme = DEFAULT_SIGNAL_THEMES[theme];

    // 根据策略类型调整样式
    const strategySpecificStyles = this.getStrategySpecificStyles(
      strategyType,
      theme,
    );

    return {
      buy: { ...baseTheme.buy, ...strategySpecificStyles.buy },
      sell: { ...baseTheme.sell, ...strategySpecificStyles.sell },
      hold: { ...baseTheme.hold, ...strategySpecificStyles.hold },
      stop_loss: strategySpecificStyles.stop_loss || baseTheme.hold,
      take_profit: strategySpecificStyles.take_profit || baseTheme.buy,
    };
  }

  /**
   * 获取策略特定样式
   */
  private static getStrategySpecificStyles(
    strategyType: StrategyType,
    theme: 'light' | 'dark',
  ): Partial<Record<SignalType, SignalMarkerStyle>> {
    const styles: Partial<Record<SignalType, SignalMarkerStyle>> = {};

    switch (strategyType) {
      case 'sma_crossover':
      case 'ema_crossover':
        styles.buy = {
          shape: 'arrow_up',
          color: theme === 'light' ? '#10b981' : '#34d399',
          size: 12,
          opacity: 0.9,
          border: {
            color: theme === 'light' ? '#059669' : '#047857',
            width: 2,
          },
        };
        styles.sell = {
          shape: 'arrow_down',
          color: theme === 'light' ? '#ef4444' : '#f87171',
          size: 12,
          opacity: 0.9,
          border: {
            color: theme === 'light' ? '#dc2626' : '#b91c1c',
            width: 2,
          },
        };
        break;

      case 'rsi_oversold':
      case 'rsi_overbought':
        styles.buy = {
          shape: 'circle',
          color: theme === 'light' ? '#3b82f6' : '#60a5fa',
          size: 10,
          opacity: 0.8,
          border: {
            color: theme === 'light' ? '#1d4ed8' : '#2563eb',
            width: 2,
          },
        };
        styles.sell = {
          shape: 'square',
          color: theme === 'light' ? '#f59e0b' : '#fbbf24',
          size: 10,
          opacity: 0.8,
          border: {
            color: theme === 'light' ? '#d97706' : '#f59e0b',
            width: 2,
          },
        };
        break;

      case 'macd_crossover':
        styles.buy = {
          shape: 'triangle',
          color: theme === 'light' ? '#8b5cf6' : '#a78bfa',
          size: 11,
          opacity: 0.85,
          border: {
            color: theme === 'light' ? '#7c3aed' : '#8b5cf6',
            width: 2,
          },
        };
        styles.sell = {
          shape: 'triangle',
          color: theme === 'light' ? '#ec4899' : '#f472b6',
          size: 11,
          opacity: 0.85,
          border: {
            color: theme === 'light' ? '#db2777' : '#ec4899',
            width: 2,
          },
        };
        break;

      case 'bollinger_bands':
        styles.buy = {
          shape: 'diamond',
          color: theme === 'light' ? '#06b6d4' : '#22d3ee',
          size: 9,
          opacity: 0.8,
          border: {
            color: theme === 'light' ? '#0891b2' : '#06b6d4',
            width: 2,
          },
        };
        styles.sell = {
          shape: 'diamond',
          color: theme === 'light' ? '#84cc16' : '#a3e635',
          size: 9,
          opacity: 0.8,
          border: {
            color: theme === 'light' ? '#65a30d' : '#84cc16',
            width: 2,
          },
        };
        break;

      default:
        // 使用默认样式
        break;
    }

    return styles;
  }

  /**
   * 根据置信度调整样式
   */
  static adjustStyleByConfidence(
    baseStyle: SignalMarkerStyle,
    confidence: number,
  ): SignalMarkerStyle {
    const adjustedStyle = { ...baseStyle };

    // 根据置信度调整透明度
    adjustedStyle.opacity = Math.max(0.3, Math.min(1, confidence / 100));

    // 根据置信度调整大小
    const sizeMultiplier = 0.8 + (confidence / 100) * 0.4; // 0.8-1.2倍
    adjustedStyle.size = Math.round(baseStyle.size * sizeMultiplier);

    return adjustedStyle;
  }

  /**
   * 获取信号标签文本
   */
  static getSignalLabelText(
    signal: StrategySignal,
    includeStrategy: boolean = false,
  ): string {
    let label = StrategySignalUtils.formatSignalLabel(signal);

    if (includeStrategy) {
      label = `${signal.strategyName}\n${label}`;
    }

    return label;
  }

  /**
   * 生成对比样式
   */
  static generateComparisonStyle(
    baseStyle: SignalMarkerStyle,
    index: number,
    total: number,
  ): SignalMarkerStyle {
    const comparisonStyle = { ...baseStyle };

    // 根据在对比中的位置调整颜色
    const hueShift = (360 / total) * index;
    comparisonStyle.color = this.adjustHue(baseStyle.color, hueShift);

    // 调整大小以区分
    const sizeMultiplier = 0.9 + (index / total) * 0.2;
    comparisonStyle.size = Math.round(baseStyle.size * sizeMultiplier);

    return comparisonStyle;
  }

  /**
   * 调整色相
   */
  private static adjustHue(color: string, degrees: number): string {
    // 简化的色相调整实现
    // 在实际项目中，可能需要更复杂的颜色处理库
    return color; // 占位实现
  }
}

// 时间工具类
export class TimeUtils {
  /**
   * 格式化时间戳
   */
  static formatTimestamp(
    timestamp: number,
    format: 'date' | 'datetime' | 'time' = 'datetime',
  ): string {
    const date = new Date(timestamp);

    switch (format) {
      case 'date':
        return date.toLocaleDateString();
      case 'time':
        return date.toLocaleTimeString();
      case 'datetime':
      default:
        return date.toLocaleString();
    }
  }

  /**
   * 计算时间间隔
   */
  static getTimeInterval(
    startTime: number,
    endTime: number,
  ): {
    days: number;
    hours: number;
    minutes: number;
    totalHours: number;
  } {
    const diffMs = endTime - startTime;
    const diffHours = diffMs / (1000 * 60 * 60);

    const days = Math.floor(diffHours / 24);
    const hours = Math.floor(diffHours % 24);
    const minutes = Math.floor((diffHours * 60) % 60);

    return {
      days,
      hours,
      minutes,
      totalHours: diffHours,
    };
  }

  /**
   * 获取市场开市时间
   */
  static isMarketOpen(timestamp: number): boolean {
    const date = new Date(timestamp);
    const day = date.getDay();
    const hour = date.getHours();

    // 周末不开市
    if (day === 0 || day === 6) {
      return false;
    }

    // 简化的开市时间判断（9:30-16:00）
    return hour >= 9 && hour < 16;
  }

  /**
   * 对齐到交易周期
   */
  static alignToTradingPeriod(timestamp: number, period: TimePeriod): number {
    const date = new Date(timestamp);

    switch (period) {
      case '1m':
        date.setSeconds(0, 0);
        break;
      case '5m':
        date.setSeconds(0, 0);
        date.setMinutes(Math.floor(date.getMinutes() / 5) * 5);
        break;
      case '15m':
        date.setSeconds(0, 0);
        date.setMinutes(Math.floor(date.getMinutes() / 15) * 15);
        break;
      case '1h':
        date.setSeconds(0, 0);
        date.setMinutes(0);
        break;
      case '1d':
        date.setHours(0, 0, 0, 0);
        break;
      default:
        // 其他周期保持原样
        break;
    }

    return date.getTime();
  }
}
