import {
  CategoryScale,
  ChartConfiguration,
  Chart as ChartJS,
  ChartData as ChartJSData,
  ChartOptions,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  Plugin,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js';
import {
  ChartConfig,
  ChartData,
  MovingAverageLine,
  PricePoint,
  TradingSignal,
} from '@/types/chart.types';

// Chart.js helpers类型定义
interface ChartHelpersType {
  getRelativePosition: (value: any, chart: ChartJS) => { x: number; y: number };
}

// 注册 Chart.js 组件
export function registerChartJS() {
  ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
  );
}

// 颜色方案
export const chartColors = {
  primary: '#3B82F6',
  secondary: '#10B981',
  danger: '#EF4444',
  warning: '#F59E0B',
  info: '#06B6D4',
  gray: '#6B7280',
  grid: '#E5E7EB',
  text: '#374151',
  background: '#FFFFFF',
  positive: '#10B981',
  negative: '#EF4444',
};

// 默认图表配置
export const defaultChartOptions: ChartOptions<'line'> = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  plugins: {
    title: {
      display: true,
      text: '价格走势图',
      font: {
        size: 16,
        weight: 'bold',
      },
    },
    legend: {
      display: true,
      position: 'top',
    },
    tooltip: {
      enabled: true,
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      titleColor: '#FFFFFF',
      bodyColor: '#FFFFFF',
      borderColor: chartColors.primary,
      borderWidth: 1,
    },
  },
  scales: {
    x: {
      display: true,
      title: {
        display: true,
        text: '日期',
      },
      grid: {
        display: false,
      },
    },
    y: {
      display: true,
      title: {
        display: true,
        text: '价格',
      },
      grid: {
        color: chartColors.grid,
      },
    },
  },
};

// 创建价格数据集
export const createPriceDataset = (data: PricePoint[]) => {
  return {
    label: '价格',
    data: data.map((point) => ({
      x: new Date(point.timestamp).getTime(),
      y: point.close,
    })),
    borderColor: chartColors.primary,
    backgroundColor: `${chartColors.primary}10`,
    borderWidth: 2,
    fill: false,
    tension: 0.1,
    pointRadius: 0,
    pointHoverRadius: 4,
  };
};

// 创建移动平均线数据集
export const createMovingAverageDataset = (
  data: MovingAverageLine | MovingAverageLine[],
  color: string,
) => {
  // 处理单个对象或数组的情况
  const maArray = Array.isArray(data) ? data : [data];
  const period = maArray[0]?.period || '';

  return {
    label: `MA${period}`,
    data: maArray.map((point) => ({
      x: new Date(point.timestamp).getTime(),
      y: point.value,
    })),
    borderColor: color,
    backgroundColor: `${color}10`,
    borderWidth: 1.5,
    fill: false,
    tension: 0.1,
    pointRadius: 0,
    pointHoverRadius: 3,
    borderDash: [5, 5],
  };
};

// 创建交易信号数据集
export const createSignalDataset = (signals: TradingSignal[]) => {
  const buySignals = signals.filter((s) => s.type === 'buy');
  const sellSignals = signals.filter((s) => s.type === 'sell');

  return [
    {
      label: '买入信号',
      data: buySignals.map((signal) => ({
        x: new Date(signal.timestamp).getTime(),
        y: signal.price,
      })),
      borderColor: chartColors.positive,
      backgroundColor: chartColors.positive,
      borderWidth: 0,
      fill: false,
      tension: 0,
      pointRadius: 8,
      pointHoverRadius: 10,
    },
    {
      label: '卖出信号',
      data: sellSignals.map((signal) => ({
        x: new Date(signal.timestamp).getTime(),
        y: signal.price,
      })),
      borderColor: chartColors.negative,
      backgroundColor: chartColors.negative,
      borderWidth: 0,
      fill: false,
      tension: 0,
      pointRadius: 8,
      pointHoverRadius: 10,
    },
  ];
};

// 格式化日期
export const formatDate = (date: Date | string): string => {
  const d = new Date(date);
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
};

// 格式化数字
export const formatNumber = (num: number, decimals: number = 2): string => {
  return num.toFixed(decimals);
};

// 格式化百分比
export const formatPercent = (num: number, decimals: number = 2): string => {
  return `${num.toFixed(decimals)}%`;
};

// 计算数据范围
export const calculateDataRange = (
  data: Array<{ x: any; y: number | null }>,
) => {
  const validData = data.filter((d) => d.y !== null);
  if (validData.length === 0) {
    return { min: 0, max: 100 };
  }

  const values = validData.map((d) => d.y as number);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padding = (max - min) * 0.1;

  return {
    min: min - padding,
    max: max + padding,
  };
};

