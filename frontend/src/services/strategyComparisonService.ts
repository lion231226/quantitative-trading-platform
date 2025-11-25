import {
  StrategySignal,
  StrategySignalResult,
  SignalComparison,
  SignalStatistics,
  StrategyConfig,
  StrategyParams,
  strategySignalManager
} from '../types/strategySignal.types'
import { TimePeriod } from '../types/kline.types'

// 对比分析结果
export interface ComparisonAnalysis {
  comparisonId: string
  strategyA: {
    id: string
    name: string
    params: StrategyParams
    signals: StrategySignal[]
    statistics: SignalStatistics
  }
  strategyB: {
    id: string
    name: string
    params: StrategyParams
    signals: StrategySignal[]
    statistics: SignalStatistics
  }
  correlation: {
    overall: number
    buySignal: number
    sellSignal: number
    timing: number
  }
  performance: {
    totalReturns: {
      strategyA: number
      strategyB: number
      difference: number
      winner: 'A' | 'B' | 'tie'
    }
    winRates: {
      strategyA: number
      strategyB: number
      difference: number
      winner: 'A' | 'B' | 'tie'
    }
    signalCounts: {
      strategyA: number
      strategyB: number
      difference: number
    }
  }
  timing: {
    averageLeadTime: number // 策略A相对于策略B的平均领先时间（毫秒）
    signalAlignment: number  // 信号对齐度（0-1）
    divergencePoints: Array<{
      timestamp: number
      strategyASignal: StrategySignal | null
      strategyBSignal: StrategySignal | null
      difference: 'onlyA' | 'onlyB' | 'opposite'
    }>
  }
  risk: {
    signalVolatility: {
      strategyA: number
      strategyB: number
    }
    confidenceStability: {
      strategyA: number
      strategyB: number
    }
  }
  recommendations: string[]
}

// 对比配置
export interface ComparisonConfig {
  timeRange?: {
    start: number
    end: number
  }
  signalTypes?: string[]
  confidenceThreshold?: number
  includeHoldSignals?: boolean
}

// 实时对比监控
export interface ComparisonMonitor {
  comparisonId: string
  strategies: string[]
  isMonitoring: boolean
  lastUpdate: number
  alertThresholds: {
    correlationChange: number
    performanceChange: number
    signalDivergence: number
  }
}

// 策略对比服务类
export class StrategyComparisonService {
  private comparisons = new Map<string, ComparisonAnalysis>()
  private monitors = new Map<string, ComparisonMonitor>()
  private performanceCache = new Map<string, any>()

  /**
   * 创建策略对比
   */
  async createComparison(
    strategyA: { id: string; name: string; params: StrategyParams; signals: StrategySignal[] },
    strategyB: { id: string; name: string; params: StrategyParams; signals: StrategySignal[] },
    config?: ComparisonConfig
  ): Promise<ComparisonAnalysis> {
    const comparisonId = this.generateComparisonId(strategyA.id, strategyB.id)

    // 过滤信号
    const filteredSignalsA = this.filterSignals(strategyA.signals, config)
    const filteredSignalsB = this.filterSignals(strategyB.signals, config)

    // 计算统计信息
    const statisticsA = strategySignalManager.getStatistics(filteredSignalsA)
    const statisticsB = strategySignalManager.getStatistics(filteredSignalsB)

    // 基础对比分析
    const basicComparison = strategySignalManager.compareSignals(filteredSignalsA, filteredSignalsB)

    // 详细分析
    const detailedAnalysis = await this.performDetailedAnalysis(
      filteredSignalsA,
      filteredSignalsB,
      strategyA,
      strategyB,
      config
    )

    const comparison: ComparisonAnalysis = {
      comparisonId,
      strategyA: {
        ...strategyA,
        signals: filteredSignalsA,
        statistics: statisticsA
      },
      strategyB: {
        ...strategyB,
        signals: filteredSignalsB,
        statistics: statisticsB
      },
      correlation: detailedAnalysis.correlation,
      performance: detailedAnalysis.performance,
      timing: detailedAnalysis.timing,
      risk: detailedAnalysis.risk,
      recommendations: detailedAnalysis.recommendations
    }

    // 缓存结果
    this.comparisons.set(comparisonId, comparison)

    return comparison
  }

  /**
   * 获取对比结果
   */
  getComparison(comparisonId: string): ComparisonAnalysis | null {
    return this.comparisons.get(comparisonId) || null
  }

