import {
  TimePeriod,
  CandlestickData,
  KlineData
} from '../types/kline.types'
import { timePeriodService } from './timePeriodService'
import { timePeriodCacheManager } from './timePeriodCache'

/**
 * 时间周期数据管理器
 */
export class TimePeriodDataManager {
  private symbol: string
  private availablePeriods: Set<TimePeriod> = new Set()
  private loadingPeriods: Set<TimePeriod> = new Set()
  private listeners: Map<TimePeriod, ((data: CandlestickData[]) => void)[]> = new Map()

  constructor(symbol: string) {
    this.symbol = symbol
  }

  /**
   * 获取指定时间周期的数据
   */
  async getData(
    period: TimePeriod,
    dateRange?: { start: string; end: string }
  ): Promise<CandlestickData[]> {
    // 如果正在加载，返回空数组避免重复请求
    if (this.loadingPeriods.has(period)) {
      return []
    }

    // 尝试从缓存获取
    const cached = await timePeriodCacheManager.getSmart(
      this.symbol,
      period,
      Array.from(this.availablePeriods),
      dateRange
    )

    if (cached) {
      return cached
    }

    // 从API获取数据
    return this.fetchDataFromAPI(period, dateRange)
  }

  /**
   * 从API获取数据（示例实现）
   */
  private async fetchDataFromAPI(
    period: TimePeriod,
    dateRange?: { start: string; end: string }
  ): Promise<CandlestickData[]> {
    this.loadingPeriods.add(period)

    try {
      // TODO: 实现真实的API调用
      const data = await this.mockAPICall(period, dateRange)

      if (data.length > 0) {
        // 缓存数据
        timePeriodCacheManager.set(this.symbol, period, data, undefined, dateRange)

        // 记录可用的时间周期
        this.availablePeriods.add(period)

        // 预加载相邻的时间周期
        await this.preloadNeighborPeriods(period, data, dateRange)

        // 通知监听器
        this.notifyListeners(period, data)
      }

      return data
    } finally {
      this.loadingPeriods.delete(period)
    }
  }

  /**
   * 模拟API调用（仅用于演示）
   */
  private async mockAPICall(
    period: TimePeriod,
    dateRange?: { start: string; end: string }
  ): Promise<CandlestickData[]> {
    // 模拟网络延迟
    await new Promise(resolve => setTimeout(resolve, 100))

    const periodMinutes = timePeriodService.getPeriodMinutes(period)
    const now = new Date()
    const dataPoints = this.calculateDataPoints(period, dateRange)
    const data: CandlestickData[] = []

    for (let i = dataPoints - 1; i >= 0; i--) {
      const timestamp = new Date(now.getTime() - i * periodMinutes * 60 * 1000)

      // 生成模拟数据
      const basePrice = 100
      const volatility = 0.02
      const trend = Math.sin(i * 0.1) * 0.5

      const open = basePrice + trend + (Math.random() - 0.5) * 5
      const close = open + (Math.random() - 0.5) * 3
      const high = Math.max(open, close) + Math.random() * 2
      const low = Math.min(open, close) - Math.random() * 2
      const volume = Math.floor(1000000 + Math.random() * 9000000)

      data.push({
        timestamp: timestamp.toISOString(),
        open: Math.max(1, open),
        high: Math.max(1, high),
        low: Math.max(1, low),
        close: Math.max(1, close),
        volume
      })
    }

    return data
  }

