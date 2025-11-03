import { fireEvent, render, screen } from '@testing-library/react';
import { DateRangePicker } from '../DateRangePicker';

// Mock formatDate utility
jest.mock('@/lib/utils', () => ({
  ...jest.requireActual('@/lib/utils'),
  formatDate: (date: string) => {
    const d = new Date(date);
    return d.toLocaleDateString('zh-CN');
  },
}));

describe('DateRangePicker Component', () => {
  const mockOnDateRangeChange = jest.fn();

  beforeEach(() => {
    mockOnDateRangeChange.mockClear();
  });

  it('renders title and description', () => {
    render(<DateRangePicker onDateRangeChange={mockOnDateRangeChange} />);

    expect(screen.getByText('日期范围选择')).toBeInTheDocument();
    expect(screen.getByText('选择数据分析的时间范围')).toBeInTheDocument();
  });

  it('renders quick range buttons', () => {
    render(<DateRangePicker onDateRangeChange={mockOnDateRangeChange} />);

    expect(screen.getByText('最近7天')).toBeInTheDocument();
    expect(screen.getByText('最近30天')).toBeInTheDocument();
    expect(screen.getByText('最近90天')).toBeInTheDocument();
    expect(screen.getByText('最近180天')).toBeInTheDocument();
    expect(screen.getByText('最近一年')).toBeInTheDocument();
  });

  it('renders date inputs', () => {
    render(<DateRangePicker onDateRangeChange={mockOnDateRangeChange} />);

    // Look for date input elements by type
    const dateInputs = document.querySelectorAll('input[type="date"]');
    expect(dateInputs).toHaveLength(2);
  });

  it('calls onDateRangeChange when quick range is selected', () => {
    render(<DateRangePicker onDateRangeChange={mockOnDateRangeChange} />);

    const quickRangeButton = screen.getByText('最近30天');
    fireEvent.click(quickRangeButton);

    expect(mockOnDateRangeChange).toHaveBeenCalledTimes(1);

    const [startDate, endDate] = mockOnDateRangeChange.mock.calls[0];
    expect(startDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(endDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it('displays current selection when dates are provided', () => {
    render(
      <DateRangePicker
        onDateRangeChange={mockOnDateRangeChange}
        startDate="2024-01-01"
        endDate="2024-01-31"
      />
    );

    expect(screen.getByText(/已选择：/)).toBeInTheDocument();
    expect(screen.getByText(/2024\/1\/1/)).toBeInTheDocument();
    expect(screen.getByText(/2024\/1\/31/)).toBeInTheDocument();
  });

  it('initializes with provided dates', () => {
    render(
      <DateRangePicker
        onDateRangeChange={mockOnDateRangeChange}
        startDate="2024-01-01"
        endDate="2024-01-31"
      />
    );

    // Check that inputs have the correct values
    const dateInputs = document.querySelectorAll('input[type="date"]') as NodeListOf<HTMLInputElement>;

    const startInput = Array.from(dateInputs).find(input => input.value === '2024-01-01');
    const endInput = Array.from(dateInputs).find(input => input.value === '2024-01-31');

    expect(startInput).toBeTruthy();
    expect(endInput).toBeTruthy();
  });
});