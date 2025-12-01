/**
 * 可访问性测试工具函数
 * 提供用于Jest测试的可访问性断言和工具
 */

import { axe, toHaveNoViolations, AxeResults, Violation } from 'jest-axe';
import { RenderResult } from '@testing-library/react';
import { a11yConfig } from './test-config';

// 导出axe matcher供测试使用
export { toHaveNoViolations };

/**
 * 测试组件可访问性的便捷函数
 * @param renderResult React Testing Library的render结果
 * @param options 自定义axe配置选项
 * @returns Promise<AxeResults>
 */
export const testAccessibility = async (
  renderResult: RenderResult,
  options?: any
): Promise<AxeResults> => {
  const { container } = renderResult;

  const results = await axe(container, {
    ...a11yConfig.globalOptions,
    ...options,
  });

  return results;
};

/**
 * 断言组件没有可访问性违规
 * @param renderResult React Testing Library的render结果
 * @param options 自定义axe配置选项
 */
export const expectAccessible = async (
  renderResult: RenderResult,
  options?: any
): Promise<void> => {
  const results = await testAccessibility(renderResult, options);
  expect(results).toHaveNoViolations();
};

/**
 * 检查特定组件类型的可访问性
 * @param renderResult React Testing Library的render结果
 * @param componentType 组件类型名称
 * @param options 自定义axe配置选项
 */
export const expectComponentAccessible = async (
  renderResult: RenderResult,
  componentType: keyof typeof a11yConfig.componentConfig,
  options?: any
): Promise<void> => {
  const componentConfig = a11yConfig.componentConfig[componentType];
  const mergedOptions = {
    ...a11yConfig.globalOptions,
    ...componentConfig,
    ...options,
  };

  const results = await testAccessibility(renderResult, mergedOptions);
  expect(results).toHaveNoViolations();
};

/**
 * 获取可访问性违规的详细报告
 * @param renderResult React Testing Library的render结果
 * @returns 格式化的违规报告
 */
export const getAccessibilityReport = async (
  renderResult: RenderResult
): Promise<string> => {
  const results = await testAccessibility(renderResult);

  if (results.violations.length === 0) {
    return '✅ 无可访问性违规发现';
  }

  let report = `❌ 发现 ${results.violations.length} 个可访问性违规:\n\n`;

  results.violations.forEach((violation, index) => {
    report += `${index + 1}. ${violation.impact.toUpperCase()} - ${violation.id}\n`;
    report += `   描述: ${violation.description}\n`;
    report += `   帮助: ${violation.help}\n`;
    report += `   帮助URL: ${violation.helpUrl}\n`;

    if (violation.nodes.length > 0) {
      report += `   影响的元素 (${violation.nodes.length}个):\n`;
      violation.nodes.forEach((node, nodeIndex) => {
        report += `     ${nodeIndex + 1}. `;
        if (node.target) {
          report += node.target.join(', ');
        }
        if (node.html) {
          report += ` (${node.html.substring(0, 100)}${node.html.length > 100 ? '...' : ''})`;
        }
        report += '\n';
      });
    }

    report += '\n';
  });

  return report;
};

/**
 * 检查键盘导航可访问性
 * @param element 要测试的元素
 */
export const testKeyboardNavigation = (element: HTMLElement): void => {
  // 检查元素是否可聚焦
  expect(element.tabIndex).not.toBe(-1);

  // 模拟键盘事件
  const events = ['keydown', 'keyup', 'keypress'];
  events.forEach(eventType => {
    const event = new KeyboardEvent(eventType, {
      key: 'Enter',
      code: 'Enter',
      keyCode: 13,
    });

    expect(() => {
      element.dispatchEvent(event);
    }).not.toThrow();
  });
};

/**
 * 检查ARIA属性
 * @param element 要测试的元素
 * @param expectedAriaProps 预期的ARIA属性
 */
export const testAriaAttributes = (
  element: HTMLElement,
  expectedAriaProps: Record<string, string>
): void => {
  Object.entries(expectedAriaProps).forEach(([attr, value]) => {
    expect(element.getAttribute(attr)).toBe(value);
  });
};

/**
 * 测试屏幕阅读器通知
 * @param renderResult React Testing Library的render结果
 * @param announcement 预期的屏幕阅读器通知
 */
export const testScreenReaderAnnouncement = (
  renderResult: RenderResult,
  announcement: string
): void => {
  const { container } = renderResult;
  const liveRegions = container.querySelectorAll('[aria-live], [role="status"], [role="alert"]');

  let found = false;
  liveRegions.forEach(region => {
    if (region.textContent?.includes(announcement)) {
      found = true;
    }
  });

  expect(found).toBe(true);
};