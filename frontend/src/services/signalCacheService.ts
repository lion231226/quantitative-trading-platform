import {
  StrategySignal,
  StrategySignalResult,
  SignalDifference,
  SignalCacheItem,
  StrategyParams,
  TimePeriod,
  StrategySignalUtils,
  StrategyType
} from '../types/strategySignal.types'

// 缓存配置接口
export interface CacheConfig {
  maxEntries: number
  defaultTTL: number // 毫秒
  enableCompression: boolean
  cleanupInterval: number
}

// 默认缓存配置
const DEFAULT_CACHE_CONFIG: CacheConfig = {
  maxEntries: 100,
  defaultTTL: 10 * 60 * 1000, // 10分钟
  enableCompression: false,
  cleanupInterval: 60 * 1000 // 1分钟
}

// 缓存键类型
export type CacheKeyType =
  | 'strategy_signals'    // 策略信号缓存
  | 'market_data'        // 市场数据缓存
  | 'calculation_result' // 计算结果缓存
  | 'comparison_data'    // 对比数据缓存

// 扩展的缓存项
export interface ExtendedCacheItem extends SignalCacheItem {
  keyType: CacheKeyType
  accessCount: number
  lastAccessed: number
  compressed?: boolean
  metadata?: {
    [key: string]: any
  }
}

// 策略差异检测结果
export interface StrategyChangeDetection {
  strategyId: string
  oldParams: StrategyParams
  newParams: StrategyParams
  hasChanged: boolean
  changeTypes: ('parameter_added' | 'parameter_removed' | 'parameter_modified')[]
  criticalChanges: string[] // 影响信号的参数变化
}

// 信号更新策略
export enum UpdateStrategy {
  IMMEDIATE = 'immediate',    // 立即更新
  BATCHED = 'batched',        // 批量更新
  LAZY = 'lazy',             // 延迟更新
  INCREMENTAL = 'incremental' // 增量更新
}

// 高级信号缓存服务
export class SignalCacheService {
  private cache = new Map<string, ExtendedCacheItem>()
  private config: CacheConfig
  private cleanupTimer?: NodeJS.Timeout
  private accessStats = new Map<string, { count: number; lastAccess: number }>()

  constructor(config: Partial<CacheConfig> = {}) {
    this.config = { ...DEFAULT_CACHE_CONFIG, ...config }
    this.startCleanupTimer()
  }

  /**
   * 生成缓存键
   */
  generateCacheKey(
    keyType: CacheKeyType,
    strategyId: string,
    params: StrategyParams,
    symbol: string,
    period: TimePeriod
  ): string {
    const paramString = this.serializeParams(params)
    return `${keyType}:${strategyId}:${symbol}:${period}:${paramString}`
  }

  /**
   * 存储策略信号结果
   */
  setSignals(
    strategyId: string,
    params: StrategyParams,
    symbol: string,
    period: TimePeriod,
    result: StrategySignalResult,
    ttl?: number
  ): void {
    const key = this.generateCacheKey('strategy_signals', strategyId, params, symbol, period)
    this.setCacheItem(key, {
      keyType: 'strategy_signals',
      key,
      signals: result.signals,
      result,
      timestamp: Date.now(),
      expiresAt: Date.now() + (ttl || this.config.defaultTTL),
      accessCount: 1,
      lastAccessed: Date.now(),
      metadata: {
        strategyId,
        symbol,
        period,
        paramHash: this.hashParams(params)
      }
    })
  }

  /**
   * 获取策略信号结果
   */
  getSignals(
    strategyId: string,
    params: StrategyParams,
    symbol: string,
    period: TimePeriod
  ): StrategySignalResult | null {
    const key = this.generateCacheKey('strategy_signals', strategyId, params, symbol, period)
    const item = this.getCacheItem(key)

    if (!item) {
      return null
    }

    // 更新访问统计
    this.updateAccessStats(key)
    return item.result
  }

