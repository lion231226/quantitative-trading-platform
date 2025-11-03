import {
  ActiveElement,
  ChartConfiguration,
  ChartEvent,
  Chart as ChartJS,
  Plugin,
  Scale,
  defaults,
} from 'chart.js';
import { ChartData, PricePoint, TradingSignal } from '@/types/chart.types';

// 尝试导入缩放插件（可选）
let ZoomPlugin: any = null;
try {
  ZoomPlugin = require('chartjs-plugin-zoom');
} catch (error) {
  console.warn('Chart.js zoom plugin not available:', error);
}

// 注册缩放插件
if (typeof window !== 'undefined' && ZoomPlugin) {
  try {
    ChartJS.register(ZoomPlugin.Zoom);
  } catch (error) {
    console.warn('Failed to register zoom plugin:', error);
  }
}

// 交互工具类
export class ChartInteractions {
  private chart: ChartJS | null = null;
  private zoomPlugin: any = null;
  private crosshairPlugin: any = null;
  private dataLabelsPlugin: any = null;

  constructor(chart: ChartJS) {
    this.chart = chart;
    this.initializePlugins();
  }

  private initializePlugins() {
    if (!this.chart) return;

    // 初始化插件引用
    this.zoomPlugin = this.chart.config.plugins?.find(p => p.id === 'zoom') || null;
    this.crosshairPlugin = this.chart.config.plugins?.find(p => p.id === 'crosshair') || null;
    this.dataLabelsPlugin = this.chart.config.plugins?.find(p => p.id === 'datalabels') || null;
  }

  // 重置缩放
  resetZoom() {
    if (!this.chart) return;

    try {
      // 尝试使用缩放插件方法
      if ((this.chart as any).resetZoom) {
        (this.chart as any).resetZoom();
      } else {
        console.warn('Reset zoom not available');
      }
    } catch (error) {
      console.warn('Reset zoom not available:', error);
    }
  }

  // 缩放到指定区域
  zoomTo(xMin: number, xMax: number, yMin?: number, yMax?: number) {
    if (!this.chart) return;

    try {
      if (this.zoomPlugin) {
        this.zoomPlugin.zoom(this.chart, {
          xMin,
          xMax,
          yMin,
          yMax,
        });
      }
    } catch (error) {
      console.warn('Zoom not available:', error);
    }
  }

  // 平移图表
  panChart(deltaX: number, deltaY: number) {
    if (!this.chart) return;

    try {
      if (this.zoomPlugin) {
        this.zoomPlugin.pan(this.chart, {
          x: deltaX,
          y: deltaY,
        });
      }
    } catch (error) {
      console.warn('Pan not available:', error);
    }
  }

  // 添加点击事件监听器
  addClickListener(callback: (event: ChartEvent, elements: ActiveElement[], chart: ChartJS) => void) {
    if (!this.chart) return;

    this.chart.options.onClick = callback;
  }

  // 添加悬停事件监听器
  addHoverListener(callback: (event: ChartEvent, elements: ActiveElement[], chart: ChartJS) => void) {
    if (!this.chart) return;

    this.chart.options.onHover = callback;
  }

  // 启用交叉线
  enableCrosshair() {
    if (!this.chart) return;

    try {
      // 添加交叉线插件配置
      if (!this.chart.config.plugins) {
        this.chart.config.plugins = [];
      }

      this.chart.config.plugins.push({
        id: 'crosshair',
        afterDraw: (chart) => {
          if (chart.tooltip && chart.tooltip.getActiveElements?.().length > 0) {
            const ctx = chart.ctx;
            const xAxis = chart.scales.x;
            const yAxis = chart.scales.y;

            if (xAxis && yAxis) {
              const canvasPosition = {
                x: 0,
                y: 0,
              };

              ctx.save();
              ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
              ctx.lineWidth = 1;

              // 绘制垂直线
              ctx.beginPath();
              ctx.moveTo(canvasPosition.x, yAxis.top);
              ctx.lineTo(canvasPosition.x, yAxis.bottom);
              ctx.stroke();

              // 绘制水平线
              ctx.beginPath();
              ctx.moveTo(xAxis.left, canvasPosition.y);
              ctx.lineTo(xAxis.right, canvasPosition.y);
              ctx.stroke();

              ctx.restore();
            }
          }
        }
      } as any);

      this.chart.update();
    } catch (error) {
      console.warn('Crosshair not available:', error);
    }
  }

