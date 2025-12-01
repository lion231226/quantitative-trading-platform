/**
 * 焦点管理Hook
 * 提供键盘导航和焦点管理的实用工具
 */

import { useCallback, useEffect, useRef } from 'react';

export interface FocusManagementOptions {
  /** 焦点陷阱容器 */
  container?: HTMLElement | null;
  /** 初始焦点元素选择器 */
  initialFocus?: string;
  /** 恢复焦点元素 */
  restoreFocus?: HTMLElement | null;
  /** 禁用Tab导航 */
  disableTabNavigation?: boolean;
  /** 循环导航（在容器内循环） */
  cycleNavigation?: boolean;
}

/**
 * 焦点管理Hook
 */
export const useFocusManagement = (options: FocusManagementOptions = {}) => {
  const {
    container,
    initialFocus,
    restoreFocus,
    disableTabNavigation = false,
    cycleNavigation = true,
  } = options;

  const previousFocusRef = useRef<HTMLElement | null>(null);
  const containerRef = useRef<HTMLElement | null>(container || null);

  // 更新容器引用
  useEffect(() => {
    if (container) {
      containerRef.current = container;
    }
  }, [container]);

  // 获取容器内所有可聚焦元素
  const getFocusableElements = useCallback((element: HTMLElement) => {
    const focusableSelectors = [
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      'a[href]',
      'area[href]',
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
      'summary',
      'iframe',
      'object',
      'embed',
    ];

    return Array.from(
      element.querySelectorAll(focusableSelectors.join(', '))
    ).filter((el) => {
      const htmlEl = el as HTMLElement;
      return (
        htmlEl.offsetWidth > 0 ||
        htmlEl.offsetHeight > 0 ||
        htmlEl.getClientRects().length > 0
      );
    }) as HTMLElement[];
  }, []);

  // 获取第一个可聚焦元素
  const getFirstFocusableElement = useCallback(
    (element: HTMLElement) => {
      const focusable = getFocusableElements(element);
      return focusable.length > 0 ? focusable[0] : null;
    },
    [getFocusableElements]
  );

  // 获取最后一个可聚焦元素
  const getLastFocusableElement = useCallback(
    (element: HTMLElement) => {
      const focusable = getFocusableElements(element);
      return focusable.length > 0 ? focusable[focusable.length - 1] : null;
    },
    [getFocusableElements]
  );

  // 设置焦点到元素
  const focusElement = useCallback((element: HTMLElement | null) => {
    if (element && typeof element.focus === 'function') {
      // 保存当前滚动位置
      const scrollX = window.pageXOffset;
      const scrollY = window.pageYOffset;

      element.focus();

      // 恢复滚动位置（防止focus导致页面跳动）
      window.scrollTo(scrollX, scrollY);
      return true;
    }
    return false;
  }, []);

  // 设置初始焦点
  const setInitialFocus = useCallback(() => {
    if (containerRef.current) {
      // 保存当前焦点以便后续恢复
      previousFocusRef.current = document.activeElement as HTMLElement;

      let targetElement: HTMLElement | null = null;

      if (initialFocus) {
        // 尝试通过选择器找到初始焦点元素
        targetElement = containerRef.current.querySelector(initialFocus) as HTMLElement;
      }

      if (!targetElement) {
        // 尝试找到第一个可聚焦元素
        targetElement = getFirstFocusableElement(containerRef.current);
      }

      if (targetElement) {
        focusElement(targetElement);
      }
    }
  }, [initialFocus, getFirstFocusableElement, focusElement]);

  // 恢复焦点
  const restoreFocusToPrevious = useCallback(() => {
    let targetElement: HTMLElement | null = null;

    if (restoreFocus) {
      targetElement = restoreFocus;
    } else if (previousFocusRef.current) {
      targetElement = previousFocusRef.current;
    }

    if (targetElement && document.contains(targetElement)) {
      focusElement(targetElement);
    }

    previousFocusRef.current = null;
  }, [restoreFocus, focusElement]);

  // 处理Tab键循环导航
  const handleTabKey = useCallback((e: KeyboardEvent) => {
    if (e.key !== 'Tab' || disableTabNavigation || !containerRef.current) {
      return;
    }

    const focusableElements = getFocusableElements(containerRef.current);

    if (focusableElements.length === 0) {
      return;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Shift + Tab
    if (e.shiftKey) {
      if (document.activeElement === firstElement && cycleNavigation) {
        e.preventDefault();
        focusElement(lastElement);
      }
    }
    // Tab
    else {
      if (document.activeElement === lastElement && cycleNavigation) {
        e.preventDefault();
        focusElement(firstElement);
      }
    }
  }, [disableTabNavigation, cycleNavigation, getFocusableElements, focusElement]);

  // 处理Escape键恢复焦点
  const handleEscapeKey = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      restoreFocusToPrevious();
    }
  }, [restoreFocusToPrevious]);

  // 设置键盘事件监听
  const setupKeyboardListeners = useCallback(() => {
    if (containerRef.current && !disableTabNavigation) {
      containerRef.current.addEventListener('keydown', handleTabKey);
      document.addEventListener('keydown', handleEscapeKey);

      return () => {
        if (containerRef.current) {
          containerRef.current.removeEventListener('keydown', handleTabKey);
        }
        document.removeEventListener('keydown', handleEscapeKey);
      };
    }
    return () => {};
  }, [handleTabKey, handleEscapeKey, disableTabNavigation]);

  // 自动设置初始焦点和监听器
  useEffect(() => {
    const cleanup = setupKeyboardListeners();

    // 延迟设置初始焦点，确保DOM完全渲染
    const timer = setTimeout(() => {
      setInitialFocus();
    }, 0);

    return () => {
      clearTimeout(timer);
      cleanup();
    };
  }, [setupKeyboardListeners, setInitialFocus]);

  return {
    // 方法
    focusElement,
    setInitialFocus,
    restoreFocusToPrevious,
    getFocusableElements,
    getFirstFocusableElement,
    getLastFocusableElement,

    // 属性
    focusableElements: containerRef.current ? getFocusableElements(containerRef.current) : [],
    previousFocus: previousFocusRef.current,

    // 用于元素引用的属性
    ref: containerRef,
  };
};

