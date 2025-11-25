import {
  TimePeriod,
  CandlestickData,
  KlineCacheConfig
} from '../types/kline.types'
import { timePeriodService } from './timePeriodService'

/**
 * 缓存条目接口
 */
interface CacheEntry {
  data: CandlestickData[]
  timestamp: number
  sourcePeriod?: TimePeriod
  isAggregated: boolean
}

/**
 * 时间周期缓存管理器
 */
export class TimePeriodCacheManager {
  private cache = new Map<string, CacheEntry>()
  private config: KlineCacheConfig

  constructor(config?: Partial<KlineCacheConfig>) {
    this.config = {
      enabled: true,
      maxAge: 5 * 60 * 1000,  // 5分钟
      maxSize: 50,
      storage: 'memory',
      ...config
    }

    // 定期清理过期缓存
    setInterval(() => this.cleanup(), 60 * 1000) // 每分钟清理一次
  }

  /**
   * 生成缓存键
   */
  private generateKey(symbol: string, period: TimePeriod, startDate?: string, endDate?: string): string {
    const dateRange = startDate && endDate ? `:${startDate}:${endDate}` : ''
    return `${symbol}_${period}${dateRange}`
  }

  /**
   * 存储数据到缓存
   */
  set(
    symbol: string,
    period: TimePeriod,
    data: CandlestickData[],
    sourcePeriod?: TimePeriod,
    dateRange?: { start: string; end: string }
  ): void {
    if (!this.config.enabled || data.length === 0) return

    const key = this.generateKey(
      symbol,
      period,
      dateRange?.start,
      dateRange?.end
    )

    // 检查缓存大小限制
    if (this.cache.size >= this.config.maxSize) {
      this.evictOldest()
    }

    const entry: CacheEntry = {
      data,
      timestamp: Date.now(),
      sourcePeriod,
      isAggregated: sourcePeriod !== undefined && sourcePeriod !== period
    }

    this.cache.set(key, entry)
  }

  /**
   * 从缓存获取数据
   */
  get(
    symbol: string,
    period: TimePeriod,
    dateRange?: { start: string; end: string }
  ): CandlestickData[] | null {
    if (!this.config.enabled) return null

    const key = this.generateKey(
      symbol,
      period,
      dateRange?.start,
      dateRange?.end
    )

    const cached = this.cache.get(key)

    if (!cached) return null

    // 检查是否过期
    if (Date.now() - cached.timestamp > this.config.maxAge) {
      this.cache.delete(key)
      return null
    }

    return cached.data
  }

  /**
   * 智能获取数据，支持从缓存聚合
   */
  async getSmart(
    symbol: string,
    period: TimePeriod,
    availablePeriods: TimePeriod[],
    dateRange?: { start: string; end: string }
  ): Promise<CandlestickData[] | null> {
    // 首先尝试直接从缓存获取
    const cached = this.get(symbol, period, dateRange)
    if (cached) return cached

    // 尝试从更细粒度的缓存数据聚合
    for (const sourcePeriod of availablePeriods) {
      if (timePeriodService.isFinerPeriod(sourcePeriod, period)) {
        const sourceData = this.get(symbol, sourcePeriod, dateRange)
        if (sourceData && sourceData.length > 0) {
          try {
            const aggregated = timePeriodService.aggregateData(
              sourceData,
              sourcePeriod,
              period
            )

            // 缓存聚合后的数据
            this.set(symbol, period, aggregated, sourcePeriod, dateRange)
            return aggregated
          } catch (error) {
            console.warn(`聚合失败 ${sourcePeriod} → ${period}:`, error)
          }
        }
      }
    }

    return null
  }

  /**
   * 预加载多个时间周期的数据
   */
  async preloadPeriods(
    symbol: string,
    basePeriod: TimePeriod,
    baseData: CandlestickData[],
    targetPeriods: TimePeriod[],
    dateRange?: { start: string; end: string }
  ): Promise<void> {
    // 存储基础数据
    this.set(symbol, basePeriod, baseData, undefined, dateRange)

    // 聚合并存储目标周期数据
    for (const period of targetPeriods) {
      if (period !== basePeriod && timePeriodService.isFinerPeriod(basePeriod, period)) {
        try {
          const aggregated = timePeriodService.aggregateData(baseData, basePeriod, period)
          this.set(symbol, period, aggregated, basePeriod, dateRange)
        } catch (error) {
          console.warn(`预加载聚合失败 ${basePeriod} → ${period}:`, error)
        }
      }
    }
  }

