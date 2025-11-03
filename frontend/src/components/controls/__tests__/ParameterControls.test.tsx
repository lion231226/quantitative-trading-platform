import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ParameterControls } from '../ParameterControls';
import { ParameterChangeEvent, StrategyParameters } from '@/types/parameter.types';

// Mock子组件
jest.mock('../MovingAverageSlider', () => {
  return function MockMovingAverageSlider({
    value,
    onChange,
    disabled,
  }: any) {
    return (
      <div data-testid="moving-average-slider">
        <span>{value}</span>
        <button
          onClick={() => onChange(25)}
          disabled={disabled}
          data-testid="ma-slider-change"
        >
          Change MA
        </button>
      </div>
    );
  };
});

jest.mock('../PercentageInput', () => {
  return function MockPercentageInput({
    label,
    value,
    onChange,
    disabled,
    type,
  }: any) {
    return (
      <div data-testid={`percentage-input-${type}`}>
        <span>{label}: {value}</span>
        <button
          onClick={() => onChange(type === 'stopLoss' ? 6.0 : 12.0)}
          disabled={disabled}
          data-testid={`${type}-input-change`}
        >
          Change {type}
        </button>
      </div>
    );
  };
});

jest.mock('../ParameterPresets', () => {
  return function MockParameterPresets({
    parameters,
    onPresetSelect,
    disabled,
  }: any) {
    return (
      <div data-testid="parameter-presets">
        <span>Current params: MA{parameters.movingAveragePeriod} SL{parameters.stopLoss}% TP{parameters.takeProfit}%</span>
        <button
          onClick={() => onPresetSelect({
            id: 'test-preset',
            name: 'Test Preset',
            description: 'Test',
            parameters: { movingAveragePeriod: 30, stopLoss: 3, takeProfit: 9 },
          })}
          disabled={disabled}
          data-testid="apply-preset"
        >
          Apply Preset
        </button>
      </div>
    );
  };
});

