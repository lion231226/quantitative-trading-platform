import { DeviceInfo, NetworkInfo } from '@/types/ux.types';

/**
 * 移动端适配辅助函数
 */

// 检测是否为移动设备
export function isMobileDevice(): boolean {
  const userAgent = navigator.userAgent.toLowerCase();
  return /mobile|android|iphone|ipod|blackberry|iemobile|opera mini/i.test(userAgent);
}

// 检测是否为平板设备
export function isTabletDevice(): boolean {
  const userAgent = navigator.userAgent.toLowerCase();
  return /ipad|android(?!.*mobile)/i.test(userAgent);
}

// 检测是否为桌面设备
export function isDesktopDevice(): boolean {
  return !isMobileDevice() && !isTabletDevice();
}

// 获取设备信息
export function getDeviceInfo(): DeviceInfo {
  const userAgent = navigator.userAgent;
  const isMobile = isMobileDevice();
  const isTablet = isTabletDevice();
  const isDesktop = isDesktopDevice();

  return {
    isMobile,
    isTablet,
    isDesktop,
    userAgent,
    screenResolution: `${screen.width}x${screen.height}`,
    viewportSize: {
      width: window.innerWidth,
      height: window.innerHeight,
    },
    pixelRatio: window.devicePixelRatio || 1,
    touchSupport: 'ontouchstart' in window,
    orientation: window.innerHeight > window.innerWidth ? 'portrait' : 'landscape',
  };
}

// 获取网络信息
export function getNetworkInfo(): NetworkInfo {
  const connection = (navigator as any).connection ||
                    (navigator as any).mozConnection ||
                    (navigator as any).webkitConnection;

  return {
    online: navigator.onLine,
    effectiveType: connection?.effectiveType,
    downlink: connection?.downlink,
    rtt: connection?.rtt,
    saveData: connection?.saveData,
    connectionType: connection?.type,
  };
}

// 获取屏幕尺寸分类
export function getScreenSize(): 'xs' | 'sm' | 'md' | 'lg' | 'xl' {
  const width = window.innerWidth;
  if (width < 640) return 'xs';
  if (width < 768) return 'sm';
  if (width < 1024) return 'md';
  if (width < 1280) return 'lg';
  return 'xl';
}

// 检测是否为小屏幕
export function isSmallScreen(): boolean {
  return getScreenSize() === 'xs' || getScreenSize() === 'sm';
}

// 检测是否为中等屏幕
export function isMediumScreen(): boolean {
  return getScreenSize() === 'md';
}

// 检测是否为大屏幕
export function isLargeScreen(): boolean {
  return getScreenSize() === 'lg' || getScreenSize() === 'xl';
}

// 获取响应式断点
export const breakpoints = {
  xs: 0,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
};

// 根据屏幕尺寸获取响应式值
export function getResponsiveValue<T>(values: {
  xs?: T;
  sm?: T;
  md?: T;
  lg?: T;
  xl?: T;
}): T | undefined {
  const screenSize = getScreenSize();
  return values[screenSize] ||
         values.lg ||
         values.md ||
         values.sm ||
         values.xs;
}

