import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { VarietySelector } from '../VarietySelector';
import * as api from '@/lib/api';

// Mock API
jest.mock('@/lib/api');
const mockMarketDataAPI = api.marketDataAPI as jest.Mocked<
  typeof api.marketDataAPI
>;

// Mock symbols data
const mockSymbols = [
  { symbol: 'RB2410', name: '螺纹钢2410', sector: '金属', exchange: 'SHFE' },
  { symbol: 'I2410', name: '铁矿石2410', sector: '金属', exchange: 'DCE' },
  { symbol: 'CU2410', name: '沪铜2410', sector: '金属', exchange: 'SHFE' },
  { symbol: 'SC2410', name: '原油2410', sector: '能源', exchange: 'INE' },
  { symbol: 'TA2410', name: 'PTA2410', sector: '化工', exchange: 'ZCE' },
];

describe('VarietySelector', () => {
  const mockOnVarietiesSelect = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockMarketDataAPI.getSymbols.mockResolvedValue(mockSymbols);
  });

  it('renders correctly with loading state', () => {
    render(
      <VarietySelector
        onVarietiesSelect={mockOnVarietiesSelect}
        selectedVarieties={[]}
      />,
    );

    expect(screen.getByText('多品种选择')).toBeInTheDocument();
    expect(
      screen.getByText('选择要对比分析的期货品种（最多10个）'),
    ).toBeInTheDocument();
    expect(screen.getByText('加载期货品种...')).toBeInTheDocument();
  });

  it('displays symbols after loading', async () => {
    render(
      <VarietySelector
        onVarietiesSelect={mockOnVarietiesSelect}
        selectedVarieties={[]}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('螺纹钢2410')).toBeInTheDocument();
      expect(screen.getByText('铁矿石2410')).toBeInTheDocument();
    });

    expect(screen.queryByText('加载期货品种...')).not.toBeInTheDocument();
  });

  it('handles variety selection correctly', async () => {
    render(
      <VarietySelector
        onVarietiesSelect={mockOnVarietiesSelect}
        selectedVarieties={[]}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('螺纹钢2410')).toBeInTheDocument();
    });

    // Click on a variety
    const firstVariety = screen.getByText('螺纹钢2410');
    fireEvent.click(firstVariety);

    expect(mockOnVarietiesSelect).toHaveBeenCalledWith(['RB2410']);

    // Click again to deselect
    fireEvent.click(firstVariety);
    expect(mockOnVarietiesSelect).toHaveBeenCalledWith([]);
  });

  it('handles sector filtering', async () => {
    render(
      <VarietySelector
        onVarietiesSelect={mockOnVarietiesSelect}
        selectedVarieties={[]}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('螺纹钢2410')).toBeInTheDocument();
    });

    // Click on "金属" sector filter
    const metalSector = screen.getByText('金属');
    fireEvent.click(metalSector);

    // Should only show metal varieties
    await waitFor(() => {
      expect(screen.getByText('螺纹钢2410')).toBeInTheDocument();
      expect(screen.getByText('铁矿石2410')).toBeInTheDocument();
      expect(screen.getByText('沪铜2410')).toBeInTheDocument();
      expect(screen.queryByText('原油2410')).not.toBeInTheDocument();
      expect(screen.queryByText('PTA2410')).not.toBeInTheDocument();
    });
  });

  it('handles search functionality', async () => {
    render(
      <VarietySelector
        onVarietiesSelect={mockOnVarietiesSelect}
        selectedVarieties={[]}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('螺纹钢2410')).toBeInTheDocument();
    });

    // Type in search box
    const searchInput =
      screen.getByPlaceholderText('搜索期货品种代码或名称...');
    fireEvent.change(searchInput, { target: { value: '螺纹' } });

    // Should only show matching results
    await waitFor(() => {
      expect(screen.getByText('螺纹钢2410')).toBeInTheDocument();
      expect(screen.queryByText('铁矿石2410')).not.toBeInTheDocument();
    });
  });

  it('handles quick select functionality', async () => {
    render(
      <VarietySelector
        onVarietiesSelect={mockOnVarietiesSelect}
        selectedVarieties={[]}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('螺纹钢2410')).toBeInTheDocument();
    });

    // Click quick select for "金属" sector
    const metalQuickSelect = screen.getByTitle('快速选择金属品种');
    fireEvent.click(metalQuickSelect);

    expect(mockOnVarietiesSelect).toHaveBeenCalledWith([
      'RB2410',
      'I2410',
      'CU2410',
    ]);
  });

  it('displays selected varieties correctly', async () => {
    render(
      <VarietySelector
        onVarietiesSelect={mockOnVarietiesSelect}
        selectedVarieties={['RB2410', 'I2410']}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('已选择的品种：')).toBeInTheDocument();
      expect(screen.getByText('RB2410')).toBeInTheDocument();
      expect(screen.getByText('I2410')).toBeInTheDocument();
    });

    // Click on selected variety to remove it
    const selectedBadge = screen.getByText('RB2410').closest('.cursor-pointer');
    if (selectedBadge) {
      fireEvent.click(selectedBadge);
      expect(mockOnVarietiesSelect).toHaveBeenCalledWith(['I2410']);
    }
  });

  it('handles clear selection', async () => {
    render(
      <VarietySelector
        onVarietiesSelect={mockOnVarietiesSelect}
        selectedVarieties={['RB2410', 'I2410']}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('已选择的品种：')).toBeInTheDocument();
    });

    // Click clear selection button
    const clearButton = screen.getByText('清空选择');
    fireEvent.click(clearButton);

    expect(mockOnVarietiesSelect).toHaveBeenCalledWith([]);
  });

  it('enforces maximum selection limit', async () => {
    render(
      <VarietySelector
        onVarietiesSelect={mockOnVarietiesSelect}
        selectedVarieties={['RB2410', 'I2410', 'CU2410']} // Already selected 3
        maxSelection={3}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('已选择的品种：')).toBeInTheDocument();
    });

    // Try to select another variety (should be disabled)
    const additionalVariety = screen.getByText('SC2410');
    fireEvent.click(additionalVariety);

    // Should not call onVarietiesSelect as limit is reached
    expect(mockOnVarietiesSelect).not.toHaveBeenCalled();
  });

  it('displays error state correctly', async () => {
    mockMarketDataAPI.getSymbols.mockRejectedValue(new Error('网络错误'));

    render(
      <VarietySelector
        onVarietiesSelect={mockOnVarietiesSelect}
        selectedVarieties={[]}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeInTheDocument();
      expect(screen.getByText('重新加载')).toBeInTheDocument();
    });
  });

  it('handles retry on error', async () => {
    mockMarketDataAPI.getSymbols
      .mockRejectedValueOnce(new Error('网络错误'))
      .mockResolvedValueOnce(mockSymbols);

    render(
      <VarietySelector
        onVarietiesSelect={mockOnVarietiesSelect}
        selectedVarieties={[]}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeInTheDocument();
    });

    // Click retry button
    const retryButton = screen.getByText('重新加载');
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(screen.getByText('螺纹钢2410')).toBeInTheDocument();
    });

    expect(mockMarketDataAPI.getSymbols).toHaveBeenCalledTimes(2);
  });

  it('shows correct selection count', async () => {
    render(
      <VarietySelector
        onVarietiesSelect={mockOnVarietiesSelect}
        selectedVarieties={['RB2410', 'I2410']}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText(/已选择.*2.*10.*个/)).toBeInTheDocument();
    });
  });

  it('shows empty state when no results found', async () => {
    render(
      <VarietySelector
        onVarietiesSelect={mockOnVarietiesSelect}
        selectedVarieties={[]}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('螺纹钢2410')).toBeInTheDocument();
    });

    // Search for non-existent variety
    const searchInput =
      screen.getByPlaceholderText('搜索期货品种代码或名称...');
    fireEvent.change(searchInput, { target: { value: '不存在的品种' } });

    expect(screen.getByText('未找到匹配的期货品种')).toBeInTheDocument();
  });
});
