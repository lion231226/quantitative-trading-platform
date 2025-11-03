'use client';

import React, { memo, useMemo, useCallback, useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { DeviceInfo, NetworkInfo } from '@/types/ux.types';

// 设备检测Hook
export function useDeviceInfo(): DeviceInfo {
  const [deviceInfo, setDeviceInfo] = useState<DeviceInfo>(() => ({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    userAgent: '',
    screenResolution: '',
    viewportSize: { width: 0, height: 0 },
    pixelRatio: 1,
    touchSupport: false,
    orientation: 'landscape',
  }));

  useEffect(() => {
    const updateDeviceInfo = () => {
      const userAgent = navigator.userAgent.toLowerCase();
      const isMobile = /mobile|android|iphone|ipod|blackberry|iemobile|opera mini/i.test(userAgent);
      const isTablet = /ipad|android(?!.*mobile)/i.test(userAgent);
      const isDesktop = !isMobile && !isTablet;

      setDeviceInfo({
        isMobile,
        isTablet,
        isDesktop,
        userAgent: navigator.userAgent,
        screenResolution: `${screen.width}x${screen.height}`,
        viewportSize: {
          width: window.innerWidth,
          height: window.innerHeight,
        },
        pixelRatio: window.devicePixelRatio || 1,
        touchSupport: 'ontouchstart' in window,
        orientation: window.innerHeight > window.innerWidth ? 'portrait' : 'landscape',
      });
    };

    updateDeviceInfo();

    window.addEventListener('resize', updateDeviceInfo);
    window.addEventListener('orientationchange', updateDeviceInfo);

    return () => {
      window.removeEventListener('resize', updateDeviceInfo);
      window.removeEventListener('orientationchange', updateDeviceInfo);
    };
  }, []);

  return deviceInfo;
}

// 网络状态检测Hook
export function useNetworkInfo(): NetworkInfo {
  const [networkInfo, setNetworkInfo] = useState<NetworkInfo>(() => ({
    online: navigator.onLine,
  }));

  useEffect(() => {
    const updateNetworkInfo = () => {
      const connection = (navigator as any).connection || (navigator as any).mozConnection || (navigator as any).webkitConnection;

      setNetworkInfo({
        effectiveType: connection?.effectiveType,
        downlink: connection?.downlink,
        rtt: connection?.rtt,
        saveData: connection?.saveData,
        online: navigator.onLine,
        connectionType: connection?.type,
      });
    };

    updateNetworkInfo();

    window.addEventListener('online', updateNetworkInfo);
    window.addEventListener('offline', updateNetworkInfo);

    if ((navigator as any).connection && typeof (navigator as any).connection.addEventListener === 'function') {
      (navigator as any).connection.addEventListener('change', updateNetworkInfo);
    }

    return () => {
      window.removeEventListener('online', updateNetworkInfo);
      window.removeEventListener('offline', updateNetworkInfo);
      if ((navigator as any).connection && typeof (navigator as any).connection.removeEventListener === 'function') {
        (navigator as any).connection.removeEventListener('change', updateNetworkInfo);
      }
    };
  }, []);

  return networkInfo;
}

// 响应式Hook
export function useResponsive() {
  const deviceInfo = useDeviceInfo();
  const [screenSize, setScreenSize] = useState<'xs' | 'sm' | 'md' | 'lg' | 'xl'>('lg');

  useEffect(() => {
    const updateScreenSize = () => {
      const width = window.innerWidth;
      if (width < 640) setScreenSize('xs');
      else if (width < 768) setScreenSize('sm');
      else if (width < 1024) setScreenSize('md');
      else if (width < 1280) setScreenSize('lg');
      else setScreenSize('xl');
    };

    updateScreenSize();
    window.addEventListener('resize', updateScreenSize);

    return () => window.removeEventListener('resize', updateScreenSize);
  }, []);

  return {
    ...deviceInfo,
    screenSize,
    isSmallScreen: screenSize === 'xs' || screenSize === 'sm',
    isMediumScreen: screenSize === 'md',
    isLargeScreen: screenSize === 'lg' || screenSize === 'xl',
    breakpoints: {
      xs: 0,
      sm: 640,
      md: 768,
      lg: 1024,
      xl: 1280,
    },
  };
}

// 触摸手势Hook
export function useTouchGestures() {
  const [gestures, setGestures] = useState({
    swipeLeft: false,
    swipeRight: false,
    swipeUp: false,
    swipeDown: false,
    pinch: false,
  });

  const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(null);
  const touchEndRef = useRef<{ x: number; y: number; time: number } | null>(null);

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      const touch = e.touches[0];
      touchStartRef.current = {
        x: touch.clientX,
        y: touch.clientY,
        time: Date.now(),
      };
    }
  }, []);

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    if (e.changedTouches.length === 1 && touchStartRef.current) {
      const touch = e.changedTouches[0];
      touchEndRef.current = {
        x: touch.clientX,
        y: touch.clientY,
        time: Date.now(),
      };

      const deltaX = touchEndRef.current.x - touchStartRef.current.x;
      const deltaY = touchEndRef.current.y - touchStartRef.current.y;
      const deltaTime = touchEndRef.current.time - touchStartRef.current.time;

      const minSwipeDistance = 50;
      const maxSwipeTime = 300;

      if (Math.abs(deltaX) > minSwipeDistance && deltaTime < maxSwipeTime) {
        if (deltaX > 0) {
          setGestures(prev => ({ ...prev, swipeRight: true }));
          setTimeout(() => setGestures(prev => ({ ...prev, swipeRight: false })), 100);
        } else {
          setGestures(prev => ({ ...prev, swipeLeft: true }));
          setTimeout(() => setGestures(prev => ({ ...prev, swipeLeft: false })), 100);
        }
      }

      if (Math.abs(deltaY) > minSwipeDistance && deltaTime < maxSwipeTime) {
        if (deltaY > 0) {
          setGestures(prev => ({ ...prev, swipeDown: true }));
          setTimeout(() => setGestures(prev => ({ ...prev, swipeDown: false })), 100);
        } else {
          setGestures(prev => ({ ...prev, swipeUp: true }));
          setTimeout(() => setGestures(prev => ({ ...prev, swipeUp: false })), 100);
        }
      }
    }
  }, []);

  return {
    gestures,
    handleTouchStart,
    handleTouchEnd,
  };
}

