/**
 * 键盘导航指示器组件
 * 显示当前键盘导航状态和快捷键帮助
 */

import React, { useState, useEffect } from 'react';
import { useKeyboardNavigation } from './keyboard-navigation-provider';
import { Button } from './button';
import { Keyboard, HelpCircle, Eye, EyeOff } from 'lucide-react';

export interface KeyboardNavigationIndicatorProps {
  /** 是否显示指示器 */
  show?: boolean;
  /** 位置：'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' */
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  /** 自定义样式类名 */
  className?: string;
}

/**
 * 键盘导航状态指示器
 */
export const KeyboardNavigationIndicator: React.FC<KeyboardNavigationIndicatorProps> = ({
  show = true,
  position = 'top-right',
  className = '',
}) => {
  const { keyboardNavigationEnabled, toggleKeyboardNavigation } = useKeyboardNavigation();
  const [showHelp, setShowHelp] = useState(false);

  // 获取位置样式
  const getPositionClasses = () => {
    const baseClasses = 'fixed z-50 p-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg';

    switch (position) {
      case 'top-right':
        return `${baseClasses} top-4 right-4`;
      case 'top-left':
        return `${baseClasses} top-4 left-4`;
      case 'bottom-right':
        return `${baseClasses} bottom-4 right-4`;
      case 'bottom-left':
        return `${baseClasses} bottom-4 left-4`;
      default:
        return `${baseClasses} top-4 right-4`;
    }
  };

  // 快捷键列表
  const shortcuts = [
    { key: 'Tab', description: '在可交互元素间导航' },
    { key: 'Shift + Tab', description: '反向导航' },
    { key: 'Enter', description: '激活按钮或链接' },
    { key: 'Space', description: '激活按钮或选择' },
    { key: 'Escape', description: '关闭对话框或取消操作' },
    { key: 'Arrow Keys', description: '在列表或菜单中导航' },
    { key: 'Ctrl + /', description: '切换键盘导航' },
    { key: 'Alt + ?', description: '显示帮助信息' },
    { key: 'Home/End', description: '跳转到开头/结尾' },
  ];

  return (
    <>
      {show && (
        <div className={`${getPositionClasses()} ${className}`} role="status" aria-live="polite">
          <div className="flex items-center space-x-2">
            {/* 状态指示器 */}
            <div className="flex items-center space-x-1">
              {keyboardNavigationEnabled ? (
                <>
                  <Keyboard className="h-4 w-4 text-green-600" aria-hidden="true" />
                  <span className="text-xs text-green-600 font-medium">键盘导航启用</span>
                </>
              ) : (
                <>
                  <Keyboard className="h-4 w-4 text-gray-400" aria-hidden="true" />
                  <span className="text-xs text-gray-500">键盘导航禁用</span>
                </>
              )}
            </div>

            {/* 切换按钮 */}
            <Button
              variant="outline"
              size="sm"
              onClick={toggleKeyboardNavigation}
              aria-label={keyboardNavigationEnabled ? '禁用键盘导航' : '启用键盘导航'}
              className="h-6 px-2 text-xs"
            >
              {keyboardNavigationEnabled ? (
                <EyeOff className="h-3 w-3" />
              ) : (
                <Eye className="h-3 w-3" />
              )}
            </Button>

            {/* 帮助按钮 */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowHelp(!showHelp)}
              aria-label="显示键盘快捷键帮助"
              className="h-6 px-2 text-xs"
            >
              <HelpCircle className="h-3 w-3" />
            </Button>
          </div>
        </div>
      )}

      {/* 帮助对话框 */}
      {showHelp && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
          role="dialog"
          aria-labelledby="keyboard-help-title"
          aria-modal="true"
        >
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-md w-full mx-4 max-h-[80vh] overflow-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 id="keyboard-help-title" className="text-lg font-semibold flex items-center space-x-2">
                  <Keyboard className="h-5 w-5" />
                  <span>键盘导航快捷键</span>
                </h2>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowHelp(false)}
                  aria-label="关闭帮助对话框"
                >
                  ×
                </Button>
              </div>

              <div className="space-y-3">
                {shortcuts.map((shortcut, index) => (
                  <div key={index} className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800">
                    <div className="flex items-center space-x-2">
                      <kbd className="px-2 py-1 text-xs font-semibold text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded">
                        {shortcut.key}
                      </kbd>
                    </div>
                    <span className="text-sm text-gray-600 dark:text-gray-400 text-right">
                      {shortcut.description}
                    </span>
                  </div>
                ))}
              </div>

              <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  <strong>提示：</strong>键盘导航可以让不使用鼠标的用户完全访问所有功能。使用Tab键在元素间导航，按Enter键激活。
                </p>
              </div>

              <div className="mt-6 flex justify-end">
                <Button onClick={() => setShowHelp(false)}>
                  关闭
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

/**
 * 键盘快捷键提示组件
 */
export const KeyboardShortcut: React.FC<{
  keys: string[];
  description?: string;
  className?: string;
}> = ({ keys, description, className = '' }) => {
  return (
    <div className={`flex items-center space-x-1 ${className}`}>
      {keys.map((key, index) => (
        <React.Fragment key={index}>
          {index > 0 && <span className="text-gray-400">+</span>}
          <kbd className="px-2 py-1 text-xs font-semibold text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded">
            {key}
          </kbd>
        </React.Fragment>
      ))}
      {description && (
        <span className="text-sm text-gray-600 dark:text-gray-400 ml-2">
          {description}
        </span>
      )}
    </div>
  );
};

export default KeyboardNavigationIndicator;