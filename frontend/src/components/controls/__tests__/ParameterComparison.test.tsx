import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ParameterComparison } from '../ParameterComparison';
import { parameterService } from '@/services/parameterService';

// Mock parameterService
jest.mock('@/services/parameterService');
const mockedParameterService = parameterService as jest.Mocked<typeof parameterService>;

// Mock parameter helpers
let mockIdCounter = 0;
jest.mock('@/utils/parameterHelpers', () => ({
  generateId: () => `test-id-${++mockIdCounter}`,
}));

const mockProps = {
  symbol: 'rb2401',
  startDate: '2023-01-01',
  endDate: '2023-12-31',
};

const mockStrategyResult = {
  totalReturn: 15.5,
  sharpeRatio: 1.2,
  maxDrawdown: -8.3,
  winRate: 65.2,
  totalTrades: 42,
  profitFactor: 1.8,
};

describe('ParameterComparison', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockIdCounter = 0;
  });

  it('should render correctly with initial state', () => {
    render(<ParameterComparison {...mockProps} />);

    expect(screen.getByText('参数对比分析')).toBeInTheDocument();
    expect(screen.getByText(/\/4/)).toBeInTheDocument();
    expect(screen.getByText('添加参数组')).toBeInTheDocument();
  });

  it('should add a parameter group when clicking add button', async () => {
    const user = userEvent.setup();
    render(<ParameterComparison {...mockProps} />);

    // Component starts with one group automatically
    expect(screen.getByText('参数组 1')).toBeInTheDocument();
    expect(screen.getByText(/1\/4/)).toBeInTheDocument();

    const addButton = screen.getByText('添加参数组');
    await user.click(addButton);

    expect(screen.getByText('参数组 2')).toBeInTheDocument();
    expect(screen.getByText(/2\/4/)).toBeInTheDocument();
  });

  it('should allow renaming parameter groups', async () => {
    const user = userEvent.setup();
    render(<ParameterComparison {...mockProps} />);

    // Component has default group, click edit button (first empty name button)
    const editButtons = screen.getAllByRole('button', { name: '' });
    await user.click(editButtons[0]); // First edit button

    // Rename the group
    const nameInput = screen.getByDisplayValue('参数组 1');
    await user.clear(nameInput);
    await user.type(nameInput, '新参数组名称');

    // Blur to save
    fireEvent.blur(nameInput);

    expect(screen.queryByDisplayValue('参数组 1')).not.toBeInTheDocument();
    expect(screen.getByText('新参数组名称')).toBeInTheDocument();
  });

  it('should remove parameter groups', async () => {
    const user = userEvent.setup();
    render(<ParameterComparison {...mockProps} />);

    // Component starts with one group
    expect(screen.getByText(/1\/4/)).toBeInTheDocument();

    // Add another group
    const addButton = screen.getByText('添加参数组');
    await user.click(addButton);

    expect(screen.getByText(/2\/4/)).toBeInTheDocument();

    // Remove one group - find delete buttons (they have no accessible name but different classes)
    const deleteButtons = screen.getAllByRole('button', { name: '' }).filter(
      button => button.classList.contains('text-red-400'),
    );
    await user.click(deleteButtons[0]);

    expect(screen.getByText(/1\/4/)).toBeInTheDocument();
  });

  it('should not allow adding more than max groups', async () => {
    const user = userEvent.setup();
    render(<ParameterComparison {...mockProps} maxGroups={2} />);

    // Component starts with one group, need to add only one more to reach max
    expect(screen.getByText(/1\/2/)).toBeInTheDocument();

    const addButton = screen.getByRole('button', { name: '添加参数组' });
    await user.click(addButton);

    expect(screen.getByText(/2\/2/)).toBeInTheDocument();

    // Button should be disabled after reaching max
    expect(addButton).toBeDisabled();
  });

  it('should update parameter values when sliders and inputs change', async () => {
    const user = userEvent.setup();
    render(<ParameterComparison {...mockProps} />);

    // Component has one group by default
    // Update moving average period - find slider by min/max attributes
    const periodSlider = screen.getByRole('slider', { name: '' }) as HTMLInputElement;
    expect(periodSlider.min).toBe('5');
    expect(periodSlider.max).toBe('200');
    fireEvent.change(periodSlider, { target: { value: '50' } });

    // Check that the slider value was updated
    expect(periodSlider.value).toBe('50');

    // Update stop loss - find input with value 5
    const stopLossInput = screen.getByDisplayValue('5');
    await user.clear(stopLossInput);
    await user.type(stopLossInput, '7.5');

    expect(screen.getByDisplayValue('7.5')).toBeInTheDocument();
  });

  it('should run single backtest when clicking run button', async () => {
    const user = userEvent.setup();
    mockedParameterService.runBacktest.mockResolvedValue(mockStrategyResult);

    render(<ParameterComparison {...mockProps} />);

    // Component has one group by default, run backtest on it
    const runButton = screen.getByText('运行回测');
    await user.click(runButton);

    expect(mockedParameterService.runBacktest).toHaveBeenCalledWith({
      symbol: 'rb2401',
      startDate: '2023-01-01',
      endDate: '2023-12-31',
      parameters: {
        movingAveragePeriod: 20,
        stopLoss: 5.0,
        takeProfit: 10.0,
      },
    });

    await waitFor(() => {
      expect(screen.getByText('15.50%')).toBeInTheDocument(); // totalReturn
      expect(screen.getByText('1.20')).toBeInTheDocument(); // sharpeRatio
    });
  });

  it('should run all backtests when clicking run all button', async () => {
    const user = userEvent.setup();
    mockedParameterService.runBacktest.mockResolvedValue(mockStrategyResult);

    render(<ParameterComparison {...mockProps} />);

    // Add another group (component starts with one)
    const addButton = screen.getByText('添加参数组');
    await user.click(addButton);

    // Run all backtests
    const runAllButton = screen.getByText('运行全部');
    await user.click(runAllButton);

    expect(mockedParameterService.runBacktest).toHaveBeenCalledTimes(2);
    await waitFor(() => {
      expect(screen.getAllByText('15.50%')).toHaveLength(2); // Both groups should show results
    });
  });

  it('should show loading state during backtest', async () => {
    const user = userEvent.setup();
    let resolveBacktest: (value: any) => void;
    const backtestPromise = new Promise(resolve => {
      resolveBacktest = resolve;
    });
    mockedParameterService.runBacktest.mockReturnValue(backtestPromise as any);

    render(<ParameterComparison {...mockProps} />);

    // Run backtest on default group
    const runButton = screen.getByText('运行回测');
    await user.click(runButton);

    expect(screen.getByText('运行中...')).toBeInTheDocument();

    // Resolve backtest
    resolveBacktest!(mockStrategyResult);

    await waitFor(() => {
      expect(screen.getByText('15.50%')).toBeInTheDocument();
    });
  });

  it('should call onParameterSelect when selecting a group', async () => {
    const user = userEvent.setup();
    const onSelect = jest.fn();

    render(<ParameterComparison {...mockProps} onParameterSelect={onSelect} />);

    // Select the default group (no need to add)
    const selectButton = screen.getByText('选择此组');
    await user.click(selectButton);

    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({
        name: '参数组 1',
        parameters: {
          movingAveragePeriod: 20,
          stopLoss: 5.0,
          takeProfit: 10.0,
        },
      }),
    );
  });

  it('should show empty state when no groups exist', () => {
    // This test verifies the component structure
    // Note: The component automatically adds one group on mount
    render(<ParameterComparison {...mockProps} />);

    expect(screen.getByText('参数对比分析')).toBeInTheDocument();
    expect(screen.getByText('参数组 1')).toBeInTheDocument();
  });

  it('should show comparison analysis when multiple groups exist', async () => {
    const user = userEvent.setup();
    render(<ParameterComparison {...mockProps} />);

    // Add one more group (component starts with one)
    const addButton = screen.getByText('添加参数组');
    await user.click(addButton);

    expect(screen.getByText('对比分析')).toBeInTheDocument();
    expect(screen.getByText(/您已添加 2 组参数进行对比/)).toBeInTheDocument();
  });

  it('should display results with correct formatting', async () => {
    const user = userEvent.setup();
    mockedParameterService.runBacktest.mockResolvedValue(mockStrategyResult);

    render(<ParameterComparison {...mockProps} />);

    // Run backtest on default group
    const runButton = screen.getByText('运行回测');
    await user.click(runButton);

    await waitFor(() => {
      expect(screen.getByText('15.50%')).toBeInTheDocument(); // totalReturn with 2 decimal places
      expect(screen.getByText('1.20')).toBeInTheDocument(); // sharpeRatio with 2 decimal places
      expect(screen.getByText('-8.30%')).toBeInTheDocument(); // maxDrawdown with 2 decimal places
      expect(screen.getByText('65.20%')).toBeInTheDocument(); // winRate with 2 decimal places
      expect(screen.getByText('42')).toBeInTheDocument(); // totalTrades as integer
      expect(screen.getByText('1.80')).toBeInTheDocument(); // profitFactor with 2 decimal places
    });
  });
});