// 移动端导航组件
interface MobileNavigationProps {
  items: Array<{
    id: string;
    label: string;
    icon?: React.ReactNode;
    onClick: () => void;
    active?: boolean;
  }>;
  className?: string;
}

export const MobileNavigation = memo<MobileNavigationProps>(({
  items,
  className,
}) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { isSmallScreen } = useResponsive();

  if (!isSmallScreen) {
    return null;
  }

  return (
    <>
      {/* 底部导航栏 */}
      <div className={cn(
        'fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50',
        className
      )}>
        <div className="flex justify-around items-center py-2">
          {items.slice(0, 5).map(item => (
            <Button
              key={item.id}
              variant={item.active ? 'default' : 'ghost'}
              size="sm"
              onClick={item.onClick}
              className="flex flex-col items-center gap-1 h-auto py-2 px-3"
            >
              {item.icon && <span className="text-lg">{item.icon}</span>}
              <span className="text-xs">{item.label}</span>
            </Button>
          ))}
        </div>
      </div>

      {/* 菜单按钮（如果项目超过5个） */}
      {items.length > 5 && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsMenuOpen(true)}
          className="fixed bottom-20 right-4 rounded-full w-12 h-12 z-50"
        >
          📋
        </Button>
      )}

      {/* 侧边菜单 */}
      {isMenuOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50">
          <div className="fixed right-0 top-0 h-full w-64 bg-white shadow-lg">
            <div className="p-4 border-b">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold">更多功能</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsMenuOpen(false)}
                >
                  ✕
                </Button>
              </div>
            </div>
            <div className="p-2">
              {items.slice(5).map(item => (
                <Button
                  key={item.id}
                  variant={item.active ? 'default' : 'ghost'}
                  onClick={() => {
                    item.onClick();
                    setIsMenuOpen(false);
                  }}
                  className="w-full justify-start mb-2"
                >
                  {item.icon && <span className="mr-2">{item.icon}</span>}
                  {item.label}
                </Button>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
});

MobileNavigation.displayName = 'MobileNavigation';

// 移动端优化容器组件
interface MobileContainerProps {
  children: React.ReactNode;
  className?: string;
  enableSwipeGestures?: boolean;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
}

export const MobileContainer = memo<MobileContainerProps>(({
  children,
  className,
  enableSwipeGestures = false,
  onSwipeLeft,
  onSwipeRight,
  onSwipeUp,
  onSwipeDown,
}) => {
  const { isSmallScreen } = useResponsive();
  const { gestures, handleTouchStart, handleTouchEnd } = useTouchGestures();

  useEffect(() => {
    if (enableSwipeGestures && isSmallScreen) {
      if (gestures.swipeLeft && onSwipeLeft) onSwipeLeft();
      if (gestures.swipeRight && onSwipeRight) onSwipeRight();
      if (gestures.swipeUp && onSwipeUp) onSwipeUp();
      if (gestures.swipeDown && onSwipeDown) onSwipeDown();
    }
  }, [gestures, enableSwipeGestures, isSmallScreen, onSwipeLeft, onSwipeRight, onSwipeUp, onSwipeDown]);

  return (
    <div
      className={cn(
        'relative',
        isSmallScreen && 'touch-pan-y',
        className
      )}
      onTouchStart={enableSwipeGestures && isSmallScreen ? handleTouchStart : undefined}
      onTouchEnd={enableSwipeGestures && isSmallScreen ? handleTouchEnd : undefined}
    >
      {children}

      {/* 移动端底部安全区域 */}
      {isSmallScreen && (
        <div className="h-safe-bottom" style={{ paddingBottom: 'env(safe-area-inset-bottom, 20px)' }} />
      )}
    </div>
  );
});

MobileContainer.displayName = 'MobileContainer';

// 移动端优化的图表容器
interface MobileChartContainerProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}

export const MobileChartContainer = memo<MobileChartContainerProps>(({
  children,
  title,
  description,
  actions,
  className,
}) => {
  const { isSmallScreen } = useResponsive();

  return (
    <Card className={cn('p-4', className)}>
      {(title || description || actions) && (
        <div className={cn(
          'mb-4',
          isSmallScreen ? 'space-y-2' : 'flex justify-between items-center'
        )}>
          <div className={isSmallScreen ? 'w-full' : 'flex-1'}>
            {title && (
              <h3 className={cn(
                'font-semibold',
                isSmallScreen ? 'text-base' : 'text-lg'
              )}>
                {title}
              </h3>
            )}
            {description && (
              <p className={cn(
                'text-gray-600',
                isSmallScreen ? 'text-sm mt-1' : 'text-sm'
              )}>
                {description}
              </p>
            )}
          </div>
          {actions && (
            <div className={cn(
              'flex gap-2',
              isSmallScreen ? 'w-full justify-end' : 'flex-shrink-0'
            )}>
              {actions}
            </div>
          )}
        </div>
      )}

      <div className={cn(
        'relative',
        isSmallScreen ? 'h-64' : 'h-80'
      )}>
        {children}
      </div>
    </Card>
  );
});

MobileChartContainer.displayName = 'MobileChartContainer';

// 移动端优化的表格组件
interface MobileTableProps<T> {
  data: T[];
  columns: Array<{
    key: keyof T;
    title: string;
    render?: (value: any, record: T) => React.ReactNode;
    mobileOnly?: boolean;
  }>;
  className?: string;
}

export function MobileTable<T extends Record<string, any>>({
  data,
  columns,
  className,
}: MobileTableProps<T>) {
  const { isSmallScreen } = useResponsive();

  if (isSmallScreen) {
    // 移动端使用卡片式布局
    return (
      <div className={cn('space-y-4', className)}>
        {data.map((record, index) => (
          <Card key={index} className="p-4">
            <div className="space-y-3">
              {columns.map(column => (
                <div key={String(column.key)} className="flex justify-between items-center">
                  <span className="text-sm font-medium text-gray-600">
                    {column.title}
                  </span>
                  <span className="text-sm text-right flex-1 ml-4">
                    {column.render ? column.render(record[column.key], record) : record[column.key]}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
    );
  }

  // 桌面端使用传统表格
  return (
    <div className={cn('overflow-x-auto', className)}>
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b">
            {columns.map(column => (
              <th key={String(column.key)} className="text-left p-3 font-medium">
                {column.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((record, index) => (
            <tr key={index} className="border-b hover:bg-gray-50">
              {columns.map(column => (
                <td key={String(column.key)} className="p-3">
                  {column.render ? column.render(record[column.key], record) : record[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// 移动端优化的表单组件
interface MobileFormProps {
  children: React.ReactNode;
  className?: string;
  fullWidth?: boolean;
}

export const MobileForm = memo<MobileFormProps>(({
  children,
  className,
  fullWidth = false,
}) => {
  const { isSmallScreen } = useResponsive();

  return (
    <form className={cn(
      'space-y-4',
      isSmallScreen && 'px-4',
      fullWidth && isSmallScreen && 'w-full',
      className
    )}>
      {children}
    </form>
  );
});

MobileForm.displayName = 'MobileForm';

// 移动端状态指示器组件
interface MobileStatusBarProps {
  networkInfo: NetworkInfo;
  className?: string;
}

export const MobileStatusBar = memo<MobileStatusBarProps>(({
  networkInfo,
  className,
}) => {
  const { isSmallScreen } = useResponsive();

  if (!isSmallScreen) return null;

  const getNetworkIcon = () => {
    if (!networkInfo.online) return '📵';
    switch (networkInfo.effectiveType) {
      case 'slow-2g':
      case '2g':
        return '📶';
      case '3g':
        return '📡';
      case '4g':
        return '📶';
      default:
        return '🌐';
    }
  };

  const getNetworkColor = () => {
    if (!networkInfo.online) return 'text-red-500';
    switch (networkInfo.effectiveType) {
      case 'slow-2g':
      case '2g':
        return 'text-orange-500';
      case '3g':
        return 'text-yellow-500';
      case '4g':
        return 'text-green-500';
      default:
        return 'text-blue-500';
    }
  };

  return (
    <div className={cn(
      'fixed top-0 left-0 right-0 bg-white border-b border-gray-200 px-4 py-1 z-40',
      'flex justify-between items-center text-xs',
      className
    )}>
      <div className="flex items-center gap-2">
        <span className={getNetworkColor()}>{getNetworkIcon()}</span>
        <span className="text-gray-600">
          {networkInfo.online ? networkInfo.effectiveType?.toUpperCase() || 'ONLINE' : 'OFFLINE'}
        </span>
      </div>
      <div className="text-gray-500">
        {new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
      </div>
    </div>
  );
});

MobileStatusBar.displayName = 'MobileStatusBar';

// 响应式布局组件
interface ResponsiveLayoutProps {
  children: React.ReactNode;
  sidebar?: React.ReactNode;
  header?: React.ReactNode;
  className?: string;
}

export const ResponsiveLayout = memo<ResponsiveLayoutProps>(({
  children,
  sidebar,
  header,
  className,
}) => {
  const { isSmallScreen } = useResponsive();

  if (isSmallScreen) {
    return (
      <MobileContainer className={className}>
        {header && <div className="sticky top-0 z-30 bg-white">{header}</div>}
        <div className="flex-1">
          {sidebar && (
            <div className="mb-4">
              {sidebar}
            </div>
          )}
          <div className="px-4 pb-20">
            {children}
          </div>
        </div>
      </MobileContainer>
    );
  }

  return (
    <div className={cn('flex h-full', className)}>
      {sidebar && (
        <div className="w-64 border-r border-gray-200 flex-shrink-0">
          {sidebar}
        </div>
      )}
      <div className="flex-1 flex flex-col">
        {header && (
          <div className="border-b border-gray-200 flex-shrink-0">
            {header}
          </div>
        )}
        <div className="flex-1 overflow-auto">
          {children}
        </div>
      </div>
    </div>
  );
});

ResponsiveLayout.displayName = 'ResponsiveLayout';

export default {
  useDeviceInfo,
  useNetworkInfo,
  useResponsive,
  useTouchGestures,
  MobileNavigation,
  MobileContainer,
  MobileChartContainer,
  MobileTable,
  MobileForm,
  MobileStatusBar,
  ResponsiveLayout,
};