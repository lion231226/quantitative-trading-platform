/**
 * Web Vitals Performance Monitoring Service
 *
 * Provides comprehensive Core Web Vitals monitoring and performance optimization capabilities:
 * - Core Web Vitals tracking (LCP, FID, CLS, FCP, TTFB)
 * - Custom performance metrics
 * - Performance trend analysis
 * - Performance alerts and thresholds
 * - Integration with Sentry and other monitoring services
 */

import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';
import * as Sentry from '@sentry/react';

// Performance metric types
export interface WebVitalsMetrics {
  lcp: number; // Largest Contentful Paint (ms)
  fid: number; // First Input Delay (ms)
  cls: number; // Cumulative Layout Shift
  fcp: number; // First Contentful Paint (ms)
  ttfb: number; // Time to First Byte (ms)
}

export interface CustomMetric {
  name: string;
  value: number;
  tags?: Record<string, string>;
  timestamp: number;
}

export interface PerformanceThresholds {
  lcp: number; // Target: < 2500ms (Good), < 4000ms (Needs Improvement)
  fid: number; // Target: < 100ms (Good), < 300ms (Needs Improvement)
  cls: number; // Target: < 0.1 (Good), < 0.25 (Needs Improvement)
  fcp: number; // Target: < 1800ms (Good), < 3000ms (Needs Improvement)
  ttfb: number; // Target: < 800ms (Good), < 1800ms (Needs Improvement)
  renderTime: number; // Target: < 16ms (60fps)
  memoryUsage: number; // Target: < 100MB
}

export interface PerformanceTrend {
  metric: string;
  current: number;
  previous: number;
  change: number;
  changePercentage: number;
  trend: 'improving' | 'degrading' | 'stable';
  timeframe: string;
}

export interface TimeRange {
  start: Date;
  end: Date;
}

export interface PerformanceScore {
  lcp: 'good' | 'needs-improvement' | 'poor';
  fid: 'good' | 'needs-improvement' | 'poor';
  cls: 'good' | 'needs-improvement' | 'poor';
  fcp: 'good' | 'needs-improvement' | 'poor';
  ttfb: 'good' | 'needs-improvement' | 'poor';
  overall: 'good' | 'needs-improvement' | 'poor';
}

class WebVitalsMonitoringService {
  private thresholds: PerformanceThresholds;
  private metricsBuffer: Map<string, number[]> = new Map();
  private observers: PerformanceObserver[] = [];
  private isInitialized = false;
  private onMetricsUpdate?: (metrics: WebVitalsMetrics) => void;

  constructor() {
    // Set performance thresholds based on Google Web Vitals recommendations
    this.thresholds = {
      lcp: 2500,    // 2.5 seconds
      fid: 100,     // 100 milliseconds
      cls: 0.1,     // Cumulative Layout Shift
      fcp: 1800,    // 1.8 seconds
      ttfb: 800,    // 800 milliseconds
      renderTime: 16, // 16ms for 60fps
      memoryUsage: 100 * 1024 * 1024, // 100MB
    };
  }

  /**
   * Initialize Web Vitals monitoring
   */
  public initialize(options?: {
    onMetricsUpdate?: (metrics: WebVitalsMetrics) => void;
    thresholds?: Partial<PerformanceThresholds>;
  }): void {
    if (this.isInitialized || typeof window === 'undefined') {
      return;
    }

    this.onMetricsUpdate = options?.onMetricsUpdate;

    if (options?.thresholds) {
      this.thresholds = { ...this.thresholds, ...options.thresholds };
    }

    this.initializeWebVitals();
    this.initializeCustomMetrics();
    this.initializeMemoryMonitoring();
    this.initializeRenderPerformanceMonitoring();

    this.isInitialized = true;
    console.log('🚀 Web Vitals monitoring initialized');
  }