  /**
   * 更新对比分析
   */
  async updateComparison(
    comparisonId: string,
    newSignalsA?: StrategySignal[],
    newSignalsB?: StrategySignal[]
  ): Promise<ComparisonAnalysis | null> {
    const existingComparison = this.comparisons.get(comparisonId)
    if (!existingComparison) {
      throw new Error(`对比分析不存在: ${comparisonId}`)
    }

    // 更新信号数据
    const strategyA = {
      ...existingComparison.strategyA,
      signals: newSignalsA || existingComparison.strategyA.signals
    }

    const strategyB = {
      ...existingComparison.strategyB,
      signals: newSignalsB || existingComparison.strategyB.signals
    }

    // 重新分析
    return this.createComparison(strategyA, strategyB)
  }

  /**
   * 批量对比多个策略
   */
  async batchComparison(
    strategies: Array<{ id: string; name: string; params: StrategyParams; signals: StrategySignal[] }>,
    config?: ComparisonConfig
  ): Promise<Map<string, ComparisonAnalysis>> {
    const results = new Map<string, ComparisonAnalysis>()

    for (let i = 0; i < strategies.length; i++) {
      for (let j = i + 1; j < strategies.length; j++) {
        const strategyA = strategies[i]
        const strategyB = strategies[j]

        try {
          const comparison = await this.createComparison(strategyA, strategyB, config)
          results.set(comparison.comparisonId, comparison)
        } catch (error) {
          console.error(`批量对比失败 ${strategyA.id} vs ${strategyB.id}:`, error)
        }
      }
    }

    return results
  }

  /**
   * 启动实时监控
   */
  startMonitoring(
    comparisonId: string,
    alertThresholds: ComparisonMonitor['alertThresholds']
  ): void {
    const monitor: ComparisonMonitor = {
      comparisonId,
      strategies: [],
      isMonitoring: true,
      lastUpdate: Date.now(),
      alertThresholds
    }

    this.monitors.set(comparisonId, monitor)
  }

  /**
   * 停止实时监控
   */
  stopMonitoring(comparisonId: string): void {
    const monitor = this.monitors.get(comparisonId)
    if (monitor) {
      monitor.isMonitoring = false
    }
  }

  /**
   * 获取所有监控
   */
  getAllMonitors(): ComparisonMonitor[] {
    return Array.from(this.monitors.values())
  }

  /**
   * 生成对比报告
   */
  generateComparisonReport(comparisonId: string): {
    summary: string
    detailedAnalysis: string
    recommendations: string[]
    charts: Array<{
      type: 'correlation' | 'performance' | 'timing' | 'risk'
      data: any
      title: string
    }>
  } | null {
    const comparison = this.comparisons.get(comparisonId)
    if (!comparison) {
      return null
    }

    const summary = this.generateSummary(comparison)
    const detailedAnalysis = this.generateDetailedAnalysis(comparison)

    return {
      summary,
      detailedAnalysis,
      recommendations: comparison.recommendations,
      charts: [
        {
          type: 'correlation',
          data: comparison.correlation,
          title: '信号相关性分析'
        },
        {
          type: 'performance',
          data: comparison.performance,
          title: '性能对比'
        },
        {
          type: 'timing',
          data: comparison.timing,
          title: '时机分析'
        },
        {
          type: 'risk',
          data: comparison.risk,
          title: '风险评估'
        }
      ]
    }
  }

  /**
   * 私有方法：执行详细分析
   */
  private async performDetailedAnalysis(
    signalsA: StrategySignal[],
    signalsB: StrategySignal[],
    strategyA: { id: string; name: string; params: StrategyParams },
    strategyB: { id: string; name: string; params: StrategyParams },
    config?: ComparisonConfig
  ) {
    // 相关性分析
    const correlation = this.analyzeCorrelation(signalsA, signalsB)

    // 性能分析
    const performance = this.analyzePerformance(signalsA, signalsB)

    // 时机分析
    const timing = this.analyzeTiming(signalsA, signalsB)

    // 风险分析
    const risk = this.analyzeRisk(signalsA, signalsB)

    // 生成建议
    const recommendations = this.generateRecommendations(correlation, performance, timing, risk)

    return {
      correlation,
      performance,
      timing,
      risk,
      recommendations
    }
  }