/**
 * 键盘导航Hook
 */
export const useKeyboardNavigation = (
  options: {
    /** Enter键回调 */
    onEnter?: (e: KeyboardEvent) => void;
    /** Space键回调 */
    onSpace?: (e: KeyboardEvent) => void;
    /** Escape键回调 */
    onEscape?: (e: KeyboardEvent) => void;
    /** Arrow键回调 */
    onArrow?: (direction: 'up' | 'down' | 'left' | 'right', e: KeyboardEvent) => void;
    /** 自定义键处理器 */
    onKeyDown?: (e: KeyboardEvent) => void;
    /** 是否阻止默认行为 */
    preventDefault?: boolean;
  } = {}
) => {
  const {
    onEnter,
    onSpace,
    onEscape,
    onArrow,
    onKeyDown,
    preventDefault = true,
  } = options;

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    let handled = false;

    switch (e.key) {
      case 'Enter':
        if (onEnter) {
          if (preventDefault) e.preventDefault();
          onEnter(e);
          handled = true;
        }
        break;

      case ' ':
        if (onSpace) {
          if (preventDefault) e.preventDefault();
          onSpace(e);
          handled = true;
        }
        break;

      case 'Escape':
        if (onEscape) {
          if (preventDefault) e.preventDefault();
          onEscape(e);
          handled = true;
        }
        break;

      case 'ArrowUp':
        if (onArrow) {
          if (preventDefault) e.preventDefault();
          onArrow('up', e);
          handled = true;
        }
        break;

      case 'ArrowDown':
        if (onArrow) {
          if (preventDefault) e.preventDefault();
          onArrow('down', e);
          handled = true;
        }
        break;

      case 'ArrowLeft':
        if (onArrow) {
          if (preventDefault) e.preventDefault();
          onArrow('left', e);
          handled = true;
        }
        break;

      case 'ArrowRight':
        if (onArrow) {
          if (preventDefault) e.preventDefault();
          onArrow('right', e);
          handled = true;
        }
        break;
    }

    if (!handled && onKeyDown) {
      onKeyDown(e);
    }
  }, [onEnter, onSpace, onEscape, onArrow, onKeyDown, preventDefault]);

  return {
    handleKeyDown,
    keyDownProps: {
      onKeyDown: handleKeyDown,
    },
  };
};