  /**
   * Track Core Web Vitals
   */
  public async trackWebVitals(): Promise<WebVitalsMetrics> {
    return new Promise((resolve) => {
      const metrics: Partial<WebVitalsMetrics> = {};

      const checkComplete = () => {
        if (metrics.lcp !== undefined &&
            metrics.fid !== undefined &&
            metrics.cls !== undefined &&
            metrics.fcp !== undefined &&
            metrics.ttfb !== undefined) {

          const completeMetrics = metrics as WebVitalsMetrics;

          // Call update callback if provided
          this.onMetricsUpdate?.(completeMetrics);

          resolve(completeMetrics);
        }
      };

      // Track each metric with appropriate handlers
      getCLS((metric) => {
        metrics.cls = metric.value;
        this.sendMetric('CLS', metric.value);
        this.checkThresholds('CLS', metric.value);
        checkComplete();
      });

      getFID((metric) => {
        metrics.fid = metric.value;
        this.sendMetric('FID', metric.value);
        this.checkThresholds('FID', metric.value);
        checkComplete();
      });

      getFCP((metric) => {
        metrics.fcp = metric.value;
        this.sendMetric('FCP', metric.value);
        this.checkThresholds('FCP', metric.value);
        checkComplete();
      });

      getLCP((metric) => {
        metrics.lcp = metric.value;
        this.sendMetric('LCP', metric.value);
        this.checkThresholds('LCP', metric.value);
        checkComplete();
      });

      getTTFB((metric) => {
        metrics.ttfb = metric.value;
        this.sendMetric('TTFB', metric.value);
        this.checkThresholds('TTFB', metric.value);
        checkComplete();
      });
    });
  }

  /**
   * Track custom performance metric
   */
  public trackCustomMetric(name: string, value: number, tags?: Record<string, string>): void {
    const metric: CustomMetric = {
      name,
      value,
      tags,
      timestamp: Date.now(),
    };

    // Store in buffer for trend analysis
    if (!this.metricsBuffer.has(name)) {
      this.metricsBuffer.set(name, []);
    }
    this.metricsBuffer.get(name)!.push(value);

    // Keep only last 100 values per metric
    const buffer = this.metricsBuffer.get(name)!;
    if (buffer.length > 100) {
      buffer.shift();
    }

    // Send to monitoring service
    this.sendMetric(name, value, tags);

    // Check against thresholds
    this.checkThresholds(name, value);
  }

  /**
   * Analyze performance trends over time range
   */
  public async analyzePerformanceTrends(timeRange: TimeRange): Promise<PerformanceTrend[]> {
    const trends: PerformanceTrend[] = [];

    for (const [metricName, values] of this.metricsBuffer.entries()) {
      if (values.length < 2) continue;

      const current = values[values.length - 1];
      const previous = values[values.length - 2];
      const change = current - previous;
      const changePercentage = previous !== 0 ? (change / previous) * 100 : 0;

      let trend: 'improving' | 'degrading' | 'stable';
      const threshold = 5; // 5% change threshold

      if (Math.abs(changePercentage) < threshold) {
        trend = 'stable';
      } else if ((this.isLowerBetter(metricName) && change < 0) ||
                 (!this.isLowerBetter(metricName) && change > 0)) {
        trend = 'improving';
      } else {
        trend = 'degrading';
      }

      trends.push({
        metric: metricName,
        current,
        previous,
        change,
        changePercentage,
        trend,
        timeframe: `${timeRange.start.toISOString()} - ${timeRange.end.toISOString()}`,
      });
    }

    return trends;
  }

  /**
   * Setup performance alerts and notifications
   */
  public setupPerformanceAlerts(thresholds: Partial<PerformanceThresholds>): void {
    // Merge with default thresholds
    this.thresholds = { ...this.thresholds, ...thresholds };

    console.log('🔔 Performance alerts configured with thresholds:', this.thresholds);
  }

  /**
   * Get current performance thresholds
   */
  public getThresholds(): PerformanceThresholds {
    return { ...this.thresholds };
  }

