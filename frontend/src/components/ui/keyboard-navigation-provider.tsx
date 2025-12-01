/**
 * 键盘导航提供者组件
 * 为应用提供全局键盘导航支持和配置
 */

import React, { createContext, useContext, useEffect, useRef, useState, useCallback, ReactNode } from 'react';
import { SkipLinks } from './skip-links';
import { ScreenReaderAnnouncer } from './screen-reader-announcer';

interface KeyboardNavigationContextValue {
  /** 当前焦点元素的索引 */
  focusedIndex: number;
  /** 设置焦点到指定索引 */
  setFocusedIndex: (index: number) => void;
  /** 是否启用键盘导航 */
  keyboardNavigationEnabled: boolean;
  /** 切换键盘导航状态 */
  toggleKeyboardNavigation: () => void;
  /** 注册可聚焦元素 */
  registerFocusableElement: (id: string, element: HTMLElement) => void;
  /** 注销可聚焦元素 */
  unregisterFocusableElement: (id: string) => void;
  /** 导航到下一个元素 */
  focusNext: () => void;
  /** 导航到上一个元素 */
  focusPrevious: () => void;
  /** 跳转到第一个元素 */
  focusFirst: () => void;
  /** 跳转到最后一个元素 */
  focusLast: () => void;
}

const KeyboardNavigationContext = createContext<KeyboardNavigationContextValue | null>(null);

export interface KeyboardNavigationProviderProps {
  children: ReactNode;
  /** 是否启用键盘导航，默认true */
  enabled?: boolean;
  /** 跳过链接配置 */
  skipLinks?: Array<{
    target: string;
    label: string;
    description?: string;
  }>;
  /** 自定义键盘快捷键 */
  shortcuts?: Record<string, () => void>;
  /** 通知消息 */
  announcement?: string;
  /** 通知播报策略 */
  announcementPoliteness?: 'polite' | 'assertive';
}

/**
 * 键盘导航提供者组件
 */
