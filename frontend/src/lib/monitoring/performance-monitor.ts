/**
 * Performance Monitoring Tools
 * Enhanced performance tracking for trading platform operations
 */

import { monitoringService } from '@/services/monitoringService';
import { sentryClient } from './sentry-client';

export interface PerformanceMetrics {
  // Core Web Vitals
  lcp?: number; // Largest Contentful Paint
  fid?: number; // First Input Delay
  cls?: number; // Cumulative Layout Shift
  fcp?: number; // First Contentful Paint
  ttfb?: number; // Time to First Byte

  // Custom metrics
  apiResponseTime?: number;
  strategyCalculationTime?: number;
  chartRenderTime?: number;
  dataProcessingTime?: number;
}

export interface PerformanceTransaction {
  name: string;
  operation: string;
  startTime: number;
  endTime?: number;
  duration?: number;
  tags?: Record<string, string>;
  data?: Record<string, number>;
}

/**
 * Performance monitoring service for trading operations
 */
export class PerformanceMonitor {
  private static instance: PerformanceMonitor;
  private transactions: Map<string, PerformanceTransaction> = new Map();
  private metrics: PerformanceMetrics = {};
  private observers: PerformanceObserver[] = [];

  private constructor() {
    this.initializeObservers();
  }

  public static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor();
    }
    return PerformanceMonitor.instance;
  }

  /**
   * Initialize performance observers
   */
  private initializeObservers(): void {
    if (typeof window === 'undefined' || !('PerformanceObserver' in window)) {
      return;
    }

    // Core Web Vitals observer
    try {
      const vitalsObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach(entry => {
          this.processWebVitalEntry(entry);
        });
      });

      vitalsObserver.observe({ entryTypes: ['largest-contentful-paint', 'first-input', 'layout-shift', 'paint'] });
      this.observers.push(vitalsObserver);
    } catch (error) {
      console.warn('Failed to initialize Web Vitals observer:', error);
    }

    // Navigation timing observer
    try {
      const navigationObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach(entry => {
          this.processNavigationEntry(entry);
        });
      });

      navigationObserver.observe({ entryTypes: ['navigation'] });
      this.observers.push(navigationObserver);
    } catch (error) {
      console.warn('Failed to initialize Navigation observer:', error);
    }

    // Resource timing observer
    try {
      const resourceObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach(entry => {
          this.processResourceEntry(entry);
        });
      });

      resourceObserver.observe({ entryTypes: ['resource'] });
      this.observers.push(resourceObserver);
    } catch (error) {
      console.warn('Failed to initialize Resource observer:', error);
    }
  }

  /**
   * Start a performance transaction
   */
  public startTransaction(
    name: string,
    operation: string,
    tags?: Record<string, string>
  ): string {
    const transactionId = `${name}-${Date.now()}`;
    const transaction: PerformanceTransaction = {
      name,
      operation,
      startTime: performance.now(),
      tags,
    };

    this.transactions.set(transactionId, transaction);

    // Track with monitoring service
    monitoringService.startTransaction({
      name,
      op: operation,
      tags,
    });

    return transactionId;
  }

  /**
   * End a performance transaction
   */
  public endTransaction(
    transactionId: string,
    data?: Record<string, number>
  ): number | null {
    const transaction = this.transactions.get(transactionId);
    if (!transaction) {
      return null;
    }

    const endTime = performance.now();
    const duration = endTime - transaction.startTime;

    transaction.endTime = endTime;
    transaction.duration = duration;
    if (data) {
      transaction.data = { ...transaction.data, ...data };
    }

    // Send to monitoring services
    this.reportTransactionMetrics(transaction);

    // Clean up
    this.transactions.delete(transactionId);

    return duration;
  }

  /**
   * Measure trading operation performance
   */
  public measureTradingOperation<T>(
    operation: string,
    fn: () => T | Promise<T>,
    tags?: Record<string, string>
  ): Promise<{ result: T; duration: number }> {
    return new Promise(async (resolve, reject) => {
      const transactionId = this.startTransaction(`trading-${operation}`, 'trading', tags);

      try {
        const startTime = performance.now();
        const result = await fn();
        const endTime = performance.now();
        const duration = endTime - startTime;

        this.endTransaction(transactionId, {
          operation,
          success: 1,
          resultCount: Array.isArray(result) ? result.length : 1,
        });

        resolve({ result, duration });
      } catch (error) {
        this.endTransaction(transactionId, {
          operation,
          success: 0,
          error: 1,
        });

        reject(error);
      }
    });
  }

  /**
   * Measure API call performance
   */
  public measureApiCall<T>(
    url: string,
    method: string,
    fn: () => T | Promise<T>
  ): Promise<{ result: T; duration: number }> {
    return this.measureTradingOperation(
      `api-${method.toLowerCase()}`,
      fn,
      { url, method, type: 'api' }
    );
  }

  /**
   * Measure strategy calculation performance
   */
  public measureStrategyCalculation<T>(
    strategyName: string,
    dataPoints: number,
    fn: () => T | Promise<T>
  ): Promise<{ result: T; duration: number }> {
    return this.measureTradingOperation(
      `strategy-${strategyName}`,
      fn,
      {
        strategy: strategyName,
        dataPoints: dataPoints.toString(),
        type: 'strategy'
      }
    );
  }

  /**
   * Measure chart rendering performance
   */
  public measureChartRender<T>(
    chartType: string,
    dataPoints: number,
    fn: () => T | Promise<T>
  ): Promise<{ result: T; duration: number }> {
    return this.measureTradingOperation(
      `chart-${chartType}`,
      fn,
      {
        chart: chartType,
        dataPoints: dataPoints.toString(),
        type: 'render'
      }
    );
  }

  /**
   * Get current performance metrics
   */
  public getMetrics(): PerformanceMetrics {
    return { ...this.metrics };
  }

  /**
   * Get transaction statistics
   */
  public getTransactionStats(): {
    total: number;
    completed: number;
    averageDuration: number;
    slowOperations: PerformanceTransaction[];
  } {
    const allTransactions = Array.from(this.transactions.values());
    const completedTransactions = allTransactions.filter(t => t.duration !== undefined);

    const averageDuration = completedTransactions.length > 0
      ? completedTransactions.reduce((sum, t) => sum + (t.duration || 0), 0) / completedTransactions.length
      : 0;

    const slowOperations = completedTransactions
      .filter(t => (t.duration || 0) > 1000) // Operations over 1 second
      .sort((a, b) => (b.duration || 0) - (a.duration || 0))
      .slice(0, 10); // Top 10 slowest

    return {
      total: allTransactions.length,
      completed: completedTransactions.length,
      averageDuration,
      slowOperations,
    };
  }

  /**
   * Process Web Vitals entry
   */
  private processWebVitalEntry(entry: PerformanceEntry): void {
    switch (entry.entryType) {
      case 'largest-contentful-paint':
        this.metrics.lcp = entry.startTime;
        this.sendMetricToSentry('lcp', entry.startTime, 'millisecond');
        break;

      case 'first-input':
        this.metrics.fid = (entry as any).processingStart - entry.startTime;
        this.sendMetricToSentry('fid', this.metrics.fid, 'millisecond');
        break;

      case 'layout-shift':
        if (!(entry as any).hadRecentInput) {
          this.metrics.cls = (this.metrics.cls || 0) + (entry as any).value;
          this.sendMetricToSentry('cls', this.metrics.cls, '');
        }
        break;

      case 'paint':
        if (entry.name === 'first-contentful-paint') {
          this.metrics.fcp = entry.startTime;
          this.sendMetricToSentry('fcp', entry.startTime, 'millisecond');
        }
        break;
    }
  }

  /**
   * Process navigation entry
   */
  private processNavigationEntry(entry: PerformanceNavigationTiming): void {
    this.metrics.ttfb = entry.responseStart - entry.requestStart;
    this.sendMetricToSentry('ttfb', this.metrics.ttfb, 'millisecond');

    // Additional navigation metrics
    this.sendMetricToSentry('dom_load_time', entry.loadEventEnd - entry.loadEventStart, 'millisecond');
    this.sendMetricToSentry('page_load_time', entry.loadEventEnd - entry.fetchStart, 'millisecond');
  }

  /**
   * Process resource entry
   */
  private processResourceEntry(entry: PerformanceResourceTiming): void {
    if (entry.duration > 1000) { // Only track slow resources
      this.sendMetricToSentry('slow_resource', entry.duration, 'millisecond', {
        name: entry.name,
        type: entry.initiatorType,
      });
    }
  }

  /**
   * Send metric to Sentry
   */
  private sendMetricToSentry(
    name: string,
    value: number,
    unit: string,
    tags?: Record<string, string>
  ): void {
    try {
      monitoringService.setExtra(`performance.${name}`, value);

      if (tags) {
        Object.entries(tags).forEach(([key, tagValue]) => {
          monitoringService.setTags({ [key]: tagValue });
        });
      }

      // Add breadcrumb for performance monitoring
      monitoringService.addBreadcrumb({
        category: 'performance',
        message: `Performance metric: ${name}`,
        level: 'info',
        data: { name, value, unit, ...tags },
      });
    } catch (error) {
      console.warn('Failed to send metric to Sentry:', error);
    }
  }

  /**
   * Report transaction metrics
   */
  private reportTransactionMetrics(transaction: PerformanceTransaction): void {
    if (!transaction.duration) return;

    this.sendMetricToSentry(
      `transaction_duration_${transaction.operation}`,
      transaction.duration,
      'millisecond',
      transaction.tags
    );

    // Add breadcrumb
    monitoringService.addBreadcrumb({
      category: 'performance',
      message: `Transaction completed: ${transaction.name}`,
      level: 'info',
      data: {
        name: transaction.name,
        operation: transaction.operation,
        duration: transaction.duration,
        ...transaction.data,
        ...transaction.tags,
      },
    });

    // Alert on slow operations
    if (transaction.duration > 5000) { // 5 seconds
      monitoringService.captureMessage(
        `Slow operation detected: ${transaction.name} took ${transaction.duration.toFixed(2)}ms`,
        'warning',
        {
          tags: transaction.tags,
          extra: {
            transaction: transaction.name,
            duration: transaction.duration,
            data: transaction.data,
          },
        }
      );
    }
  }

  /**
   * Cleanup performance observers
   */
  public dispose(): void {
    this.observers.forEach(observer => {
      observer.disconnect();
    });
    this.observers = [];
    this.transactions.clear();
  }
}

// Export singleton instance
export const performanceMonitor = PerformanceMonitor.getInstance();

// Export convenience functions
export const startTransaction = (name: string, operation: string, tags?: Record<string, string>) =>
  performanceMonitor.startTransaction(name, operation, tags);

export const endTransaction = (transactionId: string, data?: Record<string, number>) =>
  performanceMonitor.endTransaction(transactionId, data);

export const measureTradingOperation = <T>(
  operation: string,
  fn: () => T | Promise<T>,
  tags?: Record<string, string>
) => performanceMonitor.measureTradingOperation(operation, fn, tags);

export const measureApiCall = <T>(
  url: string,
  method: string,
  fn: () => T | Promise<T>
) => performanceMonitor.measureApiCall(url, method, fn);

export const measureStrategyCalculation = <T>(
  strategyName: string,
  dataPoints: number,
  fn: () => T | Promise<T>
) => performanceMonitor.measureStrategyCalculation(strategyName, dataPoints, fn);

export const measureChartRender = <T>(
  chartType: string,
  dataPoints: number,
  fn: () => T | Promise<T>
) => performanceMonitor.measureChartRender(chartType, dataPoints, fn);