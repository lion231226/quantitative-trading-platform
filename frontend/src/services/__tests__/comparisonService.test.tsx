import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useVarietyComparison, useComparisonResults, useAvailableMetrics } from '../comparisonService';
import * as api from '@/lib/api';

// Mock API
jest.mock('@/lib/api');
const mockApi = api as jest.Mocked<typeof api>;

// Mock fetch
global.fetch = jest.fn();

describe('ComparisonService Hooks', () => {
  let queryClient: QueryClient;
  let wrapper: React.FC<{ children: React.ReactNode }>;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });

    wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    jest.clearAllMocks();
  });

  describe('useVarietyComparison', () => {
    const mockRequest = {
      symbols: ['RB2410', 'I2410'],
      startDate: '2024-01-01',
      endDate: '2024-12-31',
      strategy: { name: 'SMA', params: { window: 20 } }
    };

    it('should not fetch when less than 2 symbols are provided', () => {
      const { result } = renderHook(
        () => useVarietyComparison({ ...mockRequest, symbols: ['RB2410'] }),
        { wrapper }
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
      expect(fetch).not.toHaveBeenCalled();
    });

    it('should fetch comparison data when 2+ symbols are provided', async () => {
      const mockResponse = {
        requestId: 'test-id',
        timestamp: '2024-01-01T00:00:00Z',
        request: mockRequest,
        results: [
          {
            symbol: 'RB2410',
            name: '螺纹钢2410',
            sector: '金属',
            exchange: 'SHFE',
            metrics: { totalReturn: 0.15, sharpeRatio: 1.2 },
            trades: [],
            equity: [],
            signals: []
          },
          {
            symbol: 'I2410',
            name: '铁矿石2410',
            sector: '金属',
            exchange: 'DCE',
            metrics: { totalReturn: 0.08, sharpeRatio: 0.9 },
            trades: [],
            equity: [],
            signals: []
          }
        ],
        summary: {
          totalVarieties: 2,
          successfulVarieties: 2,
          failedVarieties: 0,
          bestPerformer: 'RB2410',
          worstPerformer: 'I2410',
          averageReturn: 0.115,
          averageSharpeRatio: 1.05,
          totalTrades: 0,
          dateRange: { start: '2024-01-01', end: '2024-12-31', tradingDays: 252 }
        },
        rankings: []
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const { result } = renderHook(
        () => useVarietyComparison(mockRequest),
        { wrapper }
      );

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
        expect(result.current.data).toEqual(mockResponse);
      });

      expect(fetch).toHaveBeenCalledWith(
        '/api/v1/comparison/run',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(mockRequest)
        })
      );
    });

    it('should handle API errors gracefully', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ message: 'API Error' })
      });

      const { result } = renderHook(
        () => useVarietyComparison(mockRequest),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
        expect(result.current.error).toBeDefined();
      }, { timeout: 5000 });

      expect(result.current.data).toBeUndefined();
    });

    it('should cache results for 5 minutes', async () => {
      const mockResponse = { requestId: 'test-id', results: [], summary: {}, rankings: [] };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const { result, rerender } = renderHook(
        () => useVarietyComparison(mockRequest),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.data).toEqual(mockResponse);
      });

      // Rerender should use cached data
      rerender();

      expect(fetch).toHaveBeenCalledTimes(1);
      expect(result.current.data).toEqual(mockResponse);
    });
  });

  describe('useComparisonResults', () => {
    const mockRequestId = 'test-request-id';
    const mockResults = {
      requestId: mockRequestId,
      results: [],
      summary: {},
      rankings: []
    };

    it('should fetch results for given request ID', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResults
      });

      const { result } = renderHook(
        () => useComparisonResults(mockRequestId),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.data).toEqual(mockResults);
      });

      expect(fetch).toHaveBeenCalledWith(
        `/api/v1/comparison/results/${mockRequestId}`
      );
    });

    it('should not fetch when request ID is empty', () => {
      const { result } = renderHook(
        () => useComparisonResults(''),
        { wrapper }
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
      expect(fetch).not.toHaveBeenCalled();
    });

    it('should handle 404 errors for non-existent request ID', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404
      });

      const { result } = renderHook(
        () => useComparisonResults('non-existent-id'),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.error).toBeDefined();
      });

      expect(result.current.data).toBeUndefined();
    });
  });

  describe('useAvailableMetrics', () => {
    const mockMetrics = [
      'total_return',
      'sharpe_ratio',
      'max_drawdown'
    ];

    it('should fetch available metrics', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetrics
      });

      const { result } = renderHook(
        () => useAvailableMetrics(),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.data).toEqual(mockMetrics);
      });

      expect(fetch).toHaveBeenCalledWith(
        '/api/v1/comparison/metrics'
      );
    });

    it('should cache metrics for 1 hour', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockMetrics
      });

      const { result, rerender } = renderHook(
        () => useAvailableMetrics(),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.data).toEqual(mockMetrics);
      });

      // Rerender should use cached data
      rerender();

      expect(fetch).toHaveBeenCalledTimes(1);
      expect(result.current.data).toEqual(mockMetrics);
    });

    it('should handle API errors', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ message: 'Failed to fetch metrics' })
      });

      const { result } = renderHook(
        () => useAvailableMetrics(),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.error).toBeDefined();
      });

      expect(result.current.data).toBeUndefined();
    });
  });

  describe('Query Keys', () => {
    it('should generate correct query keys', () => {
      const { COMPARISON_QUERY_KEYS } = require('../comparisonService');

      expect(COMPARISON_QUERY_KEYS.comparison('test-id')).toEqual(['comparison', 'test-id']);
      expect(COMPARISON_QUERY_KEYS.availableMetrics()).toEqual(['comparison', 'metrics']);
      expect(COMPARISON_QUERY_KEYS.historicalComparison(['RB2410', 'I2410'], 30))
        .toEqual(['comparison', 'historical', ['RB2410', 'I2410'], 30]);
    });
  });

  describe('Error Handling', () => {
    it('should retry failed requests up to 2 times', async () => {
      // Create a separate query client that allows retries for this test
      const retryQueryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: 2 },
          mutations: { retry: false }
        }
      });

      const retryWrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={retryQueryClient}>{children}</QueryClientProvider>
      );

      const mockRequest = {
        symbols: ['RB2410', 'I2410'],
        startDate: '2024-01-01',
        endDate: '2024-12-31',
        strategy: { name: 'SMA', params: { window: 20 } }
      };

      // Fail twice, then succeed
      (fetch as jest.Mock)
        .mockResolvedValueOnce({ ok: false, status: 500 })
        .mockResolvedValueOnce({ ok: false, status: 500 })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ requestId: 'success', results: [], summary: {}, rankings: [] })
        });

      const { result } = renderHook(
        () => useVarietyComparison(mockRequest),
        { wrapper: retryWrapper }
      );

      await waitFor(() => {
        expect(result.current.data).toBeDefined();
      }, { timeout: 5000 });

      expect(fetch).toHaveBeenCalledTimes(3); // 2 retries + 1 success
    });

    it('should handle network errors', async () => {
      const mockRequest = {
        symbols: ['RB2410', 'I2410'],
        startDate: '2024-01-01',
        endDate: '2024-12-31',
        strategy: { name: 'SMA', params: { window: 20 } }
      };

      (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network Error'));

      const { result } = renderHook(
        () => useVarietyComparison(mockRequest),
        { wrapper }
      );

      await waitFor(() => {
        expect(result.current.error).toBeDefined();
      });

      expect(result.current.data).toBeUndefined();
    });
  });

  describe('Cache Management', () => {
    it('should prefetch comparison data', async () => {
      const { useComparisonCache } = require('../comparisonService');
      const mockRequest = {
        symbols: ['RB2410', 'I2410'],
        startDate: '2024-01-01',
        endDate: '2024-12-31',
        strategy: { name: 'SMA', params: { window: 20 } }
      };

      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ requestId: 'prefetch', results: [], summary: {}, rankings: [] })
      });

      const { result } = renderHook(() => useComparisonCache(), { wrapper });

      result.current.prefetchComparison(mockRequest);

      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith(
          '/api/v1/comparison/run',
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify(mockRequest)
          })
        );
      });
    });

    it('should clear comparison cache', () => {
      const { useComparisonCache } = require('../comparisonService');
      const invalidateQueriesSpy = jest.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useComparisonCache(), { wrapper });

      result.current.clearComparisonCache();

      expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['comparison'] });
    });

    it('should get cached comparison data', async () => {
      const { useComparisonCache } = require('../comparisonService');
      const mockData = { requestId: 'cached', results: [] };

      // Set data in cache
      queryClient.setQueryData(['comparison', 'test-id'], mockData);

      const { result } = renderHook(() => useComparisonCache(), { wrapper });

      const cachedData = result.current.getComparisonData('test-id');
      expect(cachedData).toEqual(mockData);
    });
  });
});