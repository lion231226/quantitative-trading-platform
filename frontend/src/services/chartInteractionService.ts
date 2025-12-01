import {
  CandlestickData,
  KlineChartEvent,
  TimePeriod,
} from '../types/kline.types';
import { keyboardShortcutService } from './keyboardShortcutService';

/**
 * 交互事件监听器
 */
export interface InteractionListener {
  onZoom?: (level: number, center?: number) => void;
  onPan?: (delta: number) => void;
  onReset?: () => void;
  onCrosshairToggle?: (enabled: boolean) => void;
  onGridToggle?: (enabled: boolean) => void;
  onPeriodChange?: (period: TimePeriod) => void;
  onDataPointHover?: (
    data: CandlestickData | null,
    position: { x: number; y: number },
  ) => void;
  onDataPointClick?: (data: CandlestickData, event: MouseEvent) => void;
  onExport?: (format: string) => void;
  onFullscreen?: (enabled: boolean) => void;
  onPerformanceToggle?: (enabled: boolean) => void;
}

/**
 * 图表交互服务
 */
export class ChartInteractionService {
  private listeners: Set<InteractionListener> = new Set();
  private chartInstance: any = null;
  private isZoomEnabled: boolean = true;
  private isPanEnabled: boolean = true;
  private currentZoomLevel: number = 1;
  private isCrosshairEnabled: boolean = false;
  private isGridEnabled: boolean = true;
  private currentTimePeriod: TimePeriod = '1d' as TimePeriod;

  constructor() {
    this.setupKeyboardShortcuts();
  }

  /**
   * 设置图表实例
   */
  setChartInstance(chart: any): void {
    this.chartInstance = chart;
    this.setupChartInteractions();
  }

  /**
   * 添加交互监听器
   */
  addListener(listener: InteractionListener): void {
    this.listeners.add(listener);
  }

  /**
   * 移除交互监听器
   */
  removeListener(listener: InteractionListener): void {
    this.listeners.delete(listener);
  }

  /**
   * 通知所有监听器
   */
  private notifyListeners(
    event: keyof InteractionListener,
    ...args: any[]
  ): void {
    this.listeners.forEach((listener) => {
      const callback = listener[event];
      if (callback) {
        try {
          callback(...(args as any));
        } catch (error) {
          console.error(`交互监听器错误 (${event}):`, error);
        }
      }
    });
  }

  /**
   * 设置图表交互
   */
  private setupChartInteractions(): void {
    if (!this.chartInstance) return;

    // 设置缩放和拖拽
    this.chartInstance.applyOptions({
      handleScroll: {
        vertTouchDrag: false,
        horzTouchDrag: true,
      },
      handleScale: {
        axisPressedMouseMove: {
          time: this.isZoomEnabled,
          price: false,
        },
        mouseWheel: this.isZoomEnabled,
        pinch: this.isZoomEnabled,
      },
    });

    // 十字线配置
    this.updateCrosshairOptions();

    // 添加事件监听器
    this.chartInstance.subscribeCrosshairMove(
      this.handleCrosshairMove.bind(this),
    );
    this.chartInstance.subscribeClick(this.handleClick.bind(this));
  }

  /**
   * 更新十字线选项
   */
  private updateCrosshairOptions(): void {
    if (!this.chartInstance) return;

    const crosshairOptions = this.isCrosshairEnabled
      ? {
          mode: 'normal' as const,
          vertLine: {
            width: 1,
            color: '#757575',
            style: 'dashed' as const,
          },
          horzLine: {
            width: 1,
            color: '#757575',
            style: 'dashed' as const,
          },
        }
      : {
          mode: 'hidden' as const,
        };

    // 更新所有序列的十字线选项
    const priceScale = this.chartInstance.priceScale();
    if (priceScale) {
      priceScale.applyOptions({ crosshair: crosshairOptions });
    }
  }

  /**
   * 处理十字线移动
   */
  private handleCrosshairMove(param: any): void {
    if (!param.time) {
      this.notifyListeners('onDataPointHover', null, { x: 0, y: 0 });
      return;
    }

    // 获取鼠标位置
    const x = param.point?.x || 0;
    const y = param.point?.y || 0;

    // 查找对应的数据点
    const candlestickData = this.findCandlestickData(param.time);
    this.notifyListeners('onDataPointHover', candlestickData, { x, y });
  }

  /**
   * 处理点击事件
   */
  private handleClick(param: any): void {
    if (!param.time) return;

    const candlestickData = this.findCandlestickData(param.time);
    if (candlestickData) {
      this.notifyListeners(
        'onDataPointClick',
        candlestickData,
        param.originalEvent as MouseEvent,
      );
    }
  }

  /**
   * 查找K线数据
   */
  private findCandlestickData(time: number): CandlestickData | null {
    // 这里需要根据实际数据源来实现
    // 暂时返回null
    return null;
  }

