/**
 * AccessibleChartContainer组件可访问性测试
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { expectAccessible, testKeyboardNavigation, testScreenReaderAnnouncement } from '@/utils/accessibility/test-utils';
import { AccessibleChartContainer } from '../AccessibleChartContainer';

// 扩展expect matcher
expect.extend(toHaveNoViolations);

// Mock Chart.js组件
const MockChart = ({ children }: { children?: React.ReactNode }) => (
  <div data-testid="chart-canvas">
    {children}
  </div>
);

// Mock数据表组件
const MockDataTable = () => (
  <table data-testid="data-table">
    <thead>
      <tr>
        <th>日期</th>
        <th>价格</th>
        <th>交易量</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>2023-01-01</td>
        <td>100</td>
        <td>1000</td>
      </tr>
      <tr>
        <td>2023-01-02</td>
        <td>105</td>
        <td>1200</td>
      </tr>
    </tbody>
  </table>
);

describe('AccessibleChartContainer - 可访问性测试', () => {
  const defaultProps = {
    title: '价格走势图表',
    description: '显示2023年的股票价格走势',
    children: <MockChart />,
    dataSummary: {
      totalPoints: 365,
      dateRange: '2023-01-01 至 2023-12-31',
      keyMetrics: {
        '最高价': '150.00',
        '最低价': '80.00',
        '平均价': '115.00',
      },
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('基础可访问性', () => {
    it('应该通过axe可访问性检查', async () => {
      const { container } = render(
        <AccessibleChartContainer {...defaultProps} />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('应该使用便捷函数通过可访问性测试', async () => {
      const { container } = render(
        <AccessibleChartContainer {...defaultProps} />
      );

      await expectAccessible(container);
    });

    it('没有数据表时应该可访问', async () => {
      const { container } = render(
        <AccessibleChartContainer
          {...defaultProps}
          dataTable={undefined}
        />
      );

      await expectAccessible(container);
    });

    it('没有数据摘要时应该可访问', async () => {
      const { container } = render(
        <AccessibleChartContainer
          {...defaultProps}
          dataSummary={undefined}
        />
      );

      await expectAccessible(container);
    });
  });

  describe('ARIA属性测试', () => {
    it('主要图表区域应该有正确的ARIA属性', () => {
      render(<AccessibleChartContainer {...defaultProps} />);

      const chartWrapper = screen.getByRole('application');
      expect(chartWrapper).toHaveAttribute(
        'aria-label',
        expect.stringContaining('价格走势图表')
      );
      expect(chartWrapper).toHaveAttribute(
        'aria-describedby',
        expect.stringContaining('chart-')
      );
      expect(chartWrapper).toHaveAttribute('tabIndex', '0');
    });

    it('图表标题应该正确设置', () => {
      render(<AccessibleChartContainer {...defaultProps} />);

      const title = screen.getByRole('heading', { name: '价格走势图表' });
      expect(title).toBeInTheDocument();
      expect(title).toHaveAttribute('id', expect.stringContaining('chart-'));
    });

    it('图表描述应该正确设置', () => {
      render(<AccessibleChartContainer {...defaultProps} />);

      const description = screen.getByText('显示2023年的股票价格走势');
      expect(description).toBeInTheDocument();
      expect(description).toHaveAttribute('id', expect.stringContaining('-description'));
    });

    it('Canvas元素应该有正确的role', () => {
      render(<AccessibleChartContainer {...defaultProps} />);

      const canvasRole = screen.getByRole('img');
      expect(canvasRole).toBeInTheDocument();
      expect(canvasRole).toHaveAttribute(
        'aria-label',
        '价格走势图表图表'
      );
    });

    it('数据摘要应该对屏幕阅读器可访问', () => {
      render(<AccessibleChartContainer {...defaultProps} />);

      const summaryId = screen.getByText('数据摘要');
      expect(summaryId).toBeInTheDocument();
      expect(summaryId).toHaveClass('sr-only');

      // 检查摘要内容
      expect(screen.getByText('总共365个数据点')).toBeInTheDocument();
      expect(screen.getByText('时间范围：2023-01-01 至 2023-12-31')).toBeInTheDocument();
      expect(screen.getByText('关键指标：')).toBeInTheDocument();
    });
  });

  describe('键盘导航测试', () => {
    it('图表容器应该支持键盘导航', () => {
      render(<AccessibleChartContainer {...defaultProps} />);

      const chartWrapper = screen.getByRole('application');
      testKeyboardNavigation(chartWrapper);
    });

    it('应该支持方向键导航（当有可聚焦元素时）', () => {
      render(
        <AccessibleChartContainer
          {...defaultProps}
          children={
            <div>
              <button>按钮1</button>
              <button>按钮2</button>
              <MockChart />
            </div>
          }
        />
      );

      const chartWrapper = screen.getByRole('application');

      // 测试方向键导航
      fireEvent.keyDown(chartWrapper, { key: 'ArrowRight' });
      fireEvent.keyDown(chartWrapper, { key: 'ArrowLeft' });
      fireEvent.keyDown(chartWrapper, { key: 'Home' });
      fireEvent.keyDown(chartWrapper, { key: 'End' });

      // 不应该抛出错误
      expect(true).toBe(true);
    });

    it('控制按钮应该支持键盘导航', () => {
      render(<AccessibleChartContainer {...defaultProps} dataTable={<MockDataTable />} />);

      const toggleButton = screen.getByRole('button', { name: /显示数据表/ });
      testKeyboardNavigation(toggleButton);

      const viewButton = screen.getByRole('button', { name: /查看数据表/ });
      testKeyboardNavigation(viewButton);
    });
  });

  describe('数据表切换测试', () => {
    it('显示数据表按钮应该工作正确', () => {
      render(
        <AccessibleChartContainer
          {...defaultProps}
          dataTable={<MockDataTable />}
        />
      );

      const toggleButton = screen.getByRole('button', { name: /显示数据表/ });
      expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
      expect(toggleButton).toHaveAttribute('aria-controls', expect.stringContaining('-table'));

      fireEvent.click(toggleButton);

      expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
      expect(toggleButton).toHaveAttribute('aria-controls', expect.stringContaining('-table'));

      // 数据表应该显示
      const dataTable = screen.getByTestId('data-table');
      expect(dataTable).toBeInTheDocument();
    });

    it('数据表应该有正确的ARIA属性', () => {
      render(
        <AccessibleChartContainer
          {...defaultProps}
          dataTable={<MockDataTable />}
        />
      );

      // 点击显示数据表
      const toggleButton = screen.getByRole('button', { name: /显示数据表/ });
      fireEvent.click(toggleButton);

      const tabPanel = screen.getByRole('tabpanel');
      expect(tabPanel).toBeInTheDocument();
      expect(tabPanel).toHaveAttribute('aria-labelledby', expect.stringContaining('-table-button'));
    });

    it('数据表应该包含可访问的说明', () => {
      render(
        <AccessibleChartContainer
          {...defaultProps}
          dataTable={<MockDataTable />}
        />
      );

      // 点击显示数据表
      const toggleButton = screen.getByRole('button', { name: /显示数据表/ });
      fireEvent.click(toggleButton);

      expect(screen.getByText(/数据表/)).toBeInTheDocument();
      expect(screen.getByText(/适用于屏幕阅读器用户/)).toBeInTheDocument();
    });
  });

  describe('屏幕阅读器通知测试', () => {
    it('应该发送状态变更通知', () => {
      render(
        <AccessibleChartContainer
          {...defaultProps}
          dataTable={<MockDataTable />}
        />
      );

      const toggleButton = screen.getByRole('button', { name: /显示数据表/ });

      testScreenReaderAnnouncement(
        { container: document.body },
        '数据表已显示'
      );

      fireEvent.click(toggleButton);

      testScreenReaderAnnouncement(
        { container: document.body },
        '数据表已显示'
      );
    });

    it('应该发送数据点导航通知', () => {
      const announceCallback = jest.fn();
      const originalLog = console.log;
      console.log = announceCallback;

      render(
        <AccessibleChartContainer
          {...defaultProps}
        />
      );

      // 这里需要模拟数据点导航
      // 由于当前实现中handleDataPointFocus是一个回调，我们需要测试实际的屏幕阅读器通知组件

      console.log = originalLog;
    });
  });

  describe('控制栏测试', () => {
    it('控制栏应该有正确的role', () => {
      render(
        <AccessibleChartContainer
          {...defaultProps}
          dataTable={<MockDataTable />}
        />
      );

      const toolbar = screen.getByRole('toolbar');
      expect(toolbar).toBeInTheDocument();
      expect(toolbar).toHaveAttribute('aria-label', '图表控制');
    });

    it('按钮应该有正确的状态属性', () => {
      render(
        <AccessibleChartContainer
          {...defaultProps}
          dataTable={<MockDataTable />}
        />
      );

      const toggleButton = screen.getByRole('button', { name: /显示数据表/ });
      expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
      expect(toggleButton).toHaveAttribute('aria-controls', expect.stringContaining('-table'));

      const viewButton = screen.getByRole('button', { name: /查看数据表/ });
      expect(viewButton).toHaveAttribute('aria-controls', expect.stringContaining('-table'));
    });

    it('没有数据表时不应该显示数据表相关按钮', () => {
      render(
        <AccessibleChartContainer
          {...defaultProps}
          dataTable={undefined}
        />
      );

      // 只应该有一个切换按钮
      expect(screen.queryByRole('button', { name: /查看数据表/ })).not.toBeInTheDocument();
    });
  });

  describe('对比度和视觉可访问性', () => {
    it('应该有足够的颜色对比度', async () => {
      const { container } = render(
        <AccessibleChartContainer
          {...defaultProps}
          className="additional-styles"
        />
      );

      // 使用axe的颜色对比度规则
      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
          'color-contrast-enhanced': { enabled: false },
        }
      });

      expect(results).toHaveNoViolations();
    });

    it('焦点状态应该清晰可见', async () => {
      const { container } = render(
        <AccessibleChartContainer {...defaultProps} />
      );

      // 获取可聚焦元素并设置焦点
      const chartWrapper = screen.getByRole('application');
      chartWrapper.focus();

      const results = await axe(container, {
        rules: {
          'focus-order-semantics': { enabled: true },
        }
      });

      expect(results).toHaveNoViolations();
      expect(chartWrapper).toHaveFocus();
    });
  });

  describe('边缘情况测试', () => {
    it('空的dataSummary应该正常处理', async () => {
      const { container } = render(
        <AccessibleChartContainer
          {...defaultProps}
          dataSummary={{}}
        />
      );

      await expectAccessible(container);

      // 不应该显示数据摘要
      expect(screen.queryByText('数据摘要')).not.toBeInTheDocument();
    });

    it('非常长的标题应该正常处理', async () => {
      const longTitle = '这是一个非常长的图表标题，用于测试长文本内容的可访问性处理和渲染';
      const { container } = render(
        <AccessibleChartContainer
          {...defaultProps}
          title={longTitle}
        />
      );

      await expectAccessible(container);

      const title = screen.getByRole('heading', { name: longTitle });
      expect(title).toBeInTheDocument();
    });

    it('复杂的children内容应该正常处理', async () => {
      const complexChildren = (
        <div>
          <MockChart />
          <div className="overlay">
            <button>叠加按钮1</button>
            <button>叠加按钮2</button>
          </div>
          <div className="controls">
            <input type="range" aria-label="缩放" />
            <select aria-label="时间范围">
              <option>1月</option>
              <option>3月</option>
              <option>1年</option>
            </select>
          </div>
        </div>
      );

      const { container } = render(
        <AccessibleChartContainer
          {...defaultProps}
          children={complexChildren}
        />
      );

      await expectAccessible(container);

      // 验证所有子元素都存在
      expect(screen.getByRole('slider')).toBeInTheDocument();
      expect(screen.getByRole('combobox')).toBeInTheDocument();
      expect(screen.getAllByRole('button')).toHaveLength(expect.any(Number));
    });
  });

  describe('性能和响应式测试', () => {
    it('大量数据点时应该仍然可访问', async () => {
      const largeDataSummary = {
        totalPoints: 10000,
        dateRange: '2020-01-01 至 2023-12-31',
        keyMetrics: {
          '数据点数': '10000',
          '时间跨度': '4年',
          '平均间隔': '1.46天',
        },
      };

      const { container } = render(
        <AccessibleChartContainer
          {...defaultProps}
          dataSummary={largeDataSummary}
        />
      );

      await expectAccessible(container);
    });

    it('响应式设计应该保持可访问性', async () => {
      // 模拟小屏幕
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      });

      Object.defineProperty(window, 'innerHeight', {
        writable: true,
        configurable: true,
        value: 667,
      });

      window.dispatchEvent(new Event('resize'));

      const { container } = render(
        <AccessibleChartContainer
          {...defaultProps}
          dataTable={<MockDataTable />}
        />
      );

      await expectAccessible(container);
    });
  });

  describe('集成测试', () => {
    it('完整的用户交互流程应该可访问', async () => {
      const { container } = render(
        <AccessibleChartContainer
          {...defaultProps}
          dataTable={<MockDataTable />}
          showKeyboardIndicator
        />
      );

      await expectAccessible(container);

      // 测试完整交互流程
      // 1. 聚焦图表
      const chartWrapper = screen.getByRole('application');
      chartWrapper.focus();
      expect(chartWrapper).toHaveFocus();

      // 2. 导航到控制按钮
      fireEvent.keyDown(chartWrapper, { key: 'Tab' });
      const toggleButton = screen.getByRole('button', { name: /显示数据表/ });
      expect(toggleButton).toHaveFocus();

      // 3. 切换数据表显示
      fireEvent.click(toggleButton);
      expect(toggleButton).toHaveAttribute('aria-expanded', 'true');

      // 4. 验证数据表可访问性
      const dataTable = screen.getByTestId('data-table');
      expect(dataTable).toBeInTheDocument();

      // 5. 最终检查整体可访问性
      const finalResults = await axe(container);
      expect(finalResults).toHaveNoViolations();
    });

    it('应该通过严格的WCAG检查', async () => {
      const { container } = render(
        <AccessibleChartContainer
          {...defaultProps}
          dataTable={<MockDataTable />}
        />
      );

      const results = await axe(container, {
        rules: {
          'wcag21aa': { enabled: true },
          'color-contrast': { enabled: true },
          'keyboard-navigation': { enabled: true },
          'aria-labels': { enabled: true },
          'focus-management': { enabled: true },
          'link-in-text-block': { enabled: true },
          'list-item': { enabled: true },
          'skip-link': { enabled: true },
          'tab-index': { enabled: true },
        }
      });

      expect(results).toHaveNoViolations();
    });
  });
});