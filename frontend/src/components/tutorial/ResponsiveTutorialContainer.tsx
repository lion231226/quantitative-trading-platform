'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Monitor,
  Tablet,
  Smartphone,
  Maximize2,
  Minimize2,
  RotateCw,
  Eye,
  EyeOff,
  Settings,
  X
} from 'lucide-react';

// 响应式断点
const BREAKPOINTS = {
  mobile: 480,
  tablet: 768,
  desktop: 1024,
  large: 1440,
};

// 设备类型
type DeviceType = 'mobile' | 'tablet' | 'desktop' | 'large';

// 视口方向
type Orientation = 'portrait' | 'landscape';

// 布局模式
type LayoutMode = 'compact' | 'standard' | 'spacious' | 'adaptive';

// 触摸模式
type TouchMode = 'touch' | 'mouse' | 'hybrid';

interface ResponsiveConfig {
  deviceType: DeviceType;
  orientation: Orientation;
  screenWidth: number;
  screenHeight: number;
  touchEnabled: boolean;
  touchMode: TouchMode;
  layoutMode: LayoutMode;
  fontSize: 'small' | 'medium' | 'large';
  spacing: 'compact' | 'normal' | 'relaxed';
  animations: boolean;
  reducedMotion: boolean;
  highDensity: boolean;
}

interface ResponsiveTutorialContainerProps {
  children: React.ReactNode;
  /** 自定义断点配置 */
  customBreakpoints?: Partial<typeof BREAKPOINTS>;
  /** 是否显示响应式控制面板 */
  showControls?: boolean;
  /** 是否启用自动布局调整 */
  autoLayout?: boolean;
  /** 布局模式变更回调 */
  onLayoutChange?: (config: ResponsiveConfig) => void;
  /** 自定义样式类名 */
  className?: string;
  /** 最小高度 */
  minHeight?: string;
  /** 最大宽度 */
  maxWidth?: string;
}

