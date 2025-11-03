import { ChartConfig, ChartInteractionConfig, PerformanceConfig } from '@/types/chart.types';

// 用户偏好接口
export interface UserChartPreferences {
  // 基础配置
  chartConfig: Partial<ChartConfig>

  // 交互配置
  interactionConfig: Partial<ChartInteractionConfig>

  // 性能配置
  performanceConfig: Partial<PerformanceConfig>

  // 主题配置
  theme: ChartTheme

  // 布局配置
  layout: ChartLayout

  // 导出偏好
  exportPreferences: ExportPreferences

  // 用户信息
  userId?: string
  lastUpdated: string
}

// 图表主题
export interface ChartTheme {
  name: string
  colors: {
    background: string
    grid: string
    text: string
    price: string
    buySignal: string
    sellSignal: string
    movingAverage: string
    volume: string
  }
  fonts: {
    family: string
    size: {
      title: number
      legend: number
      axis: number
      tooltip: number
    }
  }
  styles: {
    lineWidth: number
    pointRadius: number
    gridLines: boolean
    animations: boolean
  }
}

// 图表布局
export interface ChartLayout {
  height: number
  width?: number
  padding: {
    top: number
    right: number
    bottom: number
    left: number
  }
  showControls: boolean
  showLegend: boolean
  showTooltip: boolean
  responsive: boolean
}

// 导出偏好
export interface ExportPreferences {
  defaultFormat: 'png' | 'csv' | 'json'
  defaultFilename: string
  includeMetadata: boolean
  backgroundColor: string
  quality: number
  dimensions: {
    width: number
    height: number
  }
}

// 默认主题
export const DEFAULT_THEMES: Record<string, ChartTheme> = {
  light: {
    name: 'Light',
    colors: {
      background: '#ffffff',
      grid: '#e5e7eb',
      text: '#374151',
      price: '#3b82f6',
      buySignal: '#22c55e',
      sellSignal: '#ef4444',
      movingAverage: '#f59e0b',
      volume: '#6b7280',
    },
    fonts: {
      family: 'Inter, sans-serif',
      size: {
        title: 16,
        legend: 12,
        axis: 11,
        tooltip: 12,
      },
    },
    styles: {
      lineWidth: 2,
      pointRadius: 4,
      gridLines: true,
      animations: true,
    },
  },
  dark: {
    name: 'Dark',
    colors: {
      background: '#1f2937',
      grid: '#374151',
      text: '#f3f4f6',
      price: '#60a5fa',
      buySignal: '#34d399',
      sellSignal: '#f87171',
      movingAverage: '#fbbf24',
      volume: '#9ca3af',
    },
    fonts: {
      family: 'Inter, sans-serif',
      size: {
        title: 16,
        legend: 12,
        axis: 11,
        tooltip: 12,
      },
    },
    styles: {
      lineWidth: 2,
      pointRadius: 4,
      gridLines: true,
      animations: true,
    },
  },
  professional: {
    name: 'Professional',
    colors: {
      background: '#fafafa',
      grid: '#d1d5db',
      text: '#111827',
      price: '#2563eb',
      buySignal: '#059669',
      sellSignal: '#dc2626',
      movingAverage: '#7c3aed',
      volume: '#6b7280',
    },
    fonts: {
      family: 'system-ui, sans-serif',
      size: {
        title: 18,
        legend: 13,
        axis: 12,
        tooltip: 13,
      },
    },
    styles: {
      lineWidth: 1.5,
      pointRadius: 3,
      gridLines: true,
      animations: false,
    },
  },
};

// 默认偏好
export const DEFAULT_PREFERENCES: UserChartPreferences = {
  chartConfig: {
    showSignals: true,
    showMovingAverages: true,
    movingAverageType: 'SMA',
    movingAveragePeriod: 20,
    showVolume: false,
    animationDuration: 1000,
  },
  interactionConfig: {
    enableZoom: true,
    enablePan: true,
    zoomMode: 'x',
    panMode: 'x',
    wheelSensitivity: 0.1,
    enableTooltip: true,
    enableCrosshair: false,
    enableDataLabels: false,
  },
  performanceConfig: {
    enableDataSampling: true,
    maxDataPoints: 1000,
    enableAnimation: true,
    animationDuration: 750,
  },
  theme: DEFAULT_THEMES.light,
  layout: {
    height: 400,
    padding: {
      top: 20,
      right: 20,
      bottom: 20,
      left: 20,
    },
    showControls: true,
    showLegend: true,
    showTooltip: true,
    responsive: true,
  },
  exportPreferences: {
    defaultFormat: 'png',
    defaultFilename: 'chart',
    includeMetadata: true,
    backgroundColor: '#ffffff',
    quality: 0.9,
    dimensions: {
      width: 1200,
      height: 600,
    },
  },
  lastUpdated: new Date().toISOString(),
};

