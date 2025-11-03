import { UseQueryOptions, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useMemo, useRef, useEffect } from 'react';
import { marketDataAPI } from '@/lib/api';

// UX相关类型定义
export interface UXMetrics {
  componentRenderTime: number;
  apiResponseTime: number;
  userInteractionTime: number;
  memoryUsage?: number;
  timestamp: string;
  componentName: string;
  actionType: 'render' | 'api_call' | 'user_interaction' | 'navigation';
}

export interface UserBehaviorData {
  sessionId: string;
  userId?: string;
  pagePath: string;
  actionType: 'click' | 'scroll' | 'hover' | 'form_submit' | 'navigation';
  elementId?: string;
  timestamp: string;
  duration?: number;
  metadata?: Record<string, any>;
}

export interface PerformanceThreshold {
  componentRenderTime: number; // ms
  apiResponseTime: number; // ms
  userInteractionTime: number; // ms
  memoryUsage: number; // MB
}

export interface UXOptimizationConfig {
  enablePerformanceMonitoring: boolean;
  enableUserBehaviorTracking: boolean;
  performanceThresholds: PerformanceThreshold;
  reportToService: boolean;
  debounceDelay: number;
  throttleDelay: number;
}

// 默认配置
const DEFAULT_CONFIG: UXOptimizationConfig = {
  enablePerformanceMonitoring: process.env.NODE_ENV === 'development',
  enableUserBehaviorTracking: false,
  performanceThresholds: {
    componentRenderTime: 100, // 100ms
    apiResponseTime: 500, // 500ms
    userInteractionTime: 1000, // 1s
    memoryUsage: 50, // 50MB
  },
  reportToService: false,
  debounceDelay: 300,
  throttleDelay: 200,
};

// 查询键常量
export const UX_QUERY_KEYS = {
  performanceMetrics: (componentName?: string) => ['uxPerformanceMetrics', componentName] as const,
  userBehavior: (sessionId: string) => ['uxUserBehavior', sessionId] as const,
  optimizationConfig: () => ['uxOptimizationConfig'] as const,
} as const;

/**
 * UX性能监控服务
 */
export class UXPerformanceMonitor {
  private config: UXOptimizationConfig;
  private metrics: UXMetrics[] = [];
  private startTime: number = Date.now();
  private sessionId: string;
  private observers: PerformanceObserver[] = [];

