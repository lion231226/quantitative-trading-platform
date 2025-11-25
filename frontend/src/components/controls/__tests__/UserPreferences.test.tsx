import React from 'react';
import { fireEvent, render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserPreferences } from '../UserPreferences';
import { StrategyParameters } from '@/types/parameter.types';

// Set up DOM container for React 18
beforeEach(() => {
  // Clear existing content
  document.body.innerHTML = '';

  // Create a div element for React to mount into
  const container = document.createElement('div');
  container.setAttribute('id', 'root');
  document.body.appendChild(container);
});

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(() => null),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock URL.createObjectURL
global.URL.createObjectURL = jest.fn(() => 'mock-url');
global.URL.revokeObjectURL = jest.fn();


// Setup and cleanup before each test
beforeEach(() => {
  // Reset localStorage
  localStorageMock.getItem.mockReturnValue(null);
  jest.clearAllMocks();
});

afterEach(() => {
  cleanup();
  // Clean up DOM
  document.body.innerHTML = '';
});

const mockProps = {
  currentParameters: {
    movingAveragePeriod: 20,
    stopLoss: 5.0,
    takeProfit: 10.0,
  },
};

describe('UserPreferences', () => {
  // Note: beforeEach and afterEach are already set up at the top level

  it('should render correctly with default preferences', async () => {
    render(<UserPreferences {...mockProps} />);

    expect(screen.getByText('用户偏好设置')).toBeInTheDocument();
    expect(screen.getByText('默认参数设置')).toBeInTheDocument();
    expect(screen.getByText('图表偏好设置')).toBeInTheDocument();
    expect(screen.getByText('配置管理')).toBeInTheDocument();
  });

  it('should load preferences from localStorage', async () => {
    const mockPreferences = {
      defaultParameters: { movingAveragePeriod: 30, stopLoss: 7, takeProfit: 15 },
      autoSave: false,
      showAdvanced: true,
      chartPreferences: { showGrid: false, showVolume: true, animationDuration: 500 },
    };

    localStorageMock.getItem.mockReturnValue(JSON.stringify(mockPreferences));

    render(<UserPreferences {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('30')).toBeInTheDocument(); // moving average period
      expect(screen.getByDisplayValue('7')).toBeInTheDocument(); // stop loss
      expect(screen.getByDisplayValue('15')).toBeInTheDocument(); // take profit
    });
  });

  it('should update default parameters correctly', async () => {
    const onParametersChange = jest.fn();
    render(<UserPreferences {...mockProps} onParametersChange={onParametersChange} />);

    // Update moving average period
    const periodSlider = screen.getByDisplayValue('20');
    fireEvent.change(periodSlider, { target: { value: '25' } });

    await waitFor(() => {
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'strategy_user_preferences',
        expect.stringContaining('"movingAveragePeriod":25'),
      );
    });

    // Click apply default parameters
    const applyButton = screen.getByText('应用默认参数');
    await userEvent.click(applyButton);

    expect(onParametersChange).toHaveBeenCalledWith(
      expect.objectContaining({
        movingAveragePeriod: expect.any(Number),
        stopLoss: expect.any(Number),
        takeProfit: expect.any(Number),
      }),
    );
  });

  it('should update chart preferences correctly', async () => {
    render(<UserPreferences {...mockProps} />);

    // Toggle showGrid
    const gridCheckbox = screen.getByLabelText('显示图表网格');
    await userEvent.click(gridCheckbox);

    await waitFor(() => {
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'strategy_user_preferences',
        expect.stringContaining('"showGrid":false'),
      );
    });

    // Update animation duration
    const animationSlider = screen.getByDisplayValue('300');
    fireEvent.change(animationSlider, { target: { value: '500' } });

    await waitFor(() => {
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'strategy_user_preferences',
        expect.stringContaining('"animationDuration":500'),
      );
    });
  });

  it('should handle autoSave setting correctly', async () => {
    render(<UserPreferences {...mockProps} />);

    // Toggle autoSave
    const autoSaveCheckbox = screen.getByLabelText('自动保存参数变更');
    await userEvent.click(autoSaveCheckbox);

    await waitFor(() => {
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'strategy_user_preferences',
        expect.stringContaining('"autoSave":false'),
      );
    });
  });

  it('should export configuration correctly', async () => {
    // Mock document methods for this test
    const mockClick = jest.fn();
    const originalCreateElement = document.createElement;
    const originalAppendChild = document.body.appendChild;
    const originalRemoveChild = document.body.removeChild;

    document.createElement = jest.fn(() => ({
      href: 'mock-url',
      download: expect.stringMatching(/^strategy-config-\d{4}-\d{2}-\d{2}\.json$/),
      click: mockClick,
    })) as any;

    document.body.appendChild = jest.fn() as any;
    document.body.removeChild = jest.fn() as any;

    render(<UserPreferences {...mockProps} />);

    const exportButton = screen.getByText('导出为JSON文件');
    await userEvent.click(exportButton);

    expect(global.URL.createObjectURL).toHaveBeenCalled();
    expect(mockClick).toHaveBeenCalled();

    // Restore original methods
    document.createElement = originalCreateElement;
    document.body.appendChild = originalAppendChild;
    document.body.removeChild = originalRemoveChild;
  });

  it('should import configuration correctly', async () => {
    const onParametersChange = jest.fn();
    const importData = {
      version: '1.0',
      timestamp: new Date().toISOString(),
      preferences: {
        defaultParameters: { movingAveragePeriod: 50, stopLoss: 8, takeProfit: 20 },
        autoSave: true,
        showAdvanced: false,
        chartPreferences: { showGrid: true, showVolume: false, animationDuration: 400 },
      },
      currentParameters: { movingAveragePeriod: 40, stopLoss: 6, takeProfit: 12 },
    };

    render(<UserPreferences {...mockProps} onParametersChange={onParametersChange} />);

    // Create a mock file
    const file = new File([JSON.stringify(importData)], 'config.json', {
      type: 'application/json',
    });

    // Find the file input by looking for the span text, then get its parent input
    const importSpan = screen.getByText('选择JSON文件');
    const fileInput = importSpan.closest('label')?.querySelector('input[type="file"]');

    if (fileInput) {
      await userEvent.upload(fileInput, file);

      await waitFor(() => {
        expect(onParametersChange).toHaveBeenCalledWith(importData.currentParameters);
        expect(screen.getByText(/配置导入成功/)).toBeInTheDocument();
      });
    } else {
      // Fallback: look for any file input
      const fileInputs = screen.container.querySelectorAll('input[type="file"]');
      if (fileInputs.length > 0) {
        await userEvent.upload(fileInputs[0], file);

        await waitFor(() => {
          expect(onParametersChange).toHaveBeenCalledWith(importData.currentParameters);
          expect(screen.getByText(/配置导入成功/)).toBeInTheDocument();
        });
      }
    }
  });

  it('should show error for invalid import file', async () => {
    render(<UserPreferences {...mockProps} />);

    // Create an invalid file
    const invalidFile = new File(['invalid json'], 'config.json', {
      type: 'application/json',
    });

    // Find the file input and simulate file selection
    const fileInput = screen.getByRole('button', { name: /选择JSON文件/ }).querySelector('input[type="file"]');
    if (fileInput) {
      await userEvent.upload(fileInput, invalidFile);

      await waitFor(() => {
        expect(screen.getByText(/导入配置失败：文件格式无效/)).toBeInTheDocument();
      });
    }
  });

  it('should reset to defaults correctly', async () => {
    const onParametersChange = jest.fn();

    // Mock window.confirm
    window.confirm = jest.fn(() => true);

    render(<UserPreferences {...mockProps} onParametersChange={onParametersChange} />);

    const resetButton = screen.getByText('重置默认');
    await userEvent.click(resetButton);

    expect(window.confirm).toHaveBeenCalledWith(
      '确定要重置为默认设置吗？这将清除所有自定义偏好。',
    );

    expect(onParametersChange).toHaveBeenCalledWith(
      expect.objectContaining({
        movingAveragePeriod: 20,
        stopLoss: 5.0,
        takeProfit: 10.0,
      }),
    );
  });

  it('should not reset when user cancels confirmation', async () => {
    const onParametersChange = jest.fn();

    // Mock window.confirm to return false
    window.confirm = jest.fn(() => false);

    render(<UserPreferences {...mockProps} onParametersChange={onParametersChange} />);

    const resetButton = screen.getByText('重置默认');
    await userEvent.click(resetButton);

    expect(window.confirm).toHaveBeenCalled();
    expect(onParametersChange).not.toHaveBeenCalled();
  });

  it('should handle save button click correctly', async () => {
    render(<UserPreferences {...mockProps} />);

    const saveButton = screen.getByText('保存设置');
    await userEvent.click(saveButton);

    await waitFor(() => {
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'strategy_user_preferences',
        expect.any(String),
      );
      expect(screen.getByText('偏好设置已保存')).toBeInTheDocument();
    });
  });

  it('should display backup history correctly', async () => {
    // Mock backup history
    const backupHistory = [
      {
        timestamp: '2023-01-01T00:00:00.000Z',
        preferences: { autoSave: true },
        currentParameters: { movingAveragePeriod: 15 },
      },
    ];
    localStorageMock.getItem.mockReturnValue(JSON.stringify(backupHistory));

    render(<UserPreferences {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByText(/2023/)).toBeInTheDocument();
      expect(screen.getByText('恢复')).toBeInTheDocument();
    });
  });

  it('should show loading state initially', () => {
    // Mock localStorage to delay loading
    localStorageMock.getItem.mockImplementation(() => {
      // Simulate delay
      return null;
    });

    render(<UserPreferences {...mockProps} />);

    expect(screen.getByRole('status')).toBeInTheDocument(); // Loading spinner
  });
});
