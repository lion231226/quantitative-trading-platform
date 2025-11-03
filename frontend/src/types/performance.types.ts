/**
 * 绩效指标相关类型定义
 */

// 基础绩效指标
export interface PerformanceMetrics {
  strategyId: string;
  totalReturn: number;
  annualizedReturn: number;
  maxDrawdown: number;
  maxDrawdownPeriod?: number;
  volatility: number;
  sharpeRatio: number;
  sortinoRatio: number;
  winRate: number;
  profitLossRatio: number;
  totalTrades: number;
  profitableTrades?: number;
  averageTrade?: number;
  expectancy?: number;
  calmarRatio?: number;
  calculationDate: string;
  periodStart?: string;
  periodEnd?: string;
  dataPoints: number;
}

// 收益率数据点
export interface ReturnDataPoint {
  timestamp: string;
  value: number;
  date: Date;
}

// 累计收益数据
export interface CumulativeReturnData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    borderColor?: string;
    backgroundColor?: string;
    fill?: boolean;
    tension?: number;
  }>;
}

// 回撤数据
export interface DrawdownData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    borderColor?: string;
    backgroundColor?: string;
    fill?: boolean;
  }>;
}

// 滚动收益数据
export interface RollingReturnData {
  window: number; // 滚动窗口期（天）
  returns: number[];
  labels: string[];
}

// 绩效对比数据
export interface PerformanceComparison {
  strategies: Array<{
    id: string;
    name: string;
    metrics: PerformanceMetrics;
  }>;
  comparisonDate: string;
}

// 绩效报告配置
export interface PerformanceReportConfig {
  strategyId: string;
  reportType: 'summary' | 'detailed' | 'comparative';
  timePeriod: '1m' | '3m' | '6m' | '1y' | 'all';
  format: 'pdf' | 'excel' | 'csv';
  includeCharts: boolean;
  benchmarkId?: string;
}

// 绩效报告数据
export interface PerformanceReport {
  strategyId: string;
  reportType: string;
  timePeriod: string;
  generationDate: string;
  periodStart?: string;
  periodEnd?: string;
  format: string;
  metrics: PerformanceMetrics;
  summary: string;
  recommendations: string[];
  charts?: {
    cumulativeReturns: {
      labels: string[];
      data: number[];
    };
    drawdown?: {
      labels: string[];
      data: number[];
    };
  };
}

// 绩效分析请求参数
export interface PerformanceAnalysisRequest {
  strategyId: string;
  returnType: 'simple' | 'log';
  initialCapital: number;
  positionSize: number;
  riskFreeRate: number;
  includeCosts: boolean;
  startDate?: string;
  endDate?: string;
  benchmarkId?: string;
}

// 绩效分析响应
export interface PerformanceAnalysisResponse {
  success: boolean;
  data: {
    metrics: PerformanceMetrics;
    cumulativeReturns: CumulativeReturnData;
    drawdownData: DrawdownData;
    rollingReturns?: RollingReturnData[];
  };
  message: string;
}

// Chart.js 数据类型
export interface PerformanceChartData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    borderColor?: string;
    backgroundColor?: string;
    fill?: boolean;
    tension?: number;
    borderWidth?: number;
    pointRadius?: number;
    pointHoverRadius?: number;
  }>;
}

// 绩效指标格式化配置
export interface MetricFormatConfig {
  suffix?: string;
  prefix?: string;
  decimals?: number;
  formatAsPercentage?: boolean;
  formatAsCurrency?: boolean;
  colorCode?: 'positive' | 'negative' | 'neutral';
}

// 绩效指标显示配置
export interface MetricDisplayConfig {
  key: keyof PerformanceMetrics;
  label: string;
  format: MetricFormatConfig;
  importance: 'high' | 'medium' | 'low';
  category: 'returns' | 'risk' | 'efficiency' | 'trading';
}

// 绩效组件 Props
export interface PerformanceMetricsProps {
  strategyId: string;
  startDate?: string;
  endDate?: string;
  benchmarkId?: string;
  className?: string;
  onMetricsUpdate?: (metrics: PerformanceMetrics) => void;
  showDetails?: boolean;
  compact?: boolean;
}

export interface EquityCurveProps {
  strategyId: string;
  startDate?: string;
  endDate?: string;
  benchmarkId?: string;
  height?: number;
  width?: number;
  showControls?: boolean;
  showTooltip?: boolean;
  enableZoom?: boolean;
  className?: string;
  onDataPointClick?: (point: ReturnDataPoint) => void;
}

export interface DrawdownChartProps {
  strategyId: string;
  startDate?: string;
  endDate?: string;
  height?: number;
  width?: number;
  showControls?: boolean;
  showTooltip?: boolean;
  className?: string;
  onDrawdownClick?: (point: { timestamp: string; value: number }) => void;
}

export interface PerformanceComparisonProps {
  strategyIds: string[];
  benchmarkId?: string;
  startDate?: string;
  endDate?: string;
  comparisonType: 'metrics' | 'charts' | 'both';
  height?: number;
  width?: number;
  className?: string;
}

export interface PerformanceControlsProps {
  strategyId: string;
  onTimeRangeChange?: (startDate: string, endDate: string) => void;
  onBenchmarkChange?: (benchmarkId: string) => void;
  onExport?: (format: 'pdf' | 'csv' | 'excel' | 'png') => void;
  className?: string;
}

// API 响应类型
export interface PerformanceAPIResponse<T = any> {
  success: boolean;
  data: T;
  message: string;
}

// 缓存配置
export interface PerformanceCacheConfig {
  metricsTtl: number; // 指标缓存时间（秒）
  chartsTtl: number; // 图表缓存时间（秒）
  reportsTtl: number; // 报告缓存时间（秒）
}

// 错误类型
export interface PerformanceError {
  code: string;
  message: string;
  details?: any;
}

// 加载状态
export interface PerformanceLoadingState {
  isLoading: boolean;
  isRefreshing: boolean;
  lastUpdated?: string;
}

// 绩效主题配置
export interface PerformanceTheme {
  colors: {
    positive: string;
    negative: string;
    neutral: string;
    primary: string;
    secondary: string;
    background: string;
    text: string;
  };
  chart: {
    gridColor: string;
    fontFamily: string;
    fontSize: number;
  };
}