  // 启用数据标签
  enableDataLabels() {
    if (!this.chart) return;

    try {
      if (!this.chart.config.plugins) {
        this.chart.config.plugins = [];
      }

      this.chart.config.plugins.push({
        id: 'datalabels',
        afterDatasetsDraw: (chart) => {
          const ctx = chart.ctx;
          chart.data.datasets.forEach((dataset, datasetIndex) => {
            const meta = chart.getDatasetMeta(datasetIndex);
            if (!meta.hidden) {
              meta.data.forEach((element: any, index: number) => {
                if (element && dataset.data[index] !== undefined) {
                  const dataPoint = dataset.data[index];
                  let displayText = '';

                  if (typeof dataPoint === 'number') {
                    displayText = dataPoint.toFixed(2);
                  } else if (dataPoint && typeof dataPoint === 'object') {
                    displayText = String(dataPoint.y || dataPoint);
                  }

                  if (displayText) {
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                    ctx.fillRect(element.x - 20, element.y - 25, 40, 20);
                    ctx.fillStyle = 'white';
                    ctx.textAlign = 'center';
                    ctx.fillText(displayText, element.x, element.y - 10);
                  }
                }
              });
            }
          });
        }
      } as any);

      this.chart.update();
    } catch (error) {
      console.warn('Data labels not available:', error);
    }
  }

  // 导出图表
  exportChart(format: 'png' | 'jpeg' = 'png'): string | null {
    if (!this.chart) return null;

    try {
      return (this.chart as any).toBase64Image(`image/${format}`);
    } catch (error) {
      console.error('Export failed:', error);
      return null;
    }
  }

  // 获取图表数据URL
  getDataURL(format: 'png' | 'jpeg' = 'png'): string | null {
    if (!this.chart) return null;

    try {
      return (this.chart as any).toDataURL(`image/${format}`);
    } catch (error) {
      console.error('Get data URL failed:', error);
      return null;
    }
  }

  // 设置图表响应式
  setResponsive(responsive: boolean) {
    if (!this.chart) return;

    this.chart.options.responsive = responsive;
    this.chart.update();
  }

  // 销毁交互工具
  destroy() {
    this.chart = null;
    this.zoomPlugin = null;
    this.crosshairPlugin = null;
    this.dataLabelsPlugin = null;
  }
}

// 工具函数
export const createChartInteractions = (chart: ChartJS): ChartInteractions => {
  return new ChartInteractions(chart);
};

// 交互配置生成器
export const createInteractionConfig = () => ({
  // 缩放配置
  zoom: {
    wheel: {
      enabled: true,
    },
    pinch: {
      enabled: true,
    },
    mode: 'xy' as const,
  },

  // 平移配置
  pan: {
    enabled: true,
    mode: 'xy' as const,
  },

  // 点击事件配置
  events: ['mousemove', 'mouseout', 'click', 'touchstart', 'touchmove'] as const,
});

// 信号点击处理器
export const handleSignalClick = (
  event: ChartEvent,
  elements: ActiveElement[],
  chart: ChartJS,
  signals: TradingSignal[],
  onSignalClick?: (signal: TradingSignal) => void
) => {
  if (elements.length > 0 && signals.length > 0) {
    const element = elements[0];
    const datasetIndex = element.datasetIndex;
    const index = element.index;

    // 查找对应的信号
    const signal = signals.find(s =>
      Math.floor(new Date(s.timestamp).getTime() / 1000) === index
    );

    if (signal && onSignalClick) {
      onSignalClick(signal);
    }
  }
};

// 价格点处理器
export const handlePricePointClick = (
  event: ChartEvent,
  elements: ActiveElement[],
  chart: ChartJS,
  data: PricePoint[],
  onPointClick?: (point: PricePoint) => void
) => {
  if (elements.length > 0 && data.length > 0) {
    const element = elements[0];
    const index = element.index;

    if (index >= 0 && index < data.length) {
      const point = data[index];
      if (onPointClick) {
        onPointClick(point);
      }
    }
  }
};

export default ChartInteractions;