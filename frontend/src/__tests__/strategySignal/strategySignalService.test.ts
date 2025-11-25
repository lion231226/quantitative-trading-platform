import {
  StrategySignalManager,
  strategySignalManager
} from '../../services/strategySignalService'
import {
  StrategySignal,
  StrategyType,
  SignalType,
  PRESET_STRATEGIES
} from '../../types/strategySignal.types'
import { KlineData, CandlestickData } from '../../types/kline.types'

// 模拟数据生成器
class MockDataGenerator {
  static generateKlineData(count: number): KlineData {
    const candlesticks: CandlestickData[] = []
    const now = Date.now()
    let lastClose = 100

    for (let i = count - 1; i >= 0; i--) {
      const timestamp = new Date(now - i * 24 * 60 * 60 * 1000).toISOString()
      const change = (Math.random() - 0.5) * 10
      const open = lastClose + change
      const close = open + (Math.random() - 0.5) * 5
      const high = Math.max(open, close) + Math.random() * 3
      const low = Math.min(open, close) - Math.random() * 3
      const volume = Math.floor(Math.random() * 1000000)

      candlesticks.push({
        timestamp,
        open: Math.max(1, open),
        high: Math.max(1, high),
        low: Math.max(1, low),
        close: Math.max(1, close),
        volume
      })

      lastClose = close
    }

    return { candlesticks }
  }