  /**
   * 清理过期缓存
   */
  private cleanup(): void {
    const now = Date.now()
    const keysToDelete: string[] = []

    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > this.config.maxAge) {
        keysToDelete.push(key)
      }
    }

    keysToDelete.forEach(key => this.cache.delete(key))
  }

  /**
   * 驱逐最旧的缓存条目
   */
  private evictOldest(): void {
    let oldestKey: string | null = null
    let oldestTimestamp = Infinity

    for (const [key, entry] of this.cache.entries()) {
      if (entry.timestamp < oldestTimestamp) {
        oldestTimestamp = entry.timestamp
        oldestKey = key
      }
    }

    if (oldestKey) {
      this.cache.delete(oldestKey)
    }
  }

  /**
   * 清空指定符号的所有缓存
   */
  clearSymbol(symbol: string): void {
    const keysToDelete: string[] = []

    for (const key of this.cache.keys()) {
      if (key.startsWith(`${symbol}_`)) {
        keysToDelete.push(key)
      }
    }

    keysToDelete.forEach(key => this.cache.delete(key))
  }

  /**
   * 清空所有缓存
   */
  clear(): void {
    this.cache.clear()
  }

  /**
   * 获取缓存统计信息
   */
  getStats(): {
    totalEntries: number
    aggregatedEntries: number
    directEntries: number
    entriesBySymbol: Record<string, number>
    entriesByPeriod: Record<TimePeriod, number>
  } {
    const stats = {
      totalEntries: this.cache.size,
      aggregatedEntries: 0,
      directEntries: 0,
      entriesBySymbol: {} as Record<string, number>,
      entriesByPeriod: {} as Record<TimePeriod, number>
    }

    for (const [key, entry] of this.cache.entries()) {
      const [symbol, period] = key.split('_') as [string, TimePeriod]

      // 统计聚合/直接条目
      if (entry.isAggregated) {
        stats.aggregatedEntries++
      } else {
        stats.directEntries++
      }

      // 按符号统计
      stats.entriesBySymbol[symbol] = (stats.entriesBySymbol[symbol] || 0) + 1

      // 按周期统计
      stats.entriesByPeriod[period] = (stats.entriesByPeriod[period] || 0) + 1
    }

    return stats
  }

  /**
   * 获取缓存健康状态
   */
  getHealthStatus(): {
    status: 'healthy' | 'warning' | 'critical'
    utilization: number
    oldestEntry: number
    recommendations: string[]
  } {
    const utilization = this.cache.size / this.config.maxSize
    let oldestEntry = 0

    const now = Date.now()
    for (const entry of this.cache.values()) {
      const age = now - entry.timestamp
      oldestEntry = Math.max(oldestEntry, age)
    }

    const recommendations: string[] = []

    // 评估缓存利用率
    if (utilization > 0.9) {
      recommendations.push('缓存利用率过高，考虑增加缓存大小或减少缓存时间')
    }

    // 评估缓存时效性
    if (oldestEntry > this.config.maxAge * 2) {
      recommendations.push('存在过期的缓存条目，建议手动清理或调整清理策略')
    }

    // 评估聚合缓存比例
    const stats = this.getStats()
    const aggregationRatio = stats.aggregatedEntries / stats.totalEntries
    if (aggregationRatio > 0.7) {
      recommendations.push('聚合缓存比例较高，考虑从API直接获取目标周期数据')
    }

    // 确定健康状态
    let status: 'healthy' | 'warning' | 'critical' = 'healthy'
    if (utilization > 0.9 || oldestEntry > this.config.maxAge * 2) {
      status = 'critical'
    } else if (utilization > 0.7 || oldestEntry > this.config.maxAge * 1.5) {
      status = 'warning'
    }

    return {
      status,
      utilization,
      oldestEntry,
      recommendations
    }
  }

  /**
   * 优化缓存策略
   */
  optimize(): void {
    const health = this.getHealthStatus()

    if (health.status === 'critical') {
      // 清理过期数据
      this.cleanup()

      // 如果仍然超过80%利用率，进一步清理
      if (this.getStats().totalEntries / this.config.maxSize > 0.8) {
        // 优先清理聚合数据
        const keysToDelete: string[] = []

        for (const [key, entry] of this.cache.entries()) {
          if (entry.isAggregated) {
            keysToDelete.push(key)
          }
        }

        // 删除最旧的聚合数据
        keysToDelete
          .sort(() => Math.random() - 0.5)
          .slice(0, Math.floor(keysToDelete.length * 0.5))
          .forEach(key => this.cache.delete(key))
      }
    }
  }
}

// 导出单例实例
export const timePeriodCacheManager = new TimePeriodCacheManager()