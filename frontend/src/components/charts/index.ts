// 主要K线图组件
export { default as KlineChartContainer } from './KlineChartContainer';

// 单独的K线图组件
export { default as KlineChart } from './KlineChart';
export { default as CandlestickChart } from './CandlestickChart';

// 主题化图表组件
export { default as ThemedKlineChart } from './ThemedKlineChart';

// 控制组件
export { default as TimePeriodSelector } from './TimePeriodSelector';
export { default as KlineChartControls } from './KlineChartControls';

// 性能监控组件
export { default as PerformanceMonitor } from './PerformanceMonitor';
export { default as PerformanceBenchmark } from './PerformanceBenchmark';

// 工具函数
export * from '../utils/klineHelpers';

// 服务
export { klineDataService } from '../services/klineService';
export { timePeriodService } from '../services/timePeriodService';
export { timePeriodCacheManager } from '../services/timePeriodCache';
export { createTimePeriodDataManager } from '../services/timePeriodDataManager';
export { adaptivePerformanceService } from '../services/adaptivePerformanceService';
export { keyboardShortcutService } from '../services/keyboardShortcutService';
export { chartInteractionService } from '../services/chartInteractionService';

// 类型定义
export * from '../types/kline.types';
