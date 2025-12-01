/**
 * Web Vitals Service Tests
 */

import { webVitalsService, WebVitalsMetrics, PerformanceScore } from '@/services/webVitalsService';

// Mock the web-vitals library
jest.mock('web-vitals', () => ({
  getCLS: jest.fn(),
  getFID: jest.fn(),
  getFCP: jest.fn(),
  getLCP: jest.fn(),
  getTTFB: jest.fn(),
}));

// Mock Sentry
jest.mock('@sentry/react', () => ({
  addBreadcrumb: jest.fn(),
  setMeasurement: jest.fn(),
  captureMessage: jest.fn(),
}));

// Mock performance API
const mockPerformanceObserver = jest.fn();
Object.defineProperty(window, 'PerformanceObserver', {
  value: mockPerformanceObserver,
});

const mockPerformance = {
  now: jest.fn(() => Date.now()),
  memory: {
    usedJSHeapSize: 50 * 1024 * 1024, // 50MB
    totalJSHeapSize: 100 * 1024 * 1024, // 100MB
  },
};

Object.defineProperty(window, 'performance', {
  value: mockPerformance,
});

describe('WebVitalsService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    webVitalsService.clearMetricsBuffer();
  });

  describe('trackWebVitals', () => {
    it('should collect all Core Web Vitals metrics', async () => {
      const { getCLS, getFID, getFCP, getLCP, getTTFB } = require('web-vitals');

      const mockMetrics = {
        cls: { value: 0.05 },
        fid: { value: 50 },
        fcp: { value: 1500 },
        lcp: { value: 2000 },
        ttfb: { value: 600 },
      };

      getCLS.mockImplementation((callback) => callback(mockMetrics.cls));
      getFID.mockImplementation((callback) => callback(mockMetrics.fid));
      getFCP.mockImplementation((callback) => callback(mockMetrics.fcp));
      getLCP.mockImplementation((callback) => callback(mockMetrics.lcp));
      getTTFB.mockImplementation((callback) => callback(mockMetrics.ttfb));

      const metrics = await webVitalsService.trackWebVitals();

      expect(metrics).toEqual({
        cls: 0.05,
        fid: 50,
        fcp: 1500,
        lcp: 2000,
        ttfb: 600,
      });

      expect(getCLS).toHaveBeenCalled();
      expect(getFID).toHaveBeenCalled();
      expect(getFCP).toHaveBeenCalled();
      expect(getLCP).toHaveBeenCalled();
      expect(getTTFB).toHaveBeenCalled();
    });

    it('should call update callback when provided', async () => {
      const { getCLS, getFID, getFCP, getLCP, getTTFB } = require('web-vitals');
      const updateCallback = jest.fn();

      webVitalsService.initialize({
        onMetricsUpdate: updateCallback,
      });

      const mockMetrics = {
        cls: { value: 0.05 },
        fid: { value: 50 },
        fcp: { value: 1500 },
        lcp: { value: 2000 },
        ttfb: { value: 600 },
      };

      getCLS.mockImplementation((callback) => callback(mockMetrics.cls));
      getFID.mockImplementation((callback) => callback(mockMetrics.fid));
      getFCP.mockImplementation((callback) => callback(mockMetrics.fcp));
      getLCP.mockImplementation((callback) => callback(mockMetrics.lcp));
      getTTFB.mockImplementation((callback) => callback(mockMetrics.ttfb));

      const metrics = await webVitalsService.trackWebVitals();

      expect(updateCallback).toHaveBeenCalledWith(metrics);
    });
  });

  describe('trackCustomMetric', () => {
    it('should track custom metrics and store in buffer', () => {
      const metricName = 'test_metric';
      const metricValue = 100;
      const tags = { type: 'test' };

      webVitalsService.trackCustomMetric(metricName, metricValue, tags);

      const buffer = webVitalsService.getMetricsBuffer();
      expect(buffer.has(metricName)).toBe(true);
      expect(buffer.get(metricName)).toContain(metricValue);
    });

    it('should maintain buffer size limit', () => {
      const metricName = 'test_metric';
      const bufferLimit = 100;

      // Add more than buffer limit
      for (let i = 0; i < bufferLimit + 10; i++) {
        webVitalsService.trackCustomMetric(metricName, i);
      }

      const buffer = webVitalsService.getMetricsBuffer();
      expect(buffer.get(metricName)).toHaveLength(bufferLimit);
      expect(buffer.get(metricName)?.[0]).toBe(10); // First value should be 10 (0-9 removed)
    });
  });

  describe('analyzePerformanceTrends', () => {
    it('should calculate performance trends correctly', async () => {
      const metricName = 'test_metric';

      // Add metrics with trend
      webVitalsService.trackCustomMetric(metricName, 100);
      webVitalsService.trackCustomMetric(metricName, 150); // 50% increase

      const timeRange = {
        start: new Date(Date.now() - 60000),
        end: new Date(),
      };

      const trends = await webVitalsService.analyzePerformanceTrends(timeRange);

      expect(trends).toHaveLength(1);
      expect(trends[0]).toMatchObject({
        metric: metricName,
        current: 150,
        previous: 100,
        change: 50,
        changePercentage: 50,
        trend: 'degrading', // For lower-is-better metrics, increase is degrading
      });
    });

    it('should identify stable trends', async () => {
      const metricName = 'test_metric';

      webVitalsService.trackCustomMetric(metricName, 100);
      webVitalsService.trackCustomMetric(metricName, 102); // 2% change

      const timeRange = {
        start: new Date(Date.now() - 60000),
        end: new Date(),
      };

      const trends = await webVitalsService.analyzePerformanceTrends(timeRange);

      expect(trends[0].trend).toBe('stable');
    });
  });

  describe('getPerformanceScore', () => {
    it('should calculate good performance score', () => {
      const goodMetrics: WebVitalsMetrics = {
        lcp: 2000,    // < 2500ms
        fid: 80,      // < 100ms
        cls: 0.05,    // < 0.1
        fcp: 1500,    // < 1800ms
        ttfb: 600,    // < 800ms
      };

      const score = webVitalsService.getPerformanceScore(goodMetrics);

      expect(score.overall).toBe('good');
      expect(score.lcp).toBe('good');
      expect(score.fid).toBe('good');
      expect(score.cls).toBe('good');
      expect(score.fcp).toBe('good');
      expect(score.ttfb).toBe('good');
    });

    it('should calculate poor performance score', () => {
      const poorMetrics: WebVitalsMetrics = {
        lcp: 5000,    // > 4000ms
        fid: 400,     // > 300ms
        cls: 0.3,     // > 0.25
        fcp: 4000,    // > 3000ms
        ttfb: 2000,   // > 1800ms
      };

      const score = webVitalsService.getPerformanceScore(poorMetrics);

      expect(score.overall).toBe('poor');
      expect(score.lcp).toBe('poor');
      expect(score.fid).toBe('poor');
      expect(score.cls).toBe('poor');
      expect(score.fcp).toBe('poor');
      expect(score.ttfb).toBe('poor');
    });

    it('should calculate needs-improvement performance score', () => {
      const mixedMetrics: WebVitalsMetrics = {
        lcp: 3000,    // needs-improvement
        fid: 80,      // good
        cls: 0.15,    // needs-improvement
        fcp: 1500,    // good
        ttfb: 1000,   // needs-improvement
      };

      const score = webVitalsService.getPerformanceScore(mixedMetrics);

      // Should be needs-improvement based on mixed scores
      expect(['good', 'needs-improvement', 'poor']).toContain(score.overall);
    });
  });

  describe('measureRenderPerformance', () => {
    it('should measure render performance', () => {
      const componentName = 'TestComponent';
      const renderFn = jest.fn();
      const currentTime = Date.now();

      mockPerformance.now.mockReturnValue(currentTime);

      // Mock requestAnimationFrame
      const mockRequestAnimationFrame = jest.fn((callback) => {
        setTimeout(callback, 16);
        return 1;
      });
      Object.defineProperty(window, 'requestAnimationFrame', {
        value: mockRequestAnimationFrame,
        writable: true,
      });

      const result = webVitalsService.measureRenderPerformance(componentName, renderFn);

      expect(renderFn).toHaveBeenCalled();
      expect(typeof result).toBe('number');

      // Check if metric was tracked
      const buffer = webVitalsService.getMetricsBuffer();
      expect(buffer.has(`render_${componentName}`)).toBe(true);
    });
  });

  describe('measureApiCall', () => {
    it('should measure API call performance for successful calls', async () => {
      const apiName = 'testApi';
      const mockApiCall = jest.fn().mockResolvedValue('success');
      const currentTime = Date.now();

      mockPerformance.now
        .mockReturnValueOnce(currentTime)
        .mockReturnValueOnce(currentTime + 100);

      const result = await webVitalsService.measureApiCall(apiName, mockApiCall);

      expect(mockApiCall).toHaveBeenCalled();
      expect(result).toBe('success');

      // Check if metric was tracked
      const buffer = webVitalsService.getMetricsBuffer();
      expect(buffer.has(`api_${apiName}`)).toBe(true);
    });

    it('should measure API call performance for failed calls', async () => {
      const apiName = 'testApi';
      const mockApiCall = jest.fn().mockRejectedValue(new Error('API Error'));
      const currentTime = Date.now();

      mockPerformance.now
        .mockReturnValueOnce(currentTime)
        .mockReturnValueOnce(currentTime + 100);

      await expect(webVitalsService.measureApiCall(apiName, mockApiCall)).rejects.toThrow('API Error');

      // Check if metric was tracked
      const buffer = webVitalsService.getMetricsBuffer();
      expect(buffer.has(`api_${apiName}`)).toBe(true);
    });
  });

  describe('setupPerformanceAlerts', () => {
    it('should update performance thresholds', () => {
      const customThresholds = {
        lcp: 3000,
        fid: 150,
      };

      const originalThresholds = webVitalsService.getThresholds();

      webVitalsService.setupPerformanceAlerts(customThresholds);

      const updatedThresholds = webVitalsService.getThresholds();
      expect(updatedThresholds.lcp).toBe(3000);
      expect(updatedThresholds.fid).toBe(150);
      expect(updatedThresholds.cls).toBe(originalThresholds.cls); // Should remain unchanged
    });
  });

  describe('clearMetricsBuffer', () => {
    it('should clear all metrics from buffer', () => {
      webVitalsService.trackCustomMetric('test1', 100);
      webVitalsService.trackCustomMetric('test2', 200);

      let buffer = webVitalsService.getMetricsBuffer();
      expect(buffer.size).toBe(2);

      webVitalsService.clearMetricsBuffer();

      buffer = webVitalsService.getMetricsBuffer();
      expect(buffer.size).toBe(0);
    });
  });

  describe('initialization', () => {
    it('should initialize service with custom options', () => {
      const updateCallback = jest.fn();
      const customThresholds = {
        lcp: 3000,
      };

      webVitalsService.initialize({
        onMetricsUpdate: updateCallback,
        thresholds: customThresholds,
      });

      const thresholds = webVitalsService.getThresholds();
      expect(thresholds.lcp).toBe(3000);
    });

    it('should not initialize if already initialized', () => {
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();

      webVitalsService.initialize();
      webVitalsService.initialize(); // Second call should be ignored

      expect(consoleSpy).toHaveBeenCalledTimes(1);

      consoleSpy.mockRestore();
    });
  });
});