// K线图相关类型定义
import { PricePoint, TradingSignal } from './chart.types'

// 扩展价格数据点，包含成交量
export interface CandlestickData extends PricePoint {
  volume: number
}

// K线图数据结构
export interface KlineData {
  candlesticks: CandlestickData[]
  signals?: TradingSignal[]
  movingAverages?: {
    sma?: Array<{ timestamp: string; value: number; period: number }>
    ema?: Array<{ timestamp: string; value: number; period: number }>
  }
  fundCurves?: FundCurveData[]
}

// 时间周期枚举
export enum TimePeriod {
  MINUTE_1 = '1m',
  MINUTE_5 = '5m',
  MINUTE_15 = '15m',
  MINUTE_30 = '30m',
  HOUR_1 = '1h',
  HOUR_4 = '4h',
  DAY_1 = '1d',
  DAY_7 = '1w',
  MONTH_1 = '1M'
}

// K线图配置
export interface KlineConfig {
  // 基础配置
  height?: number
  width?: number
  timePeriod: TimePeriod

  // 显示配置
  showVolume: boolean
  showSignals: boolean
  showMovingAverages: boolean
  showGrid: boolean
  showCrosshair: boolean
  showFundCurves: boolean  // 新增：显示资金曲线

  // 颜色配置
  colors: {
    bullish: string      // 上涨颜色
    bearish: string      // 下跌颜色
    volume: string       // 成交量颜色
    grid: string         // 网格颜色
    text: string         // 文字颜色
    background: string  // 背景颜色
    crosshair: string    // 十字线颜色
  }

  // 移动平均线配置
  movingAverages: {
    sma?: number[]       // SMA周期数组
    ema?: number[]       // EMA周期数组
    colors: string[]     // 移动平均线颜色数组
  }

  // 资金曲线配置
  fundCurves?: {
    enabled: boolean
    dualYAxis: DualYAxisConfig
    baselineComparison: boolean
    showMetrics: boolean
  }

  // 交互配置
  interactions: {
    enableZoom: boolean
    enablePan: boolean
    enableScroll: boolean
    wheelSensitivity: number
    keyboardShortcuts: boolean
  }

  // 性能配置
  performance: {
    enableDataSampling: boolean
    maxDataPoints: number
    enableAnimation: boolean
    animationDuration: number
  }
}

// K线图组件Props
export interface KlineChartProps {
  data: KlineData
  config?: Partial<KlineConfig>
  className?: string
  onSignalClick?: (signal: TradingSignal) => void
  onTimePeriodChange?: (period: TimePeriod) => void
  onDataPointHover?: (data: CandlestickData | null) => void
  onChartReady?: () => void
}

// 时间周期选择器Props
export interface TimePeriodSelectorProps {
  currentPeriod: TimePeriod
  availablePeriods: TimePeriod[]
  onPeriodChange: (period: TimePeriod) => void
  className?: string
  disabled?: boolean
}

// 图表控制器Props
export interface ChartControlsProps {
  onZoomIn: () => void
  onZoomOut: () => void
  onResetZoom: () => void
  onToggleCrosshair: () => void
  onToggleGrid: () => void
  onExport: () => void
  onFullscreen: () => void
  className?: string
  showCrosshair: boolean
  showGrid: boolean
  disabled?: boolean
}

// 性能监控Props
export interface PerformanceMonitorProps {
  dataPoints: number
  renderTime: number
  fps: number
  memoryUsage: number
  className?: string
  showDetails?: boolean
}

// Lightweight Charts 适配器类型
export interface LightweightChartConfig {
  container: HTMLElement
  width: number
  height: number
  layout: {
    background: {
      type: 'solid'
      color: string
    }
    textColor: string
  }
  grid: {
    vertLines: {
      visible: boolean
      color: string
    }
    horzLines: {
      visible: boolean
      color: string
    }
  }
  crosshair: {
    mode: 'normal' | 'magnet' | 'hidden'
    vertLine: {
      width: number
      color: string
      style: 'solid' | 'dotted' | 'dashed'
    }
    horzLine: {
      width: number
      color: string
      style: 'solid' | 'dotted' | 'dashed'
    }
  }
  rightPriceScale: {
    visible: boolean
    borderColor: string
    textColor: string
  }
  timeScale: {
    borderColor: string
    textColor: string
    timeVisible: boolean
    secondsVisible: boolean
  }
  watermark: {
    visible: boolean
    color: string
    fontSize: number
    horzAlign: 'left' | 'center' | 'right'
    vertAlign: 'top' | 'middle' | 'bottom'
  }
}


