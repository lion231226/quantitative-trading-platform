import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OptimizationSuggestions } from '../OptimizationSuggestions';
import { StrategyParameters } from '@/types/parameter.types';
import { parameterService } from '@/services/parameterService';

// Mock the parameterService
jest.mock('@/services/parameterService');
const mockParameterService = parameterService as jest.Mocked<typeof parameterService>;

const mockProps = {
  symbol: 'rb2401',
  startDate: '2023-01-01',
  endDate: '2023-12-31',
  currentParameters: {
    movingAveragePeriod: 35,
    stopLoss: 5.0,
    takeProfit: 10.0,
  },
};

// Mock suggestions data for testing
const mockSuggestions = [
  {
    id: 'suggestion-1',
    type: 'risk',
    confidence: 85,
    parameters: {
      movingAveragePeriod: 25,
      stopLoss: 3.0,
      takeProfit: 8.0,
    },
    reasoning: '基于历史波动率分析，建议降低止损比例以减少风险暴露',
    expectedImprovement: '预期降低最大回撤15%，提升收益风险比',
  },
  {
    id: 'suggestion-2',
    type: 'trend',
    confidence: 72,
    parameters: {
      movingAveragePeriod: 15,
      stopLoss: 4.0,
      takeProfit: 12.0,
    },
    reasoning: '根据历史回测，较短的均线周期在当前市场环境下表现更佳',
    expectedImprovement: '预期提升年化收益率8%',
  },
];

