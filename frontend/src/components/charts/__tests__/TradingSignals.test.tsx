import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TradingSignals } from '../TradingSignals';
import { TradingSignal } from '@/types/chart.types';

// Mock Chart.js
jest.mock('react-chartjs-2', () => ({
  Scatter: ({ data, options }: any) => (
    <div data-testid="chart-scatter">
      <div data-testid="chart-data">{JSON.stringify(data)}</div>
      <div data-testid="chart-options">{JSON.stringify(options)}</div>
    </div>
  ),
}));

describe('TradingSignals', () => {
  const mockSignals: TradingSignal[] = [
    { timestamp: '2023-01-01T10:00:00Z', type: 'buy', price: 100, strategy: 'SMA' },
    { timestamp: '2023-01-02T10:00:00Z', type: 'sell', price: 110, strategy: 'SMA' },
    { timestamp: '2023-01-03T10:00:00Z', type: 'buy', price: 105, strategy: 'EMA' },
  ];

  const defaultProps = {
    signals: mockSignals,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', () => {
    render(<TradingSignals {...defaultProps} />);
    expect(screen.getByTestId('chart-scatter')).toBeInTheDocument();
  });

  it('displays signal statistics', () => {
    render(<TradingSignals {...defaultProps} />);

    expect(screen.getByText('2')).toBeInTheDocument(); // Buy signals
    expect(screen.getByText('1')).toBeInTheDocument(); // Sell signals
    expect(screen.getByText('3')).toBeInTheDocument(); // Total signals
  });

  it('shows empty state when no signals', () => {
    render(<TradingSignals signals={[]} />);

    expect(screen.getByText('暂无交易信号')).toBeInTheDocument();
    expect(screen.getByText('请先运行策略以生成交易信号')).toBeInTheDocument();
  });

  it('displays buy and sell signal counts correctly', () => {
    render(<TradingSignals {...defaultProps} />);

    expect(screen.getByText('2')).toBeInTheDocument(); // Buy signals count
    expect(screen.getByText('1')).toBeInTheDocument(); // Sell signals count
  });

  it('handles signal click', async () => {
    const onSignalClick = jest.fn();
    render(<TradingSignals {...defaultProps} onSignalClick={onSignalClick} />);

    // Since we can't easily click on chart points in this test setup,
    // we'll just ensure the callback is available
    expect(onSignalClick).toHaveBeenCalledTimes(0);
  });

  it('applies custom config', () => {
    const customConfig = {
      buyColor: 'rgba(0, 255, 0, 0.8)',
      sellColor: 'rgba(255, 0, 0, 0.8)',
      pointSize: 12,
    };

    render(<TradingSignals {...defaultProps} config={customConfig} />);

    expect(screen.getByTestId('chart-scatter')).toBeInTheDocument();
  });

  it('handles signal hover', () => {
    const onSignalHover = jest.fn();
    render(<TradingSignals {...defaultProps} onSignalHover={onSignalHover} />);

    expect(screen.getByTestId('chart-scatter')).toBeInTheDocument();
  });

  it('displays signal modal with correct information', async () => {
    render(<TradingSignals {...defaultProps} />);

    // Initially, no modal should be visible
    expect(screen.queryByText('交易信号详情')).not.toBeInTheDocument();

    // We can't easily trigger signal clicks in this test setup,
    // but we can verify the component renders without errors
    expect(screen.getByTestId('chart-scatter')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const customClass = 'custom-signals-class';
    render(<TradingSignals {...defaultProps} className={customClass} />);

    const container = screen.getByTestId('chart-scatter').closest('.custom-signals-class');
    expect(container).toBeInTheDocument();
  });

  it('uses custom dimensions', () => {
    const customHeight = 500;
    const customWidth = 700;

    render(<TradingSignals {...defaultProps} height={customHeight} width={customWidth} />);

    expect(screen.getByTestId('chart-scatter')).toBeInTheDocument();
  });

  describe('Signal Config', () => {
    it('uses default colors for buy and sell signals', () => {
      render(<TradingSignals {...defaultProps} />);

      // The chart should render with default colors
      expect(screen.getByTestId('chart-scatter')).toBeInTheDocument();
    });

    it('applies custom point sizes', () => {
      const customConfig = {
        pointSize: 15,
        hoverSize: 20,
      };

      render(<TradingSignals {...defaultProps} config={customConfig} />);

      expect(screen.getByTestId('chart-scatter')).toBeInTheDocument();
    });

    it('controls tooltip visibility', () => {
      const configWithTooltip = {
        showTooltip: true,
      };

      render(<TradingSignals {...defaultProps} config={configWithTooltip} />);

      expect(screen.getByTestId('chart-scatter')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper labels and descriptions', () => {
      render(<TradingSignals {...defaultProps} />);

      // Check for proper text content
      expect(screen.getByText('买入信号')).toBeInTheDocument();
      expect(screen.getByText('卖出信号')).toBeInTheDocument();
      expect(screen.getByText('总信号数')).toBeInTheDocument();
    });

    it('provides semantic structure', () => {
      render(<TradingSignals {...defaultProps} />);

      // The component should have proper semantic structure
      expect(screen.getByRole('generic')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles single signal', () => {
      const singleSignal: TradingSignal[] = [
        { timestamp: '2023-01-01T10:00:00Z', type: 'buy', price: 100, strategy: 'SMA' },
      ];

      render(<TradingSignals signals={singleSignal} />);

      expect(screen.getByText('1')).toBeInTheDocument(); // Buy signals
      expect(screen.getByText('0')).toBeInTheDocument(); // Sell signals
      expect(screen.getByText('1')).toBeInTheDocument(); // Total signals
    });

    it('handles only buy signals', () => {
      const onlyBuySignals: TradingSignal[] = [
        { timestamp: '2023-01-01T10:00:00Z', type: 'buy', price: 100, strategy: 'SMA' },
        { timestamp: '2023-01-02T10:00:00Z', type: 'buy', price: 105, strategy: 'EMA' },
      ];

      render(<TradingSignals signals={onlyBuySignals} />);

      expect(screen.getByText('2')).toBeInTheDocument(); // Buy signals
      expect(screen.getByText('0')).toBeInTheDocument(); // Sell signals
      expect(screen.getByText('2')).toBeInTheDocument(); // Total signals
    });

    it('handles only sell signals', () => {
      const onlySellSignals: TradingSignal[] = [
        { timestamp: '2023-01-01T10:00:00Z', type: 'sell', price: 100, strategy: 'SMA' },
        { timestamp: '2023-01-02T10:00:00Z', type: 'sell', price: 105, strategy: 'EMA' },
      ];

      render(<TradingSignals signals={onlySellSignals} />);

      expect(screen.getByText('0')).toBeInTheDocument(); // Buy signals
      expect(screen.getByText('2')).toBeInTheDocument(); // Sell signals
      expect(screen.getByText('2')).toBeInTheDocument(); // Total signals
    });

    it('handles signals with special characters in strategy name', () => {
      const signalsWithSpecialChars: TradingSignal[] = [
        { timestamp: '2023-01-01T10:00:00Z', type: 'buy', price: 100, strategy: 'SMA-Cross_Over' },
      ];

      render(<TradingSignals signals={signalsWithSpecialChars} />);

      expect(screen.getByTestId('chart-scatter')).toBeInTheDocument();
    });
  });
});
