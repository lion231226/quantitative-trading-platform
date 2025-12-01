import {
  DEFAULT_SIGNAL_THEMES,
  ISignalRenderer,
  MarkerOperation,
  MarkerShape,
  SignalMarkerStyle as MarkerStyle,
  SignalDifference,
  SignalMarkerStyle,
  StrategySignal,
  StrategySignalUtils,
} from '../types/strategySignal.types';

// Lightweight Charts types (simplified)
interface LightweightChart {
  addMarker(marker: any): void;
  removeMarker(markerId: string): void;
  removeMarkers(markerIds: string[]): void;
  getMarkers(): any[];
}

interface MarkerConfig {
  id: string;
  time: Date | string | number;
  position: 'aboveBar' | 'belowBar' | 'inBar';
  color: string;
  shape: 'circle' | 'square' | 'arrowUp' | 'arrowDown' | 'triangle';
  text?: string;
  size?: number;
  style?: any;
}

// 渲染器配置
export interface RendererConfig {
  maxMarkers: number;
  batchSize: number;
  animationEnabled: boolean;
  animationDuration: number;
  theme: 'light' | 'dark';
}

// 默认配置
const DEFAULT_RENDERER_CONFIG: RendererConfig = {
  maxMarkers: 1000,
  batchSize: 50,
  animationEnabled: true,
  animationDuration: 300,
  theme: 'light',
};

// 标记点状态
export interface MarkerState {
  signalId: string;
  markerId: string;
  chartId: string;
  signal: StrategySignal;
  marker?: any;
  isAnimating: boolean;
  createdAt: number;
}

// 渲染队列项
interface RenderQueueItem {
  type: 'add' | 'remove' | 'update' | 'clear';
  chartId: string;
  signalId?: string;
  signal?: StrategySignal;
  markerId?: string;
  callback?: () => void;
}

// Lightweight Charts标记点渲染器实现
export class LightweightChartSignalRenderer implements ISignalRenderer {
  private config: RendererConfig;
  private charts = new Map<string, LightweightChart>();
  private markers = new Map<string, MarkerState[]>(); // chartId -> MarkerState[]
  private renderQueue: RenderQueueItem[] = [];
  private isProcessing = false;
  private animationFrameId?: number;

  constructor(config: Partial<RendererConfig> = {}) {
    this.config = { ...DEFAULT_RENDERER_CONFIG, ...config };
    this.startRenderLoop();
  }

  /**
   * 注册图表实例
   */
  registerChart(chartId: string, chartInstance: LightweightChart): void {
    this.charts.set(chartId, chartInstance);
    this.markers.set(chartId, []);
  }

  /**
   * 注销图表实例
   */
  unregisterChart(chartId: string): void {
    this.clearMarkers(chartId);
    this.charts.delete(chartId);
    this.markers.delete(chartId);
  }

  /**
   * 添加标记点
   */
  async addMarkers(chartId: string, signals: StrategySignal[]): Promise<void> {
    const chart = this.charts.get(chartId);
    if (!chart) {
      throw new Error(`图表实例未找到: ${chartId}`);
    }

    const markers = this.markers.get(chartId) || [];

    // 检查标记点数量限制
    if (markers.length + signals.length > this.config.maxMarkers) {
      console.warn(
        `标记点数量超过限制 ${this.config.maxMarkers}，将移除最旧的标记点`,
      );
      this.removeOldestMarkers(chartId, signals.length);
    }

    // 分批添加标记点
    const batches = this.createBatches(signals, this.config.batchSize);

    for (const batch of batches) {
      await this.addMarkerBatch(chartId, batch);
    }
  }

  /**
   * 移除标记点
   */
  async removeMarkers(chartId: string, signalIds: string[]): Promise<void> {
    const chart = this.charts.get(chartId);
    if (!chart) {
      return;
    }

    const markers = this.markers.get(chartId) || [];
    const markerIds: string[] = [];

    // 查找对应的标记点ID
    for (const signalId of signalIds) {
      const markerState = markers.find((m) => m.signalId === signalId);
      if (markerState) {
        markerIds.push(markerState.markerId);
      }
    }

    if (markerIds.length > 0) {
      chart.removeMarkers(markerIds);

      // 更新内部状态
      const updatedMarkers = markers.filter(
        (m) => !signalIds.includes(m.signalId),
      );
      this.markers.set(chartId, updatedMarkers);
    }
  }