  constructor(config: Partial<UXOptimizationConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.sessionId = this.generateSessionId();

    if (this.config.enablePerformanceMonitoring) {
      this.initializePerformanceObservers();
    }
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 初始化性能观察器
   */
  private initializePerformanceObservers(): void {
    try {
      // 监控导航性能
      if ('PerformanceObserver' in window) {
        const navigationObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry) => {
            if (entry.entryType === 'navigation') {
              this.recordMetric({
                componentName: 'PageNavigation',
                actionType: 'navigation',
                componentRenderTime: entry.duration,
                apiResponseTime: 0,
                userInteractionTime: 0,
                timestamp: new Date().toISOString(),
              });
            }
          });
        });
        navigationObserver.observe({ entryTypes: ['navigation'] });
        this.observers.push(navigationObserver);
      }

      // 监控资源加载性能
      const resourceObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry) => {
          if (entry.entryType === 'resource') {
            this.recordMetric({
              componentName: `ResourceLoad_${entry.name}`,
              actionType: 'api_call',
              componentRenderTime: 0,
              apiResponseTime: entry.duration,
              userInteractionTime: 0,
              timestamp: new Date().toISOString(),
            });
          }
        });
      });
      resourceObserver.observe({ entryTypes: ['resource'] });
      this.observers.push(resourceObserver);

    } catch (error) {
      console.warn('Performance observers not supported:', error);
    }
  }

  /**
   * 记录性能指标
   */
  recordMetric(metric: Omit<UXMetrics, 'timestamp'>): void {
    const fullMetric: UXMetrics = {
      ...metric,
      timestamp: new Date().toISOString(),
    };

    this.metrics.push(fullMetric);

    // 检查性能阈值
    this.checkPerformanceThresholds(fullMetric);

    // 发送到监控服务
    if (this.config.reportToService) {
      this.reportToService(fullMetric);
    }
  }

  /**
   * 检查性能阈值
   */
  private checkPerformanceThresholds(metric: UXMetrics): void {
    const { performanceThresholds } = this.config;
    const warnings: string[] = [];

    if (metric.actionType === 'render' && metric.componentRenderTime > performanceThresholds.componentRenderTime) {
      warnings.push(`Component render time (${metric.componentRenderTime}ms) exceeds threshold (${performanceThresholds.componentRenderTime}ms)`);
    }

    if (metric.actionType === 'api_call' && metric.apiResponseTime > performanceThresholds.apiResponseTime) {
      warnings.push(`API response time (${metric.apiResponseTime}ms) exceeds threshold (${performanceThresholds.apiResponseTime}ms)`);
    }

    if (metric.actionType === 'user_interaction' && metric.userInteractionTime > performanceThresholds.userInteractionTime) {
      warnings.push(`User interaction time (${metric.userInteractionTime}ms) exceeds threshold (${performanceThresholds.userInteractionTime}ms)`);
    }

    if (warnings.length > 0) {
      console.warn(`[UX Performance Warning] ${metric.componentName}:`, warnings.join(', '));
    }
  }

  /**
   * 发送数据到监控服务
   */
  private reportToService(metric: UXMetrics): void {
    // 这里可以集成到监控服务如Sentry、DataDog等
    if (process.env.NODE_ENV === 'development') {
      console.log('[UX Metric]', metric);
    }
  }

  /**
   * 获取性能统计
   */
  getPerformanceStats(): {
    totalMetrics: number;
    averageRenderTime: number;
    averageApiResponseTime: number;
    averageUserInteractionTime: number;
    slowestComponents: Array<{ componentName: string; time: number; actionType: string }>;
  } {
    const renderMetrics = this.metrics.filter(m => m.actionType === 'render');
    const apiMetrics = this.metrics.filter(m => m.actionType === 'api_call');
    const interactionMetrics = this.metrics.filter(m => m.actionType === 'user_interaction');

    const averageRenderTime = renderMetrics.length > 0
      ? renderMetrics.reduce((sum, m) => sum + m.componentRenderTime, 0) / renderMetrics.length
      : 0;

    const averageApiResponseTime = apiMetrics.length > 0
      ? apiMetrics.reduce((sum, m) => sum + m.apiResponseTime, 0) / apiMetrics.length
      : 0;

    const averageUserInteractionTime = interactionMetrics.length > 0
      ? interactionMetrics.reduce((sum, m) => sum + m.userInteractionTime, 0) / interactionMetrics.length
      : 0;

    const slowestComponents = this.metrics
      .map(m => ({
        componentName: m.componentName,
        time: m.actionType === 'render' ? m.componentRenderTime :
              m.actionType === 'api_call' ? m.apiResponseTime :
              m.userInteractionTime,
        actionType: m.actionType,
      }))
      .sort((a, b) => b.time - a.time)
      .slice(0, 10);

    return {
      totalMetrics: this.metrics.length,
      averageRenderTime,
      averageApiResponseTime,
      averageUserInteractionTime,
      slowestComponents,
    };
  }

  /**
   * 清理资源
   */
  destroy(): void {
    this.observers.forEach(observer => observer.disconnect());
    this.observers = [];
    this.metrics = [];
  }
}

/**
 * 用户行为追踪服务
 */
export class UserBehaviorTracker {
  private sessionId: string;
  private behaviors: UserBehaviorData[] = [];
  private isTracking: boolean = false;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }

  /**
   * 开始追踪
   */
  startTracking(): void {
    if (this.isTracking) return;

    this.isTracking = true;
    this.setupEventListeners();
  }

  /**
   * 停止追踪
   */
  stopTracking(): void {
    this.isTracking = false;
    this.removeEventListeners();
  }

  /**
   * 设置事件监听器
   */
  private setupEventListeners(): void {
    // 点击事件
    document.addEventListener('click', this.handleClick, true);

    // 滚动事件（节流）
    let scrollTimer: NodeJS.Timeout;
    document.addEventListener('scroll', () => {
      clearTimeout(scrollTimer);
      scrollTimer = setTimeout(this.handleScroll, 100);
    }, true);

    // 表单提交事件
    document.addEventListener('submit', this.handleSubmit, true);
  }

  /**
   * 移除事件监听器
   */
  private removeEventListeners(): void {
    document.removeEventListener('click', this.handleClick, true);
    document.removeEventListener('scroll', this.handleScroll, true);
    document.removeEventListener('submit', this.handleSubmit, true);
  }

  /**
   * 处理点击事件
   */
  private handleClick = (event: MouseEvent): void => {
    const target = event.target as HTMLElement;
    this.recordBehavior({
      actionType: 'click',
      elementId: target.id || target.className || undefined,
      pagePath: window.location.pathname,
      metadata: {
        tagName: target.tagName,
        text: target.textContent?.slice(0, 50),
      },
    });
  };

  /**
   * 处理滚动事件
   */
  private handleScroll = (): void => {
    this.recordBehavior({
      actionType: 'scroll',
      pagePath: window.location.pathname,
      metadata: {
        scrollY: window.scrollY,
        scrollX: window.scrollX,
      },
    });
  };

  /**
   * 处理表单提交事件
   */
  private handleSubmit = (event: Event): void => {
    const target = event.target as HTMLFormElement;
    this.recordBehavior({
      actionType: 'form_submit',
      elementId: target.id || target.className || undefined,
      pagePath: window.location.pathname,
      metadata: {
        formAction: target.action,
        formMethod: target.method,
      },
    });
  };

  /**
   * 记录用户行为
   */
  private recordBehavior(behavior: Omit<UserBehaviorData, 'sessionId' | 'timestamp'>): void {
    if (!this.isTracking) return;

    const fullBehavior: UserBehaviorData = {
      ...behavior,
      sessionId: this.sessionId,
      timestamp: new Date().toISOString(),
    };

    this.behaviors.push(fullBehavior);
  }

  /**
   * 获取行为数据
   */
  getBehaviorData(): UserBehaviorData[] {
    return [...this.behaviors];
  }

  /**
   * 清理数据
   */
  clearData(): void {
    this.behaviors = [];
  }
}