  /**
   * 检测策略参数变化
   */
  detectParameterChanges(
    strategyId: string,
    oldParams: StrategyParams,
    newParams: StrategyParams
  ): StrategyChangeDetection {
    const oldKeys = new Set(Object.keys(oldParams))
    const newKeys = new Set(Object.keys(newParams))

    const changeTypes: StrategyChangeDetection['changeTypes'] = []
    const criticalChanges: string[] = []

    // 检测新增参数
    for (const key of newKeys) {
      if (!oldKeys.has(key)) {
        changeTypes.push('parameter_added')
        if (this.isCriticalParameter(strategyId, key)) {
          criticalChanges.push(key)
        }
      }
    }

    // 检测删除参数
    for (const key of oldKeys) {
      if (!newKeys.has(key)) {
        changeTypes.push('parameter_removed')
        if (this.isCriticalParameter(strategyId, key)) {
          criticalChanges.push(key)
        }
      }
    }

    // 检测修改参数
    for (const key of oldKeys) {
      if (newKeys.has(key) && oldParams[key] !== newParams[key]) {
        changeTypes.push('parameter_modified')
        if (this.isCriticalParameter(strategyId, key)) {
          criticalChanges.push(key)
        }
      }
    }

    return {
      strategyId,
      oldParams,
      newParams,
      hasChanged: changeTypes.length > 0,
      changeTypes,
      criticalChanges
    }
  }

  /**
   * 计算信号差异（智能版本）
   */
  calculateSignalDifference(
    strategyId: string,
    oldParams: StrategyParams,
    newParams: StrategyParams,
    symbol: string,
    period: TimePeriod
  ): SignalDifference | null {
    const oldResult = this.getSignals(strategyId, oldParams, symbol, period)
    const newResult = this.getSignals(strategyId, newParams, symbol, period)

    if (!oldResult || !newResult) {
      return null
    }

    return this.calculateDifference(oldResult.signals, newResult.signals)
  }

  /**
   * 增量更新信号（基于参数变化）
   */
  async incrementalUpdate(
    strategyId: string,
    oldParams: StrategyParams,
    newParams: StrategyParams,
    symbol: string,
    period: TimePeriod,
    computeNewSignals: (params: StrategyParams) => Promise<StrategySignalResult>
  ): Promise<SignalDifference> {
    // 检测参数变化
    const changes = this.detectParameterChanges(strategyId, oldParams, newParams)

    // 如果没有关键参数变化，可以进行增量更新
    if (changes.criticalChanges.length === 0) {
      // 尝试智能增量更新
      const incrementalDiff = await this.performIncrementalUpdate(
        strategyId, oldParams, newParams, symbol, period, computeNewSignals
      )

      if (incrementalDiff) {
        return incrementalDiff
      }
    }

    // 回退到完全重新计算
    const oldResult = this.getSignals(strategyId, oldParams, symbol, period)
    const newResult = await computeNewSignals(newParams)

    // 缓存新结果
    this.setSignals(strategyId, newParams, symbol, period, newResult)

    return oldResult ?
      this.calculateDifference(oldResult.signals, newResult.signals) :
      { added: newResult.signals, removed: [], modified: [] }
  }

  /**
   * 批量获取多个策略的信号
   */
  getMultipleSignals(
    requests: Array<{
      strategyId: string
      params: StrategyParams
      symbol: string
      period: TimePeriod
    }>
  ): Map<string, StrategySignalResult> {
    const results = new Map<string, StrategySignalResult>()

    for (const request of requests) {
      const { strategyId, params, symbol, period } = request
      const result = this.getSignals(strategyId, params, symbol, period)

      if (result) {
        const key = this.generateCacheKey('strategy_signals', strategyId, params, symbol, period)
        results.set(key, result)
      }
    }

    return results
  }

  /**
   * 预热缓存
   */
  async warmupCache(
    strategies: Array<{
      strategyId: string
      params: StrategyParams
      symbol: string
      period: TimePeriod
    }>,
    computeSignals: (strategyId: string, params: StrategyParams) => Promise<StrategySignalResult>
  ): Promise<void> {
    const promises = strategies.map(async ({ strategyId, params, symbol, period }) => {
      const key = this.generateCacheKey('strategy_signals', strategyId, params, symbol, period)

      if (!this.cache.has(key)) {
        try {
          const result = await computeSignals(strategyId, params)
          this.setSignals(strategyId, params, symbol, period, result)
        } catch (error) {
          console.error(`预热缓存失败 ${strategyId}:`, error)
        }
      }
    })

    await Promise.all(promises)
  }

