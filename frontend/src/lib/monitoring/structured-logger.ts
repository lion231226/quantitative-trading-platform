/**
 * Structured Logger for Frontend
 * Comprehensive client-side logging with contextual information
 */

import { monitoringService } from '@/services/monitoringService';
import { distributedTracing } from './distributed-tracing';

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  logger: string;
  module?: string;
  function?: string;
  line?: number;

  // Contextual information
  traceId?: string;
  spanId?: string;
  userId?: string;
  sessionId?: string;
  requestId?: string;

  // Business context
  operation?: string;
  resource?: string;
  status?: string;
  duration?: number;

  // Technical context
  service: string;
  version: string;
  environment: string;
  userAgent: string;
  url: string;

  // Error context
  errorType?: string;
  errorCode?: string;
  stackTrace?: string;

  // Custom data
  tags?: Record<string, string>;
  metadata?: Record<string, any>;
}

export enum LogLevel {
  CRITICAL = 50,
  ERROR = 40,
  WARNING = 30,
  INFO = 20,
  DEBUG = 10,
}

export interface LoggerConfig {
  level: LogLevel;
  structured: boolean;
  consoleOutput: boolean;
  remoteLogging: boolean;
  sanitizeData: boolean;
  maxLogSize: number;
  batchSize: number;
  batchTimeout: number;
}

/**
 * Structured logger for frontend applications
 */
export class StructuredLogger {
  private static instance: StructuredLogger;
  private config: LoggerConfig;
  private logBuffer: LogEntry[] = [];
  private batchTimer: NodeJS.Timeout | null = null;
  private sessionId: string;

  private constructor() {
    this.sessionId = this.generateSessionId();
    this.config = this.getDefaultConfig();
    this.setupBatching();
  }

  public static getInstance(): StructuredLogger {
    if (!StructuredLogger.instance) {
      StructuredLogger.instance = new StructuredLogger();
    }
    return StructuredLogger.instance;
  }

  private getDefaultConfig(): LoggerConfig {
    const isDevelopment = process.env.NODE_ENV === 'development';

    return {
      level: isDevelopment ? LogLevel.DEBUG : LogLevel.INFO,
      structured: true,
      consoleOutput: true,
      remoteLogging: !isDevelopment,
      sanitizeData: true,
      maxLogSize: 10 * 1024, // 10KB
      batchSize: 100,
      batchTimeout: 5000, // 5 seconds
    };
  }

  /**
   * Configure logger settings
   */
  public configure(config: Partial<LoggerConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Get logger for specific module
   */
  public getLogger(name: string): Logger {
    return new Logger(name, this);
  }

  /**
   * Create log entry with context
   */
  public createLogEntry(
    level: LogLevel,
    message: string,
    logger: string,
    data: Partial<LogEntry> = {}
  ): LogEntry {
    const trace = distributedTracing.getCurrentTrace();

    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      logger,
      service: 'quant-trading-frontend',
      version: process.env.NEXT_PUBLIC_VERSION || '0.1.0',
      environment: process.env.NODE_ENV || 'development',
      userAgent: navigator.userAgent,
      url: window.location.href,

      // Add tracing context
      traceId: trace?.traceId,
      spanId: trace?.spanId,
      sessionId: this.sessionId,

      // Add custom data
      ...data,
    };

    // Sanitize sensitive data if enabled
    if (this.config.sanitizeData) {
      this.sanitizeLogEntry(entry);
    }

    return entry;
  }

  /**
   * Process log entry
   */
  public processLogEntry(entry: LogEntry): void {
    if (entry.level < this.config.level) {
      return;
    }

    // Console output
    if (this.config.consoleOutput) {
      this.outputToConsole(entry);
    }

    // Remote logging
    if (this.config.remoteLogging) {
      this.addToBatch(entry);
    }

    // Send to Sentry for errors and warnings
    if (entry.level >= LogLevel.WARNING) {
      this.sendToSentry(entry);
    }

    // Send to monitoring service
    this.sendToMonitoringService(entry);
  }

  /**
   * Output log entry to console
   */
  private outputToConsole(entry: LogEntry): void {
    const levelName = LogLevel[entry.level];
    const prefix = `[${entry.timestamp}] ${levelName} [${entry.logger}]`;

    if (this.config.structured) {
      console.log(prefix, entry);
    } else {
      console.log(`${prefix} ${entry.message}`, entry.metadata);
    }
  }