  /**
   * Get performance score based on Web Vitals
   */
  public getPerformanceScore(metrics: WebVitalsMetrics): PerformanceScore {
    const lcpScore = this.getMetricScore(metrics.lcp, this.thresholds.lcp, 4000);
    const fidScore = this.getMetricScore(metrics.fid, this.thresholds.fid, 300);
    const clsScore = this.getMetricScore(metrics.cls, this.thresholds.cls, 0.25);
    const fcpScore = this.getMetricScore(metrics.fcp, this.thresholds.fcp, 3000);
    const ttfbScore = this.getMetricScore(metrics.ttfb, this.thresholds.ttfb, 1800);

    // Calculate overall score (weighted average)
    const scores = [lcpScore, fidScore, clsScore, fcpScore, ttfbScore];
    const goodCount = scores.filter(s => s === 'good').length;
    const poorCount = scores.filter(s => s === 'poor').length;

    let overall: 'good' | 'needs-improvement' | 'poor';
    if (goodCount >= 4) {
      overall = 'good';
    } else if (poorCount >= 2) {
      overall = 'poor';
    } else {
      overall = 'needs-improvement';
    }

    return {
      lcp: lcpScore,
      fid: fidScore,
      cls: clsScore,
      fcp: fcpScore,
      ttfb: ttfbScore,
      overall,
    };
  }

  /**
   * Measure render performance for a specific component
   */
  public measureRenderPerformance(componentName: string, renderFn: () => void): number {
    const startTime = performance.now();

    // Use requestAnimationFrame to measure actual render time
    requestAnimationFrame(() => {
      const renderTime = performance.now() - startTime;
      this.trackCustomMetric(`render_${componentName}`, renderTime, {
        component: componentName,
        type: 'render'
      });
    });

    renderFn();
    return performance.now() - startTime;
  }

  /**
   * Measure API response time
   */
  public async measureApiCall<T>(
    apiName: string,
    apiCall: () => Promise<T>
  ): Promise<T> {
    const startTime = performance.now();

    try {
      const result = await apiCall();
      const responseTime = performance.now() - startTime;

      this.trackCustomMetric(`api_${apiName}`, responseTime, {
        api: apiName,
        type: 'api',
        status: 'success'
      });

      return result;
    } catch (error) {
      const responseTime = performance.now() - startTime;

      this.trackCustomMetric(`api_${apiName}`, responseTime, {
        api: apiName,
        type: 'api',
        status: 'error'
      });

      throw error;
    }
  }

  /**
   * Get buffered metrics for analysis
   */
  public getMetricsBuffer(): Map<string, number[]> {
    return new Map(this.metricsBuffer);
  }

  /**
   * Clear metrics buffer
   */
  public clearMetricsBuffer(): void {
    this.metricsBuffer.clear();
    console.log('🧹 Web Vitals metrics buffer cleared');
  }

  /**
   * Initialize Core Web Vitals tracking
   */
  private initializeWebVitals(): void {
    // Initialize Sentry performance monitoring if available
    if (typeof Sentry !== 'undefined') {
      Sentry.addBreadcrumb({
        category: 'performance',
        message: 'Web Vitals monitoring initialized',
        level: 'info',
      });
    }
  }