  /**
   * 清理过期缓存
   */
  cleanup(): void {
    const now = Date.now()
    const keysToDelete: string[] = []

    for (const [key, item] of this.cache.entries()) {
      if (item.expiresAt <= now) {
        keysToDelete.push(key)
      }
    }

    for (const key of keysToDelete) {
      this.cache.delete(key)
      this.accessStats.delete(key)
    }

    // 如果缓存仍然太大，删除最久未访问的项
    if (this.cache.size > this.config.maxEntries) {
      this.evictLeastRecentlyUsed()
    }
  }

  /**
   * 获取缓存统计信息
   */
  getCacheStats(): {
    totalEntries: number
    totalSize: number
    hitRate: number
    entriesByType: Record<CacheKeyType, number>
    oldestEntry: number
    newestEntry: number
  } {
    const entriesByType: Record<CacheKeyType, number> = {
      strategy_signals: 0,
      market_data: 0,
      calculation_result: 0,
      comparison_data: 0
    }

    let oldestEntry = Date.now()
    let newestEntry = 0
    let totalAccessCount = 0

    for (const item of this.cache.values()) {
      entriesByType[item.keyType]++
      oldestEntry = Math.min(oldestEntry, item.timestamp)
      newestEntry = Math.max(newestEntry, item.timestamp)
      totalAccessCount += item.accessCount
    }

    const totalRequests = Array.from(this.accessStats.values())
      .reduce((sum, stat) => sum + stat.count, 0)

    return {
      totalEntries: this.cache.size,
      totalSize: this.estimateCacheSize(),
      hitRate: totalRequests > 0 ? totalAccessCount / totalRequests : 0,
      entriesByType,
      oldestEntry,
      newestEntry
    }
  }

  /**
   * 清空所有缓存
   */
  clearCache(): void {
    this.cache.clear()
    this.accessStats.clear()
  }

