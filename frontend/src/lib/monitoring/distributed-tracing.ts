/**
 * Distributed Tracing for Frontend
 * Client-side distributed tracing with Sentry integration
 */

import { monitoringService } from '@/services/monitoringService';
import { sentryClient } from './sentry-client';
import { performanceMonitor } from './performance-monitor';

export interface TraceContext {
  traceId: string;
  parentSpanId?: string;
  spanId: string;
  startTime: number;
  tags: Record<string, string>;
  data: Record<string, any>;
}

export interface Span {
  name: string;
  operation: string;
  spanId: string;
  parentSpanId?: string;
  startTime: number;
  endTime?: number;
  duration?: number;
  status: 'ok' | 'error';
  tags: Record<string, string>;
  data: Record<string, any>;
  error?: Error;
}

/**
 * Distributed tracing manager for frontend
 */
export class DistributedTracing {
  private static instance: DistributedTracing;
  private currentTrace: TraceContext | null = null;
  private activeSpans: Map<string, Span> = new Map();
  private spanCounter = 0;

  private constructor() {}

  public static getInstance(): DistributedTracing {
    if (!DistributedTracing.instance) {
      DistributedTracing.instance = new DistributedTracing();
    }
    return DistributedTracing.instance;
  }

  /**
   * Start a new trace
   */
  public startTrace(traceId?: string, parentSpanId?: string): TraceContext {
    const trace: TraceContext = {
      traceId: traceId || this.generateTraceId(),
      parentSpanId,
      spanId: this.generateSpanId(),
      startTime: performance.now(),
      tags: {},
      data: {},
    };

    this.currentTrace = trace;

    // Set trace context in Sentry
    sentryClient.setTags({
      trace_id: trace.traceId,
      span_id: trace.spanId,
    });

    // Add breadcrumb for trace start
    monitoringService.addBreadcrumb({
      category: 'trace',
      message: `Trace started: ${trace.traceId}`,
      level: 'info',
      data: { traceId: trace.traceId, spanId: trace.spanId },
    });

    return trace;
  }

  /**
   * Get current trace context
   */
  public getCurrentTrace(): TraceContext | null {
    return this.currentTrace;
  }

  /**
   * Start a new span
   */
  public startSpan(name: string, operation: string = name, tags?: Record<string, string>): string {
    if (!this.currentTrace) {
      this.startTrace();
    }

    const span: Span = {
      name,
      operation,
      spanId: this.generateSpanId(),
      parentSpanId: this.currentTrace?.spanId,
      startTime: performance.now(),
      status: 'ok',
      tags: tags || {},
      data: {},
    };

    this.activeSpans.set(span.spanId, span);

    // Start Sentry transaction
    const transaction = monitoringService.startTransaction({
      name,
      op: operation,
      tags: span.tags,
      data: span.data,
    });

    // Store transaction reference for finishing
    (span as any).sentryTransaction = transaction;

    return span.spanId;
  }

  /**
   * Finish a span
   */
  public finishSpan(spanId: string, data?: Record<string, any>, error?: Error): number | null {
    const span = this.activeSpans.get(spanId);
    if (!span) {
      return null;
    }

    const endTime = performance.now();
    const duration = endTime - span.startTime;

    span.endTime = endTime;
    span.duration = duration;
    span.status = error ? 'error' : 'ok';
    span.error = error;

    if (data) {
      span.data = { ...span.data, ...data };
    }

    // Update Sentry transaction
    const sentryTransaction = (span as any).sentryTransaction;
    if (sentryTransaction) {
      if (error) {
        sentryTransaction.setStatus('internal_error');
        sentryTransaction.setTag('error', 'true');
      } else {
        sentryTransaction.setStatus('ok');
      }

      if (data) {
        Object.entries(data).forEach(([key, value]) => {
          sentryTransaction.setData(key, value);
        });
      }

      sentryTransaction.finish();
    }

    // Add breadcrumb for span completion
    monitoringService.addBreadcrumb({
      category: 'span',
      message: `Span completed: ${span.name}`,
      level: error ? 'error' : 'info',
      data: {
        spanId: span.spanId,
        operation: span.operation,
        duration: duration,
        status: span.status,
      },
    });

    // Send to performance monitor
    performanceMonitor.endTransaction(spanId, span.data);

    // Clean up
    this.activeSpans.delete(spanId);

    return duration;
  }

