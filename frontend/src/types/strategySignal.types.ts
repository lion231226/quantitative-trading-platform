// 策略信号系统类型定义
import { TimePeriod } from './kline.types'

// 策略信号类型
export type SignalType = 'buy' | 'sell' | 'hold' | 'stop_loss' | 'take_profit'

// 策略信号强度
export type SignalStrength = 'weak' | 'moderate' | 'strong' | 'very_strong'

// 策略类型
export type StrategyType = 'sma_crossover' | 'ema_crossover' | 'rsi_oversold' | 'rsi_overbought' | 'macd_crossover' | 'bollinger_bands' | 'custom'

// 标记点形状
export type MarkerShape = 'circle' | 'square' | 'triangle' | 'arrow_up' | 'arrow_down' | 'diamond' | 'star'

// 策略信号接口
export interface StrategySignal {
  // 基础信息
  id: string
  timestamp: number
  price: number

  // 信号信息
  signalType: SignalType
  strength: SignalStrength
  confidence: number // 0-100

  // 策略信息
  strategyId: string
  strategyName: string
  strategyType: StrategyType
  strategyParams: Record<string, any>

  // 市场数据
  volume?: number
  marketData?: {
    open: number
    high: number
    low: number
    close: number
  }

  // 元数据
  metadata?: {
    indicator?: string
    period?: number
    description?: string
    tags?: string[]
    relatedSignals?: string[] // 相关信号ID
  }

  // 时间戳
  createdAt: number
  updatedAt: number
}

// 策略信号标记点样式
export interface SignalMarkerStyle {
  // 基础样式
  shape: MarkerShape
  color: string
  size: number
  opacity: number

  // 边框样式
  border: {
    color: string
    width: number
    style?: 'solid' | 'dashed' | 'dotted'
  }

  // 文字样式
  textColor?: string
  fontSize?: number
  fontWeight?: string
  textOffset?: {
    x: number
    y: number
  }

  // 悬停样式
  hover?: {
    scale: number
    color?: string
    border?: {
      color: string
      width: number
    }
  }

  // 动画样式
  animation?: {
    fadeIn?: boolean
    duration?: number
    delay?: number
    easing?: string
  }
}

// 策略配置
export interface StrategyConfig {
  id: string
  name: string
  type: StrategyType
  description: string

  // 参数配置
  params: {
    [key: string]: {
      type: 'number' | 'string' | 'boolean' | 'select'
      default: any
      min?: number
      max?: number
      step?: number
      options?: any[]
      description: string
    }
  }

  // 样式配置
  styles: {
    buy: SignalMarkerStyle
    sell: SignalMarkerStyle
    hold?: SignalMarkerStyle
    stopLoss?: SignalMarkerStyle
    takeProfit?: SignalMarkerStyle
  }

  // 性能配置
  performance: {
    maxSignals: number
    updateInterval: number // 毫秒
    enableCaching: boolean
  }
}

// 策略参数
export interface StrategyParams {
  [key: string]: any
}

// 策略信号计算结果
export interface StrategySignalResult {
  strategyId: string
  signals: StrategySignal[]
  performance: {
    calculationTime: number
    signalCount: number
    cacheHit: boolean
  }
  metadata: {
    generatedAt: number
    dataRange: {
      start: number
      end: number
    }
    params: StrategyParams
  }
}

// 信号更新差异
export interface SignalDifference {
  added: StrategySignal[]    // 新增的信号
  removed: StrategySignal[]  // 移除的信号
  modified: {               // 修改的信号
    old: StrategySignal
    new: StrategySignal
  }[]
}

// 信号缓存项
export interface SignalCacheItem {
  key: string
  signals: StrategySignal[]
  result: StrategySignalResult
  timestamp: number
  expiresAt: number
}

// 信号过滤条件
export interface SignalFilter {
  signalTypes?: SignalType[]
  strategyTypes?: StrategyType[]
  confidenceRange?: {
    min: number
    max: number
  }
  priceRange?: {
    min: number
    max: number
  }
  timeRange?: {
    start: number
    end: number
  }
  strategies?: string[]
}

