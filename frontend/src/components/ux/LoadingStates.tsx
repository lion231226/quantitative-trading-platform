'use client';

import React, { memo, useCallback, useEffect, useMemo, useRef } from 'react';
import { cn } from '@/lib/utils';

// 性能优化的骨架屏组件
interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  width?: string | number;
  height?: string | number;
  lines?: number; // 用于文本骨架屏
  animation?: 'pulse' | 'wave' | 'none';
}

export const Skeleton = memo<SkeletonProps>(
  ({
    className,
    variant = 'text',
    width,
    height,
    lines = 1,
    animation = 'pulse',
  }) => {
    const animationClass = useMemo(() => {
      switch (animation) {
        case 'pulse':
          return 'animate-pulse';
        case 'wave':
          return 'animate-shimmer';
        case 'none':
          return '';
        default:
          return 'animate-pulse';
      }
    }, [animation]);

    const variantClass = useMemo(() => {
      switch (variant) {
        case 'text':
          return 'h-4 bg-gray-200 rounded';
        case 'circular':
          return 'rounded-full bg-gray-200';
        case 'rectangular':
          return 'bg-gray-200';
        case 'rounded':
          return 'rounded-lg bg-gray-200';
        default:
          return 'h-4 bg-gray-200 rounded';
      }
    }, [variant]);

    const style = useMemo(
      () => ({
        width: width || '100%',
        height: height || (variant === 'text' ? '1rem' : '100%'),
      }),
      [width, height, variant],
    );

    if (variant === 'text' && lines > 1) {
      return (
        <div
          className={cn('space-y-2', className)}
          role="status"
          aria-label="loading"
        >
          {Array.from({ length: lines }, (_, i) => (
            <div
              key={i}
              className={cn(
                animationClass,
                variantClass,
                i === lines - 1 ? 'w-3/4' : 'w-full',
              )}
              style={style}
            />
          ))}
        </div>
      );
    }

    return (
      <div
        role="status"
        aria-label="loading"
        className={cn(animationClass, variantClass, className)}
        style={style}
      />
    );
  },
);

Skeleton.displayName = 'Skeleton';

// 性能优化的加载状态组件
interface LoadingStateProps {
  isLoading: boolean;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  skeleton?: React.ReactNode;
  delay?: number; // 延迟显示加载状态，避免闪烁
  minDisplayTime?: number; // 最小显示时间，避免闪烁
}

export const LoadingState = memo<LoadingStateProps>(
  ({
    isLoading,
    children,
    fallback,
    skeleton,
    delay = 200,
    minDisplayTime = 500,
  }) => {
    const [showLoading, setShowLoading] = React.useState(false);
    const loadingStartTime = useRef<number>(0);
    const timeoutRef = useRef<NodeJS.Timeout>();

    useEffect(() => {
      if (isLoading) {
        loadingStartTime.current = Date.now();

        // 延迟显示加载状态
        timeoutRef.current = setTimeout(() => {
          setShowLoading(true);
        }, delay);
      } else {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }

        // 确保最小显示时间
        const loadingDuration = Date.now() - loadingStartTime.current;
        const remainingTime = Math.max(0, minDisplayTime - loadingDuration);

        setTimeout(() => {
          setShowLoading(false);
        }, remainingTime);
      }

      return () => {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
      };
    }, [isLoading, delay, minDisplayTime]);

    if (!isLoading) {
      return <>{children}</>;
    }

    if (!showLoading) {
      return <>{children}</>; // 在延迟期间显示原内容
    }

    if (skeleton) {
      return <>{skeleton}</>;
    }

    if (fallback) {
      return <>{fallback}</>;
    }

    return (
      <div className="flex items-center justify-center p-8">
        <Skeleton
          className="w-full max-w-md"
          height={200}
          variant="rectangular"
        />
      </div>
    );
  },
);

LoadingState.displayName = 'LoadingState';

// 性能优化的懒加载组件
interface LazyLoadProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  rootMargin?: string;
  threshold?: number;
  trigger?: boolean; // 手动触发加载
}