  /**
   * 销毁缓存服务
   */
  destroy(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer)
    }
    this.clearCache()
  }

  /**
   * 私有方法：设置缓存项
   */
  private setCacheItem(key: string, item: Omit<ExtendedCacheItem, 'key'>): void {
    // 检查缓存大小限制
    if (this.cache.size >= this.config.maxEntries) {
      this.evictLeastRecentlyUsed()
    }

    const cacheItem: ExtendedCacheItem = {
      key,
      ...item
    }

    this.cache.set(key, cacheItem)
    this.accessStats.set(key, { count: 1, lastAccess: Date.now() })
  }

  /**
   * 私有方法：获取缓存项
   */
  private getCacheItem(key: string): ExtendedCacheItem | null {
    const item = this.cache.get(key)

    if (!item || item.expiresAt <= Date.now()) {
      if (item) {
        this.cache.delete(key)
        this.accessStats.delete(key)
      }
      return null
    }

    return item
  }

  /**
   * 私有方法：更新访问统计
   */
  private updateAccessStats(key: string): void {
    const stats = this.accessStats.get(key)
    if (stats) {
      stats.count++
      stats.lastAccess = Date.now()
    }

    const item = this.cache.get(key)
    if (item) {
      item.accessCount++
      item.lastAccessed = Date.now()
    }
  }

  /**
   * 私有方法：删除最久未使用的缓存项
   */
  private evictLeastRecentlyUsed(): void {
    let oldestKey = ''
    let oldestTime = Date.now()

    for (const [key, item] of this.cache.entries()) {
      if (item.lastAccessed < oldestTime) {
        oldestTime = item.lastAccessed
        oldestKey = key
      }
    }

    if (oldestKey) {
      this.cache.delete(oldestKey)
      this.accessStats.delete(oldestKey)
    }
  }

  /**
   * 私有方法：序列化参数
   */
  private serializeParams(params: StrategyParams): string {
    return JSON.stringify(params, Object.keys(params).sort())
  }

  /**
   * 私有方法：参数哈希
   */
  private hashParams(params: StrategyParams): string {
    const serialized = this.serializeParams(params)
    let hash = 0
    for (let i = 0; i < serialized.length; i++) {
      const char = serialized.charCodeAt(i)
      hash = ((hash << 5) - hash) + char
      hash = hash & hash // 转换为32位整数
    }
    return hash.toString(36)
  }

  /**
   * 私有方法：检查是否为关键参数
   */
  private isCriticalParameter(strategyId: string, paramName: string): boolean {
    const criticalParams: Record<StrategyType, string[]> = {
      'sma_crossover': ['shortPeriod', 'longPeriod'],
      'ema_crossover': ['shortPeriod', 'longPeriod'],
      'rsi_oversold': ['period', 'oversoldThreshold'],
      'rsi_overbought': ['period', 'overboughtThreshold'],
      'macd_crossover': ['fastPeriod', 'slowPeriod', 'signalPeriod'],
      'bollinger_bands': ['period', 'stdDev'],
      'custom': [] // 自定义策略的所有参数都认为是关键的
    }

    // 从预设配置中获取策略类型
    const presetStrategies = ['sma_crossover', 'ema_crossover', 'rsi_oversold', 'rsi_overbought', 'macd_crossover', 'bollinger_bands']
    const strategyType = presetStrategies.includes(strategyId) ? strategyId as StrategyType : 'custom'

    const criticalForType = criticalParams[strategyType] || []

    // 自定义策略认为所有参数都是关键的
    return strategyType === 'custom' || criticalForType.includes(paramName)
  }

  /**
   * 私有方法：计算信号差异
   */
  private calculateDifference(oldSignals: StrategySignal[], newSignals: StrategySignal[]): SignalDifference {
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
   * 私有方法：检查信号是否发生变化
   */
  private hasSignalChanged(oldSignal: StrategySignal, newSignal: StrategySignal): boolean {
    return (
      oldSignal.signalType !== newSignal.signalType ||
      oldSignal.confidence !== newSignal.confidence ||
      oldSignal.strength !== newSignal.strength ||
      Math.abs(oldSignal.price - newSignal.price) > 0.01
    )
  }

  /**
   * 私有方法：执行增量更新
   */
  private async performIncrementalUpdate(
    strategyId: string,
    oldParams: StrategyParams,
    newParams: StrategyParams,
    symbol: string,
    period: TimePeriod,
    computeNewSignals: (params: StrategyParams) => Promise<StrategySignalResult>
  ): Promise<SignalDifference | null> {
    // 这里可以实现更智能的增量更新逻辑
    // 例如：只重新计算受影响的时间段，使用差分算法等

    // 目前简化实现：尝试缓存友好的更新
    const oldResult = this.getSignals(strategyId, oldParams, symbol, period)
    if (!oldResult) {
      return null
    }

    // 对于某些策略，可以实现特定的增量逻辑
    switch (strategyId) {
      case 'sma_crossover':
        return this.performSMAIncrementalUpdate(oldParams, newParams, oldResult, computeNewSignals)
      default:
        return null // 不支持增量更新
    }
  }

  /**
   * 私有方法：SMA策略增量更新
   */
  private async performSMAIncrementalUpdate(
    oldParams: StrategyParams,
    newParams: StrategyParams,
    oldResult: StrategySignalResult,
    computeNewSignals: (params: StrategyParams) => Promise<StrategySignalResult>
  ): Promise<SignalDifference | null> {
    const oldShortPeriod = oldParams.shortPeriod || 10
    const oldLongPeriod = oldParams.longPeriod || 30
    const newShortPeriod = newParams.shortPeriod || 10
    const newLongPeriod = newParams.longPeriod || 30

    // 如果周期没有变化，可能不需要完全重新计算
    if (oldShortPeriod === newShortPeriod && oldLongPeriod === newLongPeriod) {
      return { added: [], removed: [], modified: [] } // 没有变化
    }

    // 回退到完全重新计算
    const newResult = await computeNewSignals(newParams)
    return this.calculateDifference(oldResult.signals, newResult.signals)
  }

  /**
   * 私有方法：估算缓存大小
   */
  private estimateCacheSize(): number {
    let totalSize = 0
    for (const item of this.cache.values()) {
      // 粗略估算：每个信号约500字节，加上其他元数据
      totalSize += (item.signals.length * 500) + 1000
    }
    return totalSize
  }

  /**
   * 私有方法：启动清理定时器
   */
  private startCleanupTimer(): void {
    this.cleanupTimer = setInterval(() => {
      this.cleanup()
    }, this.config.cleanupInterval)
  }
}

// 导出单例实例
export const signalCacheService = new SignalCacheService()