  /**
   * 设置键盘快捷键
   */
  private setupKeyboardShortcuts(): void {
    // 缩放
    keyboardShortcutService.addListener('zoomIn', () => this.zoomIn());
    keyboardShortcutService.addListener('zoomOut', () => this.zoomOut());
    keyboardShortcutService.addListener('resetZoom', () => this.resetZoom());

    // 平移
    keyboardShortcutService.addListener('panLeft', () => this.panLeft());
    keyboardShortcutService.addListener('panRight', () => this.panRight());

    // 显示控制
    keyboardShortcutService.addListener('toggleCrosshair', () =>
      this.toggleCrosshair(),
    );
    keyboardShortcutService.addListener('toggleGrid', () => this.toggleGrid());

    // 周期切换
    keyboardShortcutService.addListener('nextPeriod', () => this.nextPeriod());
    keyboardShortcutService.addListener('prevPeriod', () => this.prevPeriod());

    // 其他功能
    keyboardShortcutService.addListener('exportChart', () =>
      this.exportChart('png'),
    );
    keyboardShortcutService.addListener('fullscreen', () =>
      this.toggleFullscreen(),
    );
    keyboardShortcutService.addListener('togglePerformance', () =>
      this.togglePerformance(),
    );
  }

  /**
   * 放大
   */
  zoomIn(center?: number): void {
    if (!this.chartInstance || !this.isZoomEnabled) return;

    const timeScale = this.chartInstance.timeScale();
    const visibleRange = timeScale.getVisibleLogicalRange();

    if (visibleRange) {
      const currentRange = visibleRange.to - visibleRange.from;
      const newRange = currentRange * 0.8;
      const zoomCenter =
        center !== undefined
          ? center
          : (visibleRange.from + visibleRange.to) / 2;

      timeScale.setVisibleLogicalRange({
        from: zoomCenter - newRange / 2,
        to: zoomCenter + newRange / 2,
      });

      this.currentZoomLevel *= 1.25;
      this.notifyListeners('onZoom', this.currentZoomLevel, zoomCenter);
    }
  }

  /**
   * 缩小
   */
  zoomOut(center?: number): void {
    if (!this.chartInstance || !this.isZoomEnabled) return;

    const timeScale = this.chartInstance.timeScale();
    const visibleRange = timeScale.getVisibleLogicalRange();

    if (visibleRange) {
      const currentRange = visibleRange.to - visibleRange.from;
      const newRange = currentRange * 1.25;
      const zoomCenter =
        center !== undefined
          ? center
          : (visibleRange.from + visibleRange.to) / 2;

      timeScale.setVisibleLogicalRange({
        from: zoomCenter - newRange / 2,
        to: zoomCenter + newRange / 2,
      });

      this.currentZoomLevel *= 0.8;
      this.notifyListeners('onZoom', this.currentZoomLevel, zoomCenter);
    }
  }

  /**
   * 重置缩放
   */
  resetZoom(): void {
    if (!this.chartInstance) return;

    this.chartInstance.timeScale().fitContent();
    this.currentZoomLevel = 1;
    this.notifyListeners('onReset');
  }

  /**
   * 向左平移
   */
  panLeft(): void {
    if (!this.chartInstance || !this.isPanEnabled) return;

    const timeScale = this.chartInstance.timeScale();
    const visibleRange = timeScale.getVisibleLogicalRange();

    if (visibleRange) {
      const range = visibleRange.to - visibleRange.from;
      const shift = range * 0.2;

      timeScale.setVisibleLogicalRange({
        from: visibleRange.from - shift,
        to: visibleRange.to - shift,
      });

      this.notifyListeners('onPan', -shift);
    }
  }

  /**
   * 向右平移
   */
  panRight(): void {
    if (!this.chartInstance || !this.isPanEnabled) return;

    const timeScale = this.chartInstance.timeScale();
    const visibleRange = timeScale.getVisibleLogicalRange();

    if (visibleRange) {
      const range = visibleRange.to - visibleRange.from;
      const shift = range * 0.2;

      timeScale.setVisibleLogicalRange({
        from: visibleRange.from + shift,
        to: visibleRange.to + shift,
      });

      this.notifyListeners('onPan', shift);
    }
  }

  /**
   * 切换十字线
   */
  toggleCrosshair(): void {
    this.isCrosshairEnabled = !this.isCrosshairEnabled;
    this.updateCrosshairOptions();
    this.notifyListeners('onCrosshairToggle', this.isCrosshairEnabled);
  }

  /**
   * 切换网格
   */
  toggleGrid(): void {
    this.isGridEnabled = !this.isGridEnabled;

    if (this.chartInstance) {
      this.chartInstance.applyOptions({
        grid: {
          vertLines: {
            visible: this.isGridEnabled,
          },
          horzLines: {
            visible: this.isGridEnabled,
          },
        },
      });
    }

    this.notifyListeners('onGridToggle', this.isGridEnabled);
  }