/**
 * UX性能监控Hook
 */
export function useUXPerformanceMonitor(componentName: string) {
  const monitorRef = useRef<UXPerformanceMonitor>();

  useEffect(() => {
    if (!monitorRef.current) {
      monitorRef.current = new UXPerformanceMonitor({
        enablePerformanceMonitoring: true,
        enableUserBehaviorTracking: false,
      });
    }

    return () => {
      monitorRef.current?.destroy();
    };
  }, []);

  const recordRenderTime = useCallback((renderTime: number) => {
    monitorRef.current?.recordMetric({
      componentName,
      actionType: 'render',
      componentRenderTime: renderTime,
      apiResponseTime: 0,
      userInteractionTime: 0,
    });
  }, [componentName]);

  const recordApiResponseTime = useCallback((responseTime: number, apiName?: string) => {
    monitorRef.current?.recordMetric({
      componentName: apiName || componentName,
      actionType: 'api_call',
      componentRenderTime: 0,
      apiResponseTime: responseTime,
      userInteractionTime: 0,
    });
  }, [componentName]);

  const recordUserInteractionTime = useCallback((interactionTime: number, action?: string) => {
    monitorRef.current?.recordMetric({
      componentName: action || componentName,
      actionType: 'user_interaction',
      componentRenderTime: 0,
      apiResponseTime: 0,
      userInteractionTime: interactionTime,
    });
  }, [componentName]);

  return {
    recordRenderTime,
    recordApiResponseTime,
    recordUserInteractionTime,
    getStats: () => monitorRef.current?.getPerformanceStats(),
  };
}

/**
 * 用户行为追踪Hook
 */
export function useUserBehaviorTracker() {
  const trackerRef = useRef<UserBehaviorTracker>();
  const [isTracking, setIsTracking] = React.useState(false);

  useEffect(() => {
    if (!trackerRef.current) {
      const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      trackerRef.current = new UserBehaviorTracker(sessionId);
    }

    return () => {
      trackerRef.current?.stopTracking();
    };
  }, []);

  const startTracking = useCallback(() => {
    trackerRef.current?.startTracking();
    setIsTracking(true);
  }, []);

  const stopTracking = useCallback(() => {
    trackerRef.current?.stopTracking();
    setIsTracking(false);
  }, []);

  const getBehaviorData = useCallback(() => {
    return trackerRef.current?.getBehaviorData() || [];
  }, []);

  const clearBehaviorData = useCallback(() => {
    trackerRef.current?.clearData();
  }, []);

  return {
    isTracking,
    startTracking,
    stopTracking,
    getBehaviorData,
    clearBehaviorData,
  };
}

/**
 * 防抖Hook
 */
export function useUXDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = React.useState<T>(value);

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

/**
 * 节流Hook
 */
export function useUXThrottle<T>(value: T, limit: number): T {
  const [throttledValue, setThrottledValue] = React.useState<T>(value);
  const lastRan = useRef(Date.now());

  useEffect(() => {
    const handler = setTimeout(() => {
      if (Date.now() - lastRan.current >= limit) {
        setThrottledValue(value);
        lastRan.current = Date.now();
      }
    }, limit - (Date.now() - lastRan.current));

    return () => {
      clearTimeout(handler);
    };
  }, [value, limit]);

  return throttledValue;
}

// 导出服务对象
export const uxService = {
  UXPerformanceMonitor,
  UserBehaviorTracker,
  useUXPerformanceMonitor,
  useUserBehaviorTracker,
  useUXDebounce,
  useUXThrottle,
  QUERY_KEYS: UX_QUERY_KEYS,
  DEFAULT_CONFIG,
};