import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import { PerformanceMetrics } from '@/types/performance.types';

/**
 * 性能优化辅助函数集合
 */

// 防抖函数
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  immediate = false,
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

// 节流函数
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number,
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;

  return function executedFunction(...args: Parameters<T>) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

// 深度比较对象
export function deepEqual(obj1: any, obj2: any): boolean {
  if (obj1 === obj2) return true;

  if (obj1 == null || obj2 == null) return false;

  if (typeof obj1 !== typeof obj2) return false;

  if (typeof obj1 !== 'object') return obj1 === obj2;

  const keys1 = Object.keys(obj1);
  const keys2 = Object.keys(obj2);

  if (keys1.length !== keys2.length) return false;

  for (const key of keys1) {
    if (!keys2.includes(key)) return false;
    if (!deepEqual(obj1[key], obj2[key])) return false;
  }

  return true;
}

// 内存使用监控
export function getMemoryUsage(): {
  used: number;
  total: number;
  percentage: number;
} | null {
  if ('memory' in performance) {
    const memory = (performance as any).memory;
    return {
      used: Math.round(memory.usedJSHeapSize / 1048576), // MB
      total: Math.round(memory.totalJSHeapSize / 1048576), // MB
      percentage: Math.round(
        (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100,
      ),
    };
  }
  return null;
}

// 页面加载性能分析
export function analyzePagePerformance(): {
  domContentLoaded: number;
  loadComplete: number;
  firstPaint: number;
  firstContentfulPaint: number;
  largestContentfulPaint: number;
} | null {
  if (!('performance' in window)) return null;

  const navigation = performance.getEntriesByType(
    'navigation',
  )[0] as PerformanceNavigationTiming;
  const paintEntries = performance.getEntriesByType('paint');

  const domContentLoaded = navigation
    ? navigation.domContentLoadedEventEnd -
      navigation.domContentLoadedEventStart
    : 0;
  const loadComplete = navigation
    ? navigation.loadEventEnd - navigation.loadEventStart
    : 0;

  const firstPaint =
    paintEntries.find((entry) => entry.name === 'first-paint')?.startTime || 0;
  const firstContentfulPaint =
    paintEntries.find((entry) => entry.name === 'first-contentful-paint')
      ?.startTime || 0;

  // 获取LCP需要PerformanceObserver
  let largestContentfulPaint = 0;
  try {
    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lastEntry = entries[entries.length - 1];
      largestContentfulPaint = lastEntry.startTime;
    });
    observer.observe({ entryTypes: ['largest-contentful-paint'] });
  } catch (e) {
    // LCP not supported
  }

  return {
    domContentLoaded,
    loadComplete,
    firstPaint,
    firstContentfulPaint,
    largestContentfulPaint,
  };
}

// 生成唯一ID
export function generateId(prefix = 'id'): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// 格式化文件大小
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

