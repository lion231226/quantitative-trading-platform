import {
  StrategySignal,
  StrategyConfig,
  StrategyParams,
  StrategySignalResult,
  SignalDifference,
  SignalCacheItem,
  SignalFilter,
  SignalStatistics,
  SignalComparison,
  IStrategySignalManager,
  StrategyType,
  SignalType,
  SignalStrength,
  TimePeriod,
  StrategySignalUtils,
  PRESET_STRATEGIES
} from '../types/strategySignal.types'
import { KlineData, CandlestickData } from '../types/kline.types'
import { signalRendererService } from './signalRendererService'

// 默认配置
const DEFAULT_CACHE_TTL = 5 * 60 * 1000 // 5分钟
const DEFAULT_MAX_CACHE_SIZE = 50

// 策略信号管理器实现
export class StrategySignalManager implements IStrategySignalManager {
  private cache = new Map<string, SignalCacheItem>()
  private maxCacheSize: number
  private defaultTTL: number

  constructor(maxCacheSize: number = DEFAULT_MAX_CACHE_SIZE, defaultTTL: number = DEFAULT_CACHE_TTL) {
    this.maxCacheSize = maxCacheSize
    this.defaultTTL = defaultTTL

    // 定期清理过期缓存
    setInterval(() => this.cleanupCache(), 60 * 1000)
  }

  /**
   * 加载策略信号
   */
  async loadSignals(strategyId: string, params: StrategyParams,
                   symbol: string, period: TimePeriod, data: KlineData): Promise<StrategySignalResult> {
    const startTime = performance.now()

    try {
      // 检查缓存
      const cacheKey = StrategySignalUtils.generateCacheKey(strategyId, params, symbol, period)
      const cached = this.getCachedSignals(cacheKey)

      if (cached && cached.expiresAt > Date.now()) {
        return {
          ...cached.result,
          performance: {
            ...cached.result.performance,
            cacheHit: true
          }
        }
      }

      // 获取策略配置
      const strategyConfig = this.getStrategyConfig(strategyId)
      if (!strategyConfig) {
        throw new Error(`未找到策略配置: ${strategyId}`)
      }

      // 计算信号
      const signals = await this.calculateSignals(data, strategyConfig, params)

      const result: StrategySignalResult = {
        strategyId,
        signals,
        performance: {
          calculationTime: performance.now() - startTime,
          signalCount: signals.length,
          cacheHit: false
        },
        metadata: {
          generatedAt: Date.now(),
          dataRange: {
            start: data.candlesticks.length > 0 ? new Date(data.candlesticks[0].timestamp).getTime() : 0,
            end: data.candlesticks.length > 0 ? new Date(data.candlesticks[data.candlesticks.length - 1].timestamp).getTime() : 0
          },
          params
        }
      }

      // 缓存结果
      this.setCachedSignals(cacheKey, result, this.defaultTTL)

      return result

    } catch (error) {
      console.error('加载策略信号失败:', error)
      throw error
    }
  }

  /**
   * 更新图表上的信号
   */
  async updateSignals(chartId: string, strategyId: string): Promise<void> {
    try {
      // 获取当前缓存的信号
      const cacheKey = this.generateCacheKey(strategyId, {}, chartId, 'current')
      const cachedItem = this.getCachedSignals(cacheKey)

      if (cachedItem && cachedItem.signals.length > 0) {
        // 调用信号渲染器更新信号
        await signalRendererService.updateMarkers(chartId, cachedItem.signals)
      }
    } catch (error) {
      console.error(`更新图表 ${chartId} 上的策略信号 ${strategyId} 失败:`, error)
      throw error
    }
  }

  /**
   * 移除图表上的信号
   */
  async removeSignals(chartId: string, strategyId: string): Promise<void> {
    try {
      // 调用信号渲染器移除指定策略的信号
      await signalRendererService.removeMarkers(chartId, strategyId)
    } catch (error) {
      console.error(`移除图表 ${chartId} 上的策略信号 ${strategyId} 失败:`, error)
      throw error
    }
  }

