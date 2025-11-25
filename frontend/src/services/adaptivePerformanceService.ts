import { KlineConfig, CandlestickData, KlineChartEvent } from '../types/kline.types'
import { KlineDataSampler } from '../utils/klineHelpers'

/**
 * 性能指标接口
 */
export interface PerformanceMetrics {
  fps: number
  renderTime: number
  memoryUsage: number
  dataPoints: number
  timestamp: number
}

/**
 * 自适应策略配置
 */
export interface AdaptiveStrategy {
  name: string
  priority: number
  condition: (metrics: PerformanceMetrics) => boolean
  action: (config: KlineConfig, data: CandlestickData[]) => {
    config: KlineConfig
    data: CandlestickData[]
    description: string
  }
}

/**
 * 自适应性能优化服务
 */
export class AdaptivePerformanceService {
  private strategies: AdaptiveStrategy[] = []
  private metricsHistory: PerformanceMetrics[] = []
  private isOptimizationEnabled = true
  private optimizationInterval = 5000 // 5秒检查一次

  constructor() {
    this.initializeStrategies()
  }

  /**
   * 初始化自适应策略
   */
  private initializeStrategies(): void {
    this.strategies = [
      // 策略1: 大数据量自动采样
      {
        name: '大数据量采样',
        priority: 1,
        condition: (metrics) => metrics.dataPoints > 10000 && metrics.fps < 30,
        action: (config, data) => {
          const maxPoints = Math.min(5000, Math.floor(data.length * 0.6))
          const sampledData = KlineDataSampler.sample(data, maxPoints, true)

          return {
            config: {
              ...config,
              performance: {
                ...config.performance,
                enableDataSampling: true,
                maxDataPoints: maxPoints
              }
            },
            data: sampledData,
            description: `数据采样: ${data.length} → ${sampledData.length} 数据点 (${((sampledData.length / data.length) * 100).toFixed(1)}%)`
          }
        }
      },

      // 策略2: 关闭动画提升性能
      {
        name: '关闭动画',
        priority: 2,
        condition: (metrics) => metrics.fps < 20 && metrics.renderTime > 50,
        action: (config, data) => ({
          config: {
            ...config,
            performance: {
              ...config.performance,
              enableAnimation: false,
              animationDuration: 0
            }
          },
          data,
          description: '禁用动画以提升渲染性能'
        })
      },

      // 策略3: 降低数据精度
      {
        name: '降低数据精度',
        priority: 3,
        condition: (metrics) => metrics.dataPoints > 50000 && metrics.fps < 15,
        action: (config, data) => {
          const maxPoints = Math.min(2000, Math.floor(data.length * 0.3))
          const sampledData = KlineDataSampler.sample(data, maxPoints, false) // 均匀采样

          return {
            config: {
              ...config,
              performance: {
                ...config.performance,
                enableDataSampling: true,
                maxDataPoints: maxPoints
              }
            },
            data: sampledData,
            description: `激进数据采样: ${data.length} → ${sampledData.length} 数据点`
          }
        }
      },

      // 策略4: 禁用成交量图表
      {
        name: '禁用成交量',
        priority: 4,
        condition: (metrics) => metrics.fps < 10 && metrics.renderTime > 100,
        action: (config, data) => ({
          config: {
            ...config,
            showVolume: false
          },
          data,
          description: '禁用成交量显示以减少渲染负担',
        })
      },

      // 策略5: 关闭移动平均线
      {
        name: '简化显示',
        priority: 5,
        condition: (metrics) => metrics.fps < 10 && metrics.renderTime > 150,
        action: (config, data) => ({
          config: {
            ...config,
            showMovingAverages: false,
            showSignals: false,
            showGrid: false,
            showCrosshair: false
          },
          data,
          description: '简化显示元素以最大化性能',
        })
      }
    ]
  }

  /**
   * 添加自定义策略
   */
  addStrategy(strategy: AdaptiveStrategy): void {
    this.strategies.push(strategy)
    // 按优先级排序
    this.strategies.sort((a, b) => a.priority - b.priority)
  }

  /**
   * 记录性能指标
   */
  recordMetrics(metrics: PerformanceMetrics): void {
    this.metricsHistory.push(metrics)

    // 保持历史记录在合理范围内（最近100条）
    if (this.metricsHistory.length > 100) {
      this.metricsHistory = this.metricsHistory.slice(-100)
    }

    // 自动执行优化
    if (this.isOptimizationEnabled) {
      this.performAutoOptimization(metrics)
    }
  }

  /**
   * 执行自动优化
   */
  private performAutoOptimization(currentMetrics: PerformanceMetrics): void {
    // 查找适用的策略
    const applicableStrategies = this.strategies.filter(strategy =>
      strategy.condition(currentMetrics)
    )

    if (applicableStrategies.length === 0) {
      return
    }

    // 应用优先级最高的策略
    const strategy = applicableStrategies[0]

    console.log(`🔧 触发自适应优化策略: ${strategy.name}`)

    // 触发优化事件
    this.emitOptimizationEvent(strategy, currentMetrics)
  }