  /**
   * 更新标记点
   */
  async updateMarkers(
    chartId: string,
    signals: StrategySignal[],
  ): Promise<void> {
    const chart = this.charts.get(chartId);
    if (!chart) {
      return;
    }

    const markers = this.markers.get(chartId) || [];
    const toRemove: string[] = [];
    const toAdd: StrategySignal[] = [];

    for (const signal of signals) {
      const existingMarker = markers.find((m) => m.signalId === signal.id);

      if (existingMarker) {
        // 如果信号发生了显著变化，先移除再添加
        if (this.hasSignificantChange(existingMarker.signal, signal)) {
          toRemove.push(signal.id);
          toAdd.push(signal);
        }
      } else {
        // 新信号，直接添加
        toAdd.push(signal);
      }
    }

    // 先移除，再添加
    if (toRemove.length > 0) {
      await this.removeMarkers(chartId, toRemove);
    }

    if (toAdd.length > 0) {
      await this.addMarkers(chartId, toAdd);
    }
  }

  /**
   * 清空所有标记点
   */
  async clearMarkers(chartId: string): Promise<void> {
    const chart = this.charts.get(chartId);
    if (!chart) {
      return;
    }

    const markers = this.markers.get(chartId) || [];
    const markerIds = markers.map((m) => m.markerId);

    if (markerIds.length > 0) {
      chart.removeMarkers(markerIds);
      this.markers.set(chartId, []);
    }
  }

  /**
   * 动画处理标记点过渡
   */
  async animateMarkerTransition(
    chartId: string,
    diff: SignalDifference,
  ): Promise<void> {
    if (!this.config.animationEnabled) {
      // 如果动画禁用，直接执行更新
      await this.updateMarkers(chartId, diff.added);
      await this.removeMarkers(
        chartId,
        diff.removed.map((s) => s.id),
      );
      return;
    }

    const chart = this.charts.get(chartId);
    if (!chart) {
      return;
    }

    const animations: Promise<void>[] = [];

    // 处理新增的标记点（淡入动画）
    if (diff.added.length > 0) {
      animations.push(this.animateMarkerAdd(chartId, diff.added));
    }

    // 处理移除的标记点（淡出动画）
    if (diff.removed.length > 0) {
      animations.push(this.animateMarkerRemove(chartId, diff.removed));
    }

    // 处理修改的标记点（变换动画）
    if (diff.modified.length > 0) {
      animations.push(this.animateMarkerUpdate(chartId, diff.modified));
    }

    await Promise.all(animations);
  }

  /**
   * 批量更新标记点
   */
  async batchUpdateMarkers(
    chartId: string,
    operations: MarkerOperation[],
  ): Promise<void> {
    const chart = this.charts.get(chartId);
    if (!chart) {
      return;
    }

    // 将操作分组以提高效率
    const adds: StrategySignal[] = [];
    const removes: string[] = [];
    const updates: StrategySignal[] = [];

    for (const operation of operations) {
      switch (operation.type) {
        case 'add':
          adds.push(operation.signal);
          break;
        case 'remove':
          removes.push(operation.signalId);
          break;
        case 'update':
          updates.push(operation.signal);
          break;
        case 'clear':
          await this.clearMarkers(chartId);
          return;
      }
    }

    // 按顺序执行操作
    if (removes.length > 0) {
      await this.removeMarkers(chartId, removes);
    }

    if (updates.length > 0) {
      await this.updateMarkers(chartId, updates);
    }

    if (adds.length > 0) {
      await this.addMarkers(chartId, adds);
    }
  }

  /**
   * 获取图表上的所有标记点
   */
  getMarkers(chartId: string): MarkerState[] {
    return (this.markers.get(chartId) || []).slice(); // 返回副本
  }

  /**
   * 获取标记点统计
   */
  getMarkerStats(chartId: string): {
    totalMarkers: number;
    animatingMarkers: number;
    oldestMarker: number;
    newestMarker: number;
  } {
    const markers = this.markers.get(chartId) || [];

    const animatingCount = markers.filter((m) => m.isAnimating).length;
    const timestamps = markers.map((m) => m.createdAt).filter((t) => t > 0);

    return {
      totalMarkers: markers.length,
      animatingMarkers: animatingCount,
      oldestMarker: timestamps.length > 0 ? Math.min(...timestamps) : 0,
      newestMarker: timestamps.length > 0 ? Math.max(...timestamps) : 0,
    };
  }

  /**
   * 设置配置
   */
  updateConfig(newConfig: Partial<RendererConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  /**
   * 销毁渲染器
   */
  destroy(): void {
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
    }

    // 清理所有图表
    for (const chartId of this.charts.keys()) {
      this.unregisterChart(chartId);
    }

    this.charts.clear();
    this.markers.clear();
    this.renderQueue = [];
  }

