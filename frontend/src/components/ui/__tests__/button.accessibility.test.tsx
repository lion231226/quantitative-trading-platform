/**
 * Button组件可访问性测试
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { axe, toHaveNoViolations } from 'jest-axe';
import { expectAccessible, testKeyboardNavigation } from '@/utils/accessibility/test-utils';
import { Button } from '../button';

// 扩展expect matcher
expect.extend(toHaveNoViolations);

describe('Button - 可访问性测试', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('基础可访问性', () => {
    it('默认按钮应该通过axe检查', async () => {
      const { container } = render(<Button>点击我</Button>);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('应该使用便捷函数通过可访问性测试', async () => {
      const { container } = render(<Button>测试按钮</Button>);

      await expectAccessible(container);
    });

    it('不同变体的按钮应该可访问', async () => {
      const variants = ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link'] as const;

      for (const variant of variants) {
        const { container } = render(
          <Button variant={variant}>{variant}按钮</Button>
        );

        await expectAccessible(container);
      }
    });

    it('不同尺寸的按钮应该可访问', async () => {
      const sizes = ['default', 'sm', 'lg', 'icon'] as const;

      for (const size of sizes) {
        const { container } = render(
          <Button size={size}>{size}按钮</Button>
        );

        await expectAccessible(container);
      }
    });
  });

  describe('ARIA属性测试', () => {
    it('应该有正确的role属性', () => {
      render(<Button>测试按钮</Button>);

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('自定义aria-label应该正确设置', () => {
      render(
        <Button aria-label="自定义标签">
          <span>图标</span>
        </Button>
      );

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', '自定义标签');
    });

    it('iconLabel属性应该设置aria-label', () => {
      render(<Button iconLabel="删除按钮">×</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', '删除按钮');
    });

    it('ariaDescription应该设置aria-describedby', () => {
      render(
        <div>
          <div id="help-text">这是帮助文本</div>
          <Button ariaDescription="help-text">按钮</Button>
        </div>
      );

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-describedby', 'help-text');
    });

    it('disabled状态应该设置aria-disabled', () => {
      render(<Button disabled>禁用按钮</Button>);

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute('aria-disabled', 'true');
    });

    it('应该支持自定义ARIA属性', () => {
      render(
        <Button
          aria-expanded="true"
          aria-controls="panel-1"
        >
          展开
        </Button>
      );

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-expanded', 'true');
      expect(button).toHaveAttribute('aria-controls', 'panel-1');
    });
  });

  describe('键盘导航测试', () => {
    it('应该支持Tab键聚焦', () => {
      render(<Button>可聚焦按钮</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('tabIndex', '0');
    });

    it('应该支持键盘导航', () => {
      const handleClick = jest.fn();
      render(<Button onClick={handleClick}>键盘测试</Button>);

      const button = screen.getByRole('button');

      // 测试键盘导航工具函数
      testKeyboardNavigation(button);

      // 测试实际的键盘事件
      fireEvent.keyDown(button, { key: 'Enter' });
      expect(handleClick).toHaveBeenCalledTimes(1);

      fireEvent.keyDown(button, { key: ' ' });
      expect(handleClick).toHaveBeenCalledTimes(2);
    });

    it('禁用按钮不应该响应键盘事件', () => {
      const handleClick = jest.fn();
      render(<Button disabled onClick={handleClick}>禁用按钮</Button>);

      const button = screen.getByRole('button');

      fireEvent.keyDown(button, { key: 'Enter' });
      fireEvent.keyDown(button, { key: ' ' });

      expect(handleClick).not.toHaveBeenCalled();
    });

    it('应该有正确的焦点指示器', () => {
      render(<Button>焦点测试</Button>);

      const button = screen.getByRole('button');
      button.focus();

      expect(button).toHaveFocus();
      expect(button).toHaveClass('focus-visible');
    });
  });

  describe('asChild模式测试', () => {
    it('作为链接时应该保持可访问性', async () => {
      const { container } = render(
        <Button asChild>
          <a href="/test">链接按钮</a>
        </Button>
      );

      // 应该通过axe检查
      const results = await axe(container);
      expect(results).toHaveNoViolations();

      // 应该有正确的role
      const link = screen.getByRole('link');
      expect(link).toBeInTheDocument();
      expect(link).toHaveTextContent('链接按钮');
      expect(link).toHaveAttribute('href', '/test');
    });

    it('作为链接时应该支持键盘导航', () => {
      const handleClick = jest.fn();
      render(
        <Button asChild>
          <a href="/test" onClick={handleClick}>
            链接按钮
          </a>
        </Button>
      );

      const link = screen.getByRole('link');

      // Enter键应该触发点击
      fireEvent.keyDown(link, { key: 'Enter' });
      expect(handleClick).toHaveBeenCalled();
    });
  });

  describe('按钮内容测试', () => {
    it('纯文本按钮应该可访问', async () => {
      const { container } = render(<Button>纯文本</Button>);

      await expectAccessible(container);

      const button = screen.getByRole('button');
      expect(button).toHaveTextContent('纯文本');
    });

    it('带图标的按钮应该可访问', async () => {
      const { container } = render(
        <Button>
          <span aria-hidden="true">🗑️</span>
          删除
        </Button>
      );

      await expectAccessible(container);

      const button = screen.getByRole('button');
      expect(button).toHaveTextContent('删除');
    });

    it('仅图标按钮应该有适当的标签', async () => {
      const { container } = render(
        <Button iconLabel="关闭">×</Button>
      );

      await expectAccessible(container);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', '关闭');
      expect(button).toHaveTextContent('×');
    });

    it('复杂内容按钮应该可访问', async () => {
      const { container } = render(
        <Button>
          <div>
            <strong>主标题</strong>
            <span>副标题</span>
          </div>
        </Button>
      );

      await expectAccessible(container);

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });
  });

  describe('状态测试', () => {
    it('pressed状态应该正确设置', () => {
      render(<Button aria-pressed="true">切换按钮</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-pressed', 'true');
    });

    it('expanded状态应该正确设置', () => {
      render(<Button aria-expanded="false">展开按钮</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-expanded', 'false');
    });

    it('busy状态应该正确设置', () => {
      render(<Button aria-busy="true">加载中</Button>);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-busy', 'true');
    });
  });

  describe('对比度和颜色测试', () => {
    it('不同状态下的对比度应该符合标准', async () => {
      const states = [
        { variant: 'default' as const, disabled: false },
        { variant: 'destructive' as const, disabled: false },
        { variant: 'outline' as const, disabled: false },
        { variant: 'default' as const, disabled: true },
      ];

      for (const state of states) {
        const { container } = render(
          <Button variant={state.variant} disabled={state.disabled}>
            测试按钮
          </Button>
        );

        await expectAccessible(container);
      }
    });

    it('焦点状态应该有适当的视觉指示', async () => {
      const { container } = render(<Button>焦点测试</Button>);

      // 模拟焦点
      const button = screen.getByRole('button');
      button.focus();

      await expectAccessible(container);

      // 应该有焦点样式类
      expect(button).toHaveClass('focus-visible');
    });
  });

  describe('键盘快捷键测试', () => {
    it('应该支持标准键盘快捷键', () => {
      const handleClick = jest.fn();
      render(<Button onClick={handleClick}>快捷键测试</Button>);

      const button = screen.getByRole('button');

      // Enter键
      fireEvent.keyDown(button, { key: 'Enter' });
      expect(handleClick).toHaveBeenCalledTimes(1);

      // 空格键
      fireEvent.keyDown(button, { key: ' ' });
      expect(handleClick).toHaveBeenCalledTimes(2);

      // 其他键不应该触发
      fireEvent.keyDown(button, { key: 'A' });
      expect(handleClick).toHaveBeenCalledTimes(2);
    });

    it('应该支持自定义键盘事件处理', () => {
      const handleKeyDown = jest.fn();
      const handleClick = jest.fn();

      render(
        <Button onKeyDown={handleKeyDown} onClick={handleClick}>
          自定义键盘
        </Button>
      );

      const button = screen.getByRole('button');

      fireEvent.keyDown(button, { key: 'ArrowUp' });
      expect(handleKeyDown).toHaveBeenCalledTimes(1);

      fireEvent.keyDown(button, { key: 'Enter' });
      expect(handleKeyDown).toHaveBeenCalledTimes(2);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('边缘情况测试', () => {
    it('空按钮应该可访问', async () => {
      const { container } = render(
        <Button aria-label="空按钮" />
      );

      await expectAccessible(container);

      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', '空按钮');
    });

    it('长文本按钮应该可访问', async () => {
      const longText = '这是一个非常长的按钮文本，用于测试长文本内容的可访问性处理';
      const { container } = render(<Button>{longText}</Button>);

      await expectAccessible(container);

      const button = screen.getByRole('button');
      expect(button).toHaveTextContent(longText);
    });

    it('嵌套HTML元素按钮应该可访问', async () => {
      const { container } = render(
        <Button>
          <div className="flex items-center">
            <span className="icon">🎯</span>
            <span className="text">
              <strong>重要</strong>操作
            </span>
          </div>
        </Button>
      );

      await expectAccessible(container);

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });
  });

  describe('严格模式和辅助功能测试', () => {
    it('应该通过严格的可访问性检查', async () => {
      const { container } = render(
        <div>
          <Button>按钮1</Button>
          <Button disabled>按钮2</Button>
          <Button variant="outline">按钮3</Button>
          <Button aria-label="隐藏标签" aria-describedby="desc-1">
            按钮4
          </Button>
          <div id="desc-1">描述文本</div>
        </div>
      );

      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
          'keyboard-navigation': { enabled: true },
          'aria-labels': { enabled: true },
          'focus-management': { enabled: true },
          'link-in-text-block': { enabled: true },
          'button-name': { enabled: true },
          'focus-order-semantics': { enabled: true },
        }
      });

      expect(results).toHaveNoViolations();
    });

    it('应该支持屏幕阅读器优化', () => {
      render(
        <Button
          aria-label="删除项目"
          aria-describedby="delete-help"
          iconLabel="删除"
        >
          🗑️
        </Button>
      );

      const button = screen.getByRole('button');

      // 检查屏幕阅读器相关属性
      expect(button).toHaveAttribute('aria-label', '删除项目');
      expect(button).toHaveAttribute('iconLabel'); // 自定义属性
      expect(button).toHaveAttribute('aria-describedby', 'delete-help');
    });
  });
});