import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ComparisonTable } from '../ComparisonTable';
import { VarietyResult } from '@/types/comparison.types';

// Mock data for testing
const mockResults: VarietyResult[] = [
  {
    symbol: 'RB2410',
    name: '螺纹钢2410',
    sector: '金属',
    exchange: 'SHFE',
    metrics: {
      totalReturn: 0.15,
      sharpeRatio: 1.2,
      maxDrawdown: -0.08,
      volatility: 0.12,
      winRate: 0.65,
      totalTrades: 25,
      profitFactor: 1.8,
      annualizedReturn: 0.18,
      cagr: 0.17,
      downsideDeviation: 0.09,
      sortinoRatio: 1.5,
      calmarRatio: 2.25,
      winningTrades: 16,
      losingTrades: 9,
      averageWin: 0.025,
      averageLoss: -0.018,
      averageTrade: 0.012,
      var95: -0.03,
      skewness: 0.3,
      kurtosis: 2.1,
      beta: 1.1,
      alpha: 0.02,
    },
    trades: [],
    equity: [],
    signals: [],
  },
  {
    symbol: 'I2410',
    name: '铁矿石2410',
    sector: '金属',
    exchange: 'DCE',
    metrics: {
      totalReturn: -0.05,
      sharpeRatio: -0.3,
      maxDrawdown: -0.15,
      volatility: 0.18,
      winRate: 0.45,
      totalTrades: 20,
      profitFactor: 0.9,
      annualizedReturn: -0.06,
      cagr: -0.06,
      downsideDeviation: 0.15,
      sortinoRatio: -0.4,
      calmarRatio: -0.4,
      winningTrades: 9,
      losingTrades: 11,
      averageWin: 0.018,
      averageLoss: -0.022,
      averageTrade: -0.008,
      var95: -0.05,
      skewness: -0.2,
      kurtosis: 3.2,
      beta: 0.9,
      alpha: -0.01,
    },
    trades: [],
    equity: [],
    signals: [],
  },
  {
    symbol: 'SC2410',
    name: '原油2410',
    sector: '能源',
    exchange: 'INE',
    metrics: {
      totalReturn: 0.25,
      sharpeRatio: 1.8,
      maxDrawdown: -0.12,
      volatility: 0.2,
      winRate: 0.7,
      totalTrades: 30,
      profitFactor: 2.5,
      annualizedReturn: 0.3,
      cagr: 0.28,
      downsideDeviation: 0.16,
      sortinoRatio: 2.0,
      calmarRatio: 2.5,
      winningTrades: 21,
      losingTrades: 9,
      averageWin: 0.03,
      averageLoss: -0.02,
      averageTrade: 0.015,
      var95: -0.04,
      skewness: 0.1,
      kurtosis: 2.8,
      beta: 1.3,
      alpha: 0.05,
    },
    trades: [],
    equity: [],
    signals: [],
  },
];