// 用户偏好管理器
export class ChartPreferencesManager {
  private static readonly STORAGE_KEY = 'chart-preferences';
  private preferences: UserChartPreferences;

  constructor(userId?: string) {
    this.preferences = this.loadPreferences(userId);
  }

  // 加载偏好设置
  private loadPreferences(userId?: string): UserChartPreferences {
    try {
      const stored = localStorage.getItem(ChartPreferencesManager.STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);

        // 验证和更新偏好设置
        return this.validateAndUpdatePreferences(parsed, userId);
      }
    } catch (error) {
      console.warn('Failed to load chart preferences:', error);
    }

    // 返回默认偏好
    const defaults = { ...DEFAULT_PREFERENCES };
    if (userId) defaults.userId = userId;
    return defaults;
  }

  // 验证和更新偏好设置
  private validateAndUpdatePreferences(
    stored: any,
    userId?: string,
  ): UserChartPreferences {
    // 确保所有必需的属性都存在
    const validated: UserChartPreferences = {
      ...DEFAULT_PREFERENCES,
      ...stored,
      userId: userId || stored.userId,
      lastUpdated: new Date().toISOString(),
    };

    // 验证主题
    if (!validated.theme || !DEFAULT_THEMES[validated.theme.name]) {
      validated.theme = DEFAULT_THEMES.light;
    }

    // 验证配置
    validated.chartConfig = {
      ...DEFAULT_PREFERENCES.chartConfig,
      ...validated.chartConfig,
    };

    validated.interactionConfig = {
      ...DEFAULT_PREFERENCES.interactionConfig,
      ...validated.interactionConfig,
    };

    validated.performanceConfig = {
      ...DEFAULT_PREFERENCES.performanceConfig,
      ...validated.performanceConfig,
    };

    return validated;
  }

  // 保存偏好设置
  savePreferences(): void {
    try {
      this.preferences.lastUpdated = new Date().toISOString();
      localStorage.setItem(
        ChartPreferencesManager.STORAGE_KEY,
        JSON.stringify(this.preferences),
      );
    } catch (error) {
      console.error('Failed to save chart preferences:', error);
    }
  }

  // 获取偏好设置
  getPreferences(): UserChartPreferences {
    return { ...this.preferences };
  }

  // 更新图表配置
  updateChartConfig(config: Partial<ChartConfig>): void {
    this.preferences.chartConfig = {
      ...this.preferences.chartConfig,
      ...config,
    };
    this.savePreferences();
  }

  // 更新交互配置
  updateInteractionConfig(config: Partial<ChartInteractionConfig>): void {
    this.preferences.interactionConfig = {
      ...this.preferences.interactionConfig,
      ...config,
    };
    this.savePreferences();
  }

  // 更新性能配置
  updatePerformanceConfig(config: Partial<PerformanceConfig>): void {
    this.preferences.performanceConfig = {
      ...this.preferences.performanceConfig,
      ...config,
    };
    this.savePreferences();
  }

  // 更新主题
  updateTheme(themeName: string): void {
    const theme = DEFAULT_THEMES[themeName];
    if (theme) {
      this.preferences.theme = theme;
      this.savePreferences();
    }
  }

  // 更新布局
  updateLayout(layout: Partial<ChartLayout>): void {
    this.preferences.layout = {
      ...this.preferences.layout,
      ...layout,
    };
    this.savePreferences();
  }

  // 更新导出偏好
  updateExportPreferences(preferences: Partial<ExportPreferences>): void {
    this.preferences.exportPreferences = {
      ...this.preferences.exportPreferences,
      ...preferences,
    };
    this.savePreferences();
  }

  // 重置为默认偏好
  resetToDefaults(): void {
    this.preferences = {
      ...DEFAULT_PREFERENCES,
      userId: this.preferences.userId,
      lastUpdated: new Date().toISOString(),
    };
    this.savePreferences();
  }

  // 导出偏好设置
  exportPreferences(): string {
    return JSON.stringify(this.preferences, null, 2);
  }

  // 导入偏好设置
  importPreferences(preferencesJson: string): boolean {
    try {
      const imported = JSON.parse(preferencesJson);
      this.preferences = this.validateAndUpdatePreferences(
        imported,
        this.preferences.userId,
      );
      this.savePreferences();
      return true;
    } catch (error) {
      console.error('Failed to import preferences:', error);
      return false;
    }
  }

  // 清除偏好设置
  clearPreferences(): void {
    try {
      localStorage.removeItem(ChartPreferencesManager.STORAGE_KEY);
      this.preferences = {
        ...DEFAULT_PREFERENCES,
        userId: this.preferences.userId,
        lastUpdated: new Date().toISOString(),
      };
    } catch (error) {
      console.error('Failed to clear preferences:', error);
    }
  }
}