  /**
   * 私有方法：创建标记点配置
   */
  private createMarkerConfig(
    signal: StrategySignal,
    style: MarkerStyle,
  ): MarkerConfig {
    const markerShape = this.mapSignalShapeToMarkerShape(style.shape);
    const time = new Date(signal.timestamp);

    return {
      id: signal.id,
      time: this.formatTimeForChart(time),
      position: this.getMarkerPosition(signal.signalType),
      color: style.color,
      shape: markerShape,
      text: StrategySignalUtils.formatSignalLabel(signal),
      size: style.size,
    };
  }

  /**
   * 私有方法：获取标记点位置
   */
  private getMarkerPosition(
    signalType: string,
  ): 'aboveBar' | 'belowBar' | 'inBar' {
    switch (signalType) {
      case 'buy':
      case 'take_profit':
        return 'aboveBar';
      case 'sell':
      case 'stop_loss':
        return 'belowBar';
      case 'hold':
        return 'inBar';
      default:
        return 'aboveBar';
    }
  }

  /**
   * 私有方法：映射信号形状到标记点形状
   */
  private mapSignalShapeToMarkerShape(
    shape: MarkerShape,
  ): MarkerConfig['shape'] {
    const shapeMap: Record<MarkerShape, MarkerConfig['shape']> = {
      circle: 'circle',
      square: 'square',
      triangle: 'triangle',
      arrow_up: 'arrowUp',
      arrow_down: 'arrowDown',
      diamond: 'circle', // Lightweight Charts没有diamond，使用circle替代
      star: 'circle', // Lightweight Charts没有star，使用circle替代
    };

    return shapeMap[shape] || 'circle';
  }

  /**
   * 私有方法：格式化时间用于图表
   */
  private formatTimeForChart(time: Date): Date | string | number {
    // Lightweight Charts支持多种时间格式
    return time;
  }

  /**
   * 私有方法：添加标记点批次
   */
  private async addMarkerBatch(
    chartId: string,
    signals: StrategySignal[],
  ): Promise<void> {
    const chart = this.charts.get(chartId);
    const markers = this.markers.get(chartId) || [];

    if (!chart) {
      return;
    }

    const theme = DEFAULT_SIGNAL_THEMES[this.config.theme];
    const newMarkers: MarkerState[] = [];

    for (const signal of signals) {
      try {
        // 获取信号样式
        const style = theme[signal.signalType] || theme.buy;

        // 创建标记点配置
        const markerConfig = this.createMarkerConfig(signal, style);

        // 添加标记点到图表
        chart.addMarker(markerConfig);

        // 创建标记点状态
        const markerState: MarkerState = {
          signalId: signal.id,
          markerId: signal.id,
          chartId,
          signal,
          isAnimating: false,
          createdAt: Date.now(),
        };

        newMarkers.push(markerState);
      } catch (error) {
        console.error(`添加标记点失败 ${signal.id}:`, error);
      }
    }

    // 更新内部状态
    this.markers.set(chartId, [...markers, ...newMarkers]);
  }

  /**
   * 私有方法：移除最旧的标记点
   */
  private removeOldestMarkers(chartId: string, count: number): void {
    const markers = this.markers.get(chartId) || [];

    if (markers.length <= count) {
      this.clearMarkers(chartId);
      return;
    }

    // 按创建时间排序，移除最旧的
    const sortedMarkers = [...markers].sort(
      (a, b) => a.createdAt - b.createdAt,
    );
    const toRemove = sortedMarkers.slice(0, count);
    const signalIds = toRemove.map((m) => m.signalId);

    this.removeMarkers(chartId, signalIds);
  }

  /**
   * 私有方法：创建批次
   */
  private createBatches<T>(items: T[], batchSize: number): T[][] {
    const batches: T[][] = [];
    for (let i = 0; i < items.length; i += batchSize) {
      batches.push(items.slice(i, i + batchSize));
    }
    return batches;
  }

  /**
   * 私有方法：检查信号是否有显著变化
   */
  private hasSignificantChange(
    oldSignal: StrategySignal,
    newSignal: StrategySignal,
  ): boolean {
    return (
      oldSignal.signalType !== newSignal.signalType ||
      oldSignal.confidence !== newSignal.confidence ||
      Math.abs(oldSignal.price - newSignal.price) > 0.01
    );
  }