  /**
   * 计算数据点数量
   */
  private calculateDataPoints(
    period: TimePeriod,
    dateRange?: { start: string; end: string }
  ): number {
    if (dateRange) {
      const start = new Date(dateRange.start).getTime()
      const end = new Date(dateRange.end).getTime()
      const periodMs = timePeriodService.getPeriodMinutes(period) * 60 * 1000
      return Math.floor((end - start) / periodMs)
    }

    // 默认返回不同周期的合理数据量
    const defaultPoints: Record<TimePeriod, number> = {
      [TimePeriod.MINUTE_1]: 1440, // 1天
      [TimePeriod.MINUTE_5]: 288,  // 1天
      [TimePeriod.MINUTE_15]: 96,  // 1天
      [TimePeriod.MINUTE_30]: 48,  // 1天
      [TimePeriod.HOUR_1]: 168,    // 1周
      [TimePeriod.HOUR_4]: 42,     // 1周
      [TimePeriod.DAY_1]: 365,     // 1年
      [TimePeriod.DAY_7]: 52,      // 1年
      [TimePeriod.MONTH_1]: 24     // 2年
    }

    return defaultPoints[period] || 100
  }

  /**
   * 预加载相邻的时间周期
   */
  private async preloadNeighborPeriods(
    currentPeriod: TimePeriod,
    data: CandlestickData[],
    dateRange?: { start: string; end: string }
  ): Promise<void> {
    const allPeriods = timePeriodService.getRecommendedPeriodSequence()
    const currentIndex = allPeriods.indexOf(currentPeriod)

    // 预加载前一个和后一个周期
    const neighborPeriods: TimePeriod[] = []

    if (currentIndex > 0) {
      neighborPeriods.push(allPeriods[currentIndex - 1])
    }
    if (currentIndex < allPeriods.length - 1) {
      neighborPeriods.push(allPeriods[currentIndex + 1])
    }

    await timePeriodCacheManager.preloadPeriods(
      this.symbol,
      currentPeriod,
      data,
      neighborPeriods,
      dateRange
    )
  }

  /**
   * 批量获取多个时间周期的数据
   */
  async getBatchData(
    periods: TimePeriod[],
    dateRange?: { start: string; end: string }
  ): Promise<Map<TimePeriod, CandlestickData[]>> {
    const results = new Map<TimePeriod, CandlestickData[]>()
    const promises: Promise<void>[] = []

    for (const period of periods) {
      promises.push(
        this.getData(period, dateRange).then(data => {
          results.set(period, data)
        })
      )
    }

    await Promise.all(promises)
    return results
  }

  /**
   * 添加数据变更监听器
   */
  addListener(period: TimePeriod, callback: (data: CandlestickData[]) => void): void {
    if (!this.listeners.has(period)) {
      this.listeners.set(period, [])
    }
    this.listeners.get(period)!.push(callback)
  }

