import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PriceChart from '../PriceChart';
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
  createChartConfig: jest.fn(),
  chartColors: {
    primary: '#3B82F6',
    secondary: '#10B981',
    danger: '#EF4444',
  },
}));

// Mock chart interactions
jest.mock('@/utils/chartInteractions', () => ({
  ChartInteractions: jest.fn().mockImplementation(() => ({
    addClickListener: jest.fn(),
    addHoverListener: jest.fn(),
    resetZoom: jest.fn(),
    destroy: jest.fn(),
  })),
  createChartInteractions: jest.fn(),
}));

describe('PriceChart', () => {
  const mockData: ChartData = {
    prices: [
      { date: new Date('2023-01-01'), price: 100, volume: 1000000 },
      { date: new Date('2023-01-02'), price: 102, volume: 1100000 },
      { date: new Date('2023-01-03'), price: 98, volume: 900000 },
    ],
    movingAverages: [
      [
        { date: new Date('2023-01-03'), value: 100, period: 5 },
      ],
      [
        { date: new Date('2023-01-03'), value: 99, period: 20 },
      ],
    ],
    signals: [
      { date: new Date('2023-01-02'), price: 102, type: 'buy', strength: 0.8 },
    ],
  };

  it('应该渲染图表组件', () => {
    render(<PriceChart data={mockData} />);

    expect(screen.getByTestId('chart-line')).toBeInTheDocument();
  });

  it('应该显示图表数据', () => {
    render(<PriceChart data={mockData} />);

    const chartData = screen.getByTestId('chart-data');
    expect(chartData).toBeInTheDocument();
  });

  it('应该显示图表标题', () => {
    render(<PriceChart data={mockData} title="测试图表" />);

    expect(screen.getByText('测试图表')).toBeInTheDocument();
  });

  it('应该处理空数据', () => {
    const emptyData: ChartData = {
      prices: [],
      movingAverages: [],
      signals: [],
    };

    render(<PriceChart data={emptyData} />);

    expect(screen.getByTestId('chart-line')).toBeInTheDocument();
  });

  it('应该处理点击事件', async () => {
    const onClickMock = jest.fn();
    render(<PriceChart data={mockData} onPointClick={onClickMock} />);

    const chart = screen.getByTestId('chart-container');
    fireEvent.click(chart);

    await waitFor(() => {
      expect(onClickMock).toHaveBeenCalled();
    });
  });

  it('应该支持响应式大小', () => {
    const { container } = render(<PriceChart data={mockData} width={800} height={400} />);

    expect(container.firstChild).toHaveStyle('width: 800px');
  });

  it('应该显示移动平均线', () => {
    render(<PriceChart data={mockData} showMovingAverages={true} />);

    expect(screen.getByTestId('chart-line')).toBeInTheDocument();
  });

  it('应该显示交易信号', () => {
    render(<PriceChart data={mockData} showSignals={true} />);

    expect(screen.getByTestId('chart-line')).toBeInTheDocument();
  });

  it('应该支持自定义主题', () => {
    render(<PriceChart data={mockData} theme="dark" />);

    expect(screen.getByTestId('chart-line')).toBeInTheDocument();
  });

  it('应该处理加载状态', () => {
    render(<PriceChart data={mockData} loading={true} />);

    expect(screen.getByTestId('chart-line')).toBeInTheDocument();
  });

  it('应该处理错误状态', () => {
    render(<PriceChart data={mockData} error="加载失败" />);

    expect(screen.getByTestId('chart-line')).toBeInTheDocument();
  });
});