  /**
   * 获取缓存的信号
   */
  getCachedSignals(key: string): SignalCacheItem | null {
    const item = this.cache.get(key)
    if (!item || item.expiresAt <= Date.now()) {
      this.cache.delete(key)
      return null
    }
    return item
  }

  /**
   * 设置缓存信号
   */
  setCachedSignals(key: string, result: StrategySignalResult, ttl?: number): void {
    // 检查缓存大小限制
    if (this.cache.size >= this.maxCacheSize) {
      this.evictOldestCache()
    }

    const item: SignalCacheItem = {
      key,
      signals: result.signals,
      result,
      timestamp: Date.now(),
      expiresAt: Date.now() + (ttl || this.defaultTTL)
    }

    this.cache.set(key, item)
  }

  /**
   * 清空缓存
   */
  clearCache(): void {
    this.cache.clear()
  }

  /**
   * 计算信号差异
   */
  calculateDifference(oldSignals: StrategySignal[], newSignals: StrategySignal[]): SignalDifference {
    const oldSignalMap = new Map(oldSignals.map(s => [s.id, s]))
    const newSignalMap = new Map(newSignals.map(s => [s.id, s]))

    const added: StrategySignal[] = []
    const removed: StrategySignal[] = []
    const modified: { old: StrategySignal; new: StrategySignal }[] = []

    // 查找新增和修改的信号
    for (const [id, newSignal] of newSignalMap) {
      const oldSignal = oldSignalMap.get(id)
      if (!oldSignal) {
        added.push(newSignal)
      } else if (this.hasSignalChanged(oldSignal, newSignal)) {
        modified.push({ old: oldSignal, new: newSignal })
      }
    }

    // 查找移除的信号
    for (const [id, oldSignal] of oldSignalMap) {
      if (!newSignalMap.has(id)) {
        removed.push(oldSignal)
      }
    }

    return { added, removed, modified }
  }

  /**
   * 优化信号集合
   */
  optimizeSignals(signals: StrategySignal[], filter?: SignalFilter): StrategySignal[] {
    let filteredSignals = signals

    // 应用过滤条件
    if (filter) {
      filteredSignals = this.applyFilter(signals, filter)
    }

    // 简化的去重逻辑：只移除完全重复的信号（包括ID）
    const seen = new Set<string>()
    const deduplicated = filteredSignals.filter(signal => {
      // 创建完整的信号键（包括所有属性）
      const signalKey = JSON.stringify({
        id: signal.id,
        timestamp: signal.timestamp,
        price: signal.price,
        signalType: signal.signalType,
        strategyId: signal.strategyId,
        confidence: signal.confidence,
        strength: signal.strength
      })

      if (seen.has(signalKey)) {
        return false // 移除完全重复的
      }
      seen.add(signalKey)
      return true
    })

    // 排序
    return deduplicated.sort((a, b) => a.timestamp - b.timestamp)
  }

  /**
   * 获取信号统计信息
   */
  getStatistics(signals: StrategySignal[]): SignalStatistics {
    const signalCounts = {
      buy: 0,
      sell: 0,
      hold: 0,
      stop_loss: 0,
      take_profit: 0
    }

    const strategyCounts: Record<string, number> = {}
    const timeDistribution: Record<number, number> = {}
    const confidenceDistribution = {
      weak: 0,
      moderate: 0,
      strong: 0,
      very_strong: 0
    }

    signals.forEach(signal => {
      // 信号类型统计
      signalCounts[signal.signalType]++

      // 策略统计
      strategyCounts[signal.strategyId] = (strategyCounts[signal.strategyId] || 0) + 1

      // 时间分布（按小时）
      const hour = new Date(signal.timestamp).getHours()
      timeDistribution[hour] = (timeDistribution[hour] || 0) + 1

      // 置信度分布
      if (signal.confidence <= 25) {
        confidenceDistribution.weak++
      } else if (signal.confidence <= 75) {
        confidenceDistribution.moderate++
      } else if (signal.confidence <= 90) {
        confidenceDistribution.strong++
      } else {
        confidenceDistribution.very_strong++
      }
    })

    return {
      totalSignals: signals.length,
      signalCounts,
      strategyCounts,
      timeDistribution,
      confidenceDistribution
    }
  }