describe('ComparisonTable', () => {
  it('renders correctly with results', () => {
    render(<ComparisonTable results={mockResults} />);

    expect(screen.getByText('详细对比数据')).toBeInTheDocument();
    expect(screen.getByText('RB2410')).toBeInTheDocument();
    expect(screen.getByText('I2410')).toBeInTheDocument();
    expect(screen.getByText('SC2410')).toBeInTheDocument();
  });

  it('displays metrics correctly', () => {
    render(<ComparisonTable results={mockResults} />);

    // Check total returns
    expect(screen.getByText('15.00%')).toBeInTheDocument(); // RB2410
    expect(screen.getByText('-5.00%')).toBeInTheDocument(); // I2410
    expect(screen.getByText('25.00%')).toBeInTheDocument(); // SC2410

    // Check Sharpe ratios
    expect(screen.getByText('1.20')).toBeInTheDocument();
    expect(screen.getByText('-0.30')).toBeInTheDocument();
    expect(screen.getByText('1.80')).toBeInTheDocument();

    // Check max drawdowns
    expect(screen.getByText('8.00%')).toBeInTheDocument();
    expect(screen.getByText('15.00%')).toBeInTheDocument();
    expect(screen.getByText('12.00%')).toBeInTheDocument();
  });

  it('applies correct color coding for returns', () => {
    render(<ComparisonTable results={mockResults} />);

    const positiveReturn = screen.getByText('15.00%');
    const negativeReturn = screen.getByText('-5.00%');

    expect(positiveReturn).toHaveClass('text-green-600');
    expect(negativeReturn).toHaveClass('text-red-600');
  });

  it('applies correct color coding for Sharpe ratios', () => {
    render(<ComparisonTable results={mockResults} />);

    const goodSharpe = screen.getByText('1.80'); // SC2410
    const mediumSharpe = screen.getByText('1.20'); // RB2410
    const badSharpe = screen.getByText('-0.30'); // I2410

    expect(goodSharpe).toHaveClass('text-green-600');
    expect(mediumSharpe).toHaveClass('text-yellow-600');
    expect(badSharpe).toHaveClass('text-red-600');
  });

  it('handles sorting correctly', () => {
    render(<ComparisonTable results={mockResults} />);

    // Click on total return header to sort
    const returnHeader = screen.getByText('总收益率');
    fireEvent.click(returnHeader);

    // Should sort in descending order by default
    const rows = screen.getAllByRole('row').slice(1); // Skip header
    expect(rows[0]).toHaveTextContent('SC2410'); // Highest return
    expect(rows[1]).toHaveTextContent('RB2410');
    expect(rows[2]).toHaveTextContent('I2410'); // Lowest return
  });

  it('handles search filtering', () => {
    render(<ComparisonTable results={mockResults} />);

    // Type in search box
    const searchInput =
      screen.getByPlaceholderText('搜索品种代码、名称或版块...');
    fireEvent.change(searchInput, { target: { value: 'RB' } });

    // Should only show RB2410
    expect(screen.getByText('RB2410')).toBeInTheDocument();
    expect(screen.queryByText('I2410')).not.toBeInTheDocument();
    expect(screen.queryByText('SC2410')).not.toBeInTheDocument();
  });

  it('handles sector filtering', () => {
    render(<ComparisonTable results={mockResults} />);

    // Click on sector filter
    const sectorFilter = screen.getByText('全部');
    fireEvent.click(sectorFilter);

    // Select "金属" sector
    const metalOption = screen.getByText('金属');
    fireEvent.click(metalOption);

    // Should only show metal varieties (RB2410, I2410)
    expect(screen.getByText('RB2410')).toBeInTheDocument();
    expect(screen.getByText('I2410')).toBeInTheDocument();
    expect(screen.queryByText('SC2410')).not.toBeInTheDocument();
  });

  it('shows correct result count', () => {
    render(<ComparisonTable results={mockResults} />);

    expect(screen.getByText('显示 3 / 3 个品种')).toBeInTheDocument();
  });

  it('updates result count when filtering', () => {
    render(<ComparisonTable results={mockResults} />);

    // Search for specific variety
    const searchInput =
      screen.getByPlaceholderText('搜索品种代码、名称或版块...');
    fireEvent.change(searchInput, { target: { value: 'RB' } });

    expect(screen.getByText('显示 1 / 3 个品种')).toBeInTheDocument();
    expect(screen.getByText('(搜索: "RB")')).toBeInTheDocument();
  });

  it('handles export functionality', () => {
    // Mock URL.createObjectURL and URL.revokeObjectURL
    global.URL.createObjectURL = jest.fn(() => 'mock-url');
    global.URL.revokeObjectURL = jest.fn();

    // Mock link.click
    const mockLink = {
      href: '',
      download: '',
      click: jest.fn(),
    };
    jest.spyOn(document, 'createElement').mockReturnValue(mockLink as any);

    render(<ComparisonTable results={mockResults} exportable={true} />);

    // Click export button
    const exportButton = screen.getByText('导出');
    fireEvent.click(exportButton);

    // Click CSV export option
    const csvOption = screen.getByText('导出为 CSV');
    fireEvent.click(csvOption);

    expect(mockLink.click).toHaveBeenCalled();
  });

  it('displays empty state when no results', () => {
    render(<ComparisonTable results={[]} />);

    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });

  it('displays no results message when filter returns empty', () => {
    render(<ComparisonTable results={mockResults} />);

    // Search for non-existent variety
    const searchInput =
      screen.getByPlaceholderText('搜索品种代码、名称或版块...');
    fireEvent.change(searchInput, { target: { value: '不存在的品种' } });

    expect(screen.getByText('没有找到匹配的品种')).toBeInTheDocument();
  });

  it('disables sorting when sortable prop is false', () => {
    render(<ComparisonTable results={mockResults} sortable={false} />);

    const returnHeader = screen.getByText('总收益率');
    fireEvent.click(returnHeader);

    // Order should remain unchanged
    const rows = screen.getAllByRole('row').slice(1);
    expect(rows[0]).toHaveTextContent('RB2410'); // Original order
    expect(rows[1]).toHaveTextContent('I2410');
    expect(rows[2]).toHaveTextContent('SC2410');
  });

  it('hides filter when filterable prop is false', () => {
    render(<ComparisonTable results={mockResults} filterable={false} />);

    expect(
      screen.queryByPlaceholderText('搜索品种代码、名称或版块...'),
    ).not.toBeInTheDocument();
    expect(screen.queryByText('全部')).not.toBeInTheDocument();
  });

  it('hides export button when exportable prop is false', () => {
    render(<ComparisonTable results={mockResults} exportable={false} />);

    expect(screen.queryByText('导出')).not.toBeInTheDocument();
  });

  it('handles win rate color coding correctly', () => {
    render(<ComparisonTable results={mockResults} />);

    const highWinRate = screen.getByText('70.0%'); // SC2410
    const mediumWinRate = screen.getByText('65.0%'); // RB2410
    const lowWinRate = screen.getByText('45.0%'); // I2410

    expect(highWinRate).toHaveClass('text-green-600');
    expect(mediumWinRate).toHaveClass('text-green-600');
    expect(lowWinRate).toHaveClass('text-yellow-600');
  });

  it('handles profit factor color coding correctly', () => {
    render(<ComparisonTable results={mockResults} />);

    const highProfitFactor = screen.getByText('2.50'); // SC2410
    const mediumProfitFactor = screen.getByText('1.80'); // RB2410
    const lowProfitFactor = screen.getByText('0.90'); // I2410

    expect(highProfitFactor).toHaveClass('text-green-600');
    expect(mediumProfitFactor).toHaveClass('text-yellow-600');
    expect(lowProfitFactor).toHaveClass('text-red-600');
  });
});
