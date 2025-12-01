/**
 * Application Performance Monitoring (APM) Service
 *
 * Integrates with Sentry for comprehensive error tracking and performance monitoring
 */

import * as Sentry from '@sentry/react';
import { BrowserTracing } from '@sentry/tracing';
import { webVitalsService } from './webVitalsService';

// Monitoring configuration
export interface MonitoringConfig {
  dsn?: string;
  environment?: string;
  release?: string;
  tracesSampleRate?: number;
  profilesSampleRate?: number;
  debug?: boolean;
  beforeSend?: (event: Sentry.Event) => Sentry.Event | null;
}

// User feedback interface
export interface UserFeedback {
  email?: string;
  comments: string;
  name?: string;
  eventId?: string;
}

// Performance monitoring interface
export interface PerformanceTransaction {
  name: string;
  op: string;
  tags?: Record<string, string>;
  data?: Record<string, number>;
}

class MonitoringService {
  private isInitialized = false;
  private config: MonitoringConfig = {};

  /**
   * Initialize Sentry monitoring
   */
  public initialize(config: MonitoringConfig): void {
    if (this.isInitialized || typeof window === 'undefined') {
      return;
    }

    this.config = {
      tracesSampleRate: 0.1, // 10% sample rate for performance monitoring
      profilesSampleRate: 0.1, // 10% sample rate for profiling
      environment: process.env.NODE_ENV || 'development',
      debug: process.env.NODE_ENV === 'development',
      ...config,
    };

    try {
      Sentry.init({
        dsn: this.config.dsn || process.env.NEXT_PUBLIC_SENTRY_DSN,
        environment: this.config.environment,
        release: this.config.release || this.getReleaseVersion(),
        integrations: [
          new BrowserTracing({
            // Use default browser tracing instrumentation
          }),
        ],
        tracesSampleRate: this.config.tracesSampleRate,
        profilesSampleRate: this.config.profilesSampleRate,
        debug: this.config.debug,
        beforeSend: this.config.beforeSend || this.defaultBeforeSend,

        // Performance monitoring settings
        _experiments: {
          // The profilesSampleRate feature is currently in beta
          profilesSampleRate: this.config.profilesSampleRate,
        },

        // Ignore specific errors that don't need to be tracked
        ignoreErrors: [
          // Network errors that are expected
          'Network request failed',
          'Failed to fetch',
          'Load failed',
          // Chrome extensions errors
          'Non-Error promise rejection captured',
          // ResizeObserver loop limit exceeded
          'ResizeObserver loop limit exceeded',
        ],

        // Deny URLs that don't need monitoring
        denyUrls: [
          // Chrome extensions
          /extensions\//i,
          // Local files
          /^file:\/\//i,
        ],
      });

      this.setupCustomMonitoring();
      this.isInitialized = true;

      console.log('🔍 Sentry monitoring initialized');
    } catch (error) {
      console.error('Failed to initialize Sentry monitoring:', error);
    }
  }

  /**
   * Track user action
   */
  public trackUserAction(action: string, properties?: Record<string, any>): void {
    Sentry.addBreadcrumb({
      category: 'user',
      message: action,
      level: 'info',
      data: properties,
    });
  }

  /**
   * Track API request
   */
  public trackApiRequest(
    url: string,
    method: string,
    statusCode: number,
    responseTime: number
  ): void {
    Sentry.addBreadcrumb({
      category: 'http',
      message: `${method} ${url}`,
      level: statusCode >= 400 ? 'error' : 'info',
      data: {
        url,
        method,
        statusCode,
        responseTime,
      },
    });

    // Set span data for performance monitoring
    const span = Sentry.getCurrentHub().getScope()?.getTransaction()?.getActiveSpan();
    if (span) {
      span.setData('http.response_code', statusCode);
      span.setData('http.response_time', responseTime);
    }
  }

