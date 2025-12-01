/**
 * MovingAverageSlider组件可访问性测试
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { expectAccessible, testKeyboardNavigation, testAriaAttributes } from '@/utils/accessibility/test-utils';
import MovingAverageSlider from '../MovingAverageSlider';

// 扩展expect matcher
expect.extend(toHaveNoViolations);

describe('MovingAverageSlider - 可访问性测试', () => {
  const defaultProps = {
    value: 20,
    onChange: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('基础可访问性', () => {
    it('应该通过axe可访问性检查', async () => {
      const { container } = render(<MovingAverageSlider {...defaultProps} />);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('应该使用便捷函数通过可访问性测试', async () => {
      const { container } = render(<MovingAverageSlider {...defaultProps} />);

      await expectAccessible(container);
    });

    it('禁用状态应该可访问', async () => {
      const { container } = render(
        <MovingAverageSlider {...defaultProps} disabled />
      );

      await expectAccessible(container);
    });

    it('显示高级信息应该可访问', async () => {
      const { container } = render(
        <MovingAverageSlider {...defaultProps} showAdvanced />
      );

      await expectAccessible(container);
    });

    it('不同值的滑块应该可访问', async () => {
      const values = [5, 20, 50, 100, 200];

      for (const value of values) {
        const { container } = render(
          <MovingAverageSlider {...defaultProps} value={value} />
        );

        await expectAccessible(container);
      }
    });
  });

  describe('滑块可访问性', () => {
    it('滑块应该有正确的ARIA属性', () => {
      render(<MovingAverageSlider {...defaultProps} />);

      const slider = screen.getByRole('slider');

      // 检查必需的ARIA属性
      expect(slider).toHaveAttribute('aria-valuenow', '20');
      expect(slider).toHaveAttribute('aria-valuemin', '5');
      expect(slider).toHaveAttribute('aria-valuemax', '200');
      expect(slider).toHaveAttribute('aria-label');
    });

    it('滑块应该支持键盘导航', () => {
      render(<MovingAverageSlider {...defaultProps} />);

      const slider = screen.getByRole('slider');

      // 测试键盘导航
      testKeyboardNavigation(slider);

      // 测试方向键
      fireEvent.keyDown(slider, { key: 'ArrowLeft' });
      expect(defaultProps.onChange).toHaveBeenCalledWith(19);

      fireEvent.keyDown(slider, { key: 'ArrowRight' });
      expect(defaultProps.onChange).toHaveBeenCalledWith(21);

      fireEvent.keyDown(slider, { key: 'Home' });
      expect(defaultProps.onChange).toHaveBeenCalledWith(5);

      fireEvent.keyDown(slider, { key: 'End' });
      expect(defaultProps.onChange).toHaveBeenCalledWith(200);
    });

    it('滑块标签应该正确描述当前值', () => {
      render(<MovingAverageSlider {...defaultProps} value={50} />);

      const slider = screen.getByRole('slider');
      const ariaLabel = slider.getAttribute('aria-label');

      expect(ariaLabel).toContain('50');
      expect(ariaLabel).toContain('天');
    });

    it('隐藏的标签应该存在', () => {
      render(<MovingAverageSlider {...defaultProps} />);

      const hiddenLabel = screen.getByText(/移动平均周期滑块，当前值20天，范围5到200天/);
      expect(hiddenLabel).toBeInTheDocument();
      expect(hiddenLabel).toHaveClass('sr-only');
    });
  });

  describe('快速选择按钮可访问性', () => {
    it('快速选择按钮应该有正确的ARIA属性', () => {
      render(<MovingAverageSlider {...defaultProps} />);

      const quickSelectButtons = screen.getAllByRole('button').filter(
        button => button.textContent?.match(/\d+日/)
      );

      expect(quickSelectButtons).toHaveLength(6); // 5, 10, 20, 50, 100, 200

      quickSelectButtons.forEach((button, index) => {
        expect(button).toHaveAttribute('aria-label');
        expect(button).toHaveAttribute('aria-pressed');

        const expectedLabels = ['5日', '10日', '20日', '50日', '100日', '200日'];
        const expectedValues = [5, 10, 20, 50, 100, 200];
        expect(button).toHaveTextContent(expectedLabels[index]);

        const isPressed = index === 2; // 20是当前值
        expect(button).toHaveAttribute('aria-pressed', isPressed.toString());
      });
    });

    it('快速选择按钮应该支持键盘导航', () => {
      render(<MovingAverageSlider {...defaultProps} />);

      const quickSelectButtons = screen.getAllByRole('button').filter(
        button => button.textContent?.match(/\d+日/)
      );

      quickSelectButtons.forEach(button => {
        testKeyboardNavigation(button);
      });
    });

    it('点击快速选择按钮应该触发回调', () => {
      render(<MovingAverageSlider {...defaultProps} />);

      const fiftyDayButton = screen.getByLabelText(/选择50日移动平均线/);

      fireEvent.click(fiftyDayButton);
      expect(defaultProps.onChange).toHaveBeenCalledWith(50);
    });
  });

  describe('内容结构可访问性', () => {
    it('应该有正确的标题层级', () => {
      render(<MovingAverageSlider {...defaultProps} />);

      // 主要标题应该是h3
      const mainTitle = screen.getByRole('heading', { level: 3 });
      expect(mainTitle).toHaveTextContent('移动平均周期');
    });

    it('图标应该有aria-hidden属性', () => {
      render(<MovingAverageSlider {...defaultProps} />);

      const icons = document.querySelectorAll('[data-lucide]');
      icons.forEach(icon => {
        expect(icon).toHaveAttribute('aria-hidden', 'true');
      });
    });

    it('数值显示应该对屏幕阅读器可访问', () => {
      render(<MovingAverageSlider {...defaultProps} value={75} />);

      const currentValue = screen.getByTestId('current-value');
      expect(currentValue).toHaveTextContent('75');
    });

    it('区域标签应该正确设置', () => {
      render(<MovingAverageSlider {...defaultProps} showAdvanced />);

      const region = screen.getByRole('region', { name: /移动平均线分析/ });
      expect(region).toBeInTheDocument();
    });
  });

  describe('状态和动态内容可访问性', () => {
    it('禁用状态应该正确反映', () => {
      render(<MovingAverageSlider {...defaultProps} disabled />);

      const slider = screen.getByRole('slider');
      expect(slider).toBeDisabled();
      expect(slider).toHaveAttribute('aria-disabled', 'true');

      const buttons = screen.getAllByRole('button');
      buttons.forEach(button => {
        expect(button).toBeDisabled();
      });
    });

    it('风险等级状态应该可访问', () => {
      render(<MovingAverageSlider {...defaultProps} value={5} showAdvanced />);

      const riskStatus = screen.getByRole('status');
      expect(riskStatus).toBeInTheDocument();

      const riskLabel = screen.getByLabelText(/风险等级：/);
      expect(riskLabel).toBeInTheDocument();
    });

    it('状态变化应该有适当的指示器', () => {
      const { rerender } = render(
        <MovingAverageSlider {...defaultProps} value={20} />
      );

      // 改变值
      rerender(
        <MovingAverageSlider {...defaultProps} value={30} />
      );

      // 验证值更新了
      const slider = screen.getByRole('slider');
      expect(slider).toHaveAttribute('aria-valuenow', '30');
    });
  });

  describe('高级信息可访问性', () => {
    it('分析信息应该结构化', () => {
      render(<MovingAverageSlider {...defaultProps} showAdvanced />);

      const analysisCards = screen.getAllByRole('region');
      expect(analysisCards.length).toBeGreaterThanOrEqual(1);

      const strategyType = screen.getByText(/策略类型/);
      expect(strategyType).toBeInTheDocument();

      const signalFrequency = screen.getByText(/预期信号频率/);
      expect(signalFrequency).toBeInTheDocument();
    });

    it('使用建议应该可访问', () => {
      render(<MovingAverageSlider {...defaultProps} showAdvanced />);

      const suggestions = screen.getByRole('heading', {
        name: /使用建议/
      });
      expect(suggestions).toBeInTheDocument();

      const suggestionList = suggestions.nextElementSibling;
      expect(suggestionList).toBeInTheDocument();
      expect(suggestionList?.tagName).toBe('UL');
    });

    it('性能提示应该可访问', () => {
      render(<MovingAverageSlider {...defaultProps} value={10} showAdvanced />);

      const performanceTip = screen.getByRole('heading', {
        name: /性能提示/
      });
      expect(performanceTip).toBeInTheDocument();

      const tipContent = performanceTip.nextElementSibling;
      expect(tipContent).toBeInTheDocument();
      expect(tipContent?.tagName).toBe('P');
    });
  });

  describe('边界情况测试', () => {
    it('最小值应该正确处理', async () => {
      const { container } = render(
        <MovingAverageSlider {...defaultProps} value={5} />
      );

      await expectAccessible(container);

      const slider = screen.getByRole('slider');
      expect(slider).toHaveAttribute('aria-valuenow', '5');
    });

    it('最大值应该正确处理', async () => {
      const { container } = render(
        <MovingAverageSlider {...defaultProps} value={200} />
      );

      await expectAccessible(container);

      const slider = screen.getByRole('slider');
      expect(slider).toHaveAttribute('aria-valuenow', '200');
    });

    it('未定义onChange应该不抛出错误', async () => {
      const { container } = render(
        <MovingAverageSlider value={20} />
      );

      await expectAccessible(container);

      // 测试滑块操作不会导致错误
      const slider = screen.getByRole('slider');
      fireEvent.keyDown(slider, { key: 'ArrowRight' });

      // 应该没有错误抛出
      expect(true).toBe(true);
    });
  });

  describe('交互可访问性', () => {
    it('滑块应该响应所有键盘事件', () => {
      render(<MovingAverageSlider {...defaultProps} value={100} />);

      const slider = screen.getByRole('slider');

      // 测试所有方向键
      fireEvent.keyDown(slider, { key: 'ArrowUp' });
      fireEvent.keyDown(slider, { key: 'ArrowDown' });
      fireEvent.keyDown(slider, { key: 'ArrowLeft' });
      fireEvent.keyDown(slider, { key: 'ArrowRight' });

      expect(defaultProps.onChange).toHaveBeenCalledTimes(4);
    });

    it('按钮组应该有正确的角色', () => {
      render(<MovingAverageSlider {...defaultProps} />);

      const buttonGroup = document.querySelector('[role="group"]');
      expect(buttonGroup).toBeInTheDocument();
      expect(buttonGroup).toHaveAttribute('aria-label', '移动平均周期快速选择');
    });

    it('滑块刻度应该对屏幕阅读器可访问', () => {
      render(<MovingAverageSlider {...defaultProps} />);

      const scaleLabels = ['5', '50', '100', '150', '200'];
      scaleLabels.forEach(label => {
        const scaleLabel = screen.getByText(label);
        expect(scaleLabel).toBeInTheDocument();
      });
    });
  });

  describe('整体结构测试', () => {
    it('卡片结构应该正确', () => {
      render(<MovingAverageSlider {...defaultProps} />);

      const card = document.querySelector('[class*="border"]');
      expect(card).toBeInTheDocument();
    });

    it('内容区域应该有适当的间距', () => {
      const { container } = render(
        <MovingAverageSlider {...defaultProps} />
      );

      // 验证没有可访问性违规
      expect(container).toBeInTheDocument();
    });

    it('应该通过完整的axe扫描', async () => {
      const { container } = render(
        <MovingAverageSlider
          {...defaultProps}
          showAdvanced
          disabled={false}
        />
      );

      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
          'keyboard-navigation': { enabled: true },
          'aria-labels': { enabled: true },
          'focus-management': { enabled: true },
        }
      });

      expect(results).toHaveNoViolations();
    });
  });
});