// 信号统计信息
export interface SignalStatistics {
  totalSignals: number
  signalCounts: {
    [signalType in SignalType]: number
  }
  strategyCounts: Record<string, number>
  timeDistribution: {
    [hour: number]: number
  }
  confidenceDistribution: {
    weak: number
    moderate: number
    strong: number
    very_strong: number
  }
}

// 信号对比数据
export interface SignalComparison {
  strategyA: {
    id: string
    name: string
    signals: StrategySignal[]
  }
  strategyB: {
    id: string
    name: string
    signals: StrategySignal[]
  }
  common: StrategySignal[]     // 共同信号
  uniqueA: StrategySignal[]    // A独有的信号
  uniqueB: StrategySignal[]    // B独有的信号
  correlation: number         // 相关性系数
}

// 策略信号管理器接口
export interface IStrategySignalManager {
  // 信号管理
  loadSignals(strategyId: string, params: StrategyParams): Promise<StrategySignalResult>
  updateSignals(chartId: string, strategyId: string): Promise<void>
  removeSignals(chartId: string, strategyId: string): Promise<void>

  // 缓存管理
  getCachedSignals(key: string): SignalCacheItem | null
  setCachedSignals(key: string, result: StrategySignalResult, ttl?: number): void
  clearCache(): void

  // 差异计算
  calculateDifference(oldSignals: StrategySignal[], newSignals: StrategySignal[]): SignalDifference

  // 性能优化
  optimizeSignals(signals: StrategySignal[], filter?: SignalFilter): StrategySignal[]

  // 统计分析
  getStatistics(signals: StrategySignal[]): SignalStatistics
  compareSignals(signalsA: StrategySignal[], signalsB: StrategySignal[]): SignalComparison
}

// 信号标记点渲染器接口
export interface ISignalRenderer {
  // 标记点操作
  addMarkers(chartId: string, signals: StrategySignal[]): Promise<void>
  removeMarkers(chartId: string, signalIds: string[]): Promise<void>
  updateMarkers(chartId: string, signals: StrategySignal[]): Promise<void>
  clearMarkers(chartId: string): Promise<void>

  // 动画控制
  animateMarkerTransition(chartId: string, diff: SignalDifference): Promise<void>

  // 批量操作
  batchUpdateMarkers(chartId: string, operations: MarkerOperation[]): Promise<void>
}

// 标记点操作类型
export type MarkerOperation =
  | { type: 'add'; signal: StrategySignal }
  | { type: 'remove'; signalId: string }
  | { type: 'update'; signal: StrategySignal }
  | { type: 'clear' }

// 信号事件类型
export type SignalEvent =
  | { type: 'SIGNAL_ADDED'; payload: { signal: StrategySignal } }
  | { type: 'SIGNAL_REMOVED'; payload: { signalId: string } }
  | { type: 'SIGNAL_UPDATED'; payload: { oldSignal: StrategySignal; newSignal: StrategySignal } }
  | { type: 'STRATEGY_CHANGED'; payload: { strategyId: string; oldSignals: StrategySignal[]; newSignals: StrategySignal[] } }
  | { type: 'SIGNAL_FILTERED'; payload: { signals: StrategySignal[]; filter: SignalFilter } }
  | { type: 'CACHE_UPDATED'; payload: { key: string; signals: StrategySignal[] } }

// 预设策略配置
export const PRESET_STRATEGIES: Record<string, Omit<StrategyConfig, 'id'>> = {
  sma_crossover: {
    name: 'SMA金叉死叉',
    type: 'sma_crossover',
    description: '基于简单移动平均线的金叉买入、死叉卖出策略',
    params: {
      shortPeriod: {
        type: 'number',
        default: 10,
        min: 1,
        max: 50,
        description: '短期均线周期'
      },
      longPeriod: {
        type: 'number',
        default: 30,
        min: 1,
        max: 200,
        description: '长期均线周期'
      }
    },
    styles: {
      buy: {
        shape: 'arrow_up',
        color: '#00ff00',
        size: 12,
        opacity: 0.8,
        border: { color: '#00cc00', width: 2 },
        textColor: '#ffffff',
        fontSize: 10
      },
      sell: {
        shape: 'arrow_down',
        color: '#ff0000',
        size: 12,
        opacity: 0.8,
        border: { color: '#cc0000', width: 2 },
        textColor: '#ffffff',
        fontSize: 10
      }
    },
    performance: {
      maxSignals: 1000,
      updateInterval: 500,
      enableCaching: true
    }
  },

  rsi_oversold: {
    name: 'RSI超卖',
    type: 'rsi_oversold',
    description: 'RSI指标超卖区域买入策略',
    params: {
      period: {
        type: 'number',
        default: 14,
        min: 5,
        max: 30,
        description: 'RSI计算周期'
      },
      oversoldThreshold: {
        type: 'number',
        default: 30,
        min: 10,
        max: 40,
        description: '超卖阈值'
      }
    },
    styles: {
      buy: {
        shape: 'circle',
        color: '#00aaff',
        size: 10,
        opacity: 0.7,
        border: { color: '#0088cc', width: 2 }
      }
    },
    performance: {
      maxSignals: 500,
      updateInterval: 300,
      enableCaching: true
    }
  }
}