// 键盘快捷键配置
export interface KeyboardShortcutConfig {
  enabled: boolean
  shortcuts: {
    panLeft: string[]      // 向左平移
    panRight: string[]     // 向右平移
    zoomIn: string[]       // 放大
    zoomOut: string[]      // 缩小
    resetZoom: string[]    // 重置缩放
    toggleCrosshair: string[] // 切换十字线
    toggleGrid: string[]   // 切换网格
    nextPeriod: string[]   // 下一个周期
    prevPeriod: string[]   // 上一个周期
  }
}

// 导出功能配置
export interface KlineExportConfig {
  format: 'png' | 'jpeg' | 'svg' | 'csv' | 'json'
  width?: number
  height?: number
  quality?: number
  backgroundColor?: string
  includeVolume?: boolean
  includeSignals?: boolean
  includeMovingAverages?: boolean
  filename?: string
}

// 错误处理类型
export interface KlineChartError {
  type: 'DATA_ERROR' | 'RENDER_ERROR' | 'PERFORMANCE_ERROR' | 'CONFIG_ERROR'
  message: string
  details?: any
  timestamp: string
}

// 缓存配置
export interface KlineCacheConfig {
  enabled: boolean
  maxAge: number        // 缓存过期时间（毫秒）
  maxSize: number       // 最大缓存条目数
  storage: 'memory' | 'localStorage' | 'indexedDB'
}

// 资金曲线数据点
export interface FundCurveDataPoint {
  timestamp: number
  value: number
  // 可选的指标数据
  metrics?: Partial<PerformanceMetrics>
}

// 资金曲线数据
export interface FundCurveData {
  id: string
  name: string
  data: FundCurveDataPoint[]
  // 样式配置
  color: string
  lineWidth?: number
  lineType?: 'solid' | 'dashed' | 'dotted'
  visible?: boolean
  // 曲线类型
  curveType: 'strategy' | 'baseline' | 'benchmark'
}

// 性能指标
export interface PerformanceMetrics {
  returnRate: number        // 收益率
  maxDrawdown: number       // 最大回撤
  sharpeRatio: number       // 夏普比率
  totalReturn: number       // 总收益
  annualizedReturn: number  // 年化收益
  volatility: number        // 波动率
  winRate: number          // 胜率
  profitFactor: number     // 盈利因子
  maxConsecutiveWins: number   // 最大连续盈利
  maxConsecutiveLosses: number  // 最大连续亏损
}

// 双Y轴配置
export interface DualYAxisConfig {
  // 左Y轴（价格）
  leftAxis: {
    visible: boolean
    textColor: string
    borderColor: string
    scaleMargins?: {
      top: number
      bottom: number
    }
  }
  // 右Y轴（资金）
  rightAxis: {
    visible: boolean
    textColor: string
    borderColor: string
    scaleMargins?: {
      top: number
      bottom: number
    }
  }
  // 同步配置
  synchronization: {
    enabled: boolean
    syncZoom: boolean
    syncPan: boolean
  }
}

// 数据验证结果
export interface DataValidationResult {
  isValid: boolean
  errors: string[]
  warnings: string[]
  dataPoints: number
  dateRange: {
    start: string
    end: string
  }
}

// 事件类型
export type KlineChartEvent =
  | { type: 'DATA_POINT_CLICK'; payload: CandlestickData }
  | { type: 'SIGNAL_CLICK'; payload: TradingSignal }
  | { type: 'TIME_PERIOD_CHANGE'; payload: TimePeriod }
  | { type: 'ZOOM_CHANGE'; payload: { from: number; to: number } }
  | { type: 'PAN_CHANGE'; payload: { from: number; to: number } }
  | { type: 'CROSSHAIR_MOVE'; payload: { time: number; price: number } }
  | { type: 'PERFORMANCE_WARNING'; payload: { metric: string; value: number; threshold: number } }
  | { type: 'ERROR'; payload: KlineChartError }