  /**
   * 私有方法：分析相关性
   */
  private analyzeCorrelation(signalsA: StrategySignal[], signalsB: StrategySignal[]) {
    // 整体相关性
    const overall = this.calculateSignalCorrelation(signalsA, signalsB)

    // 按信号类型分析相关性
    const buySignalsA = signalsA.filter(s => s.signalType === 'buy')
    const buySignalsB = signalsB.filter(s => s.signalType === 'buy')
    const buySignal = this.calculateSignalCorrelation(buySignalsA, buySignalsB)

    const sellSignalsA = signalsA.filter(s => s.signalType === 'sell')
    const sellSignalsB = signalsB.filter(s => s.signalType === 'sell')
    const sellSignal = this.calculateSignalCorrelation(sellSignalsA, sellSignalsB)

    // 时机相关性
    const timing = this.calculateTimingCorrelation(signalsA, signalsB)

    return {
      overall,
      buySignal,
      sellSignal,
      timing
    }
  }

  /**
   * 私有方法：分析性能
   */
  private analyzePerformance(signalsA: StrategySignal[], signalsB: StrategySignal[]) {
    // 模拟收益计算（简化版）
    const returnsA = this.calculateSimulatedReturns(signalsA)
    const returnsB = this.calculateSimulatedReturns(signalsB)

    const totalReturns = {
      strategyA: returnsA.total,
      strategyB: returnsB.total,
      difference: returnsA.total - returnsB.total,
      winner: returnsA.total > returnsB.total ? 'A' as const : returnsA.total < returnsB.total ? 'B' as const : 'tie' as const
    }

    const winRates = {
      strategyA: returnsA.winRate,
      strategyB: returnsB.winRate,
      difference: returnsA.winRate - returnsB.winRate,
      winner: returnsA.winRate > returnsB.winRate ? 'A' as const : returnsA.winRate < returnsB.winRate ? 'B' as const : 'tie' as const
    }

    const signalCounts = {
      strategyA: signalsA.length,
      strategyB: signalsB.length,
      difference: signalsA.length - signalsB.length
    }

    return {
      totalReturns,
      winRates,
      signalCounts
    }
  }

  /**
   * 私有方法：分析时机
   */
  private analyzeTiming(signalsA: StrategySignal[], signalsB: StrategySignal[]) {
    const divergencePoints: Array<{
      timestamp: number
      strategyASignal: StrategySignal | null
      strategyBSignal: StrategySignal | null
      difference: 'onlyA' | 'onlyB' | 'opposite'
    }> = []

    // 找出所有信号时间点
    const allTimestamps = new Set([
      ...signalsA.map(s => s.timestamp),
      ...signalsB.map(s => s.timestamp)
    ])

    for (const timestamp of allTimestamps) {
      const signalA = signalsA.find(s => s.timestamp === timestamp) || null
      const signalB = signalsB.find(s => s.timestamp === timestamp) || null

      let difference: 'onlyA' | 'onlyB' | 'opposite' | 'same' = 'same'

      if (signalA && !signalB) {
        difference = 'onlyA'
      } else if (!signalA && signalB) {
        difference = 'onlyB'
      } else if (signalA && signalB && signalA.signalType !== signalB.signalType) {
        // 检查是否为相反信号（买入vs卖出）
        if ((signalA.signalType === 'buy' && signalB.signalType === 'sell') ||
            (signalA.signalType === 'sell' && signalB.signalType === 'buy')) {
          difference = 'opposite'
        }
      }

      if (difference !== 'same') {
        divergencePoints.push({
          timestamp,
          strategyASignal: signalA,
          strategyBSignal: signalB,
          difference
        })
      }
    }

    // 计算平均领先时间
    const averageLeadTime = this.calculateAverageLeadTime(signalsA, signalsB)

    // 计算信号对齐度
    const signalAlignment = 1 - (divergencePoints.length / allTimestamps.size)

    return {
      averageLeadTime,
      signalAlignment,
      divergencePoints
    }
  }

  /**
   * 私有方法：分析风险
   */
  private analyzeRisk(signalsA: StrategySignal[], signalsB: StrategySignal[]) {
    // 信号波动性
    const signalVolatility = {
      strategyA: this.calculateSignalVolatility(signalsA),
      strategyB: this.calculateSignalVolatility(signalsB)
    }

    // 置信度稳定性
    const confidenceStability = {
      strategyA: this.calculateConfidenceStability(signalsA),
      strategyB: this.calculateConfidenceStability(signalsB)
    }

    return {
      signalVolatility,
      confidenceStability
    }
  }