// 默认样式主题
export const DEFAULT_SIGNAL_THEMES = {
  light: {
    buy: {
      shape: 'arrow_up' as MarkerShape,
      color: '#10b981',
      size: 12,
      opacity: 0.9,
      border: { color: '#059669', width: 2 },
      textColor: '#ffffff',
      fontSize: 10
    },
    sell: {
      shape: 'arrow_down' as MarkerShape,
      color: '#ef4444',
      size: 12,
      opacity: 0.9,
      border: { color: '#dc2626', width: 2 },
      textColor: '#ffffff',
      fontSize: 10
    },
    hold: {
      shape: 'diamond' as MarkerShape,
      color: '#6b7280',
      size: 10,
      opacity: 0.6,
      border: { color: '#4b5563', width: 1 }
    }
  },

  dark: {
    buy: {
      shape: 'arrow_up' as MarkerShape,
      color: '#34d399',
      size: 12,
      opacity: 0.9,
      border: { color: '#10b981', width: 2 },
      textColor: '#111827',
      fontSize: 10
    },
    sell: {
      shape: 'arrow_down' as MarkerShape,
      color: '#f87171',
      size: 12,
      opacity: 0.9,
      border: { color: '#ef4444', width: 2 },
      textColor: '#111827',
      fontSize: 10
    },
    hold: {
      shape: 'diamond' as MarkerShape,
      color: '#9ca3af',
      size: 10,
      opacity: 0.6,
      border: { color: '#6b7280', width: 1 }
    }
  }
}

// 工具函数
export const StrategySignalUtils = {
  // 生成信号ID
  generateSignalId(strategyId: string, timestamp: number, price: number): string {
    return `${strategyId}_${timestamp}_${Math.floor(price * 100)}_${Date.now()}`
  },

  // 生成缓存键
  generateCacheKey(strategyId: string, params: StrategyParams, symbol: string, period: TimePeriod): string {
    const paramString = Object.keys(params)
      .sort()
      .map(key => `${key}:${params[key]}`)
      .join('|')
    return `${strategyId}_${symbol}_${period}_${paramString}`
  },

  // 验证信号完整性
  validateSignal(signal: StrategySignal): boolean {
    return !!(
      signal.id &&
      signal.timestamp &&
      signal.price &&
      signal.signalType &&
      signal.strategyId &&
      signal.strategyName &&
      signal.confidence >= 0 &&
      signal.confidence <= 100
    )
  },

  // 计算信号价格偏移
  calculatePriceOffset(basePrice: number, offsetPercent: number = 0.02): number {
    return basePrice * (1 + offsetPercent)
  },

  // 格式化信号标签
  formatSignalLabel(signal: StrategySignal): string {
    const confidence = Math.round(signal.confidence)
    return `${signal.signalType.toUpperCase()}\n${confidence}%`
  },

  // 获取信号颜色
  getSignalColor(signalType: SignalType, theme: 'light' | 'dark' = 'light'): string {
    const colors = {
      light: {
        buy: '#10b981',
        sell: '#ef4444',
        hold: '#6b7280',
        stop_loss: '#f59e0b',
        take_profit: '#8b5cf6'
      },
      dark: {
        buy: '#34d399',
        sell: '#f87171',
        hold: '#9ca3af',
        stop_loss: '#fbbf24',
        take_profit: '#a78bfa'
      }
    }

    return colors[theme][signalType] || colors[theme].hold
  }
}