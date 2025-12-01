import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import PerformanceMonitor from '../PerformanceMonitor';

describe('PerformanceMonitor', () => {
  const defaultProps = {
    dataPoints: 1000,
    renderTime: 16,
    fps: 60,
    memoryUsage: 50 * 1024 * 1024, // 50MB
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders performance monitor with default props', () => {
    render(<PerformanceMonitor {...defaultProps} />);

    expect(screen.getByText('📊 性能监控')).toBeInTheDocument();
    expect(screen.getByText('60.0')).toBeInTheDocument(); // FPS
    expect(screen.getByText('16.0ms')).toBeInTheDocument(); // 渲染时间
    expect(screen.getByText('1K')).toBeInTheDocument(); // 数据点
  });

  test('shows excellent performance indicators', () => {
    render(<PerformanceMonitor {...defaultProps} />);

    // 检查优秀性能的图标
    const excellentIndicators = screen.getAllByText('🟢');
    expect(excellentIndicators.length).toBeGreaterThanOrEqual(1);
  });

  test('displays performance warnings for low FPS', () => {
    const lowFpsProps = {
      ...defaultProps,
      fps: 12,
      renderTime: 83,
    };

    render(<PerformanceMonitor {...lowFpsProps} />);

    // 应该显示警告图标
    const warningIndicators = screen.getAllByText('🟡');
    expect(warningIndicators.length).toBeGreaterThanOrEqual(1);

    // 应该显示性能警报
    expect(screen.getByText(/性能警告:/)).toBeInTheDocument();
  });

  test('displays critical performance warnings for very low FPS', () => {
    const criticalProps = {
      ...defaultProps,
      fps: 8,
      renderTime: 125,
    };

    render(<PerformanceMonitor {...criticalProps} />);

    // 应该显示严重警告图标
    const criticalIndicators = screen.getAllByText('🔴');
    expect(criticalIndicators.length).toBeGreaterThanOrEqual(1);

    // 应该显示严重性能问题警报
    expect(screen.getByText(/严重性能问题:/)).toBeInTheDocument();
  });

  test('shows memory usage warnings', () => {
    const highMemoryProps = {
      ...defaultProps,
      memoryUsage: 250 * 1024 * 1024, // 250MB
    };

    render(<PerformanceMonitor {...highMemoryProps} />);

    expect(screen.getByText(/内存使用过高:/)).toBeInTheDocument();
  });

  test('shows data volume warnings for large datasets', () => {
    const largeDataProps = {
      ...defaultProps,
      dataPoints: 60000,
    };

    render(<PerformanceMonitor {...largeDataProps} />);

    expect(screen.getByText(/数据量过大:/)).toBeInTheDocument();
  });

  test('detects FPS drop', () => {
    const { rerender } = render(<PerformanceMonitor {...defaultProps} />);

    // 初始状态应该没有警报
    expect(screen.queryByText(/FPS显著下降/)).not.toBeInTheDocument();

    // 重新渲染时FPS下降
    const lowFpsProps = {
      ...defaultProps,
      fps: 35, // 从60下降到35，下降25
    };

    rerender(<PerformanceMonitor {...lowFpsProps} />);

    expect(screen.getByText(/FPS显著下降:/)).toBeInTheDocument();
  });

  test('formats render time correctly for different scales', () => {
    // 测试毫秒格式（小于1秒）
    const msProps = { ...defaultProps, renderTime: 0.5 };
    render(<PerformanceMonitor {...msProps} />);
    expect(screen.getByText('0ms')).toBeInTheDocument();

    // 测试秒格式（大于1秒）
    const secProps = { ...defaultProps, renderTime: 2.5 };
    render(<PerformanceMonitor {...secProps} />);
    expect(screen.getByText('2.5s')).toBeInTheDocument();
  });

  test('formats data points correctly for different scales', () => {
    // 小数据量
    const smallDataProps = { ...defaultProps, dataPoints: 500 };
    render(<PerformanceMonitor {...smallDataProps} />);
    expect(screen.getByText('500')).toBeInTheDocument();

    // 大数据量（千为单位）
    const largeDataProps = { ...defaultProps, dataPoints: 5000 };
    render(<PerformanceMonitor {...largeDataProps} />);
    expect(screen.getByText('5.0K')).toBeInTheDocument();
  });

  test('formats memory size correctly', () => {
    const highMemoryProps = {
      ...defaultProps,
      memoryUsage: 1024 * 1024 * 1024, // 1GB
    };

    render(<PerformanceMonitor {...highMemoryProps} showDetails={true} />);

    expect(screen.getByText('1.00GB')).toBeInTheDocument();
  });

  test('shows detailed information when showDetails is true', () => {
    render(<PerformanceMonitor {...defaultProps} showDetails={true} />);

    expect(screen.getByText('内存使用')).toBeInTheDocument();
    expect(screen.getByText('性能评分')).toBeInTheDocument();
    expect(screen.getByText('✅ 性能表现良好，一切正常')).toBeInTheDocument();
  });

  test('hides detailed information when showDetails is false', () => {
    render(<PerformanceMonitor {...defaultProps} showDetails={false} />);

    expect(screen.queryByText('内存使用')).not.toBeInTheDocument();
    expect(screen.queryByText('性能评分')).not.toBeInTheDocument();
  });

  test('shows optimization suggestions based on performance', () => {
    const poorPerformanceProps = {
      ...defaultProps,
      fps: 25,
      renderTime: 40,
      dataPoints: 15000,
    };

    render(<PerformanceMonitor {...poorPerformanceProps} showDetails={true} />);

    expect(
      screen.getByText(/建议减少数据点数量或启用数据采样/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/大数据量场景，建议启用智能采样/),
    ).toBeInTheDocument();
  });

  test('can hide and show monitor panel', () => {
    render(<PerformanceMonitor {...defaultProps} />);

    // 初始状态应该显示面板
    expect(screen.getByText('📊 性能监控')).toBeInTheDocument();

    // 点击关闭按钮
    const closeButton = screen.getByTitle('隐藏监控面板');
    fireEvent.click(closeButton);

    // 面板应该隐藏，显示浮动的显示按钮
    expect(screen.queryByText('📊 性能监控')).not.toBeInTheDocument();

    // 点击显示按钮
    const showButton = screen.getByTitle('显示性能监控');
    fireEvent.click(showButton);

    // 面板应该重新显示
    expect(screen.getByText('📊 性能监控')).toBeInTheDocument();
  });

  test('applies custom className correctly', () => {
    const customClass = 'custom-monitor-class';
    render(<PerformanceMonitor {...defaultProps} className={customClass} />);

    const container = document.querySelector('.performance-monitor');
    expect(container).toHaveClass(customClass);
  });

  test('handles zero memory usage gracefully', () => {
    const zeroMemoryProps = {
      ...defaultProps,
      memoryUsage: 0,
    };

    render(<PerformanceMonitor {...zeroMemoryProps} showDetails={true} />);

    expect(screen.getByText('0B')).toBeInTheDocument();
  });

  test('displays correct performance level text', () => {
    // 优秀性能
    const excellentProps = { ...defaultProps, fps: 60 };
    const { rerender } = render(
      <PerformanceMonitor {...excellentProps} showDetails={true} />,
    );
    expect(screen.getByText('优秀')).toBeInTheDocument();

    // 良好性能
    rerender(
      <PerformanceMonitor {...excellentProps} fps={40} showDetails={true} />,
    );
    expect(screen.getByText('良好')).toBeInTheDocument();

    // 一般性能
    rerender(
      <PerformanceMonitor {...excellentProps} fps={20} showDetails={true} />,
    );
    expect(screen.getByText('一般')).toBeInTheDocument();

    // 需要优化
    rerender(
      <PerformanceMonitor {...excellentProps} fps={8} showDetails={true} />,
    );
    expect(screen.getByText('需优化')).toBeInTheDocument();
  });

  test('handles multiple alerts correctly', () => {
    const multipleIssueProps = {
      ...defaultProps,
      fps: 8,
      renderTime: 125,
      memoryUsage: 250 * 1024 * 1024,
      dataPoints: 60000,
    };

    render(<PerformanceMonitor {...multipleIssueProps} />);

    // 应该显示多个警报
    expect(screen.getByText(/严重性能问题:/)).toBeInTheDocument();
    expect(screen.getByText(/渲染时间过长:/)).toBeInTheDocument();
    expect(screen.getByText(/内存使用过高:/)).toBeInTheDocument();
    expect(screen.getByText(/数据量过大:/)).toBeInTheDocument();
  });
});