// 格式化时间
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`;
  return `${(ms / 3600000).toFixed(1)}h`;
}

// 获取网络信息
export function getNetworkInfo(): {
  effectiveType?: string;
  downlink?: number;
  rtt?: number;
  saveData?: boolean;
} | null {
  if ('connection' in navigator) {
    const connection = (navigator as any).connection;
    return {
      effectiveType: connection.effectiveType,
      downlink: connection.downlink,
      rtt: connection.rtt,
      saveData: connection.saveData,
    };
  }
  return null;
}

// 检测设备类型
export function getDeviceInfo(): {
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  userAgent: string;
  screenResolution: string;
} {
  const userAgent = navigator.userAgent.toLowerCase();
  const isMobile =
    /mobile|android|iphone|ipod|blackberry|iemobile|opera mini/i.test(
      userAgent,
    );
  const isTablet = /ipad|android(?!.*mobile)/i.test(userAgent);
  const isDesktop = !isMobile && !isTablet;

  return {
    isMobile,
    isTablet,
    isDesktop,
    userAgent: navigator.userAgent,
    screenResolution: `${screen.width}x${screen.height}`,
  };
}

// 检测浏览器信息
export function getBrowserInfo(): {
  name: string;
  version: string;
  engine: string;
} {
  const userAgent = navigator.userAgent;
  let name = 'Unknown';
  let version = 'Unknown';
  let engine = 'Unknown';

  // 检测浏览器名称
  if (userAgent.indexOf('Chrome') > -1) {
    name = 'Chrome';
    version = userAgent.match(/Chrome\/(\d+)/)?.[1] || 'Unknown';
    engine = 'Blink';
  } else if (userAgent.indexOf('Safari') > -1) {
    name = 'Safari';
    version = userAgent.match(/Safari\/(\d+)/)?.[1] || 'Unknown';
    engine = 'WebKit';
  } else if (userAgent.indexOf('Firefox') > -1) {
    name = 'Firefox';
    version = userAgent.match(/Firefox\/(\d+)/)?.[1] || 'Unknown';
    engine = 'Gecko';
  } else if (userAgent.indexOf('Edge') > -1) {
    name = 'Edge';
    version = userAgent.match(/Edge\/(\d+)/)?.[1] || 'Unknown';
    engine = 'EdgeHTML';
  }

  return { name, version, engine };
}

// 缓存管理
export class CacheManager<T = any> {
  private cache = new Map<
    string,
    { data: T; timestamp: number; ttl: number }
  >();

  set(key: string, data: T, ttl: number = 300000): void {
    // 默认5分钟
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl,
    });
  }

  get(key: string): T | null {
    const item = this.cache.get(key);
    if (!item) return null;

    if (Date.now() - item.timestamp > item.ttl) {
      this.cache.delete(key);
      return null;
    }

    return item.data;
  }

  delete(key: string): boolean {
    return this.cache.delete(key);
  }

  clear(): void {
    this.cache.clear();
  }

  // 清理过期缓存
  cleanup(): void {
    const now = Date.now();
    for (const [key, item] of this.cache.entries()) {
      if (now - item.timestamp > item.ttl) {
        this.cache.delete(key);
      }
    }
  }

  size(): number {
    return this.cache.size;
  }

  keys(): string[] {
    return Array.from(this.cache.keys());
  }
}

// 图片懒加载观察器
export class LazyLoadObserver {
  private observer: IntersectionObserver;
  private callbacks = new Map<Element, () => void>();

  constructor(options: IntersectionObserverInit = {}) {
    this.observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const callback = this.callbacks.get(entry.target);
            if (callback) {
              callback();
              this.observer.unobserve(entry.target);
              this.callbacks.delete(entry.target);
            }
          }
        });
      },
      {
        rootMargin: '50px',
        threshold: 0.1,
        ...options,
      },
    );
  }

  observe(element: Element, callback: () => void): void {
    this.callbacks.set(element, callback);
    this.observer.observe(element);
  }

  unobserve(element: Element): void {
    this.observer.unobserve(element);
    this.callbacks.delete(element);
  }

  disconnect(): void {
    this.observer.disconnect();
    this.callbacks.clear();
  }
}

// 请求队列管理器
export class RequestQueue {
  private queue: Array<() => Promise<any>> = [];
  private isProcessing = false;
  private maxConcurrent = 3;
  private currentRequests = 0;

  constructor(maxConcurrent = 3) {
    this.maxConcurrent = maxConcurrent;
  }

  add<T>(request: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push(async () => {
        try {
          const result = await request();
          resolve(result);
        } catch (error) {
          reject(error);
        }
      });

      this.process();
    });
  }

  private async process(): Promise<void> {
    if (this.isProcessing || this.currentRequests >= this.maxConcurrent) return;

    this.isProcessing = true;

    while (this.queue.length > 0 && this.currentRequests < this.maxConcurrent) {
      const request = this.queue.shift();
      if (request) {
        this.currentRequests++;

        request().finally(() => {
          this.currentRequests--;
          this.process();
        });
      }
    }

    this.isProcessing = false;
  }

  clear(): void {
    this.queue = [];
  }

  size(): number {
    return this.queue.length;
  }
}

// React Hooks for UX optimization

/**
 * 性能优化的memo Hook
 */
export function useMemoWithCompare<T>(
  factory: () => T,
  deps: React.DependencyList,
  compareFn?: (
    prevDeps: React.DependencyList,
    nextDeps: React.DependencyList,
  ) => boolean,
): T {
  const ref = useRef<{ deps: React.DependencyList; value: T }>();

  if (!ref.current || !compareFn?.(ref.current.deps, deps)) {
    ref.current = { deps, value: factory() };
  }

  return ref.current.value;
}

/**
 * 防抖Hook
 */
export function useDebouncedCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number,
  deps: React.DependencyList = [],
): T {
  const callbackRef = useRef(callback);
  const timeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  return useCallback((...args: Parameters<T>) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      callbackRef.current(...args);
    }, delay);
  }, deps) as T;
}

/**
 * 节流Hook
 */
export function useThrottledCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number,
  deps: React.DependencyList = [],
): T {
  const callbackRef = useRef(callback);
  const lastRun = useRef(Date.now());

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  return useCallback((...args: Parameters<T>) => {
    if (Date.now() - lastRun.current >= delay) {
      callbackRef.current(...args);
      lastRun.current = Date.now();
    }
  }, deps) as T;
}

/**
 * 防抖值Hook
 */
export function useDebouncedValue<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// 修复useState导入问题
function useState<T>(initialValue: T): [T, (value: T) => void] {
  return React.useState(initialValue);
}

// 导出所有工具函数和服务
export const uxHelpers = {
  debounce,
  throttle,
  deepEqual,
  getMemoryUsage,
  analyzePagePerformance,
  generateId,
  formatFileSize,
  formatDuration,
  getNetworkInfo,
  getDeviceInfo,
  getBrowserInfo,
  CacheManager,
  LazyLoadObserver,
  RequestQueue,
  useMemoWithCompare,
  useDebouncedCallback,
  useThrottledCallback,
  useDebouncedValue,
};