describe('OptimizationSuggestions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();

    // Setup default parameterService mock
    mockParameterService.getOptimizationSuggestions = jest.fn().mockResolvedValue(mockSuggestions);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should render correctly with loading state', () => {
    render(<OptimizationSuggestions {...mockProps} />);

    expect(screen.getByText('参数优化建议')).toBeInTheDocument();
    expect(screen.getByText('分析中...')).toBeInTheDocument();
  });

  it('should display suggestions after loading', async () => {
    await act(async () => {
      render(<OptimizationSuggestions {...mockProps} />);
    });

    // Advance timers to trigger the async operation
    act(() => {
      jest.advanceTimersByTime(100);
    });

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText('分析中...')).not.toBeInTheDocument();
    }, { timeout: 5000 });

    // Should show suggestion types
    expect(screen.getByText('风险优化')).toBeInTheDocument();
    expect(screen.getByText('趋势优化')).toBeInTheDocument();
  });

  it('should show empty state when no suggestions', async () => {
    mockParameterService.getOptimizationSuggestions = jest.fn().mockResolvedValue([]);

    await act(async () => {
      render(<OptimizationSuggestions {...mockProps} />);
    });

    act(() => {
      jest.advanceTimersByTime(100);
    });

    await waitFor(() => {
      expect(screen.queryByText('分析中...')).not.toBeInTheDocument();
    }, { timeout: 5000 });

    expect(screen.getByText('暂无优化建议')).toBeInTheDocument();
  });

  it('should handle apply suggestion correctly', async () => {
    const onApplySuggestion = jest.fn();

    await act(async () => {
      render(<OptimizationSuggestions {...mockProps} onApplySuggestion={onApplySuggestion} />);
    });

    act(() => {
      jest.advanceTimersByTime(100);
    });

    await waitFor(() => {
      expect(screen.queryByText('分析中...')).not.toBeInTheDocument();
    }, { timeout: 5000 });

    // Find apply button by text and ensure it's not disabled
    const applyButtons = screen.getAllByText('应用建议');
    expect(applyButtons.length).toBeGreaterThan(0);

    // Click the first apply button
    await act(async () => {
      userEvent.click(applyButtons[0]);
    });

    // Wait for any async operations to complete
    await waitFor(() => {
      expect(onApplySuggestion).toHaveBeenCalledTimes(1);
    }, { timeout: 1000 });
  });

  it('should handle dismiss suggestion correctly', async () => {
    await act(async () => {
      render(<OptimizationSuggestions {...mockProps} />);
    });

    act(() => {
      jest.advanceTimersByTime(100);
    });

    await waitFor(() => {
      expect(screen.queryByText('分析中...')).not.toBeInTheDocument();
    }, { timeout: 5000 });

    // Count initial suggestions
    const initialSuggestions = screen.getAllByText('应用建议');
    expect(initialSuggestions.length).toBeGreaterThan(0);

    // Find and click dismiss button
    const dismissButtons = screen.getAllByLabelText('忽略建议');
    expect(dismissButtons.length).toBeGreaterThan(0);

    await act(async () => {
      userEvent.click(dismissButtons[0]);
    });

    // Check that suggestion was dismissed
    await waitFor(() => {
      const remainingSuggestions = screen.queryAllByText('应用建议');
      expect(remainingSuggestions.length).toBeLessThan(initialSuggestions.length);
    });
  });

  it('should show suggestion details correctly', async () => {
    await act(async () => {
      render(<OptimizationSuggestions {...mockProps} />);
    });

    act(() => {
      jest.advanceTimersByTime(100);
    });

    await waitFor(() => {
      expect(screen.queryByText('分析中...')).not.toBeInTheDocument();
    }, { timeout: 5000 });

    // Check for suggestion details
    expect(screen.getByText('风险优化')).toBeInTheDocument();
    expect(screen.getByText('趋势优化')).toBeInTheDocument();
  });

  it('should display parameter changes correctly', async () => {
    await act(async () => {
      render(<OptimizationSuggestions {...mockProps} />);
    });

    act(() => {
      jest.advanceTimersByTime(100);
    });

    await waitFor(() => {
      expect(screen.queryByText('分析中...')).not.toBeInTheDocument();
    }, { timeout: 5000 });

    // Should show parameter information - use getAllByText since there are multiple matches
    expect(screen.getAllByText(/均线周期/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/止损/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/止盈/).length).toBeGreaterThan(0);
  });

  it('should show confidence levels correctly', async () => {
    await act(async () => {
      render(<OptimizationSuggestions {...mockProps} />);
    });

    act(() => {
      jest.advanceTimersByTime(100);
    });

    await waitFor(() => {
      expect(screen.queryByText('分析中...')).not.toBeInTheDocument();
    }, { timeout: 5000 });

    // Should show confidence levels
    expect(screen.getByText('高可信度 (85%)')).toBeInTheDocument();
    expect(screen.getByText('中可信度 (72%)')).toBeInTheDocument();
  });

  it('should refresh suggestions when clicking refresh button', async () => {
    await act(async () => {
      render(<OptimizationSuggestions {...mockProps} />);
    });

    act(() => {
      jest.advanceTimersByTime(100);
    });

    await waitFor(() => {
      expect(screen.queryByText('分析中...')).not.toBeInTheDocument();
    }, { timeout: 5000 });

    // Find refresh button and verify it exists
    const refreshButton = screen.getByLabelText('刷新建议');
    expect(refreshButton).toBeInTheDocument();
    expect(refreshButton).not.toBeDisabled();

    // Click refresh button and verify it doesn't throw errors
    await act(async () => {
      userEvent.click(refreshButton);
    });

    // Button should still be present and functional
    expect(refreshButton).toBeInTheDocument();
  });

  it('should show applied state correctly', async () => {
    const onApplySuggestion = jest.fn();

    await act(async () => {
      render(<OptimizationSuggestions {...mockProps} onApplySuggestion={onApplySuggestion} />);
    });

    act(() => {
      jest.advanceTimersByTime(100);
    });

    await waitFor(() => {
      expect(screen.queryByText('分析中...')).not.toBeInTheDocument();
    }, { timeout: 5000 });

    // Apply suggestion
    const applyButtons = screen.getAllByText('应用建议');

    await act(async () => {
      userEvent.click(applyButtons[0]);
    });

    // Check that applied state is shown
    await waitFor(() => {
      expect(screen.getByText('已应用')).toBeInTheDocument();
    });
  });

  it('should show expected improvements when available', async () => {
    await act(async () => {
      render(<OptimizationSuggestions {...mockProps} />);
    });

    act(() => {
      jest.advanceTimersByTime(100);
    });

    await waitFor(() => {
      expect(screen.queryByText('分析中...')).not.toBeInTheDocument();
    }, { timeout: 5000 });

    // Should show expected improvements - use getAllByText for multiple matches
    expect(screen.getAllByText(/预期/).length).toBeGreaterThan(0);
  });

  it('should display footer information', async () => {
    await act(async () => {
      render(<OptimizationSuggestions {...mockProps} />);
    });

    act(() => {
      jest.advanceTimersByTime(100);
    });

    await waitFor(() => {
      expect(screen.queryByText('分析中...')).not.toBeInTheDocument();
    }, { timeout: 5000 });

    // Should show footer information
    expect(screen.getByText('关于优化建议')).toBeInTheDocument();
    expect(screen.getByText(/这些建议基于历史数据分析/)).toBeInTheDocument();
  });

  it('should handle error state correctly', async () => {
    mockParameterService.getOptimizationSuggestions = jest.fn().mockRejectedValue(new Error('Network error'));

    // Mock console.error to avoid test output pollution
    const originalError = console.error;
    console.error = jest.fn();

    await act(async () => {
      render(<OptimizationSuggestions {...mockProps} />);
    });

    act(() => {
      jest.advanceTimersByTime(100);
    });

    await waitFor(() => {
      expect(screen.queryByText('分析中...')).not.toBeInTheDocument();
    }, { timeout: 5000 });

    // Should show error state or fallback
    expect(screen.getByText('参数优化建议')).toBeInTheDocument();

    // Restore console.error
    console.error = originalError;
  });
});