  /**
   * Track page navigation
   */
  public trackNavigation(from: string, to: string): void {
    Sentry.addBreadcrumb({
      category: 'navigation',
      message: `Navigation: ${from} → ${to}`,
      level: 'info',
    });
  }

  /**
   * Track custom transaction
   */
  public startTransaction(transaction: PerformanceTransaction): Sentry.Transaction | undefined {
    return Sentry.startTransaction({
      name: transaction.name,
      op: transaction.op,
      tags: transaction.tags,
      data: transaction.data,
    });
  }

  /**
   * Capture error with additional context
   */
  public captureError(
    error: Error | string,
    context?: {
      tags?: Record<string, string>;
      extra?: Record<string, any>;
      level?: Sentry.SeverityLevel;
    }
  ): string | undefined {
    return Sentry.captureException(error, {
      tags: context?.tags,
      extra: context?.extra,
      level: context?.level,
    });
  }

  /**
   * Capture message
   */
  public captureMessage(
    message: string,
    level: Sentry.SeverityLevel = 'info',
    context?: {
      tags?: Record<string, string>;
      extra?: Record<string, any>;
    }
  ): string | undefined {
    return Sentry.captureMessage(message, {
      level,
      tags: context?.tags,
      extra: context?.extra,
    });
  }

  /**
   * Set user context
   */
  public setUser(user: Sentry.User | null): void {
    Sentry.setUser(user);
  }

  /**
   * Set tags for additional context
   */
  public setTags(tags: Record<string, string>): void {
    Object.entries(tags).forEach(([key, value]) => {
      Sentry.setTag(key, value);
    });
  }

  /**
   * Set extra context data
   */
  public setExtra(key: string, value: any): void {
    Sentry.setExtra(key, value);
  }

  /**
   * Add breadcrumb
   */
  public addBreadcrumb(breadcrumb: Sentry.Breadcrumb): void {
    Sentry.addBreadcrumb(breadcrumb);
  }

  /**
   * Capture user feedback
   */
  public captureUserFeedback(feedback: UserFeedback): void {
    Sentry.captureUserFeedback(feedback);
  }

  /**
   * Get current session ID
   */
  public getSessionId(): string | undefined {
    return Sentry.getCurrentHub().getScope()?.getSession()?.id;
  }

  /**
   * Check if monitoring is enabled
   */
  public isEnabled(): boolean {
    return this.isInitialized;
  }

  /**
   * Configure scope with additional context
   */
  public configureScope(callback: (scope: Sentry.Scope) => void): void {
    Sentry.configureScope(callback);
  }

  /**
   * Get release version
   */
  private getReleaseVersion(): string {
    // Try to get version from package.json or environment
    if (process.env.NEXT_PUBLIC_VERSION) {
      return process.env.NEXT_PUBLIC_VERSION;
    }

    if (process.env.NEXT_PUBLIC_COMMIT_SHA) {
      return `${process.env.NEXT_PUBLIC_COMMIT_SHA}`;
    }

    return 'unknown';
  }

  /**
   * Default beforeSend filter
   */
  private defaultBeforeSend(event: Sentry.Event): Sentry.Event | null {
    // Filter out events in development unless debug mode is enabled
    if (process.env.NODE_ENV === 'development' && !this.config.debug) {
      return null;
    }

    // Add additional context to events
    if (event.exception) {
      event.contexts = {
        ...event.contexts,
        performance: {
          metrics: this.getPerformanceMetrics(),
        },
      };
    }

    return event;
  }

  /**
   * Setup custom monitoring integrations
   */
  private setupCustomMonitoring(): void {
    // Integrate with Web Vitals monitoring
    webVitalsService.initialize({
      onMetricsUpdate: (metrics) => {
        this.sendWebVitalsToSentry(metrics);
      },
    });

    // Setup global error handlers
    this.setupGlobalErrorHandlers();

    // Setup performance monitoring
    this.setupPerformanceMonitoring();
  }