  static generateStrategySignal(
    id: string,
    timestamp: number,
    price: number,
    signalType: SignalType,
    strategyId: string,
    confidence: number = 75
  ): StrategySignal {
    return {
      id,
      timestamp,
      price,
      signalType,
      confidence,
      strategyId,
      strategyName: `Test Strategy ${strategyId}`,
      strategyType: 'sma_crossover' as StrategyType,
      strength: 'moderate',
      strategyParams: {},
      marketData: {
        open: price - 1,
        high: price + 2,
        low: price - 2,
        close: price
      },
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
  }
}

describe('StrategySignalManager', () => {
  let signalManager: StrategySignalManager

  beforeEach(() => {
    signalManager = new StrategySignalManager(10, 5000) // 小缓存用于测试
  })

  afterEach(() => {
    signalManager.clearCache()
  })

  describe('loadSignals', () => {
    it('应该成功加载SMA金叉死叉策略信号', async () => {
      const strategyId = 'sma_crossover'
      const params = { shortPeriod: 10, longPeriod: 30 }
      const symbol = 'TEST'
      const period = '1d' as any
      const data = MockDataGenerator.generateKlineData(100)

      const result = await signalManager.loadSignals(strategyId, params, symbol, period, data)

      expect(result).toBeDefined()
      expect(result.strategyId).toBe(strategyId)
      expect(result.signals).toBeDefined()
      expect(Array.isArray(result.signals)).toBe(true)
      expect(result.performance).toBeDefined()
      expect(result.performance.signalCount).toBe(result.signals.length)
      expect(result.performance.calculationTime).toBeGreaterThan(0)
    })

    it('应该正确计算RSI超卖策略信号', async () => {
      const strategyId = 'rsi_oversold'
      const params = { period: 14, oversoldThreshold: 30 }
      const symbol = 'TEST'
      const period = '1d' as any
      const data = MockDataGenerator.generateKlineData(50)

      const result = await signalManager.loadSignals(strategyId, params, symbol, period, data)

      expect(result.strategyId).toBe(strategyId)
      expect(result.signals.every(signal => signal.signalType === 'buy')).toBe(true)
      expect(result.signals.every(signal => signal.strategyType === 'rsi_oversold')).toBe(true)
    })

    it('应该缓存计算结果', async () => {
      const strategyId = 'sma_crossover'
      const params = { shortPeriod: 10, longPeriod: 30 }
      const symbol = 'TEST'
      const period = '1d' as any
      const data = MockDataGenerator.generateKlineData(100)

      // 第一次计算
      const startTime = performance.now()
      const result1 = await signalManager.loadSignals(strategyId, params, symbol, period, data)
      const firstTime = performance.now() - startTime

      // 第二次计算（应该从缓存获取）
      const startTime2 = performance.now()
      const result2 = await signalManager.loadSignals(strategyId, params, symbol, period, data)
      const secondTime = performance.now() - startTime2

      expect(result1.signals).toEqual(result2.signals)
      expect(result2.performance.cacheHit).toBe(true)
      expect(secondTime).toBeLessThan(firstTime) // 缓存应该更快
    })

    it('应该处理无效策略ID', async () => {
      const strategyId = 'invalid_strategy'
      const params = {}
      const symbol = 'TEST'
      const period = '1d' as any
      const data = MockDataGenerator.generateKlineData(100)

      await expect(
        signalManager.loadSignals(strategyId, params, symbol, period, data)
      ).rejects.toThrow('未找到策略配置')
    })

    it('应该处理数据不足的情况', async () => {
      const strategyId = 'sma_crossover'
      const params = { shortPeriod: 50, longPeriod: 100 }
      const symbol = 'TEST'
      const period = '1d' as any
      const data = MockDataGenerator.generateKlineData(30) // 数据不足以计算长期均线

      const result = await signalManager.loadSignals(strategyId, params, symbol, period, data)

      expect(result.signals.length).toBe(0)
      expect(result.performance.signalCount).toBe(0)
    })
  })

  describe('calculateDifference', () => {
    it('应该正确计算信号差异', () => {
      const oldSignals = [
        MockDataGenerator.generateStrategySignal('1', Date.now(), 100, 'buy', 'sma_1'),
        MockDataGenerator.generateStrategySignal('2', Date.now() + 1000, 101, 'sell', 'sma_1')
      ]

      const newSignals = [
        MockDataGenerator.generateStrategySignal('1', Date.now(), 100, 'buy', 'sma_1'), // 相同
        MockDataGenerator.generateStrategySignal('3', Date.now() + 2000, 102, 'buy', 'sma_1'), // 新增
        MockDataGenerator.generateStrategySignal('2', Date.now() + 1000, 101, 'sell', 'sma_1')  // 相同
      ]

      const difference = signalManager.calculateDifference(oldSignals, newSignals)

      expect(difference.added).toHaveLength(1)
      expect(difference.added[0].id).toBe('3')
      expect(difference.removed).toHaveLength(0)
      expect(difference.modified).toHaveLength(0)
    })

    it('应该检测到修改的信号', () => {
      const baseSignal = MockDataGenerator.generateStrategySignal('1', Date.now(), 100, 'buy', 'sma_1')
      const modifiedSignal = {
        ...baseSignal,
        confidence: 90,
        price: 101
      }

      const difference = signalManager.calculateDifference([baseSignal], [modifiedSignal])

      expect(difference.added).toHaveLength(0)
      expect(difference.removed).toHaveLength(0)
      expect(difference.modified).toHaveLength(1)
      expect(difference.modified[0].old.confidence).toBe(75)
      expect(difference.modified[0].new.confidence).toBe(90)
    })

    it('应该检测到移除的信号', () => {
      const oldSignals = [
        MockDataGenerator.generateStrategySignal('1', Date.now(), 100, 'buy', 'sma_1'),
        MockDataGenerator.generateStrategySignal('2', Date.now(), 1000, 101, 'sell', 'sma_1')
      ]

      const newSignals = [
        MockDataGenerator.generateStrategySignal('1', Date.now(), 100, 'buy', 'sma_1')
      ]

      const difference = signalManager.calculateDifference(oldSignals, newSignals)

      expect(difference.added).toHaveLength(0)
      expect(difference.removed).toHaveLength(1)
      expect(difference.removed[0].id).toBe('2')
      expect(difference.modified).toHaveLength(0)
    })
  })

  describe('optimizeSignals', () => {
    it('应该正确应用过滤条件', () => {
      const signals = [
        MockDataGenerator.generateStrategySignal('1', Date.now(), 100, 'buy', 'sma_1'),
        MockDataGenerator.generateStrategySignal('2', Date.now() + 1000, 101, 'sell', 'sma_1'),
        MockDataGenerator.generateStrategySignal('3', Date.now() + 2000, 102, 'hold', 'sma_1')
      ]

      const filter = {
        signalTypes: ['buy' as SignalType]
      }

      const optimized = signalManager.optimizeSignals(signals, filter)

      expect(optimized).toHaveLength(1)
      expect(optimized[0].signalType).toBe('buy')
    })

    it('应该按时间戳排序', () => {
      const signals = [
        MockDataGenerator.generateStrategySignal('3', Date.now() + 2000, 102, 'buy', 'sma_1'),
        MockDataGenerator.generateStrategySignal('1', Date.now(), 100, 'buy', 'sma_1'),
        MockDataGenerator.generateStrategySignal('2', Date.now() + 1000, 101, 'buy', 'sma_1')
      ]

      const optimized = signalManager.optimizeSignals(signals)

      expect(optimized[0].timestamp).toBeLessThan(optimized[1].timestamp)
      expect(optimized[1].timestamp).toBeLessThan(optimized[2].timestamp)
    })

    it('应该移除重复信号', () => {
      const duplicateSignal = MockDataGenerator.generateStrategySignal('1', Date.now(), 100, 'buy', 'sma_1')
      const signals = [
        duplicateSignal,
        { ...duplicateSignal, id: '2' }, // 相同内容，不同ID
        duplicateSignal // 完全重复
      ]

      const optimized = signalManager.optimizeSignals(signals)

      expect(optimized).toHaveLength(2) // 应该移除一个重复项
      expect(optimized.map(s => s.id)).not.toContain('1') // 其中一个1被移除
    })
  })

  describe('getStatistics', () => {
    it('应该正确计算信号统计', () => {
      const signals = [
        MockDataGenerator.generateStrategySignal('1', Date.now(), 100, 'buy', 'sma_1', 80),
        MockDataGenerator.generateStrategySignal('2', Date.now() + 1000, 101, 'sell', 'sma_1', 60),
        MockDataGenerator.generateStrategySignal('3', Date.now() + 2000, 102, 'buy', 'sma_1', 90),
        MockDataGenerator.generateStrategySignal('4', Date.now() + 3000, 103, 'hold', 'sma_1', 70)
      ]

      const stats = signalManager.getStatistics(signals)

      expect(stats.totalSignals).toBe(4)
      expect(stats.signalCounts.buy).toBe(2)
      expect(stats.signalCounts.sell).toBe(1)
      expect(stats.signalCounts.hold).toBe(1)
      expect(stats.strategyCounts['sma_1']).toBe(4)
      expect(stats.confidenceDistribution.strong).toBe(2) // 80, 90
      expect(stats.confidenceDistribution.moderate).toBe(2) // 60, 70
    })

    it('应该处理空信号列表', () => {
      const stats = signalManager.getStatistics([])

      expect(stats.totalSignals).toBe(0)
      expect(stats.signalCounts.buy).toBe(0)
      expect(stats.signalCounts.sell).toBe(0)
      expect(Object.keys(stats.strategyCounts)).toHaveLength(0)
    })
  })

  describe('compareSignals', () => {
    it('应该正确比较两组信号', () => {
      const commonSignal = MockDataGenerator.generateStrategySignal('1', Date.now(), 100, 'buy', 'sma_1')
      const signalsA = [
        commonSignal,
        MockDataGenerator.generateStrategySignal('2', Date.now() + 1000, 101, 'sell', 'sma_1')
      ]

      const signalsB = [
        commonSignal,
        MockDataGenerator.generateStrategySignal('3', Date.now() + 2000, 102, 'buy', 'sma_2')
      ]

      const comparison = signalManager.compareSignals(signalsA, signalsB)

      expect(comparison.common).toHaveLength(1)
      expect(comparison.uniqueA).toHaveLength(1)
      expect(comparison.uniqueB).toHaveLength(1)
      expect(comparison.correlation).toBeGreaterThanOrEqual(0)
      expect(comparison.correlation).toBeLessThanOrEqual(1)
    })

    it('应该处理空信号对比', () => {
      const signals = [MockDataGenerator.generateStrategySignal('1', Date.now(), 100, 'buy', 'sma_1')]
      const emptySignals: StrategySignal[] = []

      const comparison = signalManager.compareSignals(signals, emptySignals)

      expect(comparison.common).toHaveLength(0)
      expect(comparison.uniqueA).toHaveLength(1)
      expect(comparison.uniqueB).toHaveLength(0)
      expect(comparison.correlation).toBe(0)
    })
  })

  describe('缓存管理', () => {
    it('应该正确管理缓存大小限制', async () => {
      const signalManager = new StrategySignalManager(2, 5000) // 最大2个缓存项
      const data = MockDataGenerator.generateKlineData(50)

      // 添加超过限制的缓存项
      await signalManager.loadSignals('sma_crossover', { shortPeriod: 5, longPeriod: 10 }, 'TEST', '1d', data)
      await signalManager.loadSignals('sma_crossover', { shortPeriod: 10, longPeriod: 20 }, 'TEST', '1d', data)
      await signalManager.loadSignals('sma_crossover', { shortPeriod: 15, longPeriod: 30 }, 'TEST', '1d', data)

      // 最旧的缓存项应该被移除
      const oldCacheKey = signalManager['generateCacheKey']('sma_crossover', { shortPeriod: 5, longPeriod: 10 }, 'TEST', '1d')
      expect(signalManager.getCachedSignals(oldCacheKey)).toBeNull()
    })

    it('应该正确清理过期缓存', async () => {
      const signalManager = new StrategySignalManager(10, 100) // 100ms TTL
      const data = MockDataGenerator.generateKlineData(50)

      const cacheKey = signalManager['generateCacheKey']('sma_crossover', { shortPeriod: 10, longPeriod: 30 }, 'TEST', '1d')

      await signalManager.loadSignals('sma_crossover', { shortPeriod: 10, longPeriod: 30 }, 'TEST', '1d', data)

      // 立即检查应该存在
      expect(signalManager.getCachedSignals(cacheKey)).toBeTruthy()

      // 等待过期
      await new Promise(resolve => setTimeout(resolve, 150))

      // 现在应该被清理
      expect(signalManager.getCachedSignals(cacheKey)).toBeNull()
    })
  })
})

describe('PRESET_STRATEGIES', () => {
  it('应该包含预期的预设策略', () => {
    expect(PRESET_STRATEGIES).toHaveProperty('sma_crossover')
    expect(PRESET_STRATEGIES).toHaveProperty('rsi_oversold')
  })

  it('预设策略应该有必要的属性', () => {
    const smaStrategy = PRESET_STRATEGIES['sma_crossover']

    expect(smaStrategy.name).toBeDefined()
    expect(smaStrategy.type).toBe('sma_crossover')
    expect(smaStrategy.params).toBeDefined()
    expect(smaStrategy.styles).toBeDefined()
    expect(smaStrategy.styles.buy).toBeDefined()
    expect(smaStrategy.styles.sell).toBeDefined()
  })

  it('预设策略参数应该有正确的类型和默认值', () => {
    const smaStrategy = PRESET_STRATEGIES['sma_crossover']

    expect(smaStrategy.params.shortPeriod.type).toBe('number')
    expect(smaStrategy.params.shortPeriod.default).toBe(10)
    expect(smaStrategy.params.shortPeriod.min).toBe(1)
    expect(smaStrategy.params.shortPeriod.max).toBe(50)
  })
})