const ResponsiveTutorialContainer: React.FC<ResponsiveTutorialContainerProps> = ({
  children,
  customBreakpoints = {},
  showControls = true,
  autoLayout = true,
  onLayoutChange,
  className = '',
  minHeight = '400px',
  maxWidth = '100%',
}) => {
  const [config, setConfig] = useState<ResponsiveConfig>({
    deviceType: 'desktop',
    orientation: 'landscape',
    screenWidth: 1024,
    screenHeight: 768,
    touchEnabled: false,
    touchMode: 'mouse',
    layoutMode: 'adaptive',
    fontSize: 'medium',
    spacing: 'normal',
    animations: true,
    reducedMotion: false,
    highDensity: false,
  });

  const [isControlsOpen, setIsControlsOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

  // 合并自定义断点
  const breakpoints = { ...BREAKPOINTS, ...customBreakpoints };

  // 检测设备类型
  const detectDeviceType = useCallback((width: number): DeviceType => {
    if (width < breakpoints.mobile) return 'mobile';
    if (width < breakpoints.tablet) return 'tablet';
    if (width < breakpoints.desktop) return 'desktop';
    return 'large';
  }, [breakpoints]);

  // 检测屏幕方向
  const detectOrientation = useCallback((width: number, height: number): Orientation => {
    return width > height ? 'landscape' : 'portrait';
  }, []);

  // 检测触摸能力
  const detectTouchCapabilities = useCallback((): { enabled: boolean; mode: TouchMode } => {
    const touchEnabled = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    const touchMode: TouchMode = touchEnabled ?
      (window.matchMedia('(pointer: coarse)').matches ? 'touch' : 'hybrid') : 'mouse';

    return { enabled: touchEnabled, mode: touchMode };
  }, []);

  // 计算最佳布局模式
  const calculateOptimalLayout = useCallback((
    deviceType: DeviceType,
    orientation: Orientation,
    touchMode: TouchMode
  ): LayoutMode => {
    if (!autoLayout) return config.layoutMode;

    // 移动设备优先使用紧凑布局
    if (deviceType === 'mobile') {
      return orientation === 'portrait' ? 'compact' : 'standard';
    }

    // 平板设备根据方向和触摸模式调整
    if (deviceType === 'tablet') {
      if (touchMode === 'touch') {
        return orientation === 'landscape' ? 'standard' : 'compact';
      }
      return 'standard';
    }

    // 桌面设备使用标准或宽松布局
    if (deviceType === 'desktop') {
      return 'standard';
    }

    // 大屏设备使用宽松布局
    return 'spacious';
  }, [autoLayout, config.layoutMode]);

  // 计算最佳字体大小
  const calculateOptimalFontSize = useCallback((
    deviceType: DeviceType,
    screenWidth: number
  ): 'small' | 'medium' | 'large' => {
    if (deviceType === 'mobile') return 'small';
    if (deviceType === 'tablet') return screenWidth < 900 ? 'small' : 'medium';
    if (deviceType === 'large') return 'large';
    return 'medium';
  }, []);

  // 计算最佳间距
  const calculateOptimalSpacing = useCallback((
    deviceType: DeviceType,
    layoutMode: LayoutMode
  ): 'compact' | 'normal' | 'relaxed' => {
    if (deviceType === 'mobile') return 'compact';
    if (layoutMode === 'spacious') return 'relaxed';
    if (layoutMode === 'compact') return 'compact';
    return 'normal';
  }, []);

  // 更新响应式配置
  const updateConfig = useCallback(() => {
    if (!containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const screenWidth = window.innerWidth;
    const screenHeight = window.innerHeight;

    const deviceType = detectDeviceType(screenWidth);
    const orientation = detectOrientation(screenWidth, screenHeight);
    const { enabled: touchEnabled, mode: touchMode } = detectTouchCapabilities();
    const layoutMode = calculateOptimalLayout(deviceType, orientation, touchMode);
    const fontSize = calculateOptimalFontSize(deviceType, screenWidth);
    const spacing = calculateOptimalSpacing(deviceType, layoutMode);

    // 检测用户偏好
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const prefersHighDensity = window.matchMedia('(resolution: 2dppx)').matches;

    const newConfig: ResponsiveConfig = {
      deviceType,
      orientation,
      screenWidth,
      screenHeight,
      touchEnabled,
      touchMode,
      layoutMode,
      fontSize,
      spacing,
      animations: !prefersReducedMotion,
      reducedMotion: prefersReducedMotion,
      highDensity: prefersHighDensity,
    };

    setConfig(newConfig);
    onLayoutChange?.(newConfig);

    // 应用CSS自定义属性
    const root = document.documentElement;
    root.style.setProperty('--device-type', deviceType);
    root.style.setProperty('--orientation', orientation);
    root.style.setProperty('--touch-mode', touchMode);
    root.style.setProperty('--layout-mode', layoutMode);
    root.style.setProperty('--font-size', fontSize);
    root.style.setProperty('--spacing', spacing);
  }, [
    detectDeviceType,
    detectOrientation,
    detectTouchCapabilities,
    calculateOptimalLayout,
    calculateOptimalFontSize,
    calculateOptimalSpacing,
    onLayoutChange,
  ]);

  // 初始化和事件监听
  useEffect(() => {
    updateConfig();

    // 监听窗口大小变化
    const handleResize = () => {
      updateConfig();
    };

    // 监听屏幕方向变化
    const handleOrientationChange = () => {
      setTimeout(updateConfig, 100); // 延迟更新以获得正确的尺寸
    };

    // 监听媒体查询变化
    const mediaQueries = [
      window.matchMedia('(prefers-reduced-motion: reduce)'),
      window.matchMedia('(pointer: coarse)'),
      window.matchMedia('(resolution: 2dppx)'),
    ];

    mediaQueries.forEach(mq => {
      mq.addEventListener('change', updateConfig);
    });

    window.addEventListener('resize', handleResize);
    window.addEventListener('orientationchange', handleOrientationChange);

    // 设置ResizeObserver监听容器大小变化
    if (containerRef.current && window.ResizeObserver) {
      resizeObserverRef.current = new ResizeObserver(updateConfig);
      resizeObserverRef.current.observe(containerRef.current);
    }

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleOrientationChange);

      mediaQueries.forEach(mq => {
        mq.removeEventListener('change', updateConfig);
      });

      if (resizeObserverRef.current) {
        resizeObserverRef.current.disconnect();
      }
    };
  }, [updateConfig]);

  // 全屏切换
  const toggleFullscreen = useCallback(async () => {
    if (!document.fullscreenElement) {
      try {
        await containerRef.current?.requestFullscreen();
        setIsFullscreen(true);
      } catch (error) {
        console.warn('Failed to enter fullscreen:', error);
      }
    } else {
      try {
        await document.exitFullscreen();
        setIsFullscreen(false);
      } catch (error) {
        console.warn('Failed to exit fullscreen:', error);
      }
    }
  }, []);

  // 生成响应式样式类
  const getResponsiveClasses = useCallback(() => {
    const baseClasses = [
      'responsive-tutorial-container',
      `device-${config.deviceType}`,
      `orientation-${config.orientation}`,
      `layout-${config.layoutMode}`,
      `font-${config.fontSize}`,
      `spacing-${config.spacing}`,
      `touch-${config.touchMode}`,
    ];

    if (config.animations) {
      baseClasses.push('animations-enabled');
    }

    if (config.reducedMotion) {
      baseClasses.push('reduced-motion');
    }

    if (config.highDensity) {
      baseClasses.push('high-density');
    }

    if (config.touchEnabled) {
      baseClasses.push('touch-enabled');
    }

    return baseClasses.join(' ');
  }, [config]);

  // 渲染控制面板
  const renderControls = () => {
    if (!showControls) return null;

    return (
      <div className={`fixed top-4 right-4 z-50 transition-all duration-300 ${
        isControlsOpen ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-2'
      }`}>
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4 min-w-[280px]">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900 dark:text-white">响应式控制</h3>
            <button
              onClick={() => setIsControlsOpen(false)}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Device Info */}
          <div className="space-y-3 mb-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">设备类型</span>
              <div className="flex items-center gap-1">
                {config.deviceType === 'mobile' && <Smartphone className="w-4 h-4" />}
                {config.deviceType === 'tablet' && <Tablet className="w-4 h-4" />}
                {config.deviceType === 'desktop' && <Monitor className="w-4 h-4" />}
                {config.deviceType === 'large' && <Monitor className="w-4 h-4" />}
                <span className="font-medium text-gray-900 dark:text-white">
                  {config.deviceType === 'mobile' ? '手机' :
                   config.deviceType === 'tablet' ? '平板' :
                   config.deviceType === 'desktop' ? '桌面' : '大屏'}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">屏幕尺寸</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {config.screenWidth} × {config.screenHeight}
              </span>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">方向</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {config.orientation === 'portrait' ? '竖屏' : '横屏'}
              </span>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">触摸模式</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {config.touchMode === 'touch' ? '触摸' :
                 config.touchMode === 'mouse' ? '鼠标' : '混合'}
              </span>
            </div>
          </div>

          {/* Layout Controls */}
          <div className="space-y-3 border-t border-gray-200 dark:border-gray-700 pt-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">布局模式</span>
              <select
                value={config.layoutMode}
                onChange={(e) => setConfig(prev => ({
                  ...prev,
                  layoutMode: e.target.value as LayoutMode
                }))}
                className="px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="compact">紧凑</option>
                <option value="standard">标准</option>
                <option value="spacious">宽松</option>
                <option value="adaptive">自适应</option>
              </select>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">字体大小</span>
              <select
                value={config.fontSize}
                onChange={(e) => setConfig(prev => ({
                  ...prev,
                  fontSize: e.target.value as 'small' | 'medium' | 'large'
                }))}
                className="px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="small">小</option>
                <option value="medium">中</option>
                <option value="large">大</option>
              </select>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">间距</span>
              <select
                value={config.spacing}
                onChange={(e) => setConfig(prev => ({
                  ...prev,
                  spacing: e.target.value as 'compact' | 'normal' | 'relaxed'
                }))}
                className="px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="compact">紧凑</option>
                <option value="normal">正常</option>
                <option value="relaxed">宽松</option>
              </select>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">动画</span>
              <button
                onClick={() => setConfig(prev => ({
                  ...prev,
                  animations: !prev.animations
                }))}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                  config.animations ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                    config.animations ? 'translate-x-5' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={toggleFullscreen}
              className="flex-1 flex items-center justify-center gap-1 px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            >
              {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              {isFullscreen ? '退出全屏' : '全屏'}
            </button>
            <button
              onClick={updateConfig}
              className="flex items-center justify-center px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              <RotateCw className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="relative">
      {/* Control Toggle Button */}
      {showControls && (
        <button
          onClick={() => setIsControlsOpen(!isControlsOpen)}
          className={`fixed top-4 right-4 z-40 p-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 transition-all duration-300 ${
            isControlsOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'
          }`}
        >
          <Settings className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        </button>
      )}

      {/* Controls Panel */}
      {renderControls()}

      {/* Main Container */}
      <div
        ref={containerRef}
        className={`tutorial-container ${getResponsiveClasses()} ${className}`}
        style={{
          minHeight,
          maxWidth,
          width: '100%',
          position: 'relative',
        }}
      >
        {/* Responsive CSS Variables */}
        <style jsx>{`
          .tutorial-container {
            --container-width: ${config.screenWidth}px;
            --container-height: ${config.screenHeight}px;
            --scale-factor: ${Math.min(config.screenWidth / 1920, 1)};

            /* Font size variables */
            --font-size-xs: ${config.fontSize === 'small' ? '0.75rem' :
                             config.fontSize === 'large' ? '0.875rem' : '0.8125rem'};
            --font-size-sm: ${config.fontSize === 'small' ? '0.875rem' :
                             config.fontSize === 'large' ? '1rem' : '0.9375rem'};
            --font-size-base: ${config.fontSize === 'small' ? '1rem' :
                               config.fontSize === 'large' ? '1.125rem' : '1.0625rem'};
            --font-size-lg: ${config.fontSize === 'small' ? '1.125rem' :
                             config.fontSize === 'large' ? '1.25rem' : '1.1875rem'};
            --font-size-xl: ${config.fontSize === 'small' ? '1.25rem' :
                             config.fontSize === 'large' ? '1.5rem' : '1.375rem'};

            /* Spacing variables */
            --spacing-xs: ${config.spacing === 'compact' ? '0.25rem' :
                          config.spacing === 'relaxed' ? '0.5rem' : '0.375rem'};
            --spacing-sm: ${config.spacing === 'compact' ? '0.5rem' :
                          config.spacing === 'relaxed' ? '1rem' : '0.75rem'};
            --spacing-md: ${config.spacing === 'compact' ? '0.75rem' :
                          config.spacing === 'relaxed' ? '1.5rem' : '1rem'};
            --spacing-lg: ${config.spacing === 'compact' ? '1rem' :
                          config.spacing === 'relaxed' ? '2rem' : '1.5rem'};
            --spacing-xl: ${config.spacing === 'compact' ? '1.5rem' :
                          config.spacing === 'relaxed' ? '3rem' : '2rem'};

            /* Animation variables */
            --animation-duration: ${config.reducedMotion ? '0.01ms' : '300ms'};
            --animation-easing: cubic-bezier(0.4, 0, 0.2, 1);
            --animation-stagger: ${config.reducedMotion ? '0ms' : '100ms'};
          }

          /* Device-specific styles */
          .device-mobile {
            --container-padding: var(--spacing-sm);
            --grid-columns: 1;
            --card-max-width: 100%;
          }

          .device-tablet {
            --container-padding: var(--spacing-md);
            --grid-columns: 2;
            --card-max-width: 400px;
          }

          .device-desktop {
            --container-padding: var(--spacing-lg);
            --grid-columns: 3;
            --card-max-width: 450px;
          }

          .device-large {
            --container-padding: var(--spacing-xl);
            --grid-columns: 4;
            --card-max-width: 500px;
          }

          /* Layout mode styles */
          .layout-compact {
            --component-gap: var(--spacing-sm);
            --card-padding: var(--spacing-md);
          }

          .layout-standard {
            --component-gap: var(--spacing-md);
            --card-padding: var(--spacing-lg);
          }

          .layout-spacious {
            --component-gap: var(--spacing-lg);
            --card-padding: var(--spacing-xl);
          }

          /* Touch-specific styles */
          .touch-enabled.touch-touch {
            --min-touch-target: 44px;
            --border-radius: 8px;
          }

          .touch-enabled.touch-mouse,
          .touch-enabled.touch-hybrid {
            --min-touch-target: 32px;
            --border-radius: 6px;
          }

          /* Animation classes */
          .animations-enabled * {
            transition: all var(--animation-duration) var(--animation-easing);
          }

          .reduced-motion * {
            animation-duration: 0.01ms !important;
            transition-duration: 0.01ms !important;
          }

          /* High density styles */
          .high-density {
            --border-width: 0.5px;
            --shadow-size: 2px;
          }

          /* Orientation-specific styles */
          .orientation-portrait {
            --stack-direction: column;
          }

          .orientation-landscape {
            --stack-direction: row;
          }
        `}</style>

        {/* Content */}
        <div className="tutorial-content w-full h-full">
          {children}
        </div>

        {/* Responsive Indicator (for development) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="fixed bottom-4 left-4 bg-black/75 text-white text-xs px-2 py-1 rounded z-50">
            {config.deviceType} • {config.orientation} • {config.screenWidth}×{config.screenHeight}
          </div>
        )}
      </div>
    </div>
  );
};

export default ResponsiveTutorialContainer;