export const LazyLoad = memo<LazyLoadProps>(
  ({
    children,
    fallback,
    rootMargin = '50px',
    threshold = 0.1,
    trigger = false,
  }) => {
    const [isIntersecting, setIsIntersecting] = React.useState(trigger);
    const [hasLoaded, setHasLoaded] = React.useState(trigger);
    const elementRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
      if (trigger || hasLoaded) return;

      const element = elementRef.current;
      if (!element) return;

      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            setIsIntersecting(true);
            setHasLoaded(true);
            observer.disconnect();
          }
        },
        { rootMargin, threshold },
      );

      observer.observe(element);

      return () => {
        observer.disconnect();
      };
    }, [rootMargin, threshold, trigger, hasLoaded]);

    const ref = useCallback((node: HTMLDivElement) => {
      elementRef.current = node;
    }, []);

    return (
      <div ref={ref}>
        {hasLoaded ? (
          children
        ) : fallback ? (
          fallback
        ) : (
          <div className="flex items-center justify-center p-8">
            <Skeleton
              className="w-full max-w-md"
              height={200}
              variant="rectangular"
            />
          </div>
        )}
      </div>
    );
  },
);

LazyLoad.displayName = 'LazyLoad';

// 性能优化的虚拟化列表组件
interface VirtualListProps<T> {
  items: T[];
  itemHeight: number;
  containerHeight: number;
  renderItem: (item: T, index: number) => React.ReactNode;
  overscan?: number; // 预渲染项目数量
  className?: string;
}

export function VirtualList<T>({
  items,
  itemHeight,
  containerHeight,
  renderItem,
  overscan = 5,
  className,
}: VirtualListProps<T>) {
  const [scrollTop, setScrollTop] = React.useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const visibleItems = useMemo(() => {
    const startIndex = Math.max(
      0,
      Math.floor(scrollTop / itemHeight) - overscan,
    );
    const endIndex = Math.min(
      items.length - 1,
      Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan,
    );

    return Array.from(
      { length: endIndex - startIndex + 1 },
      (_, i) => startIndex + i,
    );
  }, [items.length, itemHeight, containerHeight, scrollTop, overscan]);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  }, []);

  const totalHeight = useMemo(
    () => items.length * itemHeight,
    [items.length, itemHeight],
  );

  return (
    <div
      ref={containerRef}
      className={cn('overflow-auto', className)}
      style={{ height: containerHeight }}
      onScroll={handleScroll}
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        {visibleItems.map((index) => (
          <div
            key={index}
            style={{
              position: 'absolute',
              top: index * itemHeight,
              height: itemHeight,
              width: '100%',
            }}
          >
            {renderItem(items[index], index)}
          </div>
        ))}
      </div>
    </div>
  );
}

// 性能监控Hook
export function usePerformanceMonitor(componentName: string) {
  const renderStartTime = useRef<number>(0);
  const renderCount = useRef(0);

  useEffect(() => {
    renderStartTime.current = performance.now();
    renderCount.current += 1;

    return () => {
      const renderTime = performance.now() - renderStartTime.current;

      if (process.env.NODE_ENV === 'development') {
        console.log(
          `[Performance Monitor] ${componentName} - Render #${renderCount.current}: ${renderTime.toFixed(2)}ms`,
        );
      }

      // 发送性能数据到监控服务
      if (renderTime > 100) {
        // 超过100ms的渲染时间记录为警告
        console.warn(
          `[Performance Warning] ${componentName} slow render detected: ${renderTime.toFixed(2)}ms`,
        );
      }
    };
  });

  return {
    renderCount: renderCount.current,
    getRenderTime: () => performance.now() - renderStartTime.current,
  };
}

// 防抖Hook
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = React.useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// 节流Hook
export function useThrottle<T>(value: T, limit: number): T {
  const [throttledValue, setThrottledValue] = React.useState<T>(value);
  const lastRan = useRef(Date.now());

  useEffect(() => {
    const handler = setTimeout(
      () => {
        if (Date.now() - lastRan.current >= limit) {
          setThrottledValue(value);
          lastRan.current = Date.now();
        }
      },
      limit - (Date.now() - lastRan.current),
    );

    return () => {
      clearTimeout(handler);
    };
  }, [value, limit]);

  return throttledValue;
}

export default {
  Skeleton,
  LoadingState,
  LazyLoad,
  VirtualList,
  usePerformanceMonitor,
  useDebounce,
  useThrottle,
};
