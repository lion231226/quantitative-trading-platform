import {
  ChartConfiguration,
  Chart as ChartJS,
} from 'chart.js';
import { ChartData, ExportFormat, ExportOptions, MovingAverageLine, PricePoint } from '@/types/chart.types';

// 导出配置接口
export interface ChartExportConfig {
  format: ExportFormat
  width?: number
  height?: number
  backgroundColor?: string
  quality?: number // 图片质量 0-1
  filename?: string
  includeSignals?: boolean
  includeMovingAverages?: boolean
  includeMetadata?: boolean
}

// 默认导出配置
export const DEFAULT_EXPORT_CONFIG: Partial<ChartExportConfig> = {
  backgroundColor: '#ffffff',
  quality: 0.9,
  filename: `chart-${new Date().toISOString().split('T')[0]}`,
  includeSignals: true,
  includeMovingAverages: true,
  includeMetadata: true,
};

// 图表导出器类
export class ChartExporter {
  private chart: ChartJS | null = null;
  private config: ChartExportConfig;
  private originalData: ChartData | null = null;

  constructor(chart: ChartJS, config: Partial<ChartExportConfig> = {}) {
    this.chart = chart;
    this.config = { ...DEFAULT_EXPORT_CONFIG, ...config } as ChartExportConfig;
    this.originalData = this.extractChartData();
  }

  // 提取图表数据（避免直接访问private属性）
  private extractChartData(): ChartData | null {
    if (!this.chart) return null;

    try {
      const chartData = this.chart.data;
      if (!chartData) return null;

      // 从图表配置中重建ChartData结构
      const datasets = chartData.datasets || [];
      const prices: any[] = [];
      const movingAverages: any[] = [];
      const signals: any[] = [];

      datasets.forEach((dataset: any, index: number) => {
        if (dataset.label === '价格') {
          prices.push(...dataset.data.map((point: any) => ({
            timestamp: point.x,
            close: point.y,
            open: point.y,
            high: point.y,
            low: point.y,
          })));
        } else if (dataset.label?.startsWith('MA')) {
          const maData = dataset.data.map((point: any) => ({
            timestamp: point.x,
            value: point.y,
            type: 'SMA' as const,
            period: parseInt(dataset.label.replace('MA', '')) || 0,
          }));
          movingAverages.push(...maData);
        } else if (dataset.label === '买入信号' || dataset.label === '卖出信号') {
          signals.push(...dataset.data.map((point: any) => ({
            timestamp: point.x,
            price: point.y,
            type: dataset.label === '买入信号' ? 'buy' : 'sell',
            strategy: 'MA Strategy',
          })));
        }
      });

      return {
        prices,
        movingAverages,
        signals,
      };
    } catch (error) {
      console.error('Failed to extract chart data:', error);
      return null;
    }
  }

  // 导出为图片
  exportAsImage(): string | null {
    if (!this.chart) return null;

    try {
      const canvas = this.chart.canvas;
      if (!canvas) return null;

      // 应用背景色
      const originalBg = canvas.style.backgroundColor;
      if (this.config.backgroundColor) {
        canvas.style.backgroundColor = this.config.backgroundColor;
      }

      // 导出图片
      const dataURL = canvas.toDataURL(`image/${this.config.format}`, this.config.quality);

      // 恢复原始背景色
      canvas.style.backgroundColor = originalBg;

      return dataURL;
    } catch (error) {
      console.error('Export image failed:', error);
      return null;
    }
  }

  // 导出为数据URL
  exportDataURL(): string | null {
    return this.exportAsImage();
  }

  // 导出为Blob
  async exportAsBlob(): Promise<Blob | null> {
    const dataURL = this.exportDataURL();
    if (!dataURL) return null;

    try {
      const response = await fetch(dataURL);
      return await response.blob();
    } catch (error) {
      console.error('Export blob failed:', error);
      return null;
    }
  }

  // 导出为文件
  async exportAsFile(): Promise<boolean> {
    const dataURL = this.exportDataURL();
    if (!dataURL) return false;

    try {
      const blob = await this.exportAsBlob();
      if (!blob) return false;

      const filename = `${this.config.filename || 'chart'}.${this.config.format}`;

      // 创建下载链接
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      return true;
    } catch (error) {
      console.error('Export file failed:', error);
      return false;
    }
  }