export const KeyboardNavigationProvider: React.FC<KeyboardNavigationProviderProps> = ({
  children,
  enabled = true,
  skipLinks,
  shortcuts,
  announcement,
  announcementPoliteness = 'polite',
}) => {
  const [keyboardNavigationEnabled, setKeyboardNavigationEnabled] = useState(enabled);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const [announcementMessage, setAnnouncementMessage] = useState(announcement);

  const focusableElementsRef = useRef<Map<string, HTMLElement>>(new Map());
  const focusableOrderRef = useRef<string[]>([]);

  // 注册可聚焦元素
  const registerFocusableElement = useCallback((id: string, element: HTMLElement) => {
    focusableElementsRef.current.set(id, element);
    if (!focusableOrderRef.current.includes(id)) {
      focusableOrderRef.current.push(id);
    }
  }, []);

  // 注销可聚焦元素
  const unregisterFocusableElement = useCallback((id: string) => {
    focusableElementsRef.current.delete(id);
    focusableOrderRef.current = focusableOrderRef.current.filter(item => item !== id);
  }, []);

  // 获取当前聚焦的元素
  const getCurrentElement = useCallback(() => {
    const currentId = focusableOrderRef.current[focusedIndex];
    return currentId ? focusableElementsRef.current.get(currentId) : null;
  }, [focusedIndex]);

  // 设置焦点到指定索引
  const setFocusedIndexWithFocus = useCallback((index: number) => {
    const focusableIds = focusableOrderRef.current;
    if (index >= 0 && index < focusableIds.length) {
      setFocusedIndex(index);
      const element = focusableElementsRef.current.get(focusableIds[index]);
      if (element && typeof element.focus === 'function') {
        element.focus();
      }
    }
  }, []);

  // 导航到下一个元素
  const focusNext = useCallback(() => {
    const nextIndex = (focusedIndex + 1) % focusableOrderRef.current.length;
    setFocusedIndexWithFocus(nextIndex);
  }, [focusedIndex, setFocusedIndexWithFocus]);

  // 导航到上一个元素
  const focusPrevious = useCallback(() => {
    const prevIndex = focusedIndex === 0 ? focusableOrderRef.current.length - 1 : focusedIndex - 1;
    setFocusedIndexWithFocus(prevIndex);
  }, [focusedIndex, setFocusedIndexWithFocus]);

  // 跳转到第一个元素
  const focusFirst = useCallback(() => {
    setFocusedIndexWithFocus(0);
  }, [setFocusedIndexWithFocus]);

  // 跳转到最后一个元素
  const focusLast = useCallback(() => {
    const lastIndex = focusableOrderRef.current.length - 1;
    setFocusedIndexWithFocus(lastIndex);
  }, [setFocusedIndexWithFocus]);

  // 切换键盘导航状态
  const toggleKeyboardNavigation = useCallback(() => {
    setKeyboardNavigationEnabled(prev => {
      const newState = !prev;
      setAnnouncementMessage(
        newState ? '键盘导航已启用' : '键盘导航已禁用'
      );
      return newState;
    });
  }, []);

  // 全局键盘事件处理
  const handleGlobalKeyDown = useCallback((event: KeyboardEvent) => {
    if (!keyboardNavigationEnabled) return;

    // Ctrl + / 切换键盘导航
    if (event.ctrlKey && event.key === '/') {
      event.preventDefault();
      toggleKeyboardNavigation();
      return;
    }

    // Alt + ? 显示帮助
    if (event.altKey && event.key === '?') {
      event.preventDefault();
      setAnnouncementMessage('使用Tab键在页面元素间导航，使用Ctrl+/切换键盘导航');
      return;
    }

    // 自定义快捷键
    if (shortcuts && shortcuts[event.key]) {
      // 检查修饰键组合
      const keyCombo = [];
      if (event.ctrlKey) keyCombo.push('Ctrl');
      if (event.altKey) keyCombo.push('Alt');
      if (event.shiftKey) keyCombo.push('Shift');
      keyCombo.push(event.key);

      const comboString = keyCombo.join('+');
      if (shortcuts[comboString]) {
        event.preventDefault();
        shortcuts[comboString]();
        return;
      }

      // 尝试单个键
      if (shortcuts[event.key]) {
        event.preventDefault();
        shortcuts[event.key]();
      }
    }
  }, [keyboardNavigationEnabled, shortcuts, toggleKeyboardNavigation]);

  // 添加全局键盘事件监听
  useEffect(() => {
    document.addEventListener('keydown', handleGlobalKeyDown);
    return () => {
      document.removeEventListener('keydown', handleGlobalKeyDown);
    };
  }, [handleGlobalKeyDown]);

  // 清理通知消息
  useEffect(() => {
    if (announcementMessage) {
      const timer = setTimeout(() => {
        setAnnouncementMessage(undefined);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [announcementMessage]);

  const contextValue: KeyboardNavigationContextValue = {
    focusedIndex,
    setFocusedIndex: setFocusedIndexWithFocus,
    keyboardNavigationEnabled,
    toggleKeyboardNavigation,
    registerFocusableElement,
    unregisterFocusableElement,
    focusNext,
    focusPrevious,
    focusFirst,
    focusLast,
  };

  return (
    <KeyboardNavigationContext.Provider value={contextValue}>
      {/* 跳过链接 */}
      {skipLinks && (
        <SkipLinks links={skipLinks} />
      )}

      {/* 屏幕阅读器通知 */}
      <ScreenReaderAnnouncer
        message={announcementMessage || ''}
        politeness={announcementPoliteness}
      />

      {children}
    </KeyboardNavigationContext.Provider>
  );
};

/**
 * 使用键盘导航上下文的Hook
 */
export const useKeyboardNavigation = () => {
  const context = useContext(KeyboardNavigationContext);
  if (!context) {
    throw new Error('useKeyboardNavigation must be used within a KeyboardNavigationProvider');
  }
  return context;
};

/**
 * 可聚焦元素Hook
 */
export const useFocusableElement = (id: string, enabled = true) => {
  const { registerFocusableElement, unregisterFocusableElement } = useKeyboardNavigation();
  const elementRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (enabled && elementRef.current && id) {
      registerFocusableElement(id, elementRef.current);
      return () => {
        unregisterFocusableElement(id);
      };
    }
  }, [id, enabled, registerFocusableElement, unregisterFocusableElement]);

  return elementRef;
};

export default KeyboardNavigationProvider;