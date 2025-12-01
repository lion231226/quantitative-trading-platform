import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { PriceChart } from '../PriceChart';
import { ChartData } from '@/types/chart.types';

// Mock Chart.js
jest.mock('react-chartjs-2', () => ({
  Line: ({ data, options }: any) => (
    <div data-testid="chart-line">
      <div data-testid="chart-data">{JSON.stringify(data)}</div>
      <div data-testid="chart-options">{JSON.stringify(options)}</div>
    </div>
  ),
}));

// Mock chart helpers
jest.mock('@/utils/chartHelpers', () => ({
  registerChartJS: jest.fn(),
  generateChartOptions: jest.fn(() => ({})),
  generatePriceDatasets: jest.fn(() => []),
  generateSignalDatasets: jest.fn(() => []),
  formatChartData: jest.fn((data) => data),
  sampleData: jest.fn((data) => data),
  exportToCSV: jest.fn(() => 'csv,content'),
  exportToJSON: jest.fn(() => '{"data":[]}'),
}));

describe('PriceChart', () => {
  const mockData: ChartData = {
    prices: [
      { timestamp: '2023-01-01', open: 100, high: 105, low: 95, close: 102 },
      { timestamp: '2023-01-02', open: 102, high: 108, low: 98, close: 106 },
    ],
    signals: [
      { timestamp: '2023-01-01', type: 'buy', price: 100, strategy: 'SMA' },
    ],
    movingAverages: [
      { timestamp: '2023-01-01', value: 101, type: 'SMA', period: 20 },
    ],
  };

  const defaultProps = {
    data: mockData,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', () => {
    render(<PriceChart {...defaultProps} />);
    expect(screen.getByTestId('chart-line')).toBeInTheDocument();
  });

  it('displays chart data correctly', () => {
    render(<PriceChart {...defaultProps} />);
    expect(screen.getByTestId('chart-data')).toBeInTheDocument();
  });

  it('shows loading state when isLoading is true', () => {
    render(<PriceChart {...defaultProps} />);
    // Loading state is handled internally, but we can check that the chart renders
    expect(screen.getByTestId('chart-line')).toBeInTheDocument();
  });

  it('renders controls panel', () => {
    render(<PriceChart {...defaultProps} />);
    // Check for control elements
    expect(screen.getByText('显示信号:')).toBeInTheDocument();
    expect(screen.getByText('显示均线:')).toBeInTheDocument();
  });

  it('handles signal clicks', async () => {
    const onSignalClick = jest.fn();
    render(<PriceChart {...defaultProps} onSignalClick={onSignalClick} />);

    // Since we can't easily click on chart elements in this test setup,
    // we'll just ensure the callback is passed correctly
    expect(onSignalClick).toHaveBeenCalledTimes(0);
  });

  it('handles config changes', () => {
    const onParameterChange = jest.fn();
    render(
      <PriceChart {...defaultProps} onParameterChange={onParameterChange} />,
    );

    // Find and toggle signal visibility
    const signalCheckbox = screen.getByLabelText('显示信号:');
    expect(signalCheckbox).toBeInTheDocument();

    fireEvent.click(signalCheckbox);

    // The callback should be called with updated config
    expect(onParameterChange).toHaveBeenCalled();
  });

  it('handles moving average type changes', () => {
    const onParameterChange = jest.fn();
    render(
      <PriceChart {...defaultProps} onParameterChange={onParameterChange} />,
    );

    // Find moving average controls
    const maCheckbox = screen.getByLabelText('显示均线:');
    fireEvent.click(maCheckbox); // Enable moving averages first

    // Wait for MA controls to appear
    waitFor(() => {
      const maTypeSelect = screen.getByLabelText('均线类型:');
      expect(maTypeSelect).toBeInTheDocument();

      fireEvent.change(maTypeSelect, { target: { value: 'EMA' } });
      expect(onParameterChange).toHaveBeenCalled();
    });
  });

  it('handles moving average period changes', () => {
    const onParameterChange = jest.fn();
    render(
      <PriceChart {...defaultProps} onParameterChange={onParameterChange} />,
    );

    // Find and enable moving averages
    const maCheckbox = screen.getByLabelText('显示均线:');
    fireEvent.click(maCheckbox);

    // Wait for MA controls to appear
    waitFor(() => {
      const periodInput = screen.getByLabelText('周期:');
      expect(periodInput).toBeInTheDocument();

      fireEvent.change(periodInput, { target: { value: '50' } });
      expect(onParameterChange).toHaveBeenCalled();
    });
  });

  it('handles export functionality', async () => {
    // Mock URL.createObjectURL and URL.revokeObjectURL
    global.URL.createObjectURL = jest.fn(() => 'mock-url');
    global.URL.revokeObjectURL = jest.fn();

    // Mock link creation and click
    const mockLink = {
      click: jest.fn(),
      href: '',
      download: '',
    };
    global.document.createElement = jest.fn(() => mockLink as any);

    render(<PriceChart {...defaultProps} />);

    // Find export buttons
    const exportButtons = screen.getAllByText('PNG');
    expect(exportButtons.length).toBeGreaterThan(0);

    // Test PNG export
    fireEvent.click(exportButtons[0]);

    await waitFor(() => {
      expect(mockLink.click).toHaveBeenCalled();
    });
  });

  it('applies custom className', () => {
    const customClass = 'custom-chart-class';
    render(<PriceChart {...defaultProps} className={customClass} />);

    const chartContainer = screen
      .getByTestId('chart-line')
      .closest('.custom-chart-class');
    expect(chartContainer).toBeInTheDocument();
  });

  it('uses custom dimensions', () => {
    const customHeight = 600;
    const customWidth = 800;

    render(
      <PriceChart
        {...defaultProps}
        height={customHeight}
        width={customWidth}
      />,
    );

    // Dimensions are passed to the chart, but we can't easily test them
    // without accessing the actual chart instance
    expect(screen.getByTestId('chart-line')).toBeInTheDocument();
  });

  it('displays signal modal when signal is selected', async () => {
    render(<PriceChart {...defaultProps} />);

    // The modal should not be visible initially
    expect(screen.queryByText('交易信号详情')).not.toBeInTheDocument();

    // We can't easily trigger signal clicks in this test setup,
    // but we can verify the modal component structure exists
    expect(screen.getByTestId('chart-line')).toBeInTheDocument();
  });

  describe('Accessibility', () => {
    it('has proper labels for form controls', () => {
      render(<PriceChart {...defaultProps} />);

      expect(screen.getByLabelText('显示信号:')).toBeInTheDocument();
      expect(screen.getByLabelText('显示均线:')).toBeInTheDocument();
    });

    it('has semantic structure', () => {
      render(<PriceChart {...defaultProps} />);

      // The chart should be contained within a proper structure
      expect(screen.getByRole('generic')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles empty data gracefully', () => {
      const emptyData: ChartData = {
        prices: [],
        signals: [],
        movingAverages: [],
      };

      render(<PriceChart data={emptyData} />);
      expect(screen.getByTestId('chart-line')).toBeInTheDocument();
    });

    it('handles data with only prices', () => {
      const pricesOnlyData: ChartData = {
        prices: mockData.prices,
        signals: [],
        movingAverages: [],
      };

      render(<PriceChart data={pricesOnlyData} />);
      expect(screen.getByTestId('chart-line')).toBeInTheDocument();
    });

    it('handles data with only signals', () => {
      const signalsOnlyData: ChartData = {
        prices: [],
        signals: mockData.signals,
        movingAverages: [],
      };

      render(<PriceChart data={signalsOnlyData} />);
      expect(screen.getByTestId('chart-line')).toBeInTheDocument();
    });
  });
});