  /**
   * 移除数据变更监听器
   */
  removeListener(period: TimePeriod, callback: (data: CandlestickData[]) => void): void {
    const callbacks = this.listeners.get(period)
    if (callbacks) {
      const index = callbacks.indexOf(callback)
      if (index !== -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  /**
   * 通知监听器
   */
  private notifyListeners(period: TimePeriod, data: CandlestickData[]): void {
    const callbacks = this.listeners.get(period)
    if (callbacks) {
      callbacks.forEach(callback => callback(data))
    }
  }

  /**
   * 更新指定时间周期的数据
   */
  async updateData(
    period: TimePeriod,
    newData: CandlestickData[],
    dateRange?: { start: string; end: string }
  ): Promise<void> {
    if (newData.length === 0) return

    // 缓存新数据
    timePeriodCacheManager.set(this.symbol, period, newData, undefined, dateRange)

    // 记录可用的时间周期
    this.availablePeriods.add(period)

    // 重新预加载其他周期
    await this.preloadNeighborPeriods(period, newData, dateRange)

    // 通知监听器
    this.notifyListeners(period, newData)
  }

  /**
   * 实时更新最新数据点
   */
  async updateLatestData(
    period: TimePeriod,
    latestData: CandlestickData
  ): Promise<void> {
    // 获取现有数据
    const existingData = await this.getData(period)

    // 更新最后一个数据点或添加新数据点
    if (existingData.length > 0) {
      const lastData = existingData[existingData.length - 1]
      if (new Date(latestData.timestamp).getTime() > new Date(lastData.timestamp).getTime()) {
        // 添加新数据点
        existingData.push(latestData)
      } else {
        // 更新最后一个数据点
        existingData[existingData.length - 1] = latestData
      }
    } else {
      existingData.push(latestData)
    }

    // 限制数据长度，避免内存溢出
    const maxDataPoints = this.getMaxDataPoints(period)
    if (existingData.length > maxDataPoints) {
      existingData.splice(0, existingData.length - maxDataPoints)
    }

    // 更新缓存
    this.updateData(period, existingData)
  }

  /**
   * 获取指定周期的最大数据点数
   */
  private getMaxDataPoints(period: TimePeriod): number {
    const limits: Record<TimePeriod, number> = {
      [TimePeriod.MINUTE_1]: 2000,
      [TimePeriod.MINUTE_5]: 2000,
      [TimePeriod.MINUTE_15]: 1000,
      [TimePeriod.MINUTE_30]: 1000,
      [TimePeriod.HOUR_1]: 1000,
      [TimePeriod.HOUR_4]: 500,
      [TimePeriod.DAY_1]: 500,
      [TimePeriod.DAY_7]: 200,
      [TimePeriod.MONTH_1]: 100
    }

    return limits[period] || 500
  }

  /**
   * 清除指定周期的数据
   */
  clearPeriod(period: TimePeriod): void {
    timePeriodCacheManager.clearSymbol(this.symbol)
    this.availablePeriods.delete(period)
  }

  /**
   * 清除所有数据
   */
  clear(): void {
    timePeriodCacheManager.clearSymbol(this.symbol)
    this.availablePeriods.clear()
    this.loadingPeriods.clear()
    this.listeners.clear()
  }

  /**
   * 获取管理器状态
   */
  getStatus(): {
    symbol: string
    availablePeriods: TimePeriod[]
    loadingPeriods: TimePeriod[]
    listenerCount: number
    cacheStats: any
  } {
    return {
      symbol: this.symbol,
      availablePeriods: Array.from(this.availablePeriods),
      loadingPeriods: Array.from(this.loadingPeriods),
      listenerCount: Array.from(this.listeners.values()).reduce((sum, callbacks) => sum + callbacks.length, 0),
      cacheStats: timePeriodCacheManager.getStats()
    }
  }

  /**
   * 获取推荐的时间周期
   */
  getRecommendedPeriods(): TimePeriod[] {
    if (this.availablePeriods.size === 0) {
      return timePeriodService.getRecommendedPeriodSequence()
    }

    return Array.from(this.availablePeriods).sort((a, b) => {
      const allPeriods = timePeriodService.getRecommendedPeriodSequence()
      return allPeriods.indexOf(a) - allPeriods.indexOf(b)
    })
  }

  /**
   * 根据时间范围推荐最合适的时间周期
   */
  recommendPeriodForDateRange(startDate: string, endDate: string): TimePeriod {
    // 首先基于时间范围推荐
    const recommended = timePeriodService.recommendTimePeriod(startDate, endDate)

    // 如果推荐的时间周期在可用列表中，直接返回
    if (this.availablePeriods.has(recommended)) {
      return recommended
    }

    // 否则返回最接近的可用周期
    const allPeriods = timePeriodService.getRecommendedPeriodSequence()
    const recommendedIndex = allPeriods.indexOf(recommended)

    // 向上查找更粗粒度的可用周期
    for (let i = recommendedIndex + 1; i < allPeriods.length; i++) {
      if (this.availablePeriods.has(allPeriods[i])) {
        return allPeriods[i]
      }
    }

    // 向下查找更细粒度的可用周期
    for (let i = recommendedIndex - 1; i >= 0; i--) {
      if (this.availablePeriods.has(allPeriods[i])) {
        return allPeriods[i]
      }
    }

    // 如果都没有找到，返回第一个可用周期
    return this.availablePeriods.size > 0
      ? Array.from(this.availablePeriods)[0]
      : TimePeriod.DAY_1
  }
}

// 导出工厂函数
export function createTimePeriodDataManager(symbol: string): TimePeriodDataManager {
  return new TimePeriodDataManager(symbol)
}