  /**
   * 比较两组信号
   */
  compareSignals(signalsA: StrategySignal[], signalsB: StrategySignal[]): SignalComparison {
    const mapA = new Map(signalsA.map(s => [s.id, s]))
    const mapB = new Map(signalsB.map(s => [s.id, s]))

    const common: StrategySignal[] = []
    const uniqueA: StrategySignal[] = []
    const uniqueB: StrategySignal[] = []

    // 找出共同信号和A独有的信号
    for (const [id, signalA] of mapA) {
      const signalB = mapB.get(id)
      if (signalB) {
        common.push(signalA)
      } else {
        uniqueA.push(signalA)
      }
    }

    // 找出B独有的信号
    for (const [id, signalB] of mapB) {
      if (!mapA.has(id)) {
        uniqueB.push(signalB)
      }
    }

    // 计算相关性系数
    const correlation = this.calculateSignalCorrelation(signalsA, signalsB)

    return {
      strategyA: {
        id: 'strategy_a',
        name: 'Strategy A',
        signals: signalsA
      },
      strategyB: {
        id: 'strategy_b',
        name: 'Strategy B',
        signals: signalsB
      },
      common,
      uniqueA,
      uniqueB,
      correlation
    }
  }

  /**
   * 私有方法：获取策略配置
   */
  private getStrategyConfig(strategyId: string): StrategyConfig | null {
    const presetConfig = PRESET_STRATEGIES[strategyId]
    if (!presetConfig) {
      return null
    }

    return {
      id: strategyId,
      ...presetConfig
    }
  }

  /**
   * 私有方法：计算策略信号
   */
  private async calculateSignals(data: KlineData, config: StrategyConfig, params: StrategyParams): Promise<StrategySignal[]> {
    switch (config.type) {
      case 'sma_crossover':
        return this.calculateSMACrossoverSignals(data, config, params)
      case 'ema_crossover':
        return this.calculateEMACrossoverSignals(data, config, params)
      case 'rsi_oversold':
        return this.calculateRSIOversoldSignals(data, config, params)
      case 'rsi_overbought':
        return this.calculateRSIOverboughtSignals(data, config, params)
      case 'macd_crossover':
        return this.calculateMACDCrossoverSignals(data, config, params)
      case 'bollinger_bands':
        return this.calculateBollingerBandsSignals(data, config, params)
      default:
        console.warn(`未实现的策略类型: ${config.type}`)
        return []
    }
  }

  /**
   * 私有方法：SMA金叉死叉策略
   */
  private calculateSMACrossoverSignals(data: KlineData, config: StrategyConfig, params: StrategyParams): StrategySignal[] {
    const { candlesticks } = data
    const shortPeriod = params.shortPeriod || 10
    const longPeriod = params.longPeriod || 30

    if (candlesticks.length < Math.max(shortPeriod, longPeriod)) {
      return []
    }

    const signals: StrategySignal[] = []
    const shortMA = this.calculateSMA(candlesticks, shortPeriod)
    const longMA = this.calculateSMA(candlesticks, longPeriod)

    for (let i = 1; i < shortMA.length; i++) {
      const prevShort = shortMA[i - 1]
      const currShort = shortMA[i]
      const prevLong = longMA[i - 1]
      const currLong = longMA[i]

      // 金叉：短期均线上穿长期均线
      if (prevShort <= prevLong && currShort > currLong) {
        const signal = this.createSignal(
          config,
          candlesticks[i],
          'buy',
          'strong',
          this.calculateGoldenCrossConfidence(currShort, currLong)
        )
        signals.push(signal)
      }
      // 死叉：短期均线下穿长期均线
      else if (prevShort >= prevLong && currShort < currLong) {
        const signal = this.createSignal(
          config,
          candlesticks[i],
          'sell',
          'strong',
          this.calculateDeathCrossConfidence(currShort, currLong)
        )
        signals.push(signal)
      }
    }

    return signals
  }

