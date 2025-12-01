/**
 * 屏幕阅读器通知组件
 * 用于向屏幕阅读器播报动态内容更新
 */

import React, { useEffect, useRef } from 'react';

export interface ScreenReaderAnnouncerProps {
  /** 要播报的消息 */
  message: string;
  /** 播报策略：polite（礼貌）或 assertive（紧急） */
  politeness?: 'polite' | 'assertive';
  /** 消息是否原子性（完整播报） */
  atomic?: boolean;
  /** 消息后是否自动清空 */
  autoClear?: boolean;
  /** 自动清空的延迟时间（毫秒） */
  clearDelay?: number;
}

/**
 * 屏幕阅读器通知组件
 *
 * 提供了一种标准化的方式来向屏幕阅读器用户播报动态内容变化
 *
 * @example
 * ```tsx
 * const [error, setError] = useState('');
 *
 * <ScreenReaderAnnouncer
 *   message={error}
 *   politeness="assertive"
 * />
 * ```
 */
export const ScreenReaderAnnouncer = React.forwardRef<
  HTMLDivElement,
  ScreenReaderAnnouncerProps
>(
  (
    {
      message,
      politeness = 'polite',
      atomic = true,
      autoClear = true,
      clearDelay = 1000,
    },
    ref
  ) => {
    const announcementRef = useRef<HTMLDivElement>(null);

    // 当消息变化时，清空并设置新消息
    useEffect(() => {
      if (!message) return;

      const element = announcementRef.current;
      if (!element) return;

      // 清空当前内容
      element.textContent = '';

      // 设置新消息
      element.textContent = message;

      // 如果需要自动清空
      if (autoClear) {
        const timer = setTimeout(() => {
          element.textContent = '';
        }, clearDelay);

        return () => clearTimeout(timer);
      }
    }, [message, autoClear, clearDelay]);

    return (
      <div
        ref={(node) => {
          announcementRef.current = node;
          if (typeof ref === 'function') {
            ref(node);
          } else if (ref) {
            ref.current = node;
          }
        }}
        aria-live={politeness}
        aria-atomic={atomic}
        className="sr-only"
        style={{
          position: 'absolute',
          width: '1px',
          height: '1px',
          padding: 0,
          margin: '-1px',
          overflow: 'hidden',
          clip: 'rect(0, 0, 0, 0)',
          whiteSpace: 'nowrap',
          borderWidth: 0,
        }}
      />
    );
  }
);

ScreenReaderAnnouncer.displayName = 'ScreenReaderAnnouncer';

/**
 * 用于hook形式的屏幕阅读器通知
 */
export const useScreenReader = () => {
  const announceRef = useRef<{
    politeness?: 'polite' | 'assertive';
    atomic?: boolean;
    autoClear?: boolean;
    clearDelay?: number;
  }>({});

  const setAnnouncerConfig = (config: {
    politeness?: 'polite' | 'assertive';
    atomic?: boolean;
    autoClear?: boolean;
    clearDelay?: number;
  }) => {
    announceRef.current = { ...announceRef.current, ...config };
  };

  const announce = (message: string, options?: {
    politeness?: 'polite' | 'assertive';
    atomic?: boolean;
    autoClear?: boolean;
    clearDelay?: number;
  }) => {
    const config = { ...announceRef.current, ...options };

    // 创建临时DOM元素来播报消息
    const announcer = document.createElement('div');
    announcer.setAttribute('aria-live', config.politeness || 'polite');
    announcer.setAttribute('aria-atomic', (config.atomic !== false).toString());
    announcer.className = 'sr-only';
    announcer.style.cssText = `
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border-width: 0;
    `;

    document.body.appendChild(announcer);

    // 设置消息
    announcer.textContent = message;

    // 自动清理
    if (config.autoClear !== false) {
      setTimeout(() => {
        if (document.body.contains(announcer)) {
          document.body.removeChild(announcer);
        }
      }, config.clearDelay || 1000);
    } else {
      // 不自动清理，手动移除
      setTimeout(() => {
        if (document.body.contains(announcer)) {
          document.body.removeChild(announcer);
        }
      }, 100);
    }
  };

  return {
    announce,
    setAnnouncerConfig,
  };
};

export default ScreenReaderAnnouncer;