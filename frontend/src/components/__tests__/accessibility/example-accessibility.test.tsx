/**
 * 示例可访问性测试文件
 * 展示如何使用jest-axe和自定义工具测试组件可访问性
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { testAccessibility, expectAccessible, testKeyboardNavigation, testAriaAttributes } from '@/utils/accessibility/test-utils';

// 示例组件（在实际使用中应导入真实组件）
const ExampleButton = ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
  <button {...props}>{children}</button>
);

const ExampleForm = () => (
  <form>
    <label htmlFor="email">邮箱地址</label>
    <input id="email" type="email" required aria-describedby="email-help" />
    <div id="email-help">请输入有效的邮箱地址</div>

    <button type="submit" aria-label="提交表单">
      提交
    </button>
  </form>
);

describe('可访问性测试示例', () => {
  beforeEach(() => {
    // 确保测试环境有正确的DOM结构
    document.body.innerHTML = '';
  });

  describe('基础可访问性测试', () => {
    it('示例按钮应该无障碍', async () => {
      const { container } = render(<ExampleButton>点击我</ExampleButton>);

      // 使用便捷函数测试可访问性
      await expectAccessible(container);
    });

    it('示例表单应该无障碍', async () => {
      const { container } = render(<ExampleForm />);

      // 使用便捷函数测试可访问性
      await expectAccessible(container);
    });

    it('键盘导航测试', () => {
      const { getByRole } = render(<ExampleButton>点击我</ExampleButton>);
      const button = getByRole('button');

      // 测试键盘导航
      testKeyboardNavigation(button);
    });

    it('ARIA属性测试', () => {
      const { getByRole } = render(
        <button aria-label="关闭对话框" aria-expanded="false">
          ✕
        </button>
      );

      const button = getByRole('button');

      // 测试ARIA属性
      testAriaAttributes(button, {
        'aria-label': '关闭对话框',
        'aria-expanded': 'false',
      });
    });
  });

  describe('详细可访问性分析', () => {
    it('生成详细的可访问性报告', async () => {
      // 故意创建一个有可访问性问题的组件
      const ProblematicComponent = () => (
        <div>
          <button style={{ color: '#cccccc', backgroundColor: '#ffffff' }}>
            低对比度按钮
          </button>
          <img src="test.jpg" alt="" /> {/* 空的alt属性 */}
          <div role="button" tabIndex={-1}>
            不可点击的按钮
          </div>
        </div>
      );

      const { container } = render(<ProblematicComponent />);
      const report = await testAccessibility(container);

      // 检查是否有违规
      expect(report.violations.length).toBeGreaterThan(0);

      // 输出详细报告（实际使用中可以记录到测试报告中）
      console.log('可访问性违规报告:', report.violations);
    });
  });

  describe('组件特定可访问性测试', () => {
    it('表单控件应该有适当的标签关联', async () => {
      const FormWithIssues = () => (
        <form>
          {/* 问题1: 输入框没有关联的标签 */}
          <input type="text" placeholder="姓名" />

          {/* 问题2: 没有表单标签 */}
          <label htmlFor="password">密码</label>
          <input id="password" type="password" />
        </form>
      );

      const { container } = render(<FormWithIssues />);
      const results = await testAccessibility(container);

      // 应该发现标签关联问题
      const inputViolation = results.violations.find(v => v.id === 'label');
      expect(inputViolation).toBeDefined();
    });

    it('颜色对比度问题检测', async () => {
      const LowContrastComponent = () => (
        <div style={{ color: '#f0f0f0', backgroundColor: '#ffffff' }}>
          低对比度文本
        </div>
      );

      const { container } = render(<LowContrastComponent />);
      const results = await testAccessibility(container);

      // 应该发现颜色对比度问题
      const contrastViolation = results.violations.find(v => v.id === 'color-contrast');
      expect(contrastViolation).toBeDefined();
    });
  });
});