  /**
   * Trace an async function
   */
  public async traceFunction<T>(
    name: string,
    fn: () => T | Promise<T>,
    operation?: string,
    tags?: Record<string, string>
  ): Promise<{ result: T; duration: number }> {
    const spanId = this.startSpan(name, operation, tags);

    try {
      const result = await fn();
      const duration = this.finishSpan(spanId, { success: true }) || 0;
      return { result, duration };
    } catch (error) {
      this.finishSpan(spanId, { success: false }, error as Error);
      throw error;
    }
  }

  /**
   * Trace an API call
   */
  public async traceApiCall<T>(
    url: string,
    method: string,
    fn: () => T | Promise<T>
  ): Promise<{ result: T; duration: number; traceId: string }> {
    const traceId = this.currentTrace?.traceId || this.generateTraceId();
    const spanId = this.startSpan(
      `HTTP ${method} ${url}`,
      'http.request',
      { 'http.method': method, 'http.url': url }
    );

    try {
      const startTime = performance.now();
      const result = await fn();
      const endTime = performance.now();
      const duration = endTime - startTime;

      this.finishSpan(spanId, {
        success: true,
        url: this.sanitizeUrl(url),
        method,
        statusCode: 'success',
      });

      // Track with monitoring service
      monitoringService.trackApiRequest(url, method, 200, duration);

      return { result, duration, traceId };
    } catch (error) {
      this.finishSpan(spanId, {
        success: false,
        url: this.sanitizeUrl(url),
        method,
        statusCode: 'error',
      }, error as Error);

      // Track error with monitoring service
      monitoringService.trackApiRequest(url, method, 500, 0);

      throw error;
    }
  }

  /**
   * Trace user interaction
   */
  public traceUserInteraction(
    element: string,
    action: string,
    properties?: Record<string, any>
  ): void {
    const spanId = this.startSpan(
      `User ${action} on ${element}`,
      'user.interaction',
      { element, action, type: 'user' }
    );

    // Finish immediately for user interactions
    setTimeout(() => {
      this.finishSpan(spanId, properties);
    }, 0);

    // Track with monitoring service
    monitoringService.trackUserAction(
      `${action} on ${element}`,
      properties
    );
  }

  /**
   * Trace navigation
   */
  public traceNavigation(from: string, to: string): void {
    const spanId = this.startSpan(
      `Navigation: ${from} → ${to}`,
      'navigation',
      { from, to, type: 'navigation' }
    );

    // Track with monitoring service
    monitoringService.trackNavigation(from, to);

    // Navigation spans are typically completed when the page loads
    const finishNavigation = () => {
      this.finishSpan(spanId, {
        from,
        to,
        pageLoadTime: performance.now() - (this.currentTrace?.startTime || 0),
      });
    };

    // Wait for page load to complete
    if (document.readyState === 'complete') {
      finishNavigation();
    } else {
      window.addEventListener('load', finishNavigation, { once: true });
    }
  }

  /**
   * Trace strategy calculation
   */
  public async traceStrategyCalculation<T>(
    strategyName: string,
    dataPoints: number,
    fn: () => T | Promise<T>
  ): Promise<{ result: T; duration: number }> {
    const spanId = this.startSpan(
      `Strategy calculation: ${strategyName}`,
      'strategy.calculation',
      { strategy: strategyName, dataPoints: dataPoints.toString() }
    );

    try {
      const result = await fn();
      const duration = this.finishSpan(spanId, {
        success: true,
        strategy: strategyName,
        dataPoints,
      }) || 0;

      return { result, duration };
    } catch (error) {
      this.finishSpan(spanId, {
        success: false,
        strategy: strategyName,
        dataPoints,
      }, error as Error);

      throw error;
    }
  }

  /**
   * Trace chart rendering
   */
  public async traceChartRender<T>(
    chartType: string,
    dataPoints: number,
    fn: () => T | Promise<T>
  ): Promise<{ result: T; duration: number }> {
    const spanId = this.startSpan(
      `Chart render: ${chartType}`,
      'chart.render',
      { chart: chartType, dataPoints: dataPoints.toString() }
    );

    try {
      const result = await fn();
      const duration = this.finishSpan(spanId, {
        success: true,
        chart: chartType,
        dataPoints,
      }) || 0;

      return { result, duration };
    } catch (error) {
      this.finishSpan(spanId, {
        success: false,
        chart: chartType,
        dataPoints,
      }, error as Error);

      throw error;
    }
  }

