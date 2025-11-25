import {
  TimePeriod,
  CandlestickData,
  KlineData
} from '../types/kline.types'
import { KlineDataAggregator } from '../utils/klineHelpers'

/**
 * 时间周期服务
 */
export class TimePeriodService {
  /**
   * 将数据聚合到目标时间周期
   */
  static aggregateData(
    data: CandlestickData[],
    fromPeriod: TimePeriod,
    toPeriod: TimePeriod
  ): CandlestickData[] {
    if (fromPeriod === toPeriod || data.length === 0) {
      return data
    }

    // 如果从更细粒度聚合到更粗粒度
    if (this.isFinerPeriod(fromPeriod, toPeriod)) {
      return this.aggregateToCoarserPeriod(data, fromPeriod, toPeriod)
    }
    // 如果从更粗粒度聚合到更细粒度（需要填充数据）
    else {
      return this.interpolateToFinerPeriod(data, fromPeriod, toPeriod)
    }
  }

  /**
   * 判断是否为更细粒度的时间周期
   */
  private static isFinerPeriod(period1: TimePeriod, period2: TimePeriod): boolean {
    const periodOrder = [
      TimePeriod.MINUTE_1,
      TimePeriod.MINUTE_5,
      TimePeriod.MINUTE_15,
      TimePeriod.MINUTE_30,
      TimePeriod.HOUR_1,
      TimePeriod.HOUR_4,
      TimePeriod.DAY_1,
      TimePeriod.DAY_7,
      TimePeriod.MONTH_1
    ]

    return periodOrder.indexOf(period1) < periodOrder.indexOf(period2)
  }

  /**
   * 聚合到更粗粒度的时间周期
   */
  private static aggregateToCoarserPeriod(
    data: CandlestickData[],
    fromPeriod: TimePeriod,
    toPeriod: TimePeriod
  ): CandlestickData[] {
    const fromMinutes = this.getPeriodMinutes(fromPeriod)
    const toMinutes = this.getPeriodMinutes(toPeriod)
    const ratio = Math.floor(toMinutes / fromMinutes)

    if (ratio <= 1) {
      return data
    }

    const result: CandlestickData[] = []

    for (let i = 0; i < data.length; i += ratio) {
      const chunk = data.slice(i, i + ratio)
      if (chunk.length === 0) continue

      const aggregated = this.aggregateCandlestickData(chunk, toPeriod)
      result.push(aggregated)
    }

    return result
  }

  /**
   * 插值到更细粒度的时间周期（简单实现）
   */
  private static interpolateToFinerPeriod(
    data: CandlestickData[],
    fromPeriod: TimePeriod,
    toPeriod: TimePeriod
  ): CandlestickData[] {
    // 这是一个简化实现，实际应用中可能需要更复杂的插值算法
    // 或者建议用户从API获取对应时间周期的数据

    console.warn(`无法从 ${fromPeriod} 插值到 ${toPeriod}，建议直接从API获取数据`)
    return data
  }

  /**
   * 聚合多个K线数据点为一个
   */
  private static aggregateCandlestickData(
    chunk: CandlestickData[],
    targetPeriod: TimePeriod
  ): CandlestickData {
    if (chunk.length === 0) {
      throw new Error('无法聚合空数据块')
    }

    const first = chunk[0]
    const last = chunk[chunk.length - 1]

    // 基本OHLCV聚合
    const open = first.open
    const close = last.close
    const high = Math.max(...chunk.map(c => c.high))
    const low = Math.min(...chunk.map(c => c.low))
    const volume = chunk.reduce((sum, c) => sum + c.volume, 0)

    // 生成目标时间周期的时间戳
    const targetTimestamp = this.generateTimestampForPeriod(
      last.timestamp,
      targetPeriod
    )

    return {
      timestamp: targetTimestamp,
      open,
      high,
      low,
      close,
      volume
    }
  }

  /**
   * 为目标时间周期生成时间戳
   */
  private static generateTimestampForPeriod(
    sourceTimestamp: string,
    targetPeriod: TimePeriod
  ): string {
    const date = new Date(sourceTimestamp)

    switch (targetPeriod) {
      case TimePeriod.MINUTE_1:
      case TimePeriod.MINUTE_5:
      case TimePeriod.MINUTE_15:
      case TimePeriod.MINUTE_30:
        return date.toISOString()

      case TimePeriod.HOUR_1:
        date.setMinutes(0, 0, 0)
        return date.toISOString()

      case TimePeriod.HOUR_4:
        const hour4 = Math.floor(date.getHours() / 4) * 4
        date.setHours(hour4, 0, 0, 0)
        return date.toISOString()

      case TimePeriod.DAY_1:
        date.setHours(0, 0, 0, 0)
        return date.toISOString()

      case TimePeriod.DAY_7:
        // 获取周的开始（周一）
        const dayOfWeek = date.getDay()
        const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1
        date.setDate(date.getDate() - daysToMonday)
        date.setHours(0, 0, 0, 0)
        return date.toISOString()

      case TimePeriod.MONTH_1:
        date.setDate(1)
        date.setHours(0, 0, 0, 0)
        return date.toISOString()

      default:
        return sourceTimestamp
    }
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
      [TimePeriod.MONTH_1]: 43200 // 约等于30天
    }

