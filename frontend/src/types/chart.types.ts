// 图表相关类型定义
export interface PricePoint {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
}

export interface TradingSignal {
  timestamp: string
  type: 'buy' | 'sell'
  price: number
  strategy: string
}

export interface MovingAverageLine {
  timestamp: string
  value: number
  type: 'SMA' | 'EMA'
  period: number
}

export interface ChartData {
  prices: PricePoint[]
  signals: TradingSignal[]
  movingAverages: MovingAverageLine[]
}

export interface ChartConfig {
  title?: string
  showSignals: boolean
  showMovingAverages: boolean
  movingAverageType: 'SMA' | 'EMA'
  movingAveragePeriod: number
  showVolume: boolean
  animationDuration: number
}

export interface PriceChartProps {
  data: ChartData
  config?: Partial<ChartConfig>
  title?: string
  onSignalClick?: (signal: TradingSignal) => void
  onPointClick?: (point: any) => void
  onParameterChange?: (config: ChartConfig) => void
  className?: string
  height?: number
  width?: number
}

// Chart.js 相关类型
export interface ChartDataset {
  label: string
  data: number[]
  borderColor: string
  backgroundColor: string
  borderWidth?: number
  pointRadius?: number
  pointHoverRadius?: number
  tension?: number
  type?: 'line' | 'scatter'
}

export interface ChartTooltipItem {
  datasetIndex: number
  dataIndex: number
  dataset: ChartDataset
  label: string
  parsed: {
    x: any
    y: number
  }
}

export interface ChartTooltipContext {
  tooltipItems: ChartTooltipItem[]
  data: {
    labels: string[]
    datasets: ChartDataset[]
  }
}

// 导出功能相关类型
export type ExportFormat = 'png' | 'jpeg' | 'csv' | 'json'

export interface ExportOptions {
  format: ExportFormat
  width?: number
  height?: number
  backgroundColor?: string
  includeSignals?: boolean
  includeMovingAverages?: boolean
}

// 图表交互配置
export interface ChartInteractionConfig {
  enableZoom: boolean
  enablePan: boolean
  zoomMode: 'x' | 'y' | 'xy'
  panMode: 'x' | 'y' | 'xy'
  wheelSensitivity: number
  enableTooltip: boolean
  enableCrosshair: boolean
  enableDataLabels: boolean
}

// 性能配置
export interface PerformanceConfig {
  enableDataSampling: boolean
  maxDataPoints: number
  enableAnimation: boolean
  animationDuration: number
}

// 图表主题
export interface ChartTheme {
  name: string
  colors: {
    background: string
    grid: string
    text: string
    price: string
    buySignal: string
    sellSignal: string
    movingAverage: string
    volume: string
  }
  fonts: {
    family: string
    size: {
      title: number
      legend: number
      axis: number
      tooltip: number
    }
  }
  styles: {
    lineWidth: number
    pointRadius: number
    gridLines: boolean
    animations: boolean
  }
}

// 图表布局
export interface ChartLayout {
  height: number
  width?: number
  padding: {
    top: number
    right: number
    bottom: number
    left: number
  }
  showControls: boolean
  showLegend: boolean
  showTooltip: boolean
  responsive: boolean
}

// 导出偏好
export interface ExportPreferences {
  defaultFormat: ExportFormat
  defaultFilename: string
  includeMetadata: boolean
  backgroundColor: string
  quality: number
  dimensions: {
    width: number
    height: number
  }
}