  /**
   * Get tracing headers for API calls
   */
  public getTracingHeaders(): Record<string, string> {
    const trace = this.getCurrentTrace();
    if (!trace) {
      return {};
    }

    return {
      'X-Trace-Id': trace.traceId,
      'X-Parent-Span-Id': trace.spanId,
    };
  }

  /**
   * Extract trace context from response headers
   */
  public extractTraceContext(headers: Record<string, string>): TraceContext | null {
    const traceId = headers['x-trace-id'];
    const spanId = headers['x-span-id'];

    if (traceId && spanId) {
      return {
        traceId,
        spanId,
        startTime: performance.now(),
        tags: {},
        data: {},
      };
    }

    return null;
  }

  /**
   * Get current trace statistics
   */
  public getTraceStats(): {
    traceId: string | null;
    activeSpans: number;
    totalSpans: number;
    traceDuration: number | null;
  } {
    return {
      traceId: this.currentTrace?.traceId || null,
      activeSpans: this.activeSpans.size,
      totalSpans: this.spanCounter,
      traceDuration: this.currentTrace
        ? performance.now() - this.currentTrace.startTime
        : null,
    };
  }

  /**
   * Finish current trace
   */
  public finishTrace(): void {
    if (this.currentTrace) {
      const duration = performance.now() - this.currentTrace.startTime;

      // Add breadcrumb for trace completion
      monitoringService.addBreadcrumb({
        category: 'trace',
        message: `Trace finished: ${this.currentTrace.traceId}`,
        level: 'info',
        data: {
          traceId: this.currentTrace.traceId,
          duration: duration,
        },
      });

      this.currentTrace = null;
    }

    // Clear active spans
    this.activeSpans.clear();
  }

  /**
   * Generate unique trace ID
   */
  private generateTraceId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Generate unique span ID
   */
  private generateSpanId(): string {
    return `span-${++this.spanCounter}`;
  }

  /**
   * Sanitize URL to remove sensitive information
   */
  private sanitizeUrl(url: string): string {
    try {
      const urlObj = new URL(url);

      // Remove sensitive query parameters
      const sensitiveParams = ['token', 'key', 'password', 'secret'];
      sensitiveParams.forEach(param => {
        urlObj.searchParams.delete(param);
      });

      return urlObj.toString();
    } catch {
      return url;
    }
  }
}

// Export singleton instance
export const distributedTracing = DistributedTracing.getInstance();

// Export convenience functions
export const startTrace = (traceId?: string, parentSpanId?: string) =>
  distributedTracing.startTrace(traceId, parentSpanId);

export const startSpan = (name: string, operation?: string, tags?: Record<string, string>) =>
  distributedTracing.startSpan(name, operation, tags);

export const finishSpan = (spanId: string, data?: Record<string, any>, error?: Error) =>
  distributedTracing.finishSpan(spanId, data, error);

export const traceFunction = <T>(
  name: string,
  fn: () => T | Promise<T>,
  operation?: string,
  tags?: Record<string, string>
) => distributedTracing.traceFunction(name, fn, operation, tags);

export const traceApiCall = <T>(
  url: string,
  method: string,
  fn: () => T | Promise<T>
) => distributedTracing.traceApiCall(url, method, fn);

export const traceUserInteraction = (
  element: string,
  action: string,
  properties?: Record<string, any>
) => distributedTracing.traceUserInteraction(element, action, properties);

export const traceNavigation = (from: string, to: string) =>
  distributedTracing.traceNavigation(from, to);

export const traceStrategyCalculation = <T>(
  strategyName: string,
  dataPoints: number,
  fn: () => T | Promise<T>
) => distributedTracing.traceStrategyCalculation(strategyName, dataPoints, fn);

export const traceChartRender = <T>(
  chartType: string,
  dataPoints: number,
  fn: () => T | Promise<T>
) => distributedTracing.traceChartRender(chartType, dataPoints, fn);

export const getTracingHeaders = () => distributedTracing.getTracingHeaders();

export const extractTraceContext = (headers: Record<string, string>) =>
  distributedTracing.extractTraceContext(headers);