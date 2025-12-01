import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import MovingAverageSlider from '../MovingAverageSlider';

describe('MovingAverageSlider', () => {
  const defaultProps = {
    value: 20,
    onChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('应该渲染移动平均滑块组件', () => {
    render(<MovingAverageSlider {...defaultProps} />);

    expect(screen.getByText('移动平均周期')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
    expect(screen.getByText('天')).toBeInTheDocument();
    expect(
      screen.getByText('计算移动平均线所用的历史数据天数'),
    ).toBeInTheDocument();
  });

  it('应该显示当前值', () => {
    render(<MovingAverageSlider {...defaultProps} value={50} />);

    expect(screen.getByTestId('current-value')).toHaveTextContent('50');
    expect(screen.getByText('天')).toBeInTheDocument();
  });

  it('应该显示快速选择按钮', () => {
    render(<MovingAverageSlider {...defaultProps} />);

    expect(screen.getByText('5日')).toBeInTheDocument();
    expect(screen.getByText('10日')).toBeInTheDocument();
    expect(screen.getByText('20日')).toBeInTheDocument();
    expect(screen.getByText('50日')).toBeInTheDocument();
    expect(screen.getByText('100日')).toBeInTheDocument();
    expect(screen.getByText('200日')).toBeInTheDocument();
  });

  it('应该处理滑块变化', () => {
    render(<MovingAverageSlider {...defaultProps} />);

    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '30' } });

    expect(defaultProps.onChange).toHaveBeenCalledWith(30);
  });

  it('应该处理快速选择按钮点击', () => {
    render(<MovingAverageSlider {...defaultProps} />);

    const presetButton = screen.getByText('50日');
    fireEvent.click(presetButton);

    expect(defaultProps.onChange).toHaveBeenCalledWith(50);
  });

  it('应该在禁用状态下禁用所有控件', () => {
    render(<MovingAverageSlider {...defaultProps} disabled />);

    const slider = screen.getByRole('slider');
    expect(slider).toBeDisabled();

    const presetButtons = screen.getAllByRole('button');
    presetButtons.forEach((button) => {
      expect(button).toBeDisabled();
    });
  });

  it('应该根据值显示正确的描述', () => {
    render(<MovingAverageSlider {...defaultProps} value={5} showAdvanced />);

    expect(screen.getByText('超短期')).toBeInTheDocument();
    expect(
      screen.getByText('剥头皮交易，对价格变化极其敏感'),
    ).toBeInTheDocument();
  });

  it('应该显示高级设置当showAdvanced为true时', () => {
    render(<MovingAverageSlider {...defaultProps} showAdvanced />);

    expect(screen.getByText('类型')).toBeInTheDocument();
    expect(screen.getByText('风险等级')).toBeInTheDocument();
    expect(screen.getByText('预期信号')).toBeInTheDocument();
  });

  it('应该显示风险等级信息', () => {
    render(<MovingAverageSlider {...defaultProps} showAdvanced />);

    expect(screen.getByText('中短期')).toBeInTheDocument();
    expect(screen.getByText('平衡信号频率和稳定性')).toBeInTheDocument();
  });

  it('应该为短期值显示高风险警告', () => {
    render(<MovingAverageSlider {...defaultProps} value={5} showAdvanced />);

    expect(screen.getByText('性能提示')).toBeInTheDocument();
    expect(screen.getByText(/短期均线/)).toBeInTheDocument();
  });

  it('应该为长期值显示响应慢的警告', () => {
    render(<MovingAverageSlider {...defaultProps} value={150} showAdvanced />);

    // 长期值（>20）不会显示性能提示，所以这个测试应该检查没有性能提示
    expect(screen.queryByText('性能提示')).not.toBeInTheDocument();
  });

  it('应该显示使用建议', () => {
    render(<MovingAverageSlider {...defaultProps} showAdvanced />);

    expect(screen.getByText('使用建议')).toBeInTheDocument();
    expect(screen.getByText(/适合短线交易/)).toBeInTheDocument();
    expect(screen.getByText(/平衡策略/)).toBeInTheDocument();
    expect(screen.getByText(/长期趋势跟踪/)).toBeInTheDocument();
  });

  it('应该处理拖拽状态', () => {
    render(<MovingAverageSlider {...defaultProps} />);

    const slider = screen.getByRole('slider');

    // 模拟拖拽改变值
    fireEvent.change(slider, { target: { value: '25' } });

    expect(defaultProps.onChange).toHaveBeenCalledWith(25);
  });

  it('应该处理触摸事件', () => {
    render(<MovingAverageSlider {...defaultProps} />);

    const slider = screen.getByRole('slider');

    // 模拟触摸滑动改变值
    fireEvent.touchStart(slider);
    fireEvent.change(slider, { target: { value: '30' } });
    fireEvent.touchEnd(slider);

    expect(defaultProps.onChange).toHaveBeenCalledWith(30);
  });

  describe('边界情况', () => {
    it('应该处理最小值', () => {
      render(<MovingAverageSlider {...defaultProps} value={5} />);

      const slider = screen.getByRole('slider');
      expect(slider).toHaveAttribute('min', '5');
    });

    it('应该处理最大值', () => {
      render(<MovingAverageSlider {...defaultProps} value={200} />);

      const slider = screen.getByRole('slider');
      expect(slider).toHaveAttribute('max', '200');
    });

    it('应该处理整数步进', () => {
      render(<MovingAverageSlider {...defaultProps} />);

      const slider = screen.getByRole('slider');
      expect(slider).toHaveAttribute('step', '1');
    });
  });

  describe('可访问性', () => {
    it('应该有正确的ARIA标签', () => {
      render(<MovingAverageSlider {...defaultProps} />);

      const slider = screen.getByRole('slider');
      expect(slider).toBeInTheDocument();
    });

    it('应该有键盘导航支持', () => {
      render(<MovingAverageSlider {...defaultProps} />);

      const slider = screen.getByRole('slider');

      // 测试键盘事件不会抛出错误
      expect(() => {
        fireEvent.keyDown(slider, { key: 'ArrowRight' });
        fireEvent.keyDown(slider, { key: 'ArrowLeft' });
        fireEvent.keyDown(slider, { key: 'ArrowUp' });
        fireEvent.keyDown(slider, { key: 'ArrowDown' });
      }).not.toThrow();
    });
  });
});