    return periodMap[period] || 60
  }

  /**
   * 预加载多个时间周期的数据
   */
  static async preloadMultiplePeriods(
    baseData: CandlestickData[],
    basePeriod: TimePeriod,
    targetPeriods: TimePeriod[]
  ): Promise<Map<TimePeriod, CandlestickData[]>> {
    const dataMap = new Map<TimePeriod, CandlestickData[]>()

    for (const period of targetPeriods) {
      if (period === basePeriod) {
        dataMap.set(period, baseData)
      } else if (this.isFinerPeriod(basePeriod, period)) {
        // 聚合到更粗粒度
        const aggregated = this.aggregateData(baseData, basePeriod, period)
        dataMap.set(period, aggregated)
      } else {
        // 对于更细粒度的数据，标记为需要从API获取
        dataMap.set(period, [])
      }
    }

    return dataMap
  }

  /**
   * 计算两个时间周期之间的转换比例
   */
  static getPeriodRatio(fromPeriod: TimePeriod, toPeriod: TimePeriod): number {
    const fromMinutes = this.getPeriodMinutes(fromPeriod)
    const toMinutes = this.getPeriodMinutes(toPeriod)
    return Math.max(1, Math.floor(toMinutes / fromMinutes))
  }

  /**
   * 获取时间周期的显示名称
   */
  static getPeriodDisplayName(period: TimePeriod): string {
    const names: Record<TimePeriod, string> = {
      [TimePeriod.MINUTE_1]: '1分钟',
      [TimePeriod.MINUTE_5]: '5分钟',
      [TimePeriod.MINUTE_15]: '15分钟',
      [TimePeriod.MINUTE_30]: '30分钟',
      [TimePeriod.HOUR_1]: '1小时',
      [TimePeriod.HOUR_4]: '4小时',
      [TimePeriod.DAY_1]: '日线',
      [TimePeriod.DAY_7]: '周线',
      [TimePeriod.MONTH_1]: '月线'
    }

    return names[period] || period
  }

  /**
   * 获取推荐的时间周期序列（从细到粗）
   */
  static getRecommendedPeriodSequence(): TimePeriod[] {
    return [
      TimePeriod.MINUTE_1,
      TimePeriod.MINUTE_5,
      TimePeriod.MINUTE_15,
      TimePeriod.MINUTE_30,
      TimePeriod.HOUR_1,
      TimePeriod.HOUR_4,
      TimePeriod.DAY_1,
      TimePeriod.DAY_7,
      TimePeriod.MONTH_1
    ]
  }

  /**
   * 根据时间范围推荐合适的时间周期
   */
  static recommendTimePeriod(startDate: string, endDate: string): TimePeriod {
    const start = new Date(startDate).getTime()
    const end = new Date(endDate).getTime()
    const days = (end - start) / (1000 * 60 * 60 * 24)

    if (days < 1) {
      return TimePeriod.MINUTE_1
    } else if (days < 7) {
      return TimePeriod.MINUTE_15
    } else if (days < 30) {
      return TimePeriod.HOUR_1
    } else if (days < 90) {
      return TimePeriod.DAY_1
    } else if (days < 365) {
      return TimePeriod.DAY_7
    } else {
      return TimePeriod.MONTH_1
    }
  }

  /**
   * 验证数据的时间周期一致性
   */
  static validateTimePeriodConsistency(data: CandlestickData[]): boolean {
    if (data.length < 2) return true

    const intervals: number[] = []
    for (let i = 1; i < data.length; i++) {
      const prev = new Date(data[i - 1].timestamp).getTime()
      const curr = new Date(data[i].timestamp).getTime()
      intervals.push(curr - prev)
    }

    // 计算平均间隔
    const avgInterval = intervals.reduce((sum, interval) => sum + interval, 0) / intervals.length

    // 检查是否有超过50%的间隔与平均间隔偏差过大
    const inconsistentCount = intervals.filter(interval =>
      Math.abs(interval - avgInterval) / avgInterval > 0.5
    ).length

    return inconsistentCount < intervals.length * 0.5
  }

  /**
   * 补充缺失的时间点（用前一个数据填充）
   */
  static fillMissingData(
    data: CandlestickData[],
    period: TimePeriod,
    startDate: string,
    endDate: string
  ): CandlestickData[] {
    if (data.length === 0) return []

    const periodMinutes = this.getPeriodMinutes(period)
    const start = new Date(startDate).getTime()
    const end = new Date(endDate).getTime()
    const result: CandlestickData[] = []

    let currentTimestamp = start
    let dataIndex = 0
    let lastValidData: CandlestickData | null = null

    while (currentTimestamp <= end) {
      const currentStr = new Date(currentTimestamp).toISOString()

      // 查找对应的数据点
      while (dataIndex < data.length && new Date(data[dataIndex].timestamp).getTime() < currentTimestamp) {
        lastValidData = data[dataIndex]
        dataIndex++
      }

      if (dataIndex < data.length && new Date(data[dataIndex].timestamp).getTime() === currentTimestamp) {
        result.push(data[dataIndex])
        lastValidData = data[dataIndex]
        dataIndex++
      } else if (lastValidData) {
        // 用前一个有效数据填充缺失的时间点
        result.push({
          ...lastValidData,
          timestamp: currentStr,
          open: lastValidData.close,
          high: lastValidData.close,
          low: lastValidData.close,
          close: lastValidData.close,
          volume: 0
        })
      }

      currentTimestamp += periodMinutes * 60 * 1000
    }

    return result
  }
}

// 导出单例实例
export const timePeriodService = TimePeriodService