describe('ParameterControls', () => {
  const defaultProps = {
    parameters: {
      movingAveragePeriod: 20,
      stopLoss: 5.0,
      takeProfit: 10.0,
    },
    onParametersChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('应该渲染参数控制组件', () => {
    render(<ParameterControls {...defaultProps} />);

    expect(screen.getByText('策略参数配置')).toBeInTheDocument();
    expect(screen.getByTestId('moving-average-slider')).toBeInTheDocument();
    expect(screen.getByTestId('percentage-input-stopLoss')).toBeInTheDocument();
    expect(screen.getByTestId('percentage-input-takeProfit')).toBeInTheDocument();
  });

  it('应该显示当前参数值', () => {
    render(<ParameterControls {...defaultProps} />);

    expect(screen.getByText('20')).toBeInTheDocument(); // MA值
    expect(screen.getByText('止损设置')).toBeInTheDocument();
    expect(screen.getByText('5.0%')).toBeInTheDocument();
    expect(screen.getByText('止盈设置')).toBeInTheDocument();
    expect(screen.getByText('10.0%')).toBeInTheDocument();
  });

  it('应该在compact模式下显示简化界面', () => {
    render(<ParameterControls {...defaultProps} compact />);

    expect(screen.getByText('策略参数')).toBeInTheDocument();
    expect(screen.getByText('周期:')).toBeInTheDocument();
    expect(screen.getByText('止损:')).toBeInTheDocument();
    expect(screen.getByText('止盈:')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
    expect(screen.getByText('5.0%')).toBeInTheDocument();
    expect(screen.getByText('10.0%')).toBeInTheDocument();
  });

  it('应该处理移动平均周期变化', async () => {
    render(<ParameterControls {...defaultProps} />);

    const changeButton = screen.getByTestId('ma-slider-change');
    fireEvent.click(changeButton);

    expect(defaultProps.onParametersChange).toHaveBeenCalledWith({
      movingAveragePeriod: 25,
      stopLoss: 5.0,
      takeProfit: 10.0,
    });
  });

  it('应该处理止损变化', async () => {
    render(<ParameterControls {...defaultProps} />);

    const changeButton = screen.getByTestId('stopLoss-input-change');
    fireEvent.click(changeButton);

    expect(defaultProps.onParametersChange).toHaveBeenCalledWith({
      movingAveragePeriod: 20,
      stopLoss: 6.0,
      takeProfit: 10.0,
    });
  });

  it('应该处理止盈变化', async () => {
    render(<ParameterControls {...defaultProps} />);

    const changeButton = screen.getByTestId('takeProfit-input-change');
    fireEvent.click(changeButton);

    expect(defaultProps.onParametersChange).toHaveBeenCalledWith({
      movingAveragePeriod: 20,
      stopLoss: 5.0,
      takeProfit: 12.0,
    });
  });

  it('应该处理参数变化事件', () => {
    const onParameterChange = jest.fn();
    render(<ParameterControls {...defaultProps} onParameterChange={onParameterChange} />);

    const changeButton = screen.getByTestId('ma-slider-change');
    fireEvent.click(changeButton);

    expect(onParameterChange).toHaveBeenCalledWith({
      parameter: 'movingAveragePeriod',
      value: 25,
      previousValue: 20,
    });
  });

  it('应该处理预设选择', () => {
    render(<ParameterControls {...defaultProps} showPresets />);

    const presetButton = screen.getByTestId('apply-preset');
    fireEvent.click(presetButton);

    expect(defaultProps.onParametersChange).toHaveBeenCalledWith({
      movingAveragePeriod: 30,
      stopLoss: 3.0,
      takeProfit: 9.0,
    });
  });

  it('应该处理重置功能', () => {
    const onReset = jest.fn();
    render(<ParameterControls {...defaultProps} onReset={onReset} />);

    const resetButton = screen.getByText('重置');
    fireEvent.click(resetButton);

    expect(defaultProps.onParametersChange).toHaveBeenCalledWith({
      movingAveragePeriod: 20,
      stopLoss: 5.0,
      takeProfit: 10.0,
    });
    expect(onReset).toHaveBeenCalled();
  });

  it('应该处理保存功能', () => {
    const onSave = jest.fn();
    render(<ParameterControls {...defaultProps} onSave={onSave} />);

    // 触发参数变化以显示保存按钮
    const changeButton = screen.getByTestId('ma-slider-change');
    fireEvent.click(changeButton);

    const saveButton = screen.getByText('保存');
    fireEvent.click(saveButton);

    expect(onSave).toHaveBeenCalledWith({
      movingAveragePeriod: 25,
      stopLoss: 5.0,
      takeProfit: 10.0,
    });
  });

  it('应该在禁用状态下禁用所有控件', () => {
    render(<ParameterControls {...defaultProps} disabled />);

    const maSlider = screen.getByTestId('ma-slider-change');
    const stopLossInput = screen.getByTestId('stopLoss-input-change');
    const takeProfitInput = screen.getByTestId('takeProfit-input-change');

    expect(maSlider).toBeDisabled();
    expect(stopLossInput).toBeDisabled();
    expect(takeProfitInput).toBeDisabled();
  });

  it('应该隐藏预设组件当showPresets为false时', () => {
    render(<ParameterControls {...defaultProps} showPresets={false} />);

    expect(screen.queryByTestId('parameter-presets')).not.toBeInTheDocument();
  });

  it('应该同步外部参数变化', () => {
    const { rerender } = render(<ParameterControls {...defaultProps} />);

    expect(screen.getByText('20')).toBeInTheDocument();

    const newParameters = {
      movingAveragePeriod: 30,
      stopLoss: 3.0,
      takeProfit: 9.0,
    };

    rerender(<ParameterControls {...defaultProps} parameters={newParameters} />);

    expect(screen.getByText('30')).toBeInTheDocument();
    expect(screen.getByText('止损设置')).toBeInTheDocument();
    expect(screen.getByText('3.0%')).toBeInTheDocument();
    expect(screen.getByText('止盈设置')).toBeInTheDocument();
    expect(screen.getByText('9.0%')).toBeInTheDocument();
  });

  it('应该处理高级设置切换', () => {
    render(<ParameterControls {...defaultProps} />);

    const advancedButton = screen.getByText('高级设置');
    fireEvent.click(advancedButton);

    expect(screen.getByText('风险评估')).toBeInTheDocument();
    expect(screen.getByText('参数配置')).toBeInTheDocument();
    expect(screen.getByText('收益风险比')).toBeInTheDocument();
  });

  it('应该显示风险等级信息', () => {
    render(<ParameterControls {...defaultProps} showAdvanced />);

    expect(screen.getByText('风险评估')).toBeInTheDocument();
    // 应该显示风险等级、评分和风险因素
  });

  it('应该计算并显示收益风险比', () => {
    render(<ParameterControls {...defaultProps} showAdvanced />);

    // 止盈/止损比例 = 10.0 / 5.0 = 2.0
    expect(screen.getByText('2.00')).toBeInTheDocument();
    expect(screen.getByText('良好')).toBeInTheDocument(); // 2:1比例是良好的
  });

  it('应该处理无止盈的情况', () => {
    const parametersWithNoTP = {
      movingAveragePeriod: 20,
      stopLoss: 5.0,
      takeProfit: 0,
    };

    render(<ParameterControls {...defaultProps} parameters={parametersWithNoTP} showAdvanced />);

    expect(screen.getByText('N/A')).toBeInTheDocument(); // 收益风险比
  });

  it('应该显示验证错误', () => {
    const invalidParameters = {
      movingAveragePeriod: 3, // 小于最小值
      stopLoss: 60, // 大于最大值
      takeProfit: 80, // 大于最大值
    };

    render(<ParameterControls {...defaultProps} parameters={invalidParameters} />);

    // 应该显示验证错误信息
    expect(screen.getByText(/参数错误/)).toBeInTheDocument();
  });

  it('应该显示参数警告', () => {
    const warningParameters = {
      movingAveragePeriod: 8, // 短期均线
      stopLoss: 15, // 止损大于止盈
      takeProfit: 5,
    };

    render(<ParameterControls {...defaultProps} parameters={warningParameters} />);

    // 应该显示参数警告信息
    expect(screen.getByText(/参数建议/)).toBeInTheDocument();
  });

  describe('边界情况', () => {
    it('应该处理空参数', () => {
      const emptyParameters = {
        movingAveragePeriod: 0,
        stopLoss: 0,
        takeProfit: 0,
      };

      render(<ParameterControls {...defaultProps} parameters={emptyParameters} />);

      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('应该处理极值参数', () => {
      const extremeParameters = {
        movingAveragePeriod: 200,
        stopLoss: 50,
        takeProfit: 50,
      };

      render(<ParameterControls {...defaultProps} parameters={extremeParameters} />);

      expect(screen.getByText('200')).toBeInTheDocument();
      expect(screen.getByText('止损设置')).toBeInTheDocument();
      expect(screen.getByText('50.0%')).toBeInTheDocument();
      expect(screen.getByText('止盈设置')).toBeInTheDocument();
      expect(screen.getByText('50.0%')).toBeInTheDocument();
    });

    it('应该处理小数精度', () => {
      const decimalParameters = {
        movingAveragePeriod: 20,
        stopLoss: 5.15,
        takeProfit: 10.25,
      };

      render(<ParameterControls {...defaultProps} parameters={decimalParameters} />);

      expect(screen.getByText('止损设置')).toBeInTheDocument();
      expect(screen.getByText('5.1%')).toBeInTheDocument(); // 应该被格式化
      expect(screen.getByText('止盈设置')).toBeInTheDocument();
      expect(screen.getByText('10.2%')).toBeInTheDocument(); // 应该被格式化
    });
  });
});