// 创建图表配置
export const createChartConfig = (
  data: ChartData,
  options: Partial<ChartOptions<'line'>> = {},
): ChartConfiguration<'line'> => {
  const datasets = [
    createPriceDataset(data.prices),
    ...data.movingAverages.map((ma, index) =>
      createMovingAverageDataset(
        ma,
        [chartColors.secondary, chartColors.warning, chartColors.info][
          index % 3
        ],
      ),
    ),
    ...createSignalDataset(data.signals),
  ].filter(Boolean);

  return {
    type: 'line',
    data: {
      datasets,
    },
    options: {
      ...defaultChartOptions,
      ...options,
    },
  };
};

// 自定义工具提示
export const createCustomTooltip = (tooltipModel: any) => {
  if (!tooltipModel.body) return;

  const titleLines = tooltipModel.title || [];
  const bodyLines = tooltipModel.body.map((bodyItem: any) => bodyItem.lines);

  let innerHtml = '<thead>';

  titleLines.forEach((title: string) => {
    innerHtml += `<tr><th style="color: #fff; font-weight: bold;">${title}</th></tr>`;
  });

  innerHtml += '</thead><tbody>';

  bodyLines.forEach((body: string, i: number) => {
    const colors = tooltipModel.labelColors[i];
    const style = `background:${colors.backgroundColor}; color:${colors.borderColor}; border-color:${colors.borderColor};`;
    innerHtml += `<tr><td style="${style} padding: 4px 8px; border-radius: 4px;">${body}</td></tr>`;
  });

  innerHtml += '</tbody>';

  const tooltipRoot = document.createElement('div');
  tooltipRoot.innerHTML = `<table style="border-collapse: collapse; background: rgba(0,0,0,0.8); color: white; border-radius: 6px;">${innerHtml}</table>`;
  return tooltipRoot;
};

// 查找最近的信号
export const findNearestSignal = (
  signals: TradingSignal[],
  targetDate: Date,
  maxDistanceMs: number = 24 * 60 * 60 * 1000, // 24小时
): TradingSignal | null => {
  if (signals.length === 0) return null;

  const targetTime = targetDate.getTime();
  let nearestSignal: TradingSignal | null = null;
  let minDistance = maxDistanceMs;

  signals.forEach((signal) => {
    const signalTime = new Date(signal.timestamp).getTime();
    const distance = Math.abs(signalTime - targetTime);

    if (distance < minDistance) {
      minDistance = distance;
      nearestSignal = signal;
    }
  });

  return nearestSignal;
};

// 计算移动平均线
export const calculateMovingAverage = (
  data: PricePoint[],
  period: number,
): MovingAverageLine[] => {
  const result: MovingAverageLine[] = [];

  for (let i = period - 1; i < data.length; i++) {
    const subset = data.slice(i - period + 1, i + 1);
    const sum = subset.reduce((acc, point) => acc + point.close, 0);
    const average = sum / period;

    result.push({
      timestamp: data[i].timestamp,
      value: average,
      type: 'SMA' as const,
      period,
    });
  }

  return result;
};

// 生成测试数据
export const generateTestData = (days: number = 30): ChartData => {
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - days);

  const prices: PricePoint[] = [];
  let currentPrice = 100;

  for (let i = 0; i < days; i++) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + i);

    // 随机价格波动
    const change = (Math.random() - 0.5) * 4;
    currentPrice = Math.max(1, currentPrice + change);

    prices.push({
      timestamp: date.toISOString(),
      open: currentPrice,
      high: currentPrice + Math.random() * 2,
      low: currentPrice - Math.random() * 2,
      close: currentPrice,
    });
  }

  // 生成移动平均线
  const closePrices = prices.map((p) => p.close);
  const ma5Values = calculateSMA(closePrices, 5);
  const ma20Values = calculateSMA(closePrices, 20);

  const ma5: MovingAverageLine[] = ma5Values.map((value, index) => ({
    timestamp: prices[index + 4].timestamp,
    value,
    type: 'SMA',
    period: 5,
  }));

  const ma20: MovingAverageLine[] = ma20Values.map((value, index) => ({
    timestamp: prices[index + 19].timestamp,
    value,
    type: 'SMA',
    period: 20,
  }));

  // 生成随机信号
  const signals: TradingSignal[] = [];
  for (let i = 5; i < prices.length - 5; i++) {
    if (Math.random() > 0.9) {
      signals.push({
        timestamp: prices[i].timestamp,
        type: Math.random() > 0.5 ? 'buy' : 'sell',
        price: prices[i].close,
        strategy: 'Test Strategy',
      });
    }
  }

  return {
    prices,
    movingAverages: [...ma5, ...ma20],
    signals,
  };
};