  /**
   * 私有方法：生成建议
   */
  private generateRecommendations(
    correlation: any,
    performance: any,
    timing: any,
    risk: any
  ): string[] {
    const recommendations: string[] = []

    // 基于相关性的建议
    if (correlation.overall > 0.8) {
      recommendations.push('两个策略高度相关，考虑只使用其中一个或组合使用以减少冗余')
    } else if (correlation.overall < 0.2) {
      recommendations.push('两个策略相关性较低，可以考虑组合使用以提高稳定性')
    }

    // 基于性能的建议
    if (performance.totalReturns.difference > 10) {
      recommendations.push(`策略${performance.totalReturns.winner}收益表现显著优于另一个策略`)
    }

    // 基于时机的建议
    if (timing.signalAlignment < 0.5) {
      recommendations.push('策略信号对齐度较低，建议检查参数配置是否合理')
    }

    // 基于风险的建议
    if (risk.signalVolatility.strategyA > risk.signalVolatility.strategyB * 1.5) {
      recommendations.push('策略A的信号波动性较高，建议优化参数或加强风险管理')
    }

    return recommendations
  }

  /**
   * 私有方法：过滤信号
   */
  private filterSignals(signals: StrategySignal[], config?: ComparisonConfig): StrategySignal[] {
    if (!config) {
      return signals
    }

    let filtered = signals

    // 时间范围过滤
    if (config.timeRange) {
      filtered = filtered.filter(s =>
        s.timestamp >= config.timeRange!.start &&
        s.timestamp <= config.timeRange!.end
      )
    }

    // 信号类型过滤
    if (config.signalTypes && config.signalTypes.length > 0) {
      filtered = filtered.filter(s => config.signalTypes!.includes(s.signalType))
    }

    // 置信度过滤
    if (config.confidenceThreshold) {
      filtered = filtered.filter(s => s.confidence >= config.confidenceThreshold!)
    }

    // 排除持有信号
    if (!config.includeHoldSignals) {
      filtered = filtered.filter(s => s.signalType !== 'hold')
    }

    return filtered
  }

  /**
   * 私有方法：计算信号相关性
   */
  private calculateSignalCorrelation(signalsA: StrategySignal[], signalsB: StrategySignal[]): number {
    if (signalsA.length === 0 || signalsB.length === 0) {
      return 0
    }

    const timePoints = new Set([
      ...signalsA.map(s => s.timestamp),
      ...signalsB.map(s => s.timestamp)
    ])

    let matches = 0
    let total = 0

    for (const timestamp of timePoints) {
      const signalA = signalsA.find(s => s.timestamp === timestamp)
      const signalB = signalsB.find(s => s.timestamp === timestamp)

      if (signalA && signalB) {
        total++
        if (signalA.signalType === signalB.signalType) {
          matches++
        }
      }
    }

    return total > 0 ? matches / total : 0
  }

  /**
   * 私有方法：计算时机相关性
   */
  private calculateTimingCorrelation(signalsA: StrategySignal[], signalsB: StrategySignal[]): number {
    // 简化实现：计算信号时间的标准差相关性
    const timesA = signalsA.map(s => s.timestamp).sort()
    const timesB = signalsB.map(s => s.timestamp).sort()

    if (timesA.length < 2 || timesB.length < 2) {
      return 0
    }

    // 计算间隔序列
    const intervalsA = this.calculateIntervals(timesA)
    const intervalsB = this.calculateIntervals(timesB)

    // 计算相关性
    return this.calculatePearsonCorrelation(intervalsA, intervalsB)
  }

  /**
   * 私有方法：计算模拟收益
   */
  private calculateSimulatedReturns(signals: StrategySignal[]) {
    // 简化的收益计算
    let total = 0
    let wins = 0
    let totalTrades = 0

    for (let i = 0; i < signals.length - 1; i += 2) {
      if (i + 1 < signals.length) {
        const entry = signals[i]
        const exit = signals[i + 1]

        if (entry.signalType === 'buy' && exit.signalType === 'sell') {
          const profit = exit.price - entry.price
          total += profit
          totalTrades++

          if (profit > 0) {
            wins++
          }
        }
      }
    }

    return {
      total,
      winRate: totalTrades > 0 ? (wins / totalTrades) * 100 : 0
    }
  }