// 响应式配置工具
export class ResponsiveChartConfig {
  // 根据屏幕尺寸生成配置
  static generateConfig(screenWidth: number): Partial<UserChartPreferences> {
    const isMobile = screenWidth < 768;
    const isTablet = screenWidth >= 768 && screenWidth < 1024;

    const config: Partial<UserChartPreferences> = {
      layout: {
        height: isMobile ? 300 : isTablet ? 350 : 400,
        padding: {
          top: isMobile ? 10 : 20,
          right: isMobile ? 10 : 20,
          bottom: isMobile ? 10 : 20,
          left: isMobile ? 10 : 20,
        },
        showControls: !isMobile,
        showLegend: !isMobile,
        showTooltip: true,
        responsive: true,
      },
      interactionConfig: {
        enableZoom: !isMobile,
        enablePan: !isMobile,
        enableDataLabels: false,
        enableCrosshair: false,
      },
      performanceConfig: {
        maxDataPoints: isMobile ? 500 : isTablet ? 750 : 1000,
        enableAnimation: !isMobile,
        animationDuration: isMobile ? 500 : 750,
      },
      theme: isMobile ? DEFAULT_THEMES.light : DEFAULT_THEMES.light,
    };

    return config;
  }

  // 获取当前屏幕尺寸的配置
  static getCurrentConfig(): Partial<UserChartPreferences> {
    if (typeof window === 'undefined') {
      return this.generateConfig(1024); // 默认桌面尺寸
    }

    return this.generateConfig(window.innerWidth);
  }

  // 监听屏幕尺寸变化
  static onScreenSizeChange(callback: (config: Partial<UserChartPreferences>) => void): () => void {
    if (typeof window === 'undefined') {
      return () => {};
    }

    let currentWidth = window.innerWidth;

    const handleResize = () => {
      const newWidth = window.innerWidth;
      if (Math.abs(newWidth - currentWidth) > 100) { // 只在显著变化时触发
        currentWidth = newWidth;
        callback(this.generateConfig(newWidth));
      }
    };

    window.addEventListener('resize', handleResize, { passive: true });

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }
}

// 工具函数
export const ChartPreferencesUtils = {
  // 生成主题CSS变量
  generateThemeCSS(theme: ChartTheme): string {
    return `
      :root {
        --chart-bg-color: ${theme.colors.background};
        --chart-grid-color: ${theme.colors.grid};
        --chart-text-color: ${theme.colors.text};
        --chart-price-color: ${theme.colors.price};
        --chart-buy-signal-color: ${theme.colors.buySignal};
        --chart-sell-signal-color: ${theme.colors.sellSignal};
        --chart-ma-color: ${theme.colors.movingAverage};
        --chart-volume-color: ${theme.colors.volume};
        --chart-font-family: ${theme.fonts.family};
        --chart-title-size: ${theme.fonts.size.title}px;
        --chart-legend-size: ${theme.fonts.size.legend}px;
        --chart-axis-size: ${theme.fonts.size.axis}px;
        --chart-tooltip-size: ${theme.fonts.size.tooltip}px;
        --chart-line-width: ${theme.styles.lineWidth}px;
        --chart-point-radius: ${theme.styles.pointRadius}px;
      }
    `;
  },

  // 应用主题到DOM
  applyThemeToDOM(theme: ChartTheme): void {
    if (typeof document === 'undefined') return;

    const root = document.documentElement;
    root.style.setProperty('--chart-bg-color', theme.colors.background);
    root.style.setProperty('--chart-grid-color', theme.colors.grid);
    root.style.setProperty('--chart-text-color', theme.colors.text);
    root.style.setProperty('--chart-price-color', theme.colors.price);
    root.style.setProperty('--chart-buy-signal-color', theme.colors.buySignal);
    root.style.setProperty('--chart-sell-signal-color', theme.colors.sellSignal);
    root.style.setProperty('--chart-ma-color', theme.colors.movingAverage);
    root.style.setProperty('--chart-volume-color', theme.colors.volume);
  },

  // 检测系统主题偏好
  detectSystemTheme(): 'light' | 'dark' {
    if (typeof window === 'undefined') return 'light';

    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  },

  // 监听系统主题变化
  onSystemThemeChange(callback: (theme: 'light' | 'dark') => void): () => void {
    if (typeof window === 'undefined') return () => {};

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e: MediaQueryListEvent) => {
      callback(e.matches ? 'dark' : 'light');
    };

    mediaQuery.addEventListener('change', handleChange);

    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  },
};