  /**
   * 私有方法：RSI超卖策略
   */
  private calculateRSIOversoldSignals(data: KlineData, config: StrategyConfig, params: StrategyParams): StrategySignal[] {
    const { candlesticks } = data
    const period = params.period || 14
    const threshold = params.oversoldThreshold || 30

    if (candlesticks.length < period + 1) {
      return []
    }

    const signals: StrategySignal[] = []
    const rsiValues = this.calculateRSI(candlesticks, period)

    for (let i = 0; i < rsiValues.length; i++) {
      const rsi = rsiValues[i]
      const candle = candlesticks[i + period] // 对应的K线数据

      if (rsi < threshold) {
        const confidence = Math.max(0, Math.min(100, (threshold - rsi) * 2))
        const signal = this.createSignal(
          config,
          candle,
          'buy',
          'moderate',
          confidence
        )
        signals.push(signal)
      }
    }

    return signals
  }

  /**
   * 私有方法：创建策略信号
   */
  private createSignal(
    config: StrategyConfig,
    candle: CandlestickData,
    signalType: SignalType,
    strength: SignalStrength,
    confidence: number
  ): StrategySignal {
    const now = Date.now()
    const signalId = StrategySignalUtils.generateSignalId(
      config.id,
      new Date(candle.timestamp).getTime(),
      candle.close
    )

    return {
      id: signalId,
      timestamp: new Date(candle.timestamp).getTime(),
      price: candle.close,
      signalType,
      strength,
      confidence: Math.max(0, Math.min(100, confidence)),
      strategyId: config.id,
      strategyName: config.name,
      strategyType: config.type,
      strategyParams: {},
      volume: candle.volume,
      marketData: {
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close
      },
      metadata: {
        indicator: config.type,
        description: `${config.name} - ${signalType} 信号`
      },
      createdAt: now,
      updatedAt: now
    }
  }

  /**
   * 私有方法：计算简单移动平均线
   */
  private calculateSMA(candlesticks: CandlestickData[], period: number): number[] {
    const sma: number[] = []

    for (let i = period - 1; i < candlesticks.length; i++) {
      let sum = 0
      for (let j = 0; j < period; j++) {
        sum += candlesticks[i - j].close
      }
      sma.push(sum / period)
    }

    return sma
  }

  /**
   * 私有方法：计算RSI
   */
  private calculateRSI(candlesticks: CandlestickData[], period: number): number[] {
    if (candlesticks.length < period + 1) {
      return []
    }

    const gains: number[] = []
    const losses: number[] = []

    for (let i = 1; i < candlesticks.length; i++) {
      const change = candlesticks[i].close - candlesticks[i - 1].close
      gains.push(change > 0 ? change : 0)
      losses.push(change < 0 ? Math.abs(change) : 0)
    }

    const rsi: number[] = []
    let avgGain = gains.slice(0, period).reduce((sum, g) => sum + g, 0) / period
    let avgLoss = losses.slice(0, period).reduce((sum, l) => sum + l, 0) / period

    for (let i = period; i < gains.length; i++) {
      avgGain = (avgGain * (period - 1) + gains[i]) / period
      avgLoss = (avgLoss * (period - 1) + losses[i]) / period

      const rs = avgGain / avgLoss
      const rsiValue = 100 - (100 / (1 + rs))
      rsi.push(rsiValue)
    }

    return rsi
  }

  /**
   * 私有方法：计算金叉置信度
   */
  private calculateGoldenCrossConfidence(shortMA: number, longMA: number): number {
    const ratio = shortMA / longMA
    const diff = (ratio - 1) * 100
    return Math.min(90, Math.max(30, 50 + diff * 5))
  }

  /**
   * 私有方法：计算死叉置信度
   */
  private calculateDeathCrossConfidence(shortMA: number, longMA: number): number {
    const ratio = shortMA / longMA
    const diff = (1 - ratio) * 100
    return Math.min(90, Math.max(30, 50 + diff * 5))
  }

