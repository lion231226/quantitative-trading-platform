/**
 * 跳过链接组件
 * 为键盘用户提供快速跳转到主要内容区域的链接
 */

import React from 'react';
import { cn } from '@/lib/utils';

export interface SkipLink {
  /** 链接目标元素ID */
  target: string;
  /** 链接显示文本 */
  label: string;
  /** 可选的描述信息 */
  description?: string;
}

export interface SkipLinksProps {
  /** 跳过链接列表 */
  links: SkipLink[];
  /** 自定义样式类名 */
  className?: string;
}

/**
 * 跳过链接组件
 *
 * 提供可访问的跳过导航链接，让键盘用户可以快速跳到页面主要内容
 *
 * @example
 * ```tsx
 * <SkipLinks
 *   links={[
 *     { target: 'main-content', label: '跳转到主要内容' },
 *     { target: 'navigation', label: '跳转到导航菜单' },
 *     { target: 'search', label: '跳转到搜索框' }
 *   ]}
 * />
 * ```
 */
export const SkipLinks = ({ links, className }: SkipLinksProps) => {
  return (
    <nav
      aria-label="页面导航快捷链接"
      className={cn(
        // 默认隐藏，只有在获得焦点时显示
        'absolute left-0 top-0 z-50',
        'transform -translate-y-full focus-within:translate-y-0',
        'transition-transform duration-200 ease-out',
        className
      )}
    >
      <ul className="flex flex-col p-4 m-0 list-none bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 shadow-lg rounded-md">
        {links.map((link, index) => (
          <li key={index} className="m-0">
            <a
              href={`#${link.target}`}
              className={cn(
                // 样式：高对比度，清晰可见
                'block px-4 py-3 text-sm font-medium',
                'text-gray-900 dark:text-gray-100',
                'bg-white dark:bg-gray-900',
                'hover:bg-blue-50 dark:hover:bg-gray-800',
                'focus:bg-blue-100 dark:focus:bg-gray-700',
                'outline-none ring-2 ring-blue-500 ring-offset-2 ring-offset-white dark:ring-offset-gray-900',
                'rounded-md transition-colors duration-150',
                // 确保文字与背景有足够对比度
                'border border-transparent hover:border-blue-200 dark:hover:border-gray-600'
              )}
              onClick={(e) => {
                e.preventDefault();
                const target = document.getElementById(link.target);
                if (target) {
                  target.focus();
                  target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  const target = document.getElementById(link.target);
                  if (target) {
                    target.focus();
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                  }
                }
              }}
            >
              <span className="block">{link.label}</span>
              {link.description && (
                <span className="block text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {link.description}
                </span>
              )}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
};

/**
 * 主内容包装器，包含可访问的目标ID
 */
export interface MainContentProps {
  children: React.ReactNode;
  /** 内容区域ID，用于跳过链接的目标 */
  id?: string;
  /** 区域标签，供屏幕阅读器使用 */
  ariaLabel?: string;
  /** 区域标签ID，用于与标题关联 */
  ariaLabelledBy?: string;
  /** 自定义样式类名 */
  className?: string;
}

/**
 * 主内容组件
 *
 * 提供标准化的主要内容区域，包含适当的可访问性属性
 */
export const MainContent = ({
  children,
  id = 'main-content',
  ariaLabel,
  ariaLabelledBy,
  className,
}: MainContentProps) => {
  return (
    <main
      id={id}
      role="main"
      aria-label={ariaLabel}
      aria-labelledby={ariaLabelledBy}
      tabIndex={-1} // 可以通过程序获得焦点
      className={cn(
        // 确保在获得焦点时有视觉指示
        'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
        className
      )}
    >
      {children}
    </main>
  );
};

/**
 * 创建跳过链接的便捷函数
 */
export const createSkipLinks = (): SkipLink[] => [
  {
    target: 'main-content',
    label: '跳转到主要内容',
    description: '跳到页面的主要内容区域',
  },
  {
    target: 'navigation',
    label: '跳转到导航菜单',
    description: '跳到主导航菜单',
  },
  {
    target: 'search',
    label: '跳转到搜索框',
    description: '跳到搜索功能',
  },
];

export default SkipLinks;