  /**
   * Add log entry to batch
   */
  private addToBatch(entry: LogEntry): void {
    this.logBuffer.push(entry);

    if (this.logBuffer.length >= this.config.batchSize) {
      this.flushBatch();
    }
  }

  /**
   * Setup batch processing
   */
  private setupBatching(): void {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
    }

    this.batchTimer = setInterval(() => {
      if (this.logBuffer.length > 0) {
        this.flushBatch();
      }
    }, this.config.batchTimeout);
  }

  /**
   * Flush log batch to remote server
   */
  private async flushBatch(): Promise<void> {
    if (this.logBuffer.length === 0) {
      return;
    }

    const batch = [...this.logBuffer];
    this.logBuffer = [];

    try {
      await this.sendBatchToServer(batch);
    } catch (error) {
      console.error('Failed to send log batch:', error);
      // Re-add failed entries to buffer for retry
      this.logBuffer.unshift(...batch.slice(0, 10)); // Limit retry to 10 entries
    }
  }

  /**
   * Send log batch to server
   */
  private async sendBatchToServer(batch: LogEntry[]): Promise<void> {
    if (typeof window === 'undefined') return;

    const response = await fetch('/api/logs', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...distributedTracing.getTracingHeaders(),
      },
      body: JSON.stringify({
        logs: batch,
        timestamp: new Date().toISOString(),
        source: 'frontend',
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to send logs: ${response.statusText}`);
    }
  }

  /**
   * Send error to Sentry
   */
  private sendToSentry(entry: LogEntry): void {
    if (entry.level >= LogLevel.ERROR) {
      const error = new Error(entry.message);
      if (entry.stackTrace) {
        error.stack = entry.stackTrace;
      }

      monitoringService.captureError(error, {
        tags: entry.tags,
        extra: {
          logEntry: entry,
          operation: entry.operation,
          resource: entry.resource,
        },
        level: this.getSentryLevel(entry.level),
      });
    } else {
      monitoringService.captureMessage(entry.message, this.getSentryLevel(entry.level), {
        tags: entry.tags,
        extra: entry.metadata,
      });
    }
  }

  /**
   * Send to monitoring service
   */
  private sendToMonitoringService(entry: LogEntry): void {
    monitoringService.addBreadcrumb({
      category: entry.operation || 'application',
      message: entry.message,
      level: this.getMonitoringLevel(entry.level),
      data: entry.metadata,
    });

    // Set user context if available
    if (entry.userId) {
      monitoringService.setUser({
        id: entry.userId,
        session_id: entry.sessionId,
      });
    }

    // Set tags
    if (entry.tags) {
      monitoringService.setTags(entry.tags);
    }
  }

  /**
   * Sanitize log entry to remove sensitive data
   */
  private sanitizeLogEntry(entry: LogEntry): void {
    const sensitiveFields = [
      'password', 'token', 'secret', 'key', 'auth', 'credential',
      'session', 'cookie', 'authorization', 'bearer', 'api_key'
    ];

    const sanitizeObject = (obj: any): any => {
      if (typeof obj !== 'object' || obj === null) {
        return obj;
      }

      if (Array.isArray(obj)) {
        return obj.map(sanitizeObject);
      }

      const sanitized: any = {};
      for (const [key, value] of Object.entries(obj)) {
        if (sensitiveFields.some(field => key.toLowerCase().includes(field))) {
          sanitized[key] = '[REDACTED]';
        } else if (typeof value === 'object') {
          sanitized[key] = sanitizeObject(value);
        } else {
          sanitized[key] = value;
        }
      }
      return sanitized;
    };

    if (entry.metadata) {
      entry.metadata = sanitizeObject(entry.metadata);
    }

    if (entry.tags) {
      entry.tags = sanitizeObject(entry.tags);
    }
  }

  /**
   * Get Sentry level from log level
   */
  private getSentryLevel(level: LogLevel): import('@sentry/react').SeverityLevel {
    switch (level) {
      case LogLevel.CRITICAL:
        return 'fatal';
      case LogLevel.ERROR:
        return 'error';
      case LogLevel.WARNING:
        return 'warning';
      case LogLevel.INFO:
        return 'info';
      case LogLevel.DEBUG:
        return 'debug';
      default:
        return 'info';
    }
  }

  /**
   * Get monitoring level from log level
   */
  private getMonitoringLevel(level: LogLevel): 'fatal' | 'error' | 'warning' | 'info' | 'debug' {
    switch (level) {
      case LogLevel.CRITICAL:
        return 'fatal';
      case LogLevel.ERROR:
        return 'error';
      case LogLevel.WARNING:
        return 'warning';
      case LogLevel.INFO:
        return 'info';
      case LogLevel.DEBUG:
        return 'debug';
      default:
        return 'info';
    }
  }

  /**
   * Generate session ID
   */
  private generateSessionId(): string {
    return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Force flush all logs
   */
  public async flush(): Promise<void> {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
    }
    await this.flushBatch();
    this.setupBatching();
  }

  /**
   * Get logger statistics
   */
  public getStats(): {
    bufferSize: number;
    sessionId: string;
    config: LoggerConfig;
  } {
    return {
      bufferSize: this.logBuffer.length,
      sessionId: this.sessionId,
      config: this.config,
    };
  }
}

/**
 * Logger class for specific modules
 */
export class Logger {
  private name: string;
  private structuredLogger: StructuredLogger;

  constructor(name: string, structuredLogger: StructuredLogger) {
    this.name = name;
    this.structuredLogger = structuredLogger;
  }

  private log(
    level: LogLevel,
    message: string,
    data: Partial<LogEntry> = {},
    error?: Error
  ): void {
    const entry = this.structuredLogger.createLogEntry(level, message, this.name, {
      ...data,
      ...(error && {
        errorType: error.name,
        stackTrace: error.stack,
      }),
    });

    this.structuredLogger.processLogEntry(entry);
  }

  public debug(message: string, data: Partial<LogEntry> = {}): void {
    this.log(LogLevel.DEBUG, message, data);
  }

  public info(message: string, data: Partial<LogEntry> = {}): void {
    this.log(LogLevel.INFO, message, data);
  }

  public warning(message: string, data: Partial<LogEntry> = {}): void {
    this.log(LogLevel.WARNING, message, data);
  }

  public error(message: string, error?: Error, data: Partial<LogEntry> = {}): void {
    this.log(LogLevel.ERROR, message, data, error);
  }

  public critical(message: string, error?: Error, data: Partial<LogEntry> = {}): void {
    this.log(LogLevel.CRITICAL, message, data, error);
  }

  /**
   * Log user action
   */
  public userAction(action: string, resource: string, data: Partial<LogEntry> = {}): void {
    this.info(`User action: ${action} on ${resource}`, {
      operation: 'user_action',
      action,
      resource,
      ...data,
    });
  }

  /**
   * Log API call
   */
  public apiCall(method: string, url: string, statusCode: number, duration: number, data: Partial<LogEntry> = {}): void {
    const level = statusCode >= 400 ? LogLevel.ERROR : LogLevel.INFO;
    this.log(level, `API ${method} ${url} - ${statusCode}`, {
      operation: 'api_call',
      method,
      url,
      statusCode,
      duration,
      ...data,
    });
  }

  /**
   * Log performance metric
   */
  public performance(metricName: string, value: number, unit: string = 'ms', data: Partial<LogEntry> = {}): void {
    this.info(`Performance: ${metricName} = ${value}${unit}`, {
      operation: 'performance_metric',
      metricName,
      value,
      unit,
      ...data,
    });
  }

  /**
   * Log strategy calculation
   */
  public strategyCalculation(
    strategyName: string,
    dataPoints: number,
    duration: number,
    success: boolean = true,
    data: Partial<LogEntry> = {}
  ): void {
    const level = success ? LogLevel.INFO : LogLevel.ERROR;
    this.log(level, `Strategy calculation: ${strategyName}`, {
      operation: 'strategy_calculation',
      strategyName,
      dataPoints,
      duration,
      success,
      ...data,
    });
  }
}

// Export singleton instance
export const structuredLogger = StructuredLogger.getInstance();

// Export convenience functions
export const getLogger = (name: string) => structuredLogger.getLogger(name);

export const configureLogging = (config: Partial<LoggerConfig>) => {
  structuredLogger.configure(config);
};

export const flushLogs = () => structuredLogger.flush();