  /**
   * 私有方法：清理过期缓存
   */
  private cleanupCache(): void {
    const now = Date.now()
    for (const [key, item] of this.cache.entries()) {
      if (item.expiresAt <= now) {
        this.cache.delete(key)
      }
    }
  }

  /**
   * 私有方法：淘汰最旧的缓存项
   */
  private evictOldestCache(): void {
    let oldestKey = ''
    let oldestTime = Date.now()

    for (const [key, item] of this.cache.entries()) {
      if (item.timestamp < oldestTime) {
        oldestTime = item.timestamp
        oldestKey = key
      }
    }

    if (oldestKey) {
      this.cache.delete(oldestKey)
    }
  }

  /**
   * 私有方法：检查信号是否发生变化
   */
  private hasSignalChanged(oldSignal: StrategySignal, newSignal: StrategySignal): boolean {
    return (
      oldSignal.signalType !== newSignal.signalType ||
      oldSignal.confidence !== newSignal.confidence ||
      oldSignal.strength !== newSignal.strength ||
      oldSignal.price !== newSignal.price
    )
  }

  /**
   * 私有方法：生成缓存键
   */
  private generateCacheKey(
    strategyType: string,
    params: Record<string, any>,
    symbol: string,
    timePeriod: string
  ): string {
    return `${strategyType}_${symbol}_${timePeriod}_${JSON.stringify(params)}`
  }

  /**
   * 私有方法：应用过滤条件
   */
  private applyFilter(signals: StrategySignal[], filter: SignalFilter): StrategySignal[] {
    return signals.filter(signal => {
      // 信号类型过滤
      if (filter.signalTypes && !filter.signalTypes.includes(signal.signalType)) {
        return false
      }

      // 策略类型过滤
      if (filter.strategyTypes && !filter.strategyTypes.includes(signal.strategyType)) {
        return false
      }

      // 置信度范围过滤
      if (filter.confidenceRange) {
        const { min, max } = filter.confidenceRange
        if (signal.confidence < min || signal.confidence > max) {
          return false
        }
      }

      // 价格范围过滤
      if (filter.priceRange) {
        const { min, max } = filter.priceRange
        if (signal.price < min || signal.price > max) {
          return false
        }
      }

      // 时间范围过滤
      if (filter.timeRange) {
        const { start, end } = filter.timeRange
        if (signal.timestamp < start || signal.timestamp > end) {
          return false
        }
      }

      // 策略ID过滤
      if (filter.strategies && !filter.strategies.includes(signal.strategyId)) {
        return false
      }

      return true
    })
  }

  /**
   * 私有方法：计算信号相关性
   */
  private calculateSignalCorrelation(signalsA: StrategySignal[], signalsB: StrategySignal[]): number {
    const mapA = new Map(signalsA.map(s => [s.id, s]))
    const mapB = new Map(signalsB.map(s => [s.id, s]))

    let commonCount = 0
    for (const [id] of mapA) {
      if (mapB.has(id)) {
        commonCount++
      }
    }

    const maxSignals = Math.max(signalsA.length, signalsB.length)
    if (maxSignals === 0) {
      return 1
    }

    return commonCount / maxSignals
  }

  /**
   * 占位方法：其他策略类型实现
   */
  private calculateEMACrossoverSignals(data: KlineData, config: StrategyConfig, params: StrategyParams): StrategySignal[] {
    // TODO: 实现EMA金叉死叉策略
    return []
  }

  private calculateRSIOverboughtSignals(data: KlineData, config: StrategyConfig, params: StrategyParams): StrategySignal[] {
    // TODO: 实现RSI超买策略
    return []
  }

  private calculateMACDCrossoverSignals(data: KlineData, config: StrategyConfig, params: StrategyParams): StrategySignal[] {
    // TODO: 实现MACD金叉死叉策略
    return []
  }

  private calculateBollingerBandsSignals(data: KlineData, config: StrategyConfig, params: StrategyParams): StrategySignal[] {
    // TODO: 实现布林带策略
    return []
  }
}

// 导出单例实例
export const strategySignalManager = new StrategySignalManager()