  // 导出为JSON数据
  exportAsJSON(): string | null {
    if (!this.originalData) return null;

    const exportData = {
      metadata: this.config.includeMetadata ? {
        exportedAt: new Date().toISOString(),
        format: this.config.format,
        includeSignals: this.config.includeSignals,
        includeMovingAverages: this.config.includeMovingAverages,
      } : undefined,
      data: {
        prices: this.originalData.prices,
        movingAverages: this.config.includeMovingAverages ? this.originalData.movingAverages : [],
        signals: this.config.includeSignals ? this.originalData.signals : [],
      },
    };

    return JSON.stringify(exportData, null, 2);
  }

  // 导出为CSV
  exportAsCSV(): string | null {
    if (!this.originalData) return null;

    try {
      const rows: string[] = [];

      // CSV头部
      rows.push('Date,Price,MA5,MA20,Signal Type,Signal Price');

      // 合并所有数据并按日期排序
      const allData: any[] = [];

      // 添加价格数据
      this.originalData.prices.forEach(price => {
        allData.push({
          date: price.timestamp,
          price: price.close,
          ma5: null,
          ma20: null,
          signalType: '',
          signalPrice: '',
        });
      });

      // 添加移动平均线数据
      if (this.config.includeMovingAverages) {
        this.originalData.movingAverages.forEach(point => {
          const existingRow = allData.find(row =>
            new Date(row.date).getTime() === new Date(point.timestamp).getTime()
          );
          if (existingRow) {
            const periodKey = `ma${point.period}`;
            existingRow[periodKey] = point.value;
          }
        });
      }

      // 添加信号数据
      if (this.config.includeSignals) {
        this.originalData.signals.forEach(signal => {
          const existingRow = allData.find(row =>
            new Date(row.date).getTime() === new Date(signal.timestamp).getTime()
          );
          if (existingRow) {
            existingRow.signalType = signal.type;
            existingRow.signalPrice = signal.price;
          }
        });
      }

      // 转换为CSV行
      allData.forEach(row => {
        const date = new Date(row.date).toLocaleDateString('zh-CN');
        rows.push(`${date},${row.price},${row.ma5 || ''},${row.ma20 || ''},${row.signalType},${row.signalPrice}`);
      });

      return rows.join('\n');
    } catch (error) {
      console.error('Export CSV failed:', error);
      return null;
    }
  }

  // 预览导出结果
  previewExport(): string | null {
    switch (this.config.format) {
      case 'png':
      case 'jpeg':
        return this.exportDataURL();
      case 'json':
        return this.exportAsJSON();
      case 'csv':
        return this.exportAsCSV();
      default:
        return null;
    }
  }

  // 更新导出配置
  updateConfig(newConfig: Partial<ChartExportConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  // 获取当前配置
  getConfig(): ChartExportConfig {
    return { ...this.config };
  }

  // 销毁导出器
  destroy(): void {
    this.chart = null;
    this.originalData = null;
  }

  // 静态方法：快速导出
  static quickExport(
    chart: ChartJS,
    format: ExportFormat = 'png',
    filename?: string
  ): Promise<boolean> {
    const exporter = new ChartExporter(chart, { format, filename });
    return exporter.exportAsFile();
  }

  // 静态方法：批量导出
  static async batchExport(
    charts: ChartJS[],
    formats: ExportFormat[],
    filenamePrefix?: string
  ): Promise<boolean[]> {
    const results: boolean[] = [];

    for (const chart of charts) {
      const chartResults: boolean[] = [];

      for (const format of formats) {
        const filename = filenamePrefix
          ? `${filenamePrefix}_${Date.now()}.${format}`
          : undefined;

        const success = await ChartExporter.quickExport(chart, format, filename);
        chartResults.push(success);
      }

      results.push(chartResults.every(r => r));
    }

    return results;
  }
}

// 工具函数：创建导出器
export const createChartExporter = (
  chart: ChartJS,
  config?: Partial<ChartExportConfig>
): ChartExporter => {
  return new ChartExporter(chart, config);
};

// 工具函数：获取支持的格式
export const getSupportedFormats = (): ExportFormat[] => {
  return ['png', 'jpeg', 'json', 'csv'];
};

// 工具函数：验证导出配置
export const validateExportConfig = (config: Partial<ChartExportConfig>): boolean => {
  const supportedFormats = getSupportedFormats();

  if (config.format && !supportedFormats.includes(config.format)) {
    return false;
  }

  if (config.quality && (config.quality < 0 || config.quality > 1)) {
    return false;
  }

  return true;
};

export default ChartExporter;