// 图表主题
export const chartThemes = {
  light: {
    background: chartColors.background,
    text: chartColors.text,
    grid: chartColors.grid,
    primary: chartColors.primary,
    secondary: chartColors.secondary,
  },
  dark: {
    background: '#1F2937',
    text: '#F9FAFB',
    grid: '#374151',
    primary: '#60A5FA',
    secondary: '#34D399',
  },
};

// 应用主题
export const applyTheme = (
  options: ChartOptions<'line'>,
  theme: keyof typeof chartThemes,
) => {
  const colors = chartThemes[theme];

  options.plugins?.title && (options.plugins.title.color = colors.text);
  options.plugins?.legend &&
    (options.plugins.legend.labels = {
      ...options.plugins.legend.labels,
      color: colors.text,
    });
  options.scales?.x &&
    (options.scales.x.ticks = {
      ...options.scales.x.ticks,
      color: colors.text,
    });
  options.scales?.y &&
    (options.scales.y.ticks = {
      ...options.scales.y.ticks,
      color: colors.text,
    });
  options.scales?.x &&
    (options.scales.x.grid = { ...options.scales.x.grid, color: colors.grid });
  options.scales?.y &&
    (options.scales.y.grid = { ...options.scales.y.grid, color: colors.grid });

  return options;
};

// 计算SMA
export const calculateSMA = (data: number[], period: number): number[] => {
  const result: number[] = [];
  for (let i = period - 1; i < data.length; i++) {
    const sum = data.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0);
    result.push(sum / period);
  }
  return result;
};

// 计算EMA
export const calculateEMA = (data: number[], period: number): number[] => {
  const result: number[] = [];
  const multiplier = 2 / (period + 1);

  // Start with SMA for the first EMA value
  let ema = data.slice(0, period).reduce((a, b) => a + b, 0) / period;
  result.push(ema);

  for (let i = period; i < data.length; i++) {
    ema = (data[i] - ema) * multiplier + ema;
    result.push(ema);
  }

  return result;
};

// 导出功能
export const exportToCSV = (data: ChartData): string => {
  const rows: string[] = [];
  rows.push('Date,Open,High,Low,Close,Signal Type,Signal Price');

  data.prices.forEach((price) => {
    const signal = data.signals.find(
      (s) =>
        new Date(s.timestamp).toDateString() ===
        new Date(price.timestamp).toDateString(),
    );
    rows.push(
      `${price.timestamp},${price.open},${price.high},${price.low},${price.close},${signal ? signal.type : ''},${signal ? signal.price : ''}`,
    );
  });

  return rows.join('\n');
};

export const exportToJSON = (data: ChartData): string => {
  return JSON.stringify(data, null, 2);
};

// 格式化图表数据
export const formatChartData = (data: ChartData): ChartData => {
  return {
    ...data,
    prices: data.prices.sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    ),
    signals: data.signals.sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    ),
  };
};

// 生成图表选项
export const generateChartOptions = (
  config: any,
  onSignalClick?: (signal: TradingSignal) => void,
) => {
  return {
    ...defaultChartOptions,
    onClick: (event: any, elements: any[]) => {
      if (elements.length > 0) {
        // Handle signal clicks
      }
    },
  };
};

// 生成价格数据集
export const generatePriceDatasets = (data: ChartData, config: any) => {
  return [createPriceDataset(data.prices)];
};

// 生成信号数据集
export const generateSignalDatasets = (signals: TradingSignal[]) => {
  return createSignalDataset(signals);
};

// 数据采样
export const sampleData = <T>(data: T[], maxPoints: number): T[] => {
  if (data.length <= maxPoints) return data;
  const step = Math.ceil(data.length / maxPoints);
  return data.filter((_, index) => index % step === 0);
};

export default {
  registerChartJS,
  createPriceDataset,
  createMovingAverageDataset,
  createSignalDataset,
  createChartConfig,
  formatDate,
  formatNumber,
  formatPercent,
  findNearestSignal,
  calculateMovingAverage,
  generateTestData,
  chartColors,
  chartThemes,
  applyTheme,
  calculateSMA,
  calculateEMA,
  exportToCSV,
  exportToJSON,
  formatChartData,
  generateChartOptions,
  generatePriceDatasets,
  generateSignalDatasets,
  sampleData,
};
