/**
 * Sentry Client Configuration
 * Enhanced monitoring setup with production-ready configuration
 */

import * as Sentry from '@sentry/nextjs';
import { BrowserTracing } from '@sentry/tracing';
import { monitoringService } from '@/services/monitoringService';

export interface SentryClientConfig {
  dsn?: string;
  environment?: string;
  release?: string;
  tracesSampleRate?: number;
  profilesSampleRate?: number;
  debug?: boolean;
  tunnel?: string;
}

/**
 * Initialize Sentry client for Next.js application
 */
export class SentryClient {
  private static instance: SentryClient;
  private isInitialized = false;

  private constructor() {}

  public static getInstance(): SentryClient {
    if (!SentryClient.instance) {
      SentryClient.instance = new SentryClient();
    }
    return SentryClient.instance;
  }

  /**
   * Initialize Sentry with enhanced configuration
   */
  public initialize(config: SentryClientConfig = {}): void {
    if (this.isInitialized) {
      console.warn('Sentry already initialized');
      return;
    }

    try {
      Sentry.init({
        dsn: config.dsn || process.env.NEXT_PUBLIC_SENTRY_DSN,
        environment: config.environment || process.env.NODE_ENV || 'development',
        release: config.release || this.getReleaseVersion(),
        tracesSampleRate: config.tracesSampleRate || 0.1,
        profilesSampleRate: config.profilesSampleRate || 0.1,
        debug: config.debug || process.env.NODE_ENV === 'development',
        tunnel: config.tunnel,

        // Performance monitoring integrations
        integrations: [
          new BrowserTracing({
            routingInstrumentation: Sentry.reactRouterV6Instrumentation(
              React.useEffect,
              useLocation,
              useNavigationType,
              createRoutesFromChildren,
              matchRoutes
            ),
          }),
        ],

        // Error filtering and processing
        beforeSend: this.beforeSend.bind(this),
        ignoreErrors: [
          // Network errors
          'Network request failed',
          'Failed to fetch',
          'Load failed',
          // Browser extension errors
          'Non-Error promise rejection captured',
          'ResizeObserver loop limit exceeded',
          // Third-party script errors
          'Script error.',
          'Non-Error promise rejection captured',
        ],
        denyUrls: [
          // Chrome extensions
          /extensions\//i,
          // Firefox extensions
          /^resource:\/\//i,
          // Local files
          /^file:\/\//i,
        ],

        // Performance settings
        tracesSampler: (samplingContext) => {
          // Sample more transactions in production for better monitoring
          const environment = process.env.NODE_ENV;
          if (environment === 'production') {
            return 0.2; // 20% sampling in production
          }
          return 0.1; // 10% sampling in other environments
        },

        // Security settings
        sendDefaultPii: false,
        attachStacktrace: true,
        maxBreadcrumbs: 100,

        // Session replay
        _experiments: {
          // Enable session replay if available
          replaySessionSampleRate: 0.1,
          replayOnErrorSampleRate: 1.0,
        },
      });

      // Setup custom monitoring integrations
      this.setupCustomIntegrations();

      this.isInitialized = true;
      console.log('✅ Sentry client initialized successfully');

    } catch (error) {
      console.error('❌ Failed to initialize Sentry client:', error);
    }
  }

  /**
   * Custom beforeSend filter
   */
  private beforeSend(event: Sentry.Event, hint: Sentry.EventHint): Sentry.Event | null {
    // Filter out events in development unless debug mode is enabled
    if (process.env.NODE_ENV === 'development' && !process.env.NEXT_PUBLIC_SENTRY_DEBUG) {
      return null;
    }

    // Add custom context to errors
    if (event.exception) {
      event.contexts = {
        ...event.contexts,
        app: {
          name: 'quant-trading-platform',
          version: process.env.NEXT_PUBLIC_VERSION || '0.1.0',
          buildTime: process.env.NEXT_PUBLIC_BUILD_TIME,
        },
        performance: {
          metrics: this.getPerformanceMetrics(),
        },
      };
    }

    // Filter out sensitive information
    if (event.request) {
      // Remove sensitive headers
      const sensitiveHeaders = ['authorization', 'cookie', 'x-api-key'];
      if (event.request.headers) {
        sensitiveHeaders.forEach(header => {
          delete event.request?.headers?.[header];
        });
      }

      // Sanitize URLs
      if (event.request.url) {
        event.request.url = this.sanitizeUrl(event.request.url);
      }
    }

    return event;
  }

  /**
   * Setup custom monitoring integrations
   */
  private setupCustomIntegrations(): void {
    // Enhanced error tracking for financial operations
    this.setupFinancialOperationTracking();

    // User session monitoring
    this.setupUserSessionMonitoring();

    // Performance monitoring for trading operations
    this.setupTradingPerformanceMonitoring();
  }

  /**
   * Setup financial operation tracking
   */
  private setupFinancialOperationTracking(): void {
    // This will integrate with trading operations
    // to provide specialized error context
  }

  /**
   * Setup user session monitoring
   */
  private setupUserSessionMonitoring(): void {
    // Monitor user session lifecycle
    if (typeof window !== 'undefined') {
      // Track session start
      Sentry.addBreadcrumb({
        category: 'session',
        message: 'Session started',
        level: 'info',
        timestamp: Date.now() / 1000,
      });

      // Track page visibility changes
      document.addEventListener('visibilitychange', () => {
        Sentry.addBreadcrumb({
          category: 'session',
          message: `Page visibility: ${document.visibilityState}`,
          level: 'info',
        });
      });
    }
  }

  /**
   * Setup trading performance monitoring
   */
  private setupTradingPerformanceMonitoring(): void {
    // Monitor critical trading operations performance
    // This will be enhanced in subtask 1.2
  }

  /**
   * Get current release version
   */
  private getReleaseVersion(): string {
    if (process.env.NEXT_PUBLIC_VERSION) {
      return process.env.NEXT_PUBLIC_VERSION;
    }

    if (process.env.NEXT_PUBLIC_COMMIT_SHA) {
      return `v${process.env.NEXT_PUBLIC_COMMIT_SHA.substring(0, 8)}`;
    }

    return '0.1.0';
  }

  /**
   * Get performance metrics
   */
  private getPerformanceMetrics(): Record<string, any> {
    const metrics: Record<string, any> = {};

    if (typeof window !== 'undefined' && 'performance' in window) {
      // Navigation timing
      const navigationEntries = performance.getEntriesByType('navigation');
      if (navigationEntries.length > 0) {
        const navEntry = navigationEntries[0] as PerformanceNavigationTiming;
        metrics.navigation = {
          domLoadTime: navEntry.loadEventEnd - navEntry.loadEventStart,
          pageLoadTime: navEntry.loadEventEnd - navEntry.fetchStart,
          domInteractive: navEntry.domInteractive - navEntry.fetchStart,
          firstContentfulPaint: this.getFirstContentfulPaint(),
        };
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
    }

    return metrics;
  }

  /**
   * Get First Contentful Paint time
   */
  private getFirstContentfulPaint(): number | null {
    if (typeof window === 'undefined' || !('performance' in window)) {
      return null;
    }

    const paintEntries = performance.getEntriesByType('paint');
    const fcpEntry = paintEntries.find(entry => entry.name === 'first-contentful-paint');
    return fcpEntry ? fcpEntry.startTime : null;
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

  /**
   * Check if Sentry is initialized
   */
  public isEnabled(): boolean {
    return this.isInitialized;
  }
}

// Export singleton instance
export const sentryClient = SentryClient.getInstance();

// Re-export Sentry utilities
export { Sentry };