  /**
   * Send Web Vitals metrics to Sentry
   */
  private sendWebVitalsToSentry(metrics: any): void {
    Sentry.setMeasurement('lcp', metrics.lcp, 'millisecond');
    Sentry.setMeasurement('fid', metrics.fid, 'millisecond');
    Sentry.setMeasurement('cls', metrics.cls, '');
    Sentry.setMeasurement('fcp', metrics.fcp, 'millisecond');
    Sentry.setMeasurement('ttfb', metrics.ttfb, 'millisecond');

    // Add breadcrumb for performance monitoring
    Sentry.addBreadcrumb({
      category: 'performance',
      message: 'Web Vitals collected',
      level: 'info',
      data: metrics,
    });
  }

  /**
   * Setup global error handlers
   */
  private setupGlobalErrorHandlers(): void {
    // Handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.captureError(event.reason, {
        tags: {
          unhandled: 'true',
          type: 'promise-rejection',
        },
      });
    });

    // Handle JavaScript errors
    window.addEventListener('error', (event) => {
      this.captureError(event.error || new Error(event.message), {
        tags: {
          unhandled: 'true',
          type: 'javascript-error',
        },
        extra: {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
        },
      });
    });
  }

  /**
   * Setup performance monitoring
   */
  private setupPerformanceMonitoring(): void {
    // Monitor page load performance
    if ('performance' in window && 'getEntriesByType' in performance) {
      setTimeout(() => {
        const navigationEntries = performance.getEntriesByType('navigation');
        if (navigationEntries.length > 0) {
          const navEntry = navigationEntries[0] as PerformanceNavigationTiming;

          this.addBreadcrumb({
            category: 'performance',
            message: 'Page load metrics',
            level: 'info',
            data: {
              domLoadTime: navEntry.loadEventEnd - navEntry.loadEventStart,
              pageLoadTime: navEntry.loadEventEnd - navEntry.fetchStart,
              domInteractive: navEntry.domInteractive - navEntry.fetchStart,
              firstContentfulPaint: this.getFirstContentfulPaint(),
            },
          });
        }
      }, 0);
    }
  }

  /**
   * Get First Contentful Paint time
   */
  private getFirstContentfulPaint(): number | null {
    const paintEntries = performance.getEntriesByType('paint');
    const fcpEntry = paintEntries.find(entry => entry.name === 'first-contentful-paint');
    return fcpEntry ? fcpEntry.startTime : null;
  }

  /**
   * Get current performance metrics
   */
  private getPerformanceMetrics(): Record<string, any> {
    const metrics: Record<string, any> = {};

    // Navigation timing
    if ('performance' in window && 'getEntriesByType' in performance) {
      const navigationEntries = performance.getEntriesByType('navigation');
      if (navigationEntries.length > 0) {
        const navEntry = navigationEntries[0] as PerformanceNavigationTiming;
        metrics.navigation = {
          domLoadTime: navEntry.loadEventEnd - navEntry.loadEventStart,
          pageLoadTime: navEntry.loadEventEnd - navEntry.fetchStart,
          domInteractive: navEntry.domInteractive - navEntry.fetchStart,
        };
      }
    }

    // Memory usage
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      metrics.memory = {
        usedJSHeapSize: memory.usedJSHeapSize,
        totalJSHeapSize: memory.totalJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit,
      };
    }

    return metrics;
  }

  /**
   * Cleanup monitoring resources
   */
  public dispose(): void {
    if (this.isInitialized) {
      // Close Sentry if needed
      Sentry.close(2000).then(() => {
        console.log('🔍 Sentry monitoring closed');
      });
      this.isInitialized = false;
    }
  }
}

// Export singleton instance
export const monitoringService = new MonitoringService();

// Export types
export type {
  MonitoringConfig,
  UserFeedback,
  PerformanceTransaction,
};

// Re-export Sentry utilities for convenience
export { Sentry };

// Export commonly used functions
export const {
  captureException,
  captureMessage,
  setUser,
  setTag,
  setTags,
  setExtra,
  addBreadcrumb,
  configureScope,
} = Sentry;