  /**
   * 触发优化事件
   */
  private emitOptimizationEvent(strategy: AdaptiveStrategy, metrics: PerformanceMetrics): void {
    const event = new CustomEvent('klinePerformanceOptimization', {
      detail: {
        strategy: strategy.name,
        metrics,
        timestamp: Date.now()
      }
    })

    window.dispatchEvent(event)
  }

  /**
   * 手动优化配置
   */
  optimize(
    config: KlineConfig,
    data: CandlestickData[],
    currentMetrics: PerformanceMetrics
  ): { config: KlineConfig; data: CandlestickData[]; appliedStrategies: string[] } {
    if (!this.isOptimizationEnabled) {
      return { config, data, appliedStrategies: [] }
    }

    let optimizedConfig = { ...config }
    let optimizedData = [...data]
    const appliedStrategies: string[] = []

    // 按优先级应用策略
    const applicableStrategies = this.strategies.filter(strategy =>
      strategy.condition(currentMetrics)
    )

    for (const strategy of applicableStrategies) {
      try {
        const result = strategy.action(optimizedConfig, optimizedData)
        optimizedConfig = result.config
        optimizedData = result.data
        appliedStrategies.push(`${strategy.name}: ${result.description}`)
      } catch (error) {
        console.error(`应用策略 ${strategy.name} 时出错:`, error)
      }
    }

    return {
      config: optimizedConfig,
      data: optimizedData,
      appliedStrategies
    }
  }

  /**
   * 获取性能趋势分析
   */
  getPerformanceTrend(): {
    trend: 'improving' | 'declining' | 'stable'
    averageFps: number
    averageRenderTime: number
    recommendations: string[]
  } {
    if (this.metricsHistory.length < 10) {
      return {
        trend: 'stable',
        averageFps: 0,
        averageRenderTime: 0,
        recommendations: ['需要更多数据进行分析']
      }
    }

    const recentMetrics = this.metricsHistory.slice(-10)
    const olderMetrics = this.metricsHistory.slice(-20, -10)

    const recentAvgFps = recentMetrics.reduce((sum, m) => sum + m.fps, 0) / recentMetrics.length
    const recentAvgRenderTime = recentMetrics.reduce((sum, m) => sum + m.renderTime, 0) / recentMetrics.length

    let trend: 'improving' | 'declining' | 'stable' = 'stable'
    const recommendations: string[] = []

    if (olderMetrics.length > 0) {
      const olderAvgFps = olderMetrics.reduce((sum, m) => sum + m.fps, 0) / olderMetrics.length
      const olderAvgRenderTime = olderMetrics.reduce((sum, m) => sum + m.renderTime, 0) / olderMetrics.length

      if (recentAvgFps > olderAvgFps + 5) {
        trend = 'improving'
        recommendations.push('性能正在改善，继续当前优化策略')
      } else if (recentAvgFps < olderAvgFps - 5) {
        trend = 'declining'
        recommendations.push('性能正在下降，建议检查数据量或减少显示元素')
      } else {
        trend = 'stable'
      }

      if (recentAvgRenderTime > olderAvgRenderTime + 10) {
        trend = 'declining'
        recommendations.push('渲染时间增加，建议启用数据采样')
      }
    }

    // 基于当前性能的通用建议
    if (recentAvgFps < 30) {
      recommendations.push('考虑减少数据点数量或启用智能采样')
    }
    if (recentAvgRenderTime > 50) {
      recommendations.push('考虑禁用动画或简化图表显示')
    }

    return {
      trend,
      averageFps: recentAvgFps,
      averageRenderTime: recentAvgRenderTime,
      recommendations
    }
  }

  /**
   * 启用/禁用自适应优化
   */
  setOptimizationEnabled(enabled: boolean): void {
    this.isOptimizationEnabled = enabled
    console.log(`自适应性能优化已${enabled ? '启用' : '禁用'}`)
  }

  /**
   * 设置优化检查间隔
   */
  setOptimizationInterval(intervalMs: number): void {
    this.optimizationInterval = intervalMs
  }

  /**
   * 获取当前配置
   */
  getConfiguration(): {
    enabled: boolean
    interval: number
    strategiesCount: number
    metricsHistoryLength: number
  } {
    return {
      enabled: this.isOptimizationEnabled,
      interval: this.optimizationInterval,
      strategiesCount: this.strategies.length,
      metricsHistoryLength: this.metricsHistory.length
    }
  }

  /**
   * 清除历史数据
   */
  clearHistory(): void {
    this.metricsHistory = []
  }

  /**
   * 重置为默认策略
   */
  resetStrategies(): void {
    this.strategies = []
    this.initializeStrategies()
  }
}

// 导出单例实例
export const adaptivePerformanceService = new AdaptivePerformanceService()