  /**
   * 私有方法：标记点添加动画
   */
  private async animateMarkerAdd(
    chartId: string,
    signals: StrategySignal[],
  ): Promise<void> {
    const markers = this.markers.get(chartId) || [];

    // 标记新添加的标记点为动画状态
    for (const signal of signals) {
      const markerState = markers.find((m) => m.signalId === signal.id);
      if (markerState) {
        markerState.isAnimating = true;
      }
    }

    // 使用CSS动画或自定义动画逻辑
    await this.performAnimation(
      chartId,
      'fadeIn',
      signals.map((s) => s.id),
    );

    // 动画完成，更新状态
    for (const signal of signals) {
      const markerState = markers.find((m) => m.signalId === signal.id);
      if (markerState) {
        markerState.isAnimating = false;
      }
    }
  }

  /**
   * 私有方法：标记点移除动画
   */
  private async animateMarkerRemove(
    chartId: string,
    signals: StrategySignal[],
  ): Promise<void> {
    // 执行淡出动画
    await this.performAnimation(
      chartId,
      'fadeOut',
      signals.map((s) => s.id),
    );

    // 动画完成后移除标记点
    await this.removeMarkers(
      chartId,
      signals.map((s) => s.id),
    );
  }

  /**
   * 私有方法：标记点更新动画
   */
  private async animateMarkerUpdate(
    chartId: string,
    modifications: Array<{ old: StrategySignal; new: StrategySignal }>,
  ): Promise<void> {
    const signalIds = modifications.map((m) => m.new.id);

    // 执行更新动画
    await this.performAnimation(chartId, 'transform', signalIds);

    // 动画完成后更新标记点
    await this.updateMarkers(
      chartId,
      modifications.map((m) => m.new),
    );
  }

  /**
   * 私有方法：执行动画
   */
  private async performAnimation(
    chartId: string,
    animationType: 'fadeIn' | 'fadeOut' | 'transform',
    signalIds: string[],
  ): Promise<void> {
    return new Promise((resolve) => {
      // 简化实现：使用setTimeout模拟动画
      // 在实际实现中，可以使用CSS transitions或Web Animations API

      const duration = this.config.animationDuration;

      switch (animationType) {
        case 'fadeIn':
          // 触发淡入动画
          this.triggerMarkerAnimation(chartId, signalIds, {
            opacity: [0, 1],
            scale: [0.8, 1],
            duration,
          });
          break;
        case 'fadeOut':
          // 触发淡出动画
          this.triggerMarkerAnimation(chartId, signalIds, {
            opacity: [1, 0],
            scale: [1, 0.8],
            duration,
          });
          break;
        case 'transform':
          // 触发变换动画
          this.triggerMarkerAnimation(chartId, signalIds, {
            scale: [1, 1.2, 1],
            duration,
          });
          break;
      }

      setTimeout(resolve, duration);
    });
  }

  /**
   * 私有方法：触发标记点动画
   */
  private triggerMarkerAnimation(
    chartId: string,
    signalIds: string[],
    animationConfig: any,
  ): void {
    // 这里可以实现具体的DOM操作来触发动画
    // 由于Lightweight Charts是Canvas-based，动画可能需要特殊处理

    console.log(`触发动画 ${chartId}:`, {
      signalIds,
      animation: animationConfig,
    });
  }

  /**
   * 私有方法：启动渲染循环
   */
  private startRenderLoop(): void {
    const processQueue = () => {
      if (this.renderQueue.length > 0 && !this.isProcessing) {
        this.isProcessing = true;
        this.processRenderQueue();
      }

      this.animationFrameId = requestAnimationFrame(processQueue);
    };

    this.animationFrameId = requestAnimationFrame(processQueue);
  }

  /**
   * 私有方法：处理渲染队列
   */
  private async processRenderQueue(): Promise<void> {
    const batch = this.renderQueue.splice(0, 10); // 每次处理10个项目

    for (const item of batch) {
      try {
        await this.processRenderItem(item);
      } catch (error) {
        console.error('处理渲染队列项失败:', error);
      }
    }

    this.isProcessing = false;
  }

  /**
   * 私有方法：处理渲染队列项
   */
  private async processRenderItem(item: RenderQueueItem): Promise<void> {
    switch (item.type) {
      case 'add':
        if (item.signal) {
          await this.addMarkers(item.chartId, [item.signal]);
        }
        break;
      case 'remove':
        if (item.signalId) {
          await this.removeMarkers(item.chartId, [item.signalId]);
        }
        break;
      case 'update':
        if (item.signal) {
          await this.updateMarkers(item.chartId, [item.signal]);
        }
        break;
      case 'clear':
        await this.clearMarkers(item.chartId);
        break;
    }

    if (item.callback) {
      item.callback();
    }
  }
}

// 导出单例实例
export const signalRenderer = new LightweightChartSignalRenderer();