  /**
   * 下一个时间周期
   */
  nextPeriod(): void {
    const periods = [
      '1m',
      '5m',
      '15m',
      '30m',
      '1h',
      '4h',
      '1d',
      '1w',
      '1M',
    ] as TimePeriod[];
    const currentIndex = periods.indexOf(this.currentTimePeriod);

    if (currentIndex < periods.length - 1) {
      const nextPeriod = periods[currentIndex + 1];
      this.currentTimePeriod = nextPeriod;
      this.notifyListeners('onPeriodChange', nextPeriod);
    }
  }

  /**
   * 上一个时间周期
   */
  prevPeriod(): void {
    const periods = [
      '1m',
      '5m',
      '15m',
      '30m',
      '1h',
      '4h',
      '1d',
      '1w',
      '1M',
    ] as TimePeriod[];
    const currentIndex = periods.indexOf(this.currentTimePeriod);

    if (currentIndex > 0) {
      const prevPeriod = periods[currentIndex - 1];
      this.currentTimePeriod = prevPeriod;
      this.notifyListeners('onPeriodChange', prevPeriod);
    }
  }

  /**
   * 导出图表
   */
  exportChart(format: string = 'png'): void {
    if (!this.chartInstance) return;

    try {
      let data: string | ArrayBuffer;

      switch (format) {
        case 'png':
        case 'jpeg':
          const canvas = this.chartInstance.takeScreenshot();
          data = canvas.toDataURL(`image/${format}`);
          break;
        case 'svg':
          // SVG导出需要特殊处理
          data = this.exportAsSVG();
          break;
        default:
          console.warn(`不支持的导出格式: ${format}`);
          return;
      }

      // 下载文件
      this.downloadFile(data, `chart-${Date.now()}.${format}`);
      this.notifyListeners('onExport', format);
    } catch (error) {
      console.error('导出图表失败:', error);
    }
  }

  /**
   * 导出为SVG（简化实现）
   */
  private exportAsSVG(): string {
    // 这是一个简化的SVG导出实现
    // 实际实现可能需要更复杂的处理
    return '<svg></svg>';
  }

  /**
   * 下载文件
   */
  private downloadFile(data: string | ArrayBuffer, filename: string): void {
    const blob =
      typeof data === 'string'
        ? new Blob([data], { type: 'application/octet-stream' })
        : new Blob([data]);

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /**
   * 切换全屏
   */
  toggleFullscreen(): void {
    const container = document.querySelector(
      '.kline-chart-container',
    ) as HTMLElement;

    if (!container) return;

    if (!document.fullscreenElement) {
      container.requestFullscreen().catch((error) => {
        console.error('进入全屏失败:', error);
      });
    } else {
      document.exitFullscreen();
    }

    const isFullscreen = !!document.fullscreenElement;
    this.notifyListeners('onFullscreen', isFullscreen);
  }

  /**
   * 切换性能监控
   */
  togglePerformance(): void {
    // 这个功能需要与性能监控组件配合实现
    const event = new CustomEvent('togglePerformanceMonitor');
    document.dispatchEvent(event);
    this.notifyListeners('onPerformanceToggle', true);
  }

  /**
   * 启用/禁用缩放
   */
  setZoomEnabled(enabled: boolean): void {
    this.isZoomEnabled = enabled;
    if (this.chartInstance) {
      this.setupChartInteractions();
    }
  }

  /**
   * 启用/禁用平移
   */
  setPanEnabled(enabled: boolean): void {
    this.isPanEnabled = enabled;
    if (this.chartInstance) {
      this.setupChartInteractions();
    }
  }

  /**
   * 设置十字线状态
   */
  setCrosshairEnabled(enabled: boolean): void {
    this.isCrosshairEnabled = enabled;
    this.updateCrosshairOptions();
  }

  /**
   * 设置网格状态
   */
  setGridEnabled(enabled: boolean): void {
    this.isGridEnabled = enabled;
    this.toggleGrid();
  }

  /**
   * 获取当前交互状态
   */
  getInteractionState(): {
    isZoomEnabled: boolean;
    isPanEnabled: boolean;
    currentZoomLevel: number;
    isCrosshairEnabled: boolean;
    isGridEnabled: boolean;
    currentTimePeriod: TimePeriod;
  } {
    return {
      isZoomEnabled: this.isZoomEnabled,
      isPanEnabled: this.isPanEnabled,
      currentZoomLevel: this.currentZoomLevel,
      isCrosshairEnabled: this.isCrosshairEnabled,
      isGridEnabled: this.isGridEnabled,
      currentTimePeriod: this.currentTimePeriod,
    };
  }

  /**
   * 清理资源
   */
  dispose(): void {
    this.listeners.clear();
    this.chartInstance = null;
  }
}

// 导出单例实例
export const chartInteractionService = new ChartInteractionService();