  /**
   * Initialize custom performance observers
   */
  private initializeCustomMetrics(): void {
    if (typeof PerformanceObserver === 'undefined') {
      return;
    }

    // Observer for navigation timing
    const navigationObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.entryType === 'navigation') {
          const navEntry = entry as PerformanceNavigationTiming;
          this.trackCustomMetric('dom_load_time', navEntry.loadEventEnd - navEntry.loadEventStart);
          this.trackCustomMetric('page_load_time', navEntry.loadEventEnd - navEntry.fetchStart);
        }
      }
    });

    // Observer for resource timing
    const resourceObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.entryType === 'resource') {
          const resourceEntry = entry as PerformanceResourceTiming;
          this.trackCustomMetric('resource_load_time', resourceEntry.duration, {
            resource_type: this.getResourceType(resourceEntry.name),
            resource_name: resourceEntry.name.split('/').pop() || 'unknown'
          });
        }
      }
    });

    navigationObserver.observe({ entryTypes: ['navigation'] });
    resourceObserver.observe({ entryTypes: ['resource'] });

    this.observers.push(navigationObserver, resourceObserver);
  }

  /**
   * Initialize memory monitoring
   */
  private initializeMemoryMonitoring(): void {
    if ('memory' in performance) {
      setInterval(() => {
        const memory = (performance as any).memory;
        this.trackCustomMetric('memory_usage', memory.usedJSHeapSize);
        this.trackCustomMetric('memory_limit', memory.totalJSHeapSize);
        this.trackCustomMetric('memory_utilization',
          (memory.usedJSHeapSize / memory.totalJSHeapSize) * 100
        );
      }, 30000); // Every 30 seconds
    }
  }

  /**
   * Initialize render performance monitoring
   */
  private initializeRenderPerformanceMonitoring(): void {
    // Monitor long tasks that could block the main thread
    if ('PerformanceObserver' in window) {
      const longTaskObserver = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.entryType === 'longtask') {
            this.trackCustomMetric('long_task_duration', entry.duration, {
              type: 'long_task',
              start_time: entry.startTime.toString()
            });
          }
        }
      });

      try {
        longTaskObserver.observe({ entryTypes: ['longtask'] });
        this.observers.push(longTaskObserver);
      } catch (e) {
        // Long task observer might not be supported in all browsers
        console.warn('Long task observer not supported:', e);
      }
    }
  }

  /**
   * Send metric to monitoring service
   */
  private sendMetric(name: string, value: number, tags?: Record<string, string>): void {
    // Send to Sentry if available
    if (typeof Sentry !== 'undefined') {
      Sentry.addBreadcrumb({
        category: 'performance',
        message: `${name}: ${value}`,
        level: 'info',
        data: { value, tags }
      });

      Sentry.setMeasurement(name, value, 'millisecond');
    }

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`📊 ${name}: ${value}${tags ? ` (${JSON.stringify(tags)})` : ''}`);
    }
  }

  /**
   * Check if metric exceeds thresholds
   */
  private checkThresholds(metricName: string, value: number): void {
    const threshold = this.thresholds[metricName.toLowerCase() as keyof PerformanceThresholds];

    if (threshold !== undefined && value > threshold) {
      console.warn(`⚠️ Performance threshold exceeded: ${metricName} = ${value} (threshold: ${threshold})`);

      // Send alert to monitoring service
      if (typeof Sentry !== 'undefined') {
        Sentry.captureMessage(`Performance threshold exceeded: ${metricName}`, {
          level: 'warning',
          extra: { value, threshold, metricName }
        });
      }
    }
  }

  /**
   * Get metric score based on thresholds
   */
  private getMetricScore(
    value: number,
    goodThreshold: number,
    poorThreshold: number
  ): 'good' | 'needs-improvement' | 'poor' {
    if (value <= goodThreshold) {
      return 'good';
    } else if (value <= poorThreshold) {
      return 'needs-improvement';
    } else {
      return 'poor';
    }
  }

  /**
   * Determine if lower values are better for a metric
   */
  private isLowerBetter(metricName: string): boolean {
    const lowerBetterMetrics = [
      'lcp', 'fid', 'cls', 'fcp', 'ttfb', 'render_time',
      'memory_usage', 'dom_load_time', 'page_load_time',
      'resource_load_time', 'long_task_duration', 'api'
    ];

    return lowerBetterMetrics.some(metric =>
      metricName.toLowerCase().includes(metric.toLowerCase())
    );
  }

  /**
   * Get resource type from URL
   */
  private getResourceType(url: string): string {
    const extension = url.split('.').pop()?.toLowerCase();

    if (['js', 'jsx', 'ts', 'tsx'].includes(extension || '')) {
      return 'script';
    } else if (['css'].includes(extension || '')) {
      return 'stylesheet';
    } else if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(extension || '')) {
      return 'image';
    } else if (['woff', 'woff2', 'ttf', 'otf'].includes(extension || '')) {
      return 'font';
    } else {
      return 'other';
    }
  }

  /**
   * Cleanup observers
   */
  public dispose(): void {
    this.observers.forEach(observer => observer.disconnect());
    this.observers = [];
    this.metricsBuffer.clear();
    this.isInitialized = false;
    console.log('🗑️ Web Vitals monitoring disposed');
  }
}

// Singleton instance
export const webVitalsService = new WebVitalsMonitoringService();

// Export types for external use
export type {
  WebVitalsMonitoringService,
  WebVitalsMetrics,
  CustomMetric,
  PerformanceThresholds,
  PerformanceTrend,
  TimeRange,
  PerformanceScore
};

// Initialize automatically in browser environment
if (typeof window !== 'undefined') {
  // Initialize after a short delay to ensure page load is complete
  setTimeout(() => {
    webVitalsService.initialize();
  }, 1000);
}