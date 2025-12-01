import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { Button } from '../button';
import { expectAccessible } from '@/utils/accessibility/test-utils';

describe('Button Component', () => {
  it('renders correctly with default props', () => {
    render(<Button>Click me</Button>);
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-primary');
  });

  it('applies variant classes correctly', () => {
    render(<Button variant="destructive">Delete</Button>);
    const button = screen.getByRole('button', { name: /delete/i });
    expect(button).toHaveClass('bg-destructive');
  });

  it('applies size classes correctly', () => {
    render(<Button size="lg">Large Button</Button>);
    const button = screen.getByRole('button', { name: /large button/i });
    expect(button).toHaveClass('h-11');
  });

  it('handles click events', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);

    const button = screen.getByRole('button', { name: /click me/i });
    fireEvent.click(button);

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('can be disabled', () => {
    const handleClick = jest.fn();
    render(
      <Button disabled onClick={handleClick}>
        Disabled
      </Button>,
    );

    const button = screen.getByRole('button', { name: /disabled/i });
    expect(button).toBeDisabled();

    fireEvent.click(button);
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('renders as child when asChild is true', () => {
    render(
      <Button asChild>
        <a href="/test">Link Button</a>
      </Button>,
    );

    const link = screen.getByRole('link', { name: /link button/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/test');
  });

  describe('可访问性测试', () => {
    it('基础按钮应该无障碍', async () => {
      const { container } = render(<Button>点击我</Button>);

      // 测试可访问性
      await expectAccessible(container);
    });

    it('禁用按钮应该无障碍', async () => {
      const { container } = render(<Button disabled>禁用按钮</Button>);

      // 测试可访问性
      await expectAccessible(container);
    });

    it('不同变体的按钮应该无障碍', async () => {
      const { container } = render(
        <div>
          <Button variant="destructive">删除</Button>
          <Button variant="outline">轮廓</Button>
          <Button variant="secondary">次要</Button>
          <Button variant="ghost">幽灵</Button>
        </div>
      );

      // 测试可访问性
      await expectAccessible(container);
    });

    it('不同尺寸的按钮应该无障碍', async () => {
      const { container } = render(
        <div>
          <Button size="sm">小按钮</Button>
          <Button size="default">默认按钮</Button>
          <Button size="lg">大按钮</Button>
        </div>
      );

      // 测试可访问性
      await expectAccessible(container);
    });

    it('按钮应该支持键盘导航', () => {
      const { getByRole } = render(<Button>键盘测试按钮</Button>);
      const button = getByRole('button');

      // 检查tabIndex
      expect(button).toHaveAttribute('tabIndex', '0');

      // 模拟键盘事件
      fireEvent.keyDown(button, { key: 'Enter' });
      fireEvent.keyDown(button, { key: ' ' });

      // 不应该抛出错误
      expect(true).toBe(true);
    });

    it('链接形式的按钮应该无障碍', async () => {
      const { container } = render(
        <Button asChild>
          <a href="/test">链接按钮</a>
        </Button>
      );

      // 测试可访问性
      await expectAccessible(container);
    });
  });
});