// 格式化移动端数字
export function formatMobileNumber(num: number, options: {
  compact?: boolean;
  precision?: number;
} = {}): string {
  const { compact = true, precision = 1 } = options;

  if (compact) {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(precision)}M`;
    }
    if (num >= 1000) {
      return `${(num / 1000).toFixed(precision)}K`;
    }
  }

  return num.toLocaleString('zh-CN');
}

// 获取移动端优化的CSS类名
export function getMobileClassName(baseClass: string, modifiers: {
  mobile?: string;
  tablet?: string;
  desktop?: string;
} = {}): string {
  const deviceInfo = getDeviceInfo();
  let className = baseClass;

  if (deviceInfo.isMobile && modifiers.mobile) {
    className += ` ${modifiers.mobile}`;
  } else if (deviceInfo.isTablet && modifiers.tablet) {
    className += ` ${modifiers.tablet}`;
  } else if (deviceInfo.isDesktop && modifiers.desktop) {
    className += ` ${modifiers.desktop}`;
  }

  return className;
}

// 防抖函数（移动端优化）
export function createMobileDebounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  immediate = false
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      if (!immediate) func(...args);
    };

    const callNow = immediate && !timeout;

    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(later, wait);

    if (callNow) func(...args);
  };
}

// 节流函数（移动端优化）
export function createMobileThrottle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;

  return function executedFunction(...args: Parameters<T>) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

// 触摸事件处理
export class TouchHandler {
  private startX: number = 0;
  private startY: number = 0;
  private startTime: number = 0;
  private callbacks: {
    onSwipeLeft?: () => void;
    onSwipeRight?: () => void;
    onSwipeUp?: () => void;
    onSwipeDown?: () => void;
    onTap?: () => void;
    onLongPress?: () => void;
  } = {};

  constructor(callbacks: {
    onSwipeLeft?: () => void;
    onSwipeRight?: () => void;
    onSwipeUp?: () => void;
    onSwipeDown?: () => void;
    onTap?: () => void;
    onLongPress?: () => void;
  } = {}) {
    this.callbacks = callbacks;
  }

  handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      const touch = e.touches[0];
      this.startX = touch.clientX;
      this.startY = touch.clientY;
      this.startTime = Date.now();
    }
  };

  handleTouchEnd = (e: React.TouchEvent) => {
    if (e.changedTouches.length === 1) {
      const touch = e.changedTouches[0];
      const endX = touch.clientX;
      const endY = touch.clientY;
      const endTime = Date.now();

      const deltaX = endX - this.startX;
      const deltaY = endY - this.startY;
      const deltaTime = endTime - this.startTime;

      const minSwipeDistance = 50;
      const maxSwipeTime = 300;
      const maxTapDistance = 10;
      const minLongPressTime = 500;

      // 检测滑动
      if (Math.abs(deltaX) > minSwipeDistance && deltaTime < maxSwipeTime) {
        if (deltaX > 0 && this.callbacks.onSwipeRight) {
          this.callbacks.onSwipeRight();
        } else if (deltaX < 0 && this.callbacks.onSwipeLeft) {
          this.callbacks.onSwipeLeft();
        }
      }

      if (Math.abs(deltaY) > minSwipeDistance && deltaTime < maxSwipeTime) {
        if (deltaY > 0 && this.callbacks.onSwipeDown) {
          this.callbacks.onSwipeDown();
        } else if (deltaY < 0 && this.callbacks.onSwipeUp) {
          this.callbacks.onSwipeUp();
        }
      }

      // 检测点击
      if (Math.abs(deltaX) < maxTapDistance &&
          Math.abs(deltaY) < maxTapDistance &&
          deltaTime < maxSwipeTime &&
          this.callbacks.onTap) {
        this.callbacks.onTap();
      }

      // 检测长按
      if (Math.abs(deltaX) < maxTapDistance &&
          Math.abs(deltaY) < maxTapDistance &&
          deltaTime >= minLongPressTime &&
          this.callbacks.onLongPress) {
        this.callbacks.onLongPress();
      }
    }
  };

  updateCallbacks(newCallbacks: Partial<typeof this.callbacks>) {
    this.callbacks = { ...this.callbacks, ...newCallbacks };
  }
}

// 移动端图片优化
export function getOptimizedImageUrl(url: string, options: {
  width?: number;
  height?: number;
  quality?: number;
  format?: 'webp' | 'jpg' | 'png';
} = {}): string {
  const { width, height, quality = 80, format = 'webp' } = options;

  // 如果是相对路径，添加CDN前缀
  if (url.startsWith('/')) {
    const baseUrl = process.env.NEXT_PUBLIC_CDN_URL || '';
    url = baseUrl + url;
  }

  // 添加图片优化参数
  const params = new URLSearchParams();
  if (width) params.set('w', width.toString());
  if (height) params.set('h', height.toString());
  params.set('q', quality.toString());
  params.set('f', format);

  const paramString = params.toString();
  return paramString ? `${url}?${paramString}` : url;
}

// 移动端性能优化
export class MobilePerformanceOptimizer {
  private static instance: MobilePerformanceOptimizer;
  private metrics: Array<{ name: string; value: number; timestamp: number }> = [];

  static getInstance(): MobilePerformanceOptimizer {
    if (!MobilePerformanceOptimizer.instance) {
      MobilePerformanceOptimizer.instance = new MobilePerformanceOptimizer();
    }
    return MobilePerformanceOptimizer.instance;
  }

  // 记录性能指标
  recordMetric(name: string, value: number): void {
    this.metrics.push({
      name,
      value,
      timestamp: Date.now(),
    });

    // 保持最近100个指标
    if (this.metrics.length > 100) {
      this.metrics = this.metrics.slice(-100);
    }
  }

  // 获取平均性能指标
  getAverageMetric(name: string, timeWindow: number = 60000): number | null {
    const now = Date.now();
    const recentMetrics = this.metrics.filter(
      metric => metric.name === name && (now - metric.timestamp) < timeWindow
    );

    if (recentMetrics.length === 0) return null;

    return recentMetrics.reduce((sum, metric) => sum + metric.value, 0) / recentMetrics.length;
  }

  // 检测性能问题
  detectPerformanceIssues(): Array<{ type: string; severity: 'low' | 'medium' | 'high'; message: string }> {
    const issues: Array<{ type: string; severity: 'low' | 'medium' | 'high'; message: string }> = [];

    // 检查渲染时间
    const avgRenderTime = this.getAverageMetric('renderTime');
    if (avgRenderTime && avgRenderTime > 100) {
      issues.push({
        type: 'render_performance',
        severity: avgRenderTime > 200 ? 'high' : 'medium',
        message: `平均渲染时间过长: ${avgRenderTime.toFixed(2)}ms`,
      });
    }

    // 检查API响应时间
    const avgApiResponseTime = this.getAverageMetric('apiResponseTime');
    if (avgApiResponseTime && avgApiResponseTime > 1000) {
      issues.push({
        type: 'api_performance',
        severity: avgApiResponseTime > 3000 ? 'high' : 'medium',
        message: `API响应时间过长: ${avgApiResponseTime.toFixed(2)}ms`,
      });
    }

    // 检查内存使用
    const memoryUsage = this.getMemoryUsage();
    if (memoryUsage && memoryUsage > 50) {
      issues.push({
        type: 'memory_usage',
        severity: memoryUsage > 100 ? 'high' : 'medium',
        message: `内存使用过高: ${memoryUsage}MB`,
      });
    }

    return issues;
  }

  // 获取内存使用情况
  private getMemoryUsage(): number | null {
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      return Math.round(memory.usedJSHeapSize / 1048576); // MB
    }
    return null;
  }

  // 清理资源
  cleanup(): void {
    this.metrics = [];
  }
}

// 移动端调试工具
export class MobileDebugger {
  private static instance: MobileDebugger;
  private logs: Array<{ level: 'log' | 'warn' | 'error'; message: string; timestamp: number }> = [];

  static getInstance(): MobileDebugger {
    if (!MobileDebugger.instance) {
      MobileDebugger.instance = new MobileDebugger();
    }
    return MobileDebugger.instance;
  }

  // 记录日志
  log(message: string): void {
    this.logs.push({
      level: 'log',
      message,
      timestamp: Date.now(),
    });
    console.log(`[Mobile Debug] ${message}`);
  }

  // 记录警告
  warn(message: string): void {
    this.logs.push({
      level: 'warn',
      message,
      timestamp: Date.now(),
    });
    console.warn(`[Mobile Debug] ${message}`);
  }

  // 记录错误
  error(message: string): void {
    this.logs.push({
      level: 'error',
      message,
      timestamp: Date.now(),
    });
    console.error(`[Mobile Debug] ${message}`);
  }

  // 获取日志
  getLogs(): Array<{ level: 'log' | 'warn' | 'error'; message: string; timestamp: number }> {
    return [...this.logs];
  }

  // 清理日志
  clearLogs(): void {
    this.logs = [];
  }

  // 导出日志
  exportLogs(): string {
    return this.logs.map(log =>
      `[${new Date(log.timestamp).toISOString()}] ${log.level.toUpperCase()}: ${log.message}`
    ).join('\n');
  }
}

// 导出所有工具
export const mobileHelpers = {
  isMobileDevice,
  isTabletDevice,
  isDesktopDevice,
  getDeviceInfo,
  getNetworkInfo,
  getScreenSize,
  isSmallScreen,
  isMediumScreen,
  isLargeScreen,
  breakpoints,
  getResponsiveValue,
  formatMobileNumber,
  getMobileClassName,
  createMobileDebounce,
  createMobileThrottle,
  TouchHandler,
  getOptimizedImageUrl,
  MobilePerformanceOptimizer,
  MobileDebugger,
};