  /**
   * 私有方法：计算平均领先时间
   */
  private calculateAverageLeadTime(signalsA: StrategySignal[], signalsB: StrategySignal[]): number {
    const leadTimes: number[] = []

    for (const signalA of signalsA) {
      const closestB = signalsB.find(s =>
        Math.abs(s.timestamp - signalA.timestamp) < 60000 // 1分钟内
      )

      if (closestB) {
        leadTimes.push(closestB.timestamp - signalA.timestamp)
      }
    }

    return leadTimes.length > 0 ?
      leadTimes.reduce((sum, time) => sum + time, 0) / leadTimes.length :
      0
  }

  /**
   * 私有方法：计算信号波动性
   */
  private calculateSignalVolatility(signals: StrategySignal[]): number {
    if (signals.length < 2) {
      return 0
    }

    const intervals = this.calculateIntervals(signals.map(s => s.timestamp).sort())
    const mean = intervals.reduce((sum, interval) => sum + interval, 0) / intervals.length
    const variance = intervals.reduce((sum, interval) => sum + Math.pow(interval - mean, 2), 0) / intervals.length

    return Math.sqrt(variance)
  }

  /**
   * 私有方法：计算置信度稳定性
   */
  private calculateConfidenceStability(signals: StrategySignal[]): number {
    if (signals.length === 0) {
      return 0
    }

    const confidences = signals.map(s => s.confidence)
    const mean = confidences.reduce((sum, c) => sum + c, 0) / confidences.length
    const variance = confidences.reduce((sum, c) => sum + Math.pow(c - mean, 2), 0) / confidences.length

    // 稳定性 = 1 - 变异系数
    const cv = mean > 0 ? Math.sqrt(variance) / mean : 0
    return Math.max(0, 1 - cv)
  }

  /**
   * 私有方法：计算时间间隔
   */
  private calculateIntervals(timestamps: number[]): number[] {
    const intervals: number[] = []
    for (let i = 1; i < timestamps.length; i++) {
      intervals.push(timestamps[i] - timestamps[i - 1])
    }
    return intervals
  }

  /**
   * 私有方法：计算皮尔逊相关系数
   */
  private calculatePearsonCorrelation(x: number[], y: number[]): number {
    if (x.length !== y.length || x.length === 0) {
      return 0
    }

    const n = x.length
    const sumX = x.reduce((sum, val) => sum + val, 0)
    const sumY = y.reduce((sum, val) => sum + val, 0)
    const sumXY = x.reduce((sum, val, i) => sum + val * y[i], 0)
    const sumX2 = x.reduce((sum, val) => sum + val * val, 0)
    const sumY2 = y.reduce((sum, val) => sum + val * val, 0)

    const numerator = n * sumXY - sumX * sumY
    const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY))

    return denominator === 0 ? 0 : numerator / denominator
  }

  /**
   * 私有方法：生成对比ID
   */
  private generateComparisonId(strategyAId: string, strategyBId: string): string {
    const sorted = [strategyAId, strategyBId].sort()
    return `${sorted[0]}_vs_${sorted[1]}_${Date.now()}`
  }

  /**
   * 私有方法：生成摘要
   */
  private generateSummary(comparison: ComparisonAnalysis): string {
    const { strategyA, strategyB, correlation, performance } = comparison

    return `
策略对比摘要：
- 策略A (${strategyA.name}) vs 策略B (${strategyB.name})
- 整体相关性: ${(correlation.overall * 100).toFixed(1)}%
- 收益差异: ${performance.totalReturns.difference > 0 ? '+' : ''}${performance.totalReturns.difference.toFixed(2)}
- 胜率差异: ${performance.winRates.difference > 0 ? '+' : ''}${performance.winRates.difference.toFixed(1)}%
- 信号数量差异: ${performance.signalCounts.difference}
    `.trim()
  }

  /**
   * 私有方法：生成详细分析
   */
  private generateDetailedAnalysis(comparison: ComparisonAnalysis): string {
    return `
详细分析：
1. 相关性分析：两个策略在信号生成上${comparison.correlation.overall > 0.7 ? '高度' : comparison.correlation.overall > 0.3 ? '中等' : '低度'}相关
2. 性能表现：策略${performance.totalReturns.winner}在收益方面表现更优
3. 时机分析：信号对齐度为${(comparison.timing.signalAlignment * 100).toFixed(1)}%
4. 风险评估：策略A的信号波动性${comparison.risk.signalVolatility.strategyA > comparison.risk.signalVolatility.strategyB ? '高于' : '低于'}策略B
    `.trim()
  }
}

// 导出单例实例
export const